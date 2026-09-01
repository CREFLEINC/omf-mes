#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""공유계약 조항 인용 검사기.

## 왜 만들었나

**조항을 잘못 인용한 것이 세 판 연속**이다(11·12·13차).

    11차  「인벤토리가 틀렸다」          물은 것이 화면인데 테이블로 답했다
    12차  「B-18 이 C-2 를 불필요하게」  다른 문제였다
    13차  「L-3 은 파티션 얘기」          본칙을 예외로 축소했다

셋 다 **설계 결론은 맞고 근거가 틀렸다.** 사람이 원문을 열어야 걸렸다.

## ⛔ 못 잡는 것을 먼저 적는다

**이 검사기는 13차 건을 못 잡는다.** 만들면서 실측으로 확인했다.

    L-3 제목    「기간 필터를 필수로 한다 — 파티션 테이블은 파티션 키를 강제」
    틀린 인용   「L-3(파티션 키 강제)은 … 파티션 테이블 얘기이고」
    → 제목에 「파티션 키를 강제」가 실제로 있다. 낱말 대조로는 안 걸린다

⚠ **처음에는 「제목 낱말이 인용문에 있는가」로 만들었고 1,143건이 떴다** — 인용
대부분이 `(G-2)` 같은 짧은 참조라 제목을 반복하지 않는다. **90%에서 울리는 것은
신호가 아니다.** 그래서 뺐다.

**의미 오독은 기계가 못 잡는다.** 관계 주장(대체한다 / 얘기다 / 같은 것이다)의
참·거짓은 사람이 원문을 열어야 한다. 이 검사기는 **그 앞단의 기계적 오류**만 막는다.

## 잡는 것 셋

    ⛔ 실재하지 않는 조항을 인용했다              오타·폐지·글자 착각
    ⚠ 글로스가 조항 제목과 한 낱말도 겹치지 않는다   「X-N(설명)」 형태만 · 좁게
    ⚠ 공유계약 G-N 과 ds-gap G-N 을 섞어 썼다      ⭐ 만들면서 발견한 구조 문제
    ℹ 한 번도 인용되지 않은 조항                   계약 위생 — 죽은 조항 탐지

## ⭐ 만들면서 나온 발견 — `G-N` 이 두 체계에서 다른 것을 가리킨다

    공유계약 G-9   「모르는 값과 없는 값을 같은 모양으로 그리지 않는다」
    ds-gap  G-9   「파일 업로드」

**둘 다 `G-9` 로 쓰인다.** 스펙이 「G-9(파일 업로드)」라 적으면 사람은 문맥으로
읽지만 **기계도, 처음 읽는 사람도 갈린다.** 실측 34건 중 다수가 이것이다.

→ 이 검사기는 **글로스가 ds-gap 갭 이름과 맞으면 그렇게 알려 준다.**
   표기를 `ds-gap G-9` 로 구분하는 것이 근본 해결이다.

사용:
    python3 verify-contract-citation.py
    python3 verify-contract-citation.py --strict          # ⚠ 도 실패로 친다
    python3 verify-contract-citation.py --dir uiux/2026-08-11-화면상세스펙-확대14차
    python3 verify-contract-citation.py --unused          # ℹ 목록도 출력
