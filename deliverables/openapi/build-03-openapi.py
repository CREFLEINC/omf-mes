#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 03 품질 OpenAPI 생성기 — quality-03품질.json 을 만든다.
#
#   python3 deliverables/openapi/build-03-openapi.py
#
# ⛔ 계약은 손으로 고치지 않고 이 파일을 고쳐 다시 만든다.
# ⭐ 재현 확인은 「돌리고 검사기가 통과했다」로는 안 된다 — 지우고 다시 만든다:
#       rm quality-03품질.json && python3 build-03-openapi.py
#
# 규약은 06·01·02 계약을 계승한다 — 복수 명사 · :동사 는 상태 전이에만 ·
# 수정은 PUT(⛔ PATCH 0) · 쓰기에는 Idempotency-Key 필수 · 오프라인 경로는 If-Match 선택.
# 표준 라이브러리만 쓴다(저장소 관행).
#
# ⚠ /quality 접두어는 06 기준정보 계약과 나눠 쓴다 — 06 이 마스터(검사기준·불량코드),
#    03 이 실행(의뢰·결과·측정치·불량실적·특채·보류)이다. 같은 경로는 0건이다.
import json, io, os

HERE = os.path.dirname(os.path.abspath(__file__))

I64 = {"type": "integer", "format": "int64"}
QTY = {"type": "number", "format": "double"}
TS  = {"type": "string", "format": "date-time"}
DT  = {"type": "string", "format": "date"}
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
    m = {"400": "검증 실패. 고쳐야 풀린다", "403": "단말·권한 게이팅에 막혔다",
         "404": "없다", "409": "충돌", "501": "구현할 수 없다 — 상류 미해소"}
    out = {}
    for c in codes:
        s = ref("ConflictResponse") if c == "409" else ref("ErrorResponse")
        out[c] = {"description": m[c], "content": {"application/json": {"schema": s}}}
    return out


def listed(schema_name, desc="목록"):
    return {"200": {"description": desc, "content": {"application/json": {"schema": obj(
        ["items", "page"], {"items": {"type": "array", "items": ref(schema_name)},
                            "page": ref("PageMeta")})}}}}


def one(schema_name, code="200", desc="상세"):
    return {code: {"description": desc,
                   "content": {"application/json": {"schema": ref(schema_name)}}}}


def q(name, schema, desc=None):
    d = {"name": name, "in": "query", "schema": schema}
    if desc: d["description"] = desc
    return d


def pathparam(name):
    return {"name": name, "in": "path", "required": True, "schema": I64}


PAGE = [q("page", INT, "1 부터"), q("size", INT, "기본 50")]

OFFLINE = ("오프라인 대상 오퍼레이션이다 — Idempotency-Key 는 필수이고 If-Match 는 선택이다. "
           "큐는 낙관적 잠금 토큰을 싣지 않는다(공유계약 C-9). "
           "즉시 처리되면 201, 큐에 담기면 202 다(C-7).")

QUEUED = {"202": {"description": "큐에 담겼다 — 아직 서버가 모른다. 근거: 공유계약 C-7",
                  "content": {"application/json": {"schema": ref("QueuedResponse")}}}}

schemas, paths = {}, {}

# ══════════════════════════════════════════════════════════════════
# 공통 — 06·01·02 계약과 같은 모양을 쓴다
# ══════════════════════════════════════════════════════════════════
schemas["ErrorItem"] = obj(["scope", "code", "message"], {
    "scope": {"type": "string", "enum": ["field", "screen"],
              "description": "오류의 범위. 근거: 공유계약 G-1", "example": "field"},
    "field": {"type": "string", "description": "scope=field 일 때 대상 프로퍼티명",
              "example": "acceptedQty"},
    "code": {"type": "string", "example": "QTY_SUM_MISMATCH"},
    "message": {"type": "string",
                "description": "화면이 그대로 보여도 되는 문장. 「어떻게 풀 것인가」를 담는다. 근거: 공유계약 G-3"}})
schemas["ErrorResponse"] = obj(["errors"], {"errors": {"type": "array", "items": ref("ErrorItem")}})
schemas["ConflictResponse"] = obj(["code", "message"], {
    "code": {"type": "string",
             "enum": ["VERSION_CONFLICT", "DUPLICATE_KEY", "INVALID_STATE",
                      "DUPLICATE_HOLD", "HOLD_QTY_EXCEEDED"],
             "description": ("DUPLICATE_HOLD 는 해제되지 않은 전량 보류가 이미 있다는 뜻이다. "
                             "HOLD_QTY_EXCEEDED 는 부분 보류 합계가 보유 수량을 넘는다는 뜻이다. "
                             "둘 다 서버가 판정한다 — 화면이 계산하지 않는다. 근거: W-03-03 §5-5 · 공유계약 A-9 ⓑ")},
    "message": STR,
    "conflictingLotId": {"type": "integer", "format": "int64",
                         "description": "여러 LOT 을 한 번에 보류할 때 어느 LOT 이 걸렸는지. 근거: W-03-03 §6"},
    "currentVersion": {"type": "string", "description": "VERSION_CONFLICT 일 때 서버의 현재 version_no"}})
schemas["PageMeta"] = obj(["page", "size", "total"], {
    "page": {"type": "integer", "example": 1},
    "size": {"type": "integer", "example": 50},
    "total": {"type": "integer", "example": 412}})
schemas["QueuedResponse"] = obj(["idempotencyKey"], {
    "idempotencyKey": {"type": "string", "format": "uuid"},
    "message": {"type": "string", "example": "연결되면 전송됩니다"}},
    description="202 로 받는 몸통. 아직 리소스가 없으므로 식별자를 내려주지 않고 멱등키를 돌려준다. 근거: 공유계약 C-7")

schemas["LotVersionRef"] = obj(["lotId", "versionNo"], {
    "lotId": I64,
    "versionNo": {"type": "integer", "description": "trace.lot 의 낙관적 잠금 토큰"}},
    description=("⭐ 헤더 If-Match 로 표현할 수 없는 잠금이다 — 여러 LOT 을 한 트랜잭션으로 보류하므로 "
                 "토큰이 여럿이고 하나라도 어긋나면 전체를 거부한다. 근거: W-03-03 §5-1 · 3단계 §4-2"))

# ══════════════════════════════════════════════════════════════════
# 검사 3계층 — 결정 01
# ══════════════════════════════════════════════════════════════════
schemas["InspectionRequest"] = obj(
    ["inspectionRequestId", "inspectionRequestNo", "inspectionTypeCode",
     "inspectionPlanVersionId", "targetTypeCode", "targetId", "itemId",
     "targetQty", "uomId", "statusCode", "requestedAt"], {
    "inspectionRequestId": I64,
    "inspectionRequestNo": {"type": "string", "example": "IR-2026-0812-0412"},
    "inspectionTypeCode": {"type": "string",
                           "description": "IQC · PQC · OQC. ⭐ 결정 09 의 「원천 축」을 유도하는 유일한 근거다. 근거: W-03-05 §5-2"},
    "inspectionPlanVersionId": I64,
    "targetTypeCode": {"type": "string", "description": "다형 참조의 유형. 근거: 공유계약 A-10"},
    "targetId": I64,
    "itemId": I64, "lotId": I64, "workOrderId": I64, "productionResultId": I64,
    "targetQty": QTY, "uomId": I64,
    # ⛔ 전역 TS 를 그대로 쓰고 나중에 description 을 넣으면 공유 객체가 오염된다 —
    #    date-time 프로퍼티 전부에 같은 설명이 붙는다. 인라인으로 편다.
    "coverageFromAt": {**TS, "description": (
        "이 검사 결과가 대표하는 생산 구간의 시작. 표본 검사라 불합격 시 회수 범위를 정하는 데 쓴다. "
        "확정에 없는 개념인데 모델이 갖고 있다. 근거: P-02-13 §5-5")},
    "coverageToAt": {**TS, "description": "그 구간의 끝. 검사 시작·종료 시각으로 채우되 작업자가 조정할 수 있다"},
    "statusCode": STR, "requestedAt": {**TS, "description": "검사 의뢰가 만들어진 시각"},
    "versionNo": INT},
    description=("검사 의뢰. ⛔ 등록 경로를 두지 않는다 — 화면 7장에 「의뢰 등록」 버튼이 0건이고 "
                 "P-02-13 §4-A 가 「대개 자동 생성」이라 한다. 서버가 입고·생산 실적에서 만든다."))

