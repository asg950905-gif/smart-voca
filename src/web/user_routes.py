#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - 사용자 화면·API 라우트 (대시보드/학습/시험/리포트/설정)
# 파일 위치: src/web/user_routes.py

from flask import Blueprint, current_app, g, jsonify, render_template, request, send_file
from io import BytesIO
from src.business.test_engine import TestError
from src.utils.config import SettingsError
from src.web.security import json_error, login_required

bp = Blueprint('user', __name__)


# ===================== 페이지 =====================
@bp.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html', progress=current_app.study.get_progress_info(g.user['id']))


@bp.route('/study')
@login_required
def study_page():
    return render_template('study.html')


@bp.route('/test')
@login_required
def test_page():
    return render_template('test.html')


@bp.route('/report')
@login_required
def report_page():
    return render_template('report.html')


@bp.route('/settings')
@login_required
def settings_page():
    return render_template('settings.html')


# ===================== API: 학습 =====================
@bp.route('/api/study/daily-words')
@login_required
def api_daily_words():
    return jsonify(current_app.study.get_daily_words(g.user['id']))


@bp.route('/api/study/record', methods=['POST'])
@login_required
def api_record_study():
    data = request.get_json(silent=True) or {}
    results = data.get('results')
    if not isinstance(results, list):
        return json_error('학습 결과가 올바르지 않습니다.')
    summary = current_app.study.record_study(g.user['id'], results)
    return jsonify({'status': 'success', **summary})


@bp.route('/api/progress')
@login_required
def api_progress():
    return jsonify(current_app.study.get_progress_info(g.user['id']))


# ===================== API: 시험 =====================
@bp.route('/api/test/start', methods=['POST'])
@login_required
def api_test_start():
    try:
        return jsonify(current_app.tests.start_test(g.user['id'], request.get_json(silent=True) or {}))
    except TestError as e:
        return json_error(str(e))


@bp.route('/api/test/current')
@login_required
def api_test_current():
    try:
        return jsonify(current_app.tests.get_current_problem(g.user['id']))
    except TestError as e:
        return json_error(str(e), 404)


@bp.route('/api/test/answer', methods=['POST'])
@login_required
def api_test_answer():
    data = request.get_json(silent=True) or {}
    try:
        return jsonify(current_app.tests.grade_answer(g.user['id'], str(data.get('answer', ''))))
    except TestError as e:
        return json_error(str(e))


@bp.route('/api/test/finish', methods=['POST'])
@login_required
def api_test_finish():
    try:
        return jsonify(current_app.tests.finish_test(g.user['id']))
    except TestError as e:
        return json_error(str(e))


# ===================== API: 통계 =====================
@bp.route('/api/report/statistics')
@login_required
def api_statistics():
    return jsonify(current_app.reports.user_statistics(g.user['id']))


@bp.route('/api/report/charts')
@login_required
def api_charts():
    return jsonify(current_app.reports.user_charts(g.user['id']))


@bp.route('/report/export')
@login_required
def export_report():
    csv_text = current_app.reports.export_user_csv(g.user['id']).getvalue()
    return send_file(BytesIO(csv_text.encode('utf-8')), mimetype='text/csv',
                     as_attachment=True, download_name='smart-voca-report.csv')


# ===================== API: 설정 =====================
@bp.route('/api/settings', methods=['GET', 'POST'])
@login_required
def api_settings():
    if request.method == 'POST':
        try:
            return jsonify(current_app.settings.save_user_settings(g.user['id'], request.get_json(silent=True) or {}))
        except SettingsError as e:
            return json_error(str(e))
    return jsonify(current_app.settings.get_user_settings(g.user['id']))


@bp.route('/api/settings/reset', methods=['POST'])
@login_required
def api_reset_progress():
    current_app.study.reset_user_progress(g.user['id'])
    return jsonify({'status': 'success'})
