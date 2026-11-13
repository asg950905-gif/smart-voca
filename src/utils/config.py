#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - 설정 관리 (사용자 개인 설정 + 관리자 전역 설정)
# 파일 위치: src/utils/config.py

import logging
from typing import Dict
from src.data.database import Database

logger = logging.getLogger(__name__)

THEMES = ('system', 'light', 'dark')
# 전역 설정 기본값과 허용 범위 (관리자 화면에서 변경)
GLOBAL_DEFAULTS = {'total_days': 200, 'max_test_problems': 50, 'max_daily_target': 50}
GLOBAL_LIMITS = {'total_days': (1, 1000), 'max_test_problems': (5, 200), 'max_daily_target': (5, 100)}


class SettingsError(Exception):
    """사용자에게 보여줘도 되는 설정 오류"""


class SettingsManager:
    def __init__(self, db: Database):
        self.db = db

    # ---------- 사용자 개인 ----------
    def get_user_settings(self, user_id: int) -> Dict:
        row = self.db.query_one("SELECT daily_target, theme, auto_speak FROM users WHERE id = ?", (user_id,))
        row = row or {'daily_target': 10, 'theme': 'system', 'auto_speak': 0}
        row['auto_speak'] = bool(row['auto_speak'])   # 카드 넘길 때 자동 발음 (기본 꺼짐)
        row['max_daily_target'] = self.get_global()['max_daily_target']
        return row

    def save_user_settings(self, user_id: int, data: Dict) -> Dict:
        max_target = self.get_global()['max_daily_target']
        current = self.get_user_settings(user_id)
        try:
            # 일부 항목만 보내도 되도록(예: 테마 토글) 없는 항목은 현재 값을 유지한다
            target = int(data.get('daily_target', current['daily_target']))
        except (TypeError, ValueError):
            raise SettingsError('하루 학습량은 숫자여야 합니다.')
        if not 1 <= target <= max_target:
            raise SettingsError(f'하루 학습량은 1~{max_target} 사이여야 합니다.')
        theme = data.get('theme', current['theme'])
        if theme not in THEMES:
            raise SettingsError('올바르지 않은 테마입니다.')
        auto_speak = data.get('auto_speak', current['auto_speak'])
        if not isinstance(auto_speak, bool):          # 'yes'·2·null 같은 값은 받지 않는다 (JSON true/false 만)
            raise SettingsError('자동 발음 설정은 켜짐/꺼짐 값이어야 합니다.')
        self.db.execute("UPDATE users SET daily_target = ?, theme = ?, auto_speak = ? WHERE id = ?",
                        (target, theme, int(auto_speak), user_id))
        return self.get_user_settings(user_id)

    # ---------- 관리자 전역 ----------
    def get_global(self) -> Dict:
        return {k: int(self.db.get_setting(k, str(v))) for k, v in GLOBAL_DEFAULTS.items()}

    def save_global(self, data: Dict) -> Dict:
        for key, (low, high) in GLOBAL_LIMITS.items():
            if key not in data:
                continue
            try:
                value = int(data[key])
            except (TypeError, ValueError):
                raise SettingsError(f'{key} 는 숫자여야 합니다.')
            if not low <= value <= high:
                raise SettingsError(f'{key} 는 {low}~{high} 사이여야 합니다.')
            self.db.set_setting(key, str(value))
        return self.get_global()
