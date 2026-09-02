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

⛔ **⓪ 만 막는다**(2026-09-02) — 등록부↔사전 1:1 · 소유 일치 · 그룹이 등록부 안.
계수 규칙(①②④)은 여전히 막지 않는다 — 닫을 수 없는 수라 흐름만 본다.
옛 서술: ~~시험판이라 종료 코드는 언제나 0 이다.~~ 사전이 계약 527자리를
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
import importlib

# ⭐ 등록부는 **읽어 온다** — 여기에 그룹 이름 목록을 다시 적으면 그 순간 셋째 사본이 되고,
#    그것이 정확히 이 사전이 고치려는 병이다(2026-09-02 이관). 파서는 저장소에 하나뿐이다.
_ptr = importlib.import_module("check-code-group-pointer")
load_registry = _ptr.load_registry
load_registry_owners = _ptr.load_registry_owners

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
    """사전 표를 읽는다. 「| 키 | 값 | 그룹 | 프로퍼티 | 소유 | 자리 | 근거 |」 표만 본다.

    ⭐ 값 열은 «언제나» 실제 코드 문자열이다. 그룹(codeGroupCode)은 따로 둔다 —
       한 열에 두 종류를 섞으면 읽는 사람이 헷갈리고, registry 갈래의 실제 값이
       «산문에만» 남는다(2026-09-02 사용자 지적으로 갈랐다).
    """
    rows: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("|"):
                continue
            cs = [c.strip() for c in line.strip().strip("|").split("|")]
            # ⛔ 열이 «정확히 일곱»인 표만 본다 — 같은 문서의 결과·설명 표가 첫 칸에
            #    같은 키를 다시 적어 사전 행으로 세어졌다(2026-09-02 · 10 → 13).
            if len(cs) != 7:
                continue
            m = KEY.match(cs[0])
            if not m:
                continue                      # 머리·구분선·다른 표
            rows.append({
                "key": m.group(1),
                # ⭐ 값 — «언제나» 실제 코드 문자열이다. 그룹 이름은 따로 둔다.
                #    ⛔ 첫 판은 enum 갈래만 코드 문자열이고 registry 갈래는 그룹 이름이라
                #    한 열에 두 종류가 섞였고, registry 쪽 실제 값이 «산문에만» 남았다.
                "values": VALUE.findall(cs[1]),
                "group": VALUE.findall(cs[2]),
                "names": CODE_NAME.findall(cs[3]),
                "owner": cs[4].strip("`"),
                "places": int(cs[5]) if cs[5].isdigit() else None,
                "basis": cs[6],
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

    # ⓪ 사전이 가리킨 «그룹» 이 등록부 안인가 — 사전이 셋째 사본이 되지 않게 대조한다.
    gate: list[str] = []          # ⛔ 여기에 담긴 것만 종료 코드를 바꾼다
    registry = load_registry()
    outside = sorted({g for e in entries for g in e["group"]} - registry)
    if outside:
        gate.append("사전의 그룹이 등록부 밖 %d" % len(outside))
        print("⛔ 사전의 «그룹» 열이 등록부 밖입니다 %d건 — 공유계약 G-32 표에 없습니다"
              % len(outside))
        for g in outside:
            print("   %s" % g)
    else:
        print("⓪ 사전의 «그룹» 열 %d종 전부 등록부 안 (등록부 %d개)"
              % (len({g for e in entries for g in e["group"]}), len(registry)))

    # ⓪-a ⛔ **게이트** — 등록부에 이름이 올랐으면 사전에도 행이 있어야 한다.
    #     걸어 두지 않으면 새 그룹이 사전을 건너뛰고, 값은 다시 계약 산문으로 흩어진다.
    #     (2026-09-02 1단계로 62/62 가 초록이 된 뒤에 건다)
    covered = {g for e in entries for g in e["group"]}
    orphan = sorted(registry - covered)
    if orphan:
        gate.append("등록부에 있는데 사전에 없는 그룹 %d" % len(orphan))
        print()
        print("⛔ 등록부에 있는데 «사전에 없는» 그룹 %d건 — 값이 어디에도 안 적힌다"
              % len(orphan))
        for g in orphan:
            print("   %s" % g)
        print("   ⭐ 닫는 법 — design/schema/code-dictionary.md 에 행을 더한다.")
        print("      값을 모르면 ⬜ 로 «세어서» 남긴다 — 비워 두지 않는다.")

    # ⓪-b 소유가 «두 곳»에 적힌다 — 갈라지지 않게 기계가 맞춘다.
    #     사람이 맞추게 두면 등록부 이관 전의 병이 소유 축에서 그대로 재발한다.
    owners = load_registry_owners()
    clash = [(e["key"], g, e["owner"], owners[g])
             for e in entries for g in e["group"]
             if g in owners and owners[g] != "미판정" and e["owner"] != owners[g]]
    if clash:
        print()
        gate.append("사전↔등록부 소유 불일치 %d" % len(clash))
        print("⛔ 사전의 «소유» 가 등록부와 다릅니다 %d건 — 정본은 공유계약 G-32 표입니다"
              % len(clash))
        for key, g, mine, theirs in clash:
            print("   %-38s %-38s 사전 %-16s 등록부 %s" % (key, g, mine, theirs))
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
                    elif ptr and set(e["group"]) & set(ptr):
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
                        # registry 갈래는 «그룹 이름»으로 자리를 찾는다 — 값은 계약에
                        # 없고 서버 마스터에 있기 때문이다. 값 열은 사람이 읽고
                        # 나중에 서버 시드와 대조할 근거다.
                        hit = ptr and set(e["group"]) & set(ptr)
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
    if gate:
        print("⛔ 막는 규칙에 걸렸습니다 — %s" % " · ".join(gate))
        return 1
    print("⭐ 계수 규칙(①②④)은 «막지 않는다» — 흐름을 보는 수다.")
    print("   ⛔ 막는 것은 ⓪ 뿐이다 — 등록부↔사전 1:1 과 소유 일치.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
