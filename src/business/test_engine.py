#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-28 - smart-voca - 시험 엔진
# 파일 위치: src/business/test_engine.py

from typing import List, Dict, Optional
from datetime import datetime
import logging
from src.data.models import Word, Question, TestLog
from src.data.file_manager import FileManager
from src.business.word_manager import WordManager

logger = logging.getLogger(__name__)


class TestEngine:
    """시험 출제 및 채점"""

    def __init__(self, word_manager: WordManager, file_manager: FileManager):
        self.word_manager = word_manager
        self.file_manager = file_manager
        self.config = {}
        self.problems = []
        self.current_problem_idx = 0
        self.results = []

    def configure_test(self, config: Dict) -> bool:
        """시험 설정"""
        try:
            self.config = {
                'num_problems': int(config.get('num_problems', 10)),
                'mode': config.get('mode', '혼합'),  # 한->영, 영->한, 혼합
                'format': config.get('format', '혼합')  # 단답형, 4지선다형, OX형, 혼합
            }
            self.problems = []
            self.current_problem_idx = 0
            self.results = []

            # 문제 생성
            self.generate_problems()

            logger.info(f"시험 설정 완료: {self.config}")
            return True
        except Exception as e:
            logger.error(f"시험 설정 실패: {e}")
            return False

    def generate_problems(self) -> None:
        """문제 생성"""
        try:
            words = self.word_manager.get_words_by_weight(self.config['num_problems'])

            for idx, word in enumerate(words):
                # 모드 결정
                mode = self.config['mode']
                if mode == '혼합':
                    import random
                    mode = random.choice(['한->영', '영->한'])

                # 형식 결정
                fmt = self.config['format']
                if fmt == '혼합':
                    import random
                    fmt = random.choice(['단답형', '4지선다형', 'OX형'])

                # 문제 생성
                question = self.generate_question(word, mode, fmt)
                self.problems.append(question)

            logger.info(f"문제 {len(self.problems)}개 생성 완료")
        except Exception as e:
            logger.error(f"문제 생성 실패: {e}")

    def generate_question(self, word: Word, mode: str, fmt: str) -> Question:
        """개별 문제 생성"""
        if mode == '한->영':
            question_text = f"'{word.korean}'의 영문은?"
            correct_answer = word.english
        else:  # 영->한
            question_text = f"'{word.english}'의 뜻은?"
            correct_answer = word.korean

        options = None
        if fmt == '4지선다형':
            options = self.generate_options(correct_answer, word, mode)

        return Question(
            id=word.id,
            word=word,
            mode=mode,
            format=fmt,
            question_text=question_text,
            options=options,
            correct_answer=correct_answer
        )

    def generate_options(self, correct: str, word: Word, mode: str) -> List[str]:
        """4지선다형 선택지 생성"""
        import random

        options = [correct]
        all_words = self.word_manager.get_all_words()

        # 다른 단어에서 선택지 추가
        while len(options) < 4:
            random_word = random.choice(all_words)
            if random_word.id == word.id:
                continue

            option = random_word.english if mode == '한->영' else random_word.korean
            if option not in options:
                options.append(option)

        random.shuffle(options)
        return options

    def get_current_problem(self) -> Dict:
        """현재 문제 반환"""
        if self.current_problem_idx < len(self.problems):
            problem = self.problems[self.current_problem_idx]
            return problem.to_dict()
        return {}

    def grade_answer(self, user_answer: str) -> bool:
        """답변 채점"""
        if self.current_problem_idx >= len(self.problems):
            return False

        problem = self.problems[self.current_problem_idx]
        is_correct = user_answer.strip().lower() == problem.correct_answer.lower()

        problem.user_answer = user_answer
        problem.is_correct = is_correct

        self.results.append({
            'word_id': problem.id,
            'question': problem.question_text,
            'user_answer': user_answer,
            'correct_answer': problem.correct_answer,
            'is_correct': is_correct
        })

        self.current_problem_idx += 1

        return is_correct

    def next_problem(self) -> bool:
        """다음 문제로 이동"""
        if self.current_problem_idx < len(self.problems):
            return True
        return False

    def record_test(self) -> bool:
        """시험 결과 저장"""
        try:
            correct_count = sum(1 for r in self.results if r['is_correct'])
            total = len(self.results)

            test_log = TestLog(
                date=datetime.now().strftime('%Y-%m-%d'),
                mode=self.config.get('mode', '혼합'),
                format=self.config.get('format', '혼합'),
                total_problems=total,
                correct_answers=correct_count,
                score=correct_count / total * 100 if total > 0 else 0
            )

            self.file_manager.append_csv('test_log.csv', test_log.to_dict())

            # 단어 가중치 업데이트
            for result in self.results:
                self.word_manager.update_word(
                    result['word_id'],
                    result['is_correct']
                )

            self.word_manager.save_words()

            logger.info(f"시험 기록 저장: {correct_count}/{total}")
            return True
        except Exception as e:
            logger.error(f"시험 기록 저장 실패: {e}")
            return False

    def get_results(self) -> Dict:
        """시험 결과 반환"""
        correct_count = sum(1 for r in self.results if r['is_correct'])
        total = len(self.results)

        return {
            'total_problems': total,
            'correct_answers': correct_count,
            'score': correct_count / total * 100 if total > 0 else 0,
            'details': self.results
        }

    def is_finished(self) -> bool:
        """시험 완료 여부"""
        return self.current_problem_idx >= len(self.problems)
