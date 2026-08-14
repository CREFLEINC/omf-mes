#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 02 생산실행 OpenAPI 생성기 — production-02생산실행.json 을 만든다.
#
#   python3 deliverables/openapi/build-02-openapi.py
#
# 계약은 손으로 고치지 않고 이 파일을 고쳐 다시 만든다.
# 규약은 01·06 계약을 계승한다 — 복수 명사 · :동사 는 상태 전이에만 ·
# 수정은 PUT(⛔ PATCH 를 쓰지 않는다 — 앞의 세 계약이 PUT 36 · PATCH 0) ·
# 쓰기에는 Idempotency-Key 필수 · 오프라인 경로는 If-Match 선택.
# 표준 라이브러리만 쓴다(저장소 관행).
import json, io, os, re

I64 = {"type": "integer", "format": "int64"}
QTY = {"type": "number", "format": "double"}
TS  = {"type": "string", "format": "date-time"}
DT  = {"type": "string", "format": "date"}
STR = {"type": "string"}

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
    return {code: {"description": desc, "content": {"application/json": {"schema": ref(schema_name)}}}}

def q(name, schema, desc=None):
    d = {"name": name, "in": "query", "schema": schema}
    if desc: d["description"] = desc
    return d

def pathparam(name):
    return {"name": name, "in": "path", "required": True, "schema": I64}

PAGE = [q("page", {"type": "integer", "default": 1}), q("size", {"type": "integer", "default": 50})]

def action(tag, summary, desc, body=None, resp=None, idem=True, note=None, codes=("400","403","404","409")):
    op = {"tags": [tag], "summary": summary, "description": desc, "parameters": []}
    if idem: op["parameters"].append(pref("IdempotencyKey"))
    if body: op["requestBody"] = {"required": True, "content": {"application/json": {"schema": ref(body)}}}
    op["responses"] = dict(resp or {}); op["responses"].update(err(*codes))
    if note: op["x-internal-note"] = note
    return op

schemas, paths = {}, {}

# ── 공통
schemas["ErrorItem"] = obj(["scope","code","message"], {
    "scope": {"type":"string","enum":["field","screen"],"description":"오류의 범위. 근거: 공유계약 G-1","example":"field"},
    "field": {"type":"string","description":"scope=field 일 때 대상 프로퍼티명","example":"inputQty"},
    "code": {"type":"string","example":"QTY_MUST_BE_POSITIVE"},
    "message": {"type":"string","description":"화면이 그대로 보여도 되는 문장. 「어떻게 풀 것인가」를 담는다. 근거: 공유계약 G-3"}})
schemas["ErrorResponse"] = obj(["errors"], {"errors": {"type":"array","items": ref("ErrorItem")}})
schemas["ConflictResponse"] = obj(["code","message"], {
    "code": {"type":"string","enum":["VERSION_CONFLICT","DUPLICATE_KEY","OPEN_SESSION_EXISTS","BATCH_DEPENDENCY_FAILED","INVALID_STATE"],
             "description":"OPEN_SESSION_EXISTS 는 열린 구간이 이미 있다는 뜻이다. BATCH_DEPENDENCY_FAILED 는 선행 요청이 아직 없다는 뜻이며 큐가 묶음을 멈춰야 한다. 근거: 공유계약 C-2 · C-10"},
    "message": STR,
    "failedAt": {"type":"string","description":"BATCH_DEPENDENCY_FAILED 일 때 멈춘 지점의 멱등키"},
    "currentVersion": {"type":"string","description":"VERSION_CONFLICT 일 때 서버의 현재 version_no"}})
schemas["PageMeta"] = obj(["page","size","total"], {"page":{"type":"integer","example":1},"size":{"type":"integer","example":50},"total":{"type":"integer","example":137}})

# ⛔ 오프라인 큐를 202 로 표현하지 않는다 (2026-08-12 정정).
#
#   C-7 은 「저장 피드백 두 등급」이고 화면 조항이다 — Toast 성공 ↔ Chip(warning) 미확정.
#   HTTP 코드를 정한 적이 없다. 202 는 이 생성기가 덧붙인 해석이었다.
#
#   ⛔ 오프라인이면 HTTP 요청 자체가 일어나지 않는다 — C-1 이 「클라이언트가 생성해
#      outbox 에 담는다」이므로 서버는 그 요청을 본 적이 없다. 서버가 응답으로
#      「큐에 담겼다 — 아직 서버가 모른다」를 말하는 것은 자기모순이다.
#
#   ⚠ 근거로 삼았던 「01 도 202 를 쓴다(202:6)」도 틀렸다 — 그 여섯은 전부
#      결재 상신·ERP 재동기라 진짜 서버 비동기다. 응답 코드만 세고 뜻을 안 봤다.
#
#   ⭐ 미확정 표식은 셸의 outbox 가 할 일이라 클라이언트 문서 소관이다.
#      서버 계약은 온라인일 때 서버가 실제로 내는 것만 적는다.
#
#   ⛔ 빈 dict 로 남겨 두지 않았다 — 한 줄만 되돌리면 12건이 한꺼번에 되살아난다.

# ══════════ planning ══════════
schemas["ProductionOrder"] = obj(
    ["productionOrderId","productionOrderNo","itemId","orderQty","uomId","statusCode"], {
    "productionOrderId": I64, "productionOrderNo": STR,
    "erpOrderNo": {"type":"string","description":"ERP 수신 원번호"},
    "parentProductionOrderId": I64, "bomLevel": {"type":"integer"},
    "businessUnitId": I64, "plantId": I64, "itemId": I64,
    "orderQty": QTY, "uomId": I64, "dueDate": DT,
    "statusCode": STR, "remarks": STR, "versionNo": {"type":"integer"}})
schemas["ProductionOrderAcknowledge"] = obj(["decisionCode"], {
    "decisionCode": {"type":"string","enum":["APPLY","PROCEED"],"description":"반영 / 강행. 근거: W-02-06 §5"},
    "reason": {"type":"string","description":"강행이면 사유가 필요하다"}})

paths["/planning/production-orders"] = {"get": {"tags":["planning"],"summary":"P/O 목록",
    "description":"근거: W-02-01 §3","parameters":[
        q("statusCode",STR), q("plantId",I64), q("itemId",I64),
        q("dueDateFrom",DT,"납기 시작"), q("dueDateTo",DT,"납기 종료"),
        q("q",STR,"P/O 번호 검색"), q("includeChildren",{"type":"boolean","default":False},"하위 레벨 함께. 계층 펼침용")]+PAGE,
    "responses": listed("ProductionOrder")}}
paths["/planning/production-orders/{productionOrderId}"] = {"get":{"tags":["planning"],"summary":"P/O 한 건",
    "description":"근거: W-02-01 §3","parameters":[pathparam("productionOrderId")],
    "responses": dict(list(one("ProductionOrder").items())+list(err("404").items()))}}
paths["/planning/production-orders/{productionOrderId}:acknowledge"] = {"post": action(
    "planning","P/O 변경 확인 처리","관리자가 ERP 변경을 반영할지 강행할지 판정한다. 근거: W-02-06 §5-5 · :동사 규약",
    body="ProductionOrderAcknowledge", resp=one("ProductionOrder","200","처리됨"))}
