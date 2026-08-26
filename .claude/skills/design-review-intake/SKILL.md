---
name: design-review-intake
description: >-
  개발팀이 omf-mes(설계팀 저장소)에 올린 [검토 요청]·[client→uiux] 이슈를 접수해 적합성 판정
  → 독립 재실측 → 파급 산정 → 반영 → 회신 → 통지 → 닫기까지 처리하는 오케스트레이터.
  "232번 검토 요청 처리해줘", "개발팀에서 이슈 올린 거 확인해줘", "검토 요청 답변 준비해줘",
  "접수함에 뭐 있어", "이어서 처리해줘", "232 다시 봐줘", "저번 검토 요청 업데이트해줘" 같은
  요청에 반드시 이 스킬을 사용한다. ⛔ omf-mes-client로 내보내는 착수/변경 통지는
  uiux-client-handoff 소관이고(이 스킬은 그 마지막 단계에서 그 스킬을 호출만 한다),
  docs/ 기획 문서 작업은 이 스킬 소관이 아니다.
---

# design-review-intake — 설계 검토 요청 접수·처리

`multi-agent-team-workflow-v2.md` §1-2(설계 검토 요청 처리)를 절차로 세운 것이다. 개발팀이
`omf-mes` 저장소에 올린 검토 요청을, 사람 개입을 게이트 2곳으로만 최소화해 처리한다.

