#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""입고 상세 조회에 저장 충돌 토큰 원천을 선언한다. 멱등.

왜 필요한가
-----------
`W-01-13` 물류 문서 진행현황·취소는 **입하·입고·출고 셋을 한 화면에서
취소**한다. 취소는 `If-Match` 를 필수로 받는데, **입고만 그 값을 받을 곳이
선언돼 있지 않았다.**

    입하  GET …/inbound-receipts/{id}   200 → ETag  ✅
    출고  GET …/goods-issues/{id}       200 → ETag  ✅
    입고  GET …/goods-receipts/{id}     200 →        ⛔

**규칙이 달라서가 아니라 누락이다.** 그대로 두면 화면은 서는데 **입고 취소만
버튼이 죽는다** — 구현팀이 「토큰이 있으면 싣고 없으면 요청을 만들지 않는」
형태로 짓고 있기 때문이다(client#177).

⭐ 원천은 «자기 상세 조회»다 — 판단할 것이 없다
-----------------------------------------------
거래처 역할에서는 원천이 갈렸다. 부모(거래처 본체)가 기간계 수신 자료라
동기화마다 판이 바뀌어, 고치지도 않은 사용자가 충돌을 보기 때문이었다.

**입고는 그 함정이 아니다.** MES 가 만들어 «내보내는» 전표다 —
`POST /logistics/goods-receipts` 가 전표 생성과 전기를 함께 하고 기간계로는
송신만 한다. 되받는 경로(`:resync`·`:acknowledge`)가 없다.

입하·출고도 같은 성격이라 자기 상세 조회에 붙어 있다. 입고만 같게 하면 된다.

쓰기
----
    python3 deliverables/openapi/patch-01-goods-receipt-etag.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "logistics-01자재창고.json")

TARGET = "/logistics/goods-receipts/{goodsReceiptId}"
MODEL = "/logistics/inbound-receipts/{inboundReceiptId}"   # 입하 — 같은 성격


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

    paths = doc["paths"]
    if TARGET not in paths:
        print(f"⛔ 대상 경로가 없다: {TARGET}", file=sys.stderr)
        return 1

    # ⭐ 문구를 손으로 쓰지 않고 «같은 성격의 이웃»에서 베낀다.
    #    손으로 다시 쓰면 30곳과 갈리고, 갈린 것은 나중에 아무도 못 찾는다.
    model = ((paths.get(MODEL, {}).get("get", {}) or {})
             .get("responses", {}).get("200", {}) or {}).get("headers")
    if not model or "ETag" not in model:
        print(f"⛔ 베낄 선언을 못 찾았다: {MODEL}", file=sys.stderr)
        return 1

    paths[TARGET]["get"]["responses"]["200"]["headers"] = json.loads(
        json.dumps(model))

    updated = json.dumps(doc, ensure_ascii=False, indent=indent) + tail
    if updated == original:
        print("  이미 반영돼 있다 — 변경 없음")
        return 0
    open(CONTRACT, "w", encoding="utf-8").write(updated)
    print(f"  ✅ {TARGET} GET 200 에 ETag 선언 — 입하·출고와 같게")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
