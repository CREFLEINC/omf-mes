---
name: design-issue-resolution
description: >-
  "Agent : Architect" 라벨이 붙은 `CREFLEINC/omf-mes` 자기 이슈를 받아 독립 재실측 → 사람 게이트
  (분석 승인) → 반영 PR → 병합 확인까지 처리하는 Architect 전용 스킬. "Architect 역할 시작하자",
  "이 이슈 해결해줘", "저 자기 이슈 처리해", "Agent : Architect 라벨 붙은 거 봐줘" 같은 요청,
  또는 `design-request-intake`(Consultant)가 판정을 마치고 이 라벨을 붙여 넘긴 이슈를 이어받을
  때 사용한다. `.claude/worktrees/architect` 워크트리 안에서만 실행한다. 완료하면 답변서를 쓰지
  않고 병합 해시·근거를 자기 이슈 코멘트로 남긴 뒤 라벨을 "Agent : Consultant"로 되돌려
  Consultant에게 다시 넘긴다 — 이 스킬은 절대 답변서를 작성하거나(`design-request-intake` 몫)
  자기 이슈를 닫지 않는다(역할 경계). 개발팀 저장소 이슈는 받지 않는다(V3 규칙 2, 직접 소통 금지).
---

# design-issue-resolution — Architect 전용, 자기 이슈 재실측·반영

`multi-agent-team-workflow-v3-design-team-structure.md`가 정의하는 **Architect(설계자)** 역할의
작업 스킬이다. Architect는 "현재 진행 중인 작업 상태를 유지하며 제한 없이 자유롭게 자료를 수정할
수 있는" 워크트리(`.claude/worktrees/architect`, 브랜치 `architect-work`)에서만 실행한다 — 다른
워크트리(main·consultant·caster)에서 이 스킬을 돌리지 않는다.

이 스킬은 `design-request-intake`(Consultant)의 옛 Phase 3~5b를 그대로 계승한다 — 절차·검사기·
게이트 서식은 바뀌지 않았고, **누가 어느 워크트리에서 도는가**만 바뀌었다. `design-request-intake`
가 판정(Phase 0~2)까지 마치고 라벨을 스왑해 넘긴 자기 이슈만 받는다. **입력**은 `Agent : Architect`
라벨이 붙은 `CREFLEINC/omf-mes` 자기 이슈(번호 지정 또는 그 라벨이 붙은 열린 이슈 목록)다.
**출력**은 반영 PR + 자기 이슈에 남기는 인계 코멘트다 — 답변서는 쓰지 않는다.

