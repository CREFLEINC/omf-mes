#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""기준정보 계약의 품목에 MES 구분 코드를 노출한다. 멱등.

왜 필요한가
-----------
`M-01-12` 재생재 등록은 **품목코드를 스캔한 뒤 「신재 / 재생재」를 고른다.**
DR-006 확정(2026-08-10)이 「자재 정보에 **ERP 코드와 별개인 MES 구분 코드**를
두어 신재/재생재를 분류」로 정했기 때문이다.

    현재  mdm.item.item_code  UNIQUE            품목코드 하나 = 행 하나
    확정  (item_code, mes_category_code) 복합 유일   같은 코드에 두 행

⛔ **화면이 두 행 중 어느 것이 재생재인지 알 방법이 지금 없다.** 품목 응답에
구분 코드가 없어서다. 그래서 이 필드가 없으면 `M-01-12` 가 품목을 못 고르고,
품목을 못 고르면 등록도 못 한다.

⭐ 왜 필터를 안 만드나
----------------------
`GET /mdm/items?mesCategoryCode=` 를 더할 수도 있으나 **만들지 않는다.**

품목코드 하나에 행이 **최대 둘**이라, 화면은 기존 `q` 검색으로 두 행을 받아
**구분 라디오로 고르면 된다.** 화면 §4 레이아웃이 정확히 그 모양이다 —
스캔하면 품목이 뜨고 그 아래 「신재 ○ 재생재 ●」가 있다.

부르는 화면이 하나뿐인 필터를 지금 만들 이유가 없다. 「이 값을 넣는 화면이
있나 · 요구가 부르나 · 담을 자리가 있나」 셋을 통과한 것은 **필드**이고
**필터가 아니다.**

⭐ 방향 — 모델이 계약을 따라온다
--------------------------------
`mes_category_code` 컬럼은 **물리 모델에 없다**(스펙 §5-B 가 `[신설]` 로
표시했다). 그것을 이유로 계약을 물리지 않는다(2026-08-10 확정 작업 방식).
모델 요청은 omf-mes#64 에 「재생재 하위 코드」 항목으로 이미 올라가 있다.

⚠ 유일 제약이 함께 바뀐다
-------------------------
구분 코드를 더하면 `item_code` 단독 유일이 깨진다. **품목코드 하나로 행
하나를 찾던 경로가 성립하지 않는다** — 스펙 §8-4a 가 대상 셋을 짚었다
(품목코드 스캔·검색 · ERP 수신 매칭 · 품목코드로 조회하는 화면).
⭐ LOT 라벨 스캔은 무관하다 — LOT 에서 품목으로 가므로 코드를 안 거친다.

쓰기
----
    python3 deliverables/openapi/patch-06-item-mes-category.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "mdm-기준정보.json")
TARGETS = ("Item",)

FIELD = "mesCategoryCode"
SPEC = {
    "x-source-column": "mes_category_code",
    "type": "string",
    "maxLength": 50,
    "x-no-example": True,
    "description": (
        "신재와 재생재를 가르는 MES 안쪽 구분. 기간계로 보내지 않는다 — "
        "기간계에는 신재와 똑같이 처리한다. 근거: DR-006 확정 · M-01-12 §5-B. "
        "⚠ 값 목록이 아직 확정되지 않았다 — 서버가 내려주는 선택지를 그대로 쓴다"
        "(공유계약 G-2)"),
    "x-internal-note": (
        "물리 모델에 아직 없는 컬럼이다(M-01-12 §5-B 가 [신설] 로 표시). "
        "함께 바뀌는 것이 유일 제약이다 — item_code 단독 UNIQUE 가 "
        "(item_code, mes_category_code) 복합 유일이 된다. "
        "부분 유일 인덱스가 아니라 복합 유일인 이유는 구분 코드가 모든 행에 있기 때문이다"
        "(기본 NEW). W-05-07 채널 매핑과 해법이 갈리는 자리다 — 공유계약 A-19 둘째 사례. "
        "모델 요청은 omf-mes#64 「재생재 하위 코드」 항목."),
}


def detect_indent(original: str, doc: dict) -> int | None:
    """원본이 어떤 들여쓰기로 쓰였는지 되짚는다. 못 알아내면 None 이다."""
    body = original.rstrip("\n")
    for candidate in (1, 2, 4):
        if json.dumps(doc, ensure_ascii=False, indent=candidate) == body:
            return candidate
    return None


def main() -> int:
    original = open(CONTRACT, encoding="utf-8").read()
    doc = json.loads(original)
    schemas = doc["components"]["schemas"]

    indent = detect_indent(original, doc)
    if indent is None:
        print("⛔ 원본 들여쓰기를 알아낼 수 없다 — 덮어쓰지 않는다", file=sys.stderr)
        return 1
    tail = original[len(original.rstrip("\n")):]

    missing = [n for n in TARGETS if n not in schemas]
    if missing:
        print(f"⛔ 대상 스키마가 없다: {missing}", file=sys.stderr)
        return 1

    for name in TARGETS:
        props = schemas[name].get("properties")
        if props is None:
            print(f"⛔ {name} 에 properties 가 없다", file=sys.stderr)
            return 1
        props[FIELD] = SPEC

    # ⛔ 원본 서식을 그대로 되돌려 쓴다. 들여쓰기를 임의로 정하면 한 필드를
    #    더한 변경이 파일 전체를 다시 쓴 것으로 나온다 — 06 계약 패치가 실제로
    #    24,502줄을 바꾼 적이 있다. 무엇이 바뀌었는지 사람이 볼 수 없게 된다.
    updated = json.dumps(doc, ensure_ascii=False, indent=indent) + tail
    if updated == original:
        print("  이미 반영돼 있다 — 변경 없음")
        return 0

    open(CONTRACT, "w", encoding="utf-8").write(updated)
    print(f"  ✅ {' · '.join(TARGETS)}.{FIELD} 노출 — M-01-12 가 품목 행을 고를 수 있다")
    print("     ⭐ 모델이 계약을 따라온다 — omf-mes#64 로 변경 요청 중")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
