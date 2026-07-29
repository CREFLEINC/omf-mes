# OMF MES — 문서 저장소

이 저장소는 **문서만** 관리한다. 요구사항·워크플로우·데이터모델링·결정서 등 기획과 설계의 정본이
`docs/` 아래에 있다.

## 코드는 어디에 있나

| 대상 | 저장소 |
| --- | --- |
| 백엔드 API (NestJS) | [CREFLEINC/omf-mes-server](https://github.com/CREFLEINC/omf-mes-server) |

백엔드는 2026-07-29에 이 저장소의 `apps/api/`에서 분리했다. 그때까지의 커밋 이력은
분리된 저장소로 함께 옮겼으므로, `apps/api` 시절의 `git log`·`git blame`도 그쪽에서 이어 볼 수 있다.
이 저장소의 이력에도 그대로 남아 있다(`git log -- apps/api`).
