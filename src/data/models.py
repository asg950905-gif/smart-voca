#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-28 - smart-voca - 데이터 모델
# 파일 위치: src/data/models.py

from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime


@dataclass
class Word:
    """단어 데이터 모델"""
    id: int
    english: str
    korean: str
    part_of_speech: str = ""
    example: str = ""
    weight: int = 0  # 가중치 (복습 빈도)
    last_studied: Optional[str] = None  # 마지막 학습일
    success_count: int = 0  # 성공 횟수
    fail_count: int = 0  # 실패 횟수

    def to_dict(self):
        """딕셔너리로 변환"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """딕셔너리에서 생성"""
        return cls(**data)

    def get_success_rate(self) -> float:
        """성공률 계산"""
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.0
        return (self.success_count / total) * 100


@dataclass
class Progress:
    """학습 진도 모델"""
    current_day: int = 1
    total_days: int = 200
    daily_target: int = 10
    created_date: str = ""
    last_studied_date: str = ""

    def to_dict(self):
        """딕셔너리로 변환"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """딕셔너리에서 생성"""
        return cls(**data)

    def get_completion_rate(self) -> float:
        """완료율 계산 (%)"""
        return (self.current_day / self.total_days) * 100


@dataclass
class StudyLog:
    """학습 기록"""
    date: str
    day: int
    words_count: int
    correct_count: int
    success_rate: float
    duration: int = 0  # 초 단위

    def to_dict(self):
        return asdict(self)


@dataclass
class TestLog:
    """시험 기록"""
    date: str
    mode: str  # 한->영, 영->한, 혼합
    format: str  # 단답형, 4지선다형, OX형
    total_problems: int
    correct_answers: int
    score: float
    duration: int = 0

    def get_score_percentage(self) -> float:
        """점수 (%)"""
        if self.total_problems == 0:
            return 0.0
        return (self.correct_answers / self.total_problems) * 100

    def to_dict(self):
        return asdict(self)


@dataclass
class Question:
    """시험 문제"""
    id: int
    word: Word
    mode: str  # 한->영, 영->한
    format: str  # 단답형, 4지선다형, OX형
    question_text: str
    options: list = None  # 4지선다형용
    correct_answer: str = ""
    user_answer: str = ""
    is_correct: bool = False

    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question_text,
            'options': self.options,
            'format': self.format,
            'mode': self.mode
        }


@dataclass
class Statistics:
    """통계 데이터"""
    total_study_days: int = 0
    total_test_attempts: int = 0
    total_words: int = 0
    memorized_words: int = 0  # 성공률 80% 이상
    weak_words: int = 0  # 성공률 30% 이하
    average_test_score: float = 0.0
    average_study_success_rate: float = 0.0

    def to_dict(self):
        return asdict(self)