paths["/planning/production-orders/{productionOrderId}:resync"] = {"post": action(
    "planning","ERP 재동기 요청","수신본이 어긋났을 때 다시 받는다. 근거: W-02-01 §5",
    resp={"202":{"description":"재동기를 접수했다. 결과는 연계 수신으로 온다"}}, codes=("403","404"))}
for p in ["/planning/production-orders/{productionOrderId}:acknowledge","/planning/production-orders/{productionOrderId}:resync"]:
    paths[p]["post"]["parameters"].insert(0, pathparam("productionOrderId"))

schemas["ProductionPlan"] = obj(
    ["productionPlanId","productionOrderId","planNo","planDate","plannedQty","uomId","bomId","routingId","statusCode"], {
    "productionPlanId": I64, "productionOrderId": I64, "planNo": STR,
    "planDate": DT, "plannedQty": QTY, "uomId": I64,
    "bomId": I64, "routingId": I64,
    "plannedLineId": I64, "statusCode": STR,
    "confirmedAt": TS, "confirmedBy": I64, "remarks": STR, "versionNo": {"type":"integer"}},
    description="BOM·Routing 은 06 기준정보 계약이 소유한다 — 여기서는 참조만 한다. 근거: 02 계약 2단계 §1-2")
schemas["ProductionPlanCreate"] = obj(["productionOrderId","planDate","plannedQty","uomId","bomId","routingId"], {
    "productionOrderId": I64, "planDate": DT, "plannedQty": QTY, "uomId": I64,
    "bomId": I64, "routingId": I64, "plannedLineId": I64,
    "splitOfPlanId": {"$ref":"#/components/schemas/ProductionPlanSplitRef"},
    "remarks": STR})
schemas["ProductionPlanSplitRef"] = obj([], {"sourcePlanId": I64,
    "reasonCode": {"type":"string","description":"러닝체인지 분할 사유"}},
    description="러닝체인지로 계획을 나눌 때 원본을 가리킨다. 근거: W-02-02 §5")
schemas["ProductionPlanUpdate"] = obj([], {"planDate": DT, "plannedQty": QTY,
    "bomId": I64, "routingId": I64, "plannedLineId": I64, "remarks": STR})

paths["/planning/production-plans"] = {
 "get": {"tags":["planning"],"summary":"생산 계획 목록","description":"근거: W-02-02 §3",
   "parameters":[q("productionOrderId",I64), q("statusCode",STR),
                 q("planDateFrom",DT), q("planDateTo",DT)]+PAGE,
   "responses": listed("ProductionPlan")},
 "post": {"tags":["planning"],"summary":"생산 계획 추가","description":"근거: W-02-02 §5",
   "parameters":[pref("IdempotencyKey")],
   "requestBody":{"required":True,"content":{"application/json":{"schema": ref("ProductionPlanCreate")}}},
   "responses": dict(list(one("ProductionPlan","201","생성됨").items())+list(err("400","403","409").items()))}}
paths["/planning/production-plans/{productionPlanId}"] = {
 "get": {"tags":["planning"],"summary":"생산 계획 한 건","description":"근거: W-02-02 §3",
   "parameters":[pathparam("productionPlanId")],
   "responses": dict(list(one("ProductionPlan").items())+list(err("404").items()))},
 "put": {"tags":["planning"],"summary":"생산 계획 수정","description":"확정 전에만 고칠 수 있다. 근거: W-02-02 §5",
   "parameters":[pathparam("productionPlanId"), pref("IdempotencyKey"), pref("IfMatchVersion")],
   "requestBody":{"required":True,"content":{"application/json":{"schema": ref("ProductionPlanUpdate")}}},
   "responses": dict(list(one("ProductionPlan","200","수정됨").items())+list(err("400","403","404","409").items()))},
 "delete": {"tags":["planning"],"summary":"생산 계획 삭제","description":"확정 전 계획만 지운다. 확정 뒤에는 W/O 가 매달려 있어 지우지 않는다. 근거: W-02-02 §5 · 공유계약 B-4",
   "parameters":[pathparam("productionPlanId"), pref("IfMatchVersion")],
   "responses": dict([("204",{"description":"삭제됨"})]+list(err("403","404","409").items()))}}
paths["/planning/production-plans/{productionPlanId}:confirm"] = {"post": action(
    "planning","전개 확정","계획을 확정해 W/O 전개를 연다. 근거: W-02-02 §5 · :동사 규약",
    resp=one("ProductionPlan","200","확정됨"))}
paths["/planning/production-plans/{productionPlanId}:confirm"]["post"]["parameters"].insert(0, pathparam("productionPlanId"))

OFFLINE = ("오프라인 대상 오퍼레이션이다 — Idempotency-Key 는 필수이고 If-Match 는 선택이다. "
           "큐는 낙관적 잠금 토큰을 싣지 않는다(공유계약 C-9). "
           "⛔ 오프라인일 때는 이 오퍼레이션이 호출되지 않는다 — 셸의 outbox 가 들고 있다가 "
           "연결되면 그때 보낸다. 그래서 서버 응답은 온라인일 때의 것 하나뿐이다. "
           "미확정 표식은 셸이 붙인다(공유계약 C-7 — 화면 조항).")

# ══════════ production — work_order ══════════
schemas["WorkOrder"] = obj(
    ["workOrderId","workOrderNo","productionPlanId","routingOperationId","itemId","orderQty","uomId","workOrderTypeCode","statusCode","priorityNo"], {
    "workOrderId": I64, "workOrderNo": STR, "productionPlanId": I64,
    "routingOperationId": I64, "itemId": I64, "orderQty": QTY, "uomId": I64,
    "workOrderTypeCode": {"type":"string","description":"NORMAL 기본. 긴급·재작업이 값으로 붙는다"},
    "parentWorkOrderId": I64,
    "reworkSourceWorkOrderId": I64, "reworkSourceLotId": I64, "reworkSourceNonconformanceId": I64,
    "productionLineId": I64, "responsibleWorkerId": I64,
    "plannedStartAt": TS, "plannedEndAt": TS,
    "plannedEquipmentId": I64, "plannedMoldId": I64, "plannedShiftId": I64,
    "priorityNo": {"type":"integer","default":100},
    "defaultWipLocationId": I64, "defaultFgLocationId": I64, "defaultScrapLocationId": I64,
    "operationSettingsSnapshot": {"type":"object","description":"확정 시점의 공정 설정을 굳혀 둔 것. 근거: 공유계약 A-18"},
    "statusCode": {"type":"string","description":"편성 → 확정 → 배포 → 진행 → 완료 → 마감. 중단↕재개 반복. 취소가 값으로 붙는다. 근거: ✓설계확정 결정 14 · 예외 E-4 ④"},
    "releasedAt": TS, "completedAt": TS,
    "completionVarianceReasonCode": STR, "closedAt": TS,
    "remarks": STR, "versionNo": {"type":"integer"}})
