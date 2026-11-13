#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-13 - smart-voca - 토익단어적용.py 테스트 (기본 '추가+수정'은 학습 기록을 지키고, --replace 는 확인 없이는 실행되지 않는다)
# 파일 위치: tests/test_word_apply.py

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.business.auth_manager import AuthManager  # noqa: E402
from src.business.word_manager import WordManager  # noqa: E402
from src.data.database import Database  # noqa: E402

_spec = importlib.util.spec_from_file_location('toeic_apply', ROOT / 'ai-agent' / 'scripts' / '토익단어적용.py')
apply_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(apply_mod)


@pytest.fixture()
def db_with_progress(tmp_path):
    db = Database(tmp_path / 'test.db')
    words = WordManager(db)
    old = words.add_word('summary', '요약본', 'noun', 'Please send me a summary.')
    words.add_word('custom', '직접 추가한 단어', 'noun', 'Added by an admin.')
    user = AuthManager(db).register('kim', 'pass1234', display_name='Kim')
    db.execute("INSERT INTO user_word_stats(user_id, word_id, weight, success_count, fail_count) VALUES(?,?,?,?,?)",
               (user['id'], old['id'], 1, 2, 1))
    return db, old['id']


ROWS = [('summary', '요약', 'noun', 'Please send me a summary.'),     # 뜻만 수정
        ('deadline', '마감 기한', 'noun', 'The deadline is Friday.')]  # 새 단어


def test_default_mode_adds_and_updates_but_keeps_user_progress(db_with_progress):
    db, summary_id = db_with_progress
    result = apply_mod.apply_upsert(db, ROWS)
    assert (result['added'], result['updated'], result['unchanged']) == (1, 1, 0)
    row = db.query_one("SELECT id, korean FROM words WHERE english = 'summary'")
    assert row['id'] == summary_id and row['korean'] == '요약'                       # id 유지, 뜻만 바뀜
    assert db.scalar("SELECT COUNT(*) FROM user_word_stats") == 1                     # 학습 기록 그대로
    assert db.scalar("SELECT COUNT(*) FROM words WHERE english = 'custom'") == 1      # CSV 에 없는 단어는 그대로
    assert db.scalar("SELECT COUNT(*) FROM words WHERE english = 'deadline'") == 1


def test_default_mode_is_idempotent_and_case_insensitive(db_with_progress):
    db, _ = db_with_progress
    apply_mod.apply_upsert(db, ROWS)
    again = apply_mod.apply_upsert(db, [('SUMMARY', '요약', 'noun', 'Please send me a summary.')] + ROWS[1:])
    assert (again['added'], again['updated']) == (0, 0)


def test_dry_run_changes_nothing(db_with_progress):
    db, _ = db_with_progress
    result = apply_mod.apply_upsert(db, ROWS, dry_run=True)
    assert (result['added'], result['updated']) == (1, 1)
    assert db.query_one("SELECT korean FROM words WHERE english = 'summary'")['korean'] == '요약본'
    assert db.scalar("SELECT COUNT(*) FROM words WHERE english = 'deadline'") == 0


def test_replace_warning_states_what_will_be_deleted(db_with_progress):
    db, _ = db_with_progress
    text = apply_mod.replace_warning(db)
    assert '경고' in text and '학습 통계: 1건' in text and '사용자 1명' in text and '배포' in text


@pytest.mark.parametrize('typed, expected', [('단어 교체', True), ('  단어 교체  ', True),
                                             ('yes', False), ('y', False), ('', False), ('단어교체 ', False)])
def test_replace_needs_exact_confirmation_phrase(typed, expected):
    assert apply_mod.confirm_replace(lambda _prompt: typed) is expected


def test_replace_confirmation_cancels_when_input_is_closed():
    def closed_stdin(_prompt):
        raise EOFError
    assert apply_mod.confirm_replace(closed_stdin) is False


def test_replace_refuses_without_confirmation_in_noninteractive_mode(db_with_progress, tmp_path, monkeypatch):
    db, _ = db_with_progress
    csv_path = tmp_path / 'w.csv'
    csv_path.write_text('english,korean,part_of_speech,example\nnew,새로운,adj,A new word.\n', encoding='utf-8')
    monkeypatch.setattr(sys.stdin, 'isatty', lambda: False)
    with pytest.raises(SystemExit) as exc:
        apply_mod.main(['--replace', '--csv', str(csv_path), '--db', str(db.db_path)])
    assert apply_mod.NONINTERACTIVE_FLAG in str(exc.value)
    assert db.scalar("SELECT COUNT(*) FROM words") == 2 and db.scalar("SELECT COUNT(*) FROM user_word_stats") == 1


def test_replace_dry_run_never_deletes(db_with_progress, tmp_path, capsys):
    db, _ = db_with_progress
    csv_path = tmp_path / 'w.csv'
    csv_path.write_text('english,korean,part_of_speech,example\nnew,새로운,adj,A new word.\n', encoding='utf-8')
    apply_mod.main(['--replace', '--dry-run', '--csv', str(csv_path), '--db', str(db.db_path)])
    assert '경고' in capsys.readouterr().out
    assert db.scalar("SELECT COUNT(*) FROM words") == 2 and db.scalar("SELECT COUNT(*) FROM user_word_stats") == 1


def test_apply_replace_keeps_accounts_and_logs(db_with_progress):
    db, _ = db_with_progress
    db.execute("INSERT INTO study_logs(user_id, date, words_count, correct_count, success_rate) VALUES(1,'2026-11-13',5,4,80)")
    removed = apply_mod.apply_replace(db, [('only', '하나뿐', 'adj', 'This is the only word.')])
    assert removed == 1 and db.scalar("SELECT COUNT(*) FROM words") == 1
    assert db.scalar("SELECT COUNT(*) FROM user_word_stats") == 0
    assert db.scalar("SELECT COUNT(*) FROM users") == 1 and db.scalar("SELECT COUNT(*) FROM study_logs") == 1


def test_backup_is_a_consistent_copy(db_with_progress, monkeypatch, tmp_path):
    db, _ = db_with_progress
    monkeypatch.setattr(apply_mod, 'PROJECT_ROOT', tmp_path)       # 실제 backups/ 를 건드리지 않게
    backup = apply_mod.make_backup(db.db_path, 'test')
    copy = Database(backup)
    assert copy.scalar("SELECT COUNT(*) FROM words") == 2 and copy.scalar("SELECT COUNT(*) FROM user_word_stats") == 1