schemas["InspectionMeasurement"] = obj(
    ["inspectionMeasurementId", "inspectionItemSpecId", "sampleNo", "judgmentCode", "measuredAt"], {
    "inspectionMeasurementId": I64,
    "inspectionItemSpecId": I64,
    "sampleNo": INT,
    "numericValue": {"type": "number", "format": "double"},
    "textValue": STR,
    "booleanValue": BOOL,
    "judgmentCode": STR,
    "measuredAt": TS,
    "inspectionEquipmentId": I64,
    "calibrationExpiredAtMeasurement": {"type": "boolean",
        "description": ("⭐ 서버가 판정한 값이다 — 측정 시점에 이 장비의 교정이 만료였는가. "
                        "화면이 계산하지 않는다(공유계약 L-2). 근거: W-03-05 §5-6")}},
    description=("측정치 — 3계층의 3층. ⛔ version_no 가 없다(기록 전용) — 잠금은 검사 결과로 대표한다. "
                 "⛔ 값 세 칸 중 하나만 채운다(ck_measurement_single_value 는 ≤1 이라 "
                 "전부 NULL 도 통과하며 그때는 「미측정」이다)."))
schemas["InspectionMeasurementInput"] = obj(
    ["inspectionItemSpecId", "sampleNo", "judgmentCode", "measuredAt"], {
    "inspectionItemSpecId": I64, "sampleNo": INT,
    "numericValue": {"type": "number", "format": "double"},
    "textValue": STR, "booleanValue": BOOL,
    "judgmentCode": STR, "measuredAt": TS, "inspectionEquipmentId": I64},
    description="측정치는 자체 쓰기 경로가 없다 — 검사 결과 저장에 함께 실린다. 근거: 03 계약 1단계 §6")

schemas["InspectionResult"] = obj(
    ["inspectionResultId", "inspectionResultNo", "inspectionRequestId", "inspectionRound",
     "inspectedQty", "acceptedQty", "rejectedQty", "heldQty", "uomId",
     "overallJudgmentCode", "inspectorId", "inspectedAt", "statusCode"], {
    "inspectionResultId": I64,
    "inspectionResultNo": {"type": "string", "example": "IRS-2026-0812-0412-1"},
    "inspectionRequestId": I64,
    "inspectionRequestNo": {"type": "string", "example": "IR-2026-0812-0412",
        "description": "목록 한 행을 그리는 데 필요해 함께 내린다 — 화면이 의뢰를 따로 부르지 않는다"},
    "inspectionTypeCode": {"type": "string", "description": "의뢰에서 따온 읽기 전용"},
    "itemId": I64, "lotId": I64,
    "inspectionRound": {"type": "integer",
                        "description": "UNIQUE(의뢰, 회차). 재검은 정정이 아니라 새 회차다. 근거: 공유계약 B-10"},
    "inspectedQty": QTY, "acceptedQty": QTY, "rejectedQty": QTY, "heldQty": QTY, "uomId": I64,
    "overallJudgmentCode": {"type": "string",
        "description": ("합격·불합격·보류 3값. ⛔ enum 으로 못박지 않는다 — 값 목록은 공통코드가 갖고 "
                        "늘 수 있다(공유계약 G-2·G-6). 근거: 회신 E-3 종결 2026-08-07")},
    "inspectorId": I64, "inspectedAt": TS,
    "confirmedAt": {"type": "string", "format": "date-time",
        "description": ("확정 시각. ⛔ 확정자 컬럼은 두지 않는다 — 검사자와 확정자를 분리하지 않기로 "
                        "확정됐다(omf-mes#62 · 1차 범위). 근거: W-01-01 §8-3")},
    "terminalId": I64,
    "statusCode": {"type": "string", "description": "작성중 · 확정. 임시 저장은 작성중으로 남는다"},
    "previousResultId": I64,
    "reinspectionReasonCode": STR,
    "remarks": STR,
    "versionNo": INT},
    description=("검사 결과 — 3계층의 2층. ⭐ 라인이 아니라 문서다 — 자체 번호·상태·잠금·자식·멱등키를 갖는다. "
                 "근거: 03 계약 1단계 §5"))
schemas["InspectionResultCreate"] = obj(
    ["inspectionRequestId", "inspectedQty", "acceptedQty", "rejectedQty", "heldQty",
     "uomId", "inspectorId", "inspectedAt", "statusCode"], {
    "inspectionRequestId": I64,
    "inspectedQty": QTY, "acceptedQty": QTY, "rejectedQty": QTY, "heldQty": QTY, "uomId": I64,
    "overallJudgmentCode": {"type": "string", "description": "statusCode=확정 이면 필수다"},
    "inspectorId": I64, "inspectedAt": TS, "terminalId": I64,
    "statusCode": {"type": "string", "enum": ["작성중", "확정"],
        "description": ("⭐ 오프라인 큐는 언제나 확정으로 보낸다 — 임시 저장은 단말에 남고 서버로 오지 않는다. "
                        "근거: 03 계약 3단계 §3-2")},
    "previousResultId": {"type": "integer", "format": "int64",
        "description": "재검이면 앞 회차를 가리킨다. 회차는 서버가 +1 한다. 근거: 공유계약 B-10"},
    "reinspectionReasonCode": STR,
    "measurements": {"type": "array", "items": ref("InspectionMeasurementInput")},
    "remarks": STR},
    description=("⛔ statusCode=확정 이면 acceptedQty + rejectedQty + heldQty = inspectedQty 를 강제한다 "
                 "(ck_inspection_result_qty · 공유계약 A-3). 작성중은 통과시킨다."))
schemas["InspectionResultUpdate"] = obj([], {
    "inspectedQty": QTY, "acceptedQty": QTY, "rejectedQty": QTY, "heldQty": QTY,
    "overallJudgmentCode": STR, "inspectorId": I64, "inspectedAt": TS,
    "measurements": {"type": "array", "items": ref("InspectionMeasurementInput")},
    "remarks": STR},
    description="작성중인 결과만 고칠 수 있다. 확정된 것은 409 INVALID_STATE — 고치는 것이 아니라 재검이다(B-10)")
schemas["InspectionResultConfirm"] = obj([], {
    "overallJudgmentCode": {"type": "string", "description": "비우면 저장된 값을 쓴다"},
    "remarks": STR},
    description="작성중 → 확정. ⭐ 이 순간 Lot Status 가 전이한다 — 독립 경로를 두지 않는다(결정 10 · B-8)")

