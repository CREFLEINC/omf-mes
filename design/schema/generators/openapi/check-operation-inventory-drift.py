#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""요구서가 「⛔ 0건」·「미착지」로 적은 자리에 계약이 이미 실재하는 경로를 갖고 있는가.

왜 필요한가
-----------
`06-API-요구서-app공통승인.md` §1-2 「상신 경로 전수」가 「긴급 IQC 생략」 행을
「⛔ 0건 — 이 축의 유일한 실결손」으로 적어 두었다. 그런데 그 경로
(`POST /trace/lots/{lotId}:request-iqc-skip`)는 **같은 커밋**(`e38c5d9`,
2026-08-29)이 이미 만들어 두었다 — 표를 먼저 쓰고 경로를 나중에 넣은 것으로
보인다. 그 어긋남은 **사흘**을 갔고(`omf-mes#336` 이 재실측할 때까지) 어떤
검사기도 잡지 않았다.

무엇을 보나
-----------
요구서 9벌의 표에서 **한 칸이 정확히 「0건」또는「미착지」인 행**을 찾는다
(장식 기호·강조를 걷어 낸 뒤 정확히 같아야 한다 — 「금액 컬럼 **0건**」처럼
긴 문장 안에 우연히 낀 「0건」은 걸지 않는다). 그 행에 같이 적힌 화면 ID
(`W-01-06` 같은 토큰)를 뽑는다.

계약 7벌에서 **`:request-` 상신 오퍼레이션**(이 저장소가 「상신」에 일관되게
쓰는 경로 규약 — `:request-approval`·`:request-cancel`·`:request-iqc-skip`
등)의 `summary`·`description`·`x-internal-note` 에서 같은 화면 ID 를 찾는다.

행이 「0건/미착지」라고 적은 화면에 계약이 **이미 상신 오퍼레이션을 갖고
있으면** 어긋남이다 — 요구서가 계약을 따라잡지 못했다.

⚠ 왜 `:request-` 로 좁히나
---------------------------
화면 하나는 보통 여러 오퍼레이션(목록 조회·상세·수정 …)에 걸린다. 전부 보면
「이 화면에 아무 경로나 있다」까지만 확인돼 **그 행이 말하는 «상신» 경로와
무관한 경로**로도 초록이 돼 버린다(예: `M-01-01` 은 입하 등록 `POST` 를
갖지만 그 행이 말하는 건 「예외 입하 «승인»」이다). `:request-` 는 이
저장소가 상신에 일관되게 쓰는 경로 규약이라(`02_measure.md` §3-1 — 요청
본문이 `ApprovalRequestCreate` 인 오퍼레이션 8개가 전부 이 규약을 쓴다),
그 접두로 좁히면 «상신»이라는 행의 주제와 어긋나지 않는다.

⚠ 이 검사기가 못 보는 것
------------------------
- `:request-` 규약을 안 따르는 오퍼레이션은 못 본다 — 이 회차 실측으로는
  상신 오퍼레이션 8개가 전부 이 규약을 쓴다(예외 0건)
- 화면 ID 가 행에 «전혀» 안 적힌 「0건」 행은 못 본다 — 무엇과 대조할지
  모른다(예: 「특채 | 미특정 | ⛔ 0건」처럼 화면이 아직 없는 행)
- 계약에 경로가 있다고 **요구서가 그것을 실제로 안내에 반영했는지**는
  안 본다 — 「경로가 실재하는가」까지만 본다

쓰기
----
    python3 design/schema/generators/openapi/check-operation-inventory-drift.py
"""
from __future__ import annotations

import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACTS_DIR = os.path.join(HERE, "..", "..", "..", "wiki", "api-contracts", "openapi")
REQUIREMENTS_DIR = os.path.join(HERE, "..", "..", "..", "wiki", "api-contracts")

SCREEN_ID = re.compile(r"[WPM]-(?:CO|\d{2})-\d{2}")
DECORATION = re.compile(r"[*`⛔⚠✅ℹ️\s]+")
ZERO_MARKS = ("0건", "미착지")


def clean_cell(cell: str) -> str:
    return DECORATION.sub("", cell)


def zero_rows() -> list[tuple[str, int, set[str], str]]:
    """요구서 9벌에서 [(파일, 줄, 화면ID 집합, 원문 줄)] — 「0건/미착지」칸을 가진 행."""
    out = []
    for path in sorted(glob.glob(os.path.join(REQUIREMENTS_DIR, "06-API-요구서*.md"))):
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        for i, line in enumerate(lines, start=1):
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if any(c.startswith("---") for c in cells):
                continue
            if not any(clean_cell(c) in ZERO_MARKS for c in cells):
                continue
            screens = set()
            for c in cells:
                screens |= set(SCREEN_ID.findall(c))
            if screens:
                out.append((os.path.basename(path), i, screens, line.rstrip("\n")))
    return out


def request_operations_by_screen() -> dict[str, list[tuple[str, str, str]]]:
    """화면 ID → [(계약 파일, METHOD, path)] — `:request-` 상신 오퍼레이션이 그 화면을 인용한 자리."""
    out: dict[str, list[tuple[str, str, str]]] = {}
    for path in sorted(glob.glob(os.path.join(CONTRACTS_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        fname = os.path.basename(path)
        for op_path, item in (doc.get("paths") or {}).items():
            if ":request-" not in op_path or not isinstance(item, dict):
                continue
            for method, op in item.items():
                if method not in ("get", "post", "put", "patch", "delete"):
                    continue
                if not isinstance(op, dict):
                    continue
                text = " ".join(str(op.get(k, ""))
                                 for k in ("summary", "description", "x-internal-note"))
                for screen in set(SCREEN_ID.findall(text)):
                    out.setdefault(screen, []).append((fname, method.upper(), op_path))
    return out


def drifts() -> list[tuple[str, int, str, str, list[tuple[str, str, str]]]]:
    """[(파일, 줄, 화면, 원문 줄, 계약에 실재하는 상신 오퍼레이션들)]."""
    by_screen = request_operations_by_screen()
    out = []
    for fname, lineno, screens, raw in zero_rows():
        for screen in sorted(screens):
            ops = by_screen.get(screen)
            if ops:
                out.append((fname, lineno, screen, raw, ops))
    return out


def main() -> int:
    rows = zero_rows()
    print("요구서 9벌에서 「0건/미착지」+ 화면 ID 를 가진 행 %d개를 찾았다." % len(rows))
    found = drifts()

    if not found:
        print("✅ 그 행들이 가리키는 화면에 계약의 `:request-` 상신 경로가 없습니다"
              " — 어긋남이 없습니다.")
        return 0

    print("\n⛔ 요구서가 「0건/미착지」라고 적은 화면에 계약이 이미 상신 경로를 가진 자리 %d건"
          % len(found))
    for fname, lineno, screen, raw, ops in found:
        print("\n   %s:%d — %s" % (fname, lineno, screen))
        print("      요구서: %s" % raw.strip())
        for cfile, method, path in ops:
            print("      계약:   %-6s %s  (%s)" % (method, path, cfile))
    print("\n   ⭐ 표를 정정한다 — 경로가 이미 있으면 「0건/미착지」를 걷고 그 경로를 적는다.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
