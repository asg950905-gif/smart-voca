#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-13 - smart-voca - words_toeic.csv 의 토익 단어를 DB 에 넣는다 (추가 또는 전체 교체)
# 파일 위치: ai-agent/scripts/토익단어적용.py
"""사용법 (프로젝트 루트에서):
    python ai-agent/scripts/토익단어적용.py              # 기존 단어는 두고, 새 단어만 추가 (중복은 건너뜀)
    python ai-agent/scripts/토익단어적용.py --replace    # 기존 단어를 모두 지우고 CSV 로 교체 (자동 백업)
`시연데이터생성.py --reset` 으로 DB 가 초기화된 뒤에도 같은 명령으로 다시 넣을 수 있다.
--replace 는 단어에 딸린 사용자별 학습 통계(user_word_stats)와 진행 중 시험(test_sessions)도 함께 지운다.
계정과 학습·시험 요약 기록(study_logs, test_logs)은 그대로 둔다.
"""
import argparse
import csv
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.database import Database          # noqa: E402
from src.business.word_manager import WordManager  # noqa: E402

DEFAULT_CSV = Path(__file__).resolve().parent / 'words_toeic.csv'


def read_rows(csv_path: Path):
    with open(csv_path, encoding='utf-8-sig', newline='') as fp:
        rows = list(csv.DictReader(fp))
    for line_no, row in enumerate(rows, start=2):
        if not (row.get('english') or '').strip() or not (row.get('korean') or '').strip():
            sys.exit(f'{csv_path.name} {line_no}행: english/korean 이 비어 있습니다.')
        if len(row['english']) > 100 or len(row['korean']) > 200:
            sys.exit(f'{csv_path.name} {line_no}행: 길이 제한(영단어 100자, 뜻 200자) 초과')
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description='토익 단어 CSV 를 DB 에 적용')
    parser.add_argument('--csv', default=str(DEFAULT_CSV))
    parser.add_argument('--db', default=str(PROJECT_ROOT / 'data' / 'smart_voca.db'))
    parser.add_argument('--replace', action='store_true', help='기존 단어를 모두 지우고 교체')
    args = parser.parse_args()

    csv_path, db_path = Path(args.csv), Path(args.db)
    if not csv_path.exists():
        sys.exit(f'CSV 가 없습니다: {csv_path}')
    rows = read_rows(csv_path)
    db = Database(db_path)
    before = db.scalar("SELECT COUNT(*) FROM words")
    print(f'CSV {len(rows)}개 / DB 현재 단어 {before}개')

    if not args.replace:
        result = WordManager(db).import_csv(csv_path.read_bytes())
        print(f"추가 {result['added']}개, 건너뜀(중복) {result['skipped']}개")
    else:
        backup_dir = PROJECT_ROOT / 'backups'      # .gitignore 대상
        backup_dir.mkdir(exist_ok=True)
        backup = backup_dir / f"smart_voca_{datetime.now():%y%m%d_%H%M%S}_교체전.db"
        shutil.copy2(db_path, backup)
        print(f'백업: {backup}')
        with db.session() as conn:                 # 한 트랜잭션: 실패하면 전부 되돌린다
            stats = conn.execute("SELECT COUNT(*) FROM user_word_stats").fetchone()[0]
            conn.execute("DELETE FROM test_sessions")
            conn.execute("DELETE FROM user_word_stats")
            conn.execute("DELETE FROM words")
            conn.executemany(
                "INSERT INTO words(english, korean, part_of_speech, example) VALUES(?,?,?,?)",
                [(r['english'].strip(), r['korean'].strip(), (r.get('part_of_speech') or '').strip(),
                  (r.get('example') or '').strip()) for r in rows])
        print(f'교체 완료: 삭제된 단어별 통계 {stats}건')

    after = db.scalar("SELECT COUNT(*) FROM words")
    print(f'DB 단어 수: {before} -> {after}')


if __name__ == '__main__':
    main()
