#!/usr/bin/env python3
"""값 목록이 없는 코드 필드를 센다 — 산출물이 인용하는 수치의 정본.

왜 있는가
---------
1차 제안안과 DR-011 이 「`*Code` 중 enum 도 값 목록도 없는 것 **79종** →
업무 코드 **51종**」을 인용했는데 **기준을 안 남겨 재현되지 않았다.**
무엇을 셌는지 되짚을 수 없는 수치는 결정 근거가 못 된다.

이 스크립트가 그 수치의 정본이다. 문서가 수치를 인용할 때 이 출력을 붙인다.

세는 기준
---------
- 대상 = 프로퍼티 이름이 `Code` 로 끝나고, `type` 또는 `$ref` 를 가진 것
- **이름 단위로 센다** — 같은 이름이 여러 스키마에 나와도 하나로 본다
  (값 목록은 이름마다 정하지 자리마다 정하지 않는다.
   ⚠ 단 `reasonCode` 는 예외 — 자리마다 값 집합이 다르다. §reasonCode 참고)
- `enum` 이 하나라도 붙어 있으면 **확정으로 본다**

갈래
----
- **인스턴스 식별** — 값이 코드 목록이 아니라 마스터 데이터다(`itemCode`·
  `warehouseCode`). 업무가 정할 「값 목록」이 아니다
- **표준값** — 외부 표준을 그대로 쓴다(`countryCode`·`timezoneCode`)
- **상태값** — 상태 기계와 함께 정해야 해 따로 센다
- **미착지** — `x-source-column` 이 없는 것. 쿼리 파라미터·파생 필드라
  저장되지 않는다. 값 목록의 대상이 아니다
- ⭐ **업무 코드** — 나머지. **이것이 정해야 할 것이다**
"""
from __future__ import annotations

import glob
import json
import os
import re

CONTRACT_GLOB = os.path.join(os.path.dirname(__file__), "*.json")

# 값이 마스터 레코드를 가리키는 것 — 코드 목록이 아니다
INSTANCE = {
    "bomCode", "businessUnitCode", "departmentCode", "equipmentCode",
    "erpPartnerCode", "externalItemCode", "externalSystemCode", "groupCode",
    "inspectionItemCode", "inspectionPlanCode", "interfaceCode", "itemCode",
    "legalEntityCode", "lineCode", "locationCode", "partnerCode",
    "permissionCode", "plantCode", "processCode", "roleCode", "routingCode",
    "warehouseCode",
}
# 외부 표준을 그대로 쓴다
STANDARD = {"countryCode", "timezoneCode", "uomCode", "frequencyIntervalUomCode"}


def collect(paths: list[str]) -> dict[str, dict]:
    """계약 전체에서 `*Code` 프로퍼티를 이름 단위로 모은다."""
    found: dict[str, dict] = {}

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, val in node.items():
                if (
                    isinstance(val, dict)
                    and key.endswith("Code")
                    and ("type" in val or "$ref" in val)
                ):
                    rec = found.setdefault(key, {"enum": False, "columns": set()})
                    if "enum" in val:
                        rec["enum"] = True
                    if "x-source-column" in val:
                        rec["columns"].add(val["x-source-column"])
                walk(val)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for path in paths:
        walk(json.load(open(path, encoding="utf-8")))
    return found


def main() -> int:
    paths = sorted(p for p in glob.glob(CONTRACT_GLOB) if "ui-요구목록" not in p)
    found = collect(paths)

    undecided = {k: v for k, v in found.items() if not v["enum"]}
    landed = {k: v for k, v in undecided.items() if v["columns"]}
    unlanded = sorted(set(undecided) - set(landed))

    status = sorted(k for k in landed if "Status" in k)
    instance = sorted(k for k in landed if k in INSTANCE)
    standard = sorted(k for k in landed if k in STANDARD)
    business = sorted(set(landed) - set(status) - set(instance) - set(standard))

    print(f"계약 {len(paths)}종")
    print(f"  *Code 프로퍼티 이름            {len(found)}")
    print(f"  그중 enum 없음                 {len(undecided)}")
    print(f"    ├ x-source-column 없음(미착지) {len(unlanded)}   대상 아님")
    print(f"    └ 실제 컬럼에 착지            {len(landed)}   ← 여기서 가른다")
    print(f"        ├ 인스턴스 식별            {len(instance)}   대상 아님")
    print(f"        ├ 표준값                   {len(standard)}   대상 아님")
    print(f"        ├ 상태값                   {len(status)}   상태 기계와 함께")
    print(f"        └ ⭐ 업무 코드              {len(business)}   ← 정해야 할 것")

    print("\n⭐ 업무 코드")
    for i in range(0, len(business), 3):
        print("   " + "  ".join(f"{n:<30}" for n in business[i : i + 3]))

    # reasonCode 는 이름이 아니라 자리로 센다 — 자리마다 값 집합이 다르다
    positions = set()
    for path in paths:
        text = json.load(open(path, encoding="utf-8"))

        def walk(node: object, owner: str = "") -> None:
            if isinstance(node, dict):
                for key, val in node.items():
                    if key == "reasonCode" and isinstance(val, dict):
                        positions.add(re.sub(r"(Create|Upsert)$", "", owner))
                    walk(val, key if node.get(key) is val and key[:1].isupper() else owner)
            elif isinstance(node, list):
                for item in node:
                    walk(item, owner)

        walk(text)
    print(f"\n⚠ reasonCode 는 이름 하나이나 **자리 {len(positions)}개**다 — 자리마다 값 집합이 다르다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
