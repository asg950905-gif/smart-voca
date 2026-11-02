#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - 통계·보고서 (사용자 개인 통계 + 관리자 전체 통계)
# 파일 위치: src/business/report_generator.py

import csv
import logging
from datetime import datetime, timedelta
from io import StringIO
from typing import Dict
from src.data.database import Database

logger = logging.getLogger(__name__)


def _days_ago(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')


class ReportGenerator:
    """학습 통계 집계"""

    def __init__(self, db: Database):
        self.db = db

    # ---------- 사용자 개인 ----------
    def user_statistics(self, user_id: int) -> Dict:
        today = datetime.now().strftime('%Y-%m-%d')
        study = self.db.query_one(
            "SELECT COUNT(DISTINCT date) AS days, ROUND(AVG(success_rate), 1) AS avg_rate, "
            "COALESCE(SUM(words_count), 0) AS words FROM study_logs WHERE user_id = ?", (user_id,))
        test = self.db.query_one(
            "SELECT COUNT(*) AS attempts, ROUND(AVG(score), 1) AS avg_score, MAX(score) AS best "
            "FROM test_logs WHERE user_id = ?", (user_id,))
        return {
            'total_study_days': study['days'],
            'total_words_studied': study['words'],
            'average_study_success_rate': study['avg_rate'] or 0,
            'total_test_attempts': test['attempts'],
            'average_test_score': test['avg_score'] or 0,
            'best_test_score': test['best'] or 0,
            'today_studied': bool(self.db.scalar(
                "SELECT COUNT(*) FROM study_logs WHERE user_id = ? AND date = ?", (user_id, today))),
        }

    def user_charts(self, user_id: int, days: int = 14) -> Dict:
        since = _days_ago(days - 1)
        study = self.db.query(
            "SELECT date, ROUND(AVG(success_rate), 1) AS rate, SUM(words_count) AS words "
            "FROM study_logs WHERE user_id = ? AND date >= ? GROUP BY date ORDER BY date", (user_id, since))
        tests = self.db.query(
            "SELECT date, ROUND(AVG(score), 1) AS score FROM test_logs "
            "WHERE user_id = ? AND date >= ? GROUP BY date ORDER BY date", (user_id, since))
        weak = self.db.query(
            """SELECT w.english AS label, s.fail_count AS value FROM user_word_stats s
               JOIN words w ON w.id = s.word_id WHERE s.user_id = ? AND s.fail_count > 0
               ORDER BY s.fail_count DESC, w.english LIMIT 8""", (user_id,))
        return {
            'study_trend': {'labels': [r['date'][5:] for r in study], 'rates': [r['rate'] for r in study],
                            'words': [r['words'] for r in study]},
            'test_scores': {'labels': [r['date'][5:] for r in tests], 'scores': [r['score'] for r in tests]},
            'weak_words': {'labels': [r['label'] for r in weak], 'values': [r['value'] for r in weak]},
        }

    def export_user_csv(self, user_id: int) -> StringIO:
        stats = self.user_statistics(user_id)
        out = StringIO()
        out.write('﻿')
        writer = csv.writer(out)
        writer.writerow(['항목', '값'])
        writer.writerow(['학습 일수', stats['total_study_days']])
        writer.writerow(['학습한 단어 수(누적)', stats['total_words_studied']])
        writer.writerow(['평균 학습 성공률', f"{stats['average_study_success_rate']}%"])
        writer.writerow(['시험 응시 횟수', stats['total_test_attempts']])
        writer.writerow(['평균 시험 점수', f"{stats['average_test_score']}점"])
        writer.writerow(['최고 시험 점수', f"{stats['best_test_score']}점"])
        out.seek(0)
        return out

    # ---------- 관리자 전체 ----------
    def admin_overview(self) -> Dict:
        today = datetime.now().strftime('%Y-%m-%d')
        week_ago = _days_ago(6)
        return {
            'total_users': self.db.scalar("SELECT COUNT(*) FROM users WHERE role = 'user'"),
            'active_today': self.db.scalar("SELECT COUNT(DISTINCT user_id) FROM study_logs WHERE date = ?", (today,)),
            'active_week': self.db.scalar(
                "SELECT COUNT(DISTINCT user_id) FROM study_logs WHERE date >= ?", (week_ago,)),
            'total_words': self.db.scalar("SELECT COUNT(*) FROM words"),
            'total_tests': self.db.scalar("SELECT COUNT(*) FROM test_logs"),
            'avg_test_score': self.db.scalar("SELECT ROUND(AVG(score), 1) FROM test_logs"),
            'avg_study_rate': self.db.scalar("SELECT ROUND(AVG(success_rate), 1) FROM study_logs"),
        }

    def admin_charts(self, days: int = 14) -> Dict:
        since = _days_ago(days - 1)
        daily = self.db.query(
            "SELECT date, COUNT(DISTINCT user_id) AS users, SUM(words_count) AS words "
            "FROM study_logs WHERE date >= ? GROUP BY date ORDER BY date", (since,))
        scores = self.db.query(
            "SELECT date, ROUND(AVG(score), 1) AS score FROM test_logs WHERE date >= ? GROUP BY date ORDER BY date",
            (since,))
        hard = self.db.query(
            """SELECT w.english AS label, SUM(s.fail_count) AS fails, SUM(s.success_count) AS oks
               FROM user_word_stats s JOIN words w ON w.id = s.word_id
               GROUP BY w.id HAVING fails > 0 ORDER BY fails DESC, w.english LIMIT 10""")
        ranking = self.db.query(
            """SELECT u.display_name AS name, COUNT(DISTINCT s.date) AS days, COALESCE(SUM(s.words_count), 0) AS words
               FROM users u LEFT JOIN study_logs s ON s.user_id = u.id
               WHERE u.role = 'user' GROUP BY u.id ORDER BY words DESC, days DESC LIMIT 5""")
        return {
            'daily_activity': {'labels': [r['date'][5:] for r in daily], 'users': [r['users'] for r in daily],
                               'words': [r['words'] for r in daily]},
            'test_scores': {'labels': [r['date'][5:] for r in scores], 'scores': [r['score'] for r in scores]},
            'hard_words': {'labels': [r['label'] for r in hard], 'values': [r['fails'] for r in hard]},
            'ranking': ranking,
        }
