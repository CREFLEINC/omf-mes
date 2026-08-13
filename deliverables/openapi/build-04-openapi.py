#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 04 제품출하 OpenAPI 생성기 — shipment-04제품출하.json 을 만든다.
#
#   python3 deliverables/openapi/build-04-openapi.py
#
# ⛔ 계약은 손으로 고치지 않고 이 파일을 고쳐 다시 만든다.
# ⭐ 재현 확인은 지우고 다시 만든다 — rm shipment-04제품출하.json && python3 build-04-openapi.py
#
# 규약 — 복수 명사 · :동사 는 상태 전이에만 · 수정은 PUT(PATCH 0) ·
#        쓰기에 Idempotency-Key 필수 · ⛔ 오프라인 202 를 쓰지 않는다(2026-08-12 철회).
# 표준 라이브러리만 쓴다(저장소 관행).
import json, io, os

HERE = os.path.dirname(os.path.abspath(__file__))

I64 = {"type": "integer", "format": "int64"}
QTY = {"type": "number", "format": "double"}
TS = {"type": "string", "format": "date-time"}
DT = {"type": "string", "format": "date"}
STR = {"type": "string"}
INT = {"type": "integer"}
BOOL = {"type": "boolean"}


def ref(n): return {"$ref": f"#/components/schemas/{n}"}
def pref(n): return {"$ref": f"#/components/parameters/{n}"}


def obj(req, props, **extra):
    d = {"type": "object", "properties": props}
    if req: d["required"] = req
    d.update(extra); return d


def err(*codes):
    m = {"400": "검증 실패. 고쳐야 풀린다", "403": "권한·단말 게이팅에 막혔다",
         "404": "없다", "409": "충돌", "501": "구현할 수 없다 — 상류 미해소"}
    out = {}
    for c in codes:
        s = ref("ConflictResponse") if c == "409" else ref("ErrorResponse")
        out[c] = {"description": m[c], "content": {"application/json": {"schema": s}}}
    return out


def listed(name, desc="목록"):
    return {"200": {"description": desc, "content": {"application/json": {"schema": obj(
        ["items", "page"], {"items": {"type": "array", "items": ref(name)},
                            "page": ref("PageMeta")})}}}}


def one(name, code="200", desc="상세"):
    return {code: {"description": desc, "content": {"application/json": {"schema": ref(name)}}}}


def q(name, schema, desc=None):
    d = {"name": name, "in": "query", "schema": schema}
    if desc: d["description"] = desc
    return d


def pathparam(name):
    return {"name": name, "in": "path", "required": True, "schema": I64}


PAGE = [q("page", INT, "1 부터"), q("size", INT, "기본 50")]

# ⛔ 오프라인 파라미터를 쓰지 않는다.
#
#   3단계 실측 — 04 계약의 오프라인 대상 오퍼레이션은 0건이다.
#   04 테이블을 쓰는 현장 화면은 M-04-01(제품LOT 피킹) 하나뿐인데 오프라인
#   진입 차단이다(Release 판정을 캐시할 수 없다 · 공유계약 C-6 · 결정 10).
#   오프라인을 허용하는 셋(P-04-03·M-04-03·M-04-04)은 전부 남의 테이블(01·02)에
#   쓰므로 그쪽 계약의 IfMatchVersionOptional 을 그대로 쓴다.
#
#   ⚠ 「POP·모바일이 몇 장인가」로 오프라인 표면을 세면 틀린다 — 어느 테이블에
#      쓰는가를 봐야 한다.
#   ⛔ 202 는 2026-08-12 에 철회됐다(공유계약 C-7 주석) — 오프라인이면 HTTP 요청
#      자체가 일어나지 않아 서버가 「접수했다」를 말할 수 없다.

schemas, paths = {}, {}

# ══════════════════════════════════════════════════════════════════
# 공통
# ══════════════════════════════════════════════════════════════════
schemas["ErrorItem"] = obj(["scope", "code", "message"], {
    "scope": {"type": "string", "enum": ["field", "screen"],
              "description": "오류의 범위. 근거: 공유계약 G-1", "example": "field"},
    "field": {"type": "string", "description": "scope=field 일 때 대상 프로퍼티명",
              "example": "shippedQty"},
    "code": {"type": "string", "example": "QTY_EXCEEDS_ALLOCATION"},
    "message": {"type": "string",
                "description": "화면이 그대로 보여도 되는 문장. 「어떻게 풀 것인가」를 담는다. 근거: 공유계약 G-3"}})
schemas["ErrorResponse"] = obj(["errors"], {"errors": {"type": "array", "items": ref("ErrorItem")}})
schemas["ConflictResponse"] = obj(["code", "message"], {
    "code": {"type": "string",
             "enum": ["VERSION_CONFLICT", "DUPLICATE_KEY", "INVALID_STATE",
                      "ALREADY_CONFIRMED", "CANCEL_IN_PROGRESS"],
             "description": ("ALREADY_CONFIRMED 는 이미 확정된 출하라는 뜻이다 — 확정 취소 경로가 없으므로 "
                             "되돌릴 수 없다(W-04-12 §5-3). CANCEL_IN_PROGRESS 는 취소 결재가 진행 중이라 "
                             "확정할 수 없다는 뜻이다(J-7). 근거: W-04-12 §5-8")},
    "message": STR,
    "currentVersion": {"type": "string", "description": "VERSION_CONFLICT 일 때 서버의 현재 version_no"}})
