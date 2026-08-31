#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""계약이 가리킨 공통코드 «그룹 이름»이 등록부 안의 것인가.

왜 필요한가
-----------
공유계약 **G-32** — 화면이 값 목록을 부를 때 그룹을 `codeGroupCode`(문자열)로
가리킨다. 채번 식별자(`codeGroupId`)는 환경마다 달라 하드코딩하면 다른
환경에서 «조용히 빈 목록»을 받고 그 화면의 주 기능이 막힌다.

⛔ **오류가 나지 않아 눈에 안 띈다.** 등록부(`mdm.code_group` 에 그 행이
«있는» 이름)에 없는 이름을 계약에 적으면 화면은 오류 없이 빈 목록을 받는다 —
그것이 G-32 가 막으려던 바로 그 실패다.

⚠ **이름을 «도출»할 수 있는 것과 그 행이 «있는» 것은 다른 문제다.**
G-32 의 「그룹 이름 짓는 규칙」은 이름을 *짓는* 법이고, 이 등록부는 이름이
*있는가* 다. 규칙만 보고 지어낸 이름은 이 검사기가 잡는다.

무엇을 보나
-----------
① ⛔ **`description` 의 `codeGroupCode=<이름>` 포인터가 등록부 40 밖**인 자리.
   전건 출력하고 종료 코드 1 을 낸다.
② ⚠ `enum` 도 `codeGroupCode=` 포인터도 `x-no-example` 도 없는 `*Code` 자리.
   **개수와 상위 파일만** 찍고 종료 코드를 바꾸지 않는다.

⛔ 왜 ②를 게이트로 걸지 않나
----------------------------
「`enum` 없는 `*Code` 는 포인터나 `x-no-example` 중 하나를 반드시 가진다」를
게이트로 걸면 **기준선이 361자리 빨강**이다(2026-08-29 실측). 이 회차의 어떤
반영으로도 닫히지 않는 수라, 걸면 «초록을 기준선으로 쓸 수 없게» 된다.
그래서 **닫을 수 있는 것만** 게이트로 건다. ②는 흐름을 보는 계수기다.

⚠ 이 검사기가 못 보는 것
------------------------
  - 등록부에 «있는» 이름을 «틀린 자리»에 쓴 것 — 이름이 맞으면 통과한다
  - `description` 밖(예시·본문 산문)에 적힌 그룹 이름 — 포인터 형태만 본다
  - 그룹에 실제로 «값이 들어 있는가» — 계약이 답할 수 있는 물음이 아니다

쓰기
----
    python3 design/schema/generators/openapi/check-code-group-pointer.py
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
# Tier 0 — OpenAPI JSON 정본. Phase 5 컷오버(2026-08-25)로 design/wiki/api-contracts/openapi/가 정본 위치다.
CONTRACTS_DIR = os.path.join(HERE, "..", "..", "..", "wiki", "api-contracts", "openapi")

