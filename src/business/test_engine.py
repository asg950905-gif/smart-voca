#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - 시험 엔진 (사용자별 시험 세션을 DB 에 저장해 동시 응시를 지원)
# 파일 위치: src/business/test_engine.py

import json
import logging
import random
import re
from datetime import datetime
from typing import Dict, Optional
from src.data.database import Database
from src.business.word_manager import WordManager
from src.business.gamification import GamificationManager, level_info, quiz_xp

logger = logging.getLogger(__name__)

MODES = ('한->영', '영->한', '혼합')
FORMATS = ('단답형', '4지선다형', 'OX형', '빈칸형', '혼합')
MIN_WORDS_FOR_CHOICE = 4  # 4지선다형은 오답 보기를 만들 단어가 최소 4개 필요
# 출제 범위: 오늘 공부한 단어 / 지금까지 공부한 단어 / 전체 단어. 앞의 둘은 user_word_stats(학습·시험에서 본 단어) 기준이다.
SCOPES = ('today', 'studied', 'all')
DEFAULT_SCOPE = 'all'   # scope 를 보내지 않는 기존 호출은 예전처럼 전체 단어에서 출제한다 (화면은 항상 'today' 를 보낸다)
SCOPE_EMPTY_MESSAGE = {
    'today': '오늘 공부한 단어가 없어요. 먼저 학습을 해주세요.',
    'studied': '아직 공부한 단어가 없어요. 먼저 학습을 해주세요.',
}

_BRACKETED = re.compile(r'[(\[（［][^)\]）］]*[)\]）］]')   # (법을) [예] 같은 보충 설명


def normalize_answer(text: str) -> str:
    """채점용 정규화: 괄호 안 설명, 물결표(~), 모든 공백을 지우고 소문자로 만든다.
    예) '(법을) 지키다' 와 '지키다' 와 '법을지키다' 중 괄호 밖 글자만 같으면 같은 답으로 본다."""
    text = _BRACKETED.sub('', text or '')
    return re.sub(r'[~～\s]+', '', text).lower()


def is_same_answer(user_answer: str, correct_answer: str) -> bool:
    user, correct = normalize_answer(user_answer), normalize_answer(correct_answer)
    if not correct:                   # 정답이 전부 괄호 같은 기호라 비면 원문끼리 비교 (빈 입력은 오답)
        raw_user = (user_answer or '').strip().lower()
        return bool(raw_user) and raw_user == (correct_answer or '').strip().lower()
    if not user:                      # 빈 입력(공백·물결표만 입력)은 항상 오답
        return False
    return user == correct


def pick_distractors(candidates, correct: str, count: int = 3) -> list:
    """보기용 오답을 고른다. 채점 기준(normalize_answer)으로 정답과 같은 후보와, 서로 같은 후보는 뺀다.
    (뜻이 같은 동의어나 띄어쓰기만 다른 영단어를 보기에 넣으면 '정답이 둘'이 되어 버린다.)"""
    def key_of(text: str) -> str:
        return normalize_answer(text) or (text or '').strip().lower()

    seen = {key_of(correct)}
    shuffled = list(candidates)
    random.shuffle(shuffled)
    picked = []
    for candidate in shuffled:
        key = key_of(candidate)
        if key in seen:
            continue
        seen.add(key)
        picked.append(candidate)
        if len(picked) == count:
            break
    return picked


class TestError(Exception):
    """사용자에게 보여줘도 되는 시험 오류"""


