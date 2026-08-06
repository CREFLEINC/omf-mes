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
  python3 check-public-safe.py [spec.json]
  통과하면 0, 위반이 있으면 1 을 돌려준다.
"""
import json, re, sys, io, os

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(HERE, 'mdm-기준정보.json')

RULES = [
    ('비공개 문서 경로', re.compile(r'\b(?:deliverables|docs)/'),
     'x-internal-note 로 옮기거나 이슈 번호로 대체한다'),
    ('설계 규칙 요약', re.compile(r'공유계약\s+[A-K]-\d+\s*\('),
     '괄호 안 요약을 x-internal-note 로 옮기고 식별자만 남긴다'),
    ('설계 진행 상태', re.compile(r'미결|미착지'),
     '진행 상태는 x-internal-note 로. 소비자에게 필요한 경고는 「확정되지 않았다」로 바꿔 남긴다'),
    ('사내 운영 용어', re.compile(r'\bWBS\b|통합 Agent|SQL \d+ 주석'),
     'x-internal-note 로 옮긴다'),
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


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    spec = json.load(io.open(path, encoding='utf-8'))
    descs = collect(spec)

    violations = []
    for loc, d in descs:
        for name, rx, fix in RULES:
            m = rx.search(d)
            if m:
                s = max(0, m.start() - 40)
                violations.append((name, loc, d[s:m.end() + 40].replace('\n', ' '), fix))

    print('description %d개 검사' % len(descs))
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


if __name__ == '__main__':
    sys.exit(main())
