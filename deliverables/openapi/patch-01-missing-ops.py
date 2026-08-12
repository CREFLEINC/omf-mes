#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""01 자재창고 계약에 빠져 있던 오퍼레이션 3건을 더한다.

    python3 deliverables/openapi/patch-01-missing-ops.py

⛔ 왜 생성기가 아니라 패치인가 — `logistics-01자재창고.json` 은 손으로 유지돼 왔고
   생성기가 없다(02 완료보고 §8 #5). 105스키마를 통째로 생성기로 옮기는 것은 이 작업의
   범위가 아니므로, 더하는 것만 **되돌릴 수 있고 다시 돌릴 수 있는 형태**로 남긴다.
   멱등하다 — 이미 있으면 건드리지 않는다.

## 무엇이 빠져 있었나

02 요구서가 세 화면에 「01 계약이 준다 · 02 가 정의하지 않는다」라고 적었는데
**01 도 정의하지 않았다.** 역방향 ② 검사기(`verify-doc-citations.py`)가 찾았다.

    W-02-10  POST /logistics/material-issue-requests            경로는 있고 GET 만 있었다
    P-02-06  POST /trace/lots/{lotId}:complete                  경로가 없었다
    P-02-08  POST /inventory/handling-units/{handlingUnitId}:pack  경로가 없었다

세 화면 다 착수 통지가 나가 있었다(client #72·#75·#76). 프론트가 아직 착수하지
않아 코드 피해는 없었다.
"""
from __future__ import annotations

import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "logistics-01자재창고.json")

I64 = {"type": "integer", "format": "int64"}
QTY = {"type": "number", "format": "double"}
TS = {"type": "string", "format": "date-time"}
DT = {"type": "string", "format": "date"}


def ref(name: str) -> dict:
    return {"$ref": f"#/components/schemas/{name}"}


def pref(name: str) -> dict:
    return {"$ref": f"#/components/parameters/{name}"}


def err(*codes: str) -> dict:
    msg = {"400": "검증 실패. 고쳐야 풀린다", "403": "권한 없음",
           "404": "없다", "409": "저장 충돌. 다시 읽어 오면 풀린다"}
    return {c: {"description": msg[c], "content": {"application/json": {
        "schema": ref("ErrorResponse" if c != "409" else "ConflictResponse")}}} for c in codes}


def col(source: str, schema: dict, desc: str, example=None) -> dict:
    """01 계약의 프로퍼티 표기 — x-source-column 을 앞에 둔다."""
    out = {"x-source-column": source, **schema, "description": desc}
    if example is not None:
        out["example"] = example
    return out


# ── 오프라인 3종 세트 — 01 계약이 쓰는 형태 그대로(C-1 · C-7 · C-8 · C-9)
OFFLINE_BODY = {
    "businessDate": {"type": "string", "format": "date",
                     "description": "근거: 공유계약 C-8", "example": "2026-08-12"},
    "occurredAt": {"type": "string", "format": "date-time",
                   "description": "단말에서 실제로 일어난 시각. 근거: 공유계약 C-8",
                   "example": "2026-08-12T10:22:00+09:00"},
}
# ⛔ 202/QueuedResponse 를 쓰지 않는다.
#    C-7 의 「큐 접수 202」 표현은 02 계약이 처음 도입한 것이고, 01 은 오프라인 대상
#    오퍼레이션 10건 전부가 IfMatchVersionOptional 만 달고 202 를 선언하지 않는다.
#    (01 의 202 여섯 건은 결재 상신용이라 성격이 다르다.)
#    여기서만 202 를 넣으면 01 이 스스로와 어긋난다 — 01 전체를 202 로 옮기는 것은
#    오퍼레이션 10건을 건드리는 별개 작업이므로 이 패치의 범위가 아니다.


def build_schemas() -> dict:
    """더할 스키마 넷."""
    return {
        "MaterialIssueRequestCreateLine": {
            "type": "object",
            "required": ["itemId", "requestedQty", "uomId"],
            "description": (
                "출고 요청 라인. bomComponentId 가 비면 BOM 밖 품목이다 — 모델이 허용하므로 "
                "계약도 허용하되 화면이 경고를 붙인다. 근거: W-02-10 §5-3"),
            "properties": {
                "bomComponentId": col("bom_component_id", {"type": ["integer", "null"], "format": "int64"},
                                      "BOM 소요량에서 불러온 라인이면 원본을 가리킨다. 비면 BOM 밖 품목", 1001),
                "itemId": col("item_id", I64, "요청 품목", 1001),
                "requestedQty": col("requested_qty", QTY, "요청 수량. 0 보다 커야 한다", 120.0),
                "uomId": col("uom_id", I64, "단위", 1001),
            },
        },
        "MaterialIssueRequestCreate": {
            "type": "object",
            "required": ["workOrderId", "destinationLocationId", "lines",
                         "businessDate", "occurredAt"],
            "description": (
                "추가 자재 출고 요청 발행. 라인이 1건 이상이고 수량이 0 보다 커야 한다. "
                "근거: W-02-10 §5-6"),
            "properties": {
                "workOrderId": col("work_order_id", I64, "대상 작업지시", 1001),
                "destinationLocationId": col("destination_location_id", I64,
                                             "도착 위치. FK 라 실재하는 위치여야 한다. 근거: W-02-10 §5-4", 1001),
                "requiredAt": col("required_at", {"type": ["string", "null"], "format": "date-time"},
                                  "필요 시각", "2026-08-12T14:00:00+09:00"),
                "reasonCode": {
                    "type": ["string", "null"],
                    "description": (
                        "요청 사유. ⛔ 담을 코드 컬럼이 아직 없어 remarks 로 저장된다 — "
                        "「무절차 반출 금지」를 화면이 말하지만 집계는 안 된다. 근거: omf-mes#87"),
                    "example": "부족분 보충"},
                "remarks": col("remarks", {"type": ["string", "null"]},
                               "비고. 사유 코드 자리가 생기기 전까지 사유가 여기 담긴다", "라인 정지로 추가 소요"),
                "lines": {"type": "array", "minItems": 1,
                          "items": ref("MaterialIssueRequestCreateLine"),
                          "description": "1건 이상. 근거: W-02-10 §5-6"},
                **OFFLINE_BODY,
            },
        },
        "LotComplete": {
            "type": "object",
            "required": ["businessDate", "occurredAt"],
            "description": (
                "생산 LOT 완료. 계획 수량에 미달하면 사유 코드가 필요하고, 서버가 작업지시에 "
                "그 사유를 함께 기록한다 — 한 트랜잭션이다(공유계약 B-8). 근거: P-02-06 §5-5"),
            "properties": {
                "completionVarianceReasonCode": {
                    "type": ["string", "null"],
                    "description": (
                        "미달 마감 사유. 계획 수량에 미달하면 필수이고 서버가 400 으로 막는다. "
                        "work_order.completion_variance_reason_code 로 간다. 근거: P-02-06 §5-5"),
                    "example": "자재 부족"},
                "remarks": col("remarks", {"type": ["string", "null"]}, "비고", "비고"),
                **OFFLINE_BODY,
            },
        },
        "HandlingUnitPack": {
            "type": "object",
            "required": ["contents", "businessDate", "occurredAt"],
            "description": (
                "포장 확정. 포장 단위와 내용물 N행이 한 트랜잭션으로 확정된다(공유계약 B-8) — "
                "내용물 없이 확정할 수 없다. 근거: P-02-08 §5-6"),
            "properties": {
                "contents": {"type": "array", "minItems": 1,
                             "items": ref("HandlingUnitContentUpsert"),
                             "description": "포장에 담긴 것. 1건 이상"},
                "locationId": col("location_id", {"type": ["integer", "null"], "format": "int64"},
                                  "포장을 둔 위치", 1001),
                "remarks": {"type": ["string", "null"], "description": "비고", "example": "비고"},
                **OFFLINE_BODY,
            },
        },
    }


def build_paths() -> dict:
    """더할 오퍼레이션 셋. 키가 이미 있으면 병합한다(POST 만 얹는다)."""
    return {
        "/logistics/material-issue-requests": {
            "post": {
                "tags": ["logistics"],
                "summary": "추가 자재 출고 요청 발행",
                "description": (
                    "현장이 BOM 소요량 밖의 자재를 수동으로 요청한다. 라인 1건 이상이고 "
                    "각 수량이 0 보다 커야 한다. BOM 밖 품목도 담을 수 있다. "
                    "오프라인 대상 오퍼레이션이다 — Idempotency-Key 는 필수이고 If-Match 는 선택이다"
                    "(공유계약 C-9). 근거: W-02-10 §5-6"),
                "parameters": [pref("IdempotencyKey"), pref("IfMatchVersionOptional")],
                "requestBody": {"required": True, "content": {"application/json": {
                    "schema": ref("MaterialIssueRequestCreate")}}},
                "responses": {
                    "201": {"description": "발행됨", "content": {"application/json": {
                        "schema": ref("MaterialIssueRequestDetailResponse")}}},
                    **err("400", "403", "409")},
                "x-internal-note": (
                    "02 요구서 §3-9 가 이 오퍼레이션을 「01 계약」이라 적었는데 01 에 GET 만 있었다. "
                    "역방향 ② 검사기가 찾아 2026-08-12 에 더했다(client #72). "
                    "⛔ 요청 사유 코드 컬럼이 아직 없어 reasonCode 가 remarks 로 저장된다(omf-mes#87)."),
            }
        },
        "/trace/lots/{lotId}:complete": {
            "parameters": [{"name": "lotId", "in": "path", "required": True, "schema": I64}],
            "post": {
                "tags": ["trace"],
                "summary": "생산 LOT 완료",
                "description": (
                    "생산 LOT 을 완료로 옮긴다. 계획 수량에 미달하면 사유 코드가 필수이고, "
                    "서버가 LOT 상태와 작업지시 사유를 한 트랜잭션으로 기록한다(공유계약 B-8). "
                    "⛔ 라벨 출력은 이 오퍼레이션 밖이다 — 공통 출력물 계약이 소유한다. "
                    "오프라인 대상이다(공유계약 C-9). 근거: P-02-06 §5-5"),
                "parameters": [pref("IdempotencyKey"), pref("IfMatchVersionOptional")],
                "requestBody": {"required": True, "content": {"application/json": {
                    "schema": ref("LotComplete")}}},
                "responses": {
                    "200": {"description": "완료됨", "content": {"application/json": {
                        "schema": ref("Lot")}}},
                    **err("400", "403", "404", "409")},
                "x-internal-note": (
                    "02 요구서 §3-16 이 이 오퍼레이션을 「01 계약」이라 적었는데 경로 자체가 없었다. "
                    "역방향 ② 검사기가 찾아 2026-08-12 에 더했다(client #75). "
                    "품질 판정 축(정상·불량 등)은 03 품질 계약이 옮긴다 — 여기서 바꾸는 것은 "
                    "생산 LOT 의 수명주기 상태다."),
            }
        },
        "/inventory/handling-units/{handlingUnitId}:pack": {
            "parameters": [{"name": "handlingUnitId", "in": "path", "required": True, "schema": I64}],
            "post": {
                "tags": ["inventory"],
                "summary": "포장 확정",
                "description": (
                    "포장 단위와 내용물 N행을 한 트랜잭션으로 확정한다(공유계약 B-8). "
                    "내용물이 비면 400 이다. 이미 확정된 포장은 409 다. "
                    "⛔ 라벨·인식표 출력은 이 오퍼레이션 밖이다 — 공통 출력물 계약이 소유한다. "
                    "오프라인 대상이다(공유계약 C-9). 근거: P-02-08 §5-6"),
                "parameters": [pref("IdempotencyKey"), pref("IfMatchVersionOptional")],
                "requestBody": {"required": True, "content": {"application/json": {
                    "schema": ref("HandlingUnitPack")}}},
                "responses": {
                    "200": {"description": "확정됨", "content": {"application/json": {
                        "schema": ref("HandlingUnitDetailResponse")}}},
                    **err("400", "403", "404", "409")},
                "x-internal-note": (
                    "02 요구서 §3-17 이 이 오퍼레이션을 「01 계약」이라 적었는데 경로 자체가 없었다. "
                    "역방향 ② 검사기가 찾아 2026-08-12 에 더했다(client #76). "
                    "POST /inventory/handling-units 는 빈 포장 단위를 만들고, 이 액션이 내용물과 함께 "
                    "닫는다 — 두 왕복인 것은 스캔이 여러 번 일어나기 때문이다."),
            }
        },
    }


def main() -> int:
    with io.open(TARGET, encoding="utf-8") as f:
        doc = json.load(f)

    schemas = doc["components"]["schemas"]
    paths = doc["paths"]

    added_s, added_p, skipped = [], [], []

    for name, body in build_schemas().items():
        if name in schemas:
            skipped.append(f"스키마 {name}")
            continue
        schemas[name] = body
        added_s.append(name)

    for path, item in build_paths().items():
        target = paths.setdefault(path, {})
        for key, value in item.items():
            if key in target:
                skipped.append(f"{path} [{key}]")
                continue
            target[key] = value
            if key != "parameters":
                added_p.append(f"{key.upper()} {path}")

    doc["paths"] = dict(sorted(paths.items()))
    doc["components"]["schemas"] = dict(sorted(schemas.items()))

    with io.open(TARGET, "w", encoding="utf-8") as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=1))

    ops = sum(1 for p in doc["paths"].values() for m in p
              if m in ("get", "post", "put", "patch", "delete"))
    print(f"더한 오퍼레이션 {len(added_p)}: {', '.join(added_p) or '없음'}")
    print(f"더한 스키마 {len(added_s)}: {', '.join(added_s) or '없음'}")
    if skipped:
        print(f"이미 있어 건너뜀 {len(skipped)}: {', '.join(skipped)}")
    print(f"결과 — 경로 {len(doc['paths'])} · 오퍼레이션 {ops} "
          f"· 스키마 {len(doc['components']['schemas'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