# 등록부 — 공유계약 G-32 확정 11 · omf-mes#198 확정 29 · 2026-08-29 등재 2 · 2026-08-31 등재 1 = 43 (겹치는 이름 0).
# ⛔ 여기에 없는 이름을 계약에 적지 않는다. 늘리려면 «먼저» G-32 를 고친다 —
#    조항이 정본이고 이 집합은 그 사본이다.
REGISTRY = set("""
EQUIPMENT_TYPE INSTRUMENT_TYPE
INSPECTION_REQUEST_STATUS INSPECTION_RESULT_OVERALL_JUDGMENT INSPECTION_MEASUREMENT_JUDGMENT
INSPECTION_ITEM_SPEC_DATA_TYPE LOT_STATUS LOT_TYPE EQUIPMENT_STATUS EQUIPMENT_INSPECTION_TYPE
EQUIPMENT_INSPECTION_JUDGMENT_METHOD QUALITY_INSPECTION_TYPE CYCLE_TYPE
GOODS_ISSUE_REASON INBOUND_VARIANCE_REASON INVENTORY_ADJUSTMENT_REASON PUTAWAY_TASK_TEMPORARY_REASON
SUBSTITUTE_LOT_REASON VARIANCE_REASON INBOUND_RECEIPT_EXCEPTION_TYPE HANDLING_UNIT_TYPE
LOT_EXTERNAL_IDENTIFIER_TYPE OWNERSHIP_TYPE PICKING_TYPE RESERVATION_TYPE INVENTORY_COUNT_TYPE
CONTROL_OVERRIDE_REASON PRODUCTION_PLAN_SPLIT_REASON WORK_ORDER_CANCEL_REASON
WORK_ORDER_COMPLETION_VARIANCE_REASON WORK_SESSION_EVENT_REASON WORK_CALENDAR_DAY_REASON
LOT_HOLD_REASON DOWNTIME_REASON INSPECTION_FREQUENCY INSPECTION_ITEM_SPEC_METHOD
INSPECTION_SAMPLING_METHOD PROCESS_TYPE QUALIFICATION_TYPE STORAGE_CONDITION REISSUE_REASON
WORK_SESSION_EVENT_TYPE INBOUND_VARIANCE_TYPE
""".split())

POINTER = re.compile(r"codeGroupCode=([A-Z][A-Z0-9_]*)")


def schemas(doc: dict):
    """(스키마 이름, 필드 이름, 프로퍼티) 를 전건 낸다."""
    for name, schema in (doc.get("components", {}).get("schemas") or {}).items():
        if not isinstance(schema, dict):
            continue
        for field, prop in (schema.get("properties") or {}).items():
            if isinstance(prop, dict):
                yield name, field, prop


def main() -> int:
    stray: list[tuple[str, str, str, str]] = []
    bare = collections.Counter()
    total_code = 0
    pointers = 0

    for f in sorted(glob.glob(os.path.join(CONTRACTS_DIR, "*.json"))):
        fname = os.path.basename(f)
        with open(f, encoding="utf-8") as fh:
            doc = json.load(fh)
        for sname, field, prop in schemas(doc):
            desc = prop.get("description") or ""
            names = POINTER.findall(desc)
            pointers += len(names)
            for n in names:
                if n not in REGISTRY:
                    stray.append((fname, sname, field, n))
            if not field.endswith("Code"):
                continue
            total_code += 1
            if "enum" in prop or names or "x-no-example" in prop:
                continue
            bare[fname] += 1

    if bare:
        print("⚠ `enum` 도 그룹 포인터도 `x-no-example` 도 없는 `*Code` 자리 "
              "%d건 (전체 `*Code` %d) — 계수만 낸다(EXIT 를 바꾸지 않는다)"
              % (sum(bare.values()), total_code))
        for fname, n in sorted(bare.items(), key=lambda kv: (-kv[1], kv[0])):
            print("   %-30s %4d" % (fname, n))
        print()

    if not stray:
        print("✅ 계약이 가리킨 그룹 이름이 전부 등록부 안입니다 — 포인터 %d자리 검사"
              " (등록부 %d개)" % (pointers, len(REGISTRY)))
        return 0

    print("⛔ 등록부 밖 그룹 이름을 가리키는 자리 %d건 (포인터 %d자리 검사 · 등록부 %d개)\n"
          % (len(stray), pointers, len(REGISTRY)))
    for fname, sname, field, name in stray:
        print("   %-26s %-24s %-24s → %s" % (fname, sname, field, name))
    print("\n   ⭐ 둘 중 하나를 «정해서» 닫는다 —\n"
          "      ① 그 이름을 공유계약 G-32 등록부에 올린다(마스터에 행이 실재해야 한다)\n"
          "      ② 등록부에 있는 이름으로 포인터를 고친다\n"
          "   ⛔ 검사기의 REGISTRY 만 늘려 초록을 만들지 마세요 — 조항이 정본입니다.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
