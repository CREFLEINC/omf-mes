# omf-mes 설계팀 저장소 하네스

이 저장소는 `multi-agent-team-workflow-v3.md`(2026-09-03 사용자 확정)가 정의하는 **설계팀
저장소**다 — 이슈 라벨 종류·형식만 V2(`multi-agent-team-workflow-v2.md`)를 그대로 쓴다. 산출물
정본은 `design/`(raw/wiki/schema 3층 — `design/README.md` 참조)이고, 이 파일은 하네스 존재를
알리는 포인터만 담는다. 에이전트·스킬 목록은 `.claude/agents/`·`.claude/skills/`에서 직접 확인한다.
설계팀 내부 팀 구성(3역할·워크트리)은 `multi-agent-team-workflow-v3-design-team-structure.md`
(2026-09-04 사용자 확정, 원문 그대로 보존)가 정의한다 — 아래 「설계팀 3역할」 절 참조.

⭐ **설계 내용은 전부 `design/` 안에 있다.** 2026-08-25 재구성(`a8f46f2`)으로 `uiux/`·
`deliverables/`·`docs/research/`가 사라졌다 — 옛 이슈·문서가 그 경로를 가리키면 죽은 인용이고,
지금 자리는 `design/schema/redirect-map.md`가 말한다. 고칠 곳을 그 경로에서 찾지 않는다.

⛔ **`design/raw/`는 고치지 않는다** — 확정기록 원문·고객 원자료의 시점 고착본이라 훅이 쓰기를
막는다. 「확정기록의 그 줄이 지금은 틀렸다」는 원문을 고쳐서가 아니라 **`design/wiki/`가 지금
무엇이 맞는지 말하는 것**으로 해소한다(작성 규칙 5의 정합주·구표기 보존이 그 수단이다).

## 트리거

- **설계 변동 공지 발행**("공지해", "배포 공지", "개발팀에 변경 알려줘" 등 — 직전 공지 태그
  `notice/*` → HEAD 를 묶어 개발팀 저장소 2곳에 이슈 1건씩) → `design-change-notice` 스킬을 사용하라.
