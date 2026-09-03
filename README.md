# OMF MES — 설계 저장소

이 저장소는 **문서만** 관리한다. 요구사항·업무 흐름·화면 설계·API 계약·결정서 등
**설계의 정본은 전부 [`design/`](design/) 안에 있다.**

## `design/` — 3층 (raw / wiki / schema)

| 층 | 무엇을 담나 | 언제 여나 |
| --- | --- | --- |
| [`design/raw/`](design/raw/) | 설계 과정의 부산물·고객 원자료·확정기록 원문 — **불변**, 고치지 않는다 | 근거를 원문으로 확인할 때 |
| [`design/wiki/`](design/wiki/) | 설계의 결과물 — 요구사항 명세서·화면 설계서·API 요구서·계약서 등 **살아 있는 정본** | **지금 무엇이 맞는지** 알고 싶을 때(가장 자주) |
| [`design/schema/`](design/schema/) | 이 자료를 어떻게 쓰고 채우는지에 대한 규칙·검사기·생성기 | 처음 접근할 때, 새로 문서를 쓸 때 |

자세한 것은 [`design/README.md`](design/README.md) 와 [`design/wiki/00-index.md`](design/wiki/00-index.md).

⛔ **`design/raw/` 의 어떤 줄이 지금은 틀렸다**고 해서 원문을 고치지 않는다 — 지금 무엇이
맞는지는 **`design/wiki/` 가 말한다.**

## ⭐ 옛 경로를 가리키는 인용을 만났다면

2026-08-25 재구성(`a8f46f2`)으로 **`uiux/` · `deliverables/` · `docs/research/` 세 구조가
사라졌다.** 그 이전에 발행된 이슈·문서가 그 경로를 가리키면 **죽은 인용**이다. 지금 자리는
[`design/schema/redirect-map.md`](design/schema/redirect-map.md) 가 구경로→신경로 전건으로
말한다. 고칠 곳을 옛 경로에서 찾지 않는다.

## `docs/` 에 남은 것 — 설계 정본이 아니다

`docs/` 디렉터리는 **아직 있다**(추적 199파일). 다만 **설계 정본은 여기에 없다** —
남아 있는 것은 다음 셋이다.

| 경로 | 무엇 |
| --- | --- |
| `docs/planning/` | 고객 발표자료·개발제안서·WBS·HW 구성 제안서 등 **대외 산출물과 그 원본** |
| `docs/_workspace/` | 옛 작업 공간(`figjam-team` · `doc-team`) |
| `docs/.claude/` · `docs/CLAUDE.md` | 구 문서 하네스 — 현행 하네스는 저장소 루트의 [`CLAUDE.md`](CLAUDE.md) 다 |

⏳ **`docs/` 를 어떻게 처분할지는 아직 정해지지 않았다**(사용자 판정 대기). 이 README 는
「설계 정본이 어디인가」만 말한다 — 남은 것의 처분은 별건이다.

## 코드는 어디에 있나

| 대상 | 저장소 |
| --- | --- |
| 백엔드 API (NestJS) | [CREFLEINC/omf-mes-server](https://github.com/CREFLEINC/omf-mes-server) |
| 웹 프론트 | [CREFLEINC/omf-mes-client](https://github.com/CREFLEINC/omf-mes-client) |

백엔드는 2026-07-29에 이 저장소의 `apps/api/`에서 분리했다. 그때까지의 커밋 이력은
분리된 저장소로 함께 옮겼으므로, `apps/api` 시절의 `git log`·`git blame`도 그쪽에서 이어 볼 수 있다.
이 저장소의 이력에도 그대로 남아 있다(`git log -- apps/api`).

## 개발팀에 변경을 어떻게 알리나

설계팀 → 개발팀의 직접 소통은 **「설계 변동 공지」 이슈 하나뿐**이다
(`multi-agent-team-workflow-v3.md` 규칙 2). 공지는 **무엇이 언제 바뀌었는지**만 파일
단위로 알리고, 내용은 개발팀이 이 저장소를 직접 열람해 확인한다. 절차는
`.claude/skills/design-change-notice/`.
