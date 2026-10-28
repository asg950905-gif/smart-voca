#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-28 - smart-voca - 설정 관리
# 파일 위치: src/utils/config.py

from typing import Dict
import logging
from src.data.file_manager import FileManager

logger = logging.getLogger(__name__)


class ConfigManager:
    """설정 관리"""

    DEFAULT_CONFIG = {
        'daily_target': 10,
        'dark_mode': False,
        'theme': 'default',
        'font_size': 'medium',
        'auto_save': True
    }

    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager
        self.config = self.load_settings()

    def load_settings(self) -> Dict:
        """설정 로드"""
        try:
            settings = self.file_manager.read_json('settings.json')
            if settings:
                # 기본값과 병합
                return {**self.DEFAULT_CONFIG, **settings}
            return self.DEFAULT_CONFIG
        except Exception as e:
            logger.warning(f"설정 로드 실패: {e}, 기본값 사용")
            return self.DEFAULT_CONFIG

    def save_settings(self, config: Dict) -> bool:
        """설정 저장"""
        try:
            self.config = {**self.DEFAULT_CONFIG, **config}
            return self.file_manager.write_json('settings.json', self.config)
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")
            return False

    def get_settings(self) -> Dict:
        """설정 조회"""
        return self.config

    def get(self, key: str, default=None):
        """개별 설정 조회"""
        return self.config.get(key, default)

    def set(self, key: str, value) -> bool:
        """개별 설정 저장"""
        self.config[key] = value
        return self.save_settings(self.config)

    def reset_data(self, data_dir) -> bool:
        """모든 데이터 초기화"""
        try:
            # 파일 삭제
            for filename in ['progress.json', 'study_log.csv', 'test_log.csv']:
                self.file_manager.delete_file(filename)

            # 단어 파일의 가중치 초기화
            words = self.file_manager.read_csv('words.csv')
            for word in words:
                word['weight'] = 0
                word['success_count'] = 0
                word['fail_count'] = 0

            if words:
                self.file_manager.write_csv('words.csv', words)

            logger.info("데이터 초기화 완료")
            return True
        except Exception as e:
            logger.error(f"데이터 초기화 실패: {e}")
            return False
