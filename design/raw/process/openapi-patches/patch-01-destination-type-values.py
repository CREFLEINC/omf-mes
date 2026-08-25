#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""출고 도착지 유형 값 목록을 확정한다 — 값 셋. 멱등.

무엇을 확정하나
---------------
2026-08-16 사용자 확정. 도착지 유형은 **출고 전표 하나만** 쓴다 —
다른 도착지는 전부 참조 키로 직접 박혀 있다(destination_location_id 등).

    LOCATION        위치      자재 출고(생산창고 라인사이드) · 창고 간 기타 출고
    PARTNER         거래처    공급사 반품
    DISPOSAL_SITE   거래처    폐기 출고 — 업체가 가져갈 때
    (비움)          —        자체 폐기

⭐ 왜 PARTNER 와 DISPOSAL_SITE 를 나누나
----------------------------------------
둘 다 같은 거래처 표를 가리킨다. 그래도 나누는 쪽을 골랐다(2026-08-16 확정).

    나누면   화면이 유형 «하나»만 보고 거래처 목록을 좁힌다(폐기면 폐기 역할만)
    합치면   유형 + 출고 유형 «둘»을 조합해 역할 필터를 다시 판정해야 한다

프론트가 이미 DISPOSAL_SITE 로 구현해 둔 것과도 맞는다.

⭐ LOCATION 의 근거는 실측이다
------------------------------
출고 요청(material_issue_request)이 도착지를 **위치 참조 키**로 갖는다.
출고 전표가 그것을 따라가므로 위치다. M-01-08 §5-6 이 같은 결론을 적었다 —
「프로세스가 말하는 도착은 생산창고(라인사이드)」.

⛔ 자체 폐기는 값을 두지 않는다
-------------------------------
「없음」을 뜻하는 값을 만들지 않는다. 짝을 통째로 비우는 것이 사실이고,
값을 만들면 「도착지가 있는데 그 값이 NONE」이라는 거짓 상태가 생긴다.

쓰기
----
    python3 deliverables/openapi/patch-01-destination-type-values.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "logistics-01자재창고.json")

VALUES = ["LOCATION", "PARTNER", "DISPOSAL_SITE"]
DESC = (
    "도착지 유형. 위치(LOCATION) → mdm.location · 거래처(PARTNER) → mdm.partner · "
    "폐기 거래처(DISPOSAL_SITE) → mdm.partner 셋이다. "
    "창고 내 이동과 생산 투입은 위치, 공급사 반품은 거래처, 폐기는 폐기 거래처를 가리킨다. "
    "⭐ 자체 폐기면 도착지 짝을 통째로 비운다 — 나가서 없어지는 물건에는 도착지가 없다. "
    "⭐ 2026-08-16 업무 확정."
)
NOTE = (
    "값 목록이 확정돼 enum 을 못박았다(2026-08-16). PARTNER 와 DISPOSAL_SITE 는 같은 표를 "
    "가리키지만 값을 나눴다 — 나누면 화면이 유형 하나만 보고 거래처 목록을 역할로 좁힐 수 "
    "있고, 합치면 출고 유형까지 봐야 한다. LOCATION 의 근거는 실측이다 — "
    "material_issue_request 가 도착지를 위치 참조 키로 갖는다. "
    "⛔ 자체 폐기를 뜻하는 값을 만들지 않는다: 짝을 비우는 것이 사실이고, 값을 만들면 "
    "「도착지가 있는데 그 값이 없음」이라는 거짓 상태가 생긴다."
)


def detect_indent(original: str, doc: dict) -> int | None:
    body = original.rstrip("\n")
    for candidate in (1, 2, 4):
        if json.dumps(doc, ensure_ascii=False, indent=candidate) == body:
            return candidate
    return None


def main() -> int:
    original = open(CONTRACT, encoding="utf-8").read()
    doc = json.loads(original)
    indent = detect_indent(original, doc)
    if indent is None:
        print("⛔ 원본 들여쓰기를 알아낼 수 없다 — 덮어쓰지 않는다", file=sys.stderr)
        return 1
    tail = original[len(original.rstrip("\n")):]

    hit = 0
    for name, schema in doc["components"]["schemas"].items():
        prop = (schema.get("properties") or {}).get("destinationTypeCode")
        if not isinstance(prop, dict):
            continue
        prop.pop("x-no-example", None)
        # 비울 수 있는 자리는 enum 에 null 을 함께 둔다 — 자체 폐기가 그 상태다.
        nullable = "null" in (prop.get("type") or [])
        prop["enum"] = VALUES + ([None] if nullable else [])
        prop["example"] = "DISPOSAL_SITE"
        prop["description"] = DESC
        prop["x-internal-note"] = NOTE
        hit += 1

    if not hit:
        print("⛔ destinationTypeCode 를 가진 스키마가 없다", file=sys.stderr)
        return 1

    updated = json.dumps(doc, ensure_ascii=False, indent=indent) + tail
    if updated == original:
        print("  이미 반영돼 있다 — 변경 없음")
        return 0
    open(CONTRACT, "w", encoding="utf-8").write(updated)
    print(f"  ✅ 도착지 유형 값 {len(VALUES)} 확정 — {hit}곳")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
