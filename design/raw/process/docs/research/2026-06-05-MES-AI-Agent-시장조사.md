# MES 제품 시장조사 — AI Agent 적용 범위 중심

> 조사일: 2026-06-05 · 방법: 다중 출처 웹 검색 후 3표 적대적 검증(20개 주장 확정, 5개 반박) · 출처 26건(1차/벤더 공식 자료 중심)

---

## 0. 한 줄 결론 (전략적 시사점)

**한국 MES 벤더의 'MES 본 제품'에는 아직 LLM 기반 AI Agent(생성형 AI·코파일럿·자율 에이전트)가 거의 탑재되어 있지 않다.** 한국 벤더는 AI/ML을 MES 본체가 아니라 *별도의 분석·엔지니어링 제품*으로 분리해 제공한다. 반대로 글로벌 벤더(SAP·Siemens·AVEVA·Rockwell)는 2024~2026년에 걸쳐 MES/산업 플랫폼에 **명시적 AI Agent**를 빠르게 탑재 중이다. → **"AI Agent 네이티브 한국형 MES"는 현재 시장의 화이트 스페이스(공백)다.**

---

## 1. MES 기능 표준 프레임 (ISA-95)

- ISA-95 / IEC 62264 자동화 계층은 **Level 0~4의 5단계**로 구성된다.
- **MES(제조실행시스템) = Level 3(제조운영관리, MOM)** — "원하는 최종 제품을 생산하기 위한 워크플로우 활동을 정의"하는 계층.
- AI Agent가 MES에 적용된다는 것은 결국 이 **Level 3 워크플로우**(생산지시·실적·품질·설비·자재) 위에 지능형 에이전트를 얹는다는 의미.
- *출처: Siemens ISA-95 framework, ISA.org/IEC 62264 (검증 3-0)*

---

## 2. 한국 주요 MES 벤더·제품 및 핵심 기능 모듈

| 벤더 | 제품 | 핵심 기능 모듈 | AI Agent 탑재 현황 |
|------|------|----------------|-------------------|
| **미라콤아이앤씨** | Nexplant MESplus | **MES Core 4모듈**: 생산관리(WIP)·자재관리(INV)·품질관리(QCM)·설비관리(RAS). Cloud Edition도 동일 | MES Core에는 없음. 확장(EES)에 FDC·EPT·sDM 등 ML 기반 설비 분석 |
| **삼성SDS** | Nexplant MES | **5모듈**: Schedule & Dispatch, Manufacturing Operation, Equipment Engineering, Machine Control, Materials Control | 본 제품에는 'AI Agent' 명시 없음(advanced analytics 수준). AI는 별도 제품(Brightics, Nexplant Analytics, Visual Insight, EAM/CBM)에 귀속 |
| **LG CNS** | Factova MES | 시스템관리·실시간모니터링·라벨디자인 / 공정물류자동화(RTD·온라인설비) / 공정·라인 품질관리 / 모델링 기반 개발도구(웹·모바일 UI) / 멀티 OS·DBMS / 메시지 기반 미들웨어 통합 | 본 제품 페이지에 명시적 AI Agent 기능 불명확 (※ "AI 언급이 전무"라는 단정은 검증에서 반박됨 — 단정 금지) |
| **VMS Solutions** | MOZART | ※ **MES 아님** — AI·디지털트윈 기반 **APS(생산계획·스케줄링)·SCM**. 모듈: 생산계획(Resilient Planning)·생산스케줄링(Optimized Scheduling)·시뮬레이션&디지털트윈·제조AI(Manufacturing AI) | 제조 AI는 **ML 기반**(시뮬레이터 대량학습). 생성형 AI/코파일럿/자율 에이전트는 명시 안 됨. Gartner APAC SCP MQ Notable Vendor |
| **BISTel** | eDataLyzer | ※ **분석 플랫폼** — Map Analyzer·IntelliMine·Trace Analyzer 3개 도구. 수율·품질 근본원인분석(RCA), MES·YMS·FDC·EPT/OEE·PPM DB와 통합 | "detect/analyze/predict/adapt" 포지셔닝. **ML 기반 분석**이며 '자율 에이전트(agentic)'로 단정하는 주장은 반박됨 |

**미확인(추가 조사 필요):** 포스코DX, 신성이엔지, 더존비즈온, 영림원소프트랩 — 이번 검증에서 1차 출처로 확인되지 않음.

### 핵심 패턴
> 한국 벤더는 **"MES 본체 = 운영 실행 기록(트랜잭션) 시스템 / AI = 별도 분석·엔지니어링 제품"** 으로 분리. 즉 MES와 AI가 *제품 단위로 분리*되어 있어, 한 화면·한 대화창에서 작동하는 통합형 AI Agent 경험은 아직 약하다.

---

## 3. 글로벌 벤더의 AI Agent 탑재 현황 (선두 그룹)

