#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-13 - smart-voca - 한→영 단답형: 뜻이 같은 동의어를 입력해도 정답 처리 ("정답 처리 (출제 단어: obvious)")
# 파일 위치: tests/test_synonym_grading.py

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import create_app  # noqa: E402

CSRF = 'test-csrf-token'
TWINS = {'evident': 'obvious', 'obvious': 'evident'}          # 뜻이 같은 동의어 (둘 다 "명백한")
WORDS = [('evident', '명백한'), ('obvious', '명백한'), ('observe', '(법을) 지키다'), ('protect', '보호하다'),
         ('apple', '사과'), ('banana', '바나나'), ('cherry', '체리'), ('dog', '개'), ('egg', '달걀'), ('fish', '물고기')]


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv('ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('ADMIN_PASSWORD', 'admin1234')
    app = create_app(tmp_path)
    app.config['TESTING'] = True
    for en, ko in WORDS:
        app.words.add_word(en, ko)
    return app


@pytest.fixture()
def user_id(app):
    return app.auth.register('kim', 'pass1234', display_name='Kim')['id']


def run_test(app, user_id, answer_for, mode='한->영', fmt='단답형'):
    """시험을 만들고 문제마다 answer_for(문제) 를 제출한다. [(문제, 채점 결과)] 를 돌려준다."""
    app.tests.start_test(user_id, {'num_problems': len(WORDS), 'mode': mode, 'format': fmt})
    problems = app.tests._load(user_id)['problems']
    return [(p, app.tests.grade_answer(user_id, answer_for(p))) for p in problems]


def test_synonym_is_accepted_and_reports_the_asked_word(app, user_id):
    out = run_test(app, user_id, lambda p: TWINS.get(p['correct_answer'], p['correct_answer']))
    twin_results = [(p, r) for p, r in out if p['correct_answer'] in TWINS]
    assert len(twin_results) == 2
    for p, r in twin_results:
        assert r['is_correct'] is True
        assert r['correct_answer'] == p['correct_answer']                 # 출제 단어
        assert r['synonym'] == TWINS[p['correct_answer']]                 # 사용자가 쓴 동의어
    for p, r in out:
        if p['correct_answer'] not in TWINS:
            assert r['is_correct'] is True and r['synonym'] is None       # 평범한 정답은 동의어 표시가 없다


def test_exact_answer_is_not_marked_as_synonym(app, user_id):
    out = run_test(app, user_id, lambda p: p['correct_answer'])
    assert all(r['is_correct'] and r['synonym'] is None for _, r in out)


@pytest.mark.parametrize('style', [' EVIDENT ', 'Evident', 'evident'])
def test_synonym_ignores_case_and_spaces(app, user_id, style):
    out = run_test(app, user_id, lambda p: style if p['correct_answer'] == 'obvious' else p['correct_answer'])
    (p, r), = [(p, r) for p, r in out if p['correct_answer'] == 'obvious']
    assert r['is_correct'] and r['synonym'] == 'evident'


@pytest.mark.parametrize('wrong', ['apple', 'protect', 'zzzz', '', '   ', '명백한'])
def test_different_meaning_unknown_or_empty_words_stay_wrong(app, user_id, wrong):
    out = run_test(app, user_id, lambda p: wrong if p['correct_answer'] in TWINS else p['correct_answer'])
    for p, r in out:
        if p['correct_answer'] in TWINS:
            assert r['is_correct'] is False and r['synonym'] is None


def test_synonym_rule_applies_only_to_korean_to_english_short_answer(app, user_id):
    # 4지선다: 보기에 없는 동의어를 직접 보내도 정답이 아니다
    out = run_test(app, user_id, lambda p: TWINS.get(p['correct_answer'], p['correct_answer']), fmt='4지선다형')
    for p, r in out:
        if p['correct_answer'] in TWINS:
            assert r['is_correct'] is False and r['synonym'] is None
    # 영→한 단답: 한글 답만 비교한다 (영어 동의어를 보내도 소용없음)
    out = run_test(app, user_id, lambda p: 'evident', mode='영->한')
    assert not any(r['is_correct'] for p, r in out if p['correct_answer'] not in ('명백한',))


def test_finish_counts_synonym_as_correct_for_the_asked_word(app, user_id):
    out = run_test(app, user_id, lambda p: TWINS.get(p['correct_answer'], p['correct_answer']))
    result = app.tests.finish_test(user_id)
    assert result['correct_answers'] == result['total_problems'] == len(WORDS) and result['score'] == 100
    by_word = {d['word_id']: d for d in result['details']}
    for p, r in out:
        detail = by_word[p['word_id']]
        assert detail['correct_answer'] == p['correct_answer'] and detail['synonym'] == r['synonym']
    for p, _ in out:                                              # 통계는 출제된 단어 기준으로 한 번씩 반영
        row = app.db.query_one("SELECT success_count, fail_count FROM user_word_stats WHERE user_id = ? AND word_id = ?",
                               (user_id, p['word_id']))
        assert row == {'success_count': 1, 'fail_count': 0}


def test_api_response_and_result_list_include_the_synonym(app):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_csrf'] = CSRF
    client.post('/login', data={'username': 'admin', 'password': 'admin1234', 'csrf_token': CSRF})
    with client.session_transaction() as sess:
        sess['_csrf'] = CSRF
    post = lambda url, **kw: client.post(url, headers={'X-CSRF-Token': CSRF}, **kw)
    assert post('/api/test/start', json={'num_problems': len(WORDS), 'mode': '한->영', 'format': '단답형'}).status_code == 200
    problems = json.loads(app.db.scalar("SELECT state_json FROM test_sessions"))['problems']
    for p in problems:
        cur = client.get('/api/test/current', headers={'X-CSRF-Token': CSRF}).get_json()
        assert 'correct_answer' not in cur and 'synonym' not in cur          # 출제 중에는 정답·동의어 정보가 없다
        body = post('/api/test/answer', json={'answer': TWINS.get(p['correct_answer'], p['correct_answer'])}).get_json()
        assert body['is_correct'] is True
        assert body['synonym'] == TWINS.get(p['correct_answer'])
    finished = post('/api/test/finish').get_json()
    synonyms = {d['correct_answer']: d['synonym'] for d in finished['details']}
    assert synonyms['obvious'] == 'evident' and synonyms['evident'] == 'obvious' and synonyms['apple'] is None


def test_front_end_shows_the_synonym_notice():
    js = (Path(__file__).resolve().parent.parent / 'static' / 'js' / 'test.js').read_text(encoding='utf-8')
    assert '정답 처리 (출제 단어: ${r.correct_answer})' in js                  # 문제 풀이 중 피드백
    assert '정답 처리 (출제 단어: ${esc(d.correct_answer)})' in js             # 결과 목록 (서버 문자열은 esc 로 감쌈)
