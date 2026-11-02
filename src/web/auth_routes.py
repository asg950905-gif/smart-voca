#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - 인증 라우트 (로그인/가입/로그아웃)
# 파일 위치: src/web/auth_routes.py

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, session, url_for
from src.business.auth_manager import AuthError
from src.web.security import (clear_login_failures, login_blocked, record_login_failure, safe_next_url)

bp = Blueprint('auth', __name__)


def home_for(user: dict) -> str:
    return url_for('admin.dashboard') if user['role'] == 'admin' else url_for('user.dashboard')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if g.get('user'):
        return redirect(home_for(g.user))
    if request.method == 'POST':
        username = request.form.get('username', '')
        remain = login_blocked(username)
        if remain:
            flash(f'로그인 시도가 너무 많습니다. {remain // 60 + 1}분 후 다시 시도하세요.', 'error')
        else:
            try:
                user = current_app.auth.authenticate(username, request.form.get('password', ''))
            except AuthError as e:
                record_login_failure(username)
                flash(str(e), 'error')
            else:
                clear_login_failures(username)
                session.clear()  # 세션 고정 공격 방지: 로그인 시 세션을 새로 시작
                session['user_id'] = user['id']
                session.permanent = True
                return redirect(safe_next_url(request.args.get('next', ''), home_for(user)))
    return render_template('login.html', username=request.form.get('username', ''))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if g.get('user'):
        return redirect(home_for(g.user))
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password != request.form.get('password_confirm', ''):
            flash('비밀번호 확인이 일치하지 않습니다.', 'error')
        else:
            try:
                user = current_app.auth.register(
                    request.form.get('username', ''), password, request.form.get('display_name', ''))
            except AuthError as e:
                flash(str(e), 'error')
            else:
                session.clear()
                session['user_id'] = user['id']
                session.permanent = True
                return redirect(url_for('user.dashboard'))
    return render_template('register.html', username=request.form.get('username', ''),
                           display_name=request.form.get('display_name', ''))


@bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
