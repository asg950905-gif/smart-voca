# 스마트 보카 (smart-voca)

웹 기반 영어 단어 학습 플랫폼. 사용자 화면(학습·시험·통계)과 관리자 화면(단어·사용자·전체 통계 관리)을 분리했다.

## 빠른 시작 (Windows PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python ai-agent/scripts/시연데이터생성.py --reset   # 시연용 샘플 데이터 (선택)
python app.py                                       # http://127.0.0.1:5000
```

| 역할 | 아이디 / 비밀번호 (시연 데이터 기준) |
| :--- | :--- |
| 관리자 | `admin` / `admin1234` |
| 사용자 | `minsu`, `jiyoung`, `hojun` / `demo1234` |

시연 계정의 비밀번호는 **시연 전용**이다. 팀 테스트 배포 때는 새 DB 로 시작하고 `.env`(`.env.example` 참고)로 관리자 계정을 만든다.

## 주요 기능

- **사용자**: 회원가입/로그인, 오늘의 단어 플립카드 학습, 시험(4지선다·단답·OX), 개인 통계 차트, 하루 학습량·다크모드 설정
- **관리자**: 전체 현황 대시보드, 단어 CRUD·CSV 가져오기/내보내기, 사용자 관리(역할·활성화·비밀번호 재설정·삭제), 전역 설정
- **UI**: 카드형 디자인, 다크모드, 모바일 하단 탭바, 키보드 단축키(학습: Space/←/→)

## 구조

```
app.py                  앱 팩토리 (환경변수 · 보안 헤더 · 오류 처리)
src/data/database.py    SQLite 스키마·접속
src/business/           auth / word / study / test_engine / report_generator
src/web/                Blueprint (auth, user, admin) + security (권한·CSRF·로그인 제한)
src/utils/config.py     사용자 설정 + 관리자 전역 설정
templates/ static/      화면 (admin/ 하위가 관리자 화면)
tests/                  pytest
ai-agent/               설계·분석 문서, 작업계획, 일지, 스크립트
docs/                   승인된 산출물 (개발방법론)
```

## 테스트

```powershell
pip install -r requirements-dev.txt
python -m pytest tests -q
```

## 문서

- 프로젝트 지침: `CLAUDE.md` / 개발방법론: `docs/개발방법론.md`
- 작업 계획·결정 기록(ADR-001 SQLite): `ai-agent/claude/작업계획_261102_사용자관리자화면_UI개편_시연.md`
- 시연 시나리오: `ai-agent/claude/테스트_261102_시연 시나리오 v1.0.md`