schemas["InspectionSummary"] = obj(
    ["inspectionCount", "inspectedQty", "acceptedQty", "rejectedQty", "defectRate"], {
    "inspectionCount": {"type": "integer", "example": 412},
    "inspectedQty": QTY, "acceptedQty": QTY, "rejectedQty": QTY, "heldQty": QTY,
    "defectRate": {"type": "number", "format": "double", "example": 1.78,
        "description": ("백분율. ⭐ 분모는 검사 수량이다 — 생산 수량이 아니다. "
                        "W-02-08 의 수율(생산 수량 기준 · 손실 분리)과 다른 수가 나오는 것이 정상이다. "
                        "근거: W-03-05 §5-4 · 확정 QA #13")},
    "calibrationExpiredCount": {"type": "integer",
        "description": ("교정 만료 장비로 측정된 건수. ⛔ 집계에서 자동으로 빼지 않는다 — "
                        "무효화 정책이 미정이다(WF03 예외 E-9 ①). 근거: W-03-05 §5-6 · 공유계약 L-8")},
    "finalRoundOnly": {"type": "boolean",
        "description": ("검사 건수·수량은 최종 회차만 센다. 재검 합격분은 합격으로 세지만 "
                        "1회차 불량 실적은 그대로 남아 두 수가 다르다. 근거: W-03-05 §5-3 · 결정 09 ①")}},
    description="L-1 — 요약은 필터 전체 기준이고 목록은 페이지다. 파생은 서버가 계산한다(L-2)")
schemas["DefectRatePoint"] = obj(["bucket", "inspectedQty", "rejectedQty", "defectRate"], {
    "bucket": {"type": "string", "example": "2026-08-11", "description": "일자"},
    "inspectedQty": QTY, "rejectedQty": QTY,
    "defectRate": {"type": "number", "format": "double", "example": 1.78}},
    description="불량률 추이. ⛔ 관리도 통계(Xbar-R · Cp/Cpk)는 없다 — Analytics 이연(결정 11)")
schemas["DefectRateTrend"] = obj(["points"], {
    "points": {"type": "array", "items": ref("DefectRatePoint")}})

# ══════════════════════════════════════════════════════════════════
# 불량 실적 — 나. 부여·회수 형
# ══════════════════════════════════════════════════════════════════
schemas["DefectRecord"] = obj(
    ["defectRecordId", "workOrderId", "defectCodeId", "defectQty", "uomId",
     "occurrenceProcessId", "detectionProcessId", "detectedAt"], {
    "defectRecordId": I64,
    "productionResultId": I64, "inspectionResultId": I64,
    "workOrderId": {"type": "integer", "format": "int64",
        "description": ("⛔ NOT NULL 이다. 그래서 W/O 없는 클레임 불량(고객 지급품·외주 가공품)이 "
                        "들어오지 못한다 — 계약이 우회하지 않는다. 근거: W-03-05 §5-2 · 확정 QA #15")},
    "lotId": I64,
    "defectCodeId": I64,
    "suspectedCauseCodeId": I64, "confirmedCauseCodeId": I64,
    "responsibilityTypeCode": STR, "responsibleDepartmentId": I64, "workerId": I64,
    "defectDescription": STR,
    "defectQty": QTY, "uomId": I64,
    "occurrenceProcessId": I64, "detectionProcessId": I64,
    "equipmentId": I64, "moldId": I64,
    "occurredAt": TS, "detectedAt": TS,
    "sourceAxisCode": {"type": "string",
        "description": ("서버가 유도한 원천 축 — 현장 / PQC / OQC / 원천미상. "
                        "⛔ 결정 09 의 5축 중 「수리」와 「클레임」은 나오지 않는다(omf-mes#83 · workOrderId NOT NULL). "
                        "근거: W-03-05 §5-2")}},
    description=("불량 실적. ⛔ 등록 경로를 두지 않는다 — 03 화면 7장에 불량코드 입력이 0건이다. "
                 "만드는 화면은 M-02-02(#83 로 막힘) · P-04-03(04 계약 없음)이다. "
                 "근거: 03 계약 2단계 §6"))
schemas["DefectDistributionNode"] = obj(
    ["defectCodeId", "label", "recordCount", "defectQty"], {
    "defectCodeId": I64,
    "parentDefectCodeId": I64,
    "label": {"type": "string", "example": "스크래치"},
    "recordCount": {"type": "integer", "example": 142},
    "defectQty": QTY,
    "share": {"type": "number", "format": "double", "example": 52.6, "description": "백분율"},
    "duplicateRisk": {"type": "boolean",
        "description": ("⚠ 공정별로 나눌 때 같은 현상이 공정 수만큼 복제 등록됐을 수 있다는 표식이다. "
                        "결정 12 의 공정—불량코드 N:M 이 물리 모델에 착지하지 않아 defect_code.process_id 가 "
                        "아직 N:1 이다. 화면이 경고를 상시 보인다. 근거: W-03-05 §5-5")}})
schemas["DefectDistribution"] = obj(["nodes", "groupBy"], {
    "nodes": {"type": "array", "items": ref("DefectDistributionNode")},
    "groupBy": {"type": "string",
        "description": "occurrenceProcess 로 묶어야 개선 대상이 나온다. 근거: W-03-05 §5-5"}})

# ══════════════════════════════════════════════════════════════════
# 보류 — 사. 구간 형 (02 가 만든 패턴이 처음 남의 테이블에 선다)
# ══════════════════════════════════════════════════════════════════
schemas["LotHold"] = obj(
    ["lotHoldId", "lotId", "reasonCode", "statusCode", "heldAt"], {
    "lotHoldId": I64, "lotId": I64,
    "lotNo": STR, "itemId": I64,
    "holdQty": {"type": "number", "format": "double",
        "description": ("⛔ 비면 전량 보류다 — 지금 수량뿐 아니라 이후 입고분까지 막힌다. "
                        "uomId 와 짝이다(ck_lot_hold_qty_uom). 근거: W-03-03 §5-2 · 공유계약 A-2")},
    "uomId": I64,
    "reasonCode": STR,
    "releaseCondition": {"type": "string",
        "description": ("무엇을 확인하면 풀리는지. DB 는 nullable 이지만 보류로 갈 때는 계약이 필수로 막는다 — "
                        "비면 아무도 조건을 몰라 영구히 안 풀린다. 근거: W-03-03 §5-4 · 공유계약 A-9 ⓑ")},
    "statusCode": {"type": "string",
        "description": ("⚠ 보류 「건」의 진행 상태다 — LOT 의 품질 판정(lot.status_code)과 다른 축이다. "
                        "근거: W-03-01 §5-3")},
    "heldBy": I64, "heldAt": TS,
    "releasedBy": I64,
    "releasedAt": {"type": "string", "format": "date-time",
        "description": "⭐ 구간 형 — 비어 있으면 「진행 중」이다. 상태 컬럼으로 판정하지 않는다(공유계약 G-16)"},
    "lotStatusCode": {"type": "string", "description": "이 보류가 걸었을 때 LOT 이 간 상태"},
    "remarks": STR},
    description=("LOT 보류. ⚠ trace.lot_hold 는 01 소유 테이블이고 01 계약은 읽기만 갖는다 — "
                 "쓰기는 품질 도메인 소관이다. 물류 축의 조회는 GET /trace/lots/{lotId}/holds 다. "
                 "근거: 01 요구서 §7 · 03 계약 2단계 §4"))
