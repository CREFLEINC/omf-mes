# 위임 브리프 템플릿 — 도식 파이프라인 4단계

`{NN}`=도메인 번호(03·04·05), `{도메인명}`=한글 도메인명. 각 에이전트는 **포그라운드**(run_in_background:false)로. 오케스트레이터는 결과를 직접 조회로 검증(에이전트 최종 메시지 신뢰 금지).

공통 헤더(모든 브리프에 포함):
- 작업 디렉터리 `/Users/rangkim/projects/crefle/ohmyfactory/apps/omf/docs`
- 도구 로드: `ToolSearch query="select:mcp__plugin_figma_figma__use_figma,mcp__plugin_figma_figma__get_screenshot,mcp__plugin_figma_figma__get_figjam"` → Skill `figma:figma-use`,`figma:figma-use-figjam` 로드
- fileKey `Sgy5IKD4aWuzpKtJAbMyWz`. use_figma 첫 호출 연결 실패 시 재시도 말고 즉시 보고.
- raw/·planning/versions/ 접근 금지.
- **SKILL.md의 함정을 그대로 상속**: 폰트 선로드, 커넥터 `.height` 5000+ 오보고(섹션 높이 계산 시 CONNECTOR 제외), clone-not-draw, 증분 ≤10연산/콜, 소스 ID 무효 시 재발견(01 섹션 인스턴스의 `getMainComponentAsync().parent.name`으로 유형 매칭 또는 컴포넌트 key로 import).
- **배치 좌표는 오케스트레이터가 이 브리프에 채워 넣는다**: `{섹션 origin (x,y)}`·`{축 y·중심 간격 260·체인 스텝 190}`. 슬롯이 비어 있으면 오케스트레이터에게 되물어라(임의 배치 금지).

---

## ① 계획 에이전트 (스펙 작성) — 02~05는 이미 있으니 신규 도메인만

임무: 도식 제작 스펙을 `research/2026-07-06-도식스펙-{NN}-{도메인명}.md`에 작성(신규 Write).

필수 선행 독해(전부): `research/2026-07-03-워크플로우-요구사항반영-{NN}-*.md`(단계·Rule·Exception 정본) · 개념데이터모델 v2 해당 클러스터 · 설계결정서 14건 해당분 · QA 확정기록 해당 #.

