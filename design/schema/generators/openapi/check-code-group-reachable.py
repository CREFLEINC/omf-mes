#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""계약이 가리킨 공통코드 그룹에 **화면이 닿을 수 있는가**.

왜 필요한가
-----------
계약(`description`)에 `codeGroupCode=…` 를 적는 것만으로는 **화면이 그 호출을
만들지 않는다.** 프론트가 읽는 것은 요구서 §3 액션표이고, 착수·변경 통지도
거기서 「이 화면이 부르는 경로」를 뽑는다. 계약에만 있고 요구서에 없는 그룹은
**통지가 나를 수 없다.**

⛔ 2026-09-01 에 그 형태가 실측으로 드러났다 — 초과 입하 분리(`W-01-03`)의
예외 유형은 계약에 포인터가 **2026-08-29 에 이미 실렸는데**(`#288`) 요구서
§3 은 그 자리를 「**API 불필요** — 요청 본문을 채우는 일」로 적어 두었다.
프론트는 요구서대로 만들었고, 화면은 오류 없이 **빈 선택칸**으로 섰다.
같은 형태가 8화면이었다. 어떤 검사기도 그것을 보지 않았다.

무엇을 보나
-----------
계약 7벌의 포인터 그룹 집합 ∖ 요구서 8벌에 적힌 그룹 집합.

⛔ 왜 «전부 초록»을 요구하지 않나
---------------------------------
기준선이 **34그룹**이다(2026-09-01). 이 회차의 어떤 반영으로도 닫히지 않는
수라, 게이트로 걸면 초록을 기준선으로 쓸 수 없게 된다. 대신 **래칫**으로 건다 —
늘면 ⛔, 줄면 「기준선을 낮추라」고 알린다. 새로 만드는 자리가 같은 구멍을
반복하는 것만은 막는다.

⚠ 이 검사기가 못 보는 것
------------------------
  - 요구서에 적혔다고 «그 화면» 절에 적힌 것은 아니다 — 문서 단위로만 센다
  - 화면이 실제로 그 호출을 구현했는지 — 이 저장소가 답할 수 있는 물음이 아니다
  - 그룹 이름이 등록부 안인지 — 그것은 `check-code-group-pointer.py` 가 본다

쓰기
----
    python3 design/schema/generators/openapi/check-code-group-reachable.py
"""
from __future__ import annotations

import collections
import glob
import importlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_cg = importlib.import_module("check-code-group-pointer")

CONTRACTS = os.path.join(HERE, "..", "..", "..", "wiki", "api-contracts", "openapi")
REQUIREMENTS = os.path.join(HERE, "..", "..", "..", "wiki", "api-contracts")

POINTER = re.compile(r"codeGroupCode=([A-Z][A-Z0-9_]*)")

# 기준선 — 2026-09-01 실측. ⛔ 늘리지 않는다. 줄었으면 이 수를 낮춘다.
BASELINE = 34


def main() -> int:
    sites: dict[str, list[str]] = collections.defaultdict(list)
    for f in sorted(glob.glob(os.path.join(CONTRACTS, "*.json"))):
        fname = os.path.basename(f)
        with open(f, encoding="utf-8") as fh:
            doc = json.load(fh)
        for where, desc in _cg.descriptions(doc):
            for name in POINTER.findall(desc):
                sites[name].append("%s :: %s" % (fname, where))

    in_req: set[str] = set()
    files = sorted(glob.glob(os.path.join(REQUIREMENTS, "06-API-요구서*.md")))
    for f in files:
        with open(f, encoding="utf-8") as fh:
            in_req |= set(POINTER.findall(fh.read()))

    gap = sorted(set(sites) - in_req)
    print("계약 포인터 그룹 %d · 요구서(%d벌)에 적힌 그룹 %d · 닿지 않는 그룹 **%d**"
          % (len(sites), len(files), len(in_req), len(gap)))

    if gap:
        print("\n⚠ 계약은 가리키는데 요구서가 한 번도 적지 않은 그룹 — **통지가 나를 수 없다**")
        for name in gap:
            print("   %-38s %s" % (name, sites[name][0]))
        print("\n   ⭐ 닫는 법 — 그 그룹을 쓰는 화면의 요구서 §3 액션표에")
        print("      `GET /mdm/code-values?codeGroupCode=<이름>` 행을 «추가»한다.")
        print("      ⛔ 「API 불필요」로 적지 않는다 — 선택칸의 값 목록은 API 호출이다.")

    if len(gap) > BASELINE:
        print("\n⛔ 기준선 %d 보다 %d 늘었다 — 새로 만든 자리가 같은 구멍을 반복했다."
              % (BASELINE, len(gap) - BASELINE))
        return 1
    if len(gap) < BASELINE:
        print("\n⭐ 기준선 %d → %d 로 줄었다. 이 파일의 `BASELINE` 을 %d 로 낮추세요."
              % (BASELINE, len(gap), len(gap)))
    else:
        print("\n✅ 기준선 %d 유지 — 늘지 않았다." % BASELINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
