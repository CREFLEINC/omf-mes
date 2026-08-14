#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""01 계약에 재생재 등록 경로를 더한다 — `M-01-12` 의 결손을 메운다. 멱등.

왜 필요한가
-----------
`M-01-12` 재생재 등록은 **화면 스펙이 완성돼 있는데 계약만 없었다.**

01 계약 트랙(2026-08-06)이 「#64 재생재 하위코드 미확정으로 동결」이라 적고
**23화면만 다루고 끝냈다.** 그 뒤 **DR-006 이 확정**(2026-08-10)돼 확대 17차
(2026-08-11)에서 스펙이 작성됐는데, **계약이 따라오지 않았다.**

그래서 스펙 §8 이 「차단 미결 0건 — 착수 통지 조건은 만족하나 **API 계약이
없어 내지 않는다**」로 끝나 있다. 이 패치가 그 문장을 지운다.

⭐ 왜 기존 `POST /trace/lots` 를 안 쓰나
----------------------------------------
두 가지가 다르다.

    M-01-02 자재LOT 스캔·등록   스캔한 34자리가 **그대로** 번호가 된다
    M-01-12 재생재 등록          **서버가 발번**한다(오프라인 두 단말이
                                 같은 번호를 만들면 안 된다 · 공유계약 C-2)

`LotCreate` 는 `lotNo` 를 `required` 로 받는다. 여기에 재생재를 태우려면
그 `required` 를 빼야 하는데, **그러면 `M-01-02` 가 번호를 안 보내도
계약이 통과시킨다.** 그 화면은 반드시 보내야 한다 — 계약을 느슨하게 만드는
대가가 크다.

⭐ 왜 「등록 건」이 자원인가
---------------------------
스펙 §5-2 가 정확히 그것을 요구했다.

    trace.lot.source_type_code · source_id 는 FK 없는 다형 참조다
    (한 칸이 상황에 따라 여러 표를 가리킨다).
    재생재 LOT 은 **입고 전표도 작업지시도 아니다** →  새 값 RECYCLE_ENTRY
    source_id 가 NOT NULL 이다 →  **가리킬 행이 있어야 한다**

⚠ 「추적하지 않는다」와 「기록하지 않는다」는 다르다(스펙 §9-3). DR-006 이
뺀 것은 **원료 계보**이고, **누가 언제 얼마를 등록했나는 남는다.**

⛔ 왜 목록·상세 조회를 안 두나
------------------------------
부르는 화면이 0건이다. `M-01-12` 는 저장 후 입력만 비우고 같은 화면에
머물며(스펙 §5-3), 횡단 조회인 `/logistics/document-progress` 가 덮는
6유형에도 재생재 등록이 없다. `/production/material-losses` 를 뺀 것과
같은 기준이다 — **테이블이 아니라 버튼을 센다.**

⭐ 방향 — 모델이 계약을 따라온다
--------------------------------
물리 모델에 **등록 건을 담을 표가 없고** `mdm.item.mes_category_code` 도
없다. **그것을 이유로 계약을 물리지 않는다**(2026-08-10 확정 작업 방식).
모델 요청은 omf-mes#64 에 이미 「재생재 하위 코드」 항목으로 올라가 있고,
DR-006 확정 내용을 코멘트로 구체화한다.

쓰기
----
    python3 deliverables/openapi/patch-01-recycle-entry.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "logistics-01자재창고.json")
PATH = "/logistics/recycle-entries"

I64 = {"type": "integer", "format": "int64", "example": 1001}


def schemas_to_add() -> dict:
    """등록 건 하나와 그 결과. 결과에 LOT 번호가 실려 온다 — 화면이 그것을 보인다."""
    return {
        "RecycleEntryCreate": {
            "x-source-table": "trace.lot",
            "type": "object",
            "required": ["itemId", "quantity", "warehouseId", "locationId",
                         "businessDate", "occurredAt"],
            "description": (
                "재생재 등록. 새 자재 LOT 을 만들고 그 수량만큼 재고를 늘린다. "
                "LOT 번호는 서버가 매긴다 — 화면이 미리 보이지 못한다. 근거: M-01-12 §5-1"),
            "properties": {
                "itemId": {
                    **I64,
                    "description": (
                        "재생재 품목. 신재와 다른 행이다 — 재고·투입·출고가 품목으로 서므로 "
                        "품목이 갈리면 집계가 자동으로 갈린다. 근거: M-01-12 §3-2. "
                        "⚠ 이 행은 품목 마스터에 미리 있어야 한다 — 이 경로가 만들지 않는다"),
                },
                "quantity": {
                    "x-source-column": "initial_qty",
                    "type": "number",
                    "exclusiveMinimum": 0,
                    "example": 12.5,
                    "description": "0 이하는 400 이다. 근거: M-01-12 §6",
                },
                "warehouseId": {**I64, "description": "기본값은 단말에 묶인 창고다"},
                "locationId": {**I64, "description": "비울 수 없다. 근거: M-01-12 §6"},
                "businessDate": {"type": "string", "format": "date", "example": "2026-08-11"},
                "occurredAt": {"type": "string", "format": "date-time",
                               "example": "2026-08-11T09:12:00+09:00"},
                "remarks": {"type": "string", "example": "비고"},
            },
            "x-internal-note": (
                "단위를 본문으로 받지 않는다 — 품목의 기본 단위를 그대로 쓴다. "
                "화면도 읽기 전용으로 보인다(스펙 §5-A). 받으면 품목과 어긋난 단위가 들어올 자리가 생긴다. "
                "⛔ 구분(신재·재생재)도 본문에 없다 — 그것은 품목 마스터의 값이고, "
                "화면은 품목코드 + 구분으로 «어느 품목 행인가»를 정한 뒤 itemId 하나만 보낸다."),
        },
        "RecycleEntry": {
            "type": "object",
            "required": ["recycleEntryId", "lotId", "lotNo", "itemId", "quantity"],
            "description": "등록 결과. 서버가 매긴 LOT 번호가 실려 온다 — 화면이 그것을 보인다.",
            "properties": {
                "recycleEntryId": {
                    **I64,
                    "description": (
                        "등록 건 자체의 번호. 새로 만든 LOT 의 원천 참조가 이것을 가리킨다 "
                        "— 원천 유형 코드는 RECYCLE_ENTRY 다"),
                },
                "lotId": I64,
                "lotNo": {"type": "string", "example": "LOT-2026-000045",
                          "description": "서버가 매긴 번호"},
                "itemId": I64,
                "quantity": {"type": "number", "example": 12.5},
                "uomId": {**I64, "description": "품목의 기본 단위가 그대로 온다"},
                "warehouseId": I64,
                "locationId": I64,
                "businessDate": {"type": "string", "format": "date", "example": "2026-08-11"},
                "occurredAt": {"type": "string", "format": "date-time",
                               "example": "2026-08-11T09:12:00+09:00"},
            },
            "x-internal-note": (
                "계보를 싣지 않는다. trace.lot.parent_lot_id 와 trace.lot_relation 이 "
                "둘 다 실재하지만 DR-006 이 「어디서 어떻게 만들어졌는지 추적은 불필요」로 확정했다. "
                "⚠ 일부만 채워진 계보가 빈 계보보다 위험하다 — 재생재에만 부모가 있으면 "
                "계보 조회 화면이 「추적 가능」으로 오해한다(스펙 §3-1 · 공유계약 G-24 의 데이터 판)."),
        },
    }


