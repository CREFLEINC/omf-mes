---
name: design-change-notice
description: >-
  Caster(캐스터) 전용 스킬 — 설계 변동 공지. 배포를 선언할 때 직전 공지(git tag `notice/*`)
  이후 main에 merge된 설계 자료 변경을 검증하고, 바뀐 «지점»을 개발팀 저장소 둘
  (CREFLEINC/omf-mes-client · CREFLEINC/omf-mes-server)에 같은 본문의 이슈로 발행한다.
  V3(2026-09-03) 규칙 2 가 허용한 설계팀→개발팀의 **유일한 직접 채널**이다. "공지해", "설계
  변동 공지 발행", "배포 공지 내줘", "개발팀에 변경 알려줘", "Caster 역할 시작하자" 같은 요청에
  쓴다. `.claude/worktrees/caster` 워크트리 안에서만 실행한다. 검증은 `uiux-design` §5 검사기
  표를 main 최신 tip 기준으로 재실행하는 것이고, 실패하면 Caster가 직접 고치지 않고 Architect의
  자기 이슈에 코멘트로 돌려보낸다(역할 경계). 초안은 손으로 쓰지 않고 `scripts/build-notice.py`
  가 git 이력에서 만들고, `scripts/check-notice.py` 를 통과한 뒤 사람 게이트를 거쳐 발행한다.
  ⛔ 「변경 요약 통지」·「착수 가능 통지」·「⛔/⚠ 화면 단위 통지」는 2026-09-03 V3 로 폐지됐다 —
  새로 발행하지 않는다. 개발팀이 보내는 정보 요청·설계 개선 요청의 처리는
  `design-request-intake`(Consultant)·`design-issue-resolution`(Architect) 스킬 소관이다
  (방향이 반대다).
---

# 설계 변동 공지 — 설계팀에서 개발팀으로

이 스킬은 `multi-agent-team-workflow-v3-design-team-structure.md`가 정의하는 **Caster(캐스터)**
역할의 작업 스킬이다. Caster는 "현재 작업 중인 상태를 제외한 검증이 완료된 변경 사항"만 보는
`.claude/worktrees/caster`(`origin/main` 최신 추적)에서만 실행한다 — 다른 워크트리에서 이 스킬을
돌리지 않는다.

## 1. 왜 이 모양인가

`multi-agent-team-workflow-v3.md`(2026-09-03) 두 규칙이 이 스킬의 모양을 정한다.

> **규칙 2.** 설계팀과 개발팀의 직접 소통은 설계팀이 개발팀에 이슈를 발행하는 "설계 변동 공지"를
> 제외하면 원칙적으로 모두 금지한다.

> **규칙 5.** 설계 자료는 설계팀에서 "변동 공지"가 올라왔을 때만 지정된 버전으로 갱신한다. …
> 이 공지에는 자세한 내용이 적히는 것을 금지한다. 이 공지의 목적은 "변동 사항이 있다는 사실"을
> 알리는 것이다. … 무슨 내용이 어떻게 변경되었는지 작성하지마라. 그건 개발팀에서 자료를 보면
> 확인할 수 있다. 주의 : 백엔드, 클라이언트 개발팀을 구분해서 공지를 작성하지마라. 괜한 실수를
> 만든다.

여기서 나오는 네 가지가 이 스킬의 전부다.

| 원칙 | 뜻 | 어디에 박혀 있나 |
| --- | --- | --- |
| **내용이 아니라 지점 — 지점은 파일** | 공지는 「어느 파일이 바뀌었나」까지만 적는다(한 파일이 한 줄). 파일 «안»의 무엇 — 절·경로·스키마·코드 키·값·문장·화살표·「왜」 — 은 적지 않는다. 개발팀이 저장소를 열어 파일을 본다(2026-09-03 사용자 확정 — 「변경 점은 파일 단위로, API 계약서 내에 어떤 게 바뀌었는지 나열하지 말 것」) | `build-notice.py` 는 `git diff --name-status` 만 읽는다 · `check-notice.py` N4 |
| **팀 구분 금지** | 같은 본문이 두 저장소에 나간다. 「백엔드 몫」「클라이언트 몫」을 가르지 않는다 — 선별은 개발팀 몫이다 | `check-notice.py` N3 |
| **발행 = 배포 선언 시 묶음** | 화면 하나 고칠 때마다 내지 않는다. 사용자가 「배포한다」고 선언한 시점에 직전 공지 이후 전부를 **한 건**으로 낸다 | 절차 ① · 금지 표 |
| **이전 버전 = 최신 `notice/*` 태그** | 「직전 공지가 어디였나」는 사람 기억이 아니라 git tag 다. 발행하면 태그를 찍는다 | 절차 ①·⑥ · `build-notice.py --since` 기본값 |

