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

- **랜딩 페이지**(로그인 전 `/`): 떠다니는 파스텔 카드 히어로, 브라우저에서 바로 풀어보는 빈칸 퀴즈 체험, 기능 소개, **DB 실제 수치**, FAQ
- **사용자**: 회원가입/로그인, 오늘의 단어 플립카드 학습(🔊 발음 듣기), 시험(**빈칸 채우기**·4지선다·단답·OX), XP·레벨·연속 학습·**주간 리그**, 개인 통계 차트, 하루 학습량·다크모드 설정
- **관리자**: 전체 현황 대시보드, 단어 CRUD·CSV 가져오기/내보내기, 사용자 관리(역할·활성화·비밀번호 재설정·삭제), 전역 설정
- **UI**: 파스텔 디자인 시스템(토큰·라이트/다크), 마스코트 '보카'(직접 그린 SVG), 컨페티·체크 애니메이션, 모바일 하단 탭바, 키보드 단축키(학습: Space/←/→/P)

## 구조

```
app.py                  앱 팩토리 (환경변수 · 보안 헤더 · 오류 처리)
src/data/database.py    SQLite 스키마·접속
src/business/           auth / word / study / test_engine / gamification / report_generator
src/web/                Blueprint (auth, user, admin) + security (권한·CSRF·로그인 제한)
src/utils/config.py     사용자 설정 + 관리자 전역 설정
templates/ static/      화면 (admin/ 하위가 관리자 화면)
tests/                  pytest
ai-agent/               설계·분석 문서, 작업계획, 일지, 스크립트
docs/                   승인된 산출물 (개발방법론)
```

## 모듈별 설명 (역할 · 설계 이유 · 예상 질문)

| 모듈 | 문서 |
| :--- | :--- |
| 데이터(SQLite) | [src/data/README.md](src/data/README.md) |
| 비즈니스 로직 | [src/business/README.md](src/business/README.md) |
| 웹·보안 | [src/web/README.md](src/web/README.md) |
| 설정 | [src/utils/README.md](src/utils/README.md) |
| 화면(템플릿) | [templates/README.md](templates/README.md) |
| 정적 파일(CSS/JS) | [static/README.md](static/README.md) |
| 테스트 | [tests/README.md](tests/README.md) |

발표자료(.pptx)는 `python ai-agent/scripts/발표자료생성.py` 로 다시 만들 수 있다 (python-pptx 필요, 내용은 스크립트의 텍스트를 수정).

## 테스트

```powershell
pip install -r requirements-dev.txt
python -m pytest tests -q
```

## 다른 컴퓨터에서 이어서 작업하기

**처음 한 번 (새 컴퓨터)**

```powershell
git --version; python --version            # 없으면 Git, Python 3.9+ 설치
git clone https://github.com/asg950905-gif/smart-voca.git
cd smart-voca
git config --local user.name  "asg950905-gif"   # --global 말고 --local (공용 PC 흔적 방지)
git config --local user.email "asg950905@gmail.com"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python ai-agent/scripts/시연데이터생성.py --reset   # data/ 는 git 에 없으므로 다시 생성
```

- 내려받기(clone)는 로그인 없이 되지만 **push 는 GitHub 로그인 필요**: `gh auth login`
- `claude` 실행 후 "ai-agent/claude 의 최근 일지를 읽고 어디까지 했는지 정리해줘" 라고 요청한다. (이전 대화·자동 메모리는 따라오지 않으므로 일지가 인수인계 문서)

**작업 시작할 때**: `git pull`
**작업 끝낼 때**: 일지(`ai-agent/claude/일지_*.md`) 갱신 → 커밋 → `git push`
**공용 PC(실습실)에서는 종료 전**: `gh auth logout`, Windows 자격 증명 관리자의 `github.com` 삭제, 클론 폴더 삭제.
토큰·비밀번호·`.env` 내용은 Claude 대화창에 붙여넣지 않는다.

문제 해결: push 거절 → `git pull` 후 재시도 / `Activate.ps1` 차단 → `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## 문서

- 프로젝트 지침: `CLAUDE.md` / 개발방법론: `docs/개발방법론.md`
- 작업 계획·결정 기록(ADR-001 SQLite): `ai-agent/claude/작업계획_261102_사용자관리자화면_UI개편_시연.md`
- 시연 시나리오: `ai-agent/claude/테스트_261102_시연시나리오_v1.0.md`