def operation() -> dict:
    return {
        "post": {
            "tags": ["logistics"],
            "summary": "재생재 등록",
            "description": (
                "분쇄재가 생기면 현장이 등록한다. 새 자재 LOT 을 만들고 그 수량만큼 "
                "재고를 늘린다 — 한 트랜잭션이다. **LOT 번호는 서버가 매긴다**: "
                "번호를 클라이언트가 정하면 오프라인 두 단말이 같은 번호를 만든다"
                "(공유계약 C-2). 그래서 화면이 「번호는 저장 후 정해집니다」를 먼저 말한다. "
                "근거: M-01-12 §5-1·§5-3 · DR-006 확정. "
                "오프라인 대상 오퍼레이션이다 — Idempotency-Key 는 필수이고 If-Match 는 선택이다. "
                "⛔ 오프라인일 때는 이 오퍼레이션이 호출되지 않는다 — 셸의 outbox 가 들고 있다가 "
                "연결되면 그때 보낸다. 그래서 서버 응답은 온라인일 때의 것 하나뿐이다."),
            "parameters": [
                {"$ref": "#/components/parameters/IdempotencyKey"},
                {"$ref": "#/components/parameters/IfMatchVersionOptional"},
            ],
            "requestBody": {
                "required": True,
                "content": {"application/json": {
                    "schema": {"$ref": "#/components/schemas/RecycleEntryCreate"}}},
            },
            "responses": {
                "201": {"description": "등록됨 — LOT 번호가 실려 온다",
                        "content": {"application/json": {
                            "schema": {"$ref": "#/components/schemas/RecycleEntry"}}}},
                "400": {"description": "검증 실패. 고쳐야 풀린다",
                        "content": {"application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "403": {"description": "단말·권한 게이팅에 막혔다",
                        "content": {"application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorResponse"}}}},
                "409": {"description": "충돌",
                        "content": {"application/json": {
                            "schema": {"$ref": "#/components/schemas/ConflictResponse"}}}},
            },
            "x-internal-note": (
                "혼적 제약(allow_mixed_item·allow_mixed_lot)을 서버가 막지 않는다 — "
                "화면이 경고하고 현장이 판단한다(스펙 §6). 「막지 않는다」가 설계다. "
                "⚠ 물리 모델에 등록 건을 담을 표가 없고 mdm.item.mes_category_code 도 없다. "
                "계약은 화면이 요구하는 것을 말하고 모델 변경은 omf-mes#64 로 나가 있다 "
                "— 「데이터 모델은 UI/UX 설계 결정에 맞춰 따라온다」(2026-08-10 확정)."),
        }
    }


def main() -> int:
    original = open(CONTRACT, encoding="utf-8").read()
    doc = json.loads(original)

    for dep in ("ErrorResponse", "ConflictResponse"):
        if dep not in doc["components"]["schemas"]:
            print(f"⛔ 의존 스키마가 없다: {dep}", file=sys.stderr)
            return 1
    for dep in ("IdempotencyKey", "IfMatchVersionOptional"):
        if dep not in doc["components"]["parameters"]:
            print(f"⛔ 의존 파라미터가 없다: {dep}", file=sys.stderr)
            return 1

    doc["components"]["schemas"].update(schemas_to_add())
    doc["components"]["schemas"] = dict(sorted(doc["components"]["schemas"].items()))
    doc["paths"][PATH] = operation()
    doc["paths"] = dict(sorted(doc["paths"].items()))

    updated = json.dumps(doc, ensure_ascii=False, indent=1)
    if updated == original:
        print("  이미 반영돼 있다 — 변경 없음")
        return 0

    open(CONTRACT, "w", encoding="utf-8").write(updated)
    print(f"  ✅ {PATH} 신설 — 경로 {len(doc['paths'])} · 스키마 {len(doc['components']['schemas'])}")
    print("     ⭐ 모델이 계약을 따라온다 — omf-mes#64 로 변경 요청 중")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
