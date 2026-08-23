#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「개발품」을 품목 속성으로 확정해 계약에 앉힌다. 멱등.

무엇을 더하나
-------------
    Item.developmentItem         (boolean)  조회 응답
    ItemUpdate.developmentItem   (boolean)  MES 확장 속성 편집

⭐ 사용자 확정 2026-08-24 — 「**개발품 구분은 품목이다**」(`omf-mes#70`)
--------------------------------------------------------------------
확정 문구(✓확정 QA #35 · WF06 S7)가 「생산 실적 송신 = **필수(개발품 제외)**」
라고만 적고 **무엇이 개발품인지의 기준**을 안 적어, 두 문서가 다르게 읽혔다.

| 문서 | 읽히는 기준 |
| --- | --- |
| 화면 인벤토리 `W-06-05` 근거란 — 「개발품 **플래그**」 | **품목 속성** |
| 설계 결정 14 · 개념모델 v2.0 — 「W/O **유형**(양산/긴급/개발품)」 | **작업지시 유형** |

**품목으로 확정됐다.** 이제 판정 축이 하나다.

⛔ 물리 컬럼이 아직 없다 — 그래도 물러서지 않는다
-------------------------------------------------
`mdm.item` 에 개발품 구분 컬럼이 **없다**(`W-06-05` §8-1 실측 · SQL 363~385 전건).
규칙 2 그대로다 — **계약은 화면대로 쓰고**, 모델 결손은 데이터 모델 담당에게
**통지**한다. 기다리지 않는다.

⭐ 선례가 바로 옆에 있다 — `Item.mesCategoryCode`
--------------------------------------------------
신재/재생재 구분도 **ERP 가 주지 않는 MES 쪽 분류**이고 같은 스키마에 이미 있다.
개발품 구분도 같은 성격이라 **같은 자리에 같은 형태로** 둔다. 새 자원을 세우지
않는다.

⛔ 코드가 아니라 참/거짓이다
----------------------------
확정 문구가 가르는 것은 「개발품인가 아닌가」 하나뿐이다. 값을 셋 이상으로
늘릴 근거가 어느 문서에도 없다 — 있는 것으로 답이 나면 값을 늘리지 않는다
(공유계약 `A-14`).

⚠ 작업지시 유형의 「개발품」을 지우지 않았다
--------------------------------------------
`work_order_type_code` 값 목록은 아직 미확정이고, `R15` 가 「양산/긴급/개발품」을
그 축으로 이름 지은 것은 사실이다. **이번 확정이 정한 것은 「ERP 송신 제외를
무엇으로 판정하는가」이지 「작업지시 유형에서 개발품을 뺀다」가 아니다.**
⭐ 계약의 현재 `workOrderTypeCode` 설명은 이미 「NORMAL 기본 · 긴급·재작업」이라
개발품이 없다(실측) — 이번 확정과 어긋나지 않는다.

⛔ 이 값을 «편집»할 수 있는 화면은 하나다
-----------------------------------------
`W-06-05`(수신본 확장 속성 편집)다. 품목 자체는 ERP 정본이라 읽기 전용이지만
**MES 확장 속성은 편집 대상**이다(공유계약 `B-4-1` ②). 그래서 `ItemUpdate` 에만
넣고 `ItemCreate` 는 건드리지 않는다 — 품목을 MES 에서 «만들지» 않는다.

쓰기
----
    python3 deliverables/openapi/patch-70-development-item.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "mdm-기준정보.json")

FIELD = "developmentItem"

DESC = (
    "개발품인가 — 참이면 생산 실적을 ERP 로 송신하지 않는다. "
    "⭐ 「개발품 제외」의 판정 축은 «품목»이다(사용자 확정 2026-08-24 · omf-mes#70). "
    "확정 문구(✓확정 QA #35 · WF06 S7)가 「생산 실적 송신 = 필수(개발품 제외)」라고만 "
    "적고 무엇이 개발품인지를 안 적어 품목 속성(화면 인벤토리)과 작업지시 유형"
    "(설계 결정 14)으로 갈려 읽히던 것을 품목으로 닫았다. "
    "⛔ mdm.item 에 담을 컬럼이 아직 없다 — 데이터 모델 담당에게 통지했다"
    "(W-06-05 §8-1). 컬럼이 서기 전까지 서버는 이 값을 늘 거짓으로 내리고, "
    "W-06-12 는 그동안 전건 송신으로 물러나 있다(A-11). "
    "근거: W-06-12 §4-B · W-06-05 §4-B"
)


def detect_indent(original: str, doc: dict):
    body = original.rstrip("\n")
    for candidate in (1, 2, 4):
        if json.dumps(doc, ensure_ascii=False, indent=candidate) == body:
            return candidate
    return None


def put_after(props: dict, key: str, value: dict, after: str) -> None:
    """`after` 바로 뒤에 끼워 넣는다 — 읽는 차례를 지킨다. 멱등."""
    props.pop(key, None)
    rebuilt: dict = {}
    placed = False
    for k, v in props.items():
        rebuilt[k] = v
        if k == after:
            rebuilt[key] = json.loads(json.dumps(value))
            placed = True
    if not placed:
        rebuilt[key] = json.loads(json.dumps(value))
    props.clear()
    props.update(rebuilt)


def main() -> int:
    original = open(CONTRACT, encoding="utf-8").read()
    doc = json.loads(original)
    indent = detect_indent(original, doc)
    if indent is None:
        print("⛔ 들여쓰기를 알아낼 수 없다 — 덮어쓰지 않는다", file=sys.stderr)
        return 1
    tail = original[len(original.rstrip("\n")):]

    schemas = doc["components"]["schemas"]
    field = {"type": "boolean", "description": DESC, "example": False}

    # 조회 — mesCategoryCode(신재/재생재) 옆에 둔다. 둘 다 MES 쪽 분류다.
    put_after(schemas["Item"]["properties"], FIELD, field, after="mesCategoryCode")
    # 편집 — W-06-05 가 MES 확장 속성으로 고친다. ⛔ ItemCreate 에는 넣지 않는다.
    put_after(schemas["ItemUpdate"]["properties"], FIELD, field, after="isActive")

    updated = json.dumps(doc, ensure_ascii=False, indent=indent) + tail
    if updated == original:
        print("  이미 반영돼 있다 — 변경 없음")
        return 0
    open(CONTRACT, "w", encoding="utf-8").write(updated)
    print("  ✅ mdm-기준정보.json — Item·ItemUpdate 에 developmentItem")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