| 벤더 | AI Agent 제품 | 형태 | 적용 범위 | 단계 |
|------|---------------|------|-----------|------|
| **SAP** | **Joule Agents (14종)** | 자율형 에이전트 | 재무·HR·조달·공급망에 임베딩. 그중 **Production Planning & Operations Agent**가 조건 충족 시 **주문 자동 검증·릴리스** → 생산 착수 시간 단축 | 생산 에이전트 **2026 Q1 GA 예정**(로드맵) |
| **Siemens** | **Industrial Copilot** | 생성형 AI 어시스턴트(Azure AI/OpenAI) | 설계·계획~운영·서비스 전 가치사슬. **자연어 대화형 정비 지원**(문제 설명→상세 요청→변경 논의) | 2024-07 GA, 2025-03 생성형 정비 확장(파일럿 반응형 정비시간 25%↓ *벤더 주장*) |
| **AVEVA** | **Industrial AI Assistant** | LLM + RAG(Azure OpenAI) | CONNECT 플랫폼 위 **채팅형 자연어 질의** → 공정 데이터·이벤트·자산/태그 검색·요약. HMI/SCADA/**MES** 지원 | MES 데이터 질의 일부 Open Beta/Preview |
| **Rockwell** | **NVIDIA Nemotron Nano(SLM)** | 엣지형 소형 언어 모델 | FactoryTalk Design Studio 등 워크플로 최적화. **엣지·오프라인·에어갭** 환경에서 클라우드 없이 작동 | Automation Fair 2025 시연 예정(초기 발표) |

### 한국 vs 글로벌 — 핵심 격차
- **글로벌:** 명시적 'AI Agent / Copilot / 자율 에이전트'를 **MES·산업 플랫폼 안에** 탑재(특히 SAP의 자율 주문 처리, Siemens·AVEVA의 자연어 인터페이스).
- **한국:** ML 기반 분석·예측은 강하나, **LLM 기반 대화형/자율 에이전트는 MES 본 제품에 거의 부재.**

---

## 4. MES에서 AI Agent가 적용될 수 있는 기능 영역 (검증된 5개 축)

| # | 기능 영역 | 현재 시장 사례 | 에이전트 성숙도 |
|---|-----------|----------------|-----------------|
| 1 | **품질 예측·근본원인 분석(RCA)** | BISTel eDataLyzer RCA, 삼성/미라콤 SPC·분석 | ML 분석 단계(자율 에이전트 아님) |
| 2 | **설비 이상탐지(FDC)·예지보전** | 미라콤 FDC/EPT/sDM, BISTel 설비 헬스, Siemens 생성형 AI 정비 | ML + 생성형(Siemens) 혼재 |
| 3 | **생산계획·스케줄링 최적화** | VMS MOZART APS, SAP 생산계획·운영 에이전트 | 자율 에이전트 등장(SAP) |
| 4 | **자연어 질의·요약(NLQ)** | AVEVA Industrial AI Assistant, Siemens Industrial Copilot | 생성형 코파일럿 단계 |
| 5 | **자율 업무 실행** | SAP Joule Agent — 자동 주문 검증·릴리스 | **유일하게 '자율 에이전트' 수준** |

> 명백한 **자율(autonomous) 에이전트** 수준은 **SAP Joule Agent**(자율 주문 검증·릴리스)와 **Siemens Copilot**(생성형 정비)에 한정. 나머지(한국 벤더·BISTel·VMS)는 주로 **ML 기반 분석·예측**.

---

## 5. 신뢰성 주의사항 (Caveats)

1. **시간 민감성**: SAP 생산 에이전트는 2026 Q1 GA *예정*, Rockwell-NVIDIA는 시연 예정, AVEVA MES 질의는 Open Beta — 모두 **"실증된 GA 제품"이 아니라 발표/로드맵 단계**.
2. **출처 품질**: 한국 벤더 정보는 대부분 **벤더 자체 마케팅 페이지/데이터시트** 의존. 기능 존재 여부엔 적절하나 **성능 수치(예: 정비시간 25%↓)는 독립 검증 안 됨**.
3. **'본 제품' vs '확장/별도 제품' 경계**: 삼성SDS MES 본 제품엔 AI 없지만 Brightics 등 별도 제품엔 있음. 미라콤 FDC/EPT/sDM은 MES Core가 아닌 **EES 확장**. → "MES에 AI가 있다/없다"는 **어느 제품 단위로 보느냐**에 따라 달라짐.
4. **반박된 주장(단정 금지)**: BISTel RCA·VMS 제조AI를 '자율/agentic'으로 규정 / LG CNS·미라콤 페이지에 'AI 언급 전무' → **모두 검증에서 반박됨(0-3 또는 1-2)**.
5. 삼성SDS 한국어 본 제품 URL이 현재 /error 리다이렉트 → US/EN 미러로 검증.

---

## 6. 다음 단계로 남은 질문 (기획서 작성 전 보강 필요)

1. 포스코DX·신성이엔지·더존비즈온·영림원소프트랩 MES 기능·AI 현황 추가 조사.
2. 삼성SDS AI 제품(Brightics·Nexplant Analytics)이 MES와 **실제 통합 깊이/UX** — 'MES 내 AI Agent'처럼 작동하는지.
3. 한국 벤더가 2025~2026년 **LLM 기반 코파일럿/NLQ를 MES에 출시·로드맵**에 두었는지(글로벌 대응 국산 동향).
4. SAP ME/MII, Siemens Opcenter의 **모듈 단위 기능** 및 Joule Agent/Copilot의 MES 직접 임베딩 범위.

---

## 출처 (1차/공식 위주)

- 미라콤아이앤씨 Nexplant MESplus / EES: miracom-inc.com
- 삼성SDS Nexplant MES: samsungsds.com
- LG CNS Factova MES: lgcns.com
- VMS Solutions MOZART: vms-solutions.com
- BISTel eDataLyzer 데이터시트: synopsys.com
- Siemens Industrial Copilot / ISA-95: siemens.com, press.siemens.com
- SAP Joule Agents: news.sap.com (2025-10)
- AVEVA Industrial AI Assistant: aveva.com
- Rockwell + NVIDIA Nemotron: rockwellautomation.com (2025-11)
