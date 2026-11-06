# static — CSS · JavaScript · 라이브러리

**파일 위치**: `static/README.md`
**작성일**: 2026-11-02
**버전**: v1.0
**설명**: 브라우저에서 실행되는 스타일과 스크립트. 프레임워크 없이 Vanilla JS 로 구현했다.

---

## 구성
| 파일 | 역할 |
| :--- | :--- |
| `css/style.css` | 디자인 시스템 기본 (토큰, 라이트/다크, 반응형, 버튼·카드·표) |
| `css/components.css` | 파스텔 타일, 레벨/XP, 컨페티, 빈칸 문제, TTS 버튼, 리그 |
| `css/landing.css` | 랜딩 전용 (히어로·데모·기능 블록·FAQ) |
| `js/main.js` | 공통: `api()`(CSRF 자동 첨부 fetch), `toast()`, `confirmDialog()`, `esc()`, 테마 |
| `js/charts.js` | Chart.js 공통 헬퍼(테마 색 연동, 빈 데이터 처리) |
| `js/landing.js` `league.js` | 랜딩(스크롤 등장·퀴즈 체험·카운트업), 리그 화면 |
| `img/shot-*.png` | 랜딩에 쓰는 실제 화면 캡처 (시연 데이터로 촬영) |
| `js/study.js` `test.js` `report.js` `settings.js` | 사용자 화면별 동작 |
| `js/admin-*.js` | 관리자 화면별 동작 (dashboard, words, users, settings) |
| `vendor/chart.umd.min.js` | Chart.js 4.4.1 (CDN 이 아니라 **로컬 파일**) |
| `vendor/icons.svg` | 아이콘 스프라이트 — 출처: [Lucide](https://lucide.dev) v0.454.0 (ISC 라이선스, 전문은 `vendor/LICENSE-lucide.txt`). 템플릿은 `_icons.html` 의 `icon()`, JS 는 `main.js` 의 `icon()` 으로 쓴다 |

## 설계 이유
- **왜 Vanilla JS (React/Vue 아님)?** 화면 12개 규모에서 빌드 도구(Node, 번들러)를 도입하면 설치·배포가 복잡해진다. Flask 하나로 실행되고, 코드가 곧 동작 원리라 설명하기 쉽다.
  화면이 훨씬 복잡해지면 프레임워크 도입을 검토한다.
- **왜 CSS 변수(디자인 토큰)?** 색·간격·반경을 `:root` 변수로 두고 `[data-theme="dark"]` 에서 값만 덮어쓰면 **다크모드가 CSS 몇십 줄**로 끝난다. 관리자 영역은 포인트 색 변수만 바꿔 구분한다.
- **왜 Chart.js 를 로컬에 두었나?** 시연 환경에 인터넷이 없어도 차트가 나오고, 외부 CDN 장애·변조 위험이 없다. 테마를 바꾸면 `MutationObserver` 로 차트 색도 다시 그린다.
- **반응형**: 700px 이하에서 상단 메뉴를 숨기고 **하단 탭바**(엄지로 누르기 쉬움)를 보여준다. `prefers-reduced-motion` 을 존중한다.
- **접근성**: 포커스 표시, `aria-label`, 키보드 조작(학습: Space/←/→, 시험: Enter), 터치 영역 44px 내외.

## v2 설계 이유
- **발음 듣기(TTS)**: 브라우저 내장 `speechSynthesis`(Web Speech API)를 쓴다. 서버·외부 API·키가 필요 없고 오프라인 시연이 된다. 지원하지 않는 브라우저에서는 버튼을 숨긴다. 마이크 기반 발음 진단은 브라우저·환경 편차가 커서 제외했다.
- **마스코트·일러스트는 직접 그린 SVG**: 외부 이미지·저작권 이슈가 없고 색을 CSS 변수로 바꿀 수 있다.
- **버튼 색 토큰(`--btn-a/--btn-b`)**: 다크모드에서 강조색이 밝아져도 흰 글씨 대비가 유지되도록 분리했다.
- **`word-break: keep-all`**: 한글이 어절 중간에서 줄바꿈되지 않게 한다.
- **`prefers-reduced-motion`**: 움직임을 줄이는 설정이면 컨페티·떠다니는 애니메이션을 끈다.

## 규칙
- 서버에서 온 값을 `innerHTML` 에 넣을 때는 `esc()` 필수.
- 상태를 바꾸는 요청은 `api()` 를 사용 (CSRF 헤더 자동). 직접 `fetch` 하지 않는다.
