#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - 백엔드 통합 테스트 (인증·권한·CSRF·단어 CRUD·학습·시험·통계 격리)
# 파일 위치: tests/test_backend.py

import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import create_app  # noqa: E402

CSRF = 'test-csrf-token'
SAMPLE_WORDS = [
    ('apple', '사과'), ('banana', '바나나'), ('cherry', '체리'), ('dog', '개'),
    ('egg', '달걀'), ('fish', '물고기'), ('grape', '포도'), ('house', '집'),
]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv('ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('ADMIN_PASSWORD', 'admin1234')
    app = create_app(tmp_path)
    app.config['TESTING'] = True
    for en, ko in SAMPLE_WORDS:
        app.words.add_word(en, ko)
    return app


def new_client(app):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_csrf'] = CSRF
    return client


def login(client, username, password):
    resp = client.post('/login', data={'username': username, 'password': password, 'csrf_token': CSRF})
    # 로그인은 세션을 새로 만들므로 토큰도 사라진다. 실제 브라우저는 리다이렉트된 페이지를 렌더링하며
    # 새 토큰을 받으므로, 테스트에서도 같은 상황을 재현한다.
    with client.session_transaction() as sess:
        sess['_csrf'] = CSRF
    return resp


def api(client, method, url, **kwargs):
    headers = {'X-CSRF-Token': CSRF}
    return getattr(client, method)(url, headers=headers, **kwargs)


@pytest.fixture()
def admin(app):
    client = new_client(app)
    assert login(client, 'admin', 'admin1234').status_code == 302
    return client


def make_user(app, username='kim', password='pass1234'):
    app.auth.register(username, password, display_name=username)
    client = new_client(app)
    assert login(client, username, password).status_code == 302
    return client


# ---------- 인증/권한 ----------
def test_anonymous_is_blocked(app):
    client = new_client(app)
    assert client.get('/').status_code == 302
    assert client.get('/api/progress').status_code == 401
    assert client.get('/api/admin/overview').status_code == 401


def test_register_validation_and_login(app):
    client = new_client(app)
    bad = client.post('/register', data={'username': 'a', 'password': 'x', 'password_confirm': 'x', 'csrf_token': CSRF})
    assert bad.status_code == 200  # 검증 실패 시 폼 다시 표시
    ok = client.post('/register', data={'username': 'lee', 'password': 'pass1234',
                                        'password_confirm': 'pass1234', 'csrf_token': CSRF})
    assert ok.status_code == 302
    assert api(client, 'get', '/api/progress').status_code == 200


def test_register_cannot_choose_admin_role(app):
    client = new_client(app)
    client.post('/register', data={'username': 'sneaky', 'password': 'pass1234', 'password_confirm': 'pass1234',
                                   'csrf_token': CSRF, 'role': 'admin'})
    assert app.auth.db.scalar("SELECT role FROM users WHERE username = 'sneaky'", default='') == 'user'


def test_wrong_password_and_inactive(app):
    app.auth.register('park', 'pass1234')
    client = new_client(app)
    assert login(client, 'park', 'wrong').status_code == 200
    uid = app.db.scalar("SELECT id FROM users WHERE username = 'park'")
    app.auth.set_active(uid, False, acting_user_id=999)
    assert login(client, 'park', 'pass1234').status_code == 200


def test_login_lockout_after_repeated_failures(app):
    app.auth.register('choi', 'pass1234')
    client = new_client(app)
    for _ in range(5):
        login(client, 'choi', 'bad')
    assert login(client, 'choi', 'pass1234').status_code == 200  # 올바른 비밀번호여도 잠금


def test_csrf_required_for_state_changes(app):
    client = make_user(app)
    assert client.post('/api/settings/reset').status_code == 400  # 토큰 없음
    assert api(client, 'post', '/api/settings/reset').status_code == 200


def test_user_cannot_access_admin(app):
    client = make_user(app)
    assert client.get('/admin/').status_code == 403
    assert api(client, 'get', '/api/admin/users').status_code == 403
    assert api(client, 'post', '/api/admin/words', json={'english': 'x', 'korean': 'y'}).status_code == 403


def test_open_redirect_blocked(app):
    app.auth.register('han', 'pass1234')
    client = new_client(app)
    resp = client.post('/login?next=//evil.example', data={'username': 'han', 'password': 'pass1234', 'csrf_token': CSRF})
    assert resp.status_code == 302 and 'evil.example' not in resp.headers['Location']


# ---------- 관리자: 단어 ----------
def test_admin_word_crud_and_duplicates(admin):
    created = api(admin, 'post', '/api/admin/words', json={'english': 'Zebra', 'korean': '얼룩말'})
    assert created.status_code == 201
    word_id = created.get_json()['id']
    assert api(admin, 'post', '/api/admin/words', json={'english': 'zebra', 'korean': '중복'}).status_code == 400
    assert api(admin, 'put', f'/api/admin/words/{word_id}', json={'english': 'Zebra', 'korean': '제브라'}).status_code == 200
    assert api(admin, 'get', '/api/admin/words?q=제브라').get_json()['total'] == 1
    assert api(admin, 'delete', f'/api/admin/words/{word_id}').status_code == 200
    assert api(admin, 'delete', f'/api/admin/words/{word_id}').status_code == 400


def test_csv_import(admin):
    csv_bytes = '﻿english,korean,part_of_speech,example\nlion,사자,noun,\napple,중복,noun,\n,빈값,,\n'.encode('utf-8')
    resp = api(admin, 'post', '/api/admin/words/import',
               data={'file': (io.BytesIO(csv_bytes), 'w.csv')}, content_type='multipart/form-data')
    body = resp.get_json()
    assert resp.status_code == 200 and body['added'] == 1 and body['skipped'] == 2
    bad = api(admin, 'post', '/api/admin/words/import',
              data={'file': (io.BytesIO(b'a,b\n1,2\n'), 'w.csv')}, content_type='multipart/form-data')
    assert bad.status_code == 400
    exported = api(admin, 'get', '/api/admin/words/export')
    assert b'lion' in exported.data


# ---------- 관리자: 사용자 ----------
def test_admin_user_management_guards(app, admin):
    make_user(app, 'kim')
    uid = app.db.scalar("SELECT id FROM users WHERE username = 'kim'")
    admin_id = app.db.scalar("SELECT id FROM users WHERE username = 'admin'")
    assert api(admin, 'post', f'/api/admin/users/{admin_id}/role', json={'role': 'user'}).status_code == 400
    assert api(admin, 'delete', f'/api/admin/users/{admin_id}').status_code == 400
    assert api(admin, 'post', f'/api/admin/users/{uid}/role', json={'role': 'superuser'}).status_code == 400
    assert api(admin, 'post', f'/api/admin/users/{uid}/password', json={'password': '12'}).status_code == 400
    assert api(admin, 'post', f'/api/admin/users/{uid}/password', json={'password': 'newpass99'}).status_code == 200
    assert api(admin, 'delete', f'/api/admin/users/{uid}').status_code == 200


def test_deactivated_session_is_invalidated(app, admin):
    kim = make_user(app, 'kim')
    uid = app.db.scalar("SELECT id FROM users WHERE username = 'kim'")
    api(admin, 'post', f'/api/admin/users/{uid}/active', json={'active': False})
    assert api(kim, 'get', '/api/progress').status_code == 401


# ---------- 학습/시험/통계 ----------
def test_study_flow_and_progress(app):
    client = make_user(app)
    words = api(client, 'get', '/api/study/daily-words').get_json()
    assert len(words) == 8  # 단어 8개 < 하루 목표 10
    results = [{'word_id': w['id'], 'is_correct': i % 2 == 0} for i, w in enumerate(words)]
    assert api(client, 'post', '/api/study/record', json={'results': results}).get_json()['correct_count'] == 4
    progress = api(client, 'get', '/api/progress').get_json()
    assert progress['studied_days'] == 1 and progress['studied_today'] and progress['streak'] == 1
    assert api(client, 'post', '/api/study/record', json={'results': 'bad'}).status_code == 400
    assert api(client, 'post', '/api/study/record', json={'results': [{'word_id': 9999, 'is_correct': True}]}) \
        .get_json()['words_count'] == 0  # 존재하지 않는 단어는 무시


def test_daily_words_prioritize_wrong_answers(app):
    client = make_user(app)
    api(client, 'post', '/api/settings', json={'daily_target': 5, 'theme': 'dark'})
    words = api(client, 'get', '/api/study/daily-words').get_json()
    target = words[0]
    api(client, 'post', '/api/study/record', json={'results': [{'word_id': target['id'], 'is_correct': False}]})
    again = api(client, 'get', '/api/study/daily-words').get_json()
    assert len(again) == 5 and again[0]['id'] == target['id']


def test_full_test_flow_hides_answers(app):
    client = make_user(app)
    assert api(client, 'post', '/api/test/start', json={'num_problems': 4, 'mode': '영->한', 'format': '4지선다형'}) \
        .get_json()['total'] == 4
    answered = 0
    while True:
        problem = api(client, 'get', '/api/test/current').get_json()
        if problem['finished']:
            break
        assert 'correct_answer' not in problem and len(problem['options']) == 4
        graded = api(client, 'post', '/api/test/answer', json={'answer': problem['options'][0]}).get_json()
        assert 'is_correct' in graded
        answered += 1
    result = api(client, 'post', '/api/test/finish').get_json()
    assert result['total_problems'] == answered == 4
    assert api(client, 'get', '/api/test/current').status_code == 404  # 세션 종료됨
    assert api(client, 'get', '/api/report/statistics').get_json()['total_test_attempts'] == 1


def test_test_validation(app):
    client = make_user(app)
    assert api(client, 'post', '/api/test/start', json={'mode': '이상한모드'}).status_code == 400
    assert api(client, 'post', '/api/test/answer', json={'answer': 'x'}).status_code == 400  # 시험 없음


def test_users_data_is_isolated(app, admin):
    a, b = make_user(app, 'userA'), make_user(app, 'userB')
    words = api(a, 'get', '/api/study/daily-words').get_json()
    api(a, 'post', '/api/study/record', json={'results': [{'word_id': w['id'], 'is_correct': True} for w in words]})
    assert api(a, 'get', '/api/progress').get_json()['studied_days'] == 1
    assert api(b, 'get', '/api/progress').get_json()['studied_days'] == 0  # B 에게는 A 의 기록이 보이지 않음
    # 동시에 각자 시험 진행
    api(a, 'post', '/api/test/start', json={'num_problems': 3})
    api(b, 'post', '/api/test/start', json={'num_problems': 5})
    assert api(a, 'get', '/api/test/current').get_json()['total'] == 3
    assert api(b, 'get', '/api/test/current').get_json()['total'] == 5
    overview = api(admin, 'get', '/api/admin/overview').get_json()
    assert overview['total_users'] == 2 and overview['active_today'] == 1


def test_admin_charts_and_settings(app, admin):
    client = make_user(app)
    words = api(client, 'get', '/api/study/daily-words').get_json()
    api(client, 'post', '/api/study/record', json={'results': [{'word_id': w['id'], 'is_correct': False} for w in words]})
    charts = api(admin, 'get', '/api/admin/charts').get_json()
    assert len(charts['hard_words']['labels']) > 0 and charts['ranking'][0]['words'] == 8
    assert api(admin, 'post', '/api/admin/settings', json={'max_test_problems': 3}).status_code == 400  # 하한 5
    assert api(admin, 'post', '/api/admin/settings', json={'max_test_problems': 20}).get_json()['max_test_problems'] == 20
    assert api(client, 'post', '/api/settings', json={'daily_target': 500}).status_code == 400


# ---------- 화면(HTML) 렌더링 ----------
USER_PAGES = ['/', '/study', '/test', '/report', '/settings']
ADMIN_PAGES = ['/admin/', '/admin/words', '/admin/users', '/admin/settings']


def test_all_user_pages_render(app):
    client = make_user(app)
    for url in USER_PAGES:
        assert client.get(url).status_code == 200, url
    assert client.get('/nope').status_code == 404


def test_all_admin_pages_render_and_login_redirects_by_role(app, admin):
    for url in ADMIN_PAGES + USER_PAGES:  # 관리자도 사용자 화면을 볼 수 있다
        assert admin.get(url).status_code == 200, url
    fresh = new_client(app)
    assert login(fresh, 'admin', 'admin1234').headers['Location'].endswith('/admin/')
    app.auth.register('plain', 'pass1234')
    other = new_client(app)
    assert login(other, 'plain', 'pass1234').headers['Location'].endswith('/')



# ---------- 리허설에서 발견한 문제의 회귀 테스트 ----------
def test_forbidden_page_does_not_leak_admin_menu(app):
    client = make_user(app)
    resp = client.get('/admin/')
    html = resp.get_data(as_text=True)
    assert resp.status_code == 403
    assert '/admin/words' not in html and 'ADMIN' not in html  # 일반 사용자에게 관리자 메뉴 구조를 보여주지 않는다


def test_deactivated_user_sees_reason_after_redirect(app, admin):
    kim = make_user(app, 'kim')
    uid = app.db.scalar("SELECT id FROM users WHERE username = 'kim'")
    api(admin, 'post', f'/api/admin/users/{uid}/active', json={'active': False})
    assert kim.get('/').status_code == 302  # 로그인 화면으로 이동
    assert '비활성화되었거나 삭제되어' in kim.get('/login').get_data(as_text=True)  # 이유를 안내한다