schemas["PageMeta"] = obj(["page", "size", "total"], {
    "page": {"type": "integer", "example": 1},
    "size": {"type": "integer", "example": 50},
    "total": {"type": "integer", "example": 84}})

# ══════════════════════════════════════════════════════════════════
# 출하 3층 — 라. 업무 문서 형
# ══════════════════════════════════════════════════════════════════
schemas["SalesOrderLine"] = obj(
    ["salesOrderLineId", "lineNo", "itemId", "orderedQty", "uomId", "shippedQty"], {
    "salesOrderLineId": I64, "lineNo": INT, "itemId": I64,
    "orderedQty": QTY, "uomId": I64,
    "requestedDeliveryDate": DT,
    "shippedQty": {"type": "number", "format": "double",
                   "description": "누적 출하 수량. 서버가 유지한다 — 화면이 더하지 않는다(공유계약 L-2)"}})
schemas["SalesOrder"] = obj(
    ["salesOrderId", "salesOrderNo", "customerId", "shipToPartnerId", "orderDate", "statusCode"], {
    "salesOrderId": I64,
    "salesOrderNo": {"type": "string", "example": "SO-2026-0813-0042"},
    "erpSalesOrderNo": {"type": "string",
                        "description": "ERP 원번호. 연계로 들어온 건에만 있다", "example": "ERP-SO-99001"},
    "customerId": I64, "shipToPartnerId": I64, "orderDate": DT,
    "statusCode": STR,
    "lines": {"type": "array", "items": ref("SalesOrderLine")},
    "versionNo": INT},
    description=("고객사 출하지시서 수신본. ⛔ 등록 경로를 두지 않는다 — 연계 수신이 기본이라 "
                 "목록에 그냥 나타난다(W-04-01 §5-6). 파일 업로드는 고객사마다 형식이 달라 "
                 "요청 본문을 정할 수 없고 화면도 비활성이다. "
                 "⭐ 상위지시는 nullable 이 확정이다 — 무지시 standalone 이 예외가 아니라 상시 구조다"))

schemas["ShipmentRequestLine"] = obj(
    ["shipmentRequestLineId", "lineNo", "itemId", "requestedQty", "allocatedQty",
     "shippedQty", "uomId", "shippingInspectionRequired"], {
    "shipmentRequestLineId": I64, "lineNo": INT,
    "salesOrderLineId": {"type": ["integer", "null"], "format": "int64",
                         "description": "⛔ 비어도 된다 — 단독 생성이면 상위 지시서가 없다"},
    "itemId": I64,
    "requestedQty": QTY,
    "allocatedQty": {"type": "number", "format": "double",
                     "description": "배정 수량. 요청 수량을 넘을 수 없다(W-04-01 §5-1)"},
    "shippedQty": QTY, "uomId": I64,
    "customerLotRequirement": {"type": ["string", "null"],
                               "description": "고객이 지정한 LOT 조건. 피킹이 이것을 지켜야 한다(M-04-01)"},
    "shippingInspectionRequired": {"type": "boolean",
                                   "description": "출하검사 대상인가. 라인마다 토글한다(W-04-01)"},
    "minimumRemainingShelfLifeDays": {"type": ["integer", "null"],
                                      "description": "잔여 유효기간 하한. 피킹이 이것으로 LOT 을 거른다"}})
schemas["ShipmentRequestLineCreate"] = obj(
    ["itemId", "requestedQty", "allocatedQty", "uomId", "shippingInspectionRequired"], {
    "salesOrderLineId": {"type": ["integer", "null"], "format": "int64"},
    "itemId": I64, "requestedQty": QTY, "allocatedQty": QTY, "uomId": I64,
    "customerLotRequirement": {"type": ["string", "null"]},
    "shippingInspectionRequired": BOOL,
    "minimumRemainingShelfLifeDays": {"type": ["integer", "null"]}})
schemas["ShipmentRequest"] = obj(
    ["shipmentRequestId", "shipmentRequestNo", "customerId", "shipToPartnerId",
     "requestedShipDate", "statusCode"], {
    "shipmentRequestId": I64,
    "shipmentRequestNo": {"type": "string", "example": "SR-2026-0813-0108"},
    "salesOrderId": {"type": ["integer", "null"], "format": "int64",
                     "description": "⛔ 필수가 아니다 — 단독 생성 경로가 상시 구조다(W-04-01 §5-2)"},
    "customerId": I64, "shipToPartnerId": I64, "requestedShipDate": DT,
    "statusCode": STR,
    "lines": {"type": "array", "items": ref("ShipmentRequestLine")},
    "versionNo": INT},
    description="MES 출하작업지시. W-04-01 「편성」·「단독 생성」이 만든다")
schemas["ShipmentRequestCreate"] = obj(
    ["customerId", "shipToPartnerId", "requestedShipDate", "lines"], {
    "salesOrderId": {"type": ["integer", "null"], "format": "int64",
                     "description": "지시서를 경유하면 채우고 단독 생성이면 비운다"},
    "customerId": I64, "shipToPartnerId": I64, "requestedShipDate": DT,
    "lines": {"type": "array", "minItems": 1, "items": ref("ShipmentRequestLineCreate")}},
    description=("편성. 라인 1건 이상이고 배정 수량이 1 이상이어야 한다(W-04-01 §5-7). "
                 "⛔ 편성 취소를 두지 않는다 — 출하작업지시 취소는 범위 밖이다"))