schemas["WorkOrderCreate"] = obj(["productionPlanId","routingOperationId","itemId","orderQty","uomId"], {
    "productionPlanId": I64, "routingOperationId": I64, "itemId": I64,
    "orderQty": QTY, "uomId": I64,
    "workOrderTypeCode": STR, "priorityNo": {"type":"integer"},
    "plannedStartAt": TS, "plannedEndAt": TS, "remarks": STR})
schemas["WorkOrderUpdate"] = obj([], {
    "orderQty": QTY, "priorityNo": {"type":"integer"},
    "plannedStartAt": TS, "plannedEndAt": TS,
    "plannedEquipmentId": I64, "plannedMoldId": I64, "plannedShiftId": I64,
    "productionLineId": I64, "responsibleWorkerId": I64,
    "defaultWipLocationId": I64, "defaultFgLocationId": I64, "defaultScrapLocationId": I64,
    "remarks": STR}, description="4M 자원배정이 이 경로로 들어온다. 근거: W-02-03 §5")
schemas["WorkOrderRelease"] = obj([], {
    "lotSlotCount": {"type":"integer","description":"선발행할 생산LOT 슬롯 수. 비우면 계획값 N. 근거: R26·R27"},
    "handoverNote": {"type":"string","description":"전달사항. 공지 확인 이력이 별도로 받는다 — 근거: DR-005"}})
schemas["WorkOrderClose"] = obj(["remainderDispositionCode"], {
    "remainderDispositionCode": {"type":"string","enum":["CARRY_OVER","WRITE_OFF"],"description":"잔량 처분 — 이월 / 소멸. 근거: W-02-05 §5"},
    "reasonCode": STR,
    "erpSendItems": {"type":"array","items":STR,"description":"송신 항목 토글 결과"}})
schemas["WorkOrderCancel"] = obj(["reasonCode"], {"reasonCode": STR, "note": STR},
    description="취소하면 선발행된 생산LOT 슬롯이 자동 폐번된다 — 화면이 저장 전에 그 파급을 말한다. 근거: DR-007 · 공유계약 G-19")
schemas["WorkOrderHold"] = obj(["reasonCode","occurredAt"], {"reasonCode": STR, "occurredAt": TS, "note": STR},
    description="POP 에서 누른다 — occurredAt 은 단말 시계가 정한다. 근거: 공유계약 C-12")
schemas["WorkOrderResume"] = obj(["occurredAt"], {"occurredAt": TS, "note": STR},
    description="재시작은 상태가 아니라 중단→진행 전이 이벤트다 — 그래서 발생 시각을 받는다. 근거: ✓설계확정 결정 14 · 공유계약 C-12")
schemas["ValidationFinding"] = obj(["severity","code","message"], {
    "severity": {"type":"string","enum":["BLOCK","WARN"],
                 "description":"BLOCK 은 고쳐야 넘어간다. WARN 은 화면의 「경고 확인」 체크로 넘어갈 수 있다. 근거: W-02-03 §5"},
    "field": {"type":"string","description":"대상 프로퍼티명"},
    "code": STR, "message": STR},
    description="오류가 아니라 점검 결과다 — ErrorItem 을 재사용하지 않는다. 등급 축(BLOCK/WARN)이 필요하기 때문이다.")
schemas["ValidationReport"] = obj(["passed","findings"], {
    "passed": {"type":"boolean","description":"BLOCK 이 하나도 없으면 true"},
    "findings": {"type":"array","items": ref("ValidationFinding")}})

WO = "/production/work-orders"
paths[WO] = {
 "get": {"tags":["production"],"summary":"W/O 목록·진행현황","description":"집계 열(실적 누계)을 함께 내려준다. 근거: W-02-08 §3·§5",
   "parameters":[q("productionPlanId",I64), q("statusCode",STR), q("productionLineId",I64),
                 q("workOrderTypeCode",STR), q("plannedStartFrom",TS), q("plannedStartTo",TS),
                 q("q",STR,"W/O 번호 검색"),
                 q("sort",{"type":"string","default":"priorityNo,asc"},"정렬 키는 제한한다. 근거: 공유계약 L-4"),
                 q("withProgress",{"type":"boolean","default":True},"실적 누계를 함께 받는다")]+PAGE,
   "responses": listed("WorkOrder")},
 "post": {"tags":["production"],"summary":"W/O 발행","description":"전개로 만들거나 긴급으로 직접 만든다. 근거: W-02-02 §5 · W-02-07 §5",
   "parameters":[pref("IdempotencyKey")],
   "requestBody":{"required":True,"content":{"application/json":{"schema": ref("WorkOrderCreate")}}},
   "responses": dict(list(one("WorkOrder","201","생성됨").items())+list(err("400","403","409","501").items())),
   "x-internal-note":"긴급 W/O(workOrderTypeCode=EMERGENCY)는 productionPlanId 없이 서야 하는데 물리 모델이 NOT NULL 체인으로 막고 있다 — omf-mes#76. 미해소 동안 501 을 답한다. 근거: W-02-07 · 02 계약 2단계 §6-1"}}
paths[WO+"/{workOrderId}"] = {
 "get": {"tags":["production"],"summary":"W/O 한 건","description":"근거: W-02-08 §3",
   "parameters":[pathparam("workOrderId")],
   "responses": dict(list(one("WorkOrder").items())+list(err("404").items()))},
 "put": {"tags":["production"],"summary":"W/O 수정 · 4M 자원배정","description":"배포 전에만 고친다. 근거: W-02-03 §5 · W-02-04 §5",
   "parameters":[pathparam("workOrderId"), pref("IdempotencyKey"), pref("IfMatchVersion")],
   "requestBody":{"required":True,"content":{"application/json":{"schema": ref("WorkOrderUpdate")}}},
   "responses": dict(list(one("WorkOrder","200","수정됨").items())+list(err("400","403","404","409").items()))}}

