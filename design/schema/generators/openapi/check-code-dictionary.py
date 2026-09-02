#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""코드 사전(`design/schema/code-dictionary.md`)이 계약과 맞는가 — **시험판**.

왜 필요한가
-----------
한 코드 값이 저장소 100곳 안팎에 흩어져 있고, 그중 **판단이 적히는 자리는 산문**이라
아무도 안 본다. 사전은 그 판단(소유·자리·근거)을 표로 꺼내 «기계가 셀 수 있게» 한다.

⛔ 그런데 사전이 «또 하나의 사본»이 되면 문제가 재생산된다 — 지금 등록부가 정확히
   그 상태다(공유계약 조항 3,079자 한 줄 + `check-code-group-pointer.py` 의 REGISTRY
   상수, 손으로 동기화). **그래서 이 검사기가 사전을 «읽고» 계약과 대조한다.**

무엇을 보나
-----------
① 사전이 적은 «자리 수»가 계약 실물과 같은가
   ⚠ 소유 값 넷 — enum · registry · registry-system · derived.
     registry-system 은 「설계가 정한 값을 마스터에 싣는다」이고 계약에서는
     registry 와 같이 포인터다. 갈리는 곳은 W-06-06 편집 가부다(미결 9).
② 사전이 `enum` 이라 한 키가 정말 계약에 값 목록을 갖는가
③ 사전이 `registry` 라 한 키가 정말 `codeGroupCode=` 포인터를 갖는가
④ ⭐ **형제 자리가 갈리지 않았는가** — 같은 이름이 어떤 자리에는 값이 있고 어떤
   자리에는 «맨몸»이면 그 맨몸을 보는 사람은 「값 목록이 없다」로 읽는다.
   ⚠ 이것을 보는 검사기가 지금 «없다» — check-code-group-pointer 는 가리킨 이름이
   등록부 안인가만, check-code-group-reachable 은 화면이 닿는가만 본다.

⚠ 이 검사기가 못 보는 것
------------------------
- **키가 «맞는지»는 안 본다.** 사전이 「이 자리는 이 키」라 적은 것을 믿는다.
  그 판정은 사람이 `A-16` 으로 한다.
- **④ 의 두 갈래를 못 가른다** — (a) 같은 코드인데 값이 빠졌다 / (b) 원래 다른
  코드인데 이름이 같다. **그 구분이 곧 사전이 할 일**이고, 사전에 없는 이름은
  일단 (?) 로 낸다.
- **물리 모델·프론트·서버 시드는 안 본다.** 우리 계약 7벌만 본다.

쓰기
----
    python3 design/schema/generators/openapi/check-code-dictionary.py
    python3 design/schema/generators/openapi/check-code-dictionary.py --split   # ④ 만

⛔ **막지 않는다** — 시험판이라 종료 코드는 언제나 0 이다. 사전이 계약 527자리를
   다 덮고 ④ 가 0 이 되면 게이트로 올린다.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
DICT = os.path.join(ROOT, "design", "schema", "code-dictionary.md")
CONTRACTS = os.path.join(ROOT, "design", "wiki", "api-contracts", "openapi", "*.json")

POINTER = re.compile(r"codeGroupCode=([A-Z_]+)")
KEY = re.compile(r"^`(CD-[A-Z0-9-]+)`$")
CODE_NAME = re.compile(r"`([a-zA-Z]+Codes?)`")
VALUE = re.compile(r"`([A-Z][A-Z0-9_]+)`")     # 코드 문자열·그룹 이름은 SCREAMING 이다


# ── 사전 읽기 ─────────────────────────────────────────────────────────────

