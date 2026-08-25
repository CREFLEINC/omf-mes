#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""작업 실적에서 «교대»를 뺀다 — 설계가 정한 적이 없다 (사용자 확정 2026-08-18). 멱등.

무엇을 고치나
-------------
생산 실적 등록 요청에서 `shiftId` 를 **뺀다**. 응답에서는 **필수를 푼다**.

  ProductionResultCreate   shiftId 속성 삭제 + 필수 목록에서 삭제   ← 화면이 안 보낸다
  ProductionResult         필수 목록에서만 삭제 (속성은 남긴다)     ← 서버가 채우면 보일 수 있다

왜 — 「교대 필수」는 설계 결정이 아니었다
----------------------------------------
⛔ **사용자 확정(2026-08-18)** — 「작업 실적 등록 화면은 작업자가 사번을
등록하고 생산을 실행하기 때문에 따로 작업자 선택이 불필요하다. **교대가
필수라고 내가 정한 적 없다.**」

그리고 함께 정해졌다 — **물리 데이터 모델은 설계 결정을 앞설 수 없고,
설계 단계에서 물리 모델 자료를 참조하지 않는다.**

⭐ 이 조항은 원래 상류가 옳았다 — 프로세스 정본 S7 트리거가 「회차·교대
**무관**」이라 적었는데, 화면 스펙이 물리 모델의 `NOT NULL` 을 보고 필수로
받아 적었고 그것이 계약까지 내려왔다. **거꾸로 흐른 자리다.**

⛔ 이미 나간 화면이다 — 변경 통지 대상
--------------------------------------
작업 실적 등록 화면의 착수 가능 통지가 이미 발행돼 있다(client#74).
요청에서 필드를 빼면 **이미 만든 것이 틀린다.** ⛔ 등급으로 알린다.

⚠ 이 패치가 손대지 않는 것
--------------------------
`WorkSession`·`WorkSessionCreate` 의 `shiftId` 는 **그대로 둔다.** 사용자
확정의 주어는 **작업 실적 등록 화면**이고, 작업 세션은 다른 화면이 소유한다.
같은 판단이 걸리는지는 그 화면을 보고 따로 정한다 — 확정문의 주어를 넘겨
적용하지 않는다.

쓰기
----
    python3 deliverables/openapi/patch-02-shift-not-a-design-input.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "production-02생산실행.json")

RESPONSE_NOTE = (
    "교대는 «설계가 정의하는 값이 아니다»(2026-08-18 사용자 확정) — 작업 실적 등록 "
    "화면은 교대를 받지 않는다. 프로세스 정본의 S7 트리거가 「회차·교대 무관」이라 한 "
    "것이 맞는 쪽이고, 「교대 필수」는 물리 모델에서 거꾸로 올라온 것이었다. "
    "서버가 자체 규칙으로 채울 수는 있으므로 속성은 남기되 «필수를 풀었다». "
    "⛔ 화면이 이 값에 의존해서는 안 된다. 📨 모델의 NOT NULL 은 작업 통지 대상이며 "
    "우리를 막지 않는다."
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

    schemas = doc["components"]["schemas"]
    for dep in ("ProductionResultCreate", "ProductionResult"):
        if dep not in schemas:
            print(f"⛔ 의존 스키마가 없다: {dep}", file=sys.stderr)
            return 1

    changed = []

    # ── ① 요청 — 속성째 뺀다. 화면이 보내지 않는다
    create = schemas["ProductionResultCreate"]
    if create["properties"].pop("shiftId", None) is not None:
        changed.append("ProductionResultCreate.properties.shiftId 삭제")
    if "shiftId" in create.get("required", []):
        create["required"] = [k for k in create["required"] if k != "shiftId"]
        changed.append("ProductionResultCreate.required 에서 shiftId 삭제")

    # ── ② 응답 — 필수만 푼다. 서버가 채울 수는 있다
    resp = schemas["ProductionResult"]
    if "shiftId" in resp.get("required", []):
        resp["required"] = [k for k in resp["required"] if k != "shiftId"]
        changed.append("ProductionResult.required 에서 shiftId 삭제")
    shift = resp["properties"].get("shiftId")
    if shift is not None and shift.get("x-internal-note") != RESPONSE_NOTE:
        shift["x-internal-note"] = RESPONSE_NOTE
        changed.append("ProductionResult.shiftId 에 내부 주석")

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