WO_ACTIONS = [
 (":validate","유효성 재점검","4M 배정이 서로 부딪히는지 본다. 저장하지 않는다. 근거: W-02-03 §5",None,one("ValidationReport","200","점검 결과"),False,None),
 (":release","확정·배포 · 생산LOT 선발행","확정과 배포와 선발행이 한 트랜잭션이다. 선발행은 번호 슬롯 예약이며 완료 전에는 실물에 귀속되지 않는다. 근거: W-02-04 §5 · R26·R27","WorkOrderRelease",one("WorkOrder","200","배포됨"),True,None),
 (":hold","작업 중단","W/O 를 중단 상태로 옮긴다. 세션은 :end 로 따로 닫는다 — 중단 상태를 갖는 것은 W/O 다. POP 에서 누르므로 오프라인 대상이다. 근거: ✓설계확정 결정 14 · P-02-10 §5-4","WorkOrderHold",dict(list(one("WorkOrder","200","중단됨").items())),True,None),
 (":resume","작업 재개","중단→진행 전이 이벤트다. 재시작은 상태가 아니다. POP 에서 누르므로 오프라인 대상이다. 근거: ✓설계확정 결정 14 · P-02-01 §5","WorkOrderResume",dict(list(one("WorkOrder","200","재개됨").items())),True,None),
 (":close","마감 · ERP 실적 송신","잔량 처분을 함께 정한다. 미달 슬롯은 이 시점에 자동 폐번된다. ERP 실제 전송만 트랜잭션 밖이다. 근거: W-02-05 §5 · R27·R82","WorkOrderClose",one("WorkOrder","200","마감됨"),True,None),
 (":cancel","W/O 취소","취소 상태로 옮기고 선발행된 생산LOT 슬롯을 자동 폐번한다. 마감 시 미달 슬롯을 폐번하는 것과 같은 규칙이다. 근거: 예외 E-4 ④(2026-08-12 종결) · R27·R82 · W-02-06 §5-5","WorkOrderCancel",one("WorkOrder","200","취소됨"),True,
  "DR-007(2026-08-12 확정)로 부수 효과가 정해졌다 — R27 과 같게 즉시 폐번. 선발행은 번호 슬롯 예약이고 완료 전에는 실물에 귀속되지 않으므로(R26) 폐번해도 현장에 라벨이 남지 않는다. 신설 0 — trace.lot.status_code 의 「폐번」 값을 그대로 쓴다."),
]
OFFLINE_WO = (":hold", ":resume")   # POP 에서 누르는 액션 — 큐로 온다
for suffix, summary, desc, body, resp, idem, note in WO_ACTIONS:
    op = action("production", summary, desc, body=body, resp=resp, idem=idem, note=note)
    if suffix in OFFLINE_WO:
        op["parameters"].append(pref("IfMatchVersionOptional"))
        op["description"] += " " + OFFLINE
    op["parameters"].insert(0, pathparam("workOrderId"))
    paths[WO+"/{workOrderId}"+suffix] = {"post": op}


# ══════════ work_session — 구간 형 ══════════
schemas["WorkSession"] = obj(["workSessionId","workOrderId","sessionNo","shiftId","terminalId","startedAt","statusCode"], {
    "workSessionId": I64, "workOrderId": I64,
    "sessionNo": {"type":"integer","description":"중단·재개마다 는다. uq(workOrderId, sessionNo). 근거: P-02-01 §5-4"},
    "shiftId": I64, "equipmentId": I64, "moldId": I64, "terminalId": I64,
    "startedAt": TS,
    "endedAt": {**TS, "description":"비어 있으면 진행 중이다 — 상태 컬럼을 두지 않는다. 근거: 공유계약 G-16"},
    "statusCode": STR, "stopReasonCode": STR, "remarks": STR, "versionNo": {"type":"integer"}},
    description="구간 형 리소스다. 「진행 중」은 끝 시각의 부재로 판정한다.")
schemas["WorkSessionCreate"] = obj(["workOrderId","shiftId","terminalId","startedAt"], {
    "workOrderId": I64, "shiftId": I64, "equipmentId": I64, "moldId": I64,
    "terminalId": I64,
    "startedAt": {**TS, "description":"단말 시계가 정한다. 서버 수신 시각으로 덮지 않는다. 근거: 공유계약 C-12"},
    "workerIds": {"type":"array","items": I64, "description":"시작 시점 작업자"},
    "controlOverride": ref("ControlOverride")})
schemas["ControlOverride"] = obj(["reasonCode"], {
    "reasonCode": STR, "note": STR},
    description="작업 전 점검 통제를 우회하고 시작할 때 함께 보낸다. 서버가 세션과 work_session_event(통제 우회)를 한 트랜잭션으로 만든다. 별도 액션을 두지 않는 이유는 「우회만 하고 세션을 안 여는」 상태를 없애기 위함이다. 근거: QA #9 · P-02-02 §4 · 공유계약 F-6")
schemas["WorkSessionEnd"] = obj(["endedAt"], {
    "endedAt": {**TS, "description":"단말 시계. 시작보다 앞서면 400 이다"},
    "stopReasonCode": STR})
schemas["WorkSessionWorker"] = obj(["workSessionWorkerId","workerId","workerRoleCode","joinedAt"], {
    "workSessionWorkerId": I64, "workerId": I64,
    "workerRoleCode": {"type":"string","default":"OPERATOR"},
    "joinedAt": TS,
    "leftAt": {**TS, "description":"비어 있으면 아직 참여 중이다"}})
schemas["WorkSessionWorkerJoin"] = obj(["workerId","joinedAt"], {"workerId": I64, "workerRoleCode": STR, "joinedAt": TS})
schemas["WorkSessionWorkerLeave"] = obj(["leftAt"], {"leftAt": TS})
schemas["WorkSessionEvent"] = obj(["workSessionEventId","eventTypeCode","occurredAt"], {
    "workSessionEventId": I64,
    "eventTypeCode": {"type":"string","description":"중단·재개·통제 우회 등. 값 목록은 공통코드가 갖는다. 근거: P-02-10 §8-1 · 공유계약 A-16"},
    "occurredAt": {**TS, "description":"단말 시계가 정한다. 근거: 공유계약 C-12"},
    "recordedAt": {**TS, "description":"서버 수신 시각. 단말 시계와 차이가 커도 거부하지 않고 함께 보인다. 근거: 공유계약 G-20"},
    "reasonCode": STR, "performedBy": I64, "terminalId": I64})
schemas["WorkSessionEventCreate"] = obj(["eventTypeCode","occurredAt"], {
    "eventTypeCode": STR, "occurredAt": TS, "reasonCode": STR,
    "performedBy": I64, "terminalId": I64})

WS = "/production/work-sessions"
paths[WS] = {
 "get": {"tags":["production"],"summary":"작업 세션 목록","description":"기본은 열린 세션이다 — 상태 코드로 거르지 않는다. 근거: 공유계약 G-16 · 02 계약 2단계 §4-3",
   "parameters":[q("open",{"type":"boolean","default":True},"끝 시각이 없는 것만. 기본 true"),
                 q("workOrderId",I64), q("terminalId",I64), q("shiftId",I64),
                 q("startedFrom",TS), q("startedTo",TS)]+PAGE,
   "responses": listed("WorkSession")},
 "post": {"tags":["production"],"summary":"작업 시작 — 세션 열기",
   "description":"단말 게이팅(can_start_work)을 서버가 강제한다. 통제 우회는 controlOverride 로 함께 보낸다. "+OFFLINE+" 근거: P-02-01 §5 · P-02-02 §5 · 공유계약 F-1·F-6",
   "parameters":[pref("IdempotencyKey"), pref("IfMatchVersionOptional")],
   "requestBody":{"required":True,"content":{"application/json":{"schema": ref("WorkSessionCreate")}}},
   "responses": dict(list(one("WorkSession","201","시작됨").items())+list(err("400","403","409").items())),
   "x-internal-note":"409 OPEN_SESSION_EXISTS 는 같은 W/O 에 열린 세션이 이미 있다는 뜻이다. uq_work_session(work_order_id, session_no) 가 물리적으로도 막는다."}}
