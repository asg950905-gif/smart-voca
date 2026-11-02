# business — 비즈니스 로직 계층

**파일 위치**: `src/business/README.md`
**작성일**: 2026-11-02
**버전**: v1.0
**설명**: 화면·HTTP 를 모르는 순수 업무 규칙. 계정, 단어, 학습, 시험, 통계를 담당한다.

---

## 파일
| 파일 | 클래스 | 하는 일 |
| :--- | :--- | :--- |
| `auth_manager.py` | `AuthManager` | 가입(검증), 로그인(비밀번호 해시 비교), 사용자 목록, 역할 변경, 활성/비활성, 비밀번호 재설정, 삭제 |
| `word_manager.py` | `WordManager` | 단어 목록(검색·페이징), 추가/수정/삭제(중복 검사), CSV 가져오기·내보내기, 사용자별 통계 갱신 |
| `study_manager.py` | `StudyManager` | 오늘의 단어 선택, 학습 결과 저장, 진도·연속 학습일 계산 |
| `test_engine.py` | `TestEngine` | 시험 출제(4지선다·OX·단답), 채점, 종료 시 기록 저장 |
| `report_generator.py` | `ReportGenerator` | 사용자 개인 통계·차트 데이터, 관리자 전체 통계 |

## 핵심 로직과 이유
**1. 오늘의 단어 선택 (`StudyManager.get_daily_words`)**
`ORDER BY 오답 가중치 DESC → 아직 안 본 단어 → 오래전에 본 단어 → 무작위`.
틀린 단어를 더 자주 복습시키는 간단한 간격 반복 원리다. 정답이면 가중치 −1(최소 0), 오답이면 +1 (`WordManager.update_user_stat`).

**2. 시험 (`TestEngine`)** — 상태를 서버 메모리가 아니라 `test_sessions` 테이블(JSON)에 저장한다.
- 이유: 기존 코드는 전역 변수 하나에 시험 상태를 두어, 두 사람이 동시에 응시하면 문제가 섞였다. 사용자별로 DB 에 두면 격리된다.
- **정답은 서버에만 둔다.** `get_current_problem` 은 정답을 빼고 보내고, 채점(`grade_answer`) 후에만 알려준다. 브라우저 개발자도구로 정답을 훔쳐볼 수 없다.
- 4지선다는 단어가 4개 미만이면 OX → 단답 순으로 형식을 낮춘다(보기를 만들 수 없으므로).

**3. 트랜잭션** — `record_study`, `finish_test` 는 `db.session()` 한 번으로 "단어 통계 + 로그"를 묶는다. 중간에 실패하면 모두 취소된다.

**4. 검증과 오류** — 사용자에게 보여줘도 되는 오류는 `AuthError / WordError / TestError` 로 분리하고, 라우트가 400 으로 변환한다.
예상치 못한 오류는 일반 500 으로 처리해 내부 정보가 새지 않게 한다.

**5. 인증 (`AuthManager`)**
- 비밀번호는 `werkzeug.security.generate_password_hash` 로 **해시 저장**(원문 저장 안 함).
- 로그인 실패 시 "아이디 없음/비밀번호 틀림"을 구분하지 않는다 (아이디 존재 여부 노출 방지).
- 가입은 항상 `role='user'`. 관리자 승격은 관리자만 가능하고 **자기 자신의 역할 변경·삭제·비활성화는 막는다** (관리자가 0명이 되는 사고 방지).

## 데이터 흐름 예 (학습 완료)
`브라우저 → POST /api/study/record → user_routes → StudyManager.record_study → db.session(): user_word_stats upsert + study_logs insert → JSON 응답`

## 예상 질문
- **Q. 왜 계층을 나눴나?** 로직(business)을 HTTP 와 분리하면 화면 없이도 테스트할 수 있다. 실제로 `tests/` 가 Flask 테스트 클라이언트로 전 경로를 검증한다.
- **Q. 학습 알고리즘의 한계?** 단순 가중치라 망각 곡선(SM-2 등)은 반영하지 않았다. 향후 과제.