schemas["LotHoldCreate"] = obj(["lots", "reasonCode", "targetLotStatusCode"], {
    "lots": {"type": "array", "items": ref("LotVersionRef"),
        "description": "⚠ 2건 이상이면 전량 보류만 된다 — 수량은 LOT 마다 달라 뜻을 잃는다. 근거: W-03-03 §5-3"},
    "holdQty": QTY, "uomId": I64,
    "reasonCode": STR,
    "releaseCondition": {"type": "string",
        "description": "targetLotStatusCode 가 보류이면 필수, 불량(Hold)이면 받지 않는다. 근거: 03 계약 2단계 §5-2"},
    "targetLotStatusCode": {"type": "string",
        "description": ("⭐ 도착 상태. 의심자재 등록(C10)은 보류, 클레임·리콜 재Hold(C9)는 불량이다. "
                        "두 화면이 같은 행을 만들고 도착 상태만 다르다. 근거: 03 계약 2단계 §5")},
    "remarks": STR},
    description=("⛔ 헤더 If-Match 를 쓰지 않는다 — 여러 LOT 을 한 트랜잭션으로 걸어 토큰이 여럿이다. "
                 "lots[].versionNo 로 싣고 하나라도 어긋나면 전체를 거부한다. 근거: 3단계 §4-2"))
schemas["LotHoldRelease"] = obj(["targetLotStatusCode", "remarks"], {
    "targetLotStatusCode": {"type": "string",
        "description": "재판정 합격이면 정상, 재판정 불합격이면 불량이다(C7 · C8). 근거: W-03-02 §5-1"},
    "releaseQty": {"type": "number", "format": "double",
        "description": ("부분 해제. 원 행을 해제하고 남은 수량으로 새 보류 행을 만든다 — "
                        "hold_qty 를 줄이지 않는다(공유계약 B-3). 근거: W-03-02 §5-7")},
    "remarks": {"type": "string",
        "description": ("⛔ 해제 사유를 담을 코드 컬럼이 lot_hold 에 없다 — 등록에는 reason_code 가 있는데 "
                        "해제에는 없다. 자유 텍스트로 물러나므로 「재판정으로 풀린 건」을 셀 수 없다. "
                        "「기록하라는데 자리가 없다」 7번째(omf-mes#87). 근거: W-03-02 §5-4")}})

schemas["LotQualityStatus"] = obj(
    ["lotId", "lotNo", "itemId", "lotStatusCode", "fullyHeld"], {
    "lotId": I64, "lotNo": STR, "itemId": I64, "lotTypeCode": STR,
    "lotStatusCode": {"type": "string",
        "description": "품질 판정 축 — 정상·불량·검사 대기·폐기. ⚠ 보류 건의 진행 상태와 다른 축이다(W-03-01 §5-3)"},
    "warehouseId": I64, "locationId": I64,
    "onHandQty": QTY,
    "heldQty": {"type": "number", "format": "double",
        "description": "미해제 보류 합계. ⭐ 서버가 lot_hold 에서 파생한다 — 화면이 더하지 않는다(공유계약 L-2)"},
    "availableQty": {"type": "number", "format": "double",
        "description": "⛔ inventory_balance 를 정본으로 쓰지 않는다 — lot_hold 가 정본이고 잔액은 파생이다(W-03-03 §5-6)"},
    "uomId": I64,
    "openHoldCount": INT,
    "fullyHeld": {"type": "boolean",
        "description": ("⭐ 해제되지 않은 전량 보류(hold_qty IS NULL)가 있는가. "
                        "있으면 더 걸 수 없어 목록에서 선택 불가로 표시한다. 근거: W-03-03 §5-5 · §5-8")},
    "latestTransitionAt": {"type": "string", "format": "date-time",
        "description": ("「최근 전이」 열. ⛔ 변경이력 테이블이 없어 lot_hold 의 최대 시각으로 낸다 — "
                        "합격·불합격·재판정 전이는 여기 나타나지 않는다(W-03-01 §5-1)")},
    "latestReasonCode": STR},
    description=("품질 축의 LOT 목록. ⚠ 01 계약의 GET /trace/lots 는 물류 축이라 창고 필터·보류 요약·"
                 "최근 전이를 갖지 않는다 — 세 화면(W-03-01·02·03)이 공통으로 요구해 03 이 낸다. "
                 "근거: 03 계약 2단계 §4-1"))
schemas["LotStatusCount"] = obj(["statusCode", "lotCount"], {
    "statusCode": {"type": "string", "example": "정상"},
    "lotCount": {"type": "integer", "example": 1204},
    "lotTypeCode": {"type": "string",
        "description": "⚠ 자재·생산·제품을 합치지 않는다 — 같은 보류라도 대응이 다르다. 근거: 공유계약 L-7"}})
schemas["LotStatusSummary"] = obj(["counts", "asOf"], {
    "counts": {"type": "array", "items": ref("LotStatusCount")},
    "asOf": TS,
    "outOfScopeCount": {"type": "integer",
        "description": ("권한 범위(user_data_scope) 밖이라 목록에 안 나온 건수. "
                        "⚠ 「없다」와 구분되지 않는 문제를 화면이 문구로 푼다. 근거: W-03-01 §6 · §8-6")}},
    description="LOT 상태 4값(정상·불량·검사 대기·폐기) 집계. 근거: 회신 E-3 종결 2026-08-07")
schemas["LotStatusTransition"] = obj(["targetLotStatusCode", "allowed"], {
    "targetLotStatusCode": STR,
    "allowed": BOOL,
    "blockedReason": {"type": "string",
        "description": "갈 수 없으면 화면이 그대로 보일 문장을 담는다. 근거: 공유계약 G-3"}})
schemas["LotStatusTransitionSet"] = obj(["lotId", "currentLotStatusCode", "transitions"], {
    "lotId": I64,
    "currentLotStatusCode": STR,
    "transitions": {"type": "array", "items": ref("LotStatusTransition")},
    "note": {"type": "string",
        "description": ("갈 수 있는 곳이 없을 때 화면이 보일 문장. 불량(Hold)은 발신 전이가 0이라 "
                        "빈 드롭다운 대신 안내를 보인다. 근거: W-03-02 §5-5")}},
    description=("⭐ 전이 규칙을 화면이 갖지 않는다 — 서버가 판정한다(공유계약 G-8). "
                 "저장하지 않으므로 :동사 가 아니라 GET 이다(02 가 :validate 를 GET …/validation 으로 바꾼 것과 같다)"))