"""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
CONTRACT = os.path.join(ROOT, 'design', 'wiki', 'decisions-policy', '공유계약.md')
DSGAP = os.path.join(ROOT, 'design', 'raw', 'process', 'uiux', '화면상세스펙-공통', 'ds-gap.md')
UIUX = os.path.join(ROOT, 'design', 'wiki', 'screens')

# ── 조항처럼 보이지만 조항이 아닌 것 — 실측으로 확인한 세 갈래.
#
#   I-N   §I 「확정 ↔ 하류 불일치 대장」 항목 (실측: `### I-N.` 헤딩 0건)
#   E-N   고객 회신 번호와 §E 조항(E-1~E-4)이 같은 모양이다. 회신이 E-14 까지
#         있어 겹친다 → **E-3 이상은 회신으로 본다**
#         ⚠ **대가가 크다** — E-3(터치 규격)은 **POP 22화면 전부**가 인용하고
#            E-4(스크롤·접기 구획)도 POP 전용이라 **검사 사각이 POP 에 집중**된다.
#            문맥어(「회신 E-3」·「E-3 판정유형」)로 가르는 것이 근본 해결이나,
#            지금은 **오탐 0** 을 우선해 통째로 제외한다.
#   H-N   물리 모델 변경 번호([H-4] 등). §H 는 조항 절이 아니다
PREFIX_NOT_CLAUSE = ('I-',)
AMBIGUOUS = {'E-%d' % i for i in range(3, 30)} | {'H-%d' % i for i in range(1, 10)}
NOT_CLAUSE = re.compile(r'회신\s*$|고객\s*$|\[\s*$')

# ⭐ 이 검사기가 «권하는» 표기를 이 검사기가 인식하지 못하고 있었다.
#    「표기를 `ds-gap G-N` 으로 구분하면 사라진다」고 안내해 놓고, 그대로 써도
#    그대로 걸렸다 — 조언을 따를 수 없는 조언이었다(2026-08-21 · omf-mes#170).
DSGAP_PREFIX = re.compile(r'ds-gap`?\s*$')

# 글로스 대조에서 버릴 낱말 — 조사·형식어
STOP = {
    '한다', '하지', '않는다', '있다', '없다', '것을', '것이', '되는', '위한', '대한',
    '경우', '때는', '전에', '먼저', '함께', '그대로', '같은', '같다', '아니라',
    '아니다', '으로', '에서', '까지', '보다', '하나', '규칙', '조항', '적는다',
    '쓴다', '본다', '정한다', '둔다', '만든다', '신설', '확장', '보완', '단서',
}

CLAUSE_HEAD = re.compile(r'^#{3,4} ([A-L]-\d+(?:-\d+)?)\.\s*(.+?)\s*(?:✅|⬜|⛔|\*\*\[|$)')
# ⛔ 2026-09-01 정정(omf-mes#328) — `###` 만 잡아 `####` 소절(예: `#### B-8-1.`)을
#    「실재하지 않는 조항」으로 오탐했다. `###`·`####` 를 둘 다 잡는다.
# ⚠ 첫 칸이 «표시 기호로 시작하는» 행을 놓치고 있었다 — `| ⛔⛔ **G-14** | …`
#    2026-08-21 실측: 표에 있는 16개 중 11개만 읽고 있었다(G-14·G-15 가 안 보였다).
#    G-14 는 구현팀이 실제로 헷갈린 항목이라(omf-mes#170) 안 보이면 검사기가 제 일을 못 한다.
#    ⛔ 이름 칸 «안»에 굵게 표기가 있는 G-3 은 아직 못 읽는다 — 그 행은 표가 둘이라
#       고치면 기존 5개의 이름이 다른 표 것으로 바뀐다(실측). 별건으로 둔다.
DSGAP_ROW = re.compile(r'^\|\s*[^|A-Za-z0-9]*(G-\d+)\*{0,2}\s*\|\s*\*{0,2}([^|*]+?)\*{0,2}\s*(?:\*\(|\|)')
CITE = re.compile(r'(?<![A-Za-z0-9])([A-L]-[1-9]\d*(?:-[1-9]\d*)?)(?![0-9])')
GLOSS = re.compile(
    r'(?<![A-Za-z0-9])([A-L]-[1-9]\d*(?:-[1-9]\d*)?)\s*\(([^)]{2,60})\)')
WORD = re.compile(r'[가-힣A-Za-z_][가-힣A-Za-z0-9_]*')


def load_clauses():
    out = {}
    with open(CONTRACT, encoding='utf-8') as f:
        for line in f:
            m = CLAUSE_HEAD.match(line)
            if m:
                title = re.sub(r'\*\*|⭐|⚠|⛔|~~|`', '', m.group(2)).strip()
                out[m.group(1)] = title
    return out


def load_dsgap():
    """ds-gap 갭 대장에서 G-N → 요소명을 읽는다."""
    out = {}
    if not os.path.exists(DSGAP):
        return out
    with open(DSGAP, encoding='utf-8') as f:
        for line in f:
            m = DSGAP_ROW.match(line)
            if m:
                out.setdefault(m.group(1), re.sub(r'~~|`', '', m.group(2)).strip())
    return out


def stems(text):
    """낱말을 뽑되 **어간 2자**로 자른다 — 조사 변화를 흡수한다.

    「필터를」·「필터는」·「필터가」가 다 「필터」로 모인다. 2자는 짧지만
    한국어 명사 다수가 2자이고, 이 검사는 **한 낱말도 안 겹치는 것**만
    잡으므로 넓게 잡는 편이 오탐을 줄인다.
    """
    out = set()
    for w in WORD.findall(text):
        if len(w) < 2 or w in STOP:
            continue
        out.add(w[:2] if re.match(r'^[가-힣]', w) else w.lower())
    return out


def is_skipped(cid, before):
    return (cid.startswith(PREFIX_NOT_CLAUSE) or cid in AMBIGUOUS
            or bool(NOT_CLAUSE.search(before[-6:]))
            # ⚠ 창은 6자보다 넓어야 한다 — '`ds-gap` ' 만 9자다
            or bool(DSGAP_PREFIX.search(before[-12:])))


def spec_files(target):
    for dirpath, _dirs, files in os.walk(target):
        for fn in sorted(files):
            if fn.endswith('.md') and re.match(r'^[WPM]-[A-Z0-9]+-\d+', fn):
                yield os.path.join(dirpath, fn)


def check(target, strict, show_unused):
    clauses = load_clauses()
    gaps = load_dsgap()
    missing, weak, collide, cited, files = [], [], [], set(), 0

    for path in spec_files(target):
        files += 1
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding='utf-8') as f:
            lines = f.readlines()

        for ln, line in enumerate(lines, 1):
            for m in CITE.finditer(line):
                cid = m.group(1)
                if is_skipped(cid, line[:m.start()]):
                    continue
                if cid not in clauses:
                    missing.append((rel, ln, cid, line.strip()[:100]))
                else:
                    cited.add(cid)

            # 글로스 대조 — 「X-N(설명)」 형태만
            for m in GLOSS.finditer(line):
                cid, gloss = m.group(1), m.group(2)
                if is_skipped(cid, line[:m.start()]) or cid not in clauses:
                    continue
                g, t = stems(gloss), stems(clauses[cid])
                if not (g and t) or (g & t):
                    continue
                # ds-gap 갭 이름과 맞으면 표기 충돌이다 — 오독이 아니다
                if cid in gaps and (g & stems(gaps[cid])):
                    collide.append((rel, ln, cid, gaps[cid], gloss))
                else:
                    weak.append((rel, ln, cid, clauses[cid], gloss))

    print('조항 %d개 · 스펙 %d개 검사' % (len(clauses), files))
    print()

    if missing:
        print('⛔ 실재하지 않는 조항 인용 — %d건' % len(missing))
        for rel, ln, cid, ctx in missing:
            print('   %s:%d  %s\n      %s' % (rel, ln, cid, ctx))
        print()

    if weak:
        print('⚠ 글로스가 조항 제목과 한 낱말도 겹치지 않는다 — %d건 (확인 권고)'
              % len(weak))
        for rel, ln, cid, title, gloss in weak:
            print('   %s:%d  %s' % (rel, ln, cid))
            print('      인용 「%s」' % gloss)
            print('      제목 「%s」' % title)
        print()

    if collide:
        print('⚠ 공유계약 G-N 과 ds-gap G-N 을 섞어 썼다 — %d건' % len(collide))
        print('   (표기를 `ds-gap G-N` 으로 구분하면 사라진다)')
        for rel, ln, cid, gapname, gloss in collide:
            print('   %s:%d  %s — 인용 「%s」 ≈ **ds-gap %s 「%s」**'
                  % (rel, ln, cid, gloss, cid, gapname))
        print()

    if show_unused:
        unused = sorted(set(clauses) - cited,
                        key=lambda c: (c[0], int(c.split('-')[1])))
        print('ℹ 한 번도 인용되지 않은 조항 — %d / %d' % (len(unused), len(clauses)))
        if unused:
            print('   ' + ' · '.join(unused))
        print()

    if not missing and not weak and not collide:
        print('✅ 조항 인용이 전건 성립합니다. (인용된 조항 %d / %d)'
              % (len(cited), len(clauses)))
        print('   ⚠ 이 검사기는 **의미 오독을 못 잡는다** — 관계 주장(대체한다·'
              '얘기다·같은 것이다)은 사람이 원문을 연다.')
        return 0
    if missing:
        print('⛔ 실재하지 않는 조항 %d건 — 고쳐야 합니다.' % len(missing))
        return 1
    print('⚠ 확인 권고 — 글로스 불일치 %d건 · 표기 충돌 %d건'
          % (len(weak), len(collide)))
    return 1 if strict else 0


if __name__ == '__main__':
    args = sys.argv[1:]
    target = UIUX
    if '--dir' in args:
        target = os.path.join(ROOT, args[args.index('--dir') + 1])
    sys.exit(check(target, '--strict' in args, '--unused' in args))