def read_dictionary(path: str) -> list[dict]:
    """사전 표를 읽는다. 「| 키 | 값(이름) | 소유 | 자리 | 근거 |」 표만 본다."""
    rows: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("|"):
                continue
            cs = [c.strip() for c in line.strip().strip("|").split("|")]
            # ⛔ 열이 «정확히 여섯»인 표만 본다 — 같은 문서의 결과·설명 표가 첫 칸에
            #    같은 키를 다시 적어 사전 행으로 세어졌다(2026-09-02 · 10 → 13).
            if len(cs) != 6:
                continue
            m = KEY.match(cs[0])
            if not m:
                continue                      # 머리·구분선·다른 표
            rows.append({
                "key": m.group(1),
                # ⭐ 값 — enum 갈래면 코드 문자열들, registry 갈래면 그룹 이름.
                #    ⛔ 이름이 아니라 «값»으로 대조해야 같은 이름 다른 값집합이 갈린다.
                "values": VALUE.findall(cs[1]),
                "names": CODE_NAME.findall(cs[2]),
                "owner": cs[3].strip("`"),
                "places": int(cs[4]) if cs[4].isdigit() else None,
                "basis": cs[5] if len(cs) > 5 else "",
            })
    return rows


# ── 계약 훑기 ─────────────────────────────────────────────────────────────

def state(node: dict, desc: str | None) -> str:
    """이 자리가 값 목록을 갖는가 — enum · ptr · bare."""
    src = node.get("items") or node
    if src.get("enum"):
        return "enum"
    if POINTER.search(desc or ""):
        return "ptr"
    return "bare"


def scan() -> dict[str, list[tuple]]:
    """계약 7벌의 *Code(s) 자리를 이름별로 모은다.

    반환 — 이름 -> [(계약, 자리종류, 경로, 상태, enum튜플, 포인터튜플)]
    """
    out: dict[str, list[tuple]] = defaultdict(list)
    for path in sorted(glob.glob(CONTRACTS)):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        name = os.path.basename(path).replace(".json", "")

        def walk(node, where):
            if isinstance(node, dict):
                for k, v in node.items():
                    if (k.endswith("Code") or k.endswith("Codes")) and \
                            isinstance(v, dict) and ("type" in v or "enum" in v):
                        src = v.get("items") or v
                        out[k].append((name, "스키마", where + "/" + k,
                                       state(v, v.get("description")),
                                       tuple(src.get("enum") or ()),
                                       tuple(POINTER.findall(v.get("description") or ""))))
                    if k == "name" and isinstance(v, str) and \
                            (v.endswith("Code") or v.endswith("Codes")) and "schema" in node:
                        sc = node.get("schema") or {}
                        out[v].append((name, "쿼리", where,
                                       state(sc, node.get("description")),
                                       tuple(sc.get("enum") or ()),
                                       tuple(POINTER.findall(node.get("description") or ""))))
                    walk(v, where + "/" + str(k))
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    walk(v, where + "/%d" % i)

        walk(doc, "")
    return out


# ── ④ 형제 자리가 갈렸는가 ────────────────────────────────────────────────