# ══════════════════════════════════════════════════════════════════
# 특채 — 라. 업무 문서 형
# ══════════════════════════════════════════════════════════════════
schemas["Concession"] = obj(
    ["concessionId", "concessionNo", "nonconformanceId", "lotId",
     "approvedQty", "consumedQty", "uomId", "validFrom", "approvalRequestId", "statusCode"], {
    "concessionId": I64,
    "concessionNo": {"type": "string", "example": "CN-2026-0812-0101"},
    "nonconformanceId": I64,
    "nonconformanceNo": {"type": "string",
        "description": ("⚠ 번호만 내려준다 — 부적합 상세는 04 제품출하 계약(W-04-07) 소관이라 "
                        "지금은 열 경로가 없다. 근거: 03 계약 1단계 §8-2")},
    "lotId": I64, "lotNo": STR,
    "approvedQty": QTY,
    "consumedQty": {"type": "number", "format": "double",
        "description": "읽기 전용 — 출고·투입이 올린다. 03 은 조건만 읽는다. ck_concession_consumed 가 approved 를 넘지 못하게 막는다"},
    "uomId": I64,
    "validFrom": DT, "validTo": DT,
    "allowedWorkOrderId": I64, "allowedProcessId": I64, "allowedCustomerId": I64,
    "unrestrictedAxes": {"type": "array", "items": STR,
        "description": ("⭐ 비어 있는 허용 축의 이름을 서버가 짚어 내려준다 — 「비었다」가 「제한 없음」이므로 "
                        "화면이 빈칸으로 두면 의도보다 넓게 승인된다. 근거: W-03-09 §5-3")},
    "approvalRequestId": I64,
    "statusCode": STR,
    "usable": {"type": "boolean",
        "description": ("⭐ 서버가 파생한 3항 논리곱 — 상태가 유효하고 valid_to 가 지나지 않았고 "
                        "approvedQty − consumedQty > 0 인가. 화면이 세 조건을 계산하지 않는다(공유계약 L-2). "
                        "근거: 03 계약 1단계 §2-3")},
    "remarks": STR, "versionNo": INT},
    description=("특채 — 단순 판정이 아니라 사용 범위 통제 데이터다. "
                 "⛔ 생성 경로를 두지 않는다(요청을 만드는 화면이 미정 · W-03-09 §8-4). "
                 "⛔ 승인·반려는 app-공통 계약이다. ⛔ 조건 수정을 두지 않는다 — 결재는 예/아니오다(공유계약 J-10)"))

# ══════════════════════════════════════════════════════════════════
# 경로
# ══════════════════════════════════════════════════════════════════
CAL = q("calibrationExpired", {"type": "string", "enum": ["only", "exclude"]},
        "교정 만료 장비 측정분만 보거나 뺀다. ⛔ 기본은 섞어서 낸다 — 자동 제외는 정책이 미정이다(E-9 ①)")

paths["/quality/inspection-requests"] = {"get": {
    "tags": ["quality"], "summary": "검사 의뢰 목록",
    "description": "W-01-01 검사 대기 큐 · W-03-05 검사 목록의 1층. 근거: W-01-01 §3 · W-03-05 §5-1",
    "parameters": [
        q("inspectionTypeCode", STR, "IQC · PQC · OQC"),
        q("statusCode", STR), q("itemId", I64), q("lotId", I64), q("workOrderId", I64),
        q("requestedFrom", TS, "기간 필수 — 공유계약 L-3"),
        q("requestedTo", TS),
        q("q", STR, "의뢰번호 검색")] + PAGE,
    "responses": listed("InspectionRequest")}}
paths["/quality/inspection-requests/{inspectionRequestId}"] = {"get": {
    "tags": ["quality"], "summary": "검사 의뢰 한 건",
    "description": "P-02-13 진입 시 기준 버전·대상 수량을 읽는다. 근거: P-02-13 §4-A",
    "parameters": [pathparam("inspectionRequestId")],
    "responses": dict(list(one("InspectionRequest").items()) + list(err("404").items())),
    "x-internal-note": ("등록 경로를 두지 않았다 — 화면 7장에 「의뢰 등록」 버튼이 0건이다. "
                        "서버가 입고(01)·생산 실적(02)에서 만든다. 검사 기준 버전이 NOT NULL 이라 "
                        "기준이 없으면 의뢰 자체가 생기지 않고 화면은 진입할 수 없다(P-02-13 §5-2 · omf-mes#64 묶음 A).")}}

paths["/quality/inspection-results"] = {
    "get": {"tags": ["quality"], "summary": "검사 결과 목록",
        "description": "재검 사슬을 previousResultId 로 잇는다 — 숨기지 않고 들여쓰기로 보인다. 근거: W-03-05 §5-3",
        "parameters": [
            q("inspectionRequestId", I64), q("inspectionTypeCode", STR),
            q("overallJudgmentCode", STR), q("statusCode", STR), q("itemId", I64),
            q("inspectedFrom", TS, "기간 필수 — 공유계약 L-3"), q("inspectedTo", TS),
            q("finalRoundOnly", BOOL, "최종 회차만. 집계와 같은 기준으로 보려면 켠다"),
            CAL] + PAGE,
        "responses": listed("InspectionResult")},
    "post": {"tags": ["quality"], "summary": "검사 결과 저장",
        "description": ("임시 저장(statusCode=작성중)과 즉시 확정(=확정)을 한 경로로 받는다. "
                        "⭐ 오프라인 큐는 언제나 확정으로 온다 — 임시 저장은 단말에 남는다. "
                        "재검이면 previousResultId 를 실으면 서버가 회차를 +1 한다. " + OFFLINE +
                        " 근거: W-01-01 §5-2 · P-02-13 §5-9 · 03 계약 3단계 §3-2"),
        "parameters": [pref("IdempotencyKey"), pref("IfMatchVersionOptional")],
        "requestBody": {"required": True, "content": {"application/json": {
            "schema": ref("InspectionResultCreate")}}},
        "responses": dict(list(one("InspectionResult", "201", "저장됨").items())
                          + list(QUEUED.items()) + list(err("400", "403", "409").items())),
        "x-internal-note": ("확정 경로가 둘이다 — 이 경로에 statusCode=확정 으로 보내는 것과 "
                            ":confirm 을 부르는 것. 부수 효과가 같아야 한다(Lot Status 전이 · confirmed_at 기록). "
                            "멱등키가 둘을 잇는다 — 같은 키면 어느 쪽으로 와도 한 건이다. "
                            "idempotency_key 는 테이블 컬럼으로 실재하며 전역 UNIQUE 라 business_date 경계 문제가 없다"
                            "(SQL 1856 · 공유계약 C-8).")}}
paths["/quality/inspection-results/{inspectionResultId}"] = {
    "get": {"tags": ["quality"], "summary": "검사 결과 한 건",
        "description": "근거: W-03-05 §3 드로어",
        "parameters": [pathparam("inspectionResultId")],
        "responses": dict(list(one("InspectionResult").items()) + list(err("404").items()))},
    "put": {"tags": ["quality"], "summary": "검사 결과 수정",
        "description": ("작성중인 것만 고친다. 확정된 것은 409 INVALID_STATE — 고치는 것이 아니라 재검이다. "
                        "근거: 공유계약 B-10 · W-01-01 §5-3"),
        "parameters": [pathparam("inspectionResultId"), pref("IdempotencyKey"), pref("IfMatchVersion")],
        "requestBody": {"required": True, "content": {"application/json": {
            "schema": ref("InspectionResultUpdate")}}},
        "responses": dict(list(one("InspectionResult", "200", "수정됨").items())
                          + list(err("400", "403", "404", "409").items()))}}