schemas["ShipmentLotAllocation"] = obj(
    ["shipmentLotAllocationId", "shipmentLineId", "lotId", "allocatedQty", "uomId"], {
    "shipmentLotAllocationId": I64, "shipmentLineId": I64,
    "lotId": I64, "lotNo": STR,
    "handlingUnitId": {"type": ["integer", "null"], "format": "int64",
                       "description": "⚠ 비어도 된다 — 포장하지 않는 출하도 있다(P-04-01 §4-C)"},
    "allocatedQty": QTY, "uomId": I64,
    "oqcPassed": {"type": "boolean",
                  "description": ("⭐ 서버가 판정한 값 — 이 배분의 LOT 이 출하검사에 합격했는가. "
                                  "납품라벨 대상 목록이 「합격」만 활성하는 데 쓴다(P-04-02 §5). "
                                  "검사 결과는 03 품질 계약이 소유한다")},
    "packedQty": {"type": "number", "format": "double",
                  "description": "이미 포장에 담긴 수량. 배분 잔여 = allocatedQty − packedQty 를 서버가 파생한다(L-2)"}},
    description=("출하 LOT 배분 — genealogy 종결점이다. ⛔ 등록 경로를 두지 않는다 — "
                 "출하 처리가 shipment·shipment_line 과 한 트랜잭션으로 만든다(W-04-04 §5 · 공유계약 B-8). "
                 "shipment_line_id 가 NOT NULL 이라 출하보다 먼저 생길 수 없다"))
schemas["ShipmentLotAllocationPacking"] = obj(["handlingUnitId"], {
    "handlingUnitId": {"type": "integer", "format": "int64",
                       "description": "이 배분을 담은 포장 단위. 취급 단위는 01 자재창고 계약이 소유한다"}},
    description="포장 연결. P-04-01 이 포장을 확정할 때 배분에 포장 단위를 잇는다")

schemas["ShipmentLine"] = obj(
    ["shipmentLineId", "lineNo", "shipmentRequestLineId", "itemId", "shippedQty", "uomId"], {
    "shipmentLineId": I64, "lineNo": INT, "shipmentRequestLineId": I64,
    "itemId": I64, "shippedQty": QTY, "uomId": I64,
    "goodsIssueLineId": {"type": ["integer", "null"], "format": "int64",
                         "description": "⚠ 비어도 된다 — 재고 차감이 아직 안 걸린 구간이 있다(W-04-04 §5-2)"},
    "allocations": {"type": "array", "items": ref("ShipmentLotAllocation")}})
schemas["ShipmentLineCreate"] = obj(
    ["shipmentRequestLineId", "shippedQty", "uomId", "allocations"], {
    "shipmentRequestLineId": I64, "shippedQty": QTY, "uomId": I64,
    "allocations": {"type": "array", "minItems": 1,
                    "items": ref("ShipmentLotAllocationCreate")}})
schemas["ShipmentLotAllocationCreate"] = obj(["lotId", "allocatedQty", "uomId"], {
    "lotId": I64, "allocatedQty": QTY, "uomId": I64,
    "handlingUnitId": {"type": ["integer", "null"], "format": "int64"}})
schemas["Shipment"] = obj(
    ["shipmentId", "shipmentNo", "shipmentRequestId", "warehouseId", "statusCode"], {
    "shipmentId": I64,
    "shipmentNo": {"type": "string", "example": "SH-2026-0813-0031"},
    "shipmentRequestId": I64, "warehouseId": I64,
    "vehicleNo": STR, "driverName": STR, "sealNo": STR, "transportDocumentNo": STR,
    "loadingWorkerId": I64, "carrierId": I64,
    "loadedAt": {"type": ["string", "null"], "format": "date-time",
                 "description": "상차 시각. ⚠ 시작 시각이 필수가 아니라 구간 형이 아니다 — 상태 전이의 부수 기록이다"},
    "shippedAt": {"type": ["string", "null"], "format": "date-time", "description": "출하 시각"},
    "statusCode": {"type": "string",
                   "description": "생애주기는 여기가 갖는다 — 미확정 → 확정 / 취소. 근거: W-04-12 §5"},
    "erpDeliveryNo": {"type": ["string", "null"],
                      "description": "ERP 납품 번호. 확정 후 연계가 채운다 — 04 가 쓰지 않는다"},
    "remarks": STR,
    "lines": {"type": "array", "items": ref("ShipmentLine")},
    "versionNo": INT},
    description=("실물 출하. ⭐ 2026-08-07 「출하 2단 확정」으로 재고 차감·ERP 송신 적재가 "
                 "W-04-12 로 갔다 — 이 리소스를 만드는 것은 미확정 출하까지다(W-04-04 §5)"))
