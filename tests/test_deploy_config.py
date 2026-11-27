#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-27 - smart-voca - 배포 조건 테스트 (import 부작용 없음, DB_PATH, SECRET_KEY, 첫 가입자 관리자)
# 파일 위치: tests/test_deploy_config.py

import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from app import create_app, resolve_db_path  # noqa: E402

CSRF = 'test-csrf-token'
ENV_KEYS = ('DB_PATH', 'DATA_DIR', 'SECRET_KEY', 'ADMIN_USERNAME', 'ADMIN_PASSWORD')


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """개발 PC 에 설정된 환경변수가 테스트 결과를 바꾸지 않도록 지운다."""
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def _snapshot(folder: Path) -> dict:
    if not folder.exists():
        return {}
    return {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in folder.iterdir()}


def _run_python(code: str, env_extra: dict) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in ENV_KEYS}
    env.update(env_extra)
    env['PYTHONUTF8'] = '1'
    return subprocess.run([sys.executable, '-c', code], cwd=PROJECT_ROOT, env=env,
                          capture_output=True, text=True, timeout=60)


# ---------- import 부작용 ----------
def test_importing_app_module_opens_no_database(tmp_path):
    """예전에는 app.py 의 모듈 수준 create_app() 때문에 import 만 해도 실DB(data/)를 열었다."""
    target = tmp_path / 'should_not_exist' / 'voca.db'
    real_data = _snapshot(PROJECT_ROOT / 'data')
    result = _run_python('import app', {'DB_PATH': str(target)})
    assert result.returncode == 0, result.stderr
    assert not target.parent.exists()
    assert _snapshot(PROJECT_ROOT / 'data') == real_data


def test_wsgi_builds_the_app_at_db_path(tmp_path):
    target = tmp_path / 'data' / 'voca.db'
    result = _run_python('import wsgi; print(wsgi.app.name)', {'DB_PATH': str(target)})
    assert result.returncode == 0, result.stderr
    assert target.exists()


# ---------- DB 경로 ----------
def test_db_path_env_is_used_and_tables_are_created(tmp_path, monkeypatch):
    target = tmp_path / 'data' / 'voca.db'
    monkeypatch.setenv('DB_PATH', str(target))
    app = create_app()
    assert target.exists()
    tables = {r['name'] for r in app.db.query("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {'users', 'words', 'user_word_stats', 'study_logs', 'test_logs'} <= tables
    assert app.words.count() == 0          # 시드 단어는 자동으로 넣지 않는다 (시연에서 CSV 가져오기)
    assert (target.parent / 'secret_key.txt').exists()


def test_argument_wins_over_db_path(tmp_path, monkeypatch):
    monkeypatch.setenv('DB_PATH', str(tmp_path / 'env' / 'voca.db'))
    assert resolve_db_path(tmp_path / 'arg') == tmp_path / 'arg' / 'smart_voca.db'


def test_data_dir_is_still_supported(tmp_path, monkeypatch):
    monkeypatch.setenv('DATA_DIR', str(tmp_path))
    assert resolve_db_path() == tmp_path / 'smart_voca.db'


# ---------- SECRET_KEY ----------
def test_secret_key_is_generated_once_and_reused(tmp_path):
    first = create_app(tmp_path).config['SECRET_KEY']
    assert len(first) == 64
    assert create_app(tmp_path).config['SECRET_KEY'] == first     # worker·재시작 사이에 같은 키


def test_secret_key_env_wins_and_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'from-env')
    assert create_app(tmp_path).config['SECRET_KEY'] == 'from-env'
    assert not (tmp_path / 'secret_key.txt').exists()


# ---------- 첫 가입자 관리자 ----------
def _sign_up(app, username):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_csrf'] = CSRF
    resp = client.post('/register', data={'username': username, 'password': 'pass1234',
                                           'password_confirm': 'pass1234', 'csrf_token': CSRF})
    return client, resp


def _role(app, username):
    return app.db.scalar("SELECT role FROM users WHERE username = ?", (username,))


def test_first_sign_up_on_empty_db_becomes_admin(tmp_path):
    app = create_app(tmp_path)
    client, resp = _sign_up(app, 'first')
    assert resp.status_code == 302 and resp.headers['Location'].endswith('/admin/')
    assert _role(app, 'first') == 'admin'
    with client.session_transaction() as sess:
        sess['_csrf'] = CSRF
    # 관리자라서 단어 CSV 가져오기를 바로 할 수 있다
    csv_bytes = 'english,korean\napple,사과\n'.encode('utf-8-sig')
    resp = client.post('/api/admin/words/import', headers={'X-CSRF-Token': CSRF},
                       data={'file': (BytesIO(csv_bytes), 'words.csv')}, content_type='multipart/form-data')
    assert resp.status_code == 200 and app.words.count() == 1


def test_later_sign_ups_are_normal_users(tmp_path):
    app = create_app(tmp_path)
    _sign_up(app, 'first')
    _, resp = _sign_up(app, 'second')
    assert resp.headers['Location'] == '/'      # 일반 회원은 내 대시보드
    assert _role(app, 'second') == 'user'


def test_admin_env_takes_priority_over_first_sign_up(tmp_path, monkeypatch):
    monkeypatch.setenv('ADMIN_USERNAME', 'boss')
    monkeypatch.setenv('ADMIN_PASSWORD', 'boss1234')
    app = create_app(tmp_path)
    _sign_up(app, 'first')
    assert _role(app, 'boss') == 'admin'
    assert _role(app, 'first') == 'user'


def test_admin_is_not_created_again_when_one_exists(tmp_path):
    app = create_app(tmp_path)
    app.auth.register('existing_admin', 'pass1234', role='admin')
    _sign_up(app, 'newbie')
    assert _role(app, 'newbie') == 'user'
