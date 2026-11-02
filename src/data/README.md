# data — 데이터 계층 (SQLite)

**파일 위치**: `src/data/README.md`
**작성일**: 2026-11-02
**버전**: v1.0
**설명**: DB 접속·스키마를 한곳에 모은 모듈. 위쪽 계층(business)은 SQL 접속 방법을 몰라도 된다.

---

## 파일
| 파일 | 역할 |
| :--- | :--- |
| `database.py` | `Database` 클래스(접속·트랜잭션·질의 헬퍼)와 테이블 정의 `SCHEMA` |

## 테이블 7개
| 테이블 | 용도 | 핵심 컬럼 |
| :--- | :--- | :--- |
| `users` | 계정 | `username`(UNIQUE), `password_hash`, `role`(user/admin), `active`, `daily_target`, `theme` |
| `words` | **공용** 단어장 (관리자가 관리) | `english`(UNIQUE, 대소문자 무시), `korean`, `part_of_speech`, `example` |
| `user_word_stats` | **사용자별** 단어 학습 상태 | PK(`user_id`,`word_id`), `weight`, `success_count`, `fail_count`, `last_studied` |
| `study_logs` | 학습 기록 | `user_id`, `date`, `words_count`, `correct_count`, `success_rate` |
| `test_logs` | 시험 기록 | `user_id`, `date`, `mode`, `format`, `score` |
| `test_sessions` | 진행 중인 시험(사용자당 1개) | `user_id`(PK), `state_json` |
| `app_settings` | 관리자 전역 설정 | `key`, `value` |

관계: `users` 1 — N `user_word_stats / study_logs / test_logs / test_sessions`, `words` 1 — N `user_word_stats`.
사용자나 단어를 지우면 관련 기록이 `ON DELETE CASCADE` 로 함께 삭제된다.

## 설계 결정과 이유
- **왜 SQLite?** (ADR-001) CSV/JSON 은 파일 하나를 여러 요청이 동시에 덮어써서 사용자 기록이 섞이고, 사용자별·전체 통계 집계가 불편하다.
  SQLite 는 파이썬 표준 `sqlite3` 만으로 쓸 수 있어 **추가 설치가 없고**, 파일 하나라 백업·시연 환경 이동이 쉽다.
  대안인 PostgreSQL 등 서버형 DB 는 이번 규모(소규모 팀 테스트)에는 설치·운영 부담이 더 크다.
- **왜 요청마다 연결을 열고 닫나?** SQLite 연결은 스레드 간 공유가 안 된다. 요청마다 짧게 열고 닫으면 Flask 개발 서버의 멀티스레드에서도 안전하다.
- **왜 `session()` 컨텍스트 매니저?** 정상 종료면 commit, 예외면 rollback. 학습 결과처럼 "단어 통계 + 로그"를 **한 번에 성공하거나 한 번에 실패**하게 묶기 위해서다.
- **왜 `PRAGMA foreign_keys = ON` 을 매 연결마다?** SQLite 는 기본값이 꺼짐이라, 켜야 CASCADE 삭제가 동작한다. 연결마다 설정해야 한다.
- **왜 WAL 모드?** 읽는 쪽이 쓰는 쪽을 막지 않아 동시 접속에 유리하다.
- **SQL 은 항상 `?` 자리표시자로 값을 전달** → SQL 인젝션 방지. 문자열 이어붙이기 금지.

## 알아둘 점
- `CREATE TABLE IF NOT EXISTS` 라서 **기존 DB 의 컬럼은 자동으로 바뀌지 않는다.** 스키마를 바꾸면 시연 DB 는 `--reset` 으로 재생성하고, 배포 DB 는 마이그레이션이 필요하다. (향후 과제)
- DB 파일 `data/smart_voca.db` 와 `data/secret_key.txt` 는 `.gitignore` 대상이다 (PUBLIC 저장소).

## 예상 질문
- **Q. 동시에 두 사람이 쓰면?** 사용자별 상태를 모두 DB 에 두었고, 자동 테스트(`test_users_data_is_isolated`)로 격리를 검증했다.
- **Q. 규모가 커지면?** 접근 코드가 `Database` 한 곳에 모여 있어 서버형 DB 로 바꿀 때 수정 범위가 작다. 다만 SQLite 특유 문법(`ON CONFLICT`, `RANDOM()`)은 점검이 필요하다.
