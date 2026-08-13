#!/usr/bin/env python3
"""01 계약의 출고 도착지를 선택으로 바꾼다 — 자체 폐기가 있다. 멱등.

왜 필요한가
-----------
`W-01-06`·`W-04-10` 폐기 출고는 **자체 폐기**(외부 업체 없이 소각·자가처리)가
성립한다. 그때 도착지는 **없는 것이 사실**이다. 그런데 계약이 도착지 짝을
`required` 로 받고 있어 **화면이 표현할 수 없는 상태를 계약이 금지**하고 있었다.

  폐기 업체가 있으면   destinationTypeCode = DISPOSAL_SITE
                      destinationId       → mdm.partner
  자체 폐기면          둘 다 없음          ← 「자체 폐기」 체크박스

근거: DR-013 확정(2026-08-13) · DR-009(회계 계정은 MES 밖이나 거래처 기록은 별개)

⭐ 방향 — **모델이 계약을 따라온다**
------------------------------------
물리 모델은 지금 `destination_type_code`·`destination_id` 가 `NOT NULL` 이다.
**그것을 이유로 계약을 묶지 않는다.** 이 저장소의 확정된 작업 방식이
「데이터 모델은 UI/UX 설계 결정에 맞춰 따라온다」(2026-08-10)이기 때문이다.

계약은 화면이 요구하는 것을 말하고, 모델 변경 요청은 omf-mes#147 로 나가 있다.
같은 형태의 선례 — `MaterialIssueRequestCreate.reasonCode` 는 「담을 코드 컬럼이
아직 없어 remarks 로 저장된다」로 **필드를 유지한 채** 결손을 적어 뒀다.

짝 규약 (A-10)
--------------
`destinationTypeCode` 와 `destinationId` 는 **함께 있거나 함께 없다.**
한쪽만 오면 다형 참조의 대응이 깨진다 — 400 으로 막는다.

바이트 보존
-----------
이 파일은 indent=1 · 끝줄 없음으로 직렬화돼 있다. 같은 형식으로 다시 쓰므로
손대지 않은 곳은 한 바이트도 바뀌지 않는다.
"""
from __future__ import annotations

import json
import sys

CONTRACT = "deliverables/openapi/logistics-01자재창고.json"
TARGETS = ("GoodsIssue", "GoodsIssueCreate")
PAIR = ("destinationTypeCode", "destinationId")

TYPE_DESC = (
    "도착지 유형. 창고 내 이동은 위치, 공급사 반품은 거래처, 생산 투입은 공정이다. "
    "⭐ 폐기 출고에서 폐기 업체가 있으면 폐기 거래처(DISPOSAL_SITE)를 가리키고, "
    "자체 폐기면 도착지 짝을 통째로 비운다 — 나가서 없어지는 물건에는 도착지가 없다."
)
TYPE_NOTE = (
    "⭐ A-10 대응표 — 유형 코드가 어느 테이블을 가리키는가. "
    "FK 가 없어 DB 가 무결성을 보장하지 않으므로 이 표가 유일한 근거다. "
    "LOCATION → mdm.location · PARTNER → mdm.partner · PROCESS → mdm.process · "
    "WORK_ORDER → production.work_order · "
    "DISPOSAL_SITE → mdm.partner(역할 = 폐기처리 · mdm.partner_role 로 거른다). "
    "값 목록 자체는 미확정이다 — 1차 값 목록 제안안 §5-4. "
    "⭐ destinationId 와 짝이다(A-10) — 둘 다 있거나 둘 다 없다. 한쪽만 오면 400 이다. "
    "⛔ 물리 모델은 아직 destination_type_code·destination_id 가 NOT NULL 이다. "
    "그것을 이유로 계약을 묶지 않는다 — 데이터 모델은 UI/UX 설계 결정에 맞춰 따라온다"
    "(2026-08-10 확정 작업 방식). 모델 변경 요청 = omf-mes#147(짝 제약 CHECK 포함)."
)
ID_DESC = (
    "도착지 대상. destinationTypeCode 가 가리키는 테이블의 식별자다 — 대응표는 그 필드의 주석에 있다. "
    "⭐ 자체 폐기면 유형과 함께 비운다."
)
ID_NOTE = (
    "다형 참조(A-10) — 대응표는 destinationTypeCode 를 본다. "
    "⛔ 물리 모델은 아직 NOT NULL 이다 → omf-mes#147."
)


def relax(schema: dict) -> int:
    """도착지 짝을 required 에서 빼고 null 을 허용한다. 바뀐 개수를 준다."""
    changed = 0
    required = schema.get("required")
    if required:
        kept = [f for f in required if f not in PAIR]
        if len(kept) != len(required):
            schema["required"] = kept
            changed += 1

    for name, (desc, note) in zip(
        PAIR, ((TYPE_DESC, TYPE_NOTE), (ID_DESC, ID_NOTE))
    ):
        prop = (schema.get("properties") or {}).get(name)
        if prop is None:
            continue
        t = prop.get("type")
        if isinstance(t, str):
            prop["type"] = [t, "null"]
            changed += 1
        elif isinstance(t, list) and "null" not in t:
            prop["type"] = t + ["null"]
            changed += 1
        if prop.get("description") != desc:
            prop["description"] = desc
            changed += 1
        if prop.get("x-internal-note") != note:
            prop["x-internal-note"] = note
            changed += 1
    return changed


def main() -> int:
    """계약을 읽어 도착지 짝을 완화하고, 바뀐 것이 있을 때만 다시 쓴다."""
    original = open(CONTRACT, encoding="utf-8").read()
    doc = json.loads(original)
    schemas = doc["components"]["schemas"]

    missing = [n for n in TARGETS if n not in schemas]
    if missing:
        print(f"⛔ 대상 스키마가 없다: {missing}", file=sys.stderr)
        return 1

    total = sum(relax(schemas[n]) for n in TARGETS)

    updated = json.dumps(doc, ensure_ascii=False, indent=1)
    if updated == original:
        print("  이미 반영돼 있다 — 변경 없음")
        return 0

    open(CONTRACT, "w", encoding="utf-8").write(updated)
    print(f"  ✅ {' · '.join(TARGETS)} — 도착지 짝을 선택으로 ({total}곳)")
    print("     ⭐ 모델이 계약을 따라온다 — omf-mes#147 로 변경 요청 중")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
