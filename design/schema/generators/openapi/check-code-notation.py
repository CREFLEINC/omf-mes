#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""코드 값 표기 규칙 — 「화면 스펙은 병기 · 계약과 요구서는 단독」(작성 규칙 6).

무엇을 보나
-----------
공통코드 값(`MACHINING`·`DAY`·`EMPLOYED` …)을 문서에 적을 때 **한국어 뜻을 함께
적는가**를 문서 종류가 정한다(사용자 확정 2026-09-03 · `schema/00-authoring-rules.md`
규칙 6).

    값 자체(계약 enum · 사전 「값」 열)            ⛔ 영문만          ← 막는다
    화면 스펙 §4·본문                              ✅ 병기            ← 래칫
    계약·요구서 산문                               단독              ← 래칫

⭐ **무엇이 「코드 값」인지는 코드 사전이 정한다.** 문서에서 대문자 토큰을 아무거나
   줍지 않는다 — `PROCESS_TYPE`(그룹 이름)과 `MACHINING`(값)은 다른 것이고,
   그룹 이름은 병기 대상이 아니다. 사전의 「값」 열에 실린 문자열만 본다.

⚠ 무엇을 «안» 보나
-------------------
- **이력·회고 절** — `verify-stale-terms` 와 같은 판정을 쓴다. 그 절의 표기는
  그 시점의 기록이라 지금 규칙으로 재단하지 않는다.
- **`design/raw/`** — 시점 고착 자료다.
- **뜻이 자명한가** — 기계가 못 가른다. 그래서 ㉡㉢ 은 막지 않고 «센다».
- **한 토큰이 코드가 아닌 뜻으로 쓰인 자리** — `TEXT`·`DAY` 같은 흔한 낱말은
  다른 문맥에서도 나온다. 래칫이라 오탐이 섞여도 «늘지 않는다»만 지키면 된다.

⛔ 왜 ㉡㉢ 을 막지 않나 — 이미 쓴 글을 걷어내면 정보가 준다
------------------------------------------------------------
실측(2026-09-03) — 계약 7벌 산문에 병기 **26자리**(backtick 자리 기준)인데 그중 상당수는
병기를 빼면 **오독한다**:

    NORMAL (양산)             ← 빼면 「정상」으로 읽힌다. 실제로는 작업지시 유형
    PQC (공정·초중종·자주)      ← 병기 없이는 무슨 검사인지 알 수 없다
    INJECTION_MOLDING (사출기) · WATER_HEATER (온수기)

그래서 규칙은 **앞으로 쓰는 글**에 걸고, 기존 자리는 래칫으로 «늘지 않게»만 막는다.

쓰기
----
    python3 design/schema/generators/openapi/check-code-notation.py
    python3 design/schema/generators/openapi/check-code-notation.py --list  자리 전건
