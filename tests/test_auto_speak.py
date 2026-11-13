#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-13 - smart-voca - '카드 넘길 때 자동 발음' 설정 (기본 꺼짐, 계정별 저장, 옛 DB 자동 마이그레이션)
# 파일 위치: tests/test_auto_speak.py

import re
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import create_app  # noqa: E402
from src.data.database import Database  # noqa: E402

CSRF = 'test-csrf-token'


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv('ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('ADMIN_PASSWORD', 'admin1234')
    app = create_app(tmp_path)
    app.config['TESTING'] = True
    for en, ko in [('apple', '사과'), ('banana', '바나나'), ('cherry', '체리'), ('dog', '개')]:
        app.words.add_word(en, ko)
    return app


def make_user(app, username='kim', password='pass1234'):
    app.auth.register(username, password, display_name=username)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_csrf'] = CSRF
    client.post('/login', data={'username': username, 'password': password, 'csrf_token': CSRF})
    with client.session_transaction() as sess:
        sess['_csrf'] = CSRF
    return client


def api(client, method, url, **kwargs):
    return getattr(client, method)(url, headers={'X-CSRF-Token': CSRF}, **kwargs)


def test_auto_speak_is_off_by_default(app):
    client = make_user(app)
    assert api(client, 'get', '/api/settings').get_json()['auto_speak'] is False


def test_auto_speak_can_be_saved_and_read_back(app):
    client = make_user(app)
    saved = api(client, 'post', '/api/settings', json={'daily_target': 10, 'theme': 'system', 'auto_speak': True}).get_json()
    assert saved['auto_speak'] is True
    assert api(client, 'get', '/api/settings').get_json()['auto_speak'] is True
    assert api(client, 'post', '/api/settings', json={'auto_speak': False}).get_json()['auto_speak'] is False


def test_saving_other_settings_keeps_the_switch(app):
    client = make_user(app)
    api(client, 'post', '/api/settings', json={'auto_speak': True})
    after = api(client, 'post', '/api/settings', json={'theme': 'dark'}).get_json()     # 테마 토글은 일부 항목만 보낸다
    assert after['theme'] == 'dark' and after['auto_speak'] is True
    after = api(client, 'post', '/api/settings', json={'daily_target': 7}).get_json()
    assert after['daily_target'] == 7 and after['auto_speak'] is True


@pytest.mark.parametrize('bad', ['yes', 'true', 1, 0, 2, None, [], {}])
def test_auto_speak_rejects_non_boolean_values(app, bad):
    client = make_user(app)
    resp = api(client, 'post', '/api/settings', json={'auto_speak': bad})
    assert resp.status_code == 400
    assert api(client, 'get', '/api/settings').get_json()['auto_speak'] is False


def test_setting_is_per_user(app):
    a, b = make_user(app, 'userone'), make_user(app, 'usertwo')
    api(a, 'post', '/api/settings', json={'auto_speak': True})
    assert api(a, 'get', '/api/settings').get_json()['auto_speak'] is True
    assert api(b, 'get', '/api/settings').get_json()['auto_speak'] is False


def test_progress_reset_keeps_the_setting(app):
    client = make_user(app)
    api(client, 'post', '/api/settings', json={'auto_speak': True})
    assert api(client, 'post', '/api/settings/reset').status_code == 200
    assert api(client, 'get', '/api/settings').get_json()['auto_speak'] is True


def study_stage_attr(client):
    html = client.get('/study').get_data(as_text=True)
    return re.search(r'class="study-stage" data-auto-speak="(\d)"', html).group(1)


def test_study_page_exposes_the_setting_to_the_script(app):
    client = make_user(app)
    assert study_stage_attr(client) == '0'
    api(client, 'post', '/api/settings', json={'auto_speak': True})
    assert study_stage_attr(client) == '1'


def test_settings_page_has_the_switch_and_script_sends_it(app):
    client = make_user(app)
    html = client.get('/settings').get_data(as_text=True)
    assert 'id="auto_speak"' in html and '카드 넘길 때 자동 발음' in html
    js = (ROOT / 'static' / 'js' / 'settings.js').read_text(encoding='utf-8')
    assert 'auto_speak: $(' in js and "$('auto_speak').checked" in js


def test_study_script_never_speaks_without_the_setting():
    """자동 재생 호출이 설정(autoSpeak) 조건 없이 남아 있지 않은지 소스로 확인 (실제 재생 횟수는 브라우저 점검에서 센다)."""
    js = (ROOT / 'static' / 'js' / 'study.js').read_text(encoding='utf-8')
    assert "dataset.autoSpeak === '1'" in js
    render_body = js[js.index('function render()'):js.index('function flip()')]
    for line in render_body.splitlines():
        if 'speak(' in line and 'bindSpeakButtons' not in line:
            assert 'autoSpeak' in line, f'조건 없는 자동 발음: {line.strip()}'
    assert "e.code === 'KeyP'" in js        # P 단축키는 그대로 동작


# ---------- 옛 DB 자동 마이그레이션 ----------
OLD_USERS_TABLE = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    active INTEGER NOT NULL DEFAULT 1, daily_target INTEGER NOT NULL DEFAULT 10, theme TEXT NOT NULL DEFAULT 'system',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')));
INSERT INTO users(username, display_name, password_hash, daily_target, theme) VALUES('old', 'Old', 'x', 15, 'dark');
"""


def test_old_database_gets_the_column_and_a_backup(tmp_path):
    db_file = tmp_path / 'smart_voca.db'
    conn = sqlite3.connect(db_file)
    conn.executescript(OLD_USERS_TABLE)
    conn.commit()
    conn.close()

    db = Database(db_file)                                       # 열기만 해도 마이그레이션
    row = db.query_one("SELECT username, daily_target, theme, auto_speak FROM users")
    assert row == {'username': 'old', 'daily_target': 15, 'theme': 'dark', 'auto_speak': 0}   # 기존 값 보존, 기본 꺼짐
    backups = list(tmp_path.glob('smart_voca_migration_*.db'))
    assert len(backups) == 1                                      # 변경 전 백업이 만들어졌다
    old = sqlite3.connect(backups[0])
    assert 'auto_speak' not in {r[1] for r in old.execute('PRAGMA table_info(users)')}   # 백업은 변경 전 상태
    old.close()

    Database(db_file)                                            # 다시 열어도 추가·백업이 반복되지 않는다
    assert len(list(tmp_path.glob('smart_voca_migration_*.db'))) == 1


def test_fresh_database_has_the_column_without_backup(tmp_path):
    db = Database(tmp_path / 'fresh.db')
    assert 'auto_speak' in {r['name'] for r in db.query("PRAGMA table_info(users)")}
    assert list(tmp_path.glob('*_migration_*.db')) == []