⭐ **실측(2026-09-03)** — `CREFLEINC/omf-mes-server` 는 **PRIVATE**, `CREFLEINC/omf-mes-client` 는
**PUBLIC** 이다. 같은 본문이 둘에 나가므로 **공개 기준 하나로** 검사한다(`check-notice.py` P) —
「서버 쪽은 비공개니까」라는 완화는 없다. 두 저장소 모두 「설계 변동 공지」 라벨이 아직 없다.

## 2. 절차 ①~⑦ (+①-1 검증)

### ① 기준을 정한다 — 직전 공지 태그

```bash
git tag -l 'notice/*' --sort=-creatordate
```

맨 위가 직전 공지다. **태그가 하나도 없으면 첫 공지다** — 생성기가 기준을 추측하지 않는다(종료 2).
사용자에게 기준 해시를 묻고 `--since <해시>` 로 준다. ⚠ 기준 해시는 «개발팀이 지금 붙들고 있는
버전»이어야 한다 — 마지막 착수 통지·마지막 배포 커밋 등 사용자가 안다.

### ①-1 검증한다 — main tip 기준 재실행

이 저장소엔 `.github/workflows/`가 없다 — PR 하나하나는 Architect(`design-issue-resolution`)가
검사기를 돌리고 병합하지만, 여러 PR이 쌓인 뒤 상호작용으로 깨지는 경우를 잡아줄 CI가 없다. 이
단계가 그 마지막 그물이다.

`uiux-design/SKILL.md` §5의 검사기 표(전건)를 현재 `origin/main` tip에 대해 다시 돌린다 — PR
단위가 아니라 **직전 공지 이후 쌓인 전체 변경**을 대상으로 한다. 빨간불이 나오면 Caster가 직접
고치지 않는다 — 원인이 된 변경을 낸 자기 이슈(최근에 `Agent : Architect` 라벨이 붙어 있었던
것)를 찾아 `gh issue comment`로 실패 내용을 남기고 라벨을 `Agent : Architect`로 되돌린 뒤 발행을
정지한다(역할 경계 — 상담원이 캐스터 역할을 하면 안 되는 것의 대칭, 여기서는 캐스터가 설계자
역할을 하면 안 된다). 전건 초록이면 ②로 진행한다.

### ② 초안을 만든다 — 손으로 쓰지 않는다

```bash
python3 .claude/skills/design-change-notice/scripts/build-notice.py            # 최신 notice/* → HEAD
python3 .claude/skills/design-change-notice/scripts/build-notice.py --since <해시>   # 첫 공지
```

`tmp/notices/<YYYY-MM-DD>-<head7>.md` 에 쓴다. 「공지할 것이 없다」(종료 1)면 여기서 끝이다 —
발행할 것이 없다고 사용자에게 알린다. 생성기가 못 뽑는 자리는 **생성기를 고친다**(금지 표).

### ③ 검사한다 — 통과 전에는 발행하지 않는다

```bash
python3 .claude/skills/design-change-notice/scripts/check-notice.py tmp/notices/<파일>.md \
    --title "[설계 변동 공지] <YYYY-MM-DD> · <head7>"
```

⛔ 출력을 `tail`·`head` 로 자르지 않는다 — 마지막 줄만 보면 위반을 놓친다(2026-08 실측).
⛔ 위반이 하나라도 있으면 초안을 고치는 것이 아니라 **생성기 또는 원인 문서**를 고치고 ②부터 다시.
⚠ 경고(N5·ADVISORY)는 사람이 본다 — 「지점이 아니라 설명이 됐나」를 눈으로 판정한다.

### ④ 사람 게이트 — 초안 **전문**을 보인다

발행은 되돌릴 수 없다(공개 저장소). 초안 전문 · 제목 · 기준 해시 → HEAD · 지점 수를 사용자에게
그대로 보이고 승인을 받는다. 요약해 보이지 않는다 — 승인은 본문에 대한 것이다.

### ⑤ 발행한다 — 두 저장소, 같은 본문

③ 이 통과 시 출력한 명령 두 줄을 **그대로** 실행한다.

```bash
gh issue create --repo CREFLEINC/omf-mes-client --title "<제목>" --body-file <초안> --label "설계 변동 공지" --label "uiux→client"
gh issue create --repo CREFLEINC/omf-mes-server --title "<제목>" --body-file <초안> --label "설계 변동 공지"
```