schemas["ShipmentCreate"] = obj(["shipmentRequestId", "warehouseId", "lines"], {
    "shipmentRequestId": I64, "warehouseId": I64,
    "vehicleNo": STR, "driverName": STR, "sealNo": STR, "transportDocumentNo": STR,
    "loadingWorkerId": I64, "carrierId": I64,
    "expedited": {"type": "boolean", "default": False,
                  "description": "⭐ 긴급 직행 출하인가(W-04-05) — 피킹·검사를 건너뛴다"},
    "expediteReason": {"type": ["string", "null"],
                       "description": "expedited 가 참이면 필수다. 근거: W-04-05 §5-5 · 공유계약 A-12"},
    "remarks": STR,
    "lines": {"type": "array", "minItems": 1, "items": ref("ShipmentLineCreate")}},
    description=("출하 처리. 출하·라인·LOT 배분을 한 트랜잭션으로 만든다(공유계약 B-8). "
                 "⛔ 확정하지 않는다 — 미확정 출하까지다. 확정은 :confirm 이다"))
schemas["ShipmentCancelRequest"] = obj(["reason"], {
    "reason": {"type": "string",
               "description": "취소 사유. 필수다 — 근거: W-04-12 §5-8 · 공유계약 A-12"}})
schemas["ShipmentCancel"] = obj([], {
    "remarks": {"type": ["string", "null"]}},
    description=("취소 실행. ⭐ 승인 완료만으로 통과시키지 않는다 — 실행 시점에 후속을 다시 판정한다"
                 "(공유계약 J-8). 그 사이에 확정됐으면 409 ALREADY_CONFIRMED 다"))

# ══════════════════════════════════════════════════════════════════
# 부적합 — 라. 업무 문서 형
# ══════════════════════════════════════════════════════════════════
schemas["NonconformanceLot"] = obj(
    ["nonconformanceLotId", "lotId", "affectedQty", "uomId",
     "qualityStatusBeforeCode", "qualityStatusAfterCode"], {
    "nonconformanceLotId": I64, "lotId": I64, "lotNo": STR,
    "affectedQty": QTY, "uomId": I64,
    "qualityStatusBeforeCode": STR, "qualityStatusAfterCode": STR})
schemas["NonconformanceLotCreate"] = obj(["lotId", "affectedQty", "uomId"], {
    "lotId": I64, "affectedQty": QTY, "uomId": I64})
schemas["Nonconformance"] = obj(
    ["nonconformanceId", "nonconformanceNo", "itemId", "severityCode",
     "description", "statusCode", "openedAt"], {
    "nonconformanceId": I64,
    "nonconformanceNo": {"type": "string", "example": "NC-2026-0813-0042"},
    "itemId": I64,
    "workOrderId": I64,
    "inspectionResultId": {"type": ["integer", "null"], "format": "int64",
                           "description": "검사에서 나온 부적합이면 가리킨다. 검사 결과는 03 품질 계약이 소유한다"},
    "severityCode": STR,
    "description": {"type": "string",
                    "description": ("⭐ 판정자의 유일한 입력이다 — 「불량」 두 글자면 뒤에서 판단이 안 된다. "
                                    "화면이 형식을 유도한다. 근거: W-04-07 §5-3 · 공유계약 A-12")},
    "responsibleDepartmentId": I64,
    "actionDescription": STR, "actionOwnerId": I64,
    "actionDueDate": DT, "actionCompletedAt": TS,
    "statusCode": {"type": "string",
                   "description": ("의뢰 전 · 판정 대기 · 판정 완료. ⭐ 세 값짜리 진행 단계라 "
                                   "구간 형이 아니다 — 끝 시각의 부재로는 앞의 둘을 못 가른다(04 계약 1단계 §3)")},
    "openedAt": TS,
    "closedAt": {"type": ["string", "null"], "format": "date-time",
                 "description": "종료 시각. 개시보다 빠를 수 없다"},
    "lots": {"type": "array", "items": ref("NonconformanceLot")},
    "versionNo": INT},
    description="부적합. W-04-07 「부적합 등록」과 W-04-06 반품 등록이 만든다")
schemas["NonconformanceCreate"] = obj(["itemId", "severityCode", "description", "lots"], {
    "itemId": I64,
    "workOrderId": {"type": ["integer", "null"], "format": "int64"},
    "inspectionResultId": {"type": ["integer", "null"], "format": "int64"},
    "severityCode": STR,
    "description": {"type": "string", "minLength": 1,
                    "description": "판정의 유일한 입력이라 비울 수 없다. 근거: 공유계약 A-12"},
    "responsibleDepartmentId": {"type": ["integer", "null"], "format": "int64"},
    "lots": {"type": "array", "minItems": 1, "items": ref("NonconformanceLotCreate")}})
schemas["DispositionRequest"] = obj(["requestedQty", "uomId"], {
    "requestedQty": {"type": "number", "format": "double",
                     "description": "판정을 의뢰할 수량. 1 이상이어야 한다(W-04-07 §5-7)"},
    "uomId": I64,
    "remarks": {"type": ["string", "null"]}},
    description=("판정 의뢰. ⭐ 이 화면은 판정하지 않는다 — 재작업/폐기 판정은 전 도메인에서 "
                 "03 품질 소관으로 통일돼 있다(F04 정합 확정 2026-07-07 · W-04-07 §5-1). "
                 "받는 화면은 W-03-10 이고 처분 결정 자원은 품질 계약이 소유한다(DR-008 확정 3-A)"))