"""
from __future__ import annotations

import argparse
import glob
import importlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_cd = importlib.import_module("check-code-dictionary")
# ⭐ 이력·회고 절 판정은 `verify-stale-terms.py` 것을 «그대로» 쓴다 — 같은 판정을
#    두 곳에 따로 두면 갈린다(`check-screen-code-dictionary.py` 와 같은 방식).
sys.path.insert(0, os.path.dirname(HERE))
_stale = importlib.import_module("verify-stale-terms")

ROOT = os.path.join(HERE, "..", "..", "..")
DICT = os.path.join(ROOT, "schema", "code-dictionary.md")
CONTRACTS = os.path.join(ROOT, "wiki", "api-contracts", "openapi", "*.json")
REQUIREMENTS = os.path.join(ROOT, "wiki", "api-contracts", "06-API-요구서*.md")
SCREENS = os.path.join(ROOT, "wiki", "screens", "**", "*.md")

KO = re.compile(r"[가-힣]")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")

# ⛔ 값으로 세지 않는 토큰 — 사전에 실려 있어도 문서에서 다른 뜻으로 흔히 쓰인다.
#    래칫의 잡음을 줄이는 것이 목적이고, 규칙 자체를 좁히는 것이 아니다.
NOISE = frozenset({"API", "MES", "ERP", "POP", "QR", "PDA", "UI", "DB", "OK", "NG"})

# 기준선 — 2026-09-03 실측. ⛔ 늘리지 않는다. 줄었으면 낮춘다.
#
# ㉡ 화면 스펙에서 «병기 안 한» 자리. 화면 스펙은 병기가 규칙이므로 이 수가 곧
#    「아직 안 따라온 자리」다. ⚠ 전부 결손은 아니다 — 같은 문서에서 이미 병기한
#    값을 다시 언급하는 자리가 섞인다(매번 병기하면 산문이 무거워진다).
BASELINE_SCREEN = 488
# ㉢ 계약·요구서 산문에서 «병기한» 자리. 단독이 규칙이므로 이 수가 곧 잔여다.
#    ⛔ 걷어내지 않는다 — 위 「왜 막지 않나」 참조.
BASELINE_DOC = 26


def dictionary_values(path: str = DICT) -> set[str]:
    """사전 「값」 열의 코드 문자열 전부. ⭐ 그룹 이름은 다른 열이라 섞이지 않는다."""
    out: set[str] = set()
    for row in _cd.read_dictionary(path):
        for v in row["values"]:
            if v in NOISE or len(v) < 3:
                continue
            out.add(v)
    return out


def paired(text: str, value: str) -> tuple[int, int]:
    """(병기한 자리 수, 단독으로 쓴 자리 수) — 한 값에 대해.

    병기 = 그 값 바로 뒤에 «한국어를 담은 괄호»가 온다.

    ⛔ **backtick 안에 있는 자리만 본다.** 사전의 값 열 165행이 전부 backtick 이고,
       이 저장소는 코드 값을 그렇게 적는 관행이 확고하다. 맨몸 토큰까지 세면
       «업무 낱말»이 코드로 잡힌다 — 실측 2026-09-03: `LOT`(「LOT 라벨」·「LOT 스캔」)이
       한 파일에서 30자리, `BOM`(「BOM 기준」)이 30자리씩 걸렸다. 그 오탐이 쌓이면
       기준선이 «무엇을 세는 수»인지 뜻을 잃는다.
    ⚠ 이것은 규칙을 좁히는 것이 아니라 검사기를 정확하게 만드는 것이다 — 규칙 6 은
       「코드 값을 적을 때」이고, 코드 값으로 «적은» 표시가 backtick 이다.
    """
    both = solo = 0
    for m in re.finditer(r"`%s`" % re.escape(value), text):
        tail = text[m.end():m.end() + 24]
        mm = re.match(r"\s*[(（]\s*([^)）]{1,12})[)）]", tail)
        if mm and KO.search(mm.group(1)):
            both += 1
        else:
            solo += 1
    return both, solo


def strip_history(text: str) -> str:
    """이력·회고 절을 지운다 — `verify-stale-terms` 와 같은 판정을 쓴다."""
    out, skip = [], False
    for line in text.split("\n"):
        m = HEADING.match(line)
        if m:
            skip = _stale.in_history_section(m.group(2))
        if not skip:
            out.append(line)
    return "\n".join(out)


def scan_prose(paths: list[str], values: set[str], want_pair: bool) -> list[tuple]:
    """문서들에서 (파일, 값, 수) — want_pair=True 면 «병기 안 한» 자리를 센다."""
    found: list[tuple] = []
    for p in paths:
        if os.sep + "raw" + os.sep in p:
            continue
        with io.open(p, encoding="utf-8", errors="ignore") as fh:
            text = strip_history(fh.read())
        for v in values:
            if v not in text:
                continue
            both, solo = paired(text, v)
            n = solo if want_pair else both
            if n:
                found.append((os.path.basename(p), v, n))
    return found


def literal_korean(doc: dict) -> list[tuple[str, str]]:
    """⛔ 값 «자체»에 한국어 — 계약이 `enum` 으로 «닫은» 값 목록만 본다.

    ⛔ `example` 은 보지 않는다 — 자리채움(`"값"`·`"코드"`)이 남은 자리는
       `check-example-placeholder.py` 소관이고, 여기서 함께 잡으면 **한 결손에
       게이트가 둘**이 되어 어느 쪽을 고쳐야 하는지 흐려진다. 그 자리들은
       사전 값이 ⬜ 라 «지금 채울 수도» 없다.
    """
    bad: list[tuple[str, str]] = []

    def walk(node, where):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "enum" and isinstance(v, list):
                    for x in v:
                        if isinstance(x, str) and KO.search(x):
                            bad.append(("enum", "%s : %s" % (where, x)))
                elif isinstance(v, (dict, list)):
                    walk(v, where)
        elif isinstance(node, list):
            for it in node:
                walk(it, where)

    walk(doc, doc.get("info", {}).get("title", "?"))
    return bad


def dictionary_korean(path: str = DICT) -> list[str]:
    """⛔ 사전 「값」 열에 한국어가 섞인 행.

    ⛔ ⬜(값이 아직 없다는 «표시»)가 붙은 행은 건너뛴다 — 그 칸의 한국어는 코드가
       아니라 「미상」 같은 상태 표기다. 값이 서면 그때 이 검사가 다시 본다.
    """
    bad = []
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("| `CD-"):
                continue
            cs = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cs) != 7 or "⬜" in cs[1]:
                continue
            if KO.search(cs[1]):
                bad.append("%s — %s" % (cs[0], cs[1][:50]))
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="자리 전건을 낸다")
    args = ap.parse_args()

    values = dictionary_values()
    print("코드 사전이 정한 값 %d종 — 이 문자열만 본다"
          "(그룹 이름은 사전의 다른 열이라 섞이지 않는다)\n" % len(values))

    # ── ㉠ ⛔ 값 자체에 한국어 ──────────────────────────────────────
    hard: list[str] = []
    for p in sorted(glob.glob(CONTRACTS)):
        for kind, msg in literal_korean(json.load(io.open(p, encoding="utf-8"))):
            hard.append("%-10s %s — %s" % (kind, os.path.basename(p), msg))
    for row in dictionary_korean():
        hard.append("%-10s code-dictionary.md — %s" % ("사전 값 열", row))

    if hard:
        print("⛔ ㉠ 값 «자체»에 한국어가 있습니다 %d건" % len(hard))
        for h in hard[:20]:
            print("   " + h)
        print("   ⭐ 코드는 영문이고 화면에 보이는 것은 code_name 이다(§G).")
    else:
        print("㉠ ✅ 값 «자체»는 전부 영문이다 — 계약 enum · 사전 값 열")

    # ── ㉡ 화면 스펙 — 병기가 규칙이다 ─────────────────────────────
    screen = scan_prose(sorted(glob.glob(SCREENS, recursive=True)), values, want_pair=True)
    n_screen = sum(n for _, _, n in screen)
    print("\n㉡ 화면 스펙에서 «병기하지 않은» 자리 — %d (기준선 %d)"
          % (n_screen, BASELINE_SCREEN))

    # ── ㉢ 계약·요구서 — 단독이 규칙이다 ───────────────────────────
    docs = sorted(glob.glob(CONTRACTS)) + sorted(glob.glob(REQUIREMENTS))
    doc = scan_prose(docs, values, want_pair=False)
    n_doc = sum(n for _, _, n in doc)
    print("㉢ 계약·요구서 산문에서 «병기한» 자리 — %d (기준선 %d)"
          % (n_doc, BASELINE_DOC))

    if args.list:
        for label, rows in (("㉡ 화면 스펙 — 병기 안 함", screen),
                            ("㉢ 계약·요구서 — 병기함", doc)):
            print("\n%s" % label)
            for f, v, n in sorted(rows, key=lambda x: -x[2])[:40]:
                print("   %-38s %-28s ×%d" % (f, v, n))

    # ── 판정 ───────────────────────────────────────────────────────
    print()
    rc = 0
    if hard:
        print("⛔ 막는 규칙에 걸렸습니다 — 값 자체에 한국어 %d" % len(hard))
        rc = 1
    for label, now, base, name in (("㉡ 화면 스펙", n_screen, BASELINE_SCREEN, "BASELINE_SCREEN"),
                                   ("㉢ 계약·요구서", n_doc, BASELINE_DOC, "BASELINE_DOC")):
        if now > base:
            print("⛔ %s 기준선 %d 을 넘었습니다 — %d 늘었다." % (label, base, now - base))
            rc = 1
        elif now < base:
            print("⭐ %s 기준선 %d → %d 로 줄었다. `%s` 를 %d 로 낮추세요."
                  % (label, base, now, name, now))
        else:
            print("✅ %s 기준선 %d 유지 — 늘지 않았다." % (label, base))

    print("\n⭐ 규칙은 `schema/00-authoring-rules.md` 규칙 6 이다 —"
          " 값 자체는 «막고», 산문 표기는 «센다».")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
