#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""정본 본문이 «구조 삭제 전» 경로를 인용하고 있는가.

왜 필요한가
-----------
2026-08-25 Phase 5 로 `docs/` · `uiux/` · `deliverables/` 세 구조를 지웠다.
그런데 **정본 본문의 인용은 그대로 남았다** — 읽는 사람이 링크를 따라가면
아무것도 없다. 이 축을 보는 검사기가 없어서 아무도 못 셌다(오케스트레이터 O-3).

⛔ **`docs/` 없는 `research/…` 형태를 반드시 잡는다.** `design/wiki/domain-workflow/`
13장이 그 형태로 인용하는데(2026-08-29 실측 **233건** · 고유 경로 43개 ·
실재 0개), `docs/` 접두만 세면 그 233건이 통째로 안 보인다.

무엇을 보나
-----------
`design/wiki/**/*.md` 본문에서 구조 삭제 이전 접두
(`docs/research/` · `research/` · `uiux/` · `deliverables/`)로 시작하는 인용을
찾아, `design/schema/redirect-map.md` 에서 신경로를 찾고, 그 신경로가 실재하는지
`os.path.exists` 로 확인한다.

    치환 가능   구경로가 지도에 있고 신경로가 실재한다   → --fix 대상 · EXIT=1
    미등재      지도에 없다                              → 목록만
    신경로 부재 지도에는 있으나 파일이 없다               → 목록만

--fix
-----
지도에 등재된 것만 «기계» 치환한다. **멱등**이다 — 두 번 돌려도 결과가 같다.
⛔ `--fix` 결과를 확인 없이 커밋하지 마세요. 수백 건 치환이고 한 건이라도
엉뚱하면 정본이 «틀린 링크»를 갖게 된다. `git diff` 를 사람이 훑는다.

⛔ 예외로 두는 것 (실측으로 가른 것)
-----------------------------------
  - `> 출처:` · `> 근거 자료:` 로 시작하는 **출처 꼬리표 블록** — 「그때 무엇을
    보고 썼나」의 이력이라 그대로 둔다. 목록으로만 낸다
  - `## 변경 이력` 표 안의 행 — 시점 기록이라 다시 쓰지 않는다(저장소 관행)
  - `design/raw/` 아래 전부 — 읽지 않는다
  - **생성물**(`design/wiki/handover/*.md` — 진도표·인계대장·미결-대장) — 손으로
    고치지 않는다. 값을 바꾸려면 원천(화면 스펙 §8 등)을 고치고 «재생성»한다.
    이 검사기도 읽기만 하고 `--fix` 대상에서 뺀다
  - 와일드카드가 든 경로(`uiux/2026-08-1*-API스펙-*/…`) — `--fix` 대상 밖.
    목록으로만 낸다

⚠ 이 검사기가 못 보는 것
------------------------
  - 접두 넷 밖의 죽은 경로 — 지도가 그 넷만 담는다
  - 산문 안에서 «경로처럼 안 보이게» 적은 인용
  - 신경로가 실재해도 «가리키는 절»이 옮겨 갔는지는 안 본다

쓰기
----
    python3 design/schema/generators/check-dead-path-citations.py
    python3 design/schema/generators/check-dead-path-citations.py --fix