라벨 「설계 변동 공지」 가 없으면 먼저 만든다 — **이것도 승인 게이트다**(저장소에 남는 쓰기다).

```bash
gh label create "설계 변동 공지" --repo CREFLEINC/omf-mes-client --color 1D76DB --description "설계팀 설계 변동 공지(V3 규칙 5)"
gh label create "설계 변동 공지" --repo CREFLEINC/omf-mes-server --color 1D76DB --description "설계팀 설계 변동 공지(V3 규칙 5)"
```

⚠ **첫 발행 주의** — 실측(2026-09-03) 두 저장소 모두 「설계 변동 공지」 라벨이 없다. `omf-mes-server`
에는 GitHub 기본 라벨과 `Agent : Backend`·`status:in-progress` 만 있다. 라벨 없이 `--label` 을 주면
`gh` 가 실패한다.

### ⑥ 태그를 찍는다 — 다음 공지의 기준

```bash
N=$(( $(git tag -l 'notice/*' | wc -l) + 1 ))
TAG="notice/$(date +%Y%m%d%H%M%S)-${N}"
git tag "$TAG" <head>
git push origin "$TAG"
```

태그 명칭 양식은 `notice/<날짜시간>-<누적순번>`이다(구성안 원문) — 누적순번은 지금까지 발행한
공지 총 개수 + 1이며, 날짜시간까지 붙으므로 같은 날 두 번째 발행이라도 옛 `-2` 접미사 규칙은
쓰지 않는다. 태그가 없으면 다음 공지가 이번 지점을 또 싣는다. 발행 직후 찍는다 — 다른 커밋이
끼기 전에. `build-notice.py`의 태그 조회(`latest_notice_tag()`)는 `creatordate` 정렬만 쓰므로
이 형식 변경에 영향받지 않는다 — 코드는 그대로 두고 이 절차문만 갱신했다.

### ⑦ 자기 저장소에 남긴다

Caster의 검증→배포 작업도 `[설계] <제목>` 접두 자기 이슈로 추적한다(`Agent : Caster` 라벨 —
`omf-mes#425` 선례와 같은 형태). 그 이슈에 한 줄 코멘트 —
「공지 발행 client#n · server#m · 태그 `notice/<태그>`」를 남기고 닫는다. 개발팀 이슈는
건드리지 않는다.

## 3. ⛔ 하지 않는 것

| 하지 않는 것 | 왜 |
| --- | --- |
| 본문에 **내용·값·지시·등급·팀 구분**을 적는다 | 규칙 5 그대로. 「`null` 로 올 수 있다」도 값이고 「널 가드를 넣어라」는 지시다. ⛔/⚠ 등급은 설계팀 내부 판단(`references/change-grades.md`)이지 공지 항목이 아니다 |
| 화면 하나 고쳤다고 **즉시 발행**한다 | 발행 단위는 배포 선언이다. 공지가 잦으면 개발팀이 계획을 매번 전면 재검토해야 한다(규칙 5) |
| 개발팀 저장소 이슈를 **닫거나 라벨을 바꾼다** | 개발팀 것이다(규칙 3). 우리는 발행만 한다 — 진행 상태를 보유하지 않는다 |
| 초안을 **손으로 쓰거나 고친다** | 손끝에 「왜 바꿨는지」가 남아 내용이 섞인다. 생성기가 못 뽑으면 생성기를 고친다 — 그래야 다음 공지도 맞는다 |
| 발행한 공지를 **사후 편집**한다 | 공개 이슈의 편집 이력은 남고, 개발팀은 편집 사실을 못 본다. 틀렸으면 새 공지를 낸다(같은 날이면 `notice/<YYYYMMDD>-2`) |
| `--since` 를 **추측**한다 | 태그가 없으면 사용자에게 묻는다. 잘못된 기준은 지점을 빠뜨리거나 두 번 싣는다 |
| 검증(①-1)에서 빨간불 난 원인을 Caster가 **직접 고친다** | 역할 경계 위반 — 설계 자료를 자유롭게 고치는 것은 Architect의 워크트리·권한이다. Caster는 자기 이슈 코멘트로 돌려보내고 발행을 멈춘다 |

## 4. 「달라진 지점」의 입자 — 파일

