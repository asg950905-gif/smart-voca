#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - 학습 관리 (사용자별 오늘의 단어·학습 기록·진도)
# 파일 위치: src/business/study_manager.py

import logging
from datetime import datetime
from typing import Dict, List
from src.data.database import Database
from src.business.word_manager import WordManager
from src.business.gamification import GamificationManager, level_info, study_xp

logger = logging.getLogger(__name__)

DEFAULT_TOTAL_DAYS = 200


class StudyManager:
    """사용자별 학습 진행 관리"""

    def __init__(self, db: Database, word_manager: WordManager, game: GamificationManager):
        self.db = db
        self.word_manager = word_manager
        self.game = game

    def get_daily_words(self, user_id: int) -> List[Dict]:
        """오늘 학습할 단어. 오답이 많은 단어 → 아직 안 본 단어 → 오래전에 본 단어 순으로 고른다."""
        target = self.db.scalar("SELECT daily_target FROM users WHERE id = ?", (user_id,), default=10)
        return self.db.query(
            """SELECT w.id, w.english, w.korean, w.part_of_speech, w.example,
                      COALESCE(s.weight, 0) AS weight
               FROM words w
               LEFT JOIN user_word_stats s ON s.word_id = w.id AND s.user_id = ?
               ORDER BY COALESCE(s.weight, 0) DESC,
                        (s.last_studied IS NOT NULL),
                        s.last_studied ASC,
                        RANDOM()
               LIMIT ?""",
            (user_id, target),
        )

    def record_study(self, user_id: int, results: List[Dict]) -> Dict:
        """학습 결과 저장. results: [{'word_id': 1, 'is_correct': True}, ...]"""
        today = datetime.now().strftime('%Y-%m-%d')
        valid_ids = {r['id'] for r in self.db.query("SELECT id FROM words")}
        cleaned = [r for r in results if isinstance(r, dict) and r.get('word_id') in valid_ids]
        if not cleaned:
            return {'words_count': 0, 'correct_count': 0, 'success_rate': 0, 'xp_gained': 0, 'level_up': False}

        correct = sum(1 for r in cleaned if r.get('is_correct'))
        total = len(cleaned)
        rate = round(correct / total * 100, 1)
        xp_before = self.game.user_xp(user_id)
        with self.db.session() as conn:  # 단어 통계와 로그를 한 트랜잭션으로 묶는다
            for r in cleaned:
                self.word_manager.update_user_stat(conn, user_id, r['word_id'], bool(r.get('is_correct')), today)
            conn.execute(
                "INSERT INTO study_logs(user_id, date, words_count, correct_count, success_rate) VALUES(?,?,?,?,?)",
                (user_id, today, total, correct, rate),
            )
        gained = study_xp(correct, total)
        info = level_info(xp_before + gained)
        logger.info(f"학습 기록: user={user_id} {correct}/{total} +{gained}XP")
        return {'words_count': total, 'correct_count': correct, 'success_rate': rate, 'xp_gained': gained,
                'level_up': info['level'] > level_info(xp_before)['level'], **{k: info[k] for k in ('xp', 'level')}}

    def get_progress_info(self, user_id: int) -> Dict:
        """진도: 학습한 날 수(서로 다른 날짜)를 기준으로 계산"""
        total_days = int(self.db.get_setting('total_days', str(DEFAULT_TOTAL_DAYS)))
        studied_days = self.db.scalar("SELECT COUNT(DISTINCT date) FROM study_logs WHERE user_id = ?", (user_id,))
        total_words = self.word_manager.count()
        learned = self.db.scalar(
            "SELECT COUNT(*) FROM user_word_stats WHERE user_id = ? AND success_count > 0", (user_id,))
        mastered = self.db.scalar(
            """SELECT COUNT(*) FROM user_word_stats WHERE user_id = ?
               AND success_count + fail_count >= 3 AND success_count * 1.0 / (success_count + fail_count) >= 0.8""",
            (user_id,))
        today = datetime.now().strftime('%Y-%m-%d')
        today_log = self.db.query_one(
            "SELECT words_count, correct_count, success_rate FROM study_logs "
            "WHERE user_id = ? AND date = ? ORDER BY id DESC LIMIT 1", (user_id, today))
        return {
            'studied_days': studied_days,
            'total_days': total_days,
            'completion_rate': round(min(100.0, studied_days / total_days * 100), 1) if total_days else 0,
            'streak': self._streak(user_id),
            **self.game.user_level(user_id),
            'total_words': total_words,
            'learned_words': learned,
            'mastered_words': mastered,
            'daily_target': self.db.scalar("SELECT daily_target FROM users WHERE id = ?", (user_id,), default=10),
            'today': today_log,
            'studied_today': today_log is not None,
        }

    def _streak(self, user_id: int) -> int:
        """오늘(또는 어제)부터 거꾸로 이어진 연속 학습일 수"""
        from datetime import timedelta
        dates = {r['date'] for r in self.db.query(
            "SELECT DISTINCT date FROM study_logs WHERE user_id = ?", (user_id,))}
        day = datetime.now().date()
        if day.strftime('%Y-%m-%d') not in dates:
            day -= timedelta(days=1)  # 오늘 아직 안 했어도 어제까지의 연속 기록은 유지
        streak = 0
        while day.strftime('%Y-%m-%d') in dates:
            streak += 1
            day -= timedelta(days=1)
        return streak

    def reset_user_progress(self, user_id: int) -> None:
        """사용자 본인의 학습 기록 초기화"""
        with self.db.session() as conn:
            for table in ('user_word_stats', 'study_logs', 'test_logs', 'test_sessions'):
                conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
