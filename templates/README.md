# templates — 화면 (Jinja2 템플릿)

**파일 위치**: `templates/README.md`
**작성일**: 2026-11-02
**버전**: v1.0
**설명**: 서버가 HTML 을 만드는 템플릿. 화면별 동작은 `static/js/` 의 같은 이름 스크립트가 맡는다.

---

## 구성
| 영역 | 파일 | 화면 |
| :--- | :--- | :--- |
| 공통 | `base.html` | 상단 내비·하단 탭바·테마 초기화. 모든 화면이 상속 |
| 공통 | `login.html`, `register.html`, `error.html`, `_mascot.html` | 로그인, 가입, 오류(400/403/404/413/500), 마스코트 SVG 매크로 |
| 공개 | `landing.html` | 로그인 전 `/` 랜딩 페이지 (히어로·퀴즈 체험·기능·실제 수치·FAQ) |
| 사용자 | `dashboard.html`, `study.html`, `test.html`, `league.html`, `report.html`, `settings.html` | 홈(레벨·XP·목표), 플립카드 학습, 시험, 주간 리그, 개인 통계, 설정 |
| 관리자 | `admin/dashboard.html`, `admin/words.html`, `admin/users.html`, `admin/settings.html` | 전체 현황, 단어 관리, 사용자 관리, 전역 설정 |

## 핵심 개념
- **템플릿 상속**: `base.html` 의 `{% block content %}` 만 각 화면이 채운다. 내비·테마·CSRF 메타 태그가 한 곳에 있다.
- **사용자/관리자 영역 구분**: `base.html` 이 경로가 `/admin` 이고 **실제 관리자일 때만** 관리자 메뉴와 청록색(`body.admin`)을 보여준다.
  (일반 사용자의 403 화면에 관리자 메뉴가 보이는 문제를 리허설에서 발견해 수정함.)
- **서버 렌더링 + JS API 혼합**: 홈처럼 한 번 그리면 되는 화면은 서버가 값을 채우고, 학습·시험·통계·관리자 화면은 JS 가 `fetch` 로 API 를 호출해 갱신한다.
- **XSS 방어**: Jinja 는 `{{ }}` 를 자동 이스케이프한다. JS 로 HTML 을 만들 때는 반드시 `esc()` 를 쓴다.
- **첫 페인트 전 테마 적용**: `<head>` 의 작은 인라인 스크립트가 다크모드를 먼저 적용해 화면이 번쩍이지 않는다.

## 새 화면을 추가하려면
1. `templates/` 에 `{% extends "base.html" %}` 로 작성 → 2. `src/web/*_routes.py` 에 라우트 추가(`@login_required` / `@admin_required`)
→ 3. 필요하면 `static/js/화면이름.js` 추가 → 4. `tests/test_backend.py` 의 페이지 목록에 경로 추가.
