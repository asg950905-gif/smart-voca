# Project Development Methodology

** AI소프트웨어 개발방법론 **

**Reference:** Samsung SDS Innovator, BDD (Behavior-Driven Development), ADR (Architecture Decision Records)

---

## 1. 개요 (Introduction)

### 1.1 개발방법론의 의미
시스템 개발방법론은 소프트웨어 공학 원리를 적용하여 정보시스템을 구축하는 과정에서의 작업 단계, 절차, 산출물 및 관리 체계를 표준화한 것이다. 이는 프로젝트 팀원 간의 원활한 소통을 돕고, 개발 품질의 상향 평준화를 보장하며, 유지보수의 효율성을 극대화하는 지표가 된다.

### 1.2 적용 방법
본 방법론은 프로젝트의 규모 및 특성에 따라 유연하게 적용(Tailoring)할 수 있다. 각 단계별 산출물은 다음 단계의 입력물(Input)이 되며, 특히 AI 에이전트와 협업하는 환경에서는 산출물의 텍스트 명확성과 추적성(Traceability)을 유지하는 것이 가장 중요하다.

---

## 2. 개발 생애주기 및 산출물 (SDLC & Deliverables)

### 2.1 기획 단계 (Planning Stage)
프로젝트의 공식적인 승인과 비즈니스 목표 및 범위를 확정한다.

| 산출물 (KR) | 영문 명칭 (EN) | 주요 포함 내용 (Key Contents) |
| :--- | :--- | :--- |
| **프로젝트 기획서** | **Project Charter** | 프로젝트 승인 정보, BRD(비즈니스 요구사항), SS(시스템 범위) 통합 |

### 2.2 분석 단계 (Analysis Stage)
내/외부 환경을 진단하고 시스템이 갖춰야 할 '무엇(What)'을 확정한다.

| 산출물 (KR) | 영문 명칭 (EN) | 주요 포함 내용 (Key Contents) |
| :--- | :--- | :--- |
| **현황 분석서** | **Internal Assessment** | 기존 비즈니스 프로세스, 기존 시스템 구조/문제점, 사용자 기대/요청, 가정 및 제약, 내부 데이터 연계 활용 |
| **환경 분석서** | **External Analysis** | 비즈니스 환경 및 유사 사례, 유사 시스템 사례, 기술 환경 및 관련 기술, 외부 데이터 분석 |
| **요구사항 명세서** | **Requirement Spec** | 상세 기능 및 비기능 요구사항, 요구사항 추적 매트릭스 |

### 2.3 설계 단계 (Design Stage)
시스템의 구성 요소와 상호작용 등 '어떻게(How)'를 정의하며 결정 근거를 남긴다.

| 산출물 (KR) | 영문 명칭 (EN) | 주요 포함 내용 (Key Contents) |
| :--- | :--- | :--- |
| **시스템 아키텍처 설계서** | **Architecture Design** | 컴포넌트/컨테이너 위상(Topology), 인프라 구성, 분산 처리 및 보안 전략 |
| **기능 분해도** | **Function Map** | 시스템 기능을 원자 단위(Atomic)로 계층적 분해 |
| **데이터 설계서** | **Data Design** | 논리/물리 DB 설계, 데이터 스키마 명세, 저장소 정책 및 제약 조건 |
| **UI/UX 설계서** | **Interface Layout** | 사용자 인터페이스 레이아웃, 사용자 경험 흐름도(Storyboard) |
| **프로세스 설계서** | **Process Logic** | 단위 기능별 알고리즘, 데이터 처리 비즈니스 로직 상세 명세 |
| **인터페이스 정의서** | **Integration Spec** | **컴포넌트/컨테이너 간 통신(API, Message)**, 데이터 전문 규격 |
| **아키텍처 결정 기록** | **Decision Records** | 기술적 의사결정 기록(ADR), 선택 배경, 대안 분석 및 제약 사항 |

### 2.4 구현 및 이행 단계 (Implementation Stage)
실제 구동 환경을 구축하고 품질을 검증하여 배포한다.

| 산출물 (KR) | 영문 명칭 (EN) | 주요 포함 내용 (Key Contents) |
| :--- | :--- | :--- |
| **구현 계획서** | **Implementation Plan** | 개발 로드맵, 모듈별 개발 순서, 인력 및 자원 배분, 의존성 관리 계획 |
| **형상/배포관리 정의서** | **Deployment Spec** | 소스 버전 관리(Git) 전략, CI/CD 파이프라인, 이미지 빌드 및 태깅 규칙 |
| **테스트 정의서** | **Test Specification** | BDD 시나리오 기반 단위/통합/인터페이스 테스트 케이스 및 결과 |
| **운영/배포 정의서** | **Operations Manual** | 런타임 환경 설정(Docker/K8s), 시스템 모니터링 가이드, 장애 복구 절차 |

---

## 3. AI 에이전트를 위한 지침 (Guidance for AI Agent)

1. **추적성 준수 (Maintain Traceability):**
   - 모든 기능 구현은 `Requirement Spec`의 고유 ID와 연결되어야 한다.
   - 컴포넌트 간 통신 구현 시 반드시 `Integration Spec`에 정의된 데이터 규격 및 프로토콜을 준수한다.
2. **결정 근거 확인 (Consult Decision Records):**
   - 코드 생성이나 구조 변경 제안 전, `Decision Records`를 확인하여 특정 기술이나 패턴을 선택한 '의도'와 '맥락'을 파악한다.
3. **오류 분석 시 (When Analyzing Errors):**
   - 시스템 상호작용 오류 발생 시 `Architecture Design`과 `Integration Spec`을 대조하여 데이터 무결성과 통신 지점을 먼저 확인한다.
4. **문서 기반 소통 (Document-Driven Communication):**
   - 코드를 제안하기 전, 관련 설계 문서(`Process Logic` 또는 `Data Design`)의 최신 상태를 먼저 확인하고 변경 사항 발생 시 문서 업데이트를 병행한다.

---

## 4. 파일 관리 규칙 (File Management)

- **Naming Convention:** `{Project_Name}_{EN_Name}_vX.X_YYMMDD.md`
- **Example:** `ProjectA_Integration_Spec_v1.0_260404.md`
- **Format:** AI 에이전트와 인간 개발자의 가독성을 극대화하기 위해 마크다운(Markdown) 형식을 기본으로 한다.