# ══════════════════════════════════════════════════════════════════
# 경로
# ══════════════════════════════════════════════════════════════════
paths["/logistics/sales-orders"] = {"get": {
    "tags": ["shipment"], "summary": "출하지시서 목록",
    "description": "고객사 지시서 수신본. 연계가 채운다 — 등록 경로가 없다. 근거: W-04-01 §5-6",
    "parameters": [q("customerId", I64), q("statusCode", STR),
                   q("orderDateFrom", DT), q("orderDateTo", DT),
                   q("unassignedOnly", BOOL, "아직 편성되지 않은 것만 — 「편성 여부」 필터"),
                   q("q", STR, "지시서 번호 검색")] + PAGE,
    "responses": listed("SalesOrder")}}
paths["/logistics/sales-orders/{salesOrderId}"] = {
    "parameters": [pathparam("salesOrderId")],
    "get": {"tags": ["shipment"], "summary": "출하지시서 한 건",
            "description": "라인을 함께 내린다. 근거: W-04-01 §3",
            "responses": dict(list(one("SalesOrder").items()) + list(err("404").items())),
            "x-internal-note": ("파일 업로드 경로를 두지 않았다 — 고객사마다 형식이 달라 요청 본문을 "
                                "정할 수 없고 화면도 「비활성 + 사유」로 물러났다(W-04-01 §5-6 · 공유계약 G-9). "
                                "형식이 정해지면 그때 더한다.")}}

paths["/logistics/shipment-requests"] = {
    "get": {"tags": ["shipment"], "summary": "출하작업지시 목록",
            "description": "W-04-02 출하 예정 목록. 기간이 필수다(공유계약 L-3). 근거: W-04-02 §5",
            "parameters": [
                q("customerId", I64), q("shipToPartnerId", I64), q("statusCode", STR),
                q("shippingInspectionRequired", BOOL, "검사 상태 필터"),
                q("shipDateFrom", DT, "필수 — 공유계약 L-3"), q("shipDateTo", DT),
                q("sort", STR, "출하일·고객·작업지시번호 셋만. 근거: 공유계약 L-4")] + PAGE,
            "responses": listed("ShipmentRequest")},
    "post": {"tags": ["shipment"], "summary": "출하작업지시 편성",
             "description": ("W-04-01 「편성」과 「단독 생성」을 한 경로로 받는다. "
                             "⭐ salesOrderId 를 비우면 단독 생성이다 — 무지시 standalone 이 예외가 아니라 "
                             "상시 구조다. 배정 수량은 요청 수량을 넘을 수 없다. 근거: W-04-01 §5-1·§5-2"),
             "parameters": [pref("IdempotencyKey")],
             "requestBody": {"required": True, "content": {"application/json": {
                 "schema": ref("ShipmentRequestCreate")}}},
             "responses": dict(list(one("ShipmentRequest", "201", "편성됨").items())
                               + list(err("400", "403", "409").items()))}}
paths["/logistics/shipment-requests/{shipmentRequestId}"] = {
    "parameters": [pathparam("shipmentRequestId")],
    "get": {"tags": ["shipment"], "summary": "출하작업지시 한 건",
            "description": "라인을 함께 내린다",
            "responses": dict(list(one("ShipmentRequest").items()) + list(err("404").items())),
            "x-internal-note": ("편성 취소 경로를 두지 않았다 — 화면이 「⛔ 두지 않는다 — 출하작업지시 "
                                "취소는 범위 밖」이라 적었다(W-04-01 §5-7).")}}

paths["/logistics/shipments"] = {
    "get": {"tags": ["shipment"], "summary": "출하 목록",
            "description": "W-04-02·W-04-04·W-04-12 가 함께 쓴다. 기간 필수(L-3)",
            "parameters": [
                q("shipmentRequestId", I64), q("customerId", I64), q("statusCode", STR),
                q("warehouseId", I64),
                q("pickedOnly", BOOL, "피킹이 끝난 건만 — W-04-04 진입 필터"),
                q("unconfirmedOnly", BOOL, "미확정만 — W-04-12 기본"),
                q("shipDateFrom", DT, "필수"), q("shipDateTo", DT),
                q("sort", STR, "경과일 긴 순이 기본이다. 근거: W-04-12 §5-7")] + PAGE,
            "responses": listed("Shipment")},
    "post": {"tags": ["shipment"], "summary": "출하 처리",
             "description": ("출하·라인·LOT 배분을 한 트랜잭션으로 만든다(공유계약 B-8). "
                             "⛔ 확정하지 않는다 — 미확정 출하까지이고 확정은 :confirm 이다"
                             "(2026-08-07 출하 2단 확정). "
                             "긴급 직행이면 expedited 를 참으로 보내고 사유가 필수다(W-04-05). "
                             "근거: W-04-04 §5 · W-04-05 §5-5"),
             "parameters": [pref("IdempotencyKey")],
             "requestBody": {"required": True, "content": {"application/json": {
                 "schema": ref("ShipmentCreate")}}},
             "responses": dict(list(one("Shipment", "201", "출하됨 — 미확정").items())
                               + list(err("400", "403", "409").items())),
             "x-internal-note": ("재고 차감(goods_issue)은 01 자재창고 계약이, ERP 송신 적재는 "
                                 "06 연계가 소유한다 — 2026-08-07 출하 2단 확정으로 둘 다 W-04-12 "
                                 "확정 시점으로 갔다. shipment_line.goods_issue_line_id 가 nullable 인 "
                                 "것이 그 구간을 표현한다.")}}