스펙 구조: §1 메인 구조도(①가로축 시퀀스 표 ②작업자별 행위 체인 표 ③분기 헥사곤 표 ④MES 데이터 노트 전문 — 도식 문구 그대로·KEY 필수 ⑤ERP 연계 지점 ⑥미정의 마커) · §2 사이드 구조도(복잡 예외별 시퀀스·조건·데이터 노트) · §3 근거 매핑 표(요소↔REQ/QA/결정/WF# — **도식엔 넣지 않음**) · §4 미정의 목록.

제약: 근거 없는 내용 창작 금지(애매하면 §4 미정의). 메인 축 ≤12·행위 노드 ≤30, 아이콘 라벨 ≤10자·헥사곤 ≤16자·스티키 ≤12줄. **영역 분리**: 다른 도메인 소관은 경계 헥사곤 "→ 도식 NN"으로 위임. 완료 시 요약(축·행위·노트·사이드 수) 반환.

---

## ② 실행 에이전트 (작화) — 메인과 사이드를 **각각** (2회)

임무: 스펙 `research/2026-07-06-도식스펙-{NN}-*.md`의 **§1 메인만**(또는 **§2 사이드만**) FigJam으로 작화.

스타일 100% 재현 = 클론 킷 복제(신규 드로잉 금지). 소스 ID(검증됨): Archive `3:1019`/User `3:1230`/Mobile `3:1494`/Desktop `3:2006`/File `3:1781`/Wallet `3:1758`/Server `3:1880`/Database `3:4848`/Email `3:6494`(48×48)/헥사곤 `3:4359`/OR `3:4536`/스티키 `3:1684`. 아이콘 라벨=인스턴스 내부 TEXT 중 `characters.trim()≠"1"·≠""` 것을 폰트 로드 후 교체. 헥사곤·스티키=`node.text` 폰트 로드(getStyledTextSegments) 후 교체.

커넥터: `figma.createConnector()`, strokeWeight=4, ELBOWED, `connectorStart/End={endpointNodeId,magnet:'AUTO'}`. 색: 검정=주 흐름 / 회색=대안·생략·위임 / 초록=행위·데이터 / 빨강=시작.

배치: `figma.createSection()` name=`{NN}.{도메인명}`(사이드는 `-사이드`), **오케스트레이터가 지정한 origin (x,y)**에 배치(임의 배치 금지 — 슬롯 비면 되물어라). 섹션 로컬 좌표로 appendChild. 축 아이콘 y 고정·중심 간격 260, 행위 체인 세로 스텝 ~190. 상태 색: 시작 빨강/진행 검정/완료 파랑. **이 실행은 §1 메인 또는 §2 사이드 중 하나만**(오케스트레이터 지시대로) — 스펙 §2에 사이드가 없으면 사이드 실행은 생략된다.

증분 순서(각 후 screenshot 자가 확인): 섹션+제목 → 가로 축+축 커넥터 → 작업자별 체인 → MES 노트 스티키 → 헥사곤·OR·ERP·미정의+조건 커넥터. use_figma당 논리연산 ≤10, 폰트 선로드, 생성 ID 반환.

자가 검증 체크: 축·행위·노트·헥사곤 수 스펙 일치, 겹침 0, 커넥터 오연결 0, 금지 규칙 준수(검사결과 ERP 화살표 없음 등), clone 기반. 최종: 생성 결과·미처리·스크린샷 1장. 이 FigJam만 수정, repo 파일 Read만.

---

## ③ 검증 에이전트 (읽기 전용 — 캔버스 무수정)

임무: 섹션 `{섹션ID}`를 스펙 `research/2026-07-06-도식스펙-{NN}-*.md`와 전수 대조. 캔버스 수정 금지(결함·수정 지시만).

방법: (1) `use_figma` 읽기로 섹션 children 유형·라벨·좌표 수집 → 스펙 ①~⑥ 대조(축 노드 수·라벨·색 / 행위 체인 노드 유형·라벨 / MES 노트 KEY·문구 **전수** / 헥사곤·ERP·미정의). 금지 규칙 위반 탐지(검사결과→ERP·개발품 실적→ERP·MES가 P/O 수정=blocker). (2) `get_screenshot`(maxDimension 2000) 육안: 겹침·오연결·라벨 잘림·정렬.

산출(최종 메시지, 이 형식): **A. 판정 PASS/FAIL**(blocker 또는 major 3+ = FAIL) · **B. 결함**(각 줄 `[blocker|major|minor] <노드ID/위치> — <문제> → <수정 지시>`) · **C. 정합 확인**(수정 불요 핵심) · **D. 스크린샷 1장**. 추측 금지, 근거(노드ID/스크린샷) 명시. 사이드 미제작 시 사이드 노드 부재는 결함 아님(단 메인의 사이드 진입 헥사곤은 존재해야).

---

## ④ 수정 에이전트 (검증 결함 외과적 수정)

임무: 검증에서 확정된 결함만 수정(지정 외 무수정). 각 수정 전 해당 노드를 `getNodeByIdAsync`로 조회해 현재 상태 확인 후 최소 변경. 노드 삭제 시 물린 커넥터도 함께 제거(고아 방지). 신규 연결은 기존 패턴과 동일 색·굵기.

자가 검증: 수정 후 스크린샷으로 결함 해소 확인 + 새 겹침·고아 커넥터 0. 최종: 각 수정 처리 결과(완료/미처리+사유)·삭제/생성/이동 ID·스크린샷 1장. repo 파일 Read만.

---

## 오케스트레이터 검증(에이전트 결과 직접 조회) 스니펫

에이전트 최종 메시지는 잘려 오므로 직접 조회로 검증:

```js
// 섹션 구성 요약
const s = await figma.getNodeByIdAsync('{섹션ID}');
const byType = {}; for (const k of s.children) byType[k.type]=(byType[k.type]||0)+1;
const inst = s.children.filter(k=>k.type==='INSTANCE').map(k=>k.findAll(n=>n.type==='TEXT').map(n=>n.characters).filter(c=>c.trim()!=='1'&&c.trim()!=='').join('|'));
const stickies = s.children.filter(k=>k.type==='STICKY').map(k=>k.text.characters.split('\n')[0]);
const hexes = s.children.filter(k=>k.type==='SHAPE_WITH_TEXT').map(k=>k.text.characters);
return { byType, inst, stickies, hexes };
```

트랜스크립트에서 에이전트 최종 text만 추출(전체 read 금지):
```python
import json
for line in open(OUTPUT_FILE):
    j=json.loads(line)
    if j.get("type")!="result": continue
    # 또는 assistant text 블록만 walk해서 마지막 큰 text 출력
```
