#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 2026-11-02 - smart-voca - SQLite 데이터베이스 계층 (스키마·접속·질의 헬퍼)
# 파일 위치: src/data/database.py

import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

# 스키마: 사용자별 학습 상태를 분리해 다중 사용자 동시 접속에서도 기록이 섞이지 않게 한다.
SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    display_name  TEXT    NOT NULL DEFAULT '',
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    active        INTEGER NOT NULL DEFAULT 1,
    daily_target  INTEGER NOT NULL DEFAULT 10,
    theme         TEXT    NOT NULL DEFAULT 'system',
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS words (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    english        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    korean         TEXT NOT NULL,
    part_of_speech TEXT NOT NULL DEFAULT '',
    example        TEXT NOT NULL DEFAULT '',
    created_at     TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS user_word_stats (
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    word_id       INTEGER NOT NULL REFERENCES words(id) ON DELETE CASCADE,
    weight        INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    fail_count    INTEGER NOT NULL DEFAULT 0,
    last_studied  TEXT,
    PRIMARY KEY (user_id, word_id)
);
CREATE TABLE IF NOT EXISTS study_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date          TEXT    NOT NULL,
    words_count   INTEGER NOT NULL,
    correct_count INTEGER NOT NULL,
    success_rate  REAL    NOT NULL,
    duration      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS test_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date            TEXT    NOT NULL,
    mode            TEXT    NOT NULL,
    format          TEXT    NOT NULL,
    total_problems  INTEGER NOT NULL,
    correct_answers INTEGER NOT NULL,
    score           REAL    NOT NULL
);
CREATE TABLE IF NOT EXISTS test_sessions (
    user_id    INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    state_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_study_logs_user_date ON study_logs(user_id, date);
CREATE INDEX IF NOT EXISTS idx_test_logs_user_date  ON test_logs(user_id, date);
"""


class Database:
    """SQLite 접속·질의 헬퍼. 요청마다 짧게 연결을 열고 닫아 스레드 문제를 피한다."""

    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")  # CASCADE 삭제를 쓰려면 연결마다 켜야 한다
        return conn

    @contextmanager
    def session(self):
        """트랜잭션 단위. 정상 종료 시 commit, 예외 시 rollback."""
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.session() as conn:
            conn.execute("PRAGMA journal_mode = WAL")  # 읽기/쓰기 동시성 향상
            conn.executescript(SCHEMA)
        logger.info(f"DB 준비 완료: {self.db_path}")

    def query(self, sql: str, params: Iterable[Any] = ()) -> List[Dict]:
        with self.session() as conn:
            return [dict(row) for row in conn.execute(sql, tuple(params)).fetchall()]

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> Optional[Dict]:
        with self.session() as conn:
            row = conn.execute(sql, tuple(params)).fetchone()
            return dict(row) if row else None

    def scalar(self, sql: str, params: Iterable[Any] = (), default: Any = 0) -> Any:
        row = self.query_one(sql, params)
        if not row:
            return default
        value = next(iter(row.values()))
        return default if value is None else value

    def execute(self, sql: str, params: Iterable[Any] = ()) -> int:
        """단일 쓰기. 새 행의 id(INSERT) 또는 영향 행 수를 반환하지는 않고 lastrowid 를 돌려준다."""
        with self.session() as conn:
            return conn.execute(sql, tuple(params)).lastrowid

    def execute_rowcount(self, sql: str, params: Iterable[Any] = ()) -> int:
        with self.session() as conn:
            return conn.execute(sql, tuple(params)).rowcount

    # ---- 전역 설정 (app_settings) ----
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        row = self.query_one("SELECT value FROM app_settings WHERE key = ?", (key,))
        return row['value'] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.execute(
            "INSERT INTO app_settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, str(value)),
        )