paths[WS+"/{workSessionId}"] = {"get":{"tags":["production"],"summary":"세션 한 건","description":"근거: P-02-01 §3",
   "parameters":[pathparam("workSessionId")],
   "responses": dict(list(one("WorkSession").items())+list(err("404").items()))}}
_end = action("production","세션 닫기","끝 시각을 찍어 구간을 닫는다. 상태 컬럼을 바꾸는 것이 아니다. "+OFFLINE+" 근거: 공유계약 G-16 · C-16(큐에서 가장 먼저 보낸다)",
              body="WorkSessionEnd", resp=dict(list(one("WorkSession","200","닫힘").items())))
_end["parameters"] = [pathparam("workSessionId"), pref("IdempotencyKey"), pref("IfMatchVersionOptional")]
paths[WS+"/{workSessionId}:end"] = {"post": _end}

paths[WS+"/{workSessionId}/workers"] = {
 "get": {"tags":["production"],"summary":"세션 작업자 목록","description":"근거: P-02-01 §5",
   "parameters":[pathparam("workSessionId"), q("active",{"type":"boolean","default":True},"떠나지 않은 사람만")],
   "responses": {"200":{"description":"목록","content":{"application/json":{"schema":{"type":"array","items": ref("WorkSessionWorker")}}}}}},
 "post": {"tags":["production"],"summary":"작업자 참여","description":"세션을 닫지 않고 사람을 더한다. "+OFFLINE,
   "parameters":[pathparam("workSessionId"), pref("IdempotencyKey"), pref("IfMatchVersionOptional")],
   "requestBody":{"required":True,"content":{"application/json":{"schema": ref("WorkSessionWorkerJoin")}}},
   "responses": dict(list(one("WorkSessionWorker","201","참여됨").items())+list(err("400","403","404").items()))}}
_leave = action("production","작업자 이탈","떠난 시각을 찍는다. 행을 지우지 않는다 — 누가 언제까지 있었는지가 기록이다. "+OFFLINE+" 근거: 공유계약 B-4 의 정신",
                body="WorkSessionWorkerLeave", resp=dict(list(one("WorkSessionWorker","200","이탈 기록됨").items())))
_leave["parameters"] = [pathparam("workSessionId"), pathparam("workSessionWorkerId"), pref("IdempotencyKey")]
paths[WS+"/{workSessionId}/workers/{workSessionWorkerId}:leave"] = {"post": _leave}

paths[WS+"/{workSessionId}/events"] = {
 "get": {"tags":["production"],"summary":"세션 이벤트 목록","description":"근거: P-02-10 §5",
   "parameters":[pathparam("workSessionId"), q("eventTypeCode",STR)],
   "responses": {"200":{"description":"목록","content":{"application/json":{"schema":{"type":"array","items": ref("WorkSessionEvent")}}}}}},
 "post": {"tags":["production"],"summary":"세션 이벤트 적재",
   "description":"중단·재개·통제 우회를 기록한다. occurredAt 은 단말이 보낸다. "+OFFLINE+" ⚠ 세션이 먼저 서야 한다 — 큐에서는 세션 열기와 묶음으로 간다(C-10). 근거: P-02-10 §5-2 · 공유계약 C-12",
   "parameters":[pathparam("workSessionId"), pref("IdempotencyKey"), pref("IfMatchVersionOptional")],
   "requestBody":{"required":True,"content":{"application/json":{"schema": ref("WorkSessionEventCreate")}}},
   "responses": dict(list(one("WorkSessionEvent","201","기록됨").items())+list(err("400","403","404","409").items()))}}

# ══════════ 투입 · 반출 · 손실 · 실적 · 인계 ══════════
schemas["MaterialConsumption"] = obj(
    ["materialConsumptionId","consumptionNo","workOrderId","itemId","lotId","consumptionTypeCode","inputQty","uomId","occurredAt","workerId","terminalId","statusCode"], {
    "materialConsumptionId": I64, "consumptionNo": STR,
    "workOrderId": I64,
    "workSessionId": {**I64, "description":"비어 있을 수 있다 — 세션 없이도 투입이 선다. 근거: P-02-03 §5-5"},
    "shopfloorReceiptLineId": I64,
    "bomComponentId": {**I64, "description":"오투입 판정의 근거. 근거: P-02-03 §5-3"},
    "itemId": I64, "lotId": I64,
    "consumptionTypeCode": {"type":"string","description":"정상·재생재·대체"},
    "correctsConsumptionId": I64, "replacedConsumptionId": I64,
    "changeReasonCode": {"type":"string","description":"러닝체인지 교체 사유. 근거: P-02-11 §5-2"},
    "actualUseProcessId": {**I64, "description":"교차 투입. 근거: P-02-03 §5-3"},
    "inputQty": QTY, "actualConsumedQty": QTY, "uomId": I64,
    "enteredQty": QTY, "enteredUomId": {**I64, "description":"입력 단위가 저장 단위와 다를 수 있다. 근거: P-02-03 §5-6"},
    "occurredAt": TS, "recordedAt": TS, "lateEntryReasonCode": STR,
    "workerId": I64, "terminalId": I64, "statusCode": STR, "remarks": STR})
schemas["MaterialConsumptionCreate"] = obj(["workOrderId","itemId","lotId","consumptionTypeCode","inputQty","uomId","occurredAt","workerId","terminalId"], {
    "workOrderId": I64, "workSessionId": I64, "shopfloorReceiptLineId": I64,
    "bomComponentId": I64, "itemId": I64, "lotId": I64,
    "consumptionTypeCode": STR, "actualUseProcessId": I64,
    "changeReasonCode": STR, "replacedConsumptionId": {**I64,"description":"러닝체인지 — 지우지 않고 잇는다. 근거: P-02-11 §5-2"},
    "inputQty": QTY, "uomId": I64, "enteredQty": QTY, "enteredUomId": I64,
    "occurredAt": TS, "lateEntryReasonCode": STR, "workerId": I64, "terminalId": I64, "remarks": STR})
schemas["MaterialReturn"] = obj(["materialReturnId","materialReturnNo","workOrderId","sourceLocationId","destinationWarehouseId","statusCode","requestedAt"], {
    "materialReturnId": I64, "materialReturnNo": STR, "workOrderId": I64,
    "sourceLocationId": I64, "destinationWarehouseId": I64,
    "statusCode": STR, "requestedAt": TS, "receivedAt": TS,
    "lines": {"type":"array","items": ref("MaterialReturnLine")}})
schemas["MaterialReturnLine"] = obj(["itemId","lotId","returnQty","uomId"], {
    "materialReturnLineId": I64, "itemId": I64, "lotId": I64, "returnQty": QTY, "uomId": I64})
schemas["MaterialReturnCreate"] = obj(["workOrderId","sourceLocationId","destinationWarehouseId","lines"], {
    "workOrderId": I64, "sourceLocationId": I64, "destinationWarehouseId": I64,
    "lines": {"type":"array","minItems":1,"items": ref("MaterialReturnLine")}},
    description="라인은 본문에 싣는다 — 독립 경로를 두지 않는다. 근거: 01 계약 규약 계승")