paths["/logistics/shipments/{shipmentId}"] = {
    "parameters": [pathparam("shipmentId")],
    "get": {"tags": ["shipment"], "summary": "출하 한 건",
            "description": "라인과 LOT 배분을 함께 내린다 — genealogy 종결점이다",
            "responses": dict(list(one("Shipment").items()) + list(err("404").items()))}}
paths["/logistics/shipments/{shipmentId}:confirm"] = {
    "parameters": [pathparam("shipmentId")],
    "post": {"tags": ["shipment"], "summary": "출하 확정",
             "description": ("미확정 → 확정. ⭐ 이 시점에 재고 차감과 ERP 송신 적재가 걸린다"
                             "(2026-08-07 출하 2단 확정). "
                             "취소 결재가 진행 중이면 409 CANCEL_IN_PROGRESS 다(공유계약 J-7). "
                             "⛔ 확정 취소 경로가 없다 — 되돌릴 수 없다. 근거: W-04-12 §5-3·§5-8"),
             "parameters": [pref("IdempotencyKey"), pref("IfMatchVersion")],
             "responses": dict(list(one("Shipment", "200", "확정됨").items())
                               + list(err("400", "403", "404", "409").items()))}}
paths["/logistics/shipments/{shipmentId}:request-cancel"] = {
    "parameters": [pathparam("shipmentId")],
    "post": {"tags": ["shipment"], "summary": "출하 취소 요청",
             "description": ("미확정 구간에서만 된다. 사유가 필수다. 승인은 공통 계약이 소유한다. "
                             "01 자재창고가 쓰는 :request-cancel 과 같은 형태다. 근거: W-04-12 §5-8"),
             "parameters": [pref("IdempotencyKey"), pref("IfMatchVersion")],
             "requestBody": {"required": True, "content": {"application/json": {
                 "schema": ref("ShipmentCancelRequest")}}},
             "responses": dict(list(one("Shipment", "200", "상신됨").items())
                               + list(err("400", "403", "404", "409").items()))}}
paths["/logistics/shipments/{shipmentId}:cancel"] = {
    "parameters": [pathparam("shipmentId")],
    "post": {"tags": ["shipment"], "summary": "출하 취소 실행",
             "description": ("승인 완료 후 실행한다. ⭐ 승인만으로 통과시키지 않는다 — 실행 시점에 "
                             "후속을 다시 판정한다(공유계약 J-8). 그 사이 확정됐으면 409 다. "
                             "근거: W-04-12 §5-8"),
             "parameters": [pref("IdempotencyKey"), pref("IfMatchVersion")],
             "requestBody": {"required": True, "content": {"application/json": {
                 "schema": ref("ShipmentCancel")}}},
             "responses": dict(list(one("Shipment", "200", "취소됨").items())
                               + list(err("400", "403", "404", "409").items()))}}

paths["/logistics/shipment-lot-allocations"] = {"get": {
    "tags": ["shipment"], "summary": "출하 LOT 배분 목록",
    "description": ("P-04-01 이 납품라벨↔생산LOT 매칭을 판정받고, P-04-02 가 납품라벨 대상을 고른다. "
                    "⭐ 매칭 판정을 화면이 하지 않는다 — 서버가 배분을 보고 판정한다"
                    "(P-04-01 §5-1 · 공유계약 C-6). 근거: P-04-01 · P-04-02 §5"),
    "parameters": [
        q("shipmentId", I64), q("shipmentLineId", I64), q("lotId", I64),
        q("handlingUnitId", I64),
        q("unpackedOnly", BOOL, "아직 포장에 담기지 않은 것만 — 배분 잔여가 남은 것"),
        q("oqcPassed", BOOL,
          "⭐ 출하검사 합격분만. 납품라벨 대상 목록이 「합격」만 활성하는 데 쓴다(P-04-02 §5)")] + PAGE,
    "responses": listed("ShipmentLotAllocation"),
    "x-internal-note": ("등록 경로를 두지 않았다 — shipment_lot_allocation.shipment_line_id 가 "
                        "NOT NULL 이라 출하보다 먼저 생길 수 없고, 출하 처리가 한 트랜잭션으로 만든다"
                        "(W-04-04 §4-B). 제품 피킹(M-04-01)은 배분이 아니라 "
                        "inventory.inventory_reservation 에 쓴다 — 그 경로는 01 자재창고 계약 소관이다. "
                        "⛔ 2026-08-13 실측 — 01 계약에 POST /inventory/reservations 가 없다. "
                        "M-04-01 착수 통지가 그것에 걸린다.")}}
