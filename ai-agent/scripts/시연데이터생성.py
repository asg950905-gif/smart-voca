#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - 시연용 샘플 데이터 생성 (계정·토익 단어(words_toeic.csv)·최근 14일 학습/시험 기록)  [2026-11-13 단어를 CSV 기반으로 변경]
# 파일 위치: ai-agent/scripts/시연데이터생성.py
#
# 사용법:  python ai-agent/scripts/시연데이터생성.py --reset
#   --reset : 기존 DB(data/smart_voca.db)를 지우고 새로 만든다 (실제 사용 데이터가 있다면 사용 금지!)
# 주의: 시연 전용 비밀번호가 출력된다. 11/16 배포·사용자 공유 전에는 반드시 --reset 없이 새 DB 로 시작하거나
#       관리자 비밀번호를 바꾼다.

import argparse
import csv
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.database import Database  # noqa: E402
from src.business.auth_manager import AuthManager  # noqa: E402
from src.business.word_manager import WordManager  # noqa: E402

ADMIN = ('admin', 'admin1234', '관리자')
DEMO_USERS = [  # (아이디, 비밀번호, 표시이름, 학습 성향: 기본 정답률)
    ('minsu', 'demo1234', '김민수', 0.82),
    ('jiyoung', 'demo1234', '이지영', 0.68),
    ('hojun', 'demo1234', '박호준', 0.55),
    ('seoyun', 'demo1234', '정서윤', 0.74),   # 관리자 대시보드 '학습 랭킹 TOP 5' 가 꽉 차도록 2명 추가 (2026-11-09)
    ('taeho', 'demo1234', '최태호', 0.62),
]

WORDS_CSV = Path(__file__).resolve().parent / 'words_toeic.csv'   # 단어 원본 (english,korean,part_of_speech,example)
HISTORY_BASE_POOL = 120   # 시연 계정들이 공통으로 학습한 단어 수 (관리자 '자주 틀리는 단어' 가 겹쳐서 쌓이도록)
HISTORY_USER_POOL = 80    # 계정마다 이 중 일부만 학습: 단어가 2천 개라 무작위로 뽑으면 같은 단어를 3번 못 만나 '마스터'가 0이 된다
HISTORY_WORDS_PER_DAY = 20


def build_words(wm: WordManager) -> int:
    if not WORDS_CSV.exists():
        sys.exit(f'단어 CSV 가 없습니다: {WORDS_CSV}')
    with open(WORDS_CSV, encoding='utf-8-sig', newline='') as fp:
        rows = list(csv.DictReader(fp))
    for row in rows:
        wm.add_word(row['english'], row['korean'], row.get('part_of_speech', ''), row.get('example', ''))
    return len(rows)


def build_history(db: Database, user_id: int, accuracy: float, rng: random.Random, word_ids: list) -> None:
    """최근 14일 중 일부 날짜에 학습·시험 기록을 만든다 (오늘 포함하여 연속 학습일이 보이게)."""
    today = datetime.now().date()
    active_days = [d for d in range(14) if d < 4 or rng.random() < accuracy]  # 최근 4일은 반드시 학습
    with db.session() as conn:
        for offset in sorted(active_days, reverse=True):
            day = (today - timedelta(days=offset)).strftime('%Y-%m-%d')
            picked = rng.sample(word_ids, min(HISTORY_WORDS_PER_DAY, len(word_ids)))
            correct = 0
            for wid in picked:
                ok = rng.random() < accuracy
                correct += ok
                conn.execute(
                    """INSERT INTO user_word_stats(user_id, word_id, weight, success_count, fail_count, last_studied)
                       VALUES(?,?,?,?,?,?) ON CONFLICT(user_id, word_id) DO UPDATE SET
                       weight = MAX(0, weight + ?), success_count = success_count + ?,
                       fail_count = fail_count + ?, last_studied = excluded.last_studied""",
                    (user_id, wid, 0 if ok else 1, 1 if ok else 0, 0 if ok else 1, day,
                     -1 if ok else 1, 1 if ok else 0, 0 if ok else 1))
            conn.execute("INSERT INTO study_logs(user_id, date, words_count, correct_count, success_rate) VALUES(?,?,?,?,?)",
                         (user_id, day, len(picked), correct, round(correct / len(picked) * 100, 1)))
            if rng.random() < 0.6:
                total = rng.choice([10, 10, 20])
                right = min(total, max(0, round(total * (accuracy + rng.uniform(-0.12, 0.12)))))
                conn.execute(
                    "INSERT INTO test_logs(user_id, date, mode, format, total_problems, correct_answers, score) VALUES(?,?,?,?,?,?,?)",
                    (user_id, day, '혼합', '혼합', total, right, round(right / total * 100, 1)))


def main() -> None:
    parser = argparse.ArgumentParser(description='smart-voca 시연 데이터 생성')
    parser.add_argument('--reset', action='store_true', help='기존 DB 를 삭제하고 새로 만든다')
    parser.add_argument('--data-dir', default=str(PROJECT_ROOT / 'data'))
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    db_file = data_dir / 'smart_voca.db'
    if db_file.exists():
        if not args.reset:
            sys.exit(f'이미 DB 가 있습니다: {db_file}\n덮어쓰려면 --reset 을 붙이세요 (기존 데이터가 삭제됩니다).')
        for suffix in ('', '-wal', '-shm'):
            Path(str(db_file) + suffix).unlink(missing_ok=True)

    db = Database(db_file)
    auth, words = AuthManager(db), WordManager(db)
    auth.register(ADMIN[0], ADMIN[1], display_name=ADMIN[2], role='admin')
    n_words = build_words(words)
    rng = random.Random(20261113)  # 고정 시드: 시연할 때마다 같은 화면이 나오도록
    all_ids = [r['id'] for r in db.query("SELECT id FROM words ORDER BY id")]
    base_pool = rng.sample(all_ids, min(HISTORY_BASE_POOL, len(all_ids)))
    for username, password, name, accuracy in DEMO_USERS:
        user = auth.register(username, password, display_name=name)
        user_pool = rng.sample(base_pool, min(HISTORY_USER_POOL, len(base_pool)))
        build_history(db, user['id'], accuracy, rng, user_pool)

    print(f'시연 데이터 생성 완료 (단어 {n_words}개, 사용자 {len(DEMO_USERS)}명)')
    print(f'  관리자  : {ADMIN[0]} / {ADMIN[1]}')
    for username, password, name, _ in DEMO_USERS:
        print(f'  사용자  : {username} / {password}  ({name})')


if __name__ == '__main__':
    main()