class TestEngine:
    """시험 출제·채점. 상태는 서버 메모리가 아니라 test_sessions 테이블에 둔다."""

    __test__ = False  # pytest 가 클래스 이름 때문에 테스트로 오인하지 않도록 한다

    def __init__(self, db: Database, word_manager: WordManager, game: GamificationManager):
        self.db = db
        self.word_manager = word_manager
        self.game = game

    # ---------- 세션 저장/로드 ----------
    def _load(self, user_id: int) -> Optional[Dict]:
        row = self.db.query_one("SELECT state_json FROM test_sessions WHERE user_id = ?", (user_id,))
        return json.loads(row['state_json']) if row else None

    def _save(self, user_id: int, state: Dict) -> None:
        self.db.execute(
            "INSERT INTO test_sessions(user_id, state_json) VALUES(?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET state_json = excluded.state_json, "
            "updated_at = datetime('now', 'localtime')",
            (user_id, json.dumps(state, ensure_ascii=False)),
        )

    # ---------- 시험 시작 ----------
    def start_test(self, user_id: int, config: Dict) -> Dict:
        mode = config.get('mode', '혼합')
        fmt = config.get('format', '혼합')
        scope = config.get('scope', DEFAULT_SCOPE)
        if mode not in MODES or fmt not in FORMATS:
            raise TestError('올바르지 않은 시험 설정입니다.')
        if scope not in SCOPES:
            raise TestError('올바르지 않은 출제 범위입니다.')
        try:
            num = int(config.get('num_problems', 10))
        except (TypeError, ValueError):
            raise TestError('문제 수는 숫자여야 합니다.')
        max_num = int(self.db.get_setting('max_test_problems', '50'))
        num = max(1, min(num, max_num))

        total_words = self.word_manager.count()
        if total_words == 0:
            raise TestError('등록된 단어가 없습니다. 관리자에게 단어 등록을 요청하세요.')
        if fmt in ('4지선다형', '빈칸형', '혼합') and total_words < MIN_WORDS_FOR_CHOICE:
            fmt = 'OX형' if total_words >= 2 else '단답형'  # 단어가 부족하면 가능한 형식으로 낮춘다

        words = self._pick_words(user_id, scope, num)
        if not words:
            raise TestError(SCOPE_EMPTY_MESSAGE[scope])   # (scope 'all' 은 위에서 단어 0개를 이미 걸렀다)
        pool = self.db.query("SELECT id, english, korean FROM words")  # 보기·오답 후보는 범위와 상관없이 전체 단어
        problems = [self._make_problem(w, mode, fmt, pool) for w in words]
        random.shuffle(problems)

        state = {'config': {'num_problems': len(problems), 'mode': mode, 'format': fmt, 'scope': scope},
                 'problems': problems, 'index': 0, 'results': [],
                 'started_at': datetime.now().isoformat()}
        self._save(user_id, state)
        # requested/short: 범위 안 단어가 요청한 문제 수보다 적으면 있는 만큼만 출제했다는 뜻 (화면에서 안내)
        return {'total': len(problems), 'requested': num, 'short': len(problems) < num, 'config': state['config']}

    def _pick_words(self, user_id: int, scope: str, num: int) -> list:
        """출제 범위 안에서 문제로 낼 단어를 고른다. ①②는 오답이 많은(weight 높은) 단어를 우선하고 나머지는 무작위,
        ③ 전체 단어는 weight 와 상관없이 무작위."""
        columns = "w.id, w.english, w.korean, w.example"
        if scope == 'today':
            today = datetime.now().strftime('%Y-%m-%d')
            return self.db.query(
                f"""SELECT {columns} FROM words w JOIN user_word_stats s ON s.word_id = w.id
                    WHERE s.user_id = ? AND s.last_studied = ?
                    ORDER BY s.weight DESC, RANDOM() LIMIT ?""", (user_id, today, num))
        if scope == 'studied':
            return self.db.query(
                f"""SELECT {columns} FROM words w JOIN user_word_stats s ON s.word_id = w.id
                    WHERE s.user_id = ? AND s.success_count + s.fail_count > 0
                    ORDER BY s.weight DESC, RANDOM() LIMIT ?""", (user_id, num))
        # ③ 전체 단어: 학습 기록과 상관없이 순수 무작위 (틀린 단어 우선은 ①②에서만 적용한다)
        return self.db.query(f"SELECT {columns} FROM words w ORDER BY RANDOM() LIMIT ?", (num,))

    def scope_counts(self, user_id: int) -> Dict:
        """범위별 단어 수 (시험 시작 화면에 보여준다)."""
        today = datetime.now().strftime('%Y-%m-%d')
        return {
            'today': self.db.scalar(
                "SELECT COUNT(*) FROM user_word_stats WHERE user_id = ? AND last_studied = ?", (user_id, today)),
            'studied': self.db.scalar(
                "SELECT COUNT(*) FROM user_word_stats WHERE user_id = ? AND success_count + fail_count > 0", (user_id,)),
            'all': self.word_manager.count(),
        }

    def _make_problem(self, word: Dict, mode: str, fmt: str, pool: list) -> Dict:
        p_mode = random.choice(['한->영', '영->한']) if mode == '혼합' else mode
        p_fmt = random.choice(['단답형', '4지선다형', 'OX형', '빈칸형']) if fmt == '혼합' else fmt
        if p_fmt == '빈칸형':
            sentence = self._blank_sentence(word)
            if sentence and len(pool) >= MIN_WORDS_FOR_CHOICE:
                others = [w['english'] for w in pool if w['id'] != word['id']]
                options = pick_distractors(others, word['english']) + [word['english']]
                random.shuffle(options)
                return {'word_id': word['id'], 'mode': '빈칸', 'format': '빈칸형', 'prompt': sentence,
                        'question': sentence, 'hint': word['korean'], 'correct_answer': word['english'], 'options': options}
            p_fmt = '4지선다형'  # 예문이 없거나 단어가 예문에 그대로 나오지 않으면 일반 4지선다로 대체
        if p_fmt == '4지선다형' and len(pool) < MIN_WORDS_FOR_CHOICE:
            p_fmt = 'OX형'
        if p_fmt == 'OX형' and len(pool) < 2:
            p_fmt = '단답형'

        ask, answer = (word['korean'], word['english']) if p_mode == '한->영' else (word['english'], word['korean'])
        key = 'english' if p_mode == '한->영' else 'korean'
        others = [w[key] for w in pool if w['id'] != word['id']]   # 정답과 같은 뜻/영어는 아래에서 pick_distractors 가 뺀다
        problem = {'word_id': word['id'], 'mode': p_mode, 'format': p_fmt,
                   'prompt': ask, 'correct_answer': answer, 'options': None}

        if p_fmt == '4지선다형':
            options = pick_distractors(others, answer) + [answer]
            random.shuffle(options)
            problem['options'] = options
            problem['question'] = f"'{ask}'" + ("의 영문은?" if p_mode == '한->영' else "의 뜻은?")
        elif p_fmt == 'OX형':
            # 절반은 맞는 짝, 절반은 틀린 짝을 보여주고 O/X 를 고르게 한다
            shown, truth = (answer, True)
            wrong = pick_distractors(others, answer, 1)   # 정답과 같은 뜻이면 'X' 가 오답 처리되므로 제외
            if wrong and random.random() < 0.5:
                shown, truth = wrong[0], False
            problem['shown'] = shown
            problem['correct_answer'] = 'O' if truth else 'X'
            problem['options'] = ['O', 'X']
            problem['question'] = f"'{ask}' = '{shown}' 이(가) 맞습니까?"
        else:
            problem['question'] = f"'{ask}'" + ("의 영문은?" if p_mode == '한->영' else "의 뜻은?")
        return problem

    @staticmethod
    def _blank_sentence(word: Dict) -> Optional[str]:
        """예문에서 단어(철자 그대로)를 ____ 로 가린다. 활용형(attempted 등)이라 찾지 못하면 None."""
        example = (word.get('example') or '').strip()
        if not example:
            return None
        match = re.search(r'\b' + re.escape(word['english']) + r'\b', example, re.IGNORECASE)
        return example[:match.start()] + '_____' + example[match.end():] if match else None

    # ---------- 진행/채점 ----------
    def get_current_problem(self, user_id: int) -> Dict:
        state = self._load(user_id)
        if not state:
            raise TestError('진행 중인 시험이 없습니다.')
        idx = state['index']
        if idx >= len(state['problems']):
            return {'finished': True, 'total': len(state['problems'])}
        p = state['problems'][idx]
        # 정답은 클라이언트에 보내지 않는다
        return {'finished': False, 'index': idx + 1, 'total': len(state['problems']),
                'question': p['question'], 'format': p['format'], 'mode': p['mode'], 'options': p['options'],
                'hint': p.get('hint')}

    def grade_answer(self, user_id: int, answer: str) -> Dict:
        state = self._load(user_id)
        if not state:
            raise TestError('진행 중인 시험이 없습니다.')
        idx = state['index']
        if idx >= len(state['problems']):
            raise TestError('이미 모든 문제를 풀었습니다.')
        p = state['problems'][idx]
        user_answer = (answer or '').strip()
        is_correct = is_same_answer(user_answer, p['correct_answer'])   # 띄어쓰기·괄호·~ 는 무시
        synonym = None
        if not is_correct and p.get('mode') == '한->영' and p.get('format') == '단답형':
            # 한→영 단답: 뜻이 같은 다른 단어(동의어)를 쓰면 정답으로 인정한다 (예: '명백한' -> evident / obvious)
            synonym = self._same_meaning_word(user_answer, p['prompt'])
            is_correct = synonym is not None
        state['results'].append({'word_id': p['word_id'], 'question': p['question'],
                                 'user_answer': user_answer, 'correct_answer': p['correct_answer'],
                                 'is_correct': is_correct, 'synonym': synonym})
        state['index'] = idx + 1
        self._save(user_id, state)
        # synonym 이 있으면 정답 처리됐지만 출제 단어(correct_answer)와 다른 단어를 쓴 것이다
        return {'is_correct': is_correct, 'correct_answer': p['correct_answer'], 'synonym': synonym,
                'finished': state['index'] >= len(state['problems'])}

    def _same_meaning_word(self, typed: str, meaning: str) -> Optional[str]:
        """사용자가 입력한 영단어가 DB 에 있고 그 뜻이 meaning 과 normalize 기준으로 같으면 그 단어를 돌려준다.
        (공백·대소문자는 무시하고 찾는다. 사전에 없는 글자나 뜻이 다른 단어는 None)"""
        key = normalize_answer(typed)
        if not key:
            return None
        meaning_key = normalize_answer(meaning)
        for word in self.db.query("SELECT english, korean FROM words WHERE LOWER(REPLACE(english, ' ', '')) = ?", (key,)):
            if normalize_answer(word['korean']) == meaning_key:
                return word['english']
        return None

    def finish_test(self, user_id: int) -> Dict:
        """시험 종료: 결과 저장 + 단어 통계 반영 후 세션 삭제"""
        state = self._load(user_id)
        if not state:
            raise TestError('진행 중인 시험이 없습니다.')
        results = state['results']
        total = len(results)
        if total == 0:
            raise TestError('풀이한 문제가 없습니다.')
        correct = sum(1 for r in results if r['is_correct'])
        score = round(correct / total * 100, 1)
        today = datetime.now().strftime('%Y-%m-%d')
        cfg = state['config']
        xp_before = self.game.user_xp(user_id)
        with self.db.session() as conn:
            conn.execute(
                "INSERT INTO test_logs(user_id, date, mode, format, total_problems, correct_answers, score) "
                "VALUES(?,?,?,?,?,?,?)", (user_id, today, cfg['mode'], cfg['format'], total, correct, score))
            for r in results:
                self.word_manager.update_user_stat(conn, user_id, r['word_id'], r['is_correct'], today)
            conn.execute("DELETE FROM test_sessions WHERE user_id = ?", (user_id,))
        gained = quiz_xp(correct, total)
        info = level_info(xp_before + gained)
        return {'total_problems': total, 'correct_answers': correct, 'score': score, 'details': results,
                'xp_gained': gained, 'xp': info['xp'], 'level': info['level'],
                'level_up': info['level'] > level_info(xp_before)['level']}