⛔ **Phase 6(닫기)이 Phase 7(통지)보다 먼저 오면 안 된다.** 실측된 두 사고 — 이슈가 PR 병합
34~43분 **전에** 닫힌 사례(#206·#196), 그리고 `WorkOrderRelease.lotSlotCount` 필드 삭제 +
`lotSize` 필수 승격을 반영하고도 `omf-mes-client#80`(W-02-04 착수 이슈, 현재 OPEN)에 ⛔ 통지가
**한 번도 안 나간** 지금도 미조치 상태인 사고 — 가 모두 이 순서 위반에서 났다. 아래 Phase 순서
자체가 그 재발 방지 장치다. 순서를 재배열하지 않는다.

이 스킬은 `team-issue-protocol`(라벨·서식·8유형·회신템플릿)을 전제로 한다. 먼저 그 스킬을 `Skill`
도구로 읽는다.

## Phase 0 — 컨텍스트 확인

```
ROOT="$(git rev-parse --show-toplevel)"
```

1. 대상 이슈 번호를 정한다 — 사용자가 지정("232번")했으면 그것. 미지정이면 `team-issue-protocol`
   §4의 2축 합집합 쿼리로 OPEN 후보 전건을 나열하고 우선순위(차단 등급·경과일)로 제시, 사람에게
   확인받는다.
2. `$ROOT/.design-runs/<이슈번호>-*/` 존재 여부 확인:
   - **없음** → 초기 실행. `$ROOT/.design-runs/<이슈번호>-<YYYYMMDD>/` 생성.
   - **있고 사용자가 부분 수정 요청** → 부분 재실행. 기존 파일을 읽고 해당 Phase만 재실행.
   - **있고 사용자가 새 정보 제공** → 기존 디렉토리를 `<...>_prev/`로 이동 후 재생성.
3. ⛔ **런 디렉토리는 절대경로만 쓴다.** 상대경로 `_workspace/`를 쓰지 않는다 — 구 하네스가
   그래서 산출물이 두 갈래로 쪼개졌다(`docs/_workspace/`에 117파일이 실수로 커밋됨). 이름도
   `_workspace`로 하지 않는다 — `docs/_workspace/`와 겹쳐 grep·훅이 오폭한다.
4. `.design-runs/`는 `.gitignore`에 등재돼 있다 — 커밋하지 않는다. 감사 추적의 정본은 이슈
   코멘트+커밋 SHA+통지 이슈다(런 디렉토리는 스크래치일 뿐).

## Phase 1 — 수집

`team-issue-protocol` §4의 2축 합집합으로 이슈를 가져온다:
```
gh issue view <N> --repo CREFLEINC/omf-mes --json number,title,body,labels,comments,state
```
다건 대상이면 `gh issue list --repo CREFLEINC/omf-mes --state open --json number,title,labels`
로 전건을 받아 합집합 필터를 적용하고, **합집합 밖 OPEN 이슈는 "채널 밖 후보"로만 보고**한다
(처리하지 않는다).

⛔ 제목 접두가 `[uiux→` · `[docs→`(설계팀 자신의 발신)면 하드 제외한다 — 이 필터를 통과했더라도
검토 요청으로 처리하지 않는다.

출력: `$RUN/00_issue.json`.

## Phase 2 — 적합성 판정

이슈 본문을 **물음(문장) 단위**로 분해한다. 각 물음에 `team-issue-protocol` §5의 8유형표를
적용하고, 판정 근거로 삼은 문장의 **주어를 원문 그대로** 옮겨 적는다(주어를 못 옮기면 판정
불가로 남긴다 — 확정문의 주어를 오독해 소관을 잘못 넘긴 선례가 있다).

```
python3 design/schema/generators/collect-open-items.py --issue <N>
```
로 이 이슈가 이미 미결 표지로 걸린 화면이 있는지 먼저 확인한다(있으면 그 화면들을 분석 범위에
넣는다 — 없다고 새 표지가 필요 없다는 뜻은 아니다, Phase 8에서 심는다).

**전 물음이 유형 E(업무배정)·F(서식불비, 반려 아닌 보완요청)·H(채널오인)면 여기서 멈춘다** —
해당 회신만 남기고 Phase 3으로 진행하지 않는다.

출력: `$RUN/01_scope.md`(물음별 판정표).

## Phase 3 — 독립 재실측·분석

`design-review-analyst`(opus, 읽기전용)를 스폰한다:

```
Agent(
  subagent_type: "design-review-analyst",
  model: "opus",
  prompt: "$RUN/00_issue.json 과 01_scope.md 를 읽고, 각 적합 물음을 독립 재실측하라.
           요청자의 「없다/N건이다」 주장을 그대로 인용하지 말고 직접 명령을 돌려 재현하라.
           판정 단위는 요청 범위가 아니라 화면 전체다 — §4·§5 전건을 계약과 대조하고
           '요청 밖에서 드러난 것'을 반드시 확인하라. v2 §1-3-2 변경 적절성까지 판단해
           02_measure.md · 03_brief.md · 03_reply.md · 03_notice.md · 03_labels.md 를
           $RUN/ 에 산출하라. design-review-analyst.md 정의를 따르라."
)
```

analyst 산출물이 다음을 만족하는지 확인한다(미달이면 재작업 지시):
- `03_notice.md`가 **존재한다**(통지 불요라도 사유 명시) — 파일 부재 자체를 "판단 안 함"으로
  간주한다.
- `03_reply.md`에 "⭐ 요청 밖에서 함께 드러난 것" 절이 채워져 있다(없으면 "없음 + 확인 범위"
  명시).

## Phase 4 — ★ 사람 게이트 (1/2)

`01_scope.md`·`02_measure.md`·`03_brief.md`·`03_reply.md`·`03_notice.md`·`03_labels.md`
전문을 사용자에게 제시하고 승인을 받는다. **이 승인 하나가 Phase 6b(닫기)까지 커버한다** —
Phase 5 이후 새 사실이 드러나면(예: 반영 중 추가 미정 항목 발견) 이 게이트를 다시 돈다.

승인 없이는 Phase 5로 진행하지 않는다. **#232를 처음 실행할 때는 이 Phase에서 멈춘다** — 코멘트
게시·문서 수정·발행은 사용자가 이 게이트를 통과시킨 뒤 별도 턴에서 이어간다.

## Phase 5 — 반영

`design-doc-writer`(sonnet)를 스폰해 승인된 `03_brief.md`를 실행시킨다. writer가 검사기
빨간불로 되돌리면 Phase 3(analyst)으로 되돌아가 재판정한다 — writer가 스스로 고치지 않는다.

검사기 호출(빠짐없이, 지시서가 건드린 파일 종류에 따라 해당분만):
| 대상 | 명령 |
|---|---|
| 인용 경로 | `verify-doc-citations.py` |
| 조항 인용 | `verify-contract-citation.py` |
| 화면 액션 커버리지 | `verify-ui-coverage.py --domain <NN>` |
| 미결 정합 | `collect-open-items.py --check` |
| 계약 구조 | `openapi/check-structure.py` |
| 공개 안전 | `openapi/check-public-safe.py` |
| enum 협착(★기준 명시 필수) | `openapi/check-enum-narrowing.py $(git merge-base origin/main HEAD)` — 인자 없이 돌리면 기본 `HEAD` 비교라 커밋 후 항상 초록 |
| 생성 스냅숏 | `verify-generated-fresh.py [--domain NN]` |

각 검사기가 "안 보는 것"은 `03_brief.md`에 명시한다(예: `check-enum-narrowing`은 필드 삭제·
required 승격·경로 삭제·필수 헤더 신설·의미 변경을 못 잡는다 — 아래 등급표로 수동 보강).

계약 JSON을 고쳤으면(`git diff --name-only -- design/wiki/api-contracts/openapi/`) 아래
등급표 **전 행을 채운다**(빈칸 금지):

| 계약 변경 | 등급 | 자동 검출 |
|---|:-:|:-:|
| 경로/오퍼레이션 삭제, 필드 삭제, optional→required, 필수 헤더 신설, 의미 변경 | ⛔ | 없음 — 수동 |
| 자유문자열→enum, enum 값 삭제 | ⛔ | `check-enum-narrowing.py` |
| 필드·경로 신설, enum 값 추가 | ⚠ | 없음 — 수동 |
| description만 | ℹ | — |

반영을 PR로 올린다(`gh pr create`). 계약 JSON·화면 스펙 수정 자체에는 별도 게이트를 두지
않는다 — PR이 게이트이고 병합 전까지 완전 가역이다.

## Phase 5b — PR 병합 확인

```
gh pr view <PR> --json mergedAt
```
`mergedAt`이 null이면 **정지하고 병합을 기다린다.** null인 채로 Phase 6a로 넘어가지 않는다 —
#206·#196이 이 확인 없이 진행해 병합 34~43분 전에 닫혔다.

## Phase 6a — 회신 게시 (닫지 않는다)

`team-issue-protocol` §7 템플릿으로 `03_reply.md`를 확정하고 게시한다. 첫 줄은 정확히
`## 개발팀 전달사항`. 게시 전:
- `python3 .claude/skills/uiux-design/scripts/check-report-language.py $RUN/03_reply.md`
- `python3 .claude/skills/uiux-client-handoff/scripts/check-issue.py $RUN/03_reply.md --reply`
  — 머리 표기·공개 안전·자리표시자를 본다. ⛔ **`--reply` 없이 돌리지 마라** — 폼 6항목
  구조와 중복 발행을 검사해 「막지 않아도 되는 ⛔」가 무더기로 뜬다(2026-08-26 #442에서 9건).
- 근거 블록의 모든 경로를 `test -f`로 확인, 실재하지 않으면 그 줄을 제거하거나 대체 경로로 교체.
- 회신에 반영 PR 번호 + **병합 커밋 sha**(Phase 5b에서 확인)를 명시 — 자리표시자를 남기지 않는다.

**게시 수단은 코멘트다:**
```
gh issue comment <요청 이슈 번호> --repo <요청이 온 저장소> --body-file $RUN/03_reply.md
```

⛔ **`gh issue create`를 쓰지 않는다.** 회신은 언제나 **요청 이슈의 코멘트**다. 새 이슈로 내면
개발팀이 ⚠ 이상의 변경 통지로 읽어 **재작업으로 오해한다.** 이 명령을 여기 박아 둔 이유는,
하네스 전체에서 `gh issue` 예시가 `uiux-client-handoff`의 `gh issue create`뿐이라
「게시한다」만 적혀 있으면 **가장 가까운 실행 패턴이 "새 이슈를 만든다"**가 되기 때문이다
(2026-08-26 실측 — 사고는 없었으나 규약이 막고 있던 것이 아니었다).

⚠ **요청이 공개 저장소에서 올 수 있다.** `team-issue-protocol` §1은 「인바운드=비공개
`omf-mes`이므로 금지어 검사 불요」로 적혀 있으나, `omf-mes-client#442`처럼 **우리가 발행한
아웃바운드 이슈의 코멘트로 검토 요청이 올 수 있다.** 그때는 회신도 공개로 나가므로
**금지어 검사가 필수**이고, 이 Phase가 §8의 「공개 저장소 발행 = 승인 필수」에 걸린다.
회신 대상 저장소의 가시성을 먼저 확인한다:
```
gh repo view <저장소> --json isPrivate -q .isPrivate
```

⛔ **이 Phase에서 이슈를 닫지 않는다.** 통지가 아직이면 닫을 이유가 없다.

## Phase 7 — ★ 사람 게이트 (2/2) — 통지 발행

`03_notice.md`가 통지 필요라고 판정했으면(등급표에 ⛔/⚠ 행이 하나라도 있으면), `uiux-client-handoff`
스킬을 호출해 초안을 다듬고 `check-issue.py --change-notice`를 통과시킨 뒤, **발행 직전 초안
전문 + 검사 결과를 사용자에게 제시하고 승인받는다.** 공개 저장소 발행은 되돌릴 수 없다(인덱싱된
사본·포크는 회수 안 됨) — 이번 하네스에서 유일하게 승인이 필수인 두 번째 지점이다.

`03_notice.md`가 "통지 불요"라고 판정했으면 이 Phase는 건너뛰되, 그 사유를 Phase 6b 잠금③에
그대로 인용한다(침묵으로 넘기지 않는다).

## Phase 6b — 닫기 (4중 잠금)

전부 통과해야 닫는다. 하나라도 실패하면 닫지 않고 사유를 기록한다.

| 잠금 | 확인 | 통과 조건 |
|:-:|---|---|
| ① | `gh pr view <PR> --json mergedAt` | non-null (Phase 5b 재확인) |
| ② | `git diff --name-only <base>..<merge-sha> -- design/wiki/api-contracts/openapi/` | 계약이 바뀌었으면 등급표 전 행 기입 완료 |
| ③ | Phase 7 결과 | 통지 발행 완료(번호 있음) **또는** "불요 + 사유" 명시 |
| ④ | `collect-open-items.py --issue <N>` | 걸린 화면 0건(있으면 Phase 8을 먼저 실행) |

통과하면 `team-issue-protocol` §6 상태 전이에 따라 라벨을 정리하고 이슈를 닫는다. 닫을 수 없는
경우(백엔드 결정 대기 등)는 `in progress`→`help wanted`로 교체 + 사유 코멘트, 열어 둔다.

## Phase 8 — 되먹임

반영한 화면의 스펙 §8에 이 이슈 번호(`#N`)를 추적 표지로 심는다(없으면 미결-대장 역인덱스가
다음에 이 결정을 다시 못 찾는다). 그 후:
```
python3 design/schema/generators/collect-open-items.py
python3 design/schema/generators/build-screen-progress.py
```
을 재생성한다.

## 에러 핸들링

- `gh` 실패(네트워크·권한) — 재시도 1회, 재실패 시 "확인 불가"로 표시하고 그 Phase를 완료로
  간주하지 않는다.
- analyst/writer가 도구 실패로 중단 — 산출된 부분 파일은 보존하고, 사용자에게 상태를 보고한 뒤
  재개 여부를 확인한다(같은 이슈 번호로 재호출하면 Phase 0이 부분재실행으로 잡는다).
- Phase 4·7 게이트에서 사용자가 반려 — 반려 사유를 `$RUN/`에 기록하고 해당 Phase의 산출물만
  다시 만든다(전체를 재시작하지 않는다).

## 테스트 시나리오

**정상 흐름** — #232(단일 화면, 계약 결손 지적): P0 신규 런 생성 → P1 라벨+접두 매치로 단건
수집 → P2 물음 4개로 분해, Q1/Q2 적합·Q1′/Q2′ 부적합 판정 → P3 analyst가 `summary` 17건 등
재실측 후 4종 산출 → **P4 게이트에서 정지**(승인 후) → P5 writer가 계약에 집계 필드 추가 →
P5b 병합 확인 → P6a 회신 게시 → P7 게이트(⚠ 통지, 승인 후 발행) → P6b 4중 잠금 통과 → 닫힘 →
P8 표지 심기.

**에러 흐름** — analyst가 재실측 중 인용 경로 다수가 죽어 있음을 발견(2026-08-25 구조 삭제
영향): `02_measure.md`에 "근거 경로 붕괴 — <N>곳"으로 기록, `03_reply.md`에는 살아있는 경로만
남기고 Phase 4 게이트에서 "이 이슈 범위 밖에서 구경로 인용이 광범위하게 남아 있다"를 별도로
사용자에게 보고(하네스 밖 후속 과제로 분리, 이 이슈 처리는 계속 진행).
