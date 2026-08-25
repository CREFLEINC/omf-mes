#!/usr/bin/env python3
"""01 계약의 재고상태·품질상태에 「값이 이미 있다」를 싣는다 — 멱등.

왜 필요한가
-----------
01 계약이 `inventoryStatusCode`·`qualityStatusCode` 를 둘 다
「확정된 값 목록이 아직 없다 — 서버가 내려주는 선택지를 그대로 쓴다(G-2)」
로 적었다. 실측하니 **둘 다 값이 있었다.**

  inventoryStatusCode   물리 모델 시드에 4값이 실재한다
                        AVAILABLE · IN_TRANSIT · ON_HOLD · BLOCKED
                        (mdm.code_group 'INVENTORY_STATUS' · [E-7] 근거)

  qualityStatusCode     회신 E-3 으로 4값이 확정됐다
                        정상 · 불량 · 검사 대기 · 폐기
                        ⚠ 값 집합은 확정이나 **코드 문자열은 미정**이라
                        enum 을 못 박지 않는다.

⛔ 「없다」고 적기 전에 열어 보지 않은 것이다. 계약 전체에 같은 문구가
62곳 있으므로 나머지도 같은 의심을 받아야 한다 → uiux/2026-08-13-공통코드값목록-제안안/

⚠ example 정정
--------------
`qualityStatusCode` 의 example 이 `RELEASED` 였다. E-3 확정 4값 어디에도
없는 문자열이다. 코드 문자열이 미정이라 대체할 확정값이 없으므로 example
은 그대로 두되 x-internal-note 에 **잠정임을 명시**한다.

바이트 보존
-----------
이 파일은 indent=1 · 끝줄 없음으로 직렬화돼 있다. 같은 형식으로 다시 쓰므로
손대지 않은 곳은 한 바이트도 바뀌지 않는다. (patch-01-missing-ops.py 가
정렬 출력으로 파일 전체를 churn 시킨 전례가 있어 여기서는 피한다.)
"""
from __future__ import annotations  # py3.9 에서 `str | None` 표기를 쓰기 위해

import json
import sys

CONTRACT = "deliverables/openapi/logistics-01자재창고.json"

INVENTORY_ENUM = ["AVAILABLE", "IN_TRANSIT", "ON_HOLD", "BLOCKED"]

INVENTORY_DESC = (
    "재고 상태. 가용(AVAILABLE) · 운송중(IN_TRANSIT) · 보류(ON_HOLD) · "
    "차단(BLOCKED) 네 가지다."
)
INVENTORY_NOTE = (
    "값 출처 = 공통코드 그룹 INVENTORY_STATUS 시드 4값([E-7] — 창고 간 이동의 "
    "shipped~received 구간을 IN_TRANSIT 으로 표현). "
    "구 서술 「확정된 값 목록이 아직 없다(G-2)」는 오기였다 — 값을 열어 보지 않았다."
)

QUALITY_DESC = (
    "품질 상태. 정상 · 불량 · 검사 대기 · 폐기 네 가지다. "
    "⚠ 값 집합은 확정이나 코드 문자열이 아직 정해지지 않아 enum 을 못 박지 않는다 — "
    "서버가 내려주는 선택지를 그대로 쓴다."
)
QUALITY_NOTE = (
    "값 집합 출처 = 회신 E-3 확정(정상·불량·검사 대기·폐기). "
    "E-3 는 이 축이 재고의 차원임을 확인했다 — uq_inventory_balance_dim 에 "
    "quality_status_code 가 들어 있어 같은 LOT 이 같은 위치에 있어도 품질 상태가 "
    "다르면 재고 행이 갈린다. "
    "⚠ example 'RELEASED' 는 확정 4값 어디에도 없는 잠정값이다 — 코드 문자열 확정 시 교체한다. "
    "구 서술 「확정된 값 목록이 아직 없다(G-2)」는 오기였다."
)


def is_nullable(prop: dict) -> bool:
    """type 이 ["string","null"] 처럼 null 을 허용하는가."""
    t = prop.get("type")
    return isinstance(t, list) and "null" in t


