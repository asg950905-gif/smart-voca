#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - 웹 보안 (로그인/관리자 권한, CSRF, 로그인 시도 제한, 공용 응답 헬퍼)
# 파일 위치: src/web/security.py

import secrets
import time
from functools import wraps
from typing import Callable, Dict, Tuple
from flask import g, jsonify, redirect, request, session, url_for, abort

CSRF_SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS'}
LOGIN_MAX_FAILS = 5
LOGIN_LOCK_SECONDS = 300

# (ip, username) -> (실패 횟수, 첫 실패 시각). 단일 프로세스용 간단한 메모리 제한.
_login_failures: Dict[Tuple[str, str], Tuple[int, float]] = {}


def wants_json() -> bool:
    return request.path.startswith('/api/') or request.is_json


def json_error(message: str, status: int = 400):
    return jsonify({'error': message}), status


# ---------- 권한 ----------
def login_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.get('user') is None:
            if wants_json():
                return json_error('로그인이 필요합니다.', 401)
            return redirect(url_for('auth.login', next=request.full_path.rstrip('?')))
        return view(*args, **kwargs)
    return wrapper


def admin_required(view: Callable) -> Callable:
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if g.user['role'] != 'admin':
            if wants_json():
                return json_error('관리자 권한이 필요합니다.', 403)
            abort(403)
        return view(*args, **kwargs)
    return wrapper


def safe_next_url(target: str, default: str) -> str:
    """오픈 리다이렉트 방지: 같은 사이트의 상대 경로만 허용"""
    if target and target.startswith('/') and not target.startswith('//') and '\\' not in target:
        return target
    return default


# ---------- CSRF ----------
def get_csrf_token() -> str:
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_hex(16)
    return session['_csrf']


def check_csrf() -> None:
    """상태를 바꾸는 요청(POST/PUT/DELETE 등)은 세션 토큰과 일치하는 토큰을 요구한다."""
    if request.method in CSRF_SAFE_METHODS:
        return
    sent = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token', '')
    expected = session.get('_csrf', '')
    if not expected or not secrets.compare_digest(sent, expected):
        abort(400, description='잘못된 요청입니다. 페이지를 새로고침한 뒤 다시 시도하세요.')


# ---------- 로그인 시도 제한 ----------
def login_blocked(username: str) -> int:
    """잠금 상태면 남은 초를, 아니면 0 을 반환"""
    key = (request.remote_addr or '-', username.lower())
    fails, first = _login_failures.get(key, (0, 0.0))
    if fails >= LOGIN_MAX_FAILS:
        remain = int(first + LOGIN_LOCK_SECONDS - time.time())
        if remain > 0:
            return remain
        _login_failures.pop(key, None)
    return 0


def record_login_failure(username: str) -> None:
    key = (request.remote_addr or '-', username.lower())
    fails, first = _login_failures.get(key, (0, time.time()))
    _login_failures[key] = (fails + 1, first if fails else time.time())


def clear_login_failures(username: str) -> None:
    _login_failures.pop((request.remote_addr or '-', username.lower()), None)
