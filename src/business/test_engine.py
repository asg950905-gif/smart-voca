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
        if mode not in MODES or fmt not in FORMATS:
            raise TestError('올바르지 않은 시험 설정입니다.')
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

        # 오답이 많은 단어를 우선 출제한다
        words = self.db.query(
            """SELECT w.id, w.english, w.korean, w.example FROM words w
               LEFT JOIN user_word_stats s ON s.word_id = w.id AND s.user_id = ?
               ORDER BY COALESCE(s.weight, 0) DESC, RANDOM() LIMIT ?""",
            (user_id, num),
        )
        pool = self.db.query("SELECT id, english, korean FROM words")  # 보기·오답 후보
        problems = [self._make_problem(w, mode, fmt, pool) for w in words]
        random.shuffle(problems)

        state = {'config': {'num_problems': len(problems), 'mode': mode, 'format': fmt},
                 'problems': problems, 'index': 0, 'results': [],
                 'started_at': datetime.now().isoformat()}
        self._save(user_id, state)
        return {'total': len(problems), 'config': state['config']}

    def _make_problem(self, word: Dict, mode: str, fmt: str, pool: list) -> Dict:
        p_mode = random.choice(['한->영', '영->한']) if mode == '혼합' else mode
        p_fmt = random.choice(['단답형', '4지선다형', 'OX형', '빈칸형']) if fmt == '혼합' else fmt
        if p_fmt == '빈칸형':
            sentence = self._blank_sentence(word)
            if sentence and len(pool) >= MIN_WORDS_FOR_CHOICE:
                others = [w['english'] for w in pool if w['id'] != word['id'] and w['english'].lower() != word['english'].lower()]
                options = random.sample(others, min(3, len(others))) + [word['english']]
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
        others = [w[key] for w in pool if w['id'] != word['id'] and w[key] != answer]
        problem = {'word_id': word['id'], 'mode': p_mode, 'format': p_fmt,
                   'prompt': ask, 'correct_answer': answer, 'options': None}

        if p_fmt == '4지선다형':
            options = random.sample(others, min(3, len(others))) + [answer]
            random.shuffle(options)
            problem['options'] = options
            problem['question'] = f"'{ask}'" + ("의 영문은?" if p_mode == '한->영' else "의 뜻은?")
        elif p_fmt == 'OX형':
            # 절반은 맞는 짝, 절반은 틀린 짝을 보여주고 O/X 를 고르게 한다
            shown, truth = (answer, True)
            if others and random.random() < 0.5:
                shown, truth = random.choice(others), False
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
        state['results'].append({'word_id': p['word_id'], 'question': p['question'],
                                 'user_answer': user_answer, 'correct_answer': p['correct_answer'],
                                 'is_correct': is_correct})
        state['index'] = idx + 1
        self._save(user_id, state)
        return {'is_correct': is_correct, 'correct_answer': p['correct_answer'],
                'finished': state['index'] >= len(state['problems'])}

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