def classify(source_column: str | None) -> str | None:
    """컬럼 이름을 값 영역으로 가른다.

    ⛔ 이름 일치가 아니라 **접미사**로 본다. 전이 컬럼
    (from_/to_inventory_status_code · from_/to_quality_status_code)이
    같은 값 영역인데 이름이 달라, 완전 일치로 매칭하면 조용히 빠진다.
    실제로 1차 패치가 InventoryTransactionLine 의 넷을 놓쳤다.
    """
    if not source_column:
        return None
    if source_column.endswith("inventory_status_code"):
        return "inventory"
    if source_column.endswith("quality_status_code"):
        return "quality"
    return None


def transition_prefix(source_column: str) -> str:
    """전이 컬럼이면 「전이 전/후」임을 밝히는 접두 문구를 준다."""
    if source_column.startswith("from_"):
        return "전이 전 "
    if source_column.startswith("to_"):
        return "전이 후 "
    return ""


def rebuild(
    prop: dict, *, description: str, note: str, enum: list[str] | None = None
) -> dict:
    """키 순서를 보존하며 description/x-internal-note 를 갈고 enum 을 끼운다.

    enum 은 maxLength 바로 뒤에 둔다(type/format 계열과 붙여 읽히게).
    ⛔ 끼울 자리가 없으면 조용히 넘어가지 않고 SystemExit 한다 — 자리 부재로
    enum 이 빠졌는데 호출부가 성공을 찍는 것이 가장 나쁜 실패다.
    """
    out = {}
    for k, v in prop.items():
        if k == "description":
            out[k] = description
        elif k == "x-internal-note":
            out[k] = note
        else:
            out[k] = v
        if k == "maxLength" and enum is not None:
            out["enum"] = enum + ([None] if is_nullable(prop) else [])
    if "description" not in out:
        out["description"] = description
    if "x-internal-note" not in out:
        out["x-internal-note"] = note
    if enum is not None and "enum" not in out:
        raise SystemExit(
            f"⛔ enum 을 끼울 자리(maxLength)가 없다: {prop.get('x-source-column')}. "
            "삽입 기준을 바꾸거나 프로퍼티에 maxLength 를 넣는다."
        )
    return out


def patch(node: object, counts: dict[str, int]) -> None:
    """문서를 훑으며 두 값 영역의 프로퍼티를 제자리에서 갈아 끼운다."""
    if isinstance(node, dict):
        for key, val in list(node.items()):
            kind = classify(val.get("x-source-column")) if isinstance(val, dict) else None
            if kind is None:
                patch(val, counts)
                continue
            column = val["x-source-column"]
            where = transition_prefix(column)
            if kind == "inventory":
                node[key] = rebuild(
                    val,
                    description=where + INVENTORY_DESC,
                    note=INVENTORY_NOTE,
                    enum=INVENTORY_ENUM,
                )
            else:
                node[key] = rebuild(
                    val, description=where + QUALITY_DESC, note=QUALITY_NOTE
                )
            counts[kind] += 1
    elif isinstance(node, list):
        for item in node:
            patch(item, counts)


def main() -> int:
    """계약을 읽어 두 값 영역을 갈아 끼우고, 바뀐 것이 있을 때만 다시 쓴다."""
    original = open(CONTRACT, encoding="utf-8").read()
    doc = json.loads(original)

    counts = {"inventory": 0, "quality": 0}
    patch(doc, counts)

    if counts["inventory"] == 0 or counts["quality"] == 0:
        print(
            f"⛔ 대상을 못 찾았다 — inventory {counts['inventory']} · quality {counts['quality']}. "
            "x-source-column 이름이 바뀌었는지 확인한다.",
            file=sys.stderr,
        )
        return 1

    updated = json.dumps(doc, ensure_ascii=False, indent=1)
    if updated == original:
        print(f"  이미 반영돼 있다 — 변경 없음 (inventory {counts['inventory']} · quality {counts['quality']})")
        return 0

    open(CONTRACT, "w", encoding="utf-8").write(updated)
    print(f"  ✅ *inventory_status_code {counts['inventory']}곳 — enum 4값 + 근거")
    print(f"  ✅ *quality_status_code  {counts['quality']}곳 — E-3 4값 서술 (enum 없음: 코드 문자열 미정)")
    print("     ⭐ 접미사 매칭이라 from_/to_ 전이 컬럼도 함께 덮는다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