paths["/logistics/shipment-lot-allocations/{shipmentLotAllocationId}"] = {
    "parameters": [pathparam("shipmentLotAllocationId")],
    "put": {"tags": ["shipment"], "summary": "배분에 포장 단위 연결",
            "description": ("P-04-01 이 포장을 확정할 때 배분과 취급 단위를 잇는다. "
                            "취급 단위 자체는 01 자재창고 계약이 소유한다(POST /inventory/handling-units · :pack). "
                            "근거: P-04-01 §4-C"),
            "parameters": [pref("IdempotencyKey")],
            "requestBody": {"required": True, "content": {"application/json": {
                "schema": ref("ShipmentLotAllocationPacking")}}},
            "responses": dict(list(one("ShipmentLotAllocation", "200", "연결됨").items())
                              + list(err("400", "403", "404", "409").items())),
            "x-internal-note": ("If-Match 를 쓰지 않는다 — shipment_lot_allocation 에 version_no 가 "
                                "없다(기록 전용). 같은 배분에 다른 포장이 이미 붙어 있으면 409 다.")}}

paths["/quality/nonconformances"] = {
    "get": {"tags": ["quality"], "summary": "부적합 목록",
            "description": ("W-04-07 조회·필터. 상태는 의뢰 전 · 판정 대기 · 판정 완료 세 값이다 — "
                            "⭐ 세 값짜리 진행 단계라 열림/닫힘 두 값으로 판정하지 않는다. 근거: W-04-07 §5"),
            "parameters": [
                q("statusCode", STR, "의뢰 전 · 판정 대기 · 판정 완료"),
                q("warehouseId", I64), q("itemId", I64), q("lotId", I64),
                q("severityCode", STR),
                q("openedFrom", TS), q("openedTo", TS)] + PAGE,
            "responses": listed("Nonconformance")},
    "post": {"tags": ["quality"], "summary": "부적합 등록",
             "description": ("W-04-07 「부적합 등록」과 W-04-06 반품 입고가 만든다. "
                             "심각도와 내용이 필수다 — 내용은 판정자의 유일한 입력이라 비울 수 없다"
                             "(공유계약 A-12). 근거: W-04-07 §5-3"),
             "parameters": [pref("IdempotencyKey")],
             "requestBody": {"required": True, "content": {"application/json": {
                 "schema": ref("NonconformanceCreate")}}},
             "responses": dict(list(one("Nonconformance", "201", "등록됨").items())
                               + list(err("400", "403", "409").items())),
             "x-internal-note": ("반품 입고 자체는 01 자재창고 계약이 소유한다 — "
                                 "POST /logistics/goods-receipts 의 receiptTypeCode·reasonCode 가 이미 "
                                 "일반형이고 화면도 「원천 구분을 reason_code 에 접어 넣는다」로 설계돼 있다"
                                 "(W-04-06 §5-2). 한 화면이 두 계약을 쓴다.")}}
paths["/quality/nonconformances/{nonconformanceId}"] = {
    "parameters": [pathparam("nonconformanceId")],
    "get": {"tags": ["quality"], "summary": "부적합 한 건",
            "description": ("영향 LOT 을 함께 내린다. ⭐ 03 품질의 W-03-09 「부적합 열기」가 이 경로로 온다 — "
                            "특채는 부적합을 NOT NULL 로 참조하는데 03 계약에는 열 경로가 없었다"),
            "responses": dict(list(one("Nonconformance").items()) + list(err("404").items()))}}
paths["/quality/nonconformances/{nonconformanceId}:request-disposition"] = {
    "parameters": [pathparam("nonconformanceId")],
    "post": {"tags": ["quality"], "summary": "처분 판정 의뢰",
             "description": ("⭐ 04 는 의뢰만 한다 — 재작업/폐기 판정은 전 도메인에서 03 품질 소관으로 "
                             "통일돼 있다(F04 정합 확정 2026-07-07). 화면도 「판정」 버튼을 두지 않는다. "
                             "근거: W-04-07 §5-1·§5-7"),
             "parameters": [pref("IdempotencyKey"), pref("IfMatchVersion")],
             "requestBody": {"required": True, "content": {"application/json": {
                 "schema": ref("DispositionRequest")}}},
             "responses": dict(list(one("Nonconformance", "200", "의뢰됨").items())
                               + list(err("400", "403", "404", "409").items()))}}


# ══════════════════════════════════════════════════════════════════
# example 자동 부여
# ══════════════════════════════════════════════════════════════════
EX = {"Id": 1001, "id": 1001, "No": "SH-2026-0813-0031", "Code": "SHIPPED", "code": "SHIPPED",
      "Qty": 120.0, "qty": 120.0, "At": "2026-08-13T10:22:00+09:00",
      "Date": "2026-08-13", "Note": "비고", "note": "비고", "Name": "홍길동", "name": "홍길동"}


def example_for(name, sch):
    t, f = sch.get("type"), sch.get("format")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), None)
    if "enum" in sch: return sch["enum"][0]
    if "example" in sch: return sch["example"]
    if f == "uuid": return "6f1a0c2e-8b4d-4a1e-9c33-0b7c2f5d1a90"
    if f == "date-time": return "2026-08-13T10:22:00+09:00"
    if f == "date": return "2026-08-13"
    if t == "integer": return 1001 if name.endswith("Id") else 1
    if t == "number": return 120.0
    if t == "boolean": return True
    if t == "string":
        for k, v in EX.items():
            if name.endswith(k): return v
        if name.endswith("No"): return "SH-2026-0813-0031"
        return "값"
    return None


