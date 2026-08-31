# omf-mes 설계팀 저장소 하네스

이 저장소는 `multi-agent-team-workflow-v2.md`가 정의하는 **설계팀 저장소**다. 산출물 정본은
`design/`(raw/wiki/schema 3층 — `design/README.md` 참조)이고, 이 파일은 하네스 존재를 알리는
포인터만 담는다. 에이전트·스킬 목록은 `.claude/agents/`·`.claude/skills/`에서 직접 확인한다.

⭐ **설계 내용은 전부 `design/` 안에 있다.** 2026-08-25 재구성(`a8f46f2`)으로 `uiux/`·
`deliverables/`·`docs/research/`가 사라졌다 — 옛 이슈·문서가 그 경로를 가리키면 죽은 인용이고,
지금 자리는 `design/schema/redirect-map.md`가 말한다. 고칠 곳을 그 경로에서 찾지 않는다.

⛔ **`design/raw/`는 고치지 않는다** — 확정기록 원문·고객 원자료의 시점 고착본이라 훅이 쓰기를
막는다. 「확정기록의 그 줄이 지금은 틀렸다」는 원문을 고쳐서가 아니라 **`design/wiki/`가 지금
무엇이 맞는지 말하는 것**으로 해소한다(작성 규칙 5의 정합주·구표기 보존이 그 수단이다).

## 트리거

- **설계 검토 요청 처리**(개발팀이 `omf-mes`에 올린 `[검토 요청]` 이슈에 답하기, "232번 검토 요청
  처리해줘", "개발팀 질의 확인해줘" 등) → `design-review-intake` 스킬을 사용하라.
- **개발 업무 배정**(사용자가 직접 지시할 때만) → `design-work-assignment` 스킬을 사용하라.
- 화면 설계·계약 작업 자체는 `uiux-design`, 프론트로 넘기는 착수/변경 통지는
  `uiux-client-handoff` 스킬을 사용하라(기존).
- 단순 질문·조회는 스킬 없이 직접 응답 가능.

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
