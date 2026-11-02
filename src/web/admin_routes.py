#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - 관리자 화면·API 라우트 (대시보드/단어/사용자/설정)
# 파일 위치: src/web/admin_routes.py

from io import BytesIO
from flask import Blueprint, current_app, g, jsonify, render_template, request, send_file
from src.business.auth_manager import AuthError
from src.business.word_manager import WordError
from src.utils.config import SettingsError
from src.web.security import admin_required, json_error

bp = Blueprint('admin', __name__, url_prefix='/admin')
api = Blueprint('admin_api', __name__, url_prefix='/api/admin')


# ===================== 페이지 =====================
@bp.route('/')
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')


@bp.route('/words')
@admin_required
def words_page():
    return render_template('admin/words.html')


@bp.route('/users')
@admin_required
def users_page():
    return render_template('admin/users.html')


@bp.route('/settings')
@admin_required
def settings_page():
    return render_template('admin/settings.html')


# ===================== API: 통계 =====================
@api.route('/overview')
@admin_required
def overview():
    return jsonify(current_app.reports.admin_overview())


@api.route('/charts')
@admin_required
def charts():
    return jsonify(current_app.reports.admin_charts())


# ===================== API: 단어 =====================
def _word_fields(data: dict):
    return (data.get('english'), data.get('korean'), data.get('part_of_speech', ''), data.get('example', ''))


@api.route('/words', methods=['GET', 'POST'])
@admin_required
def words():
    wm = current_app.words
    if request.method == 'POST':
        try:
            return jsonify(wm.add_word(*_word_fields(request.get_json(silent=True) or {}))), 201
        except WordError as e:
            return json_error(str(e))
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
    return jsonify(wm.list_words(request.args.get('q', ''), page))


@api.route('/words/<int:word_id>', methods=['PUT', 'DELETE'])
@admin_required
def word_detail(word_id):
    wm = current_app.words
    try:
        if request.method == 'DELETE':
            wm.delete_word(word_id)
            return jsonify({'status': 'success'})
        return jsonify(wm.update_word(word_id, *_word_fields(request.get_json(silent=True) or {})))
    except WordError as e:
        return json_error(str(e))


@api.route('/words/import', methods=['POST'])
@admin_required
def words_import():
    file = request.files.get('file')
    if not file or not file.filename:
        return json_error('파일을 선택하세요.')
    if not file.filename.lower().endswith('.csv'):
        return json_error('CSV 파일만 업로드할 수 있습니다.')
    data = file.read(2 * 1024 * 1024 + 1)  # 2MB 초과 방지
    if len(data) > 2 * 1024 * 1024:
        return json_error('파일은 2MB 이하여야 합니다.')
    try:
        return jsonify({'status': 'success', **current_app.words.import_csv(data)})
    except WordError as e:
        return json_error(str(e))


@api.route('/words/export')
@admin_required
def words_export():
    csv_text = current_app.words.export_csv()
    return send_file(BytesIO(csv_text.encode('utf-8')), mimetype='text/csv',
                     as_attachment=True, download_name='smart-voca-words.csv')


# ===================== API: 사용자 =====================
@api.route('/users')
@admin_required
def users():
    return jsonify(current_app.auth.list_users(request.args.get('q', '')))


def _user_action(action):
    try:
        action()
        return jsonify({'status': 'success'})
    except AuthError as e:
        return json_error(str(e))


@api.route('/users/<int:user_id>/role', methods=['POST'])
@admin_required
def user_role(user_id):
    role = (request.get_json(silent=True) or {}).get('role', '')
    return _user_action(lambda: current_app.auth.set_role(user_id, role, g.user['id']))


@api.route('/users/<int:user_id>/active', methods=['POST'])
@admin_required
def user_active(user_id):
    active = bool((request.get_json(silent=True) or {}).get('active'))
    return _user_action(lambda: current_app.auth.set_active(user_id, active, g.user['id']))


@api.route('/users/<int:user_id>/password', methods=['POST'])
@admin_required
def user_password(user_id):
    password = (request.get_json(silent=True) or {}).get('password', '')
    return _user_action(lambda: current_app.auth.reset_password(user_id, password))


@api.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def user_delete(user_id):
    return _user_action(lambda: current_app.auth.delete_user(user_id, g.user['id']))


# ===================== API: 전역 설정 =====================
@api.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    if request.method == 'POST':
        try:
            return jsonify(current_app.settings.save_global(request.get_json(silent=True) or {}))
        except SettingsError as e:
            return json_error(str(e))
    return jsonify(current_app.settings.get_global())
