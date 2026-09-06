# -*- coding: utf-8 -*-
"""OpenAPI 정본의 description 이 «API 표면»으로 성립하는지 검사한다. (이슈 #92)

왜 필요한가
  `pnpm gen:api` 가 이 정본을 읽어 타입을 생성하는데, openapi-typescript 가
  `description` 을 JSDoc 주석으로 그대로 옮긴다. 생성물
  (packages/api-client/src/generated/api.d.ts)은 소비자 저장소에 커밋되어 **구현팀의
  에디터에 뜬다.** 즉 **description 에 적은 것은 계약의 «표면»이 된다** — 우리 설계
  부기를 거기 두면 계약이 API 를 설명하지 않게 된다.

  `x-internal-note` 는 생성물에 실리지 않는다(openapi-typescript 7.13.0 실측).
  내부용 서술은 그쪽에 둔다.

⚠ 2026-09-06 — 이 검사기의 «이유»가 바뀌었다. 이 저장소는 공개이고 보안 제약도 없다
  (사용자 확정). 그래도 규칙은 그대로 둔다 — 뿌리가 «비밀»이 아니라 **API 표면 분리**이기
  때문이다. `description` 은 생성 타입 주석으로 복사되어 소비자의 코드에 남는다. 거기에
  설계 부기(문서 경로·미결 상태·사내 용어)가 섞이면 계약이 API 를 설명하지 않게 된다.
  ⇒ 규칙 이름에서 「비공개」를 걷었다 — 막는 이유는 감추기가 아니라 «계약은 API 를 말한다»다.

무엇을 막나
  ① 설계 문서 경로 — design/… · docs/…
  ② 설계 규칙 요약 — 「공유계약 X-N(요약문)」의 괄호. 식별자만 남긴다
  ③ 설계 진행 상태 — 미결 · 미착지
  ④ 사내 운영 용어 — WBS · 통합 Agent · SQL NNN 주석

사용법
  python3 check-public-safe.py [spec.json ...]
  인자를 생략하면 이 폴더의 정본 전부를 검사한다.
  통과하면 0, 위반이 있으면 1 을 돌려준다.
"""
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Tier 0 — OpenAPI JSON 정본. Phase 5 컷오버(2026-08-25)로 design/wiki/api-contracts/openapi/가 정본 위치다.
CONTRACTS_DIR = os.path.join(HERE, "..", "..", "..", "wiki", "api-contracts", "openapi")

RULES = [
    ('설계 문서 경로', re.compile(r'\b(?:design|docs|deliverables|uiux)/'),
     'x-internal-note 로 옮기거나 이슈 번호로 대체한다'),
    # 절 기호는 공유계약이 늘면 함께 늘린다 — 2026-08-06 현재 §A~§L
    ('설계 규칙 요약', re.compile(r'공유계약\s+[A-L]-\d+\s*\('),
     '괄호 안 요약을 x-internal-note 로 옮기고 식별자만 남긴다'),
    ('설계 진행 상태', re.compile(r'미결|미착지'),
     '진행 상태는 x-internal-note 로. 소비자에게 필요한 경고는 「확정되지 않았다」로 바꿔 남긴다'),
    # ⭐ 2026-09-02 신설(omf-mes#367) — 고객 «실물» 식별자. design-change-notice 의
    #    check-notice.py(옛 check-issue.py) 는 이 둘을 이미 막고 있었는데 «계약» 쪽에는 없었다. 같은 값이
    #    이슈로 나가면 막히고 계약 example 로 나가면 통과하던 상태다(실측 — 실제로
    #    통과했다). 규칙을 이쪽에도 둔다. 신설 시점 위반 0건.
    ('실 사번 의심', re.compile(r'\b9\d{5}\b'),
     '실 사번 형식(6자리·90****)이다. 합성값을 쓴다'),
    ('실 LOT 번호 의심', re.compile(r'\b[A-Z]{1,3}-?20\d{6}-\d{3,4}\b'),
     '실 LOT 번호 형식이다. 합성값을 쓴다'),

    ('사내 운영 용어', re.compile(r'\bWBS\b|통합 Agent|SQL \d+ 주석'),
     'x-internal-note 로 옮긴다'),
    # ⛔ 구현팀이 찾아 알려 왔다(client#102) — 그쪽 경계 검사기는 «경로 형태»만
    #    잡아서 「06-API-요구서 §4-3」 같은 «맨 문서 이름»을 통과시켰다.
    #    ⭐ 화면 ID(`W-06-02 §4-A`)와 조항 번호(`공유계약 B-1`)는 «잡지 않는다» —
    #       이 저장소는 제품 자신이라 화면 ID 가 정상이고(실측 554곳), 조항은
    #       번호만 부르고 내용을 안 옮긴다. 가르는 기준은 «공개된 계약 안에서
    #       뜻이 통하는가»다. 문서 파일명은 «계약 밖»을 가리킨다 — 생성 타입 주석에
    #       그것이 남으면 소비자 코드가 이 저장소의 파일 구조를 인용하게 된다.
    #       ⚠ 열람 가능 여부의 문제가 아니다(이 저장소는 공개다 · 2026-09-06).
    ('설계 문서 이름',
     re.compile(r'(?:\d\d[\s\-]?)?API[\s\-]?요구서[\w가-힣\-]*\s*§'
                r'|\d\d\s요구서\s*§'
                r'|\d\d\s계약\s\d단계\s*§'
                r'|화면상세스펙'),
     '문서 이름을 x-internal-note 로 옮긴다 — 화면 ID·조항 번호는 그대로 두어도 된다'),
]


def collect(node, path='$'):
    """(경로, description) 목록. x-internal-note 안은 보지 않는다."""
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            # ⭐ example 도 본다(2026-09-02 · omf-mes#367) — 목 서버가 그 값을 그대로
            #    내려주고 생성 타입에도 실린다. description 만 보던 동안 계약 example 로
            #    나간 고객 실물 사번을 이 검사기가 통과시켰다.
            if k in ('description', 'example') and isinstance(v, (str, int)):
                out.append((path if k == 'description' else path + '.example', str(v)))
            elif k != 'x-internal-note':
                out.extend(collect(v, '%s.%s' % (path, k)))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.extend(collect(v, '%s[%d]' % (path, i)))
    return out


def check(path):
    spec = json.load(io.open(path, encoding='utf-8'))
    descs = collect(spec)

    violations = []
    for loc, d in descs:
        for name, rx, fix in RULES:
            m = rx.search(d)
            if m:
                s = max(0, m.start() - 40)
                violations.append((name, loc, d[s:m.end() + 40].replace('\n', ' '), fix))

    print('%s — description·example %d개 검사' % (os.path.basename(path), len(descs)))
    if not violations:
        print('✅ description 이 API 표면으로 성립합니다.')
        return 0

    print('⛔ 위반 %d건\n' % len(violations))
    for name, loc, snippet, fix in violations:
        print('  [%s] %s' % (name, loc))
        print('    …%s…' % snippet)
        print('    → %s' % fix)
    print('\n생성물(api.d.ts)은 구현팀 에디터에 그대로 뜹니다 — 설계 부기는'
          ' x-internal-note 로 옮기세요.')
    return 1


def main():
    targets = sys.argv[1:] or sorted(glob.glob(os.path.join(CONTRACTS_DIR, '*.json')))
    if not targets:
        print('검사할 정본이 없습니다.')
        return 1
    return max(check(t) for t in targets)


if __name__ == '__main__':
    sys.exit(main())