def fill(sch):
    for pname, p in (sch.get("properties") or {}).items():
        if not isinstance(p, dict) or "$ref" in p: continue
        t = p.get("type")
        if t in ("array", "object"): continue
        if "example" not in p:
            e = example_for(pname, p)
            if e is not None: p["example"] = e


for _s in schemas.values():
    fill(_s)

# ⛔ 공유 스칼라 오염 가드 — 03 트랙의 Blocker 를 되풀이하지 않는다.
#
#   I64·TS 같은 전역 dict 는 수십 개 프로퍼티가 같은 객체를 참조한다. 어딘가에서
#   schemas[...]["properties"][...]["description"] = ... 처럼 나중에 넣으면 그 하나가
#   전부에 붙는다. 03 에서 실제로 새서 19곳(component 12 + 쿼리 파라미터 7)에
#   엉뚱한 설명이 붙었다(PR #141).
#
#   검사기는 description 의 「존재」를 보지 「내용」을 보지 않아 못 잡는다. 여기서 막는다 —
#   설명을 붙이려면 {**TS, "description": …} 로 인라인 사본을 만든다.
_ALLOWED = {"type", "format", "example"}
for _name, _proto in (("I64", I64), ("QTY", QTY), ("TS", TS), ("DT", DT),
                      ("STR", STR), ("INT", INT), ("BOOL", BOOL)):
    _extra = set(_proto) - _ALLOWED
    if _extra:
        raise SystemExit(
            f"⛔ 공유 스칼라 {_name} 이 오염됐습니다 — 추가된 키 {sorted(_extra)}.\n"
            f"   전역 dict 를 변형하면 그 타입의 모든 프로퍼티에 같은 값이 붙습니다.\n"
            f"   설명을 붙이려면 {{**{_name}, \"description\": …}} 로 인라인 사본을 만드세요.")

OUT = os.path.join(HERE, "shipment-04제품출하.json")
src = json.load(io.open(os.path.join(HERE, "logistics-01자재창고.json"), encoding="utf-8"))
doc = {
    "openapi": "3.1.0",
    "info": {
        "title": "omf-mes 04 제품출하 도메인 API (초안)",
        "version": "0.1.0",
        "description": (
            "04 제품출하 도메인 API 계약. 출하 3층(고객사 지시서 수신본 - MES 출하작업지시 - 실물 출하)과 "
            "출하 LOT 배분, 부적합, 처분 결정 조회를 덮는다. "
            "출하지시서는 연계 수신이 기본이라 등록 경로를 두지 않고, 상위 지시가 없는 단독 편성이 상시 구조다. "
            "출하는 2단 확정이다 — 출하 처리가 미확정 출하까지 만들고 확정이 재고 차감과 연계 송신을 건다. "
            "확정 취소 경로는 없다. "
            "이 계약은 남의 계약을 많이 쓴다 — 검사는 품질, 입고·출고·재고·취급 단위는 자재창고, "
            "실적은 생산실행, 승인과 출력물은 공통, 품목과 연계는 기준정보가 소유한다. "
            "⛔ 오프라인 대상 오퍼레이션이 없다 — 이 계약의 테이블에 쓰는 현장 화면 하나가 "
            "판정값을 캐시할 수 없어 오프라인 진입을 차단하기 때문이다."),
        "x-internal-note": (
            "설계·도출 근거는 uiux/2026-08-13-API스펙-04제품출하/ 의 00~03 단계 문서다. "
            "대상 화면 16 — 도메인 배지 18 에서 출력물 계약이 덮는 P-04-02·P-04-04 를 뺀 것이다. "
            "리소스 5 · 라인 4 · 읽기만 1 · 액션 근거 147건(화면 액션 표 · 본문 도출 0). "
            "미해소를 계약이 드러낸다 — ⛔⛔ 처분 결정을 만드는 화면이 인벤토리 116 전체에 0건이라 "
            "세 화면(W-04-10·W-04-11·P-04-03)의 진입 목록이 빈다. "
            "⛔ 01 계약에 POST /inventory/reservations 가 없어 M-04-01 제품 피킹이 걸린다. "
            "omf-mes#117(재구성 이벤트 기록 테이블 부재)로 M-04-03 되돌리기 경로를 두지 않았다. "
            "omf-mes#118 로 선별 실행 경로를 두지 않았다.")
    },
    "servers": [{"url": "/api", "description": "온프레미스 설치형"}],
    "tags": [{"name": "shipment", "description": "출하 — 지시서 · 작업지시 · 출하 · LOT 배분"},
             {"name": "quality", "description": "부적합과 처분 결정 — 판정은 03 품질 소관이다"}],
    "paths": dict(sorted(paths.items())),
    "components": {"parameters": dict(src["components"]["parameters"]),
                   "schemas": dict(sorted(schemas.items()))}
}
io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
ops = sum(1 for p in doc["paths"].values() for m in p if m in ("get", "post", "put", "patch", "delete"))
acts = sum(1 for p in doc["paths"] if ":" in p.rsplit("/", 1)[-1])
print(f"경로 {len(doc['paths'])} · 오퍼레이션 {ops} · 스키마 {len(doc['components']['schemas'])} "
      f"· :동사 경로 {acts} · {os.path.getsize(OUT)/1024:.0f}KB")
