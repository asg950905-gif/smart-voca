# web — 웹 계층 (라우트·보안)

**파일 위치**: `src/web/README.md`
**작성일**: 2026-11-02
**버전**: v1.0
**설명**: HTTP 요청을 받아 business 를 호출하고 응답을 만든다. 권한 검사와 웹 보안이 여기에 있다.

---

## 파일
| 파일 | 내용 |
| :--- | :--- |
| `auth_routes.py` | `/login`, `/register`, `/logout` (Blueprint `auth`) |
| `user_routes.py` | 사용자 화면(`/`, `/study`, `/test`, `/report`, `/settings`)과 `/api/study·test·report·settings` (Blueprint `user`) |
| `admin_routes.py` | 관리자 화면 `/admin/*` (Blueprint `admin`)와 `/api/admin/*` (Blueprint `admin_api`) |
| `security.py` | 로그인·관리자 권한 데코레이터, CSRF, 로그인 시도 제한, 안전한 리다이렉트 |

`app.py`(프로젝트 루트)는 **앱 팩토리** `create_app()` 로 객체를 조립하고 Blueprint 를 등록한다.

## 왜 Blueprint 로 나눴나?
기능(인증·사용자·관리자)별로 파일을 나누면 `app.py` 가 500줄을 넘지 않고, 관리자 라우트를 한 묶음으로 보호하기 쉽다.
왜 앱 팩토리인가: 테스트마다 **임시 DB 로 새 앱**을 만들 수 있다 (`create_app(tmp_path)`).

## 보안 설계 (발표 핵심)
| 위협 | 대응 | 위치 |
| :--- | :--- | :--- |
| 비밀번호 유출 | 해시 저장 | `AuthManager` |
| 비로그인 접근 | `@login_required` (API 는 401 JSON, 화면은 로그인으로 이동) | `security.py` |
| 일반 사용자의 관리자 접근 | `@admin_required` (403) — 화면과 API 모두 | `security.py` |
| CSRF (다른 사이트가 내 로그인을 이용해 요청) | 세션 토큰을 폼 hidden / `X-CSRF-Token` 헤더로 검증 | `check_csrf` |
| 비밀번호 무차별 대입 | 같은 IP+아이디 5회 실패 시 5분 잠금 | `login_blocked` |
| 세션 고정 | 로그인 때 `session.clear()` 후 새 세션 | `auth_routes.login` |
| 오픈 리다이렉트 | `next` 는 같은 사이트 상대경로만 허용 | `safe_next_url` |
| XSS (스크립트 삽입) | 서버 렌더링은 Jinja 자동 이스케이프, JS 는 `esc()` 로 이스케이프 | `templates/`, `static/js/main.js` |
| 삭제·비활성 계정의 기존 세션 | 매 요청마다 DB 에서 사용자 상태를 확인해 즉시 무효화 | `app.py: load_user` |
| 업로드 남용 | CSV 만, 2MB 제한, 전체 요청 3MB 제한 | `admin_routes.words_import`, `create_app` |
| 정보 노출 | 오류 응답에 내부 메시지 없음, 보안 헤더(`X-Frame-Options` 등) | `app.py` |

세션 서명 키(`SECRET_KEY`)는 코드에 두지 않는다. 환경변수 또는 `data/secret_key.txt`(자동 생성, git 제외).

## 요청 흐름 (로그인한 사용자가 시험을 풀 때)
`브라우저(fetch) → CSRF 검사 → load_user(세션→사용자) → @login_required → user_routes.api_test_answer → TestEngine.grade_answer → JSON`

## 알아둘 점 / 한계
- 로그인 잠금은 **서버 메모리**에 저장된다. 프로세스를 여러 개 띄우는 배포에서는 공유되지 않는다 (향후 DB·Redis).
- HTTPS 배포 시 `SESSION_COOKIE_SECURE=1` 로 쿠키를 보호한다.
- 기본 실행은 `127.0.0.1` 만 허용, 디버그는 `FLASK_DEBUG=1` 일 때만 (공용망에서 디버거 노출 방지).

## 예상 질문
- **Q. 왜 JWT 가 아니라 세션?** 서버 렌더링 + 같은 도메인 웹앱이라 세션 쿠키가 단순하고, 즉시 로그아웃(계정 비활성화)이 쉽다. JWT 는 모바일 앱·외부 API 연동 때 고려한다.
- **Q. CSRF 를 왜 직접 구현했나?** 의존성(Flask-WTF 등)을 늘리지 않고 원리를 이해하기 위해서다. 규모가 커지면 검증된 라이브러리로 교체한다.