⛔ **Phase 5(인계)가 Phase 4(PR 병합 확인)보다 먼저 오면 안 된다.** `design-request-intake`의 옛
사고(#206·#196 — PR 병합 전에 이슈가 닫힌 사고)와 같은 뿌리다: 인계 코멘트가 인용하는 병합
해시는 병합 전에는 존재하지 않는다. Phase 순서 자체가 재발 방지 장치다 — 재배열하지 않는다.

이 스킬은 `team-issue-protocol`(자기 이슈 라벨·핸드오프 절차)을 전제로 한다. 먼저 그 스킬을
`Skill` 도구로 읽는다.

## Phase 0 — 컨텍스트 확인 (인계 받기)

```
ROOT="$(git rev-parse --show-toplevel)"   # architect 워크트리 자신이어야 한다
gh issue view <이슈번호> --repo CREFLEINC/omf-mes --json title,body,comments,labels
```

이슈에 `Agent : Architect` 라벨이 없으면 받지 않는다 — Consultant가 아직 판정 중이거나 이미
Consultant에게 돌아간 이슈다.

⭐ **착수하기로 했으면 여기서 `status:in-progress` 를 붙인다**(2026-09-05 사용자 확정 — 그 라벨은
「**설계 담당자가 실제로 착수했다**」는 뜻이라 접수 시점에는 붙지 않는다. 인계만 받아 둔 이슈와
지금 손대고 있는 이슈를 라벨 하나로 가르는 것이 이 규칙의 목적이다):
```
gh issue edit <이슈번호> --repo CREFLEINC/omf-mes --add-label "status:in-progress"
```
⛔ **읽어만 보고 착수하지 않을 것이면 붙이지 않는다** — 붙여 놓고 멈추면 그 라벨이 다시 거짓이 된다.
떼는 것은 Consultant가 이슈를 닫을 때다(`design-request-intake` Phase 6b) · 사용자 확인 대기로
멈추면 `help wanted` 로 교체한다(Phase 2).

이슈 코멘트 중 Consultant가 남긴 `01_scope.md` 요지(물음별 판정표)
를 찾아 `$ROOT/.design-runs/<식별자>-*/`에 `00_request.md`·`01_scope.md`로 복원한다 —
`.design-runs/`는 워크트리마다 독립된 gitignore 스크래치이므로, Consultant 워크트리가 만든 파일이
여기 자동으로 있지 않다. 자기 이슈 코멘트가 유일한 정본 전달 경로다.

## Phase 1 — 독립 재실측·분석

`design-review-analyst`(opus, 읽기전용)를 스폰한다:

```
Agent(
  subagent_type: "design-review-analyst",
  model: "opus",
  prompt: "$RUN/00_request.md 와 01_scope.md 를 읽고, 각 적합 물음을 독립 재실측하라.
           요청자의 「없다/N건이다」 주장을 그대로 인용하지 말고 직접 명령을 돌려 재현하라.
           판정 단위는 요청 범위가 아니라 화면 전체다 — §4·§5 전건을 계약과 대조하고
           '요청 밖에서 드러난 것'을 반드시 확인하라. V2 §1-3-2 변경 적절성(부작용·영향 범위·
           이익 비교 — V3 는 라벨 형식만 V2 를 계승하지만 이 판단 기준은 그대로 쓴다)까지
           판단해 02_measure.md · 03_brief.md · 03_reply.md 를 $RUN/ 에
           산출하라. design-review-analyst.md 정의를 따르라."
)
```

analyst 산출물이 다음을 만족하는지 확인한다(미달이면 재작업 지시):
- `03_reply.md` 가 「인계 코멘트」 서식(Phase 5)을 갖췄다. 「반영 PR」·병합 해시 칸은 이 시점에
  **자리표시자**여도 된다(Phase 5 에서 채운다).
- `03_reply.md` 의 「답변」에 "⭐ 요청 밖에서 함께 드러난 것" 절이 채워져 있다(없으면 "없음 +
  확인 범위" 명시).
- `03_brief.md` 가 계약 JSON 을 건드리면 변경 등급표(Phase 3)의 행이 **빈칸 없이** 채워져 있다.

⛔ analyst 는 `03_labels.md`·`03_notice.md` 를 만들지 않는다 — 라벨은 자기 이슈에만 붙고(Phase
0·5) 통지는 배포 단위 공지(`design-change-notice`, Caster 소관)의 몫이다.

## Phase 2 — ★ 사람 게이트 — 분석 승인

`01_scope.md`·`02_measure.md`·`03_brief.md`·`03_reply.md` 전문을 **파일로 첨부**하고, 아래
서식으로 **본문 브리핑**을 함께 낸다. **이 승인 하나가 Phase 5(인계)까지 커버한다** — Phase 3
이후 새 사실이 드러나면(예: 반영 중 추가 미정 항목 발견) 이 게이트를 다시 돈다.

승인 없이는 Phase 3 로 진행하지 않는다. 공지 발행 게이트는 이 스킬에 없다 — 그것은
`design-change-notice`(Caster)가 배포 선언 때 따로 연다.

### ⛔ 브리핑 서식 — 사용자 확정 (2026-08-28, `design-request-intake`에서 계승)

⚠ **파일 첨부만 하고 요약을 화면 코드로 늘어놓지 마라.** 사용자가 두 차례 「더 이해하기 쉽게
설명해 달라」고 되물었다 — 승인을 구하는 자리에서 되묻게 만들면 게이트가 제 역할을 못 한다.
아래 네 절을 **이 순서로, 이 제목 취지대로** 쓴다.

```markdown
## 1. 어떤 화면이고, 개발팀이 왜 물어봤나
<화면 전체 이름 + 코드>. <이 화면이 현장에서 무엇을 하는 화면인지 한두 줄 — 업무 용어로>
<무엇이 막혔는지. 필요하면 「못 채우는 항목 / 무슨 값인가 / 왜 못 채우나」 3열 표>

## 2. 조사해보니 — <한 줄 결론>
<요청자 전제가 맞았는지 틀렸는지. 틀렸으면 무엇이 실제였는지>

## 3. 제 권고
<무엇을 하자는 것인지 한 문단. 그렇게 하면 개발팀에 무엇이 풀리는지>

## 4. 당신이 결정할 것 — <몇 가지인지>
<선택지가 있으면 「무엇을 하나 / 장점 / 단점」 3열 표 + 권장안 명시>
<선택지가 없으면 「이대로 진행할까요」 한 줄>
```

**지켜야 할 것**

| ⛔ | 무엇 |
| --- | --- |
| 화면 코드 단독 표기 금지 | `P-02-03` ❌ → **자재 투입 스캔·오투입 검증**(`P-02-03`) ✅. 조항·이슈 번호도 같다 — `A-21` ❌ → 부분 확정 위험 조항(`A-21`) ✅ |
| 내부 용어를 설명 없이 쓰지 않는다 | 「계약」·「미결」·「착지」·「파생」은 우리 말이다. 처음 쓰는 자리에서 풀거나 일상어로 바꾼다 |
| 산출물 파일명을 브리핑 본문의 뼈대로 삼지 않는다 | 사용자는 `03_brief.md` 가 무엇인지 알 필요가 없다. 파일은 첨부로 두고 본문은 **업무 이야기**로 쓴다 |
| 결정을 뭉뚱그리지 않는다 | 「승인할까요」 ❌ → **무엇을 고르는 것이고 각각 무슨 대가가 있는지** 표로 ✅ |
| 권고를 숨기지 않는다 | 선택지를 나열만 하지 말고 **어느 쪽을 권하는지와 그 이유**를 반드시 적는다 |

⭐ **범위가 요청보다 넓어졌으면 그 사실을 4절에서 별도 항목으로 세운다** — 「요청 범위 / 실제
반영 범위」를 표로 대조하고, 넓힌 근거와 좁힐 때의 퇴로를 함께 준다.

⭐ **영향받는 화면을 나열할 때는 「무슨 화면인지 · 설계가 지금 어떤 상태인지 · 왜 걸리는지」를
함께 적는다.** ⚠ 여기서 말하는 「상태」는 **우리 설계 문서의 상태**다. 개발팀이 그 화면을 어디까지
만들었는지는 **우리가 보유하는 정보가 아니므로 브리핑에 적지 않는다**(V3 규칙 3).

⭐ **사용자 확인이 더 필요해 여기서 멈추면** — 자기 이슈의 `status:in-progress` 를 `help wanted`
로 바꾸고, 이슈 코멘트로 「확인 필요: <무엇>」을 남긴 뒤 라벨을 `Agent : Architect` →
`Agent : Consultant` 로 되돌린다. `[확인 요청] <제목>` 이슈를 세우는 것은 Consultant 몫이다
(그쪽이 사용자와의 접점이다). 답이 오면 Consultant 가 라벨을 다시 `Agent : Architect` 로 돌려
이 게이트를 다시 연다.

## Phase 3 — 반영

`design-doc-writer`(sonnet)를 스폰해 승인된 `03_brief.md` 를 실행시킨다. writer 가 검사기
빨간불로 되돌리면 Phase 1(analyst)으로 되돌아가 재판정한다 — writer 가 스스로 고치지 않는다.
커밋 메시지 꼬리는 `(요청 <식별자>)` 다.

검사기 호출 — **표 전건이 정본이다.** 「지시서가 건드린 파일 종류」로 고르되, ⭐ 표가 실물보다
적으면 안 돌린 것이 사고가 된다(2026-09-01 실측 — 표에 8건뿐이라 `verify-mapping-coverage` 를
**6개 PR 에서 0회** 돌렸고 `#334` 가 초록으로 병합된 뒤 빨강이 됐다).

**① 언제나 돌린다 — 무엇을 고쳤든**

| 대상 | 명령 |
|---|---|
| 인용 경로 | `verify-doc-citations.py` |
| 조항 인용 | `verify-contract-citation.py` |
| 박힌 수치 | `verify-counts.py` — 문서에 적은 「N건」이 실물과 같은가 |
| 미결 정합 | `collect-open-items.py --check` |
| 죽은 경로 | `check-dead-path-citations.py` — 2026-08-25 구조 삭제 전 경로 인용 |
| 생성 스냅숏 | `verify-generated-fresh.py [--kind md\|html] [--domain NN]` — 인자 없이 돌리면 두 축(요구목록 마크다운 9건 + HTML 배포본 9건)을 다 본다. ⛔ `--domain` 은 마크다운 축 개념이라 `--kind html` 과 함께 주지 않는다 |

**② 화면 스펙·요구서를 고쳤으면**

| 대상 | 명령 |
|---|---|
| 화면 액션 커버리지 | `verify-ui-coverage.py --domain <NN>` |
| ⭐ 매핑 커버리지 | `verify-mapping-coverage.py` — 요구목록의 액션이 요구서 §3 에 다 있는가. **스펙과 요구서 중 한쪽만 고치면 여기서 터진다** |
| 화면 정본 | `verify-screen-inventory.py` — 인벤토리와 통합 IA 가 같은 화면을 말하는가 |
| 옛 표기 | `verify-stale-terms.py <기준ref>` — 표기를 바꿨을 때만. ⛔ 막지 않는다(항상 종료 0). ⛔ 인자 없이 돌리면 기본 `HEAD` 비교라 「대조한 파일 0」로 공허하게 초록이다 |

**③ 계약 JSON 을 고쳤으면** — `git diff --name-only -- design/wiki/api-contracts/openapi/` 가 비지 않으면 전건

| 대상 | 명령 | 무엇을 막나 |
|---|---|---|
| 계약 구조 | `openapi/check-structure.py` | 계약으로 성립하는가 |
| 공개 안전 | `openapi/check-public-safe.py` | 단가·내부 주소 유출 |
| enum 협착 | `openapi/check-enum-narrowing.py $(git merge-base origin/main HEAD)` | 자유문자열→enum · 값 삭제. ⛔ 인자 없이 돌리면 기본 `HEAD` 비교라 커밋 후 항상 초록 |
| ⭐ 필수 변경 | `openapi/check-required-change.py $(git merge-base origin/main HEAD)` | optional→required. **`check-enum-narrowing` 이 못 보는 파괴 변경**. ⛔ 인자 없이 돌리면 기본 `HEAD` 비교라 커밋 후 항상 초록 |
| ⭐ 조회 표준형 | `openapi/check-query-envelope.py` | 목록·요약 응답이 §L 게이트를 지키는가. **목록에 질의를 더하고 `/summary` 짝을 안 고치면 여기서 터진다**(`L-1-1 ⑶`) |
| ⭐ 코드그룹 이름 | `openapi/check-code-group-pointer.py` | 등록부에 없는 그룹 이름을 계약이 가리키면 화면이 **빈 목록**을 받는다 |
| ⭐ 코드그룹 도달 | `openapi/check-code-group-reachable.py` | 계약엔 있는데 요구서 §3 에 없어 **화면이 부를 줄 모르는** 그룹(래칫 — 늘면 ⛔) |
| 예시값 | `openapi/check-example-placeholder.py` | `example` 이 확정값 밖 — 구현팀이 그 값으로 만든다(`#191`). ⛔ 아직 **막지 않는다**(종료 0) — `#191` 반영이 끝나 0건이 되면 게이트로 올린다 |
| 저장 충돌 토큰 | `openapi/check-lock-token-source.py` | `If-Match` 를 쓰라면서 `ETag` 받을 곳이 없는 자리 |
| 귀속 사번 | `openapi/check-worker-no.py` | 사번을 받을 곳이 계약에 있는가 |
| 오프라인 표기 | `openapi/check-offline-consistency.py` | 계약의 오프라인 표기 ↔ 그 오퍼레이션을 부르는 화면의 판정 |

⛔ **초록을 「내가 안 깼다」로, 빨강을 「내가 깼다」로 읽지 마라.** ③ 중 일부는 **손대기 전부터
비초록**이다. ⭐ **고치기 전에 먼저 돌려 기준선을 잡고**, 반영 뒤 값과 대조해 «내가 낸 것»만 가른다.
기준선 표는 `design-request-intake`(Consultant)가 아니라 이 스킬이 최신으로 유지한다 — 반영이
일어나는 자리이므로. 현재 기준선(2026-09-02 `055557d`): `check-lock-token-source` ⚠ 2건·종료 1
(의도된 보류). `check-worker-no` 는 초록(2026-09-02 · `omf-mes#350`, ⚠ 3건은 남아 있으나 검사기
자신이 막지 않는다로 둔 것). `check-required-change` 는 헤더·질의 파라미터의 `required` 뒤집힘을
초록으로 통과시킨다(스키마 필드만 본다) — 그 자리의 등급은 사람이 매긴다.

⚠ 이 표는 **떠 있는 값이다.** 기준선이 바뀌면 여기 날짜와 커밋을 함께 갱신한다.

각 검사기가 "안 보는 것"은 `03_brief.md` 에 명시한다 — `check-enum-narrowing` 은 필드 삭제·
경로 삭제·필수 헤더 신설·**의미 변경**을 못 잡는다(required 승격은 `check-required-change` 가
따로 본다). ⭐ **의미 변경은 어느 검사기도 못 잡는다** — 자리 수도 글자 수도 그대로인 채 뜻만
바뀌므로 등급표로 수동 보강한다.

계약 JSON 을 고쳤으면(`git diff --name-only -- design/wiki/api-contracts/openapi/`) 아래
등급표 **전 행을 채운다**(빈칸 금지). 등급 어휘의 정본은
`design-change-notice/references/change-grades.md` 다 — 아래 표는 그 등급을 검사기에 대응시킨
것이고, 어긋나면 그쪽이 이긴다.

| 계약 변경 | 등급 | 자동 검출 |
|---|:-:|:-:|
| `required`·널 허용 변경 — **요청/응답으로 갈라** 판정(요청 `required` 추가 ⛔ · 응답 `required` 제거 ⛔ · 그 반대는 ⚠ — `change-grades.md` 「필수 여부」 4행 표) | ⛔/⚠ | `check-required-change.py`(스키마 필드만 — 헤더·질의 파라미터는 수동) |
| 경로/오퍼레이션 삭제, 필드 삭제, 필수 헤더 신설, **의미 변경** | ⛔ | 없음 — 수동 |
| 자유문자열→enum, enum 값 삭제 | ⛔ | `check-enum-narrowing.py` |
| 필드·경로 신설, enum 값 추가 | ⚠ | 없음 — 수동 |
| description만 | ℹ | — |

⭐ **등급은 우리 안에서 쓰는 값이다.** V3 공지는 등급을 싣지 않고(「달라진 지점」만), 인계 코멘트의
「근거」 칸도 등급이 아니라 **경로·절**을 싣는다(Consultant 의 답변서도 같다 — 「응답 스키마에서
`required` 가 빠져 값이 `null` 로 올 수 있다」 같은 **사실**은 적되 「그러니 널 가드를 넣어라」는
**지시**는 적지 않는다, V3 규칙 3). 등급표를 채우는 이유는 **파괴 변경을 의식하고 고쳤는가**를
Consultant 의 6b 잠금 ② 가 되짚기 위해서다.

반영을 PR 로 올린다(`gh pr create --repo CREFLEINC/omf-mes`). 계약 JSON·화면 스펙 수정
자체에는 별도 게이트를 두지 않는다 — PR 이 게이트이고 병합 전까지 완전 가역이다.

## Phase 4 — PR 병합 확인

```
gh pr view <PR> --repo CREFLEINC/omf-mes --json mergedAt,mergeCommit
git fetch origin main
git merge-base --is-ancestor <mergeCommit.oid> origin/main && echo "조상 ✅"
```
`mergedAt` 이 null 이거나 `mergeCommit.oid` 가 `origin/main` 의 조상이 아니면 **정지하고
병합을 기다린다.** 그 상태로 Phase 5 로 넘어가지 않는다 — #206·#196 이 이 확인 없이 진행해
병합 34~43분 전에 닫힌 사고의 재발 방지 지점이다. 인계 코멘트가 인용할 병합 해시는 여기서
확인된 `mergeCommit.oid` 다.

## Phase 5 — 인계 (Consultant에게 되돌림) — ★ 여기서 정지

병합이 확인되면 자기 이슈에 인계 코멘트를 남기고 라벨을 스왑한다:

```
gh issue comment <이슈번호> --repo CREFLEINC/omf-mes --body-file $RUN/04_handoff.md
gh issue edit    <이슈번호> --repo CREFLEINC/omf-mes \
  --remove-label "Agent : Architect" --add-label "Agent : Consultant"
```

`04_handoff.md`(= 다듬어진 `03_reply.md`):
```markdown
## Architect 인계 — <날짜>

| 항목 | 값 |
| --- | --- |
| 반영 PR | `CREFLEINC/omf-mes#<n>` |
| 병합 해시 | `<mergeCommit.oid 앞 7자>` |
| 판정 | 반영 / 부분 반영 / 반영하지 않음 (개선 제안서면 채택 / 부분 채택 / 채택하지 않음) |
| 근거 | <경로 · 절> 목록 |

<03_reply.md의 「답변」 본문 그대로 — Consultant가 답변서 「## 답변」에 그대로 옮겨 쓴다>
```

⛔ **여기서 멈춘다 — 답변서 작성·자기 이슈 닫기로 스스로 넘어가지 않는다.** 상담원이 캐스터
역할을 하면 안 되는 것과 같은 경계다(구성안 원문 「주의 사항」): Architect 는 **이슈를 해결하는
것까지가 일**이고, 개발팀에 어떻게 전달할지·언제 이슈를 닫을지는 `design-request-intake`
(Consultant) 의 일이다.

Phase 2(사람 게이트)에서 사용자 확인이 더 필요해 멈춘 경우도 같은 라벨 규칙이다 — 위 절차문
그대로 라벨을 `Agent : Consultant` 로 되돌리고, `[확인 요청]` 이슈는 세우지 않는다(Consultant
몫).

## 에러 핸들링

- `gh` 실패(네트워크·권한) — 재시도 1회, 재실패 시 "확인 불가"로 표시하고 그 Phase 를 완료로
  간주하지 않는다.
- analyst/writer 가 도구 실패로 중단 — 산출된 부분 파일은 보존하고, 사용자에게 상태를 보고한 뒤
  재개 여부를 확인한다(같은 이슈 번호로 재호출하면 Phase 0 이 이어받는다).
- Phase 2 게이트에서 사용자가 반려 — 반려 사유를 `$RUN/` 에 기록하고 해당 Phase 의 산출물만
  다시 만든다(전체를 재시작하지 않는다).
- 사용자 확인이 필요해 멈춤 — Phase 2 의 라벨 절차를 따른다. 대기 중에도 개발팀은 업무를 멈추지
  않는다(규칙 1).

## 테스트 시나리오

**정상 흐름** — `Agent : Architect` 라벨이 붙은 이슈 #N(Consultant가 「W-04-03 Lot 보류 이력
화면의 계약 결손」 판정을 마치고 넘김): P0 이슈·코멘트 조회, `01_scope.md` 복원 → P1 analyst
재실측 후 3종 산출 → **P2 게이트에서 정지**(승인 후) → P3 writer 가 계약에 필드 추가, 커밋 꼬리
`(요청 w-04-03-…)` → P4 병합·조상 확인 → P5 인계 코멘트 남기고 라벨을 `Agent : Consultant` 로
되돌림 — 이 스킬은 여기서 끝난다(답변서 작성·이슈 닫기는 Consultant).

**에러 흐름** — analyst 가 재실측 중 인용 경로 다수가 죽어 있음을 발견: `02_measure.md` 에
"근거 경로 붕괴 — <N>곳"으로 기록, `03_reply.md` 에는 살아있는 경로만 남기고 Phase 2 게이트에서
"이 요청 범위 밖에서 구경로 인용이 광범위하게 남아 있다"를 별도로 사용자에게 보고(하네스 밖
후속 과제 — `[설계] <제목>` 자기 이슈로 분리, 이 요청 처리는 계속 진행).
