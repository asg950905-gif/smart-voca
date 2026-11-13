#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-13 - smart-voca - 시험 출제 범위: 오늘 공부한 단어 / 지금까지 공부한 단어 / 전체 단어
# 파일 위치: tests/test_test_scope.py

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app import create_app  # noqa: E402
from src.business.test_engine import normalize_answer  # noqa: E402

CSRF = 'test-csrf-token'
TODAY = datetime.now().strftime('%Y-%m-%d')
YESTERDAY = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv('ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('ADMIN_PASSWORD', 'admin1234')
    app = create_app(tmp_path)
    app.config['TESTING'] = True
    for i in range(20):
        app.words.add_word(f'term{i:02d}', f'용어{i:02d}')
    app.words.add_word('evident', '명백한')      # 뜻이 같은 동의어 쌍: 보기에 함께 나오면 안 된다
    app.words.add_word('obvious', '명백한')
    return app


def word_id(app, english):
    return app.db.scalar("SELECT id FROM words WHERE english = ?", (english,))


def new_user(app, name='kim'):
    return app.auth.register(name, 'pass1234', display_name=name)['id']


def study(app, user_id, englishes, correct=True):
    app.study.record_study(user_id, [{'word_id': word_id(app, e), 'is_correct': correct} for e in englishes])


def set_old_stats(app, user_id, englishes, day=YESTERDAY, weight=0):
    for e in englishes:
        app.db.execute("INSERT INTO user_word_stats(user_id, word_id, weight, success_count, fail_count, last_studied) "
                       "VALUES(?,?,?,?,?,?)", (user_id, word_id(app, e), weight, 1, 0, day))


TODAY_WORDS = [f'term{i:02d}' for i in range(5)]
OLD_WORDS = [f'term{i:02d}' for i in range(5, 9)]


@pytest.fixture()
def studied_user(app):
    uid = new_user(app)
    study(app, uid, TODAY_WORDS)
    set_old_stats(app, uid, OLD_WORDS)
    return uid


def asked_ids(app, uid):
    return [p['word_id'] for p in app.tests._load(uid)['problems']]


def ids(app, englishes):
    return {word_id(app, e) for e in englishes}


def login_client(app, username):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_csrf'] = CSRF
    client.post('/login', data={'username': username, 'password': 'pass1234', 'csrf_token': CSRF})
    with client.session_transaction() as sess:
        sess['_csrf'] = CSRF
    return client


def post(client, url, **kw):
    return client.post(url, headers={'X-CSRF-Token': CSRF}, **kw)


# ---------- 범위별 단어 수 ----------
def test_scope_counts(app, studied_user):
    assert app.tests.scope_counts(studied_user) == {'today': 5, 'studied': 9, 'all': 22}
    client = login_client(app, 'kim')
    assert client.get('/api/test/scopes').get_json() == {'today': 5, 'studied': 9, 'all': 22}


def test_scope_counts_are_zero_for_a_new_user_and_need_login(app):
    new_user(app, 'fresh')
    client = login_client(app, 'fresh')
    assert client.get('/api/test/scopes').get_json() == {'today': 0, 'studied': 0, 'all': 22}
    assert app.test_client().get('/api/test/scopes').status_code in (302, 401)


# ---------- ① 오늘 공부한 단어 ----------
def test_today_scope_asks_only_todays_words_and_only_as_many_as_exist(app, studied_user):
    result = app.tests.start_test(studied_user, {'num_problems': 10, 'scope': 'today', 'format': '4지선다형'})
    assert result['total'] == 5 and result['requested'] == 10 and result['short'] is True   # 있는 만큼만
    assert set(asked_ids(app, studied_user)) == ids(app, TODAY_WORDS)
    assert result['config']['scope'] == 'today'


def test_scope_is_not_short_when_enough_words_exist(app, studied_user):
    result = app.tests.start_test(studied_user, {'num_problems': 5, 'scope': 'today'})
    assert result['total'] == 5 and result['short'] is False


# ---------- ② 지금까지 공부한 단어 ----------
def test_studied_scope_includes_older_words_but_not_unseen_ones(app, studied_user):
    app.tests.start_test(studied_user, {'num_problems': 30, 'scope': 'studied'})
    assert set(asked_ids(app, studied_user)) == ids(app, TODAY_WORDS + OLD_WORDS)


@pytest.mark.parametrize('scope', ['today', 'studied'])
def test_wrong_words_come_first_inside_the_scope(app, studied_user, scope):
    app.db.execute("UPDATE user_word_stats SET weight = 9 WHERE user_id = ? AND word_id = ?",
                   (studied_user, word_id(app, 'term02')))
    app.db.execute("UPDATE user_word_stats SET weight = 5 WHERE user_id = ? AND word_id = ?",
                   (studied_user, word_id(app, 'term04')))
    for _ in range(8):                                   # 나머지는 무작위라 여러 번 반복해 우선순위를 확인
        app.tests.start_test(studied_user, {'num_problems': 2, 'scope': scope})
        assert set(asked_ids(app, studied_user)) == ids(app, ['term02', 'term04'])


# ---------- ③ 전체 단어 / 기본값 ----------
def test_all_scope_and_omitted_scope_ask_from_every_word(app):
    uid = new_user(app)                                  # 학습 기록이 전혀 없는 사용자
    for config in ({'num_problems': 10, 'scope': 'all'}, {'num_problems': 10}):
        result = app.tests.start_test(uid, config)
        assert result['total'] == 10 and result['config']['scope'] == 'all'   # scope 생략 = 예전처럼 전체


@pytest.mark.parametrize('config', [{'scope': 'all'}, {}])        # {} = scope 생략(기본값 all)
def test_all_scope_is_random_and_ignores_wrong_word_priority(app, studied_user, config):
    """③ 전체 단어는 틀린 단어(weight) 우선이 없다. weight 가 아주 높은 단어가 있어도 매번 그 단어만 나오지 않는다."""
    app.db.execute("UPDATE user_word_stats SET weight = 99 WHERE user_id = ? AND word_id = ?",
                   (studied_user, word_id(app, 'term02')))
    heavy, picked = word_id(app, 'term02'), []
    for _ in range(60):
        app.tests.start_test(studied_user, {'num_problems': 1, **config})
        picked += asked_ids(app, studied_user)
    assert len(set(picked)) >= 6                                       # 22개 단어에서 골고루 (weight 우선이면 1개뿐)
    assert picked.count(heavy) < 30                                     # 기대값은 60/22 ≈ 3회


def test_all_scope_can_pick_words_the_user_never_studied(app, studied_user):
    studied = ids(app, TODAY_WORDS + OLD_WORDS)
    seen = set()
    for _ in range(40):
        app.tests.start_test(studied_user, {'num_problems': 3, 'scope': 'all'})
        seen |= set(asked_ids(app, studied_user))
    assert seen - studied                                               # 공부하지 않은 단어도 출제된다


# ---------- 빈 범위 / 잘못된 범위 ----------
@pytest.mark.parametrize('scope, message', [('today', '오늘 공부한 단어가 없어요'), ('studied', '아직 공부한 단어가 없어요')])
def test_empty_scope_tells_the_user_to_study_first(app, scope, message):
    new_user(app)
    client = login_client(app, 'kim')
    resp = post(client, '/api/test/start', json={'num_problems': 10, 'scope': scope})
    assert resp.status_code == 400
    error = resp.get_json()['message'] if 'message' in resp.get_json() else resp.get_json()['error']
    assert message in error and '먼저 학습을 해주세요' in error
    assert app.db.scalar("SELECT COUNT(*) FROM test_sessions") == 0       # 시험이 만들어지지 않았다


def test_yesterdays_study_does_not_count_for_today(app):
    uid = new_user(app)
    set_old_stats(app, uid, TODAY_WORDS)                 # 전부 어제 공부한 단어
    with pytest.raises(Exception, match='오늘 공부한 단어가 없어요'):
        app.tests.start_test(uid, {'scope': 'today'})
    assert app.tests.start_test(uid, {'scope': 'studied', 'num_problems': 10})['total'] == 5


@pytest.mark.parametrize('bad', ['week', '', 'TODAY', 1, None, ['today']])
def test_invalid_scope_is_rejected(app, bad):
    uid = new_user(app)
    study(app, uid, TODAY_WORDS)
    with pytest.raises(Exception, match='출제 범위'):
        app.tests.start_test(uid, {'scope': bad})


# ---------- 보기는 지금처럼 전체 단어에서 (같은 뜻 제외 규칙 유지) ----------
def test_options_still_come_from_all_words_not_only_the_scope(app, studied_user):
    in_scope_korean = {f'용어{i:02d}' for i in range(5)}
    outside = False
    for _ in range(25):
        app.tests.start_test(studied_user, {'num_problems': 5, 'scope': 'today', 'mode': '영->한', 'format': '4지선다형'})
        for p in app.tests._load(studied_user)['problems']:
            assert len(p['options']) == 4                                  # 범위가 5단어뿐이어도 보기는 4개
            outside = outside or any(o not in in_scope_korean for o in p['options'])
    assert outside


def test_same_meaning_words_are_still_excluded_from_options(app):
    uid = new_user(app)
    study(app, uid, ['evident'] + TODAY_WORDS)
    for _ in range(25):
        app.tests.start_test(uid, {'num_problems': 6, 'scope': 'today', 'mode': '영->한', 'format': '4지선다형'})
        for p in app.tests._load(uid)['problems']:
            keys = [normalize_answer(o) for o in p['options']]
            assert keys.count(normalize_answer(p['correct_answer'])) == 1 and len(set(keys)) == 4


# ---------- 사용자 격리 / 학습·시험에서 본 단어 기준 ----------
def test_other_users_study_does_not_leak_into_my_scope(app, studied_user):
    other = new_user(app, 'other')
    assert app.tests.scope_counts(other)['today'] == 0
    with pytest.raises(Exception, match='오늘 공부한 단어가 없어요'):
        app.tests.start_test(other, {'scope': 'today'})


def test_words_seen_in_a_test_count_as_studied_words(app):
    """범위는 user_word_stats(학습·시험에서 본 단어) 기준이다 — 안내 문구와 같은 규칙."""
    uid = new_user(app)
    app.tests.start_test(uid, {'num_problems': 6, 'scope': 'all', 'format': '단답형'})
    for p in app.tests._load(uid)['problems']:
        app.tests.grade_answer(uid, p['correct_answer'])
    app.tests.finish_test(uid)
    counts = app.tests.scope_counts(uid)
    assert counts['today'] == counts['studied'] == 6
    assert app.tests.start_test(uid, {'num_problems': 10, 'scope': 'today'})['total'] == 6


# ---------- 화면 ----------
def test_test_page_has_scope_choices_with_the_requested_labels(app):
    new_user(app)
    html = login_client(app, 'kim').get('/test').get_data(as_text=True)
    assert '출제 범위' in html
    for label in ('오늘 공부한 단어', '지금까지 공부한 단어', '전체 단어'):
        assert label in html
    assert html.count('학습·시험에서 본 단어 기준') == 2                       # ①② 에만 안내 문구
    assert 'name="scope" value="today" checked' in html                      # 기본값은 ① 오늘 공부한 단어
    js = (ROOT / 'static' / 'js' / 'test.js').read_text(encoding='utf-8')
    assert "scope: radio('scope')" in js and '/api/test/scopes' in js and '먼저 학습을 해주세요' in js
