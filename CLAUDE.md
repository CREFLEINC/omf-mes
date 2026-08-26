# omf-mes 설계팀 저장소 하네스

이 저장소는 `multi-agent-team-workflow-v2.md`가 정의하는 **설계팀 저장소**다. 산출물 정본은
`design/`(raw/wiki/schema 3층 — `design/README.md` 참조)이고, 이 파일은 하네스 존재를 알리는
포인터만 담는다. 에이전트·스킬 목록은 `.claude/agents/`·`.claude/skills/`에서 직접 확인한다.

## 트리거

- **설계 검토 요청 처리**(개발팀이 `omf-mes`에 올린 `[검토 요청]` 이슈에 답하기, "232번 검토 요청
  처리해줘", "개발팀 질의 확인해줘" 등) → `design-review-intake` 스킬을 사용하라.
- **개발 업무 배정**(사용자가 직접 지시할 때만) → `design-work-assignment` 스킬을 사용하라.
- 화면 설계·계약 작업 자체는 `uiux-design`, 프론트로 넘기는 착수/변경 통지는
  `uiux-client-handoff` 스킬을 사용하라(기존).
- 단순 질문·조회는 스킬 없이 직접 응답 가능.
- `docs/.claude/`(구 문서·FigJam 하네스)는 이 하네스와 별개이며 이번 재구성 범위 밖이다 — 건드리지
  않는다.

## 변경 이력

| 날짜 | 변경 내용 | 대상 | 사유 |
| --- | --- | --- | --- |
| 2026-08-25 | 초기 구성 — 에이전트 2종(`design-review-analyst`·`design-doc-writer`) + 스킬 3종 신설(`design-review-intake`·`design-work-assignment`·`team-issue-protocol`) + `uiux-client-handoff` 수정(죽은 `issue-management` 참조 제거) + 읽기전용 보호 훅을 `design/raw/`로 재배선 | 전체 | `multi-agent-team-workflow-v2.md` 도입 — 인바운드 설계 검토 요청 처리 절차가 하네스에 전무했고, `[검토 요청]` 이슈 #232가 접수돼 있었다 |
| 2026-08-26 | 회신 게시 경로를 못박음 — `design-review-intake` Phase 6a 에 `gh issue comment` 명령 + `⛔ gh issue create 금지` 명시, `team-issue-protocol` §7 에 게시 수단 절 신설, `check-issue.py` 에 `--reply` 모드 추가(폼 구조·중복 발행 검사 끄고 머리 표기 검사 켬) | `design-review-intake` · `team-issue-protocol` · `uiux-client-handoff/scripts/check-issue.py` | `omf-mes-client#442` 처리 중 구멍 3개가 드러났다 — ① Phase 6a 에 실행 명령이 없는데 하네스의 유일한 `gh issue` 예시가 `create` 뿐이라 「새 이슈 발행」이 가장 가까운 실행 패턴이었다 ② §7 이 정본으로 못박은 머리 표기를 `#232`·`#222` 가 이미 어겼는데 검사기가 없었다 ③ 회신을 착수 통지 폼으로 검사해 「막지 않아도 되는 ⛔」 9건이 떴다 |
| 2026-08-26 | 「인바운드=비공개」 가정 정정 — 검토 요청이 공개 저장소(우리 아웃바운드 이슈)의 코멘트로 올 수 있음을 §1 에 명시, 가시성 확인 명령 추가 | `team-issue-protocol` §1 · `design-review-intake` Phase 6a | `omf-mes-client#442` 가 첫 사례 — 공개 저장소로 회신이 나가는데 §1 은 「인바운드에는 금지어 검사 불요」로 적혀 있었다 |
| 2026-08-25 | `in progress` 라벨 신설 취소 — 기존 `status:in-progress`(사용 2건)로 대체. `help wanted` 부착 기준을 "백엔드 결정 대기"가 아니라 "우리 회신이 미완성인가"로 정정 | `team-issue-protocol` | #232를 `design-review-intake`로 첫 실행한 `design-review-analyst`가 라벨 실측 오류를 잡아냄(§7-5 운영 피드백) |