schemas["ProductionResult"] = obj(
    ["productionResultId","productionResultNo","workOrderId","resultSequence","goodQty","defectQty","holdQty","scrapQty","reworkQty","uomId","resultSourceCode","occurredAt","workerId","shiftId","statusCode"], {
    "productionResultId": I64, "productionResultNo": STR,
    "workOrderId": I64, "workSessionId": I64,
    "resultSequence": {"type":"integer"},
    "correctsProductionResultId": {**I64, "description":"정정은 덧붙인다 — 원본을 고치지 않는다. 근거: 공유계약 G-18"},
    "goodQty": QTY, "defectQty": QTY, "holdQty": QTY, "scrapQty": QTY, "reworkQty": QTY,
    "uomId": I64, "resultSourceCode": STR,
    "occurredAt": TS, "recordedAt": TS, "lateEntryReasonCode": STR,
    "workerId": I64, "equipmentId": I64, "moldId": I64, "shiftId": I64, "terminalId": I64,
    "statusCode": STR, "remarks": STR},
    description="수량은 다섯 컬럼 그대로 내려준다. 정본이 3원(양품/불량/손실)이라는 지적이 열려 있으나(omf-mes#60) 계약이 임의로 접지 않는다.")
schemas["ProductionResultCreate"] = obj(["workOrderId","uomId","resultSourceCode","occurredAt","workerId","shiftId"], {
    "workOrderId": I64, "workSessionId": I64,
    "goodQty": QTY, "defectQty": QTY, "holdQty": QTY, "scrapQty": QTY, "reworkQty": QTY,
    "uomId": I64, "resultSourceCode": STR, "occurredAt": TS, "lateEntryReasonCode": STR,
    "workerId": I64, "equipmentId": I64, "moldId": I64, "shiftId": I64, "terminalId": I64,
    "lotAllocations": {"type":"array","items": ref("ResultLotAllocation"),
                       "description":"실적↔LOT 배분은 본문에 싣는다 — 독립 경로를 두지 않는다"},
    "remarks": STR},
    description="다섯 수량의 합이 0 이면 400 이다 — ck_production_result_qty 가 물리적으로도 막는다.")
schemas["ResultLotAllocation"] = obj(["lotId","allocatedQty"], {"lotId": I64, "allocatedQty": QTY})
schemas["ProductionResultCorrect"] = obj(["reasonCode"], {
    "reasonCode": STR, "note": STR,
    "goodQty": QTY, "defectQty": QTY, "holdQty": QTY, "scrapQty": QTY, "reworkQty": QTY})
schemas["OperationHandover"] = obj(["operationHandoverId","handoverNo","fromWorkOrderId","toWorkOrderId","statusCode","handedOverAt"], {
    "operationHandoverId": I64, "handoverNo": STR,
    "fromWorkOrderId": I64, "toWorkOrderId": I64,
    "statusCode": STR, "handedOverAt": TS,
    "receivedAt": {**TS, "description":"인계 확정과 같은 시각으로 함께 찍는다 — 받는 쪽 화면이 없다. 근거: M-02-01 §5"},
    "lines": {"type":"array","items": ref("OperationHandoverLine")}})
schemas["OperationHandoverLine"] = obj(["lotId","handoverQty","uomId"], {
    "operationHandoverLineId": I64, "lotId": I64, "handoverQty": QTY, "uomId": I64})
schemas["OperationHandoverCreate"] = obj(["fromWorkOrderId","toWorkOrderId","handedOverAt","lines"], {
    "fromWorkOrderId": I64, "toWorkOrderId": I64, "handedOverAt": TS,
    "lines": {"type":"array","minItems":1,"items": ref("OperationHandoverLine")}})

def doc_resource(path, tag, name, schema, create, summary_list, summary_post, desc_list, desc_post,
                 filters, offline=True, note=None):
    ps = [pref("IdempotencyKey")] + ([pref("IfMatchVersionOptional")] if offline else [])
    post = {"tags":[tag],"summary":summary_post,
            "description": desc_post + (" " + OFFLINE if offline else ""),
            "parameters": ps,
            "requestBody":{"required":True,"content":{"application/json":{"schema": ref(create)}}},
            "responses": dict(list(one(schema,"201","기록됨").items())
                              + list(err("400","403","409").items()))}
    if note: post["x-internal-note"] = note
    paths[path] = {"get": {"tags":[tag],"summary":summary_list,"description":desc_list,
                           "parameters": filters + PAGE, "responses": listed(schema)},
                   "post": post}
    idn = name + "Id"
    paths[path+"/{"+idn+"}"] = {"get":{"tags":[tag],"summary":summary_list.replace("목록","한 건"),
        "description":desc_list,"parameters":[pathparam(idn)],
        "responses": dict(list(one(schema).items())+list(err("404").items()))}}

doc_resource("/production/material-consumptions","production","materialConsumption",
  "MaterialConsumption","MaterialConsumptionCreate","자재 투입 목록","자재 투입 등록",
  "근거: P-02-03 §3","오투입 판정이 서버에서 일어난다 — 화면만으로 막지 않는다. 근거: P-02-03 §5-1·5-3 · 공유계약 F-1",
  [q("workOrderId",I64), q("workSessionId",I64), q("lotId",I64), q("consumptionTypeCode",STR),
   q("occurredFrom",TS), q("occurredTo",TS)],
  note="idempotency_key 가 테이블 컬럼으로도 있다(NOT NULL UNIQUE) — 헤더로 받아 그 자리에 저장한다. 근거: 공유계약 C-8")
doc_resource("/production/material-returns","production","materialReturn",
  "MaterialReturn","MaterialReturnCreate","자재 반출 목록","자재 반출 등록",
  "근거: M-02-02 §3","근거: M-02-02 §5",
  [q("workOrderId",I64), q("statusCode",STR), q("requestedFrom",TS), q("requestedTo",TS)])
# ⛔ /production/material-losses 를 두지 않는다 — 5단계 역방향 점검에서 뺐다.
#    material_loss 테이블은 실재하지만 부르는 화면이 0건이다.
#    P-02-04 의 「손실」은 production_result.scrap_qty 로 들어간다(R48 3원 ↔ 5컬럼 · omf-mes#60).
#    「테이블이 있으니 경로를 만든다」는 01 정정 #2(테이블이 아니라 버튼을 센다)를 되돌리는 것이다.
#    손실을 별도로 기록하는 화면이 생기면 그때 만든다.
doc_resource("/production/production-results","production","productionResult",
  "ProductionResult","ProductionResultCreate","생산 실적 목록","생산 실적 등록",
  "집계 화면이 이 경로를 쓴다. 근거: P-02-04 §3 · W-02-08 §5",
  "다섯 수량을 그대로 받는다. 근거: P-02-04 §5",
  [q("workOrderId",I64), q("workSessionId",I64), q("shiftId",I64), q("equipmentId",I64),
   q("occurredFrom",TS), q("occurredTo",TS)],
  note="수량 구분이 정본 3원과 물리 5컬럼으로 어긋나 있다 — omf-mes#60. 계약은 5를 그대로 노출하고 접지 않는다.")