paths["/quality/inspection-results/{inspectionResultId}:confirm"] = {"post": {
    "tags": ["quality"], "summary": "검사 판정 확정",
    "description": ("작성중 → 확정. ⭐ 이 순간 Lot Status 가 전이한다 — 합격이면 정상, 불합격이면 불량, "
                    "보류면 검사 대기다. 독립된 상태 전이 경로를 두지 않는다(결정 10 「상태 이중 보유 없음」 · 공유계약 B-8). "
                    "⛔ accepted + rejected + held = inspected 가 아니면 400 이다(A-3). "
                    "근거: W-01-01 §5-2 · P-02-13 §5-3"),
    "parameters": [pathparam("inspectionResultId"), pref("IdempotencyKey"), pref("IfMatchVersion")],
    "requestBody": {"required": True, "content": {"application/json": {
        "schema": ref("InspectionResultConfirm")}}},
    "responses": dict(list(one("InspectionResult", "200", "확정됨").items())
                      + list(err("400", "403", "404", "409").items())),
    "x-internal-note": ("관리웹·온라인 전용이다 — 오프라인 큐는 서버가 만든 inspectionResultId 를 모르므로 "
                        "이 경로를 부를 수 없다. 큐는 POST /quality/inspection-results 에 statusCode=확정 으로 보낸다"
                        "(03 계약 3단계 §3).")}}
paths["/quality/inspection-results/{inspectionResultId}/measurements"] = {"get": {
    "tags": ["quality"], "summary": "측정치 목록",
    "description": ("3계층의 3층. ⭐ 검사 목록에 join 하지 않는다 — 의뢰 412 · 결과 450 에 견줘 "
                    "측정치는 135,000 자릿수라 표가 터진다. 「한 화면」이지 「한 표」가 아니다. "
                    "근거: W-03-05 §5-1 · 공유계약 L-1"),
    "parameters": [pathparam("inspectionResultId"),
                   q("inspectionItemSpecId", I64), CAL] + PAGE,
    "responses": listed("InspectionMeasurement")}}
paths["/quality/inspection-results/summary"] = {"get": {
    "tags": ["quality"], "summary": "검사 요약",
    "description": ("요약 카드 5종 — 필터 전체 기준이다(공유계약 L-1). 파생은 서버가 계산한다(L-2). "
                    "근거: W-03-05 §3"),
    "parameters": [
        q("inspectionTypeCode", STR, "⚠ IQC·PQC·OQC 를 합치지 않는다 — 자재 불량률과 제품 불량률을 더하면 뜻이 없다(L-7)"),
        q("itemId", I64), q("processId", I64), q("overallJudgmentCode", STR),
        q("inspectedFrom", TS, "필수 — 공유계약 L-3"), q("inspectedTo", TS), CAL],
    "responses": one("InspectionSummary", "200", "요약")}}
paths["/quality/inspection-results/defect-rate-trend"] = {"get": {
    "tags": ["quality"], "summary": "불량률 추이",
    "description": ("일자 × 불량률. ⛔ 관리도 통계는 없다 — 1차 범위는 수집과 상하한 판정까지다(결정 11). "
                    "근거: W-03-05 §5-8"),
    "parameters": [q("inspectionTypeCode", STR), q("itemId", I64),
                   q("inspectedFrom", TS, "필수"), q("inspectedTo", TS), CAL],
    "responses": one("DefectRateTrend", "200", "추이")}}

paths["/quality/defect-records"] = {"get": {
    "tags": ["quality"], "summary": "불량 실적 목록",
    "description": "근거: W-03-05 §4-D",
    "parameters": [
        q("workOrderId", I64), q("lotId", I64), q("defectCodeId", I64),
        q("occurrenceProcessId", I64), q("detectionProcessId", I64),
        q("sourceAxisCode", STR, "현장 · PQC · OQC · 원천미상"),
        q("detectedFrom", TS, "기간 필수 — 공유계약 L-3"), q("detectedTo", TS)] + PAGE,
    "responses": listed("DefectRecord"),
    "x-internal-note": ("등록 경로를 두지 않았다 — 03 화면 7장에 불량코드 입력이 0건이다. "
                        "만드는 화면은 M-02-02(omf-mes#83 로 막힘)와 P-04-03(04 계약 미착수)이다. "
                        "⛔ 04 트랙이 POST 를 더할 때 새 경로를 만들지 말고 이 경로에 얹는다 — "
                        "접두어는 공유해도 경로는 한 계약에만 둔다(03 계약 2단계 §3).")}}
paths["/quality/defect-records/distribution"] = {"get": {
    "tags": ["quality"], "summary": "불량코드 분포",
    "description": ("2계층 분포. ⚠ 공정별로 나누면 중복 계상될 수 있어 duplicateRisk 를 함께 내린다 — "
                    "분포를 보고 개선 대상을 정하는 화면이라 왜곡이 곧 잘못된 판단이 된다. "
                    "근거: W-03-05 §5-5"),
    "parameters": [
        q("groupBy", {"type": "string", "enum": ["defectCode", "occurrenceProcess", "detectionProcess"]},
          "발생 공정으로 묶어야 개선 대상이 나온다"),
        q("sourceAxisCode", STR), q("itemId", I64),
        q("detectedFrom", TS, "필수"), q("detectedTo", TS)],
    "responses": one("DefectDistribution", "200", "분포")}}

paths["/quality/lot-holds"] = {
    "get": {"tags": ["quality"], "summary": "LOT 보류 목록",
        "description": ("⭐ 구간 형 — 기본 조회는 열린 것이다(open=true). 상태 코드로 묻지 않는다(공유계약 G-16). "
                        "W-03-01 「이력으로 찾기」와 W-03-02 대상 목록이 함께 쓴다. 근거: W-03-01 §3 · W-03-02 §3"),
        "parameters": [
            q("open", BOOL, "기본 true — 해제되지 않은 것만"),
            q("lotId", I64), q("itemId", I64), q("reasonCode", STR),
            q("heldBy", I64, "행위자 — W-03-01 요건 ①"),
            q("heldFrom", TS, "기간 — W-03-01 이력 모드에서 필수(공유계약 L-3)"),
            q("heldTo", TS)] + PAGE,
        "responses": listed("LotHold"),
        "x-internal-note": ("⛔ Lot Status 변경이력 테이블이 없다 — trace 7테이블에 previous_status 류가 0건이다. "
                            "그래서 이 목록이 낼 수 있는 것은 보류 등록·해제뿐이고, 전이 9건 중 5건이 사라지고 "
                            "2건은 반쪽이다. 화면이 결과 표 머리에 그 사실을 적는다(공유계약 A-11). "
                            "전용 테이블이냐 audit_event 규약이냐의 선후는 omf-mes#64·#68 에 코멘트로 나가 있고 "
                            "전용 테이블을 권고했다(W-03-01 §5-2).")},
    "post": {"tags": ["quality"], "summary": "LOT 보류 등록",
        "description": ("의심자재 등록(C10 · 도착 보류)과 클레임·리콜 재Hold(C9 · 도착 불량)를 한 경로로 받는다 — "
                        "같은 행을 만들고 도착 상태만 다르다. "
                        "⭐ lot_hold INSERT 와 lot.status_code UPDATE 는 한 트랜잭션이다(공유계약 B-8) — "
                        "하나만 되면 재고가 안 막히거나 막힌 이유가 없다. "
                        "⛔ inventory_balance.blocked_qty 는 쓰지 않는다 — 잔액은 서버가 파생한다(L-2). "
                        "근거: W-03-03 §5-1 · W-03-02 §5-6 · 03 계약 2단계 §5"),
        "parameters": [pref("IdempotencyKey")],
        "requestBody": {"required": True, "content": {"application/json": {
            "schema": ref("LotHoldCreate")}}},
        "responses": dict(list({"201": {"description": "등록됨",
            "content": {"application/json": {"schema": {"type": "array", "items": ref("LotHold")}}}}}.items())
            + list(err("400", "403", "404", "409").items())),
        "x-internal-note": ("헤더 If-Match 를 쓰지 않는 유일한 쓰기다 — 여러 LOT 을 한 트랜잭션으로 걸어 "
                            "토큰이 여럿이라 헤더로 표현할 수 없다. lots[].versionNo 로 싣는다(03 계약 3단계 §4-2). "
                            "409 는 둘이다 — DUPLICATE_HOLD(해제되지 않은 전량 보류가 이미 있다) · "
                            "HOLD_QTY_EXCEEDED(부분 보류 합계가 보유를 넘는다). lot_hold 에 UNIQUE 제약이 없어 "
                            "서버가 판정한다(W-03-03 §5-5).")}}
