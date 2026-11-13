#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - 인증·사용자 관리 (가입/로그인/역할/계정 관리)
# 파일 위치: src/business/auth_manager.py

import re
import logging
from typing import Dict, List, Optional, Tuple
from werkzeug.security import generate_password_hash, check_password_hash
from src.data.database import Database

logger = logging.getLogger(__name__)

USERNAME_PATTERN = re.compile(r'^[A-Za-z0-9_]{3,20}$')
MIN_PASSWORD_LENGTH = 6
PUBLIC_FIELDS = "id, username, display_name, role, active, daily_target, theme, auto_speak, created_at"


class AuthError(Exception):
    """사용자에게 그대로 보여줘도 되는 인증/검증 오류"""


class AuthManager:
    """사용자 계정과 역할 관리"""

    def __init__(self, db: Database):
        self.db = db

    # ---------- 가입/로그인 ----------
    def register(self, username: str, password: str, display_name: str = '', role: str = 'user') -> Dict:
        username = (username or '').strip()
        if not USERNAME_PATTERN.match(username):
            raise AuthError('아이디는 영문·숫자·밑줄 3~20자로 입력하세요.')
        if len(password or '') < MIN_PASSWORD_LENGTH:
            raise AuthError(f'비밀번호는 {MIN_PASSWORD_LENGTH}자 이상이어야 합니다.')
        if self.db.query_one("SELECT 1 FROM users WHERE username = ? COLLATE NOCASE", (username,)):
            raise AuthError('이미 사용 중인 아이디입니다.')
        user_id = self.db.execute(
            "INSERT INTO users(username, display_name, password_hash, role) VALUES(?, ?, ?, ?)",
            (username, (display_name or username).strip(), generate_password_hash(password), role),
        )
        logger.info(f"사용자 가입: {username} ({role})")
        return self.get_user(user_id)

    def authenticate(self, username: str, password: str) -> Dict:
        row = self.db.query_one(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE", ((username or '').strip(),)
        )
        # 아이디 존재 여부를 노출하지 않도록 동일한 메시지를 쓴다
        if not row or not check_password_hash(row['password_hash'], password or ''):
            raise AuthError('아이디 또는 비밀번호가 올바르지 않습니다.')
        if not row['active']:
            raise AuthError('비활성화된 계정입니다. 관리자에게 문의하세요.')
        return self.get_user(row['id'])

    def ensure_admin(self, username: str, password: str) -> None:
        """관리자 계정이 하나도 없을 때만 지정된 계정을 생성 (환경변수/시연 스크립트용)"""
        if self.db.scalar("SELECT COUNT(*) FROM users WHERE role = 'admin'") == 0:
            self.register(username, password, display_name='관리자', role='admin')

    # ---------- 조회 ----------
    def get_user(self, user_id: int) -> Optional[Dict]:
        return self.db.query_one(f"SELECT {PUBLIC_FIELDS} FROM users WHERE id = ?", (user_id,))

    def list_users(self, keyword: str = '') -> List[Dict]:
        like = f"%{keyword.strip()}%"
        return self.db.query(
            f"""SELECT u.id, u.username, u.display_name, u.role, u.active, u.created_at,
                   (SELECT MAX(date) FROM study_logs s WHERE s.user_id = u.id) AS last_study,
                   (SELECT COUNT(DISTINCT date) FROM study_logs s WHERE s.user_id = u.id) AS study_days,
                   (SELECT ROUND(AVG(score), 1) FROM test_logs t WHERE t.user_id = u.id) AS avg_score
                FROM users u WHERE u.username LIKE ? OR u.display_name LIKE ?
                ORDER BY u.id""",
            (like, like),
        )

    # ---------- 관리 ----------
    def set_role(self, user_id: int, role: str, acting_user_id: int) -> None:
        if role not in ('user', 'admin'):
            raise AuthError('올바르지 않은 역할입니다.')
        if user_id == acting_user_id:
            raise AuthError('자신의 역할은 변경할 수 없습니다.')
        self._require_user(user_id)
        self.db.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))

    def set_active(self, user_id: int, active: bool, acting_user_id: int) -> None:
        if user_id == acting_user_id:
            raise AuthError('자신의 계정은 비활성화할 수 없습니다.')
        self._require_user(user_id)
        self.db.execute("UPDATE users SET active = ? WHERE id = ?", (1 if active else 0, user_id))

    def reset_password(self, user_id: int, new_password: str) -> None:
        if len(new_password or '') < MIN_PASSWORD_LENGTH:
            raise AuthError(f'비밀번호는 {MIN_PASSWORD_LENGTH}자 이상이어야 합니다.')
        self._require_user(user_id)
        self.db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new_password), user_id)
        )

    def delete_user(self, user_id: int, acting_user_id: int) -> None:
        if user_id == acting_user_id:
            raise AuthError('자신의 계정은 삭제할 수 없습니다.')
        self._require_user(user_id)
        self.db.execute("DELETE FROM users WHERE id = ?", (user_id,))  # 학습 기록은 CASCADE 로 함께 삭제

    def _require_user(self, user_id: int) -> Dict:
        user = self.get_user(user_id)
        if not user:
            raise AuthError('존재하지 않는 사용자입니다.')
        return user
