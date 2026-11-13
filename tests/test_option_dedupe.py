#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-13 - smart-voca - 4지선다·OX·빈칸형 보기에 '정답과 같은 뜻(영어)'의 단어가 들어가지 않는지 검사
# 파일 위치: tests/test_option_dedupe.py
"""뜻이 같은 동의어(evident/obvious)나 채점상 같은 답(observe '(법을) 지키다' / protect '지키다',
check out / checkout)이 보기에 함께 나오면 정답이 둘이 되어 버린다. 시험을 여러 번 만들어 모든 보기를 검사한다."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import create_app  # noqa: E402
from src.business.test_engine import normalize_answer, pick_distractors  # noqa: E402

TWINS = [  # (영어, 뜻, 예문)
    ('evident', '명백한', 'The risk is evident.'),
    ('obvious', '명백한', 'The answer is obvious.'),
    ('observe', '(법을) 지키다', 'Please observe the rules.'),
    ('protect', '지키다', 'The fence will protect the garden.'),
    ('check out', '퇴실하다', 'Guests must check out by noon.'),
    ('checkout', '계산대', 'The checkout is on the left.'),
]
FILLERS = [('apple', '사과'), ('banana', '바나나'), ('cherry', '체리'), ('dog', '개'),
           ('egg', '달걀'), ('fish', '물고기'), ('grape', '포도'), ('house', '집')]
ROUNDS = 25


@pytest.fixture()
def app_and_user(tmp_path, monkeypatch):
    monkeypatch.setenv('ADMIN_USERNAME', 'admin')
    monkeypatch.setenv('ADMIN_PASSWORD', 'admin1234')
    app = create_app(tmp_path)
    app.config['TESTING'] = True
    for en, ko, ex in TWINS:
        app.words.add_word(en, ko, 'noun', ex)
    for en, ko in FILLERS:
        app.words.add_word(en, ko)
    user = app.auth.register('kim', 'pass1234', display_name='Kim')
    return app, user['id']


def collect_problems(app, user_id, fmt, mode):
    problems = []
    for _ in range(ROUNDS):
        app.tests.start_test(user_id, {'num_problems': len(TWINS) + len(FILLERS), 'mode': mode, 'format': fmt})
        problems += app.tests._load(user_id)['problems']
    return problems


@pytest.mark.parametrize('fmt', ['4지선다형', '빈칸형'])
@pytest.mark.parametrize('mode', ['영->한', '한->영'])
def test_choice_options_never_contain_a_second_correct_answer(app_and_user, fmt, mode):
    app, user_id = app_and_user
    problems = collect_problems(app, user_id, fmt, mode)
    twin_words = {w['id'] for w in app.db.query("SELECT id FROM words WHERE english IN "
                                                "('evident','obvious','observe','protect','check out','checkout')")}
    assert twin_words <= {p['word_id'] for p in problems}        # 겹치는 단어들이 실제로 출제되었다
    for p in problems:
        correct_key = normalize_answer(p['correct_answer'])
        keys = [normalize_answer(o) for o in p['options']]
        assert p['correct_answer'] in p['options']
        assert keys.count(correct_key) == 1, p                     # 정답과 같은 답이 보기에 하나뿐
        assert len(set(keys)) == len(keys), p                      # 보기끼리 같은 답도 없다


@pytest.mark.parametrize('mode', ['영->한', '한->영'])
def test_ox_false_pairs_are_really_false(app_and_user, mode):
    app, user_id = app_and_user
    problems = collect_problems(app, user_id, 'OX형', mode)
    saw_false = False
    for p in problems:
        word = app.db.query_one("SELECT english, korean FROM words WHERE id = ?", (p['word_id'],))
        real = word['english'] if mode == '한->영' else word['korean']
        if p['correct_answer'] == 'O':
            assert p['shown'] == real
        else:
            saw_false = True
            assert normalize_answer(p['shown']) != normalize_answer(real), (word, p['shown'])   # 'X' 인데 사실은 같은 뜻
    assert saw_false


def test_pick_distractors_unit():
    out = pick_distractors(['명백한', '지키다', '(법을) 지키다', '사과', '사과 ', '배'], '지키다', 3)
    keys = [normalize_answer(o) for o in out]
    assert '지키다' not in keys and len(set(keys)) == len(keys) and len(out) <= 3
    assert set(keys) <= {'명백한', '사과', '배'}
    assert pick_distractors([], '정답') == []
    assert pick_distractors(['checkout', 'Check Out'], 'check out') == []
    assert len(pick_distractors(['a', 'b', 'c', 'd', 'e'], 'z', 3)) == 3