"""
from __future__ import annotations

import collections
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
WIKI = os.path.join(ROOT, "design", "wiki")
MAP = os.path.join(ROOT, "design", "schema", "redirect-map.md")

DEAD_PREFIXES = ("docs/research/", "research/", "uiux/", "deliverables/")

# ⛔ 생성물 — 손으로 고치지 않는다(재생성으로만 갱신). 읽되 --fix 하지 않는다.
GENERATED_DIRS = (os.path.join("design", "wiki", "handover") + os.sep,)

# ⛔ 앞 글자가 경로 조각이면 잡지 않는다 — `design/raw/process/uiux/…` 안의
#    `uiux/` 를 잡으면 «이미 옮긴» 경로를 다시 옮기려 든다.
CITE = re.compile(
    r"(?<![\w/.\-])(docs/research/|research/|uiux/|deliverables/)([^\s)\]`|\"'>,]*)")

SOURCE_TAG = re.compile(r"^\s*>\s*(출처|근거 자료)\s*[:：]")
HEADING = re.compile(r"^#{1,6}\s")
CHANGELOG = re.compile(r"^#{1,6}\s*변경 이력\s*$")


def load_map():
    """redirect-map.md → (전건 대응, 접두 규칙[(구접두, 신접두)] 긴 것부터)."""
    exact: dict[str, str] = {}
    prefixes: set[tuple[str, str]] = set()
    with io.open(MAP, encoding="utf-8") as fh:
        for line in fh:
            if "→" not in line:
                continue
            old, new = [x.strip() for x in line.split("→", 1)]
            if not old or not new or new.startswith("("):
                continue          # 「(삭제됨, …)」 같은 설명 — 경로가 아니다
            exact[old.rstrip("/")] = new.rstrip("/")
            # 공통 «꼬리»를 벗겨 접두 규칙을 뽑는다 — 디렉터리 인용도 옮기려면 필요하다.
            o, n = old.rstrip("/").split("/"), new.rstrip("/").split("/")
            k = 0
            while k < min(len(o), len(n)) and o[len(o) - 1 - k] == n[len(n) - 1 - k]:
                k += 1
            if k:
                prefixes.add(("/".join(o[:len(o) - k]), "/".join(n[:len(n) - k])))
    return exact, sorted(prefixes, key=lambda p: -len(p[0]))


def resolve(cited: str, exact: dict, prefixes) -> str | None:
    """구경로 → 신경로. 못 찾으면 None."""
    for cand in (cited, "docs/" + cited if cited.startswith("research/") else None):
        if cand is None:
            continue
        c = cand.rstrip("/")
        if c in exact:
            return exact[c]
        for old, new in prefixes:
            if c == old or c.startswith(old + "/"):
                return new + c[len(old):]
    return None


def scan_file(path: str):
    """(줄번호, 원문줄, 인용, 예외사유 또는 None) 을 낸다."""
    out = []
    in_source, in_changelog = False, False
    with io.open(path, encoding="utf-8") as fh:
        for no, line in enumerate(fh, 1):
            if HEADING.match(line):
                in_changelog = bool(CHANGELOG.match(line.strip()))
            if SOURCE_TAG.match(line):
                in_source = True
            elif in_source and not line.lstrip().startswith(">"):
                in_source = False
            why = None
            if in_source:
                why = "출처 꼬리표 블록"
            elif in_changelog and line.lstrip().startswith("|"):
                why = "변경 이력 표"
            for m in CITE.finditer(line):
                out.append((no, line, m.group(0), why))
    return out


def md_files():
    for base, dirs, names in os.walk(WIKI):
        dirs[:] = [d for d in dirs if d not in (".git",)]
        for n in sorted(names):
            if n.endswith(".md"):
                yield os.path.join(base, n)


def main() -> int:
    fix = "--fix" in sys.argv
    exact, prefixes = load_map()

    fixable = collections.defaultdict(list)   # 파일 → [(구, 신)]
    generated = collections.defaultdict(list)  # 생성물 → [(구, 신)] · --fix 대상 밖
    kept = collections.Counter()              # 예외 사유 → 건수
    unmapped = collections.Counter()          # 구경로 → 건수
    missing_new = collections.Counter()       # (구, 신) → 건수
    wildcard = collections.Counter()
    total = 0

    for path in md_files():
        rel = os.path.relpath(path, ROOT)
        for no, line, cited, why in scan_file(path):
            total += 1
            if why:
                kept[why] += 1
                continue
            if "*" in cited:
                wildcard[cited] += 1
                continue
            new = resolve(cited, exact, prefixes)
            if new is None:
                unmapped[cited] += 1
                continue
            if not os.path.exists(os.path.join(ROOT, new)):
                missing_new[(cited, new)] += 1
                continue
            if rel.startswith(GENERATED_DIRS):
                generated[rel].append((cited, new))
            else:
                fixable[rel].append((cited, new))

    n_fix = sum(len(v) for v in fixable.values())

    print("죽은 경로 인용 %d건 검사 (design/wiki/**/*.md)" % total)
    n_gen = sum(len(v) for v in generated.values())
    print("   치환 가능 %d · 생성물 %d · 미등재 %d · 신경로 부재 %d · 와일드카드 %d · 예외 %d\n"
          % (n_fix, n_gen, sum(unmapped.values()), sum(missing_new.values()),
             sum(wildcard.values()), sum(kept.values())))

    if generated:
        print("ℹ  생성물 안의 죽은 인용 %d건 — ⛔ 손으로 고치지 않는다(재생성으로만 갱신)"
              % n_gen)
        for rel in sorted(generated):
            print("   %-52s %d건" % (rel, len(generated[rel])))
        print()

    if kept:
        print("ℹ  예외로 둔 것 — 이력이라 다시 쓰지 않는다")
        for why, n in sorted(kept.items()):
            print("   %-20s %d건" % (why, n))
        print()
    if wildcard:
        print("ℹ  와일드카드가 든 경로 %d종 — --fix 대상 밖 (사람이 본다)"
              % len(wildcard))
        for p, n in sorted(wildcard.items()):
            print("   %-64s %d건" % (p[:64], n))
        print()
    if missing_new:
        print("⚠ 지도에는 있으나 신경로가 실재하지 않는 인용 %d종" % len(missing_new))
        for (old, new), n in sorted(missing_new.items()):
            print("   %-48s → %-48s %d건" % (old[:48], new[:48], n))
        print()
    if unmapped:
        print("⚠ redirect-map.md 에 없는 구경로 %d종 (%d건) — 손대지 않는다"
              % (len(unmapped), sum(unmapped.values())))
        for p, n in sorted(unmapped.items()):
            print("   %-64s %d건" % (p[:64], n))
        print()

    if not n_fix:
        print("✅ 기계로 치환할 수 있는 죽은 인용 0건")
        return 0

    print("⛔ 치환 가능한 죽은 인용 %d건 · 파일 %d개" % (n_fix, len(fixable)))
    for rel in sorted(fixable):
        pairs = collections.Counter(fixable[rel])
        print("   %s — %d건" % (rel, sum(pairs.values())))
        for (old, new), n in sorted(pairs.items()):
            print("      %-52s → %-52s %d" % (old[:52], new[:52], n))

    if not fix:
        print("\n   → python3 design/schema/generators/check-dead-path-citations.py --fix")
        print("   ⛔ --fix 결과는 «git diff 를 사람이 훑은 뒤» 커밋한다.")
        return 1

    # ── --fix — 지도에 등재된 것만 · 긴 경로부터 · 멱등 ────────────────────
    changed = 0
    for rel in sorted(fixable):
        path = os.path.join(ROOT, rel)
        with io.open(path, encoding="utf-8") as fh:
            text = fh.read()
        before = text
        for old, new in sorted(set(fixable[rel]), key=lambda p: -len(p[0])):
            text = text.replace(old, new)
        if text != before:
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            changed += 1
    print("\n✅ --fix — 파일 %d개를 고쳤습니다. ⛔ git diff 를 훑고 커밋하세요." % changed)
    print("   ⚠ 예외(출처 꼬리표·변경 이력)와 미등재·와일드카드는 손대지 않았습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