_corr = action("production","실적 정정","원본을 고치지 않고 정정 레코드를 덧붙인다. 근거: 공유계약 G-18 · W-02-05 §5",
               body="ProductionResultCorrect", resp=one("ProductionResult","201","정정 기록됨"))
_corr["parameters"].insert(0, pathparam("productionResultId"))
paths["/production/production-results/{productionResultId}:correct"] = {"post": _corr}
doc_resource("/production/operation-handovers","production","operationHandover",
  "OperationHandover","OperationHandoverCreate","공정 인계 목록","공정 인계 확정",
  "근거: M-02-01 §3","인계와 인수를 한 번에 확정한다 — 화면의 버튼이 하나다. 근거: M-02-01 §5 · 02 계약 2단계 §1-1",
  [q("fromWorkOrderId",I64), q("toWorkOrderId",I64), q("statusCode",STR),
   q("handedOverFrom",TS), q("handedOverTo",TS)],
  note="물리 모델은 handed_over_at NOT NULL / received_at nullable 로 구간 형 모양이다. 그런데 받는 쪽 화면이 없어 received_at 을 채울 경로가 생기지 않는다. 화면을 따라 인계 확정 시 두 시각을 함께 찍는다 — 원칙 1(데이터 모델은 화면 설계를 따라온다). 인수 확인 화면이 나중에 생기면 :receive 를 더한다.")

# ── 제품 개체(일련번호) 발번 — trace.serial_number
#
# ⭐ 왜 여기인가. 「소유는 쓰기를 가진 쪽」 규약대로다 — 쓰는 화면이 P-02-05
#    인식표 발행·부착(생산실행 POP) 하나뿐이다. 경로 앞이 /trace 라 자재창고
#    계약의 /trace/lots 와 네임스페이스를 나눠 쓰지만, 04 계약이
#    /logistics/shipment-lot-allocations 를 소유하는 것과 같은 형태다 —
#    네임스페이스는 물리 스키마를 따르고 소유는 쓰기를 따른다.
#
# ⛔ 왜 이제서야 만드나. 출력물 계약(app-공통.json)이 §3-1 에서 「개체 생성은
#    02 생산실행 계약 소관」이라 적고 넘겼는데 이쪽에도 없었다. 2026-08-13
#    착수 통지 발행 직전 실측에서 잡혔다 — 전 계약 6종에 serial 경로 0건.
#    그 사이 P-02-05 는 주 기능이 실행 불가라 통지를 낼 수 없었다.
#
# ⛔ {serialNumberId} 한 건 조회를 두지 않는다. 부르는 화면이 0건이다 —
#    P-02-09 의 개체 단위 재출력은 미결로 비활성이고, P-02-08 포장은
#    handling_unit_content 에 개체 참조 컬럼이 아예 없다.
#    /production/material-losses 를 뺀 것과 같은 기준이다.
schemas["SerialNumber"] = obj(["serialNumberId","serialNo","itemId","lotId","statusCode"], {
    "serialNumberId": I64,
    "serialNo": {**STR, "x-no-example": True,
        "description":"전역에서 유일하다 — 공장이 달라도 겹치지 않는다. 근거: P-02-05 §5-2. ⚠ 채번 규칙이 아직 정해지지 않아 예시를 두지 않는다 — 예시를 두면 자릿수·구성이 확정된 것처럼 읽힌다"},
    "itemId": I64, "lotId": {**I64, "description":"개체는 반드시 LOT 에 속한다"},
    "statusCode": {**STR, "x-no-example": True},
    "producedAt": TS, "versionNo": {"type":"integer"}})
schemas["SerialNumberBatchCreate"] = obj(["lotId","quantity"], {
    "lotId": I64,
    "quantity": {"type":"integer","minimum":1,"maximum":1000,
                 "example": 480,
                 "description":"발번할 개체 수. 미발행 양품 수를 넘으면 400 이다. 근거: P-02-05 §6"},
    "producedAt": TS})
schemas["SerialNumberBatchResult"] = obj(["items","issuedCount"], {
    "items": {"type":"array","items": ref("SerialNumber")},
    "issuedCount": {"type":"integer","example": 480,
                    "description":"만들어진 개체 수. quantity 와 같다 — 부분 발번이 없다"}})

paths["/trace/serial-numbers"] = {
 "get": {"tags":["production"],"summary":"제품 개체 목록",
   "description":("이미 발번된 개체를 센다. 화면이 「미발행 양품」을 계산하는 근거다 — "
     "양품 누계에서 이 목록의 건수를 뺀다. 근거: P-02-05 §5-3·§6"),
   "parameters":[q("lotId",I64), q("itemId",I64), q("statusCode",STR),
                 q("producedFrom",TS), q("producedTo",TS),
                 q("q",STR,"일련번호 검색")] + PAGE,
   "responses": listed("SerialNumber")},
 "post": {"tags":["production"],"summary":"제품 개체 대량 발번",
   "description":("양품 N개에 개체 N행을 만든다 — 인식표가 개체별 1:1 이기 때문이다(R69). "
     "번호는 서버가 매긴다. ⛔ 한 트랜잭션이고 부분 발번이 없다 — 하나라도 실패하면 전량 되돌린다. "
     "부분 발번은 번호에 구멍을 만들고 그것을 메울 화면이 없다. 근거: P-02-05 §5-3·§6 · 공유계약 B-8. "
     "⭐ 발행 기록은 이 경로가 만들지 않는다 — 공통 계약의 POST /app/document-issues 가 이어서 만든다. "
     "개체가 먼저 있어야 그쪽 targets 에 담을 수 있다. " + OFFLINE),
   "parameters":[pref("IdempotencyKey"), pref("IfMatchVersionOptional")],
   "requestBody":{"required":True,"content":{"application/json":{"schema": ref("SerialNumberBatchCreate")}}},
   "responses": dict(list(one("SerialNumberBatchResult","201","발번됨").items())
                     + list(err("400","403","409").items())),
   "x-internal-note":("409 인 이유가 자재 LOT 과 반대다. serial_no 는 서버가 채번하므로 "
     "중복이 나도 사용자가 고칠 수 없다 — 다시 부르면 풀린다. 반면 M-01-02 의 자재 LOT 번호는 "
     "스캔한 값이 그대로 번호라 재시도해도 안 풀려서 400 이다(01 계약 §3-1). "
     "⚠ 채번 규칙 자체는 아직 미정이다 — app.numbering_rule 에 인식표 규칙이 정의됐는지 "
     "확인되지 않았다(P-02-05 §8-2). 계약은 「서버가 매긴다」까지만 정하고 규칙을 정하지 않는다.")}}

HERE = os.path.dirname(os.path.abspath(__file__))

# ── 규약 정합 1) :validate 는 상태 전이가 아니다 → GET .../validation
del paths["/production/work-orders/{workOrderId}:validate"]
paths["/production/work-orders/{workOrderId}/validation"] = {"get": {
  "tags":["production"],"summary":"4M 배정 유효성 점검",
  "description":"자원 배정이 서로 부딪히는지 본다. 저장하지 않으므로 상태 전이가 아니다 — :동사 를 쓰지 않는다. 근거: W-02-03 §5 · 02 계약 2단계 §4-1",
  "parameters":[pathparam("workOrderId")],
  "responses": dict(list(one("ValidationReport","200","점검 결과").items())+list(err("403","404").items()))}}

