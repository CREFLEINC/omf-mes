# new_wiki — omf-mes 설계 자료 (Raw / Wiki / Schema)

> 🚧 **재구성 진행 중** — 기존 `uiux/`·`deliverables/`·`docs/`가 아직 정본이다. 이 구조는
> 검증이 끝나기 전까지 병행 운영되는 시범 구조다. 자세한 배경은 `schema/00-authoring-rules.md`
> 및 저장소 루트 계획 문서를 참고한다.

이 프로젝트 자료를 세 영역으로 나눈다([karpathy의 LLM wiki 패턴](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 참조):

| 영역 | 무엇을 담나 | 먼저 볼 사람 |
| --- | --- | --- |
| **[`raw/`](raw/)** | 설계 과정에서 생긴 부산물·고객 원자료·확정기록 원문 — **불변**, 재작성하지 않는다 | 근거를 원문으로 확인하고 싶을 때 |
| **[`wiki/`](wiki/)** | 설계의 결과물 — 요구사항 명세서·프로젝트 스펙·UI/UX 설계도·API 계약서 등, 검토·재작성된 **살아있는 정본** | 지금 무엇이 맞는지 알고 싶을 때(가장 자주) |
| **[`schema/`](schema/)** | 이 위키를 어떻게 채우고 쓰는지에 대한 규칙 | 처음 이 자료에 접근할 때, 또는 새로 문서를 쓸 때 |

## 처음이라면

1. `schema/00-authoring-rules.md` — 작성 규칙 4가지
2. `wiki/00-index.md` — 전체 카탈로그 + 독자군(설계팀/개발팀/영업팀)별 추천 경로
3. `wiki/00-log.md` — 최근 갱신 이력

## 원칙

- **Tier 0 자료(OpenAPI 계약, 물리 모델, 확정기록 원문 등)는 절대 복제하지 않는다** — 링크만
  건다. 상세: `schema/rewrite-tiers.md`.
- 데이터 모델링 자료는 이 저장소의 범위가 아니다 — 백엔드팀 소관이다. `schema/data-model-boundary.md`.
