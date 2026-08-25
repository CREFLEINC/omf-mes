#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""검사기준 버전의 샘플 크기를 «비율(%)» 로 되돌린다 — 확정 그대로. 멱등.

무엇을 고치나
-------------
  InspectionPlanVersion / …Create / …Update
      samplingQty (수량)  →  samplingRatio (백분율 0 초과 100 이하)

왜 — 확정은 처음부터 「비율」이었다
----------------------------------
✓확정 **2026-07-15**(제품 검사 방식) — 「검사 방식 = 전수/샘플 선택제 · 샘플 방식 =
제품 단위/LOT 단위 + **샘플 비율(%)**」.

그런데 화면 스펙이 물리 모델의 `sampling_qty`(수량)를 보고 **「샘플 수량」으로
받도록 썼고**, 계약이 그대로 받았다. ⛔ **물리 모델은 설계 결정을 앞설 수 없다**
(사용자 확정 2026-08-18 · `00-서식.md` v1.1 §2).

⛔ 수량으로 두면 «검사 강도»가 로트 크기마다 달라진다
----------------------------------------------------
    「샘플 30」 설정  →  로트 100 개면      30 %
                     →  로트 10,000 개면   0.3 %

품목·공정별로 **한 번 설정**하는 값인데 로트 크기는 매번 다르다. 고객이
「30 % 를 뽑아라」를 설정할 방법이 없고, 설정한 대로 검사되지도 않는다.

⭐ **비율이 원천이고 수량이 파생이다** — 스펙 자신이 「비율↔수량 변환은 로트
크기를 알아야 한다」고 적었다. 검사 시점에 로트 크기가 정해지면 그때 환산된다.

⛔ 둘을 함께 두지 않는다
------------------------
수량 필드를 남기면 «어느 쪽이 이기는가»를 또 정해야 하고, 두 값이 어긋난 자료가
쌓인다. **비율 하나로 간다**(2026-08-18 사용자 확정).

⛔ 이미 구현된 화면이다 — 변경 통지 대상
----------------------------------------
검사기준 등록 화면의 착수 통지가 **닫혀 있다**(client#12 = 구현 완료).
필드를 갈아치우므로 **이미 만든 것이 틀린다.** ⛔ 등급으로 알린다.

📨 모델에는 비율 컬럼이 없다 — 작업 통지이고 우리를 막지 않는다.

쓰기
----
    python3 deliverables/openapi/patch-06-sampling-ratio.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "mdm-기준정보.json")

TARGETS = ("InspectionPlanVersion", "InspectionPlanVersionCreate",
           "InspectionPlanVersionUpdate")

RATIO_DESC = (
    "샘플 비율(%). 검사할 몫을 백분율로 지정한다 — 0 초과 100 이하. "
    "실제 검사 «수량»은 검사 시점에 로트 크기로 환산되는 파생값이라 여기서 받지 않는다."
)

RATIO_NOTE = (
    "✓확정 2026-07-15 가 「샘플 비율(%)」로 정한 것이다. 앞서 물리 모델의 sampling_qty(수량)를 "
    "따라 «수량»으로 받았으나 2026-08-18 되돌렸다 — 물리 모델은 설계 결정을 앞설 수 없다(사용자 확정). "
    "⛔ 수량으로 두면 한 번 설정한 값이 로트 크기마다 다른 검사 강도가 된다(30 이 로트 100 에서는 30%, "
    "10,000 에서는 0.3%). 📨 모델에 비율 컬럼이 없다 — 작업 통지이며 우리를 막지 않는다. "
    "⛔ 이미 구현된 화면이라 변경 통지 대상이다."
)

RATIO_SCHEMA = {
    "type": ["number", "null"],
    "format": "double",
    "exclusiveMinimum": 0,
    "maximum": 100,
    "example": 30,
    "description": RATIO_DESC,
    "x-internal-note": RATIO_NOTE,
}


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

    schemas = doc["components"]["schemas"]
    for dep in TARGETS:
        if dep not in schemas:
            print(f"⛔ 의존 스키마가 없다: {dep}", file=sys.stderr)
            return 1

    changed = []
    for name in TARGETS:
        props = schemas[name]["properties"]
        if "samplingQty" in props:
            props.pop("samplingQty")
            changed.append(f"{name}.samplingQty 삭제")
        req = schemas[name].get("required", [])
        if "samplingQty" in req:
            schemas[name]["required"] = [k for k in req if k != "samplingQty"]
            changed.append(f"{name}.required 에서 samplingQty 삭제")
        if props.get("samplingRatio") != RATIO_SCHEMA:
            props["samplingRatio"] = dict(RATIO_SCHEMA)
            changed.append(f"{name}.samplingRatio 신설")

    if not changed:
        print("✅ 이미 반영돼 있다 — 바꾼 것 없음 (멱등)")
        return 0

    open(CONTRACT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=indent) + tail
    )
    for line in changed:
        print(f"  · {line}")
    print(f"✅ {len(changed)}곳 반영 — {os.path.basename(CONTRACT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
