#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-13 - smart-voca - words_toeic.csv 의 토익 단어를 DB 에 반영한다 (기본: 추가 + 기존 단어 수정)
# 파일 위치: ai-agent/scripts/토익단어적용.py
"""사용법 (프로젝트 루트에서):
    python ai-agent/scripts/토익단어적용.py --dry-run    # 무엇이 바뀌는지만 보여준다 (DB 변경 없음)
    python ai-agent/scripts/토익단어적용.py              # 기본: 새 단어 추가 + 이미 있는 단어의 뜻·품사·예문 수정
    python ai-agent/scripts/토익단어적용.py --replace    # 위험: 기존 단어를 모두 지우고 교체 (경고 + 확인 입력 필요)

기본 동작은 단어 id 를 유지하므로 사용자의 학습 기록(단어별 통계)이 그대로 남는다.
단, CSV 에 있는 단어는 관리자 화면에서 고친 뜻·예문이 CSV 값으로 덮어써진다 (--dry-run 으로 먼저 확인).
CSV 에 없는 단어(관리자가 직접 추가한 단어 등)는 건드리지 않는다.
--replace 는 단어에 딸린 사용자별 학습 통계(user_word_stats)와 진행 중 시험(test_sessions)을 함께 지운다.
배포된 DB 에서는 쓰지 말 것. 계정과 학습·시험 요약 기록(study_logs, test_logs)은 남는다.
쓰기 전에는 backups/ 에 자동 백업(SQLite 백업 API, WAL 상태에서도 안전)을 만든다.
"""
import argparse
import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.database import Database  # noqa: E402

DEFAULT_CSV = Path(__file__).resolve().parent / 'words_toeic.csv'
CONFIRM_PHRASE = '단어 교체'
NONINTERACTIVE_FLAG = '--yes-delete-user-progress'


def read_rows(csv_path: Path):
    with open(csv_path, encoding='utf-8-sig', newline='') as fp:
        rows = list(csv.DictReader(fp))
    cleaned = []
    seen = set()
    for line_no, row in enumerate(rows, start=2):
        english, korean = (row.get('english') or '').strip(), (row.get('korean') or '').strip()
        if not english or not korean:
            sys.exit(f'{csv_path.name} {line_no}행: english/korean 이 비어 있습니다.')
        if len(english) > 100 or len(korean) > 200:
            sys.exit(f'{csv_path.name} {line_no}행: 길이 제한(영단어 100자, 뜻 200자) 초과')
        if english.lower() in seen:
            sys.exit(f'{csv_path.name} {line_no}행: 중복 영단어 {english}')
        seen.add(english.lower())
        cleaned.append((english, korean, (row.get('part_of_speech') or '').strip(), (row.get('example') or '').strip()))
    return cleaned


def make_backup(db_path: Path, label: str) -> Path:
    """SQLite 백업 API 로 일관된 사본을 만든다 (서버가 WAL 모드로 켜져 있어도 안전)."""
    backup_dir = PROJECT_ROOT / 'backups'          # .gitignore 대상
    backup_dir.mkdir(exist_ok=True)
    backup = backup_dir / f"smart_voca_{datetime.now():%y%m%d_%H%M%S}_{label}.db"
    src, dst = sqlite3.connect(str(db_path)), sqlite3.connect(str(backup))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return backup


# ---------------------------------------------------------------- 기본: 추가 + 수정
def plan_upsert(db: Database, rows):
    """(추가할 행, 수정할 행[(id, 새 값, 옛 값)], 그대로인 개수) 를 계산한다. DB 는 바꾸지 않는다."""
    existing = {r['english'].lower(): r for r in db.query(
        "SELECT id, english, korean, part_of_speech, example FROM words")}
    to_add, to_update, same = [], [], 0
    for english, korean, pos, example in rows:
        cur = existing.get(english.lower())
        if cur is None:
            to_add.append((english, korean, pos, example))
        elif (cur['korean'], cur['part_of_speech'], cur['example']) != (korean, pos, example):
            to_update.append((cur['id'], (korean, pos, example), cur))
        else:
            same += 1
    return to_add, to_update, same


def apply_upsert(db: Database, rows, dry_run: bool = False) -> dict:
    to_add, to_update, same = plan_upsert(db, rows)
    result = {'added': len(to_add), 'updated': len(to_update), 'unchanged': same,
              'changes': [(cur['english'], cur['korean'], new[0]) for _, new, cur in to_update]}
    if dry_run or not (to_add or to_update):
        return result
    with db.session() as conn:                     # 한 트랜잭션: 실패하면 전부 되돌린다
        conn.executemany("INSERT INTO words(english, korean, part_of_speech, example) VALUES(?,?,?,?)", to_add)
        conn.executemany("UPDATE words SET korean = ?, part_of_speech = ?, example = ? WHERE id = ?",
                         [(new[0], new[1], new[2], wid) for wid, new, _ in to_update])
    return result