⭐ 2026-09-03 사용자 확정 — **「변경 점은 파일 단위로, API 계약서 내에 어떤 게 바뀌었는지 나열하지
말 것」**. 첫 공지 초안이 화면의 절·계약의 경로·스키마·코드 사전의 키까지 내(642지점·171행) 게이트에서
반려됐다 — 그것은 개발팀이 파일을 열어 볼 자리를 «미리» 골라 주는 일이라 규칙 5 가 금지한 「자세한
내용」의 초입이다. 지점은 **파일 하나가 한 줄**이고, 갈래는 3항 표의 6줄 그대로다.

| 갈래 | 본문에 나타나는 모양 |
| --- | --- |
| 화면설계서 | `` - 화면설계서 `design/wiki/screens/04/W-04-03-….md` `` |
| API 요구서 | `` - API 요구서 `design/wiki/api-contracts/06-API-요구서-03품질.md` `` |
| API 계약서 | `` - API 계약서 `design/wiki/api-contracts/openapi/quality-03품질.json` `` |
| 코드 사전 | `` - 코드 사전 `design/schema/code-dictionary.md` `` |
| 공유계약 | `` - 공유계약 `design/wiki/decisions-policy/공유계약.md` `` |
| 사양서·요구사항 | `` - 사양서·요구사항 `design/wiki/project-spec/02-SW설계사양서.md` `` |

- 파일 «안»의 무엇이 바뀌었는지는 어느 갈래에서도 내지 않는다 — 절·경로·메서드·스키마·`CD-*` 키·값·문장 전부.
- 표지는 바뀐 «사실»의 종류까지만 — 신설 「(신설)」 · 삭제 「(삭제)」 · 이름이 바뀐 파일 「(경로 변경 · 이전 `옛 경로`)」.
- 갈래 6줄 밖의 파일(검사기·규약·`progress/`·색인·`.html` 배포본)은 싣지 않는다 — 개발팀 열람 대상이 아니다.
- 항목이 160자를 넘으면 검사기 N5 가 경고한다 — 경로 하나가 그 길이를 넘는 일은 없으므로 넘으면 설명이 섞인 것이다.

## 5. 참고 파일

| 파일 | 상태 | 내용 |
| --- | :-: | --- |
| `references/public-boundary.md` | ⭐ 살아 있음 | **핵심** — 공개 저장소에 적어도 되는 것과 안 되는 것 · 실수했을 때 |
| `references/change-grades.md` | 내부용 | ⛔/⚠/ℹ 등급표 — `check-required-change.py`·`check-enum-narrowing.py` 의 등급 정본, `design-request-intake` 답변서 잠금 ②. **공지에는 싣지 않는다** |
| `scripts/build-notice.py` | ⭐ | 초안 생성기 — `--since`(기본 최신 `notice/*`) · `--head` · `--out` · `--date` · `--repo-root` |
| `scripts/check-notice.py` | ⭐ | 검사기 — N1 4항 머리 · N2 해시 실재 · N3 팀 구분어 · N4 내용 유출 · N5 항목 길이(⚠) · N6 자리표시 · P 공개 안전(BLOCKING 10 · ADVISORY 5) · T 제목 |
| `scripts/test-check-notice.py` | ⭐ | 48건 — 공개 안전 이식 · 규칙별 통과/위반 · 임시 git 저장소 통합 |
| `../team-issue-protocol/SKILL.md` | ⭐ | 라벨·제목 접두·저장소 경계의 정본 |
| `../design-request-intake/SKILL.md` | ⭐ | 반대 방향(Consultant) — 개발팀의 정보 요청·설계 개선 요청 접수·판정 |
| `../design-issue-resolution/SKILL.md` | ⭐ | 검증(①-1)에서 빨간불이 나면 돌려보내는 곳(Architect) |
| `../uiux-design/SKILL.md` §5 | ⭐ | 검증(①-1)이 재실행하는 검사기 표의 정본 |

**2026-09-03 V3 로 삭제한 것** — `scripts/check-issue.py` · `scripts/test-check-issue.py`(38건) ·
`templates/`(착수가능-초안·예시) · `references/field-sources.md`. `--reply`·`--change-notice` 모드가
폐지되자 남은 것은 공개 안전 스캔 하나였고 그것은 `check-notice.py` 에 그대로 이식했다. 이미 발행된
착수 이슈 107건이 옛 경로를 인용하지만 그 이슈들은 유산이다 — 죽은 인용을 살려 두려고 폐지 파일을
남기지 않는다. 옛 「유산 — 착수 이슈 본문 개정」 절도 함께 폐지 — 발행된 착수 이슈는 고치지 않는다.