paths["/quality/lot-holds/{lotHoldId}"] = {"get": {
    "tags": ["quality"], "summary": "LOT 보류 한 건",
    "description": "근거: W-03-01 §3 드로어",
    "parameters": [pathparam("lotHoldId")],
    "responses": dict(list(one("LotHold").items()) + list(err("404").items()))}}
paths["/quality/lot-holds/{lotHoldId}:release"] = {"post": {
    "tags": ["quality"], "summary": "LOT 보류 해제·재판정",
    "description": ("재판정 합격(C7 · 도착 정상)과 재판정 불합격(C8 · 도착 불량)을 도착 상태로 가른다. "
                    "⛔ PUT releasedAt 이 아니다 — 구간을 닫는 것은 액션이다(공유계약 G-16). "
                    "⭐ 이 전이가 출고·출하·피킹의 가부를 바꾼다 — 화면이 확정 전에 무엇이 풀리고 막히는지 보인다"
                    "(결정 10 「차단 판정 단일 지점」 · W-03-02 §5-3). "
                    "근거: W-03-02 §5-1 · §5-8"),
    "parameters": [pathparam("lotHoldId"), pref("IdempotencyKey"), pref("IfMatchVersion")],
    "requestBody": {"required": True, "content": {"application/json": {
        "schema": ref("LotHoldRelease")}}},
    "responses": dict(list(one("LotHold", "200", "해제됨").items())
                      + list(err("400", "403", "404", "409").items())),
    "x-internal-note": ("If-Match 는 lot_hold 가 아니라 trace.lot 의 version_no 다 — lot_hold 에는 "
                        "version_no 가 없다(기록 전용). B-8 로 한 트랜잭션이라 lot 의 토큰이 이 오퍼레이션의 토큰이다. "
                        "⛔ 부분 해제는 hold_qty 를 줄이지 않는다 — 원 행을 해제하고 남은 수량으로 새 행을 만든다"
                        "(공유계약 B-3 · W-03-02 §5-7).")}}

paths["/quality/lot-statuses"] = {"get": {
    "tags": ["quality"], "summary": "LOT 품질 상태 목록",
    "description": ("W-03-01 「LOT 으로 찾기」 · W-03-02 대상 목록 · W-03-03 대상 목록이 함께 쓴다. "
                    "보류 요약·최근 전이·전량 보류 여부를 서버가 파생해 한 행에 담는다(공유계약 L-2). "
                    "⚠ 자재·생산·제품을 합쳐 보이지 않는다 — lotTypeCode 로 가른다(L-7). "
                    "근거: W-03-01 §3 · W-03-02 §3 · W-03-03 §3"),
    "parameters": [
        q("lotStatusCode", STR, "정상 · 불량 · 검사 대기 · 폐기"),
        q("lotTypeCode", STR), q("itemId", I64),
        q("warehouseId", I64, "⭐ 01 계약의 /trace/lots 에는 없는 축이다"),
        q("locationId", I64),
        q("heldOnly", BOOL, "미해제 보류가 있는 것만"),
        q("excludeFullyHeld", BOOL, "이미 전량 보류인 것을 뺀다 — W-03-03 대상 선택용"),
        q("q", STR, "LOT 번호 검색")] + PAGE,
    "responses": listed("LotQualityStatus"),
    "x-internal-note": ("01 계약의 GET /trace/lots 와 겹치지 않는다 — 그쪽은 물류 축(LOT 자체의 속성)이고 "
                        "이쪽은 품질 축(판정 상태 + 보류 요약)이다. 창고 필터·보류 수량·최근 전이·전량 보류 여부는 "
                        "01 스키마에 없어 세 화면을 그릴 수 없었다. 같은 경로를 두지 않는다는 규칙은 지킨다"
                        "(03 계약 2단계 §3).")}}
paths["/quality/lot-status-summary"] = {"get": {
    "tags": ["quality"], "summary": "LOT 상태 요약",
    "description": ("LOT 상태 4값 집계 — 요약은 필터 전체 기준이다(공유계약 L-1). "
                    "⚠ 판정 불가를 0 으로 내리지 않는다(L-8). 근거: W-03-01 §3 · §5-4"),
    "parameters": [q("lotTypeCode", STR, "⚠ 자재·생산·제품을 합치지 않는다(L-7)"),
                   q("itemId", I64), q("warehouseId", I64), q("plantId", I64)],
    "responses": one("LotStatusSummary", "200", "요약"),
    "x-internal-note": ("품질 축의 조회는 03 이 낸다 — 물류 축은 01 의 GET /trace/lots 다. "
                        "같은 테이블을 두 축에서 본다(03 계약 2단계 §4-1).")}}
paths["/quality/lot-status-transitions"] = {"get": {
    "tags": ["quality"], "summary": "갈 수 있는 LOT 상태",
    "description": ("현재 상태에서 갈 수 있는 곳을 서버가 판정해 내린다 — 화면이 전이 표를 갖지 않는다"
                    "(공유계약 G-8). 규칙이 바뀌어도 화면 3벌을 고치지 않는다. "
                    "⛔ 저장하지 않으므로 :동사 가 아니다. 근거: W-03-02 §5-5"),
    "parameters": [{"name": "lotId", "in": "query", "required": True, "schema": I64}],
    "responses": dict(list(one("LotStatusTransitionSet", "200", "선택지").items())
                      + list(err("404").items()))}}

paths["/quality/concessions"] = {"get": {
    "tags": ["quality"], "summary": "특채 목록",
    "description": ("W-03-09 가 approvalRequestId 로 조건을 찾는다 — 목록 자체는 승인 계약이 낸다"
                    "(GET /app/approval-requests). 근거: W-03-09 §3 · §4-B"),
    "parameters": [q("approvalRequestId", I64), q("lotId", I64), q("nonconformanceId", I64),
                   q("statusCode", STR),
                   q("usableOnly", BOOL, "⭐ 지금 쓸 수 있는 것만 — 상태·유효기간·잔여의 3항 논리곱을 서버가 판정한다"),
                   q("validOn", DT, "이 날짜에 유효한 것")] + PAGE,
    "responses": listed("Concession")}}
