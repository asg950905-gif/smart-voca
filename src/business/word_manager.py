#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - 단어 관리 (SQLite 기반 CRUD, CSV 가져오기/내보내기)
# 파일 위치: src/business/word_manager.py

import csv
import io
import logging
from typing import Dict, List, Optional, Tuple
from src.data.database import Database

logger = logging.getLogger(__name__)

PAGE_SIZE_DEFAULT = 20


class WordError(Exception):
    """사용자에게 보여줘도 되는 단어 검증 오류"""


class WordManager:
    """공용 단어장(관리자가 관리)과 사용자별 학습 통계 조회"""

    def __init__(self, db: Database):
        self.db = db

    # ---------- 관리자: CRUD ----------
    def count(self) -> int:
        return self.db.scalar("SELECT COUNT(*) FROM words")

    def list_words(self, keyword: str = '', page: int = 1, page_size: int = PAGE_SIZE_DEFAULT) -> Dict:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        like = f"%{keyword.strip()}%"
        total = self.db.scalar(
            "SELECT COUNT(*) FROM words WHERE english LIKE ? OR korean LIKE ?", (like, like)
        )
        items = self.db.query(
            "SELECT * FROM words WHERE english LIKE ? OR korean LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?",
            (like, like, page_size, (page - 1) * page_size),
        )
        return {'items': items, 'total': total, 'page': page, 'page_size': page_size,
                'pages': max(1, -(-total // page_size))}

    def get_word(self, word_id: int) -> Optional[Dict]:
        return self.db.query_one("SELECT * FROM words WHERE id = ?", (word_id,))

    def add_word(self, english: str, korean: str, part_of_speech: str = '', example: str = '') -> Dict:
        english, korean = self._validate(english, korean)
        if self.db.query_one("SELECT 1 FROM words WHERE english = ? COLLATE NOCASE", (english,)):
            raise WordError(f"이미 등록된 단어입니다: {english}")
        word_id = self.db.execute(
            "INSERT INTO words(english, korean, part_of_speech, example) VALUES(?, ?, ?, ?)",
            (english, korean, (part_of_speech or '').strip(), (example or '').strip()),
        )
        return self.get_word(word_id)

    def update_word(self, word_id: int, english: str, korean: str,
                    part_of_speech: str = '', example: str = '') -> Dict:
        english, korean = self._validate(english, korean)
        if not self.get_word(word_id):
            raise WordError('존재하지 않는 단어입니다.')
        if self.db.query_one("SELECT 1 FROM words WHERE english = ? COLLATE NOCASE AND id != ?", (english, word_id)):
            raise WordError(f"이미 등록된 단어입니다: {english}")
        self.db.execute(
            "UPDATE words SET english = ?, korean = ?, part_of_speech = ?, example = ? WHERE id = ?",
            (english, korean, (part_of_speech or '').strip(), (example or '').strip(), word_id),
        )
        return self.get_word(word_id)

    def delete_word(self, word_id: int) -> None:
        if self.db.execute_rowcount("DELETE FROM words WHERE id = ?", (word_id,)) == 0:
            raise WordError('존재하지 않는 단어입니다.')

    @staticmethod
    def _validate(english: str, korean: str) -> Tuple[str, str]:
        english, korean = (english or '').strip(), (korean or '').strip()
        if not english or not korean:
            raise WordError('영단어와 뜻은 필수입니다.')
        if len(english) > 100 or len(korean) > 200:
            raise WordError('영단어는 100자, 뜻은 200자 이내로 입력하세요.')
        return english, korean

    # ---------- CSV 가져오기/내보내기 ----------
    def import_csv(self, stream: bytes) -> Dict:
        """CSV(헤더: english,korean[,part_of_speech,example])를 가져온다. 중복 단어는 건너뛴다."""
        try:
            text = stream.decode('utf-8-sig')  # 엑셀이 저장한 BOM 도 허용
        except UnicodeDecodeError:
            try:
                text = stream.decode('cp949')  # 한글 윈도우 엑셀 CSV
            except UnicodeDecodeError:
                raise WordError('CSV 인코딩을 읽을 수 없습니다. UTF-8로 저장해 주세요.')

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or 'english' not in reader.fieldnames or 'korean' not in reader.fieldnames:
            raise WordError("CSV 첫 줄에 'english', 'korean' 헤더가 필요합니다.")

        added, skipped, errors = 0, 0, []
        for line_no, row in enumerate(reader, start=2):
            try:
                self.add_word(row.get('english'), row.get('korean'),
                              row.get('part_of_speech', ''), row.get('example', ''))
                added += 1
            except WordError as e:
                skipped += 1
                if len(errors) < 5:
                    errors.append(f"{line_no}행: {e}")
        logger.info(f"CSV 가져오기: 추가 {added}, 건너뜀 {skipped}")
        return {'added': added, 'skipped': skipped, 'errors': errors}

    def export_csv(self) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['english', 'korean', 'part_of_speech', 'example'])
        for w in self.db.query("SELECT english, korean, part_of_speech, example FROM words ORDER BY id"):
            writer.writerow([w['english'], w['korean'], w['part_of_speech'], w['example']])
        return '﻿' + output.getvalue()  # BOM: 엑셀에서 한글이 깨지지 않게 한다

    # ---------- 사용자: 학습 결과 반영 ----------
    def update_user_stat(self, conn, user_id: int, word_id: int, success: bool, today: str) -> None:
        """한 단어의 사용자별 통계를 갱신한다. 정답이면 가중치 감소, 오답이면 증가."""
        conn.execute(
            """INSERT INTO user_word_stats(user_id, word_id, weight, success_count, fail_count, last_studied)
               VALUES(?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id, word_id) DO UPDATE SET
                 weight = CASE WHEN ? THEN MAX(0, weight - 1) ELSE weight + 1 END,
                 success_count = success_count + ?,
                 fail_count = fail_count + ?,
                 last_studied = excluded.last_studied""",
            (user_id, word_id, 0 if success else 1, 1 if success else 0, 0 if success else 1, today,
             1 if success else 0, 1 if success else 0, 0 if success else 1),
        )