def split_siblings(found: dict[str, list[tuple]]) -> list[tuple]:
    """같은 계약 안에서 같은 이름이 「값 있음」과 「맨몸」으로 갈린 자리."""
    out = []
    for name, places in found.items():
        by_file = defaultdict(list)
        for f, kind, path, st, _, _ in places:
            by_file[f].append((kind, path, st))
        for f, ps in by_file.items():
            sts = {s for _, _, s in ps}
            if "bare" in sts and (sts - {"bare"}):
                bare = [(k, p) for k, p, s in ps if s == "bare"]
                has = [s for _, _, s in ps if s != "bare"]
                out.append((name, f, bare, has[0], len(ps)))
    return sorted(out, key=lambda x: -len(x[2]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", action="store_true", help="④ 형제 갈림만 낸다")
    args = ap.parse_args()

    entries = read_dictionary(DICT)
    found = scan()
    total = sum(len(v) for v in found.values())

    print("코드 사전 검사 — 시험판")
    print("─" * 70)
    print("사전 %d 키 · 계약 *Code(s) 자리 %d" % (len(entries), total))
    print()

    if not args.split:
        bad = 0
        claimed = 0
        for e in entries:
            want = e["values"]
            got = []
            bare = []
            # ⛔ 「맨몸」은 «같은 계약 파일» 안에서만 센다(2026-09-02).
            #    statusCode 처럼 이름이 여러 코드에 공유되면 이름으로 세는 순간
            #    «남의 자리»를 삼킨다 — 실제로 맨몸 2 를 80 으로 셌다.
            #    ⭐ 이것이 이 사전의 전제 그대로다 — 값은 중복해도 키는 유일하고,
            #    그래서 «이름»이 아니라 «값»으로 가른다.
            mine = {f for f, _, _, _, _, _ in
                    [x for n in e["names"] for x in found.get(n, [])]
                    if True}
            hit_files = set()
            for n in e["names"]:
                for f, kind, path, st, enum, ptr in found.get(n, []):
                    if e["owner"] == "enum":
                        if enum and set(want) == {x for x in enum if x is not None}:
                            hit_files.add(f)
                    elif ptr and set(want) & set(ptr):
                        hit_files.add(f)
            for n in e["names"]:
                for f, kind, path, st, enum, ptr in found.get(n, []):
                    # ⭐ «값»으로 가른다 — 이름이 같아도 값집합이 다르면 남의 자리다.
                    # registry-system 은 registry 와 «계약에서는» 같다 — 포인터다.
                    # 다른 것은 W-06-06 에서 고객이 편집할 수 있는가뿐이고,
                    # 그것은 계약이 아니라 화면·마스터 소관이다(2026-09-02 신설).
                    if e["owner"] == "enum":
                        hit = enum and set(want) == {x for x in enum if x is not None}
                    else:
                        hit = ptr and set(want) & set(ptr)
                    if hit:
                        got.append((f, kind, path, st))
                    elif st == "bare" and f in hit_files:
                        # ⛔ 값도 포인터도 없는 «형제» 자리 — 단 이 키가 실제로 걸린
                        #    계약 파일 안에서만 센다. 다른 파일의 같은 이름은 남의 코드다.
                        bare.append((f, kind, path))
            claimed += len(got)
            want_n = e["places"]
            ok = want_n is None or want_n == len(got)
            mark = "✅" if ok else "⛔"
            if not ok:
                bad += 1
            print("%s %-38s %-9s 사전 %-3s 값있음 %-3d 맨몸 %-3d %s"
                  % (mark, e["key"], e["owner"],
                     want_n if want_n is not None else "?", len(got), len(bare),
                     "" if ok else "← 맨몸 자리가 그만큼이다"))
            if not ok:
                for f, kind, path in bare[:4]:
                    print("      ⛔ %-20s %-5s %s" % (f[:20], kind, path[-58:]))
        print()
        print("① 사전이 선언한 자리 수를 «못 채운» 키: %d" % bad)
        print("   ⭐ 이것은 검사기 오류가 아니라 «계약이 비어 있다»는 뜻이다 —")
        print("      사전이 「여기도 이 코드다」라 선언해야 그 빈자리가 보인다.")
        print("② 사전이 «값으로» 짚어 낸 자리: %d / 계약 %d" % (claimed, total))
        print()

    splits = split_siblings(found)
    bare_total = sum(len(b) for _, _, b, _, _ in splits)
    q = sum(1 for _, _, b, _, _ in splits for k, _ in b if k == "쿼리")

    print("④ ⛔ 형제 자리가 갈린 코드: %d 종 · 맨몸 자리 %d (쿼리 %d · %d%%)"
          % (len(splits), bare_total, q, round(q * 100 / max(bare_total, 1))))
    print()
    known = {n for e in entries for n in e["names"]}
    for name, f, bare, has, tot in splits[:12]:
        tag = "사전에 있다" if name in known else "⚠ 사전 밖"
        print("   %-26s %-20s 맨몸 %2d / %2d  (%s → %s)"
              % (name, f[:20], len(bare), tot, has, tag))
    if len(splits) > 12:
        print("   … 그 밖 %d 종" % (len(splits) - 12))
    print()
    print("⚠ 이 수를 그대로 「고칠 것」으로 읽지 않는다 — 두 갈래다.")
    print("   (a) 같은 코드인데 어떤 자리만 값이 빠졌다  → 채운다")
    print("   (b) 원래 «다른 코드»인데 이름이 같다        → 키를 가른다")
    print("   ⭐ 그 구분이 곧 사전이 할 일이다.")
    print()
    print("⛔ 이 검사기는 «막지 않는다» — 시험판이라 종료 코드는 언제나 0 이다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
