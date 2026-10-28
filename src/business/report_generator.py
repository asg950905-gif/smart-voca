#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-28 - smart-voca - 보고서 생성
# 파일 위치: src/business/report_generator.py

from typing import Dict, List
from datetime import datetime, timedelta
import logging
import csv
from io import StringIO
from src.data.file_manager import FileManager

logger = logging.getLogger(__name__)


class ReportGenerator:
    """학습 통계 및 보고서"""

    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager

    def calculate_statistics(self) -> Dict:
        """통계 계산"""
        try:
            study_logs = self.file_manager.read_csv('study_log.csv')
            test_logs = self.file_manager.read_csv('test_log.csv')
            progress = self.file_manager.read_json('progress.json')

            # 기본값
            stats = {
                'total_study_days': len(study_logs),
                'total_test_attempts': len(test_logs),
                'average_study_success_rate': 0,
                'average_test_score': 0,
                'today_studied': False,
                'today_success_rate': 0,
                'today_test_score': 0
            }

            if study_logs:
                success_rates = [float(log.get('success_rate', 0)) for log in study_logs]
                stats['average_study_success_rate'] = sum(success_rates) / len(success_rates)

            if test_logs:
                scores = [float(log.get('score', 0)) for log in test_logs]
                stats['average_test_score'] = sum(scores) / len(scores)

            # 오늘 통계
            today = datetime.now().strftime('%Y-%m-%d')
            today_study = [log for log in study_logs if log.get('date') == today]
            today_test = [log for log in test_logs if log.get('date') == today]

            if today_study:
                stats['today_studied'] = True
                stats['today_success_rate'] = float(today_study[0].get('success_rate', 0))

            if today_test:
                stats['today_test_score'] = float(today_test[0].get('score', 0))

            # 진도
            if progress:
                stats['current_day'] = progress.get('current_day', 1)
                stats['total_days'] = progress.get('total_days', 200)
                stats['completion_rate'] = (stats['current_day'] / stats['total_days'] * 100)

            return stats

        except Exception as e:
            logger.error(f"통계 계산 실패: {e}")
            return {}

    def get_chart_data(self) -> Dict:
        """Chart.js용 차트 데이터"""
        try:
            study_logs = self.file_manager.read_csv('study_log.csv')
            test_logs = self.file_manager.read_csv('test_log.csv')

            # 최근 7일 데이터
            today = datetime.now()
            seven_days_ago = (today - timedelta(days=7)).strftime('%Y-%m-%d')

            recent_logs = [log for log in study_logs if log.get('date', '') >= seven_days_ago]
            recent_tests = [log for log in test_logs if log.get('date', '') >= seven_days_ago]

            return {
                'study_trend': self._get_study_trend_data(recent_logs),
                'test_scores': self._get_test_score_data(recent_tests),
                'weak_words': self._get_weak_words_data()
            }

        except Exception as e:
            logger.error(f"차트 데이터 생성 실패: {e}")
            return {}

    def _get_study_trend_data(self, logs: List[Dict]) -> Dict:
        """학습 추이 데이터"""
        labels = []
        data = []

        for log in sorted(logs, key=lambda x: x.get('date', '')):
            labels.append(log.get('date', ''))
            data.append(float(log.get('success_rate', 0)))

        return {
            'labels': labels,
            'datasets': [{
                'label': '성공률 (%)',
                'data': data,
                'borderColor': 'rgb(75, 192, 192)',
                'tension': 0.1
            }]
        }

    def _get_test_score_data(self, logs: List[Dict]) -> Dict:
        """시험 성적 데이터"""
        labels = []
        data = []

        for log in sorted(logs, key=lambda x: x.get('date', '')):
            labels.append(log.get('date', ''))
            data.append(float(log.get('score', 0)))

        return {
            'labels': labels,
            'datasets': [{
                'label': '시험 점수',
                'data': data,
                'backgroundColor': 'rgba(54, 162, 235, 0.5)',
                'borderColor': 'rgb(54, 162, 235)'
            }]
        }

    def _get_weak_words_data(self) -> Dict:
        """약점 단어 데이터"""
        return {
            'labels': ['word1', 'word2', 'word3'],
            'datasets': [{
                'label': '오류 횟수',
                'data': [5, 4, 3],
                'backgroundColor': 'rgba(255, 99, 132, 0.5)'
            }]
        }

    def export_csv(self) -> StringIO:
        """CSV 내보내기"""
        try:
            stats = self.calculate_statistics()

            output = StringIO()
            writer = csv.writer(output)

            writer.writerow(['항목', '값'])
            writer.writerow(['학습 일수', stats.get('total_study_days', 0)])
            writer.writerow(['시험 응시 횟수', stats.get('total_test_attempts', 0)])
            writer.writerow(['평균 성공률', f"{stats.get('average_study_success_rate', 0):.1f}%"])
            writer.writerow(['평균 시험 점수', f"{stats.get('average_test_score', 0):.1f}점"])
            writer.writerow(['진도', f"{stats.get('current_day', 1)}/{stats.get('total_days', 200)}"])
            writer.writerow(['완료율', f"{stats.get('completion_rate', 0):.1f}%"])

            output.seek(0)
            return output

        except Exception as e:
            logger.error(f"CSV 내보내기 실패: {e}")
            return StringIO()