paths["/quality/concessions/{concessionId}"] = {"get": {
    "tags": ["quality"], "summary": "특채 한 건",
    "description": "승인 화면의 「조건」 구획. 근거: W-03-09 §3 ②",
    "parameters": [pathparam("concessionId")],
    "responses": dict(list(one("Concession").items()) + list(err("404").items())),
    "x-internal-note": ("승인·반려는 app-공통 계약이다(POST /app/approval-requests/{id}:approve · :reject). "
                        "⛔ 조건 수정 경로를 두지 않는다 — 결재는 예/아니오이고 값을 바꾸면 무엇을 승인했는지가 "
                        "흐려진다(공유계약 J-10 · W-03-09 §5-4). 반려 사유로 돌려보낸다. "
                        "⛔ 생성 경로도 없다 — 특채 요청을 만드는 화면이 아직 특정되지 않았다(W-03-09 §8-4). "
                        "nonconformance_id 가 NOT NULL 이라 부적합(04 계약)이 선행한다.")}}


# ══════════════════════════════════════════════════════════════════
# example 자동 부여 — 검사기가 스칼라마다 요구한다
# ══════════════════════════════════════════════════════════════════
EX = {
    "Id": 1001, "id": 1001,
    "No": "IR-2026-0812-0412", "Code": "IQC", "code": "IQC",
    "Qty": 30.0, "qty": 30.0, "At": "2026-08-12T10:22:00+09:00",
    "Date": "2026-08-12", "Note": "비고", "note": "비고",
}


def example_for(name, sch):
    t = sch.get("type"); f = sch.get("format")
    if "enum" in sch: return sch["enum"][0]
    if "example" in sch: return sch["example"]
    if f == "uuid": return "6f1a0c2e-8b4d-4a1e-9c33-0b7c2f5d1a90"
    if f == "date-time": return "2026-08-12T10:22:00+09:00"
    if f == "date": return "2026-08-12"
    if t == "integer": return 1001 if name.endswith("Id") else 1
    if t == "number": return 30.0
    if t == "boolean": return True
    if t == "string":
        for k, v in EX.items():
            if name.endswith(k): return v
        if name.endswith("No"): return "IR-2026-0812-0412"
        return "값"
    return None


def fill(sch):
    for pname, p in (sch.get("properties") or {}).items():
        if not isinstance(p, dict): continue
        if "$ref" in p or p.get("type") in ("array", "object"): continue
        if "example" not in p:
            e = example_for(pname, p)
            if e is not None: p["example"] = e


for _s in schemas.values():
    fill(_s)

# ⛔ 공유 스칼라가 오염되지 않았는지 본다.
#
# I64·TS 같은 전역 dict 는 수십 개 프로퍼티가 **같은 객체를 참조**한다. 어딘가에서
# schemas[...]["properties"][...]["description"] = ... 처럼 나중에 넣으면 그 하나가
# 전부에 붙는다. 실제로 그렇게 새서 date-time 필드 12개에 엉뚱한 설명이 붙었다(PR #141).
#
# 검사기는 description 의 「존재」를 보지 「내용」을 보지 않아 이것을 못 잡는다.
# 여기서 막는다 — 설명을 붙이려면 {**TS, "description": …} 로 인라인 사본을 만든다.
_ALLOWED = {"type", "format", "example"}
for _name, _proto in (("I64", I64), ("QTY", QTY), ("TS", TS), ("DT", DT),
                      ("STR", STR), ("INT", INT), ("BOOL", BOOL)):
    _extra = set(_proto) - _ALLOWED
    if _extra:
        raise SystemExit(
            f"⛔ 공유 스칼라 {_name} 이 오염됐습니다 — 추가된 키 {sorted(_extra)}.\n"
            f"   전역 dict 를 변형하면 그 타입의 모든 프로퍼티에 같은 값이 붙습니다.\n"
            f"   설명을 붙이려면 {{**{_name}, \"description\": …}} 로 인라인 사본을 만드세요.")

OUT = os.path.join(HERE, "quality-03품질.json")
src = json.load(io.open(os.path.join(HERE, "logistics-01자재창고.json"), encoding="utf-8"))
doc = {
    "openapi": "3.1.0",
    "info": {
        "title": "omf-mes 03 품질 도메인 API (초안)",
        "version": "0.1.0",
        "description": (
            "03 품질 도메인 API 계약. 검사 실행 3계층(의뢰-결과-측정치)과 불량 실적 집계, LOT 보류, 특채 조건을 덮는다. "
            "검사 기준·불량코드·원인코드 마스터는 기준정보 계약이 소유하므로 여기서는 참조만 한다 — "
            "/quality 접두어를 두 계약이 나눠 쓰되 같은 경로는 두지 않는다. "
            "LOT 보류는 자재창고 계약이 읽기만 갖고 쓰기를 이 계약에 넘긴 것이다 — "
            "물류 축은 GET /trace/lots/{lotId}/holds 이고 품질 축이 /quality/lot-holds 다. "
            "보류는 구간 형 리소스다 — 「진행 중」을 상태 컬럼으로 두지 않고 끝 시각의 부재로 판정하며 "
            "닫는 것은 :release 액션이다. "
            "Lot Status 전이에 독립 경로를 두지 않는다 — 검사 판정 확정과 보류 등록·해제의 부수 효과로만 일어난다. "
            "승인·반려는 공통 계약이 소유한다. 부적합과 처분 판정은 제품출하 계약 소관이다. "
            "현장 검사 화면 한 장이 오프라인에서 쓰이므로 검사 결과 저장은 Idempotency-Key 를 필수로 받고 "
            "If-Match 를 선택으로 둔다. 즉시 처리는 201, 큐 접수는 202 다."),
        "x-internal-note": (
            "설계·도출 근거는 uiux/2026-08-12-API스펙-03품질/ 의 00~03 단계 문서다. "
            "대상 화면 7 — 03 도메인 5 에 01 이 미룬 W-01-01(01 요구서 §6-1)과 02 가 뺀 P-02-13 을 더한 것이다. "
            "리소스 6(quality 5 + trace.lot_hold 쓰기) · 액션 근거 53건(화면 액션 표 45 + W-01-01 본문 도출 8). "
            "미해소 상류를 계약이 드러낸다 — Lot Status 변경이력 테이블 부재(omf-mes#64·#68 · 전이 9건 중 5건 소실), "
            "lot_hold 해제 사유 코드 부재(omf-mes#87 7번째), "
            "defect_record.work_order_id NOT NULL 로 클레임 불량 불가, "
            "수리 실행 기록 테이블 부재(omf-mes#83), "
            "결정 12 의 공정—불량코드 N:M 미착지로 공정별 분포 중복 계상. "
            "교정 만료 장비 결과의 무효화 정책은 WF03 예외 E-9 ① 회신 대기라 표시와 분리 조회만 낸다.")
    },
    "servers": [{"url": "/api", "description": "온프레미스 설치형"}],
    "tags": [{"name": "quality", "description": "품질 실행 — 검사 3계층 · 불량 실적 · LOT 보류 · 특채"}],
    "paths": dict(sorted(paths.items())),
    "components": {"parameters": dict(src["components"]["parameters"]),
                   "schemas": dict(sorted(schemas.items()))}
}
io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
ops = sum(1 for p in doc["paths"].values() for m in p if m in ("get", "post", "put", "patch", "delete"))
acts = sum(1 for p in doc["paths"] if ":" in p.rsplit("/", 1)[-1])
print(f"경로 {len(doc['paths'])} · 오퍼레이션 {ops} · 스키마 {len(doc['components']['schemas'])} "
      f"· :동사 경로 {acts} · {os.path.getsize(OUT)/1024:.0f}KB")