# ── 규약 정합 2) DELETE 에 멱등키 · 선례 없음을 적는다
_d = paths["/planning/production-plans/{productionPlanId}"]["delete"]
_d["parameters"] = [pathparam("productionPlanId"), pref("IdempotencyKey"), pref("IfMatchVersion")]
_d["x-internal-note"] = ("01 자재창고 계약에는 DELETE 가 0건이다 — 업무 문서는 지우는 것이 아니라 상태를 옮기기 때문이다. "
  "확정 전 생산 계획은 아직 문서가 아니라 편집 중인 초안이라 물리 삭제를 둔다. 화면 액션에도 「계획 추가·삭제」가 있다(W-02-02). "
  "확정 뒤에는 W/O 가 매달려 있어 404 가 아니라 409 로 막는다.")

# ── example 자동 부여
EX = {
 "Id": 1001, "id": 1001,
 "No": "WO-2026-0812-001", "Code": "NORMAL", "code": "NORMAL",
 "Qty": 120.0, "qty": 120.0, "At": "2026-08-11T09:12:00+09:00",
 "Date": "2026-08-11", "Note": "비고", "note": "비고",
}
def example_for(name, sch):
    t = sch.get("type"); f = sch.get("format")
    if "enum" in sch: return sch["enum"][0]
    if "example" in sch: return sch["example"]
    if f == "uuid": return "6f1a0c2e-8b4d-4a1e-9c33-0b7c2f5d1a90"
    if f == "date-time": return "2026-08-11T09:12:00+09:00"
    if f == "date": return "2026-08-11"
    if t == "integer": return 1001 if name.endswith("Id") else 1
    if t == "number": return 120.0
    if t == "boolean": return True
    if t == "string":
        for k, v in EX.items():
            if name.endswith(k): return v
        if name.endswith("No"): return "WO-2026-0812-001"
        return "값"
    return None

def fill(schema_name, sch):
    props = sch.get("properties") or {}
    for pname, p in props.items():
        if not isinstance(p, dict): continue
        if "$ref" in p: continue
        if p.get("type") == "array":
            continue
        if p.get("type") == "object":
            continue
        # ⛔ 값 목록이 미확정인 코드에는 example 을 붙이지 않는다.
        #    접미사 하나로 매기는 자동 부여가 *Code 전부에 같은 값을 넣어
        #    「이 값이 확정된 것」처럼 읽히게 만든다(01·03·04 계약의 선례).
        if p.get("x-no-example"):
            continue
        if "example" not in p:
            e = example_for(pname, p)
            if e is not None: p["example"] = e
for n, s in schemas.items(): fill(n, s)

# 검사기가 잡은 둘 — object 타입 example · If-Match 를 받으면 409 를 선언한다
schemas["WorkOrder"]["properties"]["operationSettingsSnapshot"]["example"] = {
    "standardCycleTimeSec": 42, "standardYieldRate": 0.98}
_w = paths["/production/work-sessions/{workSessionId}/workers"]["post"]
_w["responses"].update(err("409"))

OUT = os.path.join(HERE, 'production-02생산실행.json')
src = json.load(io.open(os.path.join(HERE, 'logistics-01자재창고.json'),encoding='utf-8'))
doc = {
 "openapi": "3.1.0",
 "info": {
   "title": "omf-mes 02 생산실행 도메인 API (초안)",
   "version": "0.1.0",
   "description": ("02 생산실행 도메인 API 계약. P/O 수신에서 생산 계획·작업지시·작업 세션·자재 투입·생산 실적·공정 인계까지를 덮는다. "
     "경로는 물리 모델의 스키마를 그대로 네임스페이스로 쓰므로 /planning · /production · /trace 셋으로 나뉜다. "
     "/trace 는 자재창고 계약도 쓰지만 그쪽은 자재 LOT 이고 여기는 제품 개체다 — 네임스페이스는 물리 스키마를 따르고 소유는 쓰는 화면을 따른다. "
     "BOM·Routing 은 기준정보 계약이 소유하므로 여기서는 참조만 한다. "
     "자재 출고 요청·현장 수령·자재 LOT 은 자재창고 계약이 소유한다. 검사 결과는 품질 계약이 소유한다. "
     "출력물(인식표·라벨) 발행 기록은 공통 계약이 소유한다 — 다만 인식표가 붙는 제품 개체(일련번호)를 만드는 것은 여기다. 개체가 먼저 있어야 발행 기록의 대상이 된다. "
     "작업 세션은 구간 형 리소스다 — 「진행 중」을 상태 컬럼으로 두지 않고 끝 시각의 부재로 판정하며, 닫는 것은 :end 액션이다. "
     "현장 단말 화면 다수가 오프라인에서 쓰이므로 쓰기 오퍼레이션은 Idempotency-Key 를 필수로 받고 If-Match 를 선택으로 둔다. "
     "쓰기 응답은 201 하나다 — 오프라인이면 요청 자체가 서버에 닿지 않으므로 서버가 「접수했다」를 말할 자리가 없다(2026-08-12 정정). 202 는 ERP 재동기처럼 서버가 실제로 뒤에 처리하는 곳에만 남는다."),
   "x-internal-note": ("설계·도출 근거는 uiux/2026-08-11-API스펙-02생산실행/ 의 00~03 단계 문서다. "
     "리소스 12 · 액션 근거 103건(화면 액션 표 83 + 확대 3차 6장 본문 도출 20). "
     "미해소 상류 셋을 계약이 드러낸다 — omf-mes#76(긴급 W/O 가 P/O NOT NULL 체인에 막힘 · 501), "
     "omf-mes#60(수량 3원↔5컬럼). DR-007(취소 시 선발행 LOT 회수)은 2026-08-12 에 확정돼 본문에 반영됐다.")
 },
 "servers": [{"url": "/api", "description": "온프레미스 설치형"}],
 "tags": [{"name":"planning","description":"수주·계획 — P/O · 생산 계획"},
          {"name":"production","description":"생산 실행 — 작업지시 · 세션 · 투입 · 실적 · 인계"}],
 "paths": dict(sorted(paths.items())),
 "components": {"parameters": dict(src['components']['parameters']), "schemas": dict(sorted(schemas.items()))}
}
io.open(OUT,'w',encoding='utf-8').write(json.dumps(doc, ensure_ascii=False, indent=1))
ops = sum(1 for p in doc['paths'].values() for m in p if m in ('get','post','put','patch','delete'))
acts = sum(1 for p in doc['paths'] if ':' in p.rsplit('/',1)[-1])
print(f"경로 {len(doc['paths'])} · 오퍼레이션 {ops} · 스키마 {len(doc['components']['schemas'])} · :동사 경로 {acts} · {os.path.getsize(OUT)/1024:.0f}KB")