- **개발팀 요청 자료 접수·판정**(사용자가 건넨 파일·붙여넣기 — "이 자료 처리해줘", "개선 제안서
  검토", "답변서 만들어줘" 등, Consultant 전용) → `design-request-intake` 스킬을 사용하라.
- **자기 이슈 재실측·반영**("Architect 역할 시작하자", "이 이슈 해결해줘", `Agent : Architect`
  라벨 이슈 처리 등, Architect 전용) → `design-issue-resolution` 스킬을 사용하라.
- 화면 설계·계약 작업 자체는 `uiux-design` 스킬을 사용하라.
- 이슈 규약·라벨·제목 접두·승인 지점을 물으면 `team-issue-protocol` 스킬을 사용하라.
- 단순 질문·조회는 스킬 없이 직접 응답 가능.

⛔ **V3 규칙 2 — 설계팀→개발팀 직접 소통은 «설계 변동 공지» 이슈 하나뿐이다.** 개발팀 저장소에
그 외 이슈·코멘트를 쓰지 않는다. 개발팀 요청은 **사용자가 자료로 건네고**, 우리 답변서도
**사용자가 전한다**. `[검토 요청]` 이슈 직접 인바운드·회신 코멘트·변경 요약 통지는 폐지됐다 —
열린 `[검토 요청]` 이슈는 사용자가 정리한다.

⛔ **업무 배정·착수 가능 통지는 폐지됐다**(2026-09-03 사용자 확정). 설계팀은 개발팀의
업무에 관여하지 않는다 — **무엇이 언제 바뀌었는지만 전하고**, 개발팀은 이 저장소를
직접 열람해 내용을 확인하고 처리 방식도 스스로 정한다. 「어느 화면을 누가 맡나」·「지금
어디까지 만들었나」는 **설계팀이 보유하지 않는 정보**다.
⇒ 개발팀에 「무엇이 언제 바뀌었나」를 알리는 정본은 **설계 변동 공지 이슈**(개발팀 저장소,
git tag `notice/*`)다. [`design/wiki/progress/변경-요약.md`](design/wiki/progress/변경-요약.md) 는
설계팀 «내부» 이력이다(생성물 — `build-change-digest.py` 가 git 이력에서 만든다).

## 설계팀 3역할 — Consultant · Architect · Caster

설계팀은 `multi-agent-team-workflow-v3-design-team-structure.md`(2026-09-04 사용자 확정, 원문
그대로 보존)가 정의하는 3역할로 나뉜다. 각 역할은 완전히 격리된 자기 워크트리에서만 실행한다 —
`.claude/scripts/setup-team-worktrees.sh [consultant|architect|caster|all]`가 이 저장소를 새로
클론받아 처음 개발환경을 설정할 때(또는 그 이후 갱신할 때) 워크트리를 만든다.

| 역할 | 워크트리 | 보는 자료 상태 | 스킬 |
| --- | --- | --- | --- |
| Consultant(상담원) | `.claude/worktrees/consultant` | 가장 마지막 배포 버전(최신 `notice/*` 태그, 디태치드) | `design-request-intake` |
| Architect(설계자) | `.claude/worktrees/architect` | 현재 진행 중인 작업(브랜치 `architect-work`, 자유롭게 수정) | `design-issue-resolution` |
| Caster(캐스터) | `.claude/worktrees/caster` | 검증 완료된 배포 브랜치 최신(`origin/main`, 디태치드) | `design-change-notice` |

⛔ **담당 역할이 아닌 다른 역할의 작업을 하지 않는다**(구성안 원문 「주의 사항」 — 상담원이
캐스터 역할을 해서 공지를 보내면 안 된다). 이 경계는 **문서로만** 강제한다 — 세 스킬이 서로의
몫(반영 PR·공지 발행·답변서 작성)에 손대지 않도록 각자 description 과 절차문에 명시했다. 코드
훅으로 강제하지 않는다 — 이 저장소에서 다른 큰 규칙(V3 규칙 2 등)도 줄곧 문서 강제였고,
`protect_readonly.py`는 비가역적 손상(`design/raw/` 원자료 훼손) 방지라는 예외적 목적으로만
쓰는 훅이다.

⭐ **역할 지시 없이 일을 시키면 반드시 사용자에게 지금 세션의 역할이 무엇인지 먼저 물어본다**
(구성안 원문 「설계팀 시작하기」 4번 그대로) — 지금 작업 디렉토리가 어느 워크트리인지만으로
역할을 스스로 단정하지 않는다.

⚠ **`design/raw/` 보호 훅은 세션 자신의 작업 디렉토리가 실제로 그 워크트리일 때만 유효하다**
(2026-09-04 실측 — `.claude/hooks/protect_readonly.py`는 `$CLAUDE_PROJECT_DIR` 기준으로 보호
범위를 계산한다). 각 워크트리는 훅·`settings.json`을 git 이 자동으로 동반해 자기 안에서는
정상 작동하지만, 메인 체크아웃에서 절대경로로 다른 워크트리 파일을 건드리면 보호 밖이다 — 각
역할 세션은 반드시 자기 워크트리를 작업 디렉토리로 삼아 새로 실행한다.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
| --- | --- | --- | --- |
| 2026-08-25 | 초기 구성 — 에이전트 2종(`design-review-analyst`·`design-doc-writer`) + 스킬 3종 신설(`design-review-intake`·`design-work-assignment`·`team-issue-protocol`) + `uiux-client-handoff` 수정(죽은 `issue-management` 참조 제거) + 읽기전용 보호 훅을 `design/raw/`로 재배선 | 전체 | `multi-agent-team-workflow-v2.md` 도입 — 인바운드 설계 검토 요청 처리 절차가 하네스에 전무했고, `[검토 요청]` 이슈 #232가 접수돼 있었다 |
| 2026-08-26 | 회신 게시 경로를 못박음 — `design-review-intake` Phase 6a 에 `gh issue comment` 명령 + `⛔ gh issue create 금지` 명시, `team-issue-protocol` §7 에 게시 수단 절 신설, `check-issue.py` 에 `--reply`(폼 구조·중복 발행 검사 끄고 **회신 규약 = 머리 표기·자리표시자** 검사 켬)·`--private`(공개 안전 스캔만 끔 — 비공개 저장소 회신용) 모드 추가 + `test-check-issue.py` 18건 신설 | `design-review-intake` · `team-issue-protocol` · `uiux-client-handoff/scripts/check-issue.py`·`test-check-issue.py` | `omf-mes-client#442` 처리 중 구멍 3개가 드러났다 — ① Phase 6a 에 실행 명령이 없는데 하네스의 유일한 `gh issue` 예시가 `create` 뿐이라 「새 이슈 발행」이 가장 가까운 실행 패턴이었다 ② §7 이 정본으로 못박은 머리 표기를 `#232`·`#222` 가 이미 어겼는데 검사기가 없었다 ③ 회신을 착수 통지 폼으로 검사해 「막지 않아도 되는 ⛔」 9건이 떴다 |
| 2026-08-26 | 「인바운드=비공개」 가정 정정 — 검토 요청이 공개 저장소(우리 아웃바운드 이슈)의 코멘트로 올 수 있음을 §1 에 명시, 가시성 확인 명령 추가 | `team-issue-protocol` §1 · `design-review-intake` Phase 6a | `omf-mes-client#442` 가 첫 사례 — 공개 저장소로 회신이 나가는데 §1 은 「인바운드에는 금지어 검사 불요」로 적혀 있었다 |
| 2026-08-25 | `in progress` 라벨 신설 취소 — 기존 `status:in-progress`(사용 2건)로 대체. `help wanted` 부착 기준을 "백엔드 결정 대기"가 아니라 "우리 회신이 미완성인가"로 정정 | `team-issue-protocol` | #232를 `design-review-intake`로 첫 실행한 `design-review-analyst`가 라벨 실측 오류를 잡아냄(§7-5 운영 피드백) |
| 2026-08-27 | 회신 머리 표기 재확정 — `## 개발팀 전달사항`(조사 없음, 2026-08-26 확정) → `개발팀에 전달사항`(v2 문서 line 62 원문 그대로, 조사 있음). `##`는 강제하지 않음(저자 재량). 서식도 고정 골격 강제를 풀고 "이슈 종류·처리 결과에 맞춰 자유롭게, 명확히 전달되면 충분"으로 완화. `check-issue.py`의 `REPLY_HEAD` 정규식과 `test-check-issue.py` 20건(기존 18건에서 갱신) 함께 수정 | `team-issue-protocol` §7 · `uiux-client-handoff/scripts/check-issue.py`·`test-check-issue.py` | omf-mes#245 회신 준비 중 사용자가 2026-08-26 결정(관행 다수 기준)을 재검토 — v2 원문을 우선하기로 함. 관행 기준 정본은 한 번 이미 실측 위반(#232·#222)을 냈던 자리라 재확정도 검사기·테스트로 못박는다 |
| 2026-08-28 | **사람 게이트 브리핑 서식 신설** — Phase 4 에 4절 서식(①어떤 화면·왜 물었나 ②조사 결과 ③권고 ④결정할 것) + 금지 5항(화면 코드 단독 표기 금지 · 내부 용어 무설명 사용 금지 · 산출물 파일명을 브리핑 뼈대로 삼지 않기 · 결정을 뭉뚱그리지 않기 · 권고 숨기지 않기) 명문화. 범위 확대 시 「요청 범위 ↔ 실제 범위」 대조와 퇴로 제시, 영향 화면은 「무슨 화면인지·지금 상태·왜 걸리는지」 병기를 못박음. Phase 7 도 같은 서식을 따르도록 연결 | `design-review-intake` Phase 4 · Phase 7 | Phase 4 가 「전문을 제시하고 승인받는다」로만 적혀 **어떻게 설명할지가 없어** 매번 화면 코드 나열로 나갔다. `#252` 에서 사용자가 「더 이해하기 쉽게 설명해 달라」 + 「알릴 6개 화면이 각각 무엇인가」로 **두 번 되물었다** — 승인을 구하는 자리에서 되묻게 만들면 게이트가 제 역할을 못 한다 |
| 2026-09-01 | **착수 통지에 엔드포인트 «목록» 의무화** — `check-issue.py` 에 「`- [x] 엔드포인트 존재` 를 체크했는데 §3 에 경로가 0개면 ⛔」 규칙 신설 + `test-check-issue.py` 6건 추가(총 37건) · `착수가능-초안.md` §3 에 목록 칸 · `field-sources.md` 에 「요구서 표의 왼쪽 두 열만 옮긴다 / 근거 열은 옮기지 않는다」 명문화 | `uiux-client-handoff` (`check-issue.py`·`test-check-issue.py`·`착수가능-초안.md`·`field-sources.md`) | 폼 §3 이 「엔드포인트 존재 — 모두 있다」를 **체크박스로만** 두어 «검증할 수 없는 주장»이 남았다. 실측 — 열린 착수 통지 50건 중 45건이 체크했는데 §3 에 목록을 둔 것은 `#638` **하나**, 요구서가 지정한 호출 229개 중 **208개(90%)가 본문에 흔적 없음**. 프론트는 계약 정본(비공개)을 못 보고 생성 타입에는 전 경로가 들어 있어 「이 화면 몫」을 알 길이 없다. 그 결손이 `P-02-01`·`P-02-03`·`P-02-04`·`P-02-06`·`P-02-11` 다섯 화면에서 **단말 게이팅 호출 누락**으로 드러났다 — 모르면 버튼이 열린 채 굳고 화면은 정상으로 보여 테스트로도 안 잡힌다(`#69`·`#73`·`#74`·`#75`·`#78` ⛔ 통지 발행) |
| 2026-08-31 | **`docs/` 경계 삭제 + 「설계 내용은 전부 `design/` 안에 있다」 명시** — 머리말에 ⭐ 재구성 사실(`a8f46f2` 로 `uiux/`·`deliverables/`·`docs/research/` 소멸 · 지금 자리는 `redirect-map.md`)과 ⛔ `design/raw/` 불가침(확정기록 원문은 고치는 것이 아니라 `design/wiki/` 가 지금 맞는 것을 말한다) 2단락 신설. `design-review-intake` description 에서도 「docs/ 기획 문서 작업은 소관 아님」 제거 | `CLAUDE.md` · `design-review-intake` | `omf-mes#197` 이 요청한 정정 대상 두 파일이 실은 `design/raw/decisions/`(불변)와 `design/wiki/domain-workflow/`(정본)로 이미 옮겨져 있었는데, 하네스가 「`docs/` 는 범위 밖」이라고만 적어 두어 **「그럼 그 정정은 누가 하나」가 답이 없었다.** 실측 — `docs/research/` 추적 파일 **0건**. 경계를 지우는 것만으로는 다음에 또 `docs/` 를 찾게 되므로 **어디를 고치는가**를 함께 못박았다 |
| 2026-09-02 | **계약 JSON 편집 방식 확정 — `json.dumps(indent=1, ensure_ascii=False)` 가 정본 서식을 «바이트 단위로» 재현한다.** 계약 7벌 전건 실측(왕복 후 길이·내용 완전 일치). ⇒ 앞으로 계약 수정은 **JSON 로 읽어 고치고 그대로 쓴다** — 문자열 치환을 쓰지 않는다 | 계약 7벌 편집 절차 | 문자열 치환이 **JSON 으로는 유효하지만 서식이 깨진 결과**를 냈고(`f0e59b8`), 파싱·`check-structure` 둘 다 통과해 **검사기가 못 잡았다.** 사용자가 diff 를 보자고 해서 드러났다. 같은 회차에 요구서 삽입 정규식(`\s*$`)이 개행을 삼켜 **절 제목 하나를 지운** 사고도 났다 — 둘 다 「손으로 문자열을 만지면 구조가 조용히 깨진다」는 한 뿌리다. ⭐ 왕복이 완전 일치한다는 실측이 그 방식을 **불필요하게** 만들었다 |
| 2026-09-03 | ⭐⭐ **업무 방식 개정 — 배정·착수 통지 폐지**(사용자 확정). 「업무 배정을 없애고 설계팀도 개발팀의 업무에 관여하지 않는다. 설계팀은 설계 사항이 변경되면 **무엇이 언제 변경되었는지만 핵심 요약해서 전달**하고, 개발팀은 **설계팀 자료를 열람해 직접 확인**하고 처리 방식도 스스로 정한다. 즉 설계팀은 개발팀의 업무 진행에 대해 **직접 정보를 보유하지 않는다**」 — ① **`design-work-assignment` 스킬 삭제**(존재 이유가 「배정 결정 + 진행 정보 보유 + `Agent : T{n}` 라벨 부착」이라 개정안이 없애기로 한 것과 정확히 일치) ② **`uiux-client-handoff` 재편** — 「착수 가능 통지」 → **「변경 요약 통지」**. 본문 3토막 → 2토막으로 **`## 코드에 무엇을 해야 하나`를 걷었다**(처리 방법은 개발팀 몫). ⭐ 「`null` 로 올 수 있다」는 **사실**은 적되 「널 가드를 넣어 달라」는 **지시**는 적지 않는다로 갈랐다 ③ **`design-review-intake` 4중 → 3중 잠금** — 걷어낸 잠금 ④(「표지로 찾은 화면 0건」)는 **안 지켜진 데이터에 건 게이트**였다(살아 있는 미결 369행 중 244행(66%)에 표지가 없었고, `#349` 에 판정 오류로 살아 있는 5행을 「해소」로 세어 **닫으면 안 되는 이슈가 닫힐 뻔했다**). Phase 8 「표지를 심는다」도 **의무 → 권장**(표지는 «예측»이고 개정안은 «사후 전달»이다) ④ **인계 문서 3종 재편** — 진도표 「통지」 열 삭제 · 미결대장 「표지 → 화면」 역인덱스 93행 삭제 · 인계대장 제목 「99 인계 대장」 → 「99 **설계 진도** 대장」(대상이 개발팀에서 설계팀 자신으로 바뀌었다) ⑤ ⭐ **`변경-요약.md` 신설** — 개정안이 요구하는 「무엇이 언제 바뀌었나」의 정본. **git 이력을 읽어 만든다**(`build-change-digest.py`) — 손으로 요약을 다시 쓰면 두 벌이 되고 한쪽이 낡는다 | `CLAUDE.md` · 스킬 4종 · 생성기 4종 · `handover/` 3종 | 여러 팀이 함께 일하는데 **「어느 화면이 누구에게 영향을 주는지」를 설계팀이 미리 적어 두고 그것을 정본으로 믿는 구조**가 무너지고 있었다 — 실제로 표지 규약은 **3분의 2가 안 지켜졌고**(244/369) 그 데이터에 건 게이트가 사고를 냈다(`#349`). ⭐ 그리고 같은 뿌리가 계수에도 있었다 — 인계대장이 「확정되지 않은 업무 코드 **47종**」을 실었는데 실측하니 **46종이 이미 판정 완료**였다(사전이 값을 갖는 39 · 계약이 「코드 그룹 아님」으로 판정한 7). **최종 인도물이 거짓을 말하고 있었다.** ⇒ 「예측을 정본으로 믿는」 구조를 걷어내고, 팀 사이에는 **사후 통보만** 오가게 한다 |
| 2026-09-02 | **2026-09-01 행이 근거로 든 두 문장을 정정** — ① 「프론트는 계약 정본(비공개)을 못 보고 … 「이 화면 몫」을 알 길이 없다」는 **거짓이다.** 프론트는 설계 저장소를 격리 클론(`.claude/_designref/omf-mes/`)해 계약·요구서·화면 스펙을 **직접 읽는다**(`design-reference.md` 가 `gh repo clone` 을 지시하고 `resolve-spec.mjs` 가 계약 7벌을 병합한다). 프론트가 못 하는 것은 **읽기가 아니라 내용을 공개 저장소로 옮기기**다. ② 다섯 화면의 단말 게이팅 누락(`#69`·`#73`·`#74`·`#75`·`#78`)은 **이 결손의 사례가 아니다** — 착수 통지 5건은 2026-08-11 발행이고 요구서 §3 에 게이팅 행을 «처음» 신설한 것은 2026-08-29 `e38c5d9`(#288) 다. 08-11 에 경로 목록을 성실히 실었어도 **게이팅은 실리지 않았다.** 그 자리를 막은 것은 목록이 아니라 **변경 통지**다. 규칙 자체(§3 목록 의무화)는 유지 — 근거를 「검증할 수 없는 주장을 없앤다」로 바꿔 적었다 | `CLAUDE.md` · `uiux-client-handoff/references/field-sources.md` | 사용자가 직접 반증했다 — 「프론트 개발 팀은 '프론트가 계약 JSON을 안 읽기 때문' 가 아니야. API 설계서를 참고하고 있어.」 **틀린 근거는 규칙을 틀린 방향으로 키운다** — 「프론트는 못 본다」를 전제로 두면 다음 규칙은 계약 내용을 공개 저장소로 옮기는 쪽으로 간다(그것이야말로 금지된 일이다). 인과 ②도 같다 — 막지 못한 사고를 「이 규칙이 막았을 것」으로 적어 두면 실제로 막은 수단(변경 통지)이 안 보인다 |
| 2026-09-03 | ⭐⭐ **하네스 V3 개정 — 「사용자 경유 소통 · 설계 변동 공지 단일 창구」**(`multi-agent-team-workflow-v3.md` 도입 — 이슈 라벨 종류·형식만 V2 를 그대로 쓴다). ① **스킬 개명 2건** — `uiux-client-handoff` → **`design-change-notice`**(화면 단위 «변경 요약 통지» → **배포 선언 시** 직전 태그 `notice/*` → HEAD 를 묶은 **「설계 변동 공지」** 1건을 개발팀 저장소 2곳(`omf-mes-client`·`omf-mes-server`)에 **같은 본문**으로 발행 · 본문은 `build-notice.py` 가 4항(공지 날짜 · 배포 해시 · 설계 자료 목록 표 · 이전 버전과 달라진 «지점»)으로 만들고 `check-notice.py` 가 공개 안전·내용 유출·팀 구분어를 검사 · 발행 뒤 git tag `notice/<YYYYMMDD>` push · ⛔/⚠ 등급표는 `references/change-grades.md` 로 옮겨 «내부» 판단 도구로 남긴다) · `design-review-intake` → **`design-request-intake`**(입력이 「이슈 번호」에서 **「사용자가 건넨 자료」**로 — `gh issue view` 호출 0 · `omf-mes` 에 `[요청 처리]` 자기 이슈를 세우고 · 회신 코멘트 대신 **답변서** `tmp/requests/<날짜>-<식별자>/답변서.md` 를 만들어 **사용자가 전한다** · 자기 이슈 닫기 3중 잠금) ② **`team-issue-protocol` 재편** — §0 「V3 에서 이슈는 두 종류뿐(공지 · 자기 이슈)」 신설 · §1 `omf-mes-server` 를 공지 발행처로 승격 · §2 `Agent : Architect` 신설 예정(문면만) · §3 정본 접두 4종(`[설계 변동 공지]`·`[요청 처리]`·`[설계]`·`[확인 요청]`) + 「V3 이전 유산 — 새로 만들지 않는다」 표 · §4 인바운드 수집(2축 합집합) **삭제** · §5 8유형을 자료 기준으로 · §6 상태 전이를 자기 이슈용으로 · §7 「회신 코멘트」 → **「답변서 서식」+「공지 게시 수단」** · §8 승인 지점에 라벨 생성·tag push 추가 ③ `.gitignore` 에 `/tmp/`(요청 자료·답변서·공지 초안 — 정본은 자기 이슈 코멘트·커밋·공지 이슈) ④ `protect_readonly.py` `GENERATED_RELS` 에 `변경-요약.md` 추가(settings deny 는 Write/Edit 만 막고 **Bash 리다이렉션이 열려 있어** 실제로 오염됐다) ⑤ `build-change-digest.py` 비수렴 수정 — `handover/` 만 건드린 커밋을 세지 않는다(표를 갱신한 커밋이 다음 회차에 또 한 행이 되어 93→94 로 영원히 늘었다) + 머리말에 「개발팀에 알리는 창구는 공지 · 이 표는 내부 이력」 ⑥ V3 원문 `multi-agent-team-workflow-v3.md` 저장(오탈자 포함 그대로 — 고치지 않는다) ⑦ **삭제** — `check-issue.py`·`test-check-issue.py`(38건)·`templates/`·`references/field-sources.md`(착수 통지·회신 코멘트의 폼·검사기라 V3 에 남을 자리가 없다 — 공개 안전 스캔만 `check-notice.py` 로 이식) · `CLAUDE.md` 머리말·트리거 절 재작성 · `uiux-design` 검사기 참조 표 1행 | `CLAUDE.md` · `multi-agent-team-workflow-v3.md`(신설) · 스킬 3종(`design-change-notice`·`design-request-intake`·`team-issue-protocol`) · 에이전트 2종 · `.gitignore` · `.claude/hooks/protect_readonly.py` · `design/schema/generators/build-change-digest.py` · `uiux-design` §검사기 표 | **V3 원문(사용자 확정)** — 규칙 2 「설계팀과 개발팀의 직접 소통은 설계팀이 개발팀에 이슈를 발행하는 "설계 변동 공지"를 제외하면 원칙적으로 모두 금지한다. 필요한 게 있으면 무엇이든 자료를 만들어 사용자에게 전달 요청을하고 자신의 깃헙 저장소에 이슈를 발행하고 요청에 대한 회신을 대기 한다.」 · 규칙 5 「이 공지에는 자세한 내용이 적히는 것을 금지한다. 이 공지의 목적은 "변동 사항이 있다는 사실"을 알리는 것이다.」 ⛔ 하네스와의 **정면 충돌** 자리 — `design-review-intake` Phase 1 이 `gh issue view` 로 개발팀 이슈를 직접 받고 Phase 6a 가 `gh issue comment` 로 직접 회신했다(둘 다 규칙 2 가 금지한 직접 소통이고, 우리도 `omf-mes-server` 에 `[uiux→데이터모델]` 류 이슈를 직접 세우고 있었다). **사용자 판정 4건**(2026-09-03) — Q1 공지 발행처는 **개발팀 저장소 각각**(같은 본문 1건씩) · Q2 발행 단위는 **배포 선언 시 묶음**(직전 `notice/*` 태그 → HEAD) · Q4 답변서는 **루트 `tmp/`** 에 두고 **gitignore**(권고였던 `design/wiki/replies/` 커밋은 버렸다) · Q5 규칙 4 「하는 일·처리할 일」 공개를 **설계팀에도 세운다**(`omf-mes` 자기 이슈). 사용자 추가 지시 「지금 개발팀/설계팀의 이슈를 건드리지는 마」 — 그래서 `Agent : Architect`·`설계 변동 공지` 라벨과 자기 이슈는 **문면만** 세웠고, 이 회차가 GitHub 에 쓴 것은 **PR 하나**뿐이다. ⭐ 실측이 브리핑의 전제 둘을 뒤집었다 — `omf-mes-server` 는 「이슈 0·라벨 0」이 아니라 이슈 21건(접두 있는 17건 전부 설계팀이 낸 `[uiux→데이터모델]`·`[docs→데이터모델]`·`[uiux→server]` — 2026-08-25 실측 0건 뒤 아흐레 사이 V2 가 허용하던 직접 발행이 그만큼 쌓였다. V3 아래서는 새로 만들지 않는 유산이다)·라벨 11종(기본 9 + `Agent : Backend`·`status:in-progress`)이었고, `status:in-progress` 부착은 229건이 아니라 **8건**이다(계획서의 229 는 어디서 온 수인지 확인하지 못했다). 결정 자체(`in progress` 를 만들지 않고 `status:in-progress` 유지)는 그대로다 — 라벨이 실재하고 사용 중이라는 근거는 8건으로도 선다 |
| 2026-09-03 | ⭐ **공지 「달라진 지점」의 입자를 파일로 내린다** — `build-notice.py` 가 절(`§`)·계약 경로·메서드·스키마·`CD-*` 키를 뽑던 코드를 걷고 `git diff --name-status` 만 읽어 **한 파일이 한 줄**(「- 갈래 `경로`」 + 신설·삭제·경로 변경 표지)로 낸다. SKILL §4 표·원칙 표·`check-notice.py` N4 문구·시험 통합 6건(이름 바꿈 사례 추가)을 같이 맞췄다 | `design-change-notice` (`build-notice.py`·`check-notice.py`·`test-check-notice.py`·`SKILL.md`) | 1차 공지 초안(`22c08f5`→`065e5fb`, 642지점·171행)을 사람 게이트에 올리자 사용자가 반려했다 — 「변경 점은 파일단위로, API 계약서 내에 어떤게 바뀌었는지 나열하지말 것」. 절·경로·스키마까지 고르는 것은 개발팀이 열어 볼 자리를 «미리» 골라 주는 일이라 규칙 5 가 금지한 「자세한 내용」의 초입이다. ⛔ 초안은 손으로 못 고치므로(SKILL 금지 표) 생성기를 고쳤다 — 그래야 다음 공지도 같은 입자다 |
| 2026-09-04 | ⭐⭐ **설계팀 멀티 에이전트 3역할(Consultant/Architect/Caster) 체계 도입**(사용자 확정 — `multi-agent-team-workflow-v3-design-team-structure.md` 신설, 원문 그대로 보존). ① **워크트리 3개 신설** — `.claude/scripts/setup-team-worktrees.sh`(재사용 가능한 절차, 클론마다 다시 실행) 신설 + 지금 이 머신에서 실행해 `.claude/worktrees/{consultant,architect,caster}` 실제 생성(각각 최신 `notice/*` 태그·`architect-work` 브랜치·`origin/main`) + `.gitignore`에 `/.claude/worktrees/` 추가 ② **GitHub 라벨 신설** — `omf-mes`에 `Agent : Consultant`(`c5def5`)·`Agent : Caster`(`f9d0c4`) 생성, `Agent : Architect` 설명 정정(3역할 도입 반영) ③ **`design-request-intake` 를 Consultant 전용으로 재편** — 옛 Phase 3(재실측)~5b(PR 병합 확인)를 걷어내고, Phase 2가 판정 결과에 따라 그대로 답변(즉시 답변 유형)하거나 라벨 스왑(`Agent : Consultant`→`Agent : Architect`) + 자기 이슈 코멘트로 **인계**하도록 재편. Phase 6a는 인계 코멘트(병합 해시)를 받아야만 진행 — 옛 #206·#196 순서 불변식을 두 스킬에 걸쳐 유지 ④ **`design-issue-resolution` 신설**(Architect 전용) — 옛 Phase 3~5b를 그대로 계승해 재실측·사람 게이트·반영 PR·병합 확인을 수행하고, 완료하면 답변서를 쓰지 않고 인계 코멘트 + 라벨을 `Agent : Consultant`로 되돌린 뒤 정지(자기 이슈를 닫지 않는다) ⑤ **`design-change-notice` 에 Caster 검증 단계 신설** — 기존 ①(기준 태그) 뒤에 「①-1 검증」을 넣어 `uiux-design` §5 검사기 표 전건을 `origin/main` tip 기준으로 재실행(이 저장소엔 `.github/workflows/`가 없어 CI가 전무하므로 이게 마지막 그물이다), 실패하면 Architect에게 코멘트로 돌려보내고 발행 정지. 태그 형식도 `notice/<YYYYMMDD>` → `notice/<YYYYMMDDHHmmss>-<누적순번>`로 갱신(코드는 `creatordate` 정렬만 써서 무수정, SKILL.md 예시만 갱신) ⑥ **`team-issue-protocol` 갱신** — 라벨 3종 표·§6 상태 전이에 Consultant↔Architect 핸드오프(라벨 스왑 + 자기 이슈 코멘트) 명문화 | `CLAUDE.md` · `multi-agent-team-workflow-v3-design-team-structure.md`(신설) · `.claude/scripts/setup-team-worktrees.sh`(신설) · `.gitignore` · GitHub 라벨(`omf-mes`) · 스킬 4종(`design-request-intake`·`design-issue-resolution`(신설)·`design-change-notice`·`team-issue-protocol`) | **구성안 원문(사용자 확정)** — 「설계팀은 Consultant(상담원)·Architect(설계자)·Caster(캐스터) 3역할을 하며, 이 3역할은 바라보는 설계 자료의 상태가 모두 다르다 … 완전히 격리된 개별 워크트리를 가지고 작업해야 한다 … 절대 담당하는 역할이 아닌 다른 역할의 작업을 하는 것을 금지한다」. 실행 중 사용자가 계획을 한 차례 정정했다 — 워크트리는 "미리 폴더를 만들어두고 사용하는" 것이 아니라 "이 프로젝트를 클론 받은 로컬 환경에서 처음 개발환경 설정 시" 반복되는 절차여야 한다는 지적으로, 그래서 산출물이 1회성 폴더가 아니라 재사용 가능한 스크립트(`setup-team-worktrees.sh`) + 그 스크립트의 첫 실행이 됐다. ⭐ 검증 중 새 사실도 나왔다 — `design/raw/` 보호 훅(`protect_readonly.py`)은 세션의 `$CLAUDE_PROJECT_DIR`가 실제로 그 워크트리일 때만 유효하고, 메인 체크아웃에서 절대경로로 다른 워크트리 파일을 건드리면 보호 밖이다(실측 — 테스트 편집이 막히지 않고 실제로 반영됐다가 즉시 원복함) — 그래서 "각 역할 세션은 반드시 자기 워크트리를 작업 디렉토리로 삼아 새로 실행해야 한다"는 운영 규칙을 위 절에 명문화했다 |
| 2026-09-04 | **`design/wiki/handover/` → `design/wiki/progress/` 개명** — V3 개정으로 이 폴더의 대상이 «개발팀 인계»에서 **«설계팀 자신의 진도»**로 바뀌었는데 폴더 이름만 안 따라왔다. 안의 파일 제목은 이미 따라와 있었다(「99 **설계 진도** 대장」·「화면 진도표」·「변경 요약」). 함께 `99-인계대장.md` → `99-설계진도대장.md` · `build-handover-ledger.py` → `build-progress-ledger.py`. 참조 21파일 48줄 + 상대 링크 5자리. ⛔ **`operation_handover`(교대 인수인계 물리 테이블)·`handoverNote`·`handoverQty` 는 건드리지 않았다** — 글자가 같을 뿐 다른 뜻이다. ⛔ **`redirect-map.md` 의 «구경로»(왼쪽)는 되돌렸다** — 한 번 바꿨다가 그것이 「그때 실제로 있던 이름」임을 깨달았다. 구경로를 고치면 이미 발행된 이슈의 정적 인용을 되짚을 수 없다. 오른쪽(신경로)만 개명을 반영한다. ⚠ `CLAUDE.md` 의 **변경 이력 두 행에 남은 `handover/`도 그대로 둔다** — 같은 이유다 | `design/wiki/progress/`(폴더) · 생성기 5종 · `protect_readonly.py` · `.claude/settings.json` · `redirect-map.md` · `00-index.md` · `design-change-notice` · 계약 1벌(대장 이름 인용 · 등급 ℹ) | `build-handover-ledger.py:22` 가 스스로 「폴더·파일 이름 변경은 이번 범위 밖이라 **적어만 둔다**」로 미뤄 둔 자리다. 이름이 뜻과 어긋난 채로 두면 다음 사람이 「인계 대장이니 개발팀에 넘기는 것」으로 읽는다 — V3 는 정확히 그것을 폐지했다 |
