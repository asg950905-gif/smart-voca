#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-10-28 - smart-voca - Flask 메인 애플리케이션
# 파일 위치: app.py

from flask import Flask, render_template, request, jsonify, send_file
import os
import sys
from pathlib import Path

# 프로젝트 경로 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))

from business.word_manager import WordManager
from business.study_manager import StudyManager
from business.test_engine import TestEngine
from business.report_generator import ReportGenerator
from data.file_manager import FileManager
from utils.config import ConfigManager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = project_root / 'data'

# 데이터 디렉토리 생성
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(project_root / 'logs', exist_ok=True)

# 매니저 초기화
file_manager = FileManager(app.config['UPLOAD_FOLDER'])
word_manager = WordManager(file_manager)
study_manager = StudyManager(word_manager, file_manager)
test_engine = TestEngine(word_manager, file_manager)
report_generator = ReportGenerator(file_manager)
config_manager = ConfigManager(file_manager)


# ===================== 기본 라우트 =====================

@app.route('/', methods=['GET'])
def home():
    """메인 대시보드"""
    try:
        progress = study_manager.get_progress_info()
        return render_template('dashboard.html', progress=progress)
    except Exception as e:
        return render_template('dashboard.html', error=str(e))


@app.route('/study', methods=['GET'])
def study_page():
    """학습 페이지"""
    return render_template('study.html')


@app.route('/test', methods=['GET'])
def test_page():
    """시험 페이지"""
    return render_template('test.html')


@app.route('/report', methods=['GET'])
def report_page():
    """통계 페이지"""
    return render_template('report.html')


@app.route('/settings', methods=['GET'])
def settings_page():
    """설정 페이지"""
    return render_template('settings.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """CSV 파일 업로드"""
    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                return jsonify({'error': '파일을 선택하세요'}), 400

            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': '파일명이 없습니다'}), 400

            if not file.filename.endswith('.csv'):
                return jsonify({'error': 'CSV 파일만 업로드 가능합니다'}), 400

            filepath = app.config['UPLOAD_FOLDER'] / 'words.csv'
            file.save(str(filepath))

            word_manager.load_words(str(filepath))
            return jsonify({'status': 'success', 'message': f'파일 업로드 완료: {len(word_manager.words)}개 단어'})

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return render_template('upload.html')


# ===================== API - 학습 =====================

@app.route('/api/study/daily-words', methods=['GET'])
def api_get_daily_words():
    """오늘의 학습 단어"""
    try:
        words = study_manager.get_daily_words()
        return jsonify([word.to_dict() for word in words])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/study/record', methods=['POST'])
def api_record_study():
    """학습 결과 저장"""
    try:
        data = request.json
        study_manager.record_study(data.get('results', []))
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/progress', methods=['GET'])
def api_get_progress():
    """진도 정보"""
    try:
        progress = study_manager.get_progress_info()
        return jsonify(progress)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===================== API - 시험 =====================

@app.route('/api/test/configure', methods=['POST'])
def api_configure_test():
    """시험 설정"""
    try:
        config = request.json
        test_engine.configure_test(config)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/test/next-problem', methods=['GET'])
def api_next_problem():
    """다음 문제"""
    try:
        problem = test_engine.get_current_problem()
        return jsonify(problem)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/test/submit-answer', methods=['POST'])
def api_submit_answer():
    """답변 제출 및 채점"""
    try:
        data = request.json
        is_correct = test_engine.grade_answer(data.get('answer'))
        return jsonify({
            'is_correct': is_correct,
            'correct_answer': test_engine.get_current_problem().get('correct_answer')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/test/finish', methods=['POST'])
def api_finish_test():
    """시험 완료"""
    try:
        results = test_engine.get_results()
        test_engine.record_test()
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===================== API - 통계 =====================

@app.route('/api/report/statistics', methods=['GET'])
def api_get_statistics():
    """통계 데이터"""
    try:
        stats = report_generator.calculate_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/report/charts', methods=['GET'])
def api_get_charts():
    """차트 데이터"""
    try:
        charts = report_generator.get_chart_data()
        return jsonify(charts)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/report/export', methods=['GET'])
def export_report():
    """보고서 CSV 다운로드"""
    try:
        csv_data = report_generator.export_csv()
        return send_file(
            csv_data,
            mimetype='text/csv',
            as_attachment=True,
            download_name='smart-voca-report.csv'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===================== API - 설정 =====================

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """설정 조회/저장"""
    try:
        if request.method == 'POST':
            config_manager.save_settings(request.json)
            return jsonify({'status': 'success'})
        else:
            settings = config_manager.get_settings()
            return jsonify(settings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/reset', methods=['POST'])
def api_reset_settings():
    """데이터 초기화"""
    try:
        config_manager.reset_data(app.config['UPLOAD_FOLDER'])
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===================== 에러 핸들러 =====================

@app.errorhandler(404)
def not_found(error):
    """404 에러"""
    return jsonify({'error': '페이지를 찾을 수 없습니다'}), 404


@app.errorhandler(500)
def internal_error(error):
    """500 에러"""
    return jsonify({'error': '서버 오류가 발생했습니다'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
