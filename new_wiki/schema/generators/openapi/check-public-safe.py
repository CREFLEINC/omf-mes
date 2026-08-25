# -*- coding: utf-8 -*-
"""OpenAPI 정본의 description 이 공개돼도 되는지 검사한다. (이슈 #92)

왜 필요한가
  omf-mes-client 는 **공개 저장소**다. 그 저장소의 `pnpm gen:api` 가 이 정본을 읽어
  타입을 생성하는데, openapi-typescript 가 `description` 을 JSDoc 주석으로 그대로 옮긴다.
  생성물(packages/api-client/src/generated/api.d.ts)은 공개 저장소에 커밋된다.
  즉 **description 에 적은 것은 공개된다.**

  `x-internal-note` 는 생성물에 실리지 않는다(openapi-typescript 7.13.0 실측).
  내부용 서술은 그쪽에 둔다.

무엇을 막나
  ① 비공개 문서 경로 — deliverables/… · docs/…
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
# Tier 0 — OpenAPI JSON 정본. Phase 5 컷오버(2026-08-25)로 new_wiki/wiki/api-contracts/openapi/가 정본 위치다.
CONTRACTS_DIR = os.path.join(HERE, "..", "..", "..", "wiki", "api-contracts", "openapi")

RULES = [
    ('비공개 문서 경로', re.compile(r'\b(?:deliverables|docs|uiux)/'),
     'x-internal-note 로 옮기거나 이슈 번호로 대체한다'),
    # 절 기호는 공유계약이 늘면 함께 늘린다 — 2026-08-06 현재 §A~§L
    ('설계 규칙 요약', re.compile(r'공유계약\s+[A-L]-\d+\s*\('),
     '괄호 안 요약을 x-internal-note 로 옮기고 식별자만 남긴다'),
    ('설계 진행 상태', re.compile(r'미결|미착지'),
     '진행 상태는 x-internal-note 로. 소비자에게 필요한 경고는 「확정되지 않았다」로 바꿔 남긴다'),
    ('사내 운영 용어', re.compile(r'\bWBS\b|통합 Agent|SQL \d+ 주석'),
     'x-internal-note 로 옮긴다'),
    # ⛔ 구현팀이 찾아 알려 왔다(client#102) — 그쪽 경계 검사기는 «경로 형태»만
    #    잡아서 「06-API-요구서 §4-3」 같은 «맨 문서 이름»을 통과시켰다.
    #    ⭐ 화면 ID(`W-06-02 §4-A`)와 조항 번호(`공유계약 B-1`)는 «잡지 않는다» —
    #       이 저장소는 제품 자신이라 화면 ID 가 정상이고(실측 554곳), 조항은
    #       번호만 부르고 내용을 안 옮긴다. 가르는 기준은 «공개된 계약 안에서
    #       뜻이 통하는가»다. 문서 파일명은 소비자가 열 수 없는 곳을 가리킨다.
    ('비공개 문서 이름',
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
            if k == 'description' and isinstance(v, str):
                out.append((path, v))
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

    print('%s — description %d개 검사' % (os.path.basename(path), len(descs)))
    if not violations:
        print('✅ 공개돼도 되는 상태입니다.')
        return 0

    print('⛔ 위반 %d건\n' % len(violations))
    for name, loc, snippet, fix in violations:
        print('  [%s] %s' % (name, loc))
        print('    …%s…' % snippet)
        print('    → %s' % fix)
    print('\n생성물(api.d.ts)은 공개 저장소에 커밋됩니다. 고치고 다시 검사하세요.')
    return 1


def main():
    targets = sys.argv[1:] or sorted(glob.glob(os.path.join(CONTRACTS_DIR, '*.json')))
    if not targets:
        print('검사할 정본이 없습니다.')
        return 1
    return max(check(t) for t in targets)


if __name__ == '__main__':
    sys.exit(main())
