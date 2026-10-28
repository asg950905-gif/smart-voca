#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-28 - smart-voca - 단어 관리
# 파일 위치: src/business/word_manager.py

from typing import List, Dict, Optional
import logging
from src.data.models import Word
from src.data.file_manager import FileManager

logger = logging.getLogger(__name__)


class WordManager:
    """단어 데이터 관리"""

    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager
        self.words: Dict[int, Word] = {}  # ID로 인덱싱
        self.words_by_english: Dict[str, int] = {}  # 영어로 인덱싱
        self.load_words()

    def load_words(self, filepath: str = None) -> bool:
        """CSV 파일에서 단어 로드"""
        try:
            filename = filepath if filepath else 'words.csv'
            # 파일명이 경로라면 추출
            if '/' in str(filename) or '\\' in str(filename):
                filename = filename.split('/')[-1].split('\\')[-1]

            data = self.file_manager.read_csv(filename)

            if not data:
                logger.warning("로드할 단어 데이터가 없습니다")
                return False

            self.words.clear()
            self.words_by_english.clear()

            for idx, row in enumerate(data, start=1):
                try:
                    word = Word(
                        id=int(row.get('id', idx)),
                        english=row.get('english', '').strip(),
                        korean=row.get('korean', '').strip(),
                        part_of_speech=row.get('part_of_speech', ''),
                        example=row.get('example', ''),
                        weight=int(row.get('weight', 0)),
                        last_studied=row.get('last_studied'),
                        success_count=int(row.get('success_count', 0)),
                        fail_count=int(row.get('fail_count', 0))
                    )

                    if word.english:
                        self.words[word.id] = word
                        self.words_by_english[word.english.lower()] = word.id

                except Exception as e:
                    logger.warning(f"단어 로드 오류 (행 {idx}): {e}")
                    continue

            logger.info(f"단어 로드 완료: {len(self.words)}개")
            return True

        except Exception as e:
            logger.error(f"단어 로드 실패: {e}")
            return False

    def save_words(self, filename: str = 'words.csv') -> bool:
        """단어를 CSV로 저장"""
        try:
            data = [word.to_dict() for word in self.words.values()]
            return self.file_manager.write_csv(filename, data)
        except Exception as e:
            logger.error(f"단어 저장 실패: {e}")
            return False

    def get_word(self, word_id: int) -> Optional[Word]:
        """ID로 단어 조회"""
        return self.words.get(word_id)

    def get_all_words(self) -> List[Word]:
        """모든 단어 반환"""
        return list(self.words.values())

    def get_word_by_english(self, english: str) -> Optional[Word]:
        """영단어로 조회"""
        word_id = self.words_by_english.get(english.lower())
        if word_id:
            return self.words.get(word_id)
        return None

    def get_random_words(self, count: int) -> List[Word]:
        """랜덤 단어 선택"""
        import random
        words = list(self.words.values())
        if count > len(words):
            count = len(words)
        return random.sample(words, count)

    def get_words_by_weight(self, count: int) -> List[Word]:
        """가중치 기반 단어 선택 (복습이 필요한 단어 우선)"""
        words = sorted(
            self.words.values(),
            key=lambda w: w.weight,
            reverse=True
        )
        return words[:count]

    def update_word(self, word_id: int, success: bool) -> bool:
        """단어 학습 결과 업데이트"""
        word = self.get_word(word_id)
        if not word:
            return False

        if success:
            word.success_count += 1
            word.weight = max(0, word.weight - 1)  # 가중치 감소
        else:
            word.fail_count += 1
            word.weight += 1  # 가중치 증가

        from datetime import datetime
        word.last_studied = datetime.now().strftime('%Y-%m-%d')

        return True

    def validate_words(self) -> bool:
        """단어 데이터 유효성 검사"""
        if not self.words:
            logger.error("로드된 단어가 없습니다")
            return False

        for word in self.words.values():
            if not word.english or not word.korean:
                logger.error(f"필수 필드 누락: {word}")
                return False

        logger.info("단어 유효성 검사 완료")
        return True
