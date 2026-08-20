#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""설계 결정 대장이 몇 건인가 — 세는 «범위» 를 못박는다.

왜 필요한가
-----------
설계 사양서 §7.2 가 「142행」이라 적고 편람도 그 값을 인용하는데, **세는 명령이
없었다.** 그래서 다시 세어 보려던 사람이 §7 구간 전체의 표 행을 세어 197 을 얻고
「기준을 못 찾았다」로 남겼다(최종 산출물 설계 §9).

⭐ **기준은 문서에 이미 있었다.** §7.2 머리의 검산식이 그것이다 —

    메타 3 + QA 문답 38 + 설계결정서 15 + 기술 스택 ADR 5
    + 2026-06-26 결정 5 + 표기체계 1 + 날짜별 확정기록 75 = 142

⛔ **틀린 것은 값이 아니라 「어디까지 세는가」였다.** §7 에는 계열 안내표(§7.1)와
계보 체인표(§7.3)도 있어 함께 세면 부풀고, **§7.2 의 소절 표만** 세면 142 가 정확히
재현된다.

무엇을 세나
-----------
`§7.2.N` 소절 안의 표에서 **머리행과 구분선을 뺀 데이터 행**만 센다.
소절별 내역도 함께 낸다 — 어긋나면 어느 계열이 갈렸는지 바로 보인다.

⚠ 이 스크립트가 «안» 보는 것
----------------------------
- **결정의 내용이 맞는지** — 행이 있으면 있다고만 한다
- **상태 열이 「대체」인 행** — 세는 대상에서 빼지 않는다. 대장은 계보를 담는
  것이라 대체된 결정도 «있었다» 는 사실이 남아야 한다

쓰기
----
    python3 deliverables/count-decisions.py
    python3 deliverables/count-decisions.py --check    # 머리의 「N행」 표기와 대조
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "02-SW설계사양서.md")

HEAD = re.compile(r"^### §7\.2 결정 대장 전건 표 — (\d+)행", re.M)
SUB = re.compile(r"^#### (§7\.2\.\d+)\s*([^\n]*)$", re.M)
SEP = re.compile(r"^\|\s*-")


def count() -> tuple[int, list[tuple[str, str, int]], int | None]:
    with io.open(SPEC, encoding="utf-8") as f:
        text = f.read()
    declared = HEAD.search(text)
    start = text.index("### §7.2 결정 대장 전건 표")
    end = text.index("### §7.3")
    body = text[start:end]

    parts = SUB.split(body)
    rows: list[tuple[str, str, int]] = []
    total = 0
    for i in range(1, len(parts), 3):
        sid, title, block = parts[i], parts[i + 1], parts[i + 2]
        data = [l for l in block.split("\n")
                if l.startswith("|") and not SEP.match(l) and not l.startswith("| ID ")]
        rows.append((sid, title.strip(), len(data)))
        total += len(data)
    return total, rows, int(declared.group(1)) if declared else None


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--check", action="store_true",
                    help="문서 머리의 「N행」 표기와 대조한다")
    args = ap.parse_args()

    total, rows, declared = count()
    print("설계 결정 대장 — §7.2 소절의 데이터 행만 센다")
    print("─" * 62)
    for sid, title, n in rows:
        print("  %-9s %-46s %3d" % (sid, title[:46], n))
    print("  %-56s %3d" % ("계", total))

    if not args.check:
        return 0
    if declared is None:
        print("\n⛔ 문서 머리에서 「N행」 표기를 찾지 못했다.")
        return 1
    if declared != total:
        print("\n⛔ 문서 머리는 %d행이라 적었는데 실제로 센 값은 %d행이다." % (declared, total))
        print("   → 표기를 고치거나, 세는 범위가 바뀐 것이면 이 스크립트를 고친다.")
        return 1
    print("\n✅ 문서 머리 표기(%d행)와 같습니다." % declared)
    return 0


if __name__ == "__main__":
    sys.exit(main())
