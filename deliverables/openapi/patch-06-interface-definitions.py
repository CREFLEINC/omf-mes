#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""연계 정의와 송신 항목 설정을 계약에 세운다 — 06 §6 의 나머지 둘. 멱등.

무엇을 더하나
-------------
    /integration/interface-definitions               조회 · 등록      (W-06-09)
    /integration/interface-definitions/{id}          상세 · 수정
    /integration/interface-definitions/{id}:deactivate
    /integration/interface-definitions/{id}:test-connection
    /integration/outbound-item-settings              조회 · 묶음 저장  (W-06-12)

⛔ 왜 지금 쓰나 — 「지어내지 않는다」의 근거가 바뀌었다
------------------------------------------------------
06 요구서 §6 은 세 화면을 이렇게 미뤘다 —

    「엔드포인트를 지어내지 않았다. 테이블이 없으면 스키마를 만드는 순간
     전부 창작이 된다.」

**그 판단은 물리 모델을 근거의 바닥으로 놓은 것이다.** 2026-08-18 사용자 확정이
그것을 뒤집었다 — **데이터 모델링은 설계 결정을 앞설 수 없고, 무엇을 받나 ·
필수인가 선택인가 · 어떤 값이 오나는 설계가 정한다.**

⭐ **「테이블이 없다」와 「근거가 없다」는 다르다.** 이 둘은 근거가 오히려
촘촘하다 — 연계 정의는 확정 넷(QA #8·#18·#19·§3.2)이, 송신 항목은 확정 넷
(QA #1·#4·#6·#35)이 걸린다. 창작이 되는 것은 **근거 없는 칸**이지 테이블 부재가
아니다. 근거 없는 칸은 여전히 적지 않았다 — 아래 «적지 않은 것».

⛔ 적지 않은 것 — 근거가 없어서다
---------------------------------
    변환 규칙(W-06-09 §4-C)        근거 없음
    「부속 항목」(W-06-12 §3-3)     인벤토리에만 있고 원문 확인 안 됨
    트리거 조건의 표현 형식         「Event 즉시」만 확정 — 자유 문자열로 받는다

⭐ 「필수」와 「비연계」는 기본값이 아니라 «구조» 다
---------------------------------------------------
생산 실적 송신은 **끌 수 없고**(QA #35), 검사 결과는 **목록에 없다**(QA #4).
둘을 「기본값이 켜짐/꺼짐」으로 두면 누군가 끄거나 켤 수 있어 확정이 무너진다.

    필수    → locked 참 + lockReason. 서버가 거부하고 화면은 조작을 못 열게 한다
    비연계  → 값 목록에 «넣지 않는다». 꺼진 채로도 보이지 않는다

⚠ 송신 항목은 한 번에 저장한다 — 즉시 반영이 아니다
----------------------------------------------------
끄는 순간 ERP 전표가 끊긴다. **되돌려도 미송신 기간은 원상 복구되지 않는다.**
그래서 토글 즉시 반영이 아니라 묶음 저장으로 두고, 잔여 미전송 건수를 응답이
함께 내린다(W-06-12 §5·§6).

📨 물리 모델에 두 표가 없다 — 작업 통지이고 우리를 막지 않는다
--------------------------------------------------------------
`integration_message.interface_code` 는 FK 없는 맨 코드였다. 이제 계약이 가리킬
대상을 갖는다. 통지 = omf-mes#66.

⚠ 함께 손보는 것 — 낡은 설명 둘
--------------------------------
「정의 테이블이 없어 선택 목록을 만들 수 없다」가 두 곳에 적혀 있었다. 이제
만들 수 있으므로 고친다. **낡은 설명은 새 결손보다 나쁘다** — 읽는 쪽이 없는
제약을 지킨다.

⛔ 남는 결손 — 이 패치가 «못» 고치는 것
---------------------------------------
「Legacy 출처 플래그」가 대상 마스터 다섯 곳에 없어 수신본 편집 게이트가 서지
않는다(W-06-09 §8-2). 그것은 다른 마스터의 컬럼 문제라 이 계약이 혼자 못 푼다 —
omf-mes#66 에 함께 담긴다.

쓰기
----
    python3 deliverables/openapi/patch-06-interface-definitions.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "mdm-기준정보.json")

IDEM = {"$ref": "#/components/parameters/IdempotencyKey"}
IFMATCH = {"$ref": "#/components/parameters/IfMatchVersion"}

ETAG = {
    "ETag": {
        "description": ("낙관적 잠금 토큰 — 이 행의 version_no. 다음 쓰기의 If-Match 에 "
                        "그대로 담는다. 본문 필드로는 내리지 않는다 — 표시하지 않되 전달한다"),
        "schema": {"type": "string"},
        "x-internal-note": ("본문 필드로 내리지 않는 이유는 공유계약 A-4 이고, 전송 자체는 "
                            "B-1(낙관적 잠금) 구현에 필요하다"),
    }
}

EXTERNAL_SYSTEMS = ["UNIERP", "TRACKING_SYSTEM", "EQUIPMENT_STANDARD_IF"]
OUTBOUND_ITEMS = ["PRODUCTION_RESULT", "GOODS_RECEIPT", "SHIPMENT_PGI",
                  "RETURN", "STOCK_ADJUSTMENT"]

MODEL_GAP = ("물리 모델에 저장처가 없다 — 계약이 화면 요구대로 먼저 선다. "
             "데이터 모델 담당에게 낸 작업 통지는 omf-mes#66 이다.")


def prop(kind, example, **kw) -> dict:
    out = {"type": kind, "example": example}
    out.update(kw)
    return out


def nullable(kind, example, **kw) -> dict:
    return prop([kind, "null"], example, **kw)


def err(desc: str) -> dict:
    return {"description": desc,
            "content": {"application/json":
                        {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}}


def ok(desc: str, schema: str, etag: bool = False) -> dict:
    out = {"description": desc,
           "content": {"application/json":
                       {"schema": {"$ref": "#/components/schemas/%s" % schema}}}}
    if etag:
        out["headers"] = dict(ETAG)
    return out


def conflict() -> dict:
    return {"description": "저장 충돌 — 다른 사용자가 먼저 고쳤다",
            "content": {"application/json":
                        {"schema": {"$ref": "#/components/schemas/ConflictResponse"}}}}


TRIGGER_NOTE = (
    "트리거 유형이 TIME_SCHEDULE 이면 scheduleExpression 이, EVENT 이면 "
    "eventCondition 이 함께 있어야 한다. 한쪽만 채워 보내면 400 이다"
)

TARGET_NOTE = (
    "연계 대상. 확정된 수신 대상은 품목 · 자재명세 · 공통코드 · 조직 · 작업자 · "
    "구매발주 여섯이며 그 밖의 값도 받는다 — 막지 않고 표식만 한다. 확정 목록 안인지는 "
    "withinConfirmedScope 가 말한다"
)

DEFINITION_PROPS = {
    "interfaceCode": prop("string", "IF-GR-SEND", maxLength=50,
                          description="전역에서 유일하다. 연계 메시지의 interfaceCode 가 이 값을 가리킨다"),
    "interfaceName": prop("string", "입고 전표 송신", maxLength=200),
    "directionCode": prop("string", "OUTBOUND", enum=["INBOUND", "OUTBOUND"],
                          description="수신 또는 송신"),
    "targetCode": prop("string", "ITEM", maxLength=50, description=TARGET_NOTE),
    "externalSystemCode": prop(
        "string", "UNIERP", enum=list(EXTERNAL_SYSTEMS),
        description=("외부 시스템 셋. 기간계(UNIERP)는 마스터 연계, 추적관리시스템은 제품 "
                     "바코드 이력, 설비 표준 연계는 실적·측정값을 나른다 — 성격이 전혀 "
                     "다른데 같은 「연계」로 불리므로 축을 나눠 둔다")),
    "triggerTypeCode": prop("string", "TIME_SCHEDULE",
                            enum=["TIME_SCHEDULE", "EVENT"],
                            description="주기로 도는가 사건에 반응하는가"),
    "scheduleExpression": nullable(
        "string", "매일 06:00", maxLength=200,
        description=("주기 또는 시각. 표현 형식이 확정되지 않아 자유 문자열로 받되 화면이 "
                     "예시를 보여 형태를 이끈다 — 공유계약 A-12")),
    "eventCondition": nullable(
        "string", "수입검사 합격 확정 시", maxLength=500,
        description=("촉발 조건. 표현 형식에 근거가 없어 자유 문자열로 받는다 — "
                     "공유계약 A-12")),
    "relayTableName": nullable("string", "TMP_GR_SEND", maxLength=100,
                               description="데이터베이스 중계 테이블 이름"),
}

SCHEMAS = {
    "InterfaceColumnMapping": {
        "type": "object",
        "required": ["relayColumn", "targetTable", "targetColumn"],
        "description": ("중계 테이블 칸과 이 시스템의 칸을 잇는다. 근거: W-06-09 §4-C"),
        "x-internal-note": (MODEL_GAP + " 변환 규칙 칸은 «두지 않았다» — 근거가 없다. "
                            "중계 테이블 스키마 상세가 확정되면 열 구성을 다시 본다."),
        "properties": {
            "relayColumn": prop("string", "GR_QTY", maxLength=100),
            "targetTable": prop("string", "inventory.goods_receipt", maxLength=100),
            "targetColumn": prop("string", "received_qty", maxLength=100),
        },
    },
    "InterfaceDefinition": {
        "type": "object",
        "required": ["interfaceDefinitionId", "interfaceCode", "interfaceName",
                     "directionCode", "targetCode", "externalSystemCode",
                     "triggerTypeCode", "withinConfirmedScope", "isActive"],
        "description": ("연계 정의. 무엇을 어느 쪽으로 언제 나르는가를 정한다. 실제 실행과 "
                        "현황은 다른 화면이 다룬다 — 정의는 마스터이고 실행은 이력이라 "
                        "저장 방식과 조회 규약이 다르다. " + TRIGGER_NOTE +
                        ". 근거: W-06-09 §4-A·§4-B"),
        "x-internal-note": MODEL_GAP,
        "properties": dict(
            {"interfaceDefinitionId": prop("integer", 1001, format="int64")},
            **dict(DEFINITION_PROPS, **{
                "withinConfirmedScope": prop(
                    "boolean", True,
                    description=("targetCode 가 확정된 수신 대상 여섯 안에 드는가. 거짓이면 "
                                 "화면이 「확정 목록 밖입니다」를 표식한다 — 막지는 않는다")),
                "isActive": prop("boolean", True, default=True),
            })),
    },
    "InterfaceDefinitionCreate": {
        "type": "object",
        "required": ["interfaceCode", "interfaceName", "directionCode", "targetCode",
                     "externalSystemCode", "triggerTypeCode"],
        "description": TRIGGER_NOTE,
        "properties": dict(DEFINITION_PROPS, **{
            "columnMappings": {"type": "array",
                               "items": {"$ref": "#/components/schemas/InterfaceColumnMapping"}},
        }),
    },
    "InterfaceDefinitionUpdate": {
        "type": "object",
        "required": ["interfaceName", "directionCode", "targetCode",
                     "externalSystemCode", "triggerTypeCode"],
        "description": ("한 번에 저장한다 — 기본 정보 · 트리거 · 칸 잇기가 한 화면의 한 "
                        "저장이다. columnMappings 는 통째로 교체되며 보내지 않은 줄은 "
                        "사라진다. interfaceCode 는 참조가 0일 때만 보낼 수 있다. " +
                        TRIGGER_NOTE),
        "properties": dict(DEFINITION_PROPS, **{
            "columnMappings": {"type": "array",
                               "items": {"$ref": "#/components/schemas/InterfaceColumnMapping"}},
        }),
    },
    "InterfaceDefinitionDetailResponse": {
        "type": "object",
        "required": ["interfaceDefinition", "columnMappings", "editability",
                     "pendingMessageCount"],
        "properties": {
            "interfaceDefinition": {"$ref": "#/components/schemas/InterfaceDefinition"},
            "columnMappings": {"type": "array",
                               "items": {"$ref": "#/components/schemas/InterfaceColumnMapping"}},
            "editability": {"$ref": "#/components/schemas/Editability"},
            "pendingMessageCount": prop(
                "integer", 4,
                description=("아직 보내지 못한 연계 메시지 수. 사용 중지 확인 문구가 이 값을 "
                             "쓴다 — 남은 것이 있는데 끄면 그대로 멈춘다")),
        },
    },
    "InterfaceConnectionTestResult": {
        "type": "object",
        "required": ["succeeded"],
        "description": ("중계 테이블에 닿는지만 본다 — 실제 동기화를 돌리지 않는다. "
                        "실패해도 저장을 막지 않는다. 설정을 먼저 하고 연결을 나중에 "
                        "맞추는 것이 정상 순서다. 근거: W-06-09 §6"),
        "properties": {
            "succeeded": prop("boolean", False),
            "failureCauseCode": nullable(
                "string", "TABLE_NOT_FOUND",
                description=("UNREACHABLE(닿지 않는다) · TABLE_NOT_FOUND(테이블이 없다) · "
                             "PERMISSION_DENIED(권한이 없다) 셋을 가른다. 「연결 실패」 "
                             "한 마디로 뭉치면 무엇을 고쳐야 할지 알 수 없다")),
            "message": nullable("string", "중계 테이블 TMP_GR_SEND 을 찾을 수 없습니다"),
        },
    },
    "OutboundItemSetting": {
        "type": "object",
        "required": ["outboundItemCode", "outboundItemName", "enabled", "locked",
                     "pendingMessageCount"],
        "description": ("송신 항목 하나의 켜짐·꺼짐. 검사 결과는 연계하지 않기로 확정돼 "
                        "이 목록에 «나타나지 않는다» — 꺼진 채로도 보이지 않는다. "
                        "근거: W-06-12 §3-1"),
        "x-internal-note": MODEL_GAP,
        "properties": {
            "outboundItemCode": prop("string", "GOODS_RECEIPT", enum=list(OUTBOUND_ITEMS),
                                     description=("생산 실적 · 입고 · 출하 · 반품 · 실사 조정 "
                                                  "다섯. 검사 결과는 목록에 없다")),
            "outboundItemName": prop("string", "입고"),
            "enabled": prop("boolean", True),
            "locked": prop(
                "boolean", False,
                description=("참이면 끌 수 없다. 생산 실적 송신이 그렇다 — 서버가 거부하고 "
                             "화면은 조작 자체를 열지 않는다. 기본값으로 두지 않는 이유는 "
                             "기본값이면 누군가 끌 수 있기 때문이다")),
            "lockReason": nullable(
                "string", "생산 실적 송신은 필수입니다",
                description=("왜 끌 수 없는가. 화면이 그대로 보인다 — 바꿀 수 없는 것에는 "
                             "근거가 함께 보여야 재확인 요청이 정상 경로로 간다")),
            "sendTimingNote": nullable(
                "string", "수입검사 합격 직후 건별",
                description="언제 보내는가. 항목마다 다르며 화면은 표시만 한다"),
            "interfaceDefinitionId": nullable(
                "integer", 1001, format="int64",
                description="이 항목을 나르는 연계 정의. 아직 이어 두지 않았으면 비어 있다"),
            "pendingMessageCount": prop(
                "integer", 0,
                description=("아직 보내지 못한 건수. 남은 것이 있는데 끄면 그대로 멈추므로 "
                             "확인 문구가 이 값을 쓴다")),
        },
    },
    "OutboundItemSettingList": {
        "type": "object",
        "required": ["items"],
        "properties": {
            "items": {"type": "array",
                      "items": {"$ref": "#/components/schemas/OutboundItemSetting"}},
        },
    },
    "OutboundItemSettingUpdate": {
        "type": "object",
        "required": ["items"],
        "description": ("한 번에 저장한다 — 토글이 곧바로 반영되지 않는다. 끄는 순간 "
                        "외부로 나가는 전표가 끊기고 되돌려도 그 사이는 복구되지 않기 "
                        "때문이다. locked 인 항목을 꺼서 보내면 400 이다. 근거: W-06-12 §5"),
        "properties": {
            "items": {"type": "array",
                      "items": {"$ref": "#/components/schemas/OutboundItemSettingInput"}},
        },
    },
    "OutboundItemSettingInput": {
        "type": "object",
        "required": ["outboundItemCode", "enabled"],
        "properties": {
            "outboundItemCode": prop("string", "GOODS_RECEIPT", enum=list(OUTBOUND_ITEMS)),
            "enabled": prop("boolean", True),
            "interfaceDefinitionId": nullable("integer", 1001, format="int64"),
        },
    },
}

PATHS = {
    "/integration/interface-definitions": {
        "get": {
            "tags": ["integration"], "summary": "연계 정의 목록",
            "description": ("연계 메시지 조회의 연계 코드 선택 목록도 이것을 쓴다. "
                            "근거: W-06-09 §3"),
            "parameters": [
                {"name": "q", "in": "query", "schema": {"type": "string"},
                 "description": "코드·명칭 검색"},
                {"name": "directionCode", "in": "query",
                 "schema": {"type": "string", "enum": ["INBOUND", "OUTBOUND"]}},
                {"name": "targetCode", "in": "query", "schema": {"type": "string"}},
                {"name": "externalSystemCode", "in": "query",
                 "schema": {"type": "string", "enum": list(EXTERNAL_SYSTEMS)}},
                {"name": "includeInactive", "in": "query",
                 "schema": {"type": "boolean", "default": False}},
                {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                {"name": "size", "in": "query", "schema": {"type": "integer", "default": 50}},
            ],
            "responses": {"200": {
                "description": "목록",
                "content": {"application/json": {"schema": {
                    "type": "object",
                    "required": ["items", "page"],
                    "properties": {
                        "items": {"type": "array",
                                  "items": {"$ref": "#/components/schemas/InterfaceDefinition"}},
                        "page": {"$ref": "#/components/schemas/PageMeta"},
                    }}}}}},
        },
        "post": {
            "tags": ["integration"], "summary": "연계 정의 등록",
            "description": "근거: W-06-09 §5",
            "parameters": [IDEM],
            "requestBody": {"required": True,
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/InterfaceDefinitionCreate"}}}},
            "responses": {"201": ok("등록됨", "InterfaceDefinition"),
                          "400": err("검증 실패 — 유일 위반이거나 트리거 짝이 맞지 않는다"),
                          "403": err("권한 없음 — 전산 담당 전용이다")},
        },
    },
    "/integration/interface-definitions/{interfaceDefinitionId}": {
        "parameters": [{"name": "interfaceDefinitionId", "in": "path", "required": True,
                        "schema": {"type": "integer", "format": "int64"}}],
        "get": {
            "tags": ["integration"], "summary": "연계 정의 상세",
            "description": ("기본 정보 · 트리거 · 칸 잇기를 한 번에 내린다. "
                            "근거: W-06-09 §3"),
            "responses": {"200": ok("상세", "InterfaceDefinitionDetailResponse", etag=True)},
        },
        "put": {
            "tags": ["integration"], "summary": "연계 정의 수정",
            "description": "근거: W-06-09 §5 · 공유계약 B-1",
            "parameters": [IDEM, IFMATCH],
            "requestBody": {"required": True,
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/InterfaceDefinitionUpdate"}}}},
            "responses": {"200": ok("수정됨", "InterfaceDefinition", etag=True),
                          "400": err("검증 실패 — 트리거 짝이 맞지 않는다"),
                          "403": err("권한 없음"),
                          "409": conflict()},
        },
    },
    "/integration/interface-definitions/{interfaceDefinitionId}:deactivate": {
        "parameters": [{"name": "interfaceDefinitionId", "in": "path", "required": True,
                        "schema": {"type": "integer", "format": "int64"}}],
        "post": {
            "tags": ["integration"], "summary": "연계 정의 사용 중지",
            "description": ("물리 삭제는 제공하지 않는다. 보내지 못한 메시지가 남아 있으면 "
                            "상세 조회의 pendingMessageCount 를 확인 문구에 담은 뒤 부른다. "
                            "근거: W-06-09 §6 · 공유계약 B-4"),
            "parameters": [IDEM, IFMATCH],
            "responses": {"200": ok("중지됨", "InterfaceDefinition", etag=True),
                          "400": err("업무 규칙 위반"),
                          "403": err("권한 없음"),
                          "409": conflict()},
        },
    },
    "/integration/interface-definitions/{interfaceDefinitionId}:test-connection": {
        "parameters": [{"name": "interfaceDefinitionId", "in": "path", "required": True,
                        "schema": {"type": "integer", "format": "int64"}}],
        "post": {
            "tags": ["integration"], "summary": "연결 시험",
            "description": ("중계 테이블에 닿는지만 본다. 실제 동기화는 돌리지 않는다 — "
                            "그것은 연계 현황 화면 소관이다. 근거: W-06-09 §3·§6"),
            "parameters": [IDEM],
            "responses": {"200": ok("시험 결과 — 실패도 200 으로 내린다. 요청이 잘못된 것이 "
                                    "아니라 연결이 안 된 것이라 결과를 구조로 돌려준다",
                                    "InterfaceConnectionTestResult"),
                          "403": err("권한 없음")},
        },
    },
    "/integration/outbound-item-settings": {
        "get": {
            "tags": ["integration"], "summary": "송신 항목 설정",
            "description": ("송신 항목 다섯의 켜짐·꺼짐과 잠금 여부. 검사 결과는 연계하지 "
                            "않기로 확정돼 목록에 없다. 근거: W-06-12 §3-1"),
            "responses": {"200": ok("설정", "OutboundItemSettingList")},
        },
        "put": {
            "tags": ["integration"], "summary": "송신 항목 설정 저장",
            "description": ("묶음으로 저장한다. locked 인 항목을 끄려 하면 400 으로 거부한다 "
                            "— 화면이 조작을 막는 것과 별개로 계약도 막는다. "
                            "근거: W-06-12 §5·§9-1"),
            "parameters": [IDEM],
            "requestBody": {"required": True,
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/OutboundItemSettingUpdate"}}}},
            "responses": {"200": ok("저장됨", "OutboundItemSettingList"),
                          "400": err("끌 수 없는 항목을 끄려 했거나 알 수 없는 항목 코드다"),
                          "403": err("권한 없음 — 전산 담당 전용이다")},
            "x-internal-note": ("저장 충돌 보호를 붙이지 않았다 — 항목이 다섯인 고정 목록이고 "
                                "행을 오가며 편집하는 형태가 아니다. 「개발품 제외」의 판정 축"
                                "(품목이냐 작업지시 유형이냐)은 이 계약이 정하지 않는다 — "
                                "확정 문구가 갈려 있고 omf-mes#70 에서 사용자 결정을 기다린다."),
        },
    },
}

STALE = {
    "정의 테이블이 없어 선택 목록을 만들 수 없다":
        "연계 정의 목록에서 고른다 — GET /integration/interface-definitions",
}


def main() -> int:
    with open(CONTRACT, encoding="utf-8") as fh:
        spec = json.load(fh)
    before = json.dumps(spec, ensure_ascii=False, sort_keys=True)

    spec["components"]["schemas"].update(SCHEMAS)
    spec["paths"].update(PATHS)

    # 낡은 설명을 고친다 — 이제 선택 목록을 만들 수 있다.
    msg = spec["components"]["schemas"]["IntegrationMessage"]
    msg["properties"]["interfaceCode"]["description"] = (
        "연계 정의의 interfaceCode 를 가리킨다. 선택 목록은 "
        "GET /integration/interface-definitions 에서 받는다")
    for param in spec["paths"]["/integration/messages"]["get"]["parameters"]:
        if param.get("name") == "interfaceCode":
            param["description"] = (
                "연계 정의의 interfaceCode. 선택 목록은 "
                "GET /integration/interface-definitions 에서 받는다")

    after = json.dumps(spec, ensure_ascii=False, sort_keys=True)
    with open(CONTRACT, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(spec, ensure_ascii=False, indent=2) + "\n")

    print("경로 %d · 스키마 %d" % (len(spec["paths"]), len(spec["components"]["schemas"])))
    print("바뀐 것이 %s" % ("없다 — 이미 반영돼 있다" if before == after else "있다"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
