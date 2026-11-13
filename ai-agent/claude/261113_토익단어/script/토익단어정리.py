#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-13 - smart-voca - 토익 단어 묶음(batch/*.txt)을 검증·중복 제거해 CSV 로 만든다
# 파일 위치: ai-agent/claude/261113_토익단어/script/토익단어정리.py
"""사용법:
    python 토익단어정리.py            # 보고서만 출력 (파일 쓰지 않음)
    python 토익단어정리.py --write    # 검증을 통과하면 ai-agent/scripts/토익단어.csv 생성
"""
import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK_DIR = HERE.parent
BATCH_DIR = WORK_DIR / 'batch'
OUT_CSV = WORK_DIR.parent.parent / 'scripts' / 'words_toeic.csv'
OVERRIDE_FILES = [WORK_DIR / '수정목록.txt', WORK_DIR / '예문수정.txt']   # 영단어|뜻|품사|예문 (빈 칸은 원래 값 유지)
DROP_FILE = WORK_DIR / '제외목록.txt'       # 한 줄에 영단어 하나

# 띄어쓰기가 있는 표현은 실제 토익에 자주 나오는 관용 표현만 허용한다
PHRASE_ALLOW = {
    'check in', 'check out', 'fill out', 'sign up', 'log in', 'log out', 'carry out', 'real estate',
    'business trip', 'grand opening', 'market share', 'exchange rate', 'stock market', 'trade show',
    'job description', 'conference call', 'conference room', 'break even', 'in bulk', 'free of charge',
    'sick leave', 'fiscal year', 'terms and conditions', 'wake-up call', 'focus group', 'intellectual property',
    'shelf life', 'speed limit', 'parking lot', 'quality control', 'assembly line', 'raw material',
    'air conditioner', 'single room', 'double room', 'target market', 'hazardous waste', 'interest rate',
    'stock up', 'put through',
}
ALLOWED_POS = {'noun', 'verb', 'adj', 'adv', 'prep', 'conj'}
WORD_BOUNDARY = chr(92) + 'b'   # 정규식 \b (단어 경계). 앱의 빈칸 문제도 이 방식으로 단어를 찾는다


def load_lines(path: Path):
    rows = []
    for no, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
        raw = raw.strip()
        if not raw or raw.startswith('#'):
            continue
        parts = raw.split('|')
        if len(parts) != 4:
            print(f'[형식오류] {path.name}:{no} 필드가 {len(parts)}개: {raw[:50]}')
            continue
        rows.append(tuple(p.strip() for p in parts) + (f'{path.name}:{no}',))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()

    drop = set()
    if DROP_FILE.exists():
        drop = {l.strip().lower() for l in DROP_FILE.read_text(encoding='utf-8').splitlines() if l.strip()}
    overrides = {}   # 영단어(소문자) -> [뜻, 품사, 예문] ; 빈 칸이면 원래 값 유지, 여러 파일의 수정은 필드별로 합친다

    def add_override(word, ko='', pos='', ex=''):
        cur = overrides.setdefault(word.lower(), ['', '', ''])
        for i, value in enumerate((ko, pos, ex)):
            if value:
                cur[i] = value

    for of in OVERRIDE_FILES:
        if not of.exists():
            continue
        for no, line in enumerate(of.read_text(encoding='utf-8').splitlines(), start=1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) == 2:        # 영단어|뜻 -> 뜻만 교체
                add_override(parts[0], ko=parts[1])
            elif len(parts) == 4:      # 영단어|뜻|품사|예문 (빈 칸은 유지)
                add_override(parts[0], parts[1], parts[2], parts[3])
            else:
                print(f'[수정목록 형식오류] {of.name} {no}행: {line[:40]}')

    raw_rows = []
    for f in sorted(BATCH_DIR.glob('*.txt')):
        raw_rows.extend(load_lines(f))
    print(f'원본 줄 수: {len(raw_rows)}')

    seen, kept = {}, []
    dropped_phrase, dropped_dup, dropped_manual, bad_pos = [], [], [], []
    for en, ko, pos, ex, src in raw_rows:
        key = en.lower()
        if key in overrides:
            o_ko, o_pos, o_ex = overrides[key]
            ko, pos, ex = o_ko or ko, o_pos or pos, o_ex or ex
        if key in drop:
            dropped_manual.append(en)
            continue
        if ' ' in en and key not in PHRASE_ALLOW:
            dropped_phrase.append(en)
            continue
        if key in seen:
            dropped_dup.append(en)
            continue
        if pos not in ALLOWED_POS:
            bad_pos.append((en, pos))
        seen[key] = True
        kept.append([en, ko, pos, ex, src])

    print(f'구 표현 제외: {len(dropped_phrase)}개 | 중복 제거: {len(dropped_dup)}개 | 수동 제외: {len(dropped_manual)}개')
    print(f'남은 단어: {len(kept)}개')
    if bad_pos:
        print('[품사 확인 필요]', bad_pos[:10])

    # 예문에 표제어(대소문자 무시)가 그대로 들어 있어야 빈칸 문제가 만들어진다
    no_head = [(en, ex) for en, ko, pos, ex, src in kept if not re.search(WORD_BOUNDARY + re.escape(en) + WORD_BOUNDARY, ex, re.IGNORECASE)]   # test_engine._blank_sentence 와 같은 기준
    print(f'예문에 표제어가 없는 항목: {len(no_head)}개')
    for en, ex in no_head[:60]:
        print(f'   {en} :: {ex}')

    # 뜻이 같은 단어가 있으면 4지선다 보기가 모호해진다
    by_korean = defaultdict(list)
    for en, ko, pos, ex, src in kept:
        by_korean[ko].append(en)
    dup_ko = {k: v for k, v in by_korean.items() if len(v) > 1}
    print(f'뜻이 겹치는 그룹: {len(dup_ko)}개 (영단어 {sum(len(v) for v in dup_ko.values())}개)')
    for k, v in sorted(dup_ko.items()):
        print('   ' + k + ' <- ' + ', '.join(v))

    long_ko = [(en, ko) for en, ko, *_ in kept if len(ko) > 20]
    if long_ko:
        print('[뜻이 20자 초과]', long_ko[:10])

    problems = len(no_head) + len(dup_ko) + len(bad_pos)
    if args.write:
        if problems:
            sys.exit(f'\n문제 {problems}건이 남아 있어 CSV 를 만들지 않았습니다.')
        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT_CSV, 'w', encoding='utf-8-sig', newline='') as fp:
            w = csv.writer(fp)
            w.writerow(['english', 'korean', 'part_of_speech', 'example'])
            for en, ko, pos, ex, _ in kept:
                w.writerow([en, ko, pos, ex])
        print(f'\n저장: {OUT_CSV} ({len(kept)}개)')


if __name__ == '__main__':
    main()