# ---------------------------------------------------------------- 위험: 전체 교체
def replace_warning(db: Database) -> str:
    stats = db.scalar("SELECT COUNT(*) FROM user_word_stats")
    users = db.scalar("SELECT COUNT(DISTINCT user_id) FROM user_word_stats")
    sessions = db.scalar("SELECT COUNT(*) FROM test_sessions")
    words = db.scalar("SELECT COUNT(*) FROM words")
    return (
        "\n" + "!" * 64 + "\n"
        "  경고: --replace 는 기존 단어를 모두 삭제하고 CSV 로 바꿉니다.\n"
        f"  - 삭제되는 단어: {words}개\n"
        f"  - 함께 삭제되는 사용자별 학습 통계: {stats}건 (사용자 {users}명) / 진행 중 시험: {sessions}건\n"
        "  - 되돌릴 수 없습니다. (백업 파일로만 복구 가능)\n"
        "  - 이미 사용자가 쓰고 있는 DB(배포 후)에서는 쓰지 마세요.\n"
        "  - 단어만 고치려면 옵션 없이 실행하세요 (추가 + 수정, 학습 기록 유지).\n"
        + "!" * 64 + "\n")


def confirm_replace(input_fn=input) -> bool:
    try:
        answer = input_fn(f"계속하려면 '{CONFIRM_PHRASE}' 를 정확히 입력하세요 (그 외 입력은 취소): ")
    except EOFError:                  # 입력이 끊겼다(파이프·리다이렉트) = 확인하지 못했으므로 취소
        return False
    return answer.strip() == CONFIRM_PHRASE


def apply_replace(db: Database, rows) -> int:
    with db.session() as conn:                     # 한 트랜잭션: 실패하면 전부 되돌린다
        stats = conn.execute("SELECT COUNT(*) FROM user_word_stats").fetchone()[0]
        conn.execute("DELETE FROM test_sessions")
        conn.execute("DELETE FROM user_word_stats")
        conn.execute("DELETE FROM words")
        conn.executemany("INSERT INTO words(english, korean, part_of_speech, example) VALUES(?,?,?,?)", rows)
    return stats


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description='토익 단어 CSV 를 DB 에 반영 (기본: 추가 + 기존 단어 수정)')
    parser.add_argument('--csv', default=str(DEFAULT_CSV))
    parser.add_argument('--db', default=str(PROJECT_ROOT / 'data' / 'smart_voca.db'))
    parser.add_argument('--dry-run', action='store_true', help='DB 를 바꾸지 않고 변경 내용만 보여준다')
    parser.add_argument('--replace', action='store_true', help='위험: 기존 단어를 모두 지우고 교체 (학습 통계 삭제)')
    parser.add_argument(NONINTERACTIVE_FLAG, dest='yes_delete', action='store_true',
                        help='--replace 를 사람 입력 없이 실행할 때만 사용 (스크립트용)')
    args = parser.parse_args(argv)

    csv_path, db_path = Path(args.csv), Path(args.db)
    if not csv_path.exists():
        sys.exit(f'CSV 가 없습니다: {csv_path}')
    if not db_path.exists():
        sys.exit(f'DB 가 없습니다: {db_path}')
    rows = read_rows(csv_path)
    db = Database(db_path)
    before = db.scalar("SELECT COUNT(*) FROM words")
    print(f'CSV {len(rows)}개 / DB 현재 단어 {before}개 / DB: {db_path}')

    if args.replace:
        print(replace_warning(db))
        if args.dry_run:
            print('(--dry-run: 아무것도 삭제하지 않았습니다.)')
            return
        if sys.stdin.isatty():
            if not confirm_replace():
                sys.exit('취소했습니다. 아무것도 바뀌지 않았습니다.')
        elif not args.yes_delete:
            sys.exit(f'대화형 터미널이 아니라서 확인할 수 없습니다. 정말 필요하면 {NONINTERACTIVE_FLAG} 를 붙이세요.')
        print(f'백업: {make_backup(db_path, "교체전")}')
        stats = apply_replace(db, rows)
        print(f'교체 완료: 삭제된 단어별 통계 {stats}건')
    else:
        result = apply_upsert(db, rows, dry_run=True)          # 먼저 계획만 계산
        if not args.dry_run and (result['added'] or result['updated']):
            print(f'백업: {make_backup(db_path, "단어수정전")}')   # 쓰기 전에 백업
            result = apply_upsert(db, rows)
        for english, old, new in result['changes'][:20]:
            print(f'  수정: {english}  {old} -> {new}')
        if len(result['changes']) > 20:
            print(f"  … 외 {len(result['changes']) - 20}개 수정")
        print(f"{'(미리보기) ' if args.dry_run else ''}추가 {result['added']}개, 수정 {result['updated']}개, "
              f"그대로 {result['unchanged']}개 (학습 기록은 유지)")

    print(f'DB 단어 수: {before} -> {db.scalar("SELECT COUNT(*) FROM words")}')


if __name__ == '__main__':
    main()
