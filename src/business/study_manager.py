#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-28 - smart-voca - 학습 관리
# 파일 위치: src/business/study_manager.py

from typing import List, Dict, Optional
from datetime import datetime
import logging
from src.data.models import Word, Progress, StudyLog
from src.data.file_manager import FileManager
from src.business.word_manager import WordManager

logger = logging.getLogger(__name__)


class StudyManager:
    """학습 진도 및 암기 관리"""

    def __init__(self, word_manager: WordManager, file_manager: FileManager):
        self.word_manager = word_manager
        self.file_manager = file_manager
        self.progress = self.load_progress()
        self.today_results = []  # 오늘의 학습 결과

    def load_progress(self) -> Progress:
        """진도 정보 로드"""
        try:
            data = self.file_manager.read_json('progress.json')
            if data:
                return Progress(**data)
        except Exception as e:
            logger.warning(f"진도 로드 실패: {e}")

        # 기본값
        return Progress(
            current_day=1,
            total_days=200,
            daily_target=10,
            created_date=datetime.now().strftime('%Y-%m-%d')
        )

    def save_progress(self) -> bool:
        """진도 정보 저장"""
        try:
            return self.file_manager.write_json('progress.json', self.progress.to_dict())
        except Exception as e:
            logger.error(f"진도 저장 실패: {e}")
            return False

    def get_daily_words(self) -> List[Word]:
        """오늘의 학습 단어 가져오기"""
        all_words = self.word_manager.get_all_words()

        if not all_words:
            logger.warning("로드된 단어가 없습니다")
            return []

        # 진도에 따라 단어 선택
        target_count = self.progress.daily_target

        # 가중치 기반으로 선택 (복습 필요한 단어 우선)
        words = self.word_manager.get_words_by_weight(target_count)

        if len(words) < target_count:
            # 부족하면 랜덤 단어로 채우기
            remaining = target_count - len(words)
            extra = self.word_manager.get_random_words(remaining)
            words.extend([w for w in extra if w not in words])

        self.today_results = []
        return words[:target_count]

    def record_study(self, results: List[Dict]) -> bool:
        """학습 결과 저장

        results: [
            {'word_id': 1, 'is_correct': True},
            ...
        ]
        """
        try:
            correct_count = 0

            for result in results:
                word_id = result.get('word_id')
                is_correct = result.get('is_correct', False)

                # 단어 정보 업데이트
                self.word_manager.update_word(word_id, is_correct)

                if is_correct:
                    correct_count += 1

            # 단어 저장
            self.word_manager.save_words()

            # 학습 로그 기록
            total = len(results)
            success_rate = (correct_count / total * 100) if total > 0 else 0

            study_log = StudyLog(
                date=datetime.now().strftime('%Y-%m-%d'),
                day=self.progress.current_day,
                words_count=total,
                correct_count=correct_count,
                success_rate=success_rate
            )

            self.file_manager.append_csv('study_log.csv', study_log.to_dict())

            # 진도 업데이트
            self.progress.current_day += 1
            self.progress.last_studied_date = datetime.now().strftime('%Y-%m-%d')
            self.save_progress()

            logger.info(f"학습 기록 저장: {correct_count}/{total} ({success_rate:.1f}%)")
            return True

        except Exception as e:
            logger.error(f"학습 기록 저장 실패: {e}")
            return False

    def get_progress_info(self) -> Dict:
        """진도 정보 반환"""
        try:
            completion_rate = self.progress.get_completion_rate()

            return {
                'current_day': self.progress.current_day,
                'total_days': self.progress.total_days,
                'completion_rate': completion_rate,
                'daily_target': self.progress.daily_target,
                'last_studied_date': self.progress.last_studied_date,
                'status': 'completed' if self.progress.current_day > self.progress.total_days else 'in_progress'
            }
        except Exception as e:
            logger.error(f"진도 정보 조회 실패: {e}")
            return {}

    def get_today_statistics(self) -> Dict:
        """오늘의 학습 통계"""
        try:
            logs = self.file_manager.read_csv('study_log.csv')
            today = datetime.now().strftime('%Y-%m-%d')
            today_logs = [log for log in logs if log.get('date') == today]

            if not today_logs:
                return {
                    'studied_today': False,
                    'correct_count': 0,
                    'total_count': 0,
                    'success_rate': 0
                }

            log = today_logs[0]
            return {
                'studied_today': True,
                'correct_count': int(log.get('correct_count', 0)),
                'total_count': int(log.get('words_count', 0)),
                'success_rate': float(log.get('success_rate', 0))
            }
        except Exception as e:
            logger.warning(f"오늘 통계 조회 실패: {e}")
            return {'studied_today': False}

    def reset_progress(self) -> bool:
        """진도 초기화"""
        try:
            self.progress = Progress(
                current_day=1,
                total_days=200,
                daily_target=10,
                created_date=datetime.now().strftime('%Y-%m-%d')
            )
            self.save_progress()
            logger.info("진도 초기화 완료")
            return True
        except Exception as e:
            logger.error(f"진도 초기화 실패: {e}")
            return False
