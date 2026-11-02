#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - 게임화 (XP·레벨 계산, 주간 리그 순위)
# 파일 위치: src/business/gamification.py

import math
from datetime import datetime, timedelta
from typing import Dict, List
from src.data.database import Database

# XP 규칙: 맞히면 크게, 틀려도 '참여'했으니 조금 준다 (포기하지 않게 하는 장치)
STUDY_CORRECT_XP, STUDY_WRONG_XP = 10, 2
TEST_CORRECT_XP, TEST_WRONG_XP = 15, 3
LEAGUE_SIZE = 20


def study_xp(correct: int, total: int) -> int:
    return correct * STUDY_CORRECT_XP + (total - correct) * STUDY_WRONG_XP


def quiz_xp(correct: int, total: int) -> int:
    return correct * TEST_CORRECT_XP + (total - correct) * TEST_WRONG_XP



def level_info(xp: int) -> Dict:
    """레벨 n 에 도달하는 누적 XP = 50·(n-1)·n  (L2=100, L3=300, L4=600 …). 레벨이 오를수록 필요 XP 가 늘어난다."""
    level = int((1 + math.sqrt(1 + xp * 0.08)) / 2)
    base, nxt = 50 * (level - 1) * level, 50 * level * (level + 1)
    return {'xp': xp, 'level': level, 'level_xp': xp - base, 'level_need': nxt - base,
            'level_percent': round((xp - base) / (nxt - base) * 100)}


class GamificationManager:
    def __init__(self, db: Database):
        self.db = db

    def user_xp(self, user_id: int) -> int:
        study = self.db.scalar(
            "SELECT SUM(correct_count * ? + (words_count - correct_count) * ?) FROM study_logs WHERE user_id = ?",
            (STUDY_CORRECT_XP, STUDY_WRONG_XP, user_id))
        tests = self.db.scalar(
            "SELECT SUM(correct_answers * ? + (total_problems - correct_answers) * ?) FROM test_logs WHERE user_id = ?",
            (TEST_CORRECT_XP, TEST_WRONG_XP, user_id))
        return int(study) + int(tests)

    def user_level(self, user_id: int) -> Dict:
        return level_info(self.user_xp(user_id))

    def weekly_league(self, user_id: int) -> Dict:
        """최근 7일 획득 XP 순위. 관리자·비활성 계정은 제외한다."""
        since = (datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d')
        rows = self.db.query(
            """SELECT u.id, u.display_name AS name,
                      COALESCE(s.xp, 0) + COALESCE(t.xp, 0) AS xp
               FROM users u
               LEFT JOIN (SELECT user_id, SUM(correct_count * ? + (words_count - correct_count) * ?) AS xp
                          FROM study_logs WHERE date >= ? GROUP BY user_id) s ON s.user_id = u.id
               LEFT JOIN (SELECT user_id, SUM(correct_answers * ? + (total_problems - correct_answers) * ?) AS xp
                          FROM test_logs WHERE date >= ? GROUP BY user_id) t ON t.user_id = u.id
               WHERE u.role = 'user' AND u.active = 1
               ORDER BY xp DESC, u.display_name""",
            (STUDY_CORRECT_XP, STUDY_WRONG_XP, since, TEST_CORRECT_XP, TEST_WRONG_XP, since))
        board: List[Dict] = []
        my_rank = None
        for rank, r in enumerate(rows, start=1):
            me = r['id'] == user_id
            if me:
                my_rank = rank
            if rank <= LEAGUE_SIZE or me:
                board.append({'rank': rank, 'name': r['name'], 'xp': int(r['xp']), 'me': me})
        return {'board': board, 'my_rank': my_rank, 'total': len(rows), 'since': since}
