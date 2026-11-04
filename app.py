#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - Flask 애플리케이션 팩토리 (사용자/관리자 화면, SQLite)
# 파일 위치: app.py

import mimetypes
import os
import secrets
import sys
from datetime import timedelta
from pathlib import Path

from flask import Flask, flash, g, jsonify, render_template, request, session, send_from_directory

# Windows 환경에서 .js, .css MIME type 설정 (한글 경로 호환)
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')

# 프로젝트 루트를 import 경로에 추가 (src.* 패키지 import 용)
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.database import Database
from src.business.auth_manager import AuthManager
from src.business.word_manager import WordManager
from src.business.study_manager import StudyManager
from src.business.test_engine import TestEngine
from src.business.report_generator import ReportGenerator
from src.business.gamification import GamificationManager
from src.utils.config import SettingsManager
from src.web import admin_routes, auth_routes, user_routes
from src.web.security import check_csrf, get_csrf_token, wants_json


def _load_secret_key(data_dir: Path) -> str:
    """SECRET_KEY 는 환경변수를 우선하고, 없으면 data/ 에 한 번 생성해 재사용한다 (코드에 하드코딩 금지)."""
    env_key = os.environ.get('SECRET_KEY')
    if env_key:
        return env_key
    key_file = data_dir / 'secret_key.txt'
    if not key_file.exists():
        key_file.write_text(secrets.token_hex(32), encoding='utf-8')
    return key_file.read_text(encoding='utf-8').strip()


def create_app(data_dir=None) -> Flask:
    data_dir = Path(data_dir or os.environ.get('DATA_DIR') or PROJECT_ROOT / 'data')
    data_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__, static_folder=str(PROJECT_ROOT / 'static'), static_url_path='/static')
    app.config.update(
        SECRET_KEY=_load_secret_key(data_dir),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE') == '1',  # HTTPS 배포 시 1
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        MAX_CONTENT_LENGTH=3 * 1024 * 1024,  # 업로드 상한 3MB
    )

    # 서비스 객체: 요청 간 공유되지만 사용자별 상태는 모두 DB 에 있다
    db = Database(data_dir / 'smart_voca.db')
    app.db = db
    app.auth = AuthManager(db)
    app.words = WordManager(db)
    app.game = GamificationManager(db)
    app.study = StudyManager(db, app.words, app.game)
    app.tests = TestEngine(db, app.words, app.game)
    app.reports = ReportGenerator(db)
    app.settings = SettingsManager(db)

    # 관리자 계정이 없으면 환경변수로 지정된 계정을 생성 (기본 비밀번호는 코드에 두지 않는다)
    admin_user, admin_pw = os.environ.get('ADMIN_USERNAME'), os.environ.get('ADMIN_PASSWORD')
    if admin_user and admin_pw:
        app.auth.ensure_admin(admin_user, admin_pw)

    @app.route('/static/js/<path:filename>')
    def serve_js(filename):
        response = send_from_directory(app.static_folder + '/js', filename)
        response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
        return response

    @app.route('/static/css/<path:filename>')
    def serve_css(filename):
        response = send_from_directory(app.static_folder + '/css', filename)
        response.headers['Content-Type'] = 'text/css; charset=utf-8'
        return response

    @app.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory(app.static_folder, filename)

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(user_routes.bp)
    app.register_blueprint(admin_routes.bp)
    app.register_blueprint(admin_routes.api)

    @app.before_request
    def load_user():
        g.user = None
        g.kicked = False
        user_id = session.get('user_id')
        if user_id:
            user = app.auth.get_user(user_id)
            if user and user['active']:
                g.user = user
            else:
                session.pop('user_id', None)  # 삭제·비활성화된 계정의 세션은 즉시 무효화
                g.kicked = True  # 강제 로그아웃: 랜딩 대신 로그인 화면에서 사유를 보여준다
                flash('계정이 비활성화되었거나 삭제되어 로그아웃되었어요. 관리자에게 문의하세요.', 'error')
        check_csrf()

    @app.context_processor
    def inject_globals():
        return {'current_user': g.get('user'), 'csrf_token': get_csrf_token()}

    @app.after_request
    def add_security_headers(response):
        # MIME type 명시 (Windows 환경 호환)
        if request.path.endswith('.js'):
            response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
        elif request.path.endswith('.css'):
            response.headers['Content-Type'] = 'text/css; charset=utf-8'

        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'same-origin')
        return response

    def error_response(status, message):
        if wants_json():
            return jsonify({'error': message}), status
        return render_template('error.html', status=status, message=message), status

    @app.errorhandler(400)
    def bad_request(e):
        return error_response(400, getattr(e, 'description', None) or '잘못된 요청입니다.')

    @app.errorhandler(403)
    def forbidden(e):
        return error_response(403, '접근 권한이 없습니다.')

    @app.errorhandler(404)
    def not_found(e):
        return error_response(404, '페이지를 찾을 수 없습니다.')

    @app.errorhandler(413)
    def too_large(e):
        return error_response(413, '파일이 너무 큽니다 (최대 3MB).')

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.exception('서버 오류')
        return error_response(500, '서버 오류가 발생했습니다.')

    return app


app = create_app()

if __name__ == '__main__':
    # 기본은 본인 PC(127.0.0.1)만 접속 가능. 팀 테스트 배포 시 HOST=0.0.0.0, FLASK_DEBUG 는 끈 채로 사용한다.
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1',
            host=os.environ.get('HOST', '127.0.0.1'),
            port=int(os.environ.get('PORT', 5000)))
