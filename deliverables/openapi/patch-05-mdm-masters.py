#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""05 설비·툴이 요구하는 마스터를 기준정보 계약에 더한다. 멱등.

무엇을 더하나
-------------
    설비 그룹 · 설비(쓰기) · 설비 점검 항목(+부여) · 툴 · 예비품(+설비 매핑)
    작업 캘린더(+일자·적용·해석)

⛔ 2단계 「17경로」에서 늘었다 — 세 가지가 드러났다
---------------------------------------------------
① **설비 자체에 쓰기 경로가 없었다.** 2단계는 `/mdm/equipments` 를 「기존 자원을
   그대로 부른다」로 셌는데, 있는 것은 **선택 목록용 조회 하나뿐**이었다.
   그런데 `W-05-12` 는 「설비 추가·저장·사용 중지」를 요구한다.
   ⭐ 1단계가 0단계에 대해 잡은 것과 **같은 형태**다 — 「있다」와 「내가 쓸 수
   있는 형태로 있다」는 다르다.

② **점검 항목 «부여» 경로가 없었다.** 2단계는 항목 마스터 두 경로만 셌으나,
   `W-05-12` 의 「점검 항목 부여 편집」은 **설비·그룹에 묶음을 붙이는 다른 자원**
   이고 `M-05-01` 이 그 해석 결과를 읽는다.

③ **캘린더 일자·적용 경로가 없었다.** 캘린더 머리만으로는 「이 날 휴무」도
   「이 그룹은 이 캘린더를 따른다」도 저장할 곳이 없다.

⛔ 계측기 전용 경로(`/mdm/gauges`)를 두지 않는다 — 2단계 판정을 바꾼다
----------------------------------------------------------------------
`W-05-11` §3-2 가 **계측기는 `mdm.equipment` 의 한 종류**(`equipment_type_code`
가 가른다)로 확정했다. 그래서 두 경로에 각각 쓰기를 두면 **한 행을 두 계약이
쓴다** — 공유계약 B-13 이 정면으로 걸리고, 폐기 처리가 두 벌이 된다.

    ⛔ /mdm/gauges         쓰기 두 벌 · 같은 행 · 같은 version_no
    ✅ /mdm/equipments     하나 · 계측기 화면은 equipmentTypeCode 로 거른다

**「같은 테이블을 다른 눈으로 본다」는 필터이지 자원이 아니다.**
계측기 전용 속성(검교정 주기·정밀도)은 설비 스키마에 더한다 — 계측기가 아니면
비어 있는 것이 정상이다(공유계약 A-2 조건부).

⛔ 점검 항목 경로 이름을 `/mdm/equipment-inspection-items` 로 한다
------------------------------------------------------------------
2단계는 `/mdm/inspection-items` 로 적었다. **이 계약에는 품질 검사 항목이 이미
있다**(`/quality/inspection-plan-versions/{id}/items`). `W-05-12` §4-C-1 이
「점검(설비) ≠ 검사(품질)」을 **테이블을 나누는 근거**로 세웠는데 경로 이름이
그것을 지우면 안 된다.

⭐ 저장 충돌 보호는 여섯 곳 — 토큰을 «받을 곳»까지가 한 세트
-------------------------------------------------------------
    설비 그룹 · 설비 · 툴 · 예비품 · 작업 캘린더 · 부여 묶음 교체

`If-Match` 를 필수로 두는 자리마다 **같은 경로의 상세 조회가 `ETag` 응답 헤더를
선언**한다. 선언을 빠뜨려 구현이 막힌 전례가 19곳 있었다(2026-08-17).

⭐ `:deactivate` 와 `:dispose` 를 가른다
----------------------------------------
사용 중지(`is_active`)와 폐기(`status_code`)는 **다른 축**이다 — 공유계약 B-16.
툴·설비 화면이 버튼 둘을 따로 갖는다.

📨 물리 모델에 없는 것이 있다 — 작업 통지이고 우리를 막지 않는다
----------------------------------------------------------------
설비 점검 항목·부여 · 예비품 · 설비-예비품 매핑 · 작업 캘린더·일자·적용 ·
툴 유형 축 · 검교정 주기 · 정밀도. **계약은 화면대로 쓰고** 결손은
`x-internal-note` 에 적는다(사용자 확정 2026-08-18 — 데이터 모델은 설계
결정을 앞설 수 없다).

쓰기
----
    python3 deliverables/openapi/patch-05-mdm-masters.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "mdm-기준정보.json")

MODEL_GAP = ("물리 모델에 저장처가 없다 — 계약이 화면 요구대로 먼저 선다. "
             "데이터 모델 담당에게 낸 작업 통지는 omf-mes#67 이다.")

ETAG = {
    "ETag": {
        "description": ("낙관적 잠금 토큰 — 이 행의 version_no. 다음 쓰기의 If-Match 에 "
                        "그대로 담는다. 본문 필드로는 내리지 않는다 — 표시하지 않되 전달한다"),
        "schema": {"type": "string"},
        "x-internal-note": ("본문 필드로 내리지 않는 이유는 공유계약 A-4(version_no 는 화면에 "
                            "노출하지 않는다)이고, 전송 자체는 A-4 가 함께 요구하는 "
                            "B-1(낙관적 잠금) 구현에 필요하다"),
    }
}

IDEM = {"$ref": "#/components/parameters/IdempotencyKey"}
IFMATCH = {"$ref": "#/components/parameters/IfMatchVersion"}


def err(desc: str) -> dict:
    return {"description": desc,
            "content": {"application/json":
                        {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}}


def conflict() -> dict:
    return {"description": ("저장 충돌 — 다른 사용자가 먼저 고쳤다. 업무 규칙 위반"
                            "(상태 잠김·참조 존재)은 409 가 아니라 400 이다"),
            "content": {"application/json":
                        {"schema": {"$ref": "#/components/schemas/ConflictResponse"}}}}


def ok(desc: str, schema: str, etag: bool = False) -> dict:
    out = {"description": desc,
           "content": {"application/json": {"schema": {"$ref": "#/components/schemas/%s" % schema}}}}
    if etag:
        out["headers"] = dict(ETAG)
    return out


def page_response(schema: str, desc: str = "목록") -> dict:
    return {"description": desc,
            "content": {"application/json": {"schema": {
                "type": "object",
                "required": ["items", "page"],
                "properties": {
                    "items": {"type": "array",
                              "items": {"$ref": "#/components/schemas/%s" % schema}},
                    "page": {"$ref": "#/components/schemas/PageMeta"},
                }}}}}


def path_param(name: str) -> dict:
    return {"name": name, "in": "path", "required": True,
            "schema": {"type": "integer", "format": "int64"}}


def paging_params() -> list:
    return [
        {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
        {"name": "size", "in": "query", "schema": {"type": "integer", "default": 50}},
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 스키마
# ─────────────────────────────────────────────────────────────────────────────

def prop(kind, example, **kw) -> dict:
    out = {"type": kind, "example": example}
    out.update(kw)
    return out


def nullable(kind, example, **kw) -> dict:
    return prop([kind, "null"], example, **kw)


SCHEMAS = {}

# ── 설비 그룹 ────────────────────────────────────────────────────────────────
SCHEMAS["EquipmentGroup"] = {
    "x-source-table": "mdm.production_line",
    "type": "object",
    "required": ["equipmentGroupId", "plantId", "groupCode", "groupName",
                 "groupTypeCode", "isActive"],
    "description": ("설비 그룹. 화면이 「설비 그룹」이라 부르는 것과 저장처가 "
                    "같은 자원이다 — Equipment.productionLineId 가 가리키는 것이 "
                    "이 equipmentGroupId 다. 계층은 parentGroupId 자기참조이며 "
                    "순환은 서버가 막는다. 근거: W-05-12 §3·§4-A"),
    "x-internal-note": ("이름이 둘인 이유 — 상류(개념모델·결정 03)는 「설비그룹」, 물리 모델은 "
                        "mdm.production_line 이다. W-05-12 §3-1 이 형태가 같음을 실측했고 "
                        "테이블 신설을 요구하지 않기로 했다. 명칭 정리는 omf-mes#67 회신 항목."),
    "properties": {
        "equipmentGroupId": prop("integer", 1001, format="int64",
                                 **{"x-source-column": "production_line_id"}),
        "plantId": prop("integer", 1001, format="int64", **{"x-source-column": "plant_id"}),
        "groupCode": prop("string", "PRESS-A", maxLength=50,
                          description="uq_production_line(plant_id, line_code)",
                          **{"x-source-column": "line_code"}),
        "groupName": prop("string", "프레스라인 A", maxLength=200,
                          **{"x-source-column": "line_name"}),
        "groupTypeCode": prop("string", "LINE", maxLength=50,
                              description="공통코드 — 값 목록이 확정되지 않았다",
                              **{"x-source-column": "line_type_code"}),
        "parentGroupId": nullable("integer", 1001, format="int64",
                                  description="상위 그룹. 비면 최상위",
                                  **{"x-source-column": "parent_line_id"}),
        "isActive": prop("boolean", True, default=True, **{"x-source-column": "is_active"}),
    },
}
SCHEMAS["EquipmentGroupCreate"] = {
    "type": "object",
    "required": ["plantId", "groupCode", "groupName", "groupTypeCode"],
    "properties": {
        "plantId": prop("integer", 1001, format="int64"),
        "groupCode": prop("string", "PRESS-A", maxLength=50),
        "groupName": prop("string", "프레스라인 A", maxLength=200),
        "groupTypeCode": prop("string", "LINE", maxLength=50),
        "parentGroupId": nullable("integer", 1001, format="int64"),
    },
}
SCHEMAS["EquipmentGroupUpdate"] = {
    "type": "object",
    "required": ["groupName", "groupTypeCode"],
    "description": ("groupCode 는 참조가 0일 때만 보낼 수 있다 — 상세 조회의 "
                    "editability 가 가부와 사유를 함께 내린다. 근거: 공유계약 B-4"),
    "properties": {
        "groupCode": prop("string", "PRESS-A", maxLength=50),
        "groupName": prop("string", "프레스라인 A", maxLength=200),
        "groupTypeCode": prop("string", "LINE", maxLength=50),
        "parentGroupId": nullable("integer", 1001, format="int64"),
    },
}
SCHEMAS["EquipmentGroupDetailResponse"] = {
    "type": "object",
    "required": ["equipmentGroup", "editability", "memberEquipmentCount"],
    "properties": {
        "equipmentGroup": {"$ref": "#/components/schemas/EquipmentGroup"},
        "editability": {"$ref": "#/components/schemas/Editability"},
        "memberEquipmentCount": prop(
            "integer", 12,
            description="이 그룹에 소속된 설비 대수. 사용 중지 확인 문구가 이 값을 쓴다"),
    },
}

# ── 설비(쓰기) ───────────────────────────────────────────────────────────────
EQUIPMENT_WRITE_PROPS = {
    "equipmentName": prop("string", "프레스 1호기", maxLength=200),
    "equipmentTypeCode": prop("string", "PRESS", maxLength=50,
                              description="공통코드 — 계측기 화면은 이 값으로 거른다"),
    "productionLineId": nullable("integer", 1001, format="int64",
                                 description="소속 설비 그룹. 비면 계층 표시가 공장까지만 나온다"),
    "processId": nullable("integer", 1001, format="int64"),
    "calibrationRequired": prop("boolean", False, default=False),
    "calibrationCycleTypeCode": nullable(
        "string", "MONTH", maxLength=50,
        description="검교정 주기 단위. calibrationRequired 가 참이면 주기 두 칸이 함께 필요하다"),
    "calibrationCycleInterval": nullable(
        "integer", 12, minimum=1, description="검교정 주기 간격"),
    "precisionValue": nullable("number", 0.01, description="정밀도 수치"),
    "precisionUomId": nullable("integer", 1001, format="int64", description="정밀도 단위"),
}
SCHEMAS["EquipmentCreate"] = {
    "type": "object",
    "required": ["plantId", "equipmentCode", "equipmentName", "equipmentTypeCode",
                 "calibrationRequired"],
    "description": ("설비 등록. 계측기도 설비의 한 종류이며 equipmentTypeCode 가 "
                    "가른다 — 별도 자원을 두지 않는다. 근거: W-05-11 §3-2 · W-05-12 §4-B"),
    "properties": dict(
        {"plantId": prop("integer", 1001, format="int64"),
         "equipmentCode": prop("string", "PRS-01", maxLength=50,
                               description="uq_equipment(plant_id, equipment_code). 호기를 포함하는 채번 규약으로 흡수한다")},
        **EQUIPMENT_WRITE_PROPS),
}
SCHEMAS["EquipmentUpdate"] = {
    "type": "object",
    "required": ["equipmentName", "equipmentTypeCode", "calibrationRequired"],
    "description": ("equipmentCode 는 참조가 0일 때만 보낼 수 있다 — 상세 조회의 "
                    "editability 가 가부와 사유를 함께 내린다. statusCode 는 여기서 "
                    "바꾸지 않는다 — 폐기는 :dispose 가, 사용 중지는 :deactivate 가 받는다. "
                    "lastCalibrationDate·calibrationDueDate 도 받지 않는다 — 검교정 이력 "
                    "등록(W-05-10)이 정한다. 근거: 공유계약 B-4·B-13·B-16"),
    "properties": dict(
        {"equipmentCode": prop("string", "PRS-01", maxLength=50)},
        **EQUIPMENT_WRITE_PROPS),
}
SCHEMAS["EquipmentHierarchy"] = {
    "type": "object",
    "required": ["plantName", "groupNames", "equipmentName", "groupAssigned"],
    "description": ("계층 텍스트의 재료. 화면이 「공장 > 상위 그룹 > 하위 그룹 > 설비」로 "
                    "잇는다. 근거: W-05-12 §5-3 · DR-004"),
    "properties": {
        "plantName": prop("string", "호치민공장"),
        "groupNames": {"type": "array", "items": {"type": "string"},
                       "description": "최상위부터 차례로. 소속 그룹이 없으면 빈 배열"},
        "equipmentName": prop("string", "프레스 1호기"),
        "groupAssigned": prop("boolean", True,
                              description=("거짓이면 계층이 공장까지만 나온다. 화면은 이것을 "
                                           "빈칸으로 두지 않고 「소속 그룹 없음」으로 밝힌다")),
    },
}
SCHEMAS["EquipmentDetailResponse"] = {
    "type": "object",
    "required": ["equipment", "editability", "hierarchy"],
    "properties": {
        "equipment": {"$ref": "#/components/schemas/Equipment"},
        "editability": {"$ref": "#/components/schemas/Editability"},
        "hierarchy": {"$ref": "#/components/schemas/EquipmentHierarchy"},
    },
}

# ── 설비 점검 항목 마스터 ────────────────────────────────────────────────────
INSPECTION_ITEM_PROPS = {
    "itemCode": prop("string", "DAILY-01", maxLength=50),
    "itemName": prop("string", "안전커버 파손 여부", maxLength=200),
    "inspectionTypeCode": prop(
        "string", "DAILY", maxLength=50,
        description="점검 유형 — 일상 · 정기 · 보전"),
    "judgmentMethodCode": prop(
        "string", "VISUAL", maxLength=50,
        description="판정 방식 — 육안(합/NG) 또는 측정값. 측정값이면 단위·상하한이 함께 필요하다"),
    "uomId": nullable("integer", 1001, format="int64", description="측정 단위"),
    "lowerLimit": nullable("number", 0.5, description="측정 하한"),
    "upperLimit": nullable("number", 1.5, description="측정 상한"),
    "requiredFlag": prop("boolean", True, default=True,
                         description="참이면 이 항목을 판정해야 점검을 완료할 수 있다"),
    "inspectionPoint": nullable("string", "전면 커버 힌지", maxLength=200,
                                description="점검부위"),
    "sequenceNo": prop("integer", 1, minimum=1, description="표시 순서"),
    "isActive": prop("boolean", True, default=True),
}
SCHEMAS["EquipmentInspectionItem"] = {
    "type": "object",
    "required": ["equipmentInspectionItemId", "plantId", "itemCode", "itemName",
                 "inspectionTypeCode", "judgmentMethodCode", "requiredFlag",
                 "sequenceNo", "isActive"],
    "description": ("설비 점검 항목. 품질 검사 항목과 모양이 닮았으나 다른 자원이다 — "
                    "소유(설비담당)·대상(설비)·쓰임(작업 시작 통제)이 다르다. "
                    "근거: W-05-12 §4-C-1"),
    "x-internal-note": MODEL_GAP,
    "properties": dict(
        {"equipmentInspectionItemId": prop("integer", 1001, format="int64"),
         "plantId": prop("integer", 1001, format="int64")},
        **INSPECTION_ITEM_PROPS),
}
SCHEMAS["EquipmentInspectionItemCreate"] = {
    "type": "object",
    "required": ["plantId", "itemCode", "itemName", "inspectionTypeCode",
                 "judgmentMethodCode", "requiredFlag", "sequenceNo"],
    "properties": dict({"plantId": prop("integer", 1001, format="int64")},
                       **{k: v for k, v in INSPECTION_ITEM_PROPS.items() if k != "isActive"}),
}
SCHEMAS["EquipmentInspectionItemUpdate"] = {
    "type": "object",
    "required": ["itemName", "inspectionTypeCode", "judgmentMethodCode",
                 "requiredFlag", "sequenceNo", "isActive"],
    "description": ("itemCode 는 참조가 0일 때만 보낼 수 있다 — 상세 조회의 editability "
                    "가 가부와 사유를 함께 내린다. 근거: 공유계약 B-4"),
    "properties": dict(INSPECTION_ITEM_PROPS),
}
SCHEMAS["EquipmentInspectionItemDetailResponse"] = {
    "type": "object",
    "required": ["equipmentInspectionItem", "editability", "assignmentCount"],
    "properties": {
        "equipmentInspectionItem": {"$ref": "#/components/schemas/EquipmentInspectionItem"},
        "editability": {"$ref": "#/components/schemas/Editability"},
        "assignmentCount": prop("integer", 8,
                                description="이 항목이 부여된 설비·그룹 건수"),
    },
}

# ── 점검 항목 부여 ───────────────────────────────────────────────────────────
CYCLE_PROPS = {
    "cycleTypeCode": prop("string", "DAY", maxLength=50,
                          description="주기 단위 — 일 · 주 · 월"),
    "cycleInterval": prop("integer", 1, minimum=1, description="주기 간격"),
    "cycleBaseDate": nullable("string", "2026-08-01", format="date",
                              description="주기 기준일. 비면 부여일이 기준이 된다"),
}
SCHEMAS["InspectionItemAssignment"] = {
    "type": "object",
    "required": ["equipmentInspectionItemId", "itemCode", "itemName",
                 "inspectionTypeCode", "judgmentMethodCode", "requiredFlag",
                 "sequenceNo", "cycleTypeCode", "cycleInterval", "isActive"],
    "description": ("설비 또는 설비 그룹에 붙은 점검 항목 한 건. 항목 정의는 마스터가, "
                    "주기는 부여가 갖는다. 근거: W-05-12 §4-C-2 · 공유계약 B-6"),
    "x-internal-note": MODEL_GAP,
    "properties": dict(
        {"equipmentInspectionItemId": prop("integer", 1001, format="int64"),
         "itemCode": prop("string", "DAILY-01", maxLength=50),
         "itemName": prop("string", "안전커버 파손 여부", maxLength=200),
         "inspectionTypeCode": prop("string", "DAILY", maxLength=50),
         "judgmentMethodCode": prop("string", "VISUAL", maxLength=50),
         "uomId": nullable("integer", 1001, format="int64"),
         "lowerLimit": nullable("number", 0.5),
         "upperLimit": nullable("number", 1.5),
         "requiredFlag": prop("boolean", True),
         "inspectionPoint": nullable("string", "전면 커버 힌지", maxLength=200),
         "sequenceNo": prop("integer", 1, minimum=1),
         "isActive": prop("boolean", True, default=True)},
        **CYCLE_PROPS),
}
SCHEMAS["InspectionItemAssignmentInput"] = {
    "type": "object",
    "required": ["equipmentInspectionItemId", "cycleTypeCode", "cycleInterval"],
    "properties": dict(
        {"equipmentInspectionItemId": prop("integer", 1001, format="int64"),
         "isActive": prop("boolean", True, default=True)},
        **CYCLE_PROPS),
}
SCHEMAS["InspectionItemAssignmentUpdate"] = {
    "type": "object",
    "required": ["items"],
    "description": ("부여 묶음을 통째로 교체한다 — 보내지 않은 항목은 부여에서 빠진다. "
                    "근거: W-05-12 §5-1 「점검 항목 부여 편집」"),
    "properties": {
        "items": {"type": "array",
                  "items": {"$ref": "#/components/schemas/InspectionItemAssignmentInput"}},
    },
}
SCHEMAS["InspectionItemAssignmentList"] = {
    "type": "object",
    "required": ["items"],
    "properties": {
        "items": {"type": "array",
                  "items": {"$ref": "#/components/schemas/InspectionItemAssignment"}},
    },
}
SCHEMAS["EquipmentInspectionItemAssignmentsResponse"] = {
    "type": "object",
    "required": ["assigned", "effective", "resolvedFromLevelCode"],
    "description": ("설비 하나의 점검 항목. assigned 는 이 설비에 «직접» 붙은 것이고, "
                    "effective 는 해석 규칙을 적용한 결과다 — 설비에 부여가 있으면 그것, "
                    "없으면 소속 그룹의 것, 둘 다 없으면 점검 대상이 아니다. "
                    "설계 규칙: 가장 가까운 것이 이긴다 — 공유계약 B-17"),
    "properties": {
        "assigned": {"type": "array",
                     "items": {"$ref": "#/components/schemas/InspectionItemAssignment"}},
        "effective": {"type": "array",
                      "items": {"$ref": "#/components/schemas/InspectionItemAssignment"}},
        "resolvedFromLevelCode": prop(
            "string", "EQUIPMENT_GROUP",
            enum=["EQUIPMENT", "EQUIPMENT_GROUP", "NONE"],
            description=("effective 가 어느 층에서 왔는가. NONE 이면 점검 대상이 아니며 "
                         "화면은 입력을 열지 않는다")),
        "resolvedFromGroupId": nullable(
            "integer", 1001, format="int64",
            description="EQUIPMENT_GROUP 에서 왔을 때 그 그룹"),
    },
}

# ── 툴·금형·지그 ────────────────────────────────────────────────────────────
MOLD_WRITE_PROPS = {
    "moldName": prop("string", "하우징 프레스 금형", maxLength=200),
    "toolTypeCode": prop(
        "string", "MOLD", maxLength=50,
        description=("도구 유형 — 금형 · 지그 · 그 밖의 도구. 요구가 「모든 도구」라 "
                     "유형 축을 둔다")),
    "cavityCount": prop("integer", 4, minimum=1, default=1,
                        description="캐비티 수. 금형이 아니면 뜻이 없다"),
    "guaranteedShotCount": nullable(
        "integer", 500000, format="int64", minimum=0,
        description=("적정타수. 비어 있으면 사용 가능 타수를 산출할 수 없고 "
                     "예방보전 트리거의 타발수 축이 서지 않는다 — 0 으로 채우지 않는다")),
}
SCHEMAS["Mold"] = {
    "x-source-table": "mdm.mold",
    "type": "object",
    "required": ["moldId", "plantId", "moldCode", "moldName", "toolTypeCode",
                 "cavityCount", "currentShotCount", "statusCode", "isActive"],
    "description": ("툴·금형·지그 마스터. 테이블 이름은 금형이지만 담는 것은 모든 도구이며 "
                    "toolTypeCode 가 가른다. 근거: W-05-13 §3-3"),
    "x-internal-note": ("toolTypeCode 는 물리 모델에 없다 — 계약이 먼저 선다. 테이블 이름을 "
                        "바꾸지 않는 근거는 W-05-13 §3-3(참조 4곳을 함께 고칠 값이 없다). "
                        "작업 통지 = omf-mes#67"),
    "properties": {
        "moldId": prop("integer", 1001, format="int64", **{"x-source-column": "mold_id"}),
        "plantId": prop("integer", 1001, format="int64", **{"x-source-column": "plant_id"}),
        "moldCode": prop("string", "MLD-0207", maxLength=50,
                         description="uq_mold(plant_id, mold_code)",
                         **{"x-source-column": "mold_code"}),
        "moldName": prop("string", "하우징 프레스 금형", maxLength=200,
                         **{"x-source-column": "mold_name"}),
        "toolTypeCode": prop("string", "MOLD", maxLength=50,
                             description="도구 유형 — 금형 · 지그 · 그 밖의 도구"),
        "cavityCount": prop("integer", 4, minimum=1, default=1,
                            **{"x-source-column": "cavity_count"}),
        "guaranteedShotCount": nullable("integer", 500000, format="int64", minimum=0,
                                        **{"x-source-column": "guaranteed_shot_count"}),
        "currentShotCount": prop(
            "integer", 128400, format="int64", minimum=0, default=0,
            description=("누계 타발수. 읽기 전용이다 — 더하는 것은 툴 사용실적 입력이고 "
                         "되돌리는 것은 툴 예방보전 실적 등록이다"),
            **{"x-source-column": "current_shot_count"}),
        "availableShotCount": nullable(
            "integer", 371600, format="int64",
            description=("사용 가능 타수 = 적정타수 − 누계 타발수. 서버가 계산한다. "
                         "적정타수가 비어 있으면 null 이고 화면은 「산출 불가」로 그린다 — "
                         "0 으로 채우지 않는다")),
        "statusCode": prop(
            "string", "IN_SERVICE", maxLength=50,
            description=("자산 수명주기 — 운용 또는 폐기 두 값. 고장·보전 중·비가동은 "
                         "거래가 만드는 조건이라 마스터에 적지 않는다"),
            **{"x-source-column": "status_code"}),
        "isActive": prop("boolean", True, default=True, **{"x-source-column": "is_active"}),
    },
}
SCHEMAS["MoldCreate"] = {
    "type": "object",
    "required": ["plantId", "moldCode", "moldName", "toolTypeCode", "cavityCount"],
    "properties": dict(
        {"plantId": prop("integer", 1001, format="int64"),
         "moldCode": prop("string", "MLD-0207", maxLength=50)},
        **MOLD_WRITE_PROPS),
}
SCHEMAS["MoldUpdate"] = {
    "type": "object",
    "required": ["moldName", "toolTypeCode", "cavityCount"],
    "description": ("moldCode 는 상세 조회의 editability 가 허락할 때만 보낸다 — 참조가 "
                    "0이어도 라벨이 발행됐으면 잠긴다. currentShotCount 는 받지 않는다 — "
                    "실적이 정한다. 근거: W-05-13 §5-2·§5-4 · 공유계약 B-4·B-13"),
    "properties": dict({"moldCode": prop("string", "MLD-0207", maxLength=50)},
                       **MOLD_WRITE_PROPS),
}
SCHEMAS["MoldDetailResponse"] = {
    "type": "object",
    "required": ["mold", "editability", "labelIssueCount"],
    "properties": {
        "mold": {"$ref": "#/components/schemas/Mold"},
        "editability": {"$ref": "#/components/schemas/Editability"},
        "labelIssueCount": prop(
            "integer", 2,
            description=("이 툴로 발행된 라벨 회차 수. 1 이상이면 코드가 현장에 물리적으로 "
                         "나가 있어 참조 건수와 무관하게 코드를 잠근다")),
    },
}

# ── 예비품 ───────────────────────────────────────────────────────────────────
SCHEMAS["SparePart"] = {
    "type": "object",
    "required": ["sparePartId", "plantId", "sparePartCode", "sparePartName", "isActive"],
    "description": ("예비품 마스터. 품목 마스터와 통합하지 않는다 — 별도 마스터가 "
                    "확정이다. 근거: W-06-08 §2·§3-3"),
    "x-internal-note": (MODEL_GAP + " 규격·단가·적정재고·교체주기 같은 그 밖의 속성은 "
                        "근거가 없어 «적지 않았다» — 현행 예비품 엑셀 실물을 수집해야 "
                        "정해진다(W-06-08 §4-A). 빈칸이 아니라 「아직 근거가 없다」다."),
    "properties": {
        "sparePartId": prop("integer", 1001, format="int64"),
        "plantId": prop("integer", 1001, format="int64"),
        "sparePartCode": prop("string", "SP-0142", maxLength=50,
                              description="공장 안에서 유일하다"),
        "sparePartName": prop("string", "유압 실린더 씰", maxLength=200),
        "isActive": prop("boolean", True, default=True),
    },
}
SCHEMAS["SparePartCreate"] = {
    "type": "object",
    "required": ["plantId", "sparePartCode", "sparePartName"],
    "properties": {
        "plantId": prop("integer", 1001, format="int64"),
        "sparePartCode": prop("string", "SP-0142", maxLength=50),
        "sparePartName": prop("string", "유압 실린더 씰", maxLength=200),
    },
}
SCHEMAS["SparePartUpdate"] = {
    "type": "object",
    "required": ["sparePartName"],
    "description": ("sparePartCode 는 참조가 0일 때만 보낼 수 있다 — 상세 조회의 "
                    "editability 가 가부와 사유를 함께 내린다. 근거: 공유계약 B-4"),
    "properties": {
        "sparePartCode": prop("string", "SP-0142", maxLength=50),
        "sparePartName": prop("string", "유압 실린더 씰", maxLength=200),
    },
}
SCHEMAS["SparePartDetailResponse"] = {
    "type": "object",
    "required": ["sparePart", "editability", "mappedEquipmentCount"],
    "properties": {
        "sparePart": {"$ref": "#/components/schemas/SparePart"},
        "editability": {"$ref": "#/components/schemas/Editability"},
        "mappedEquipmentCount": prop("integer", 6,
                                     description="이 예비품이 매핑된 설비 대수"),
    },
}
SCHEMAS["SparePartEquipmentMapping"] = {
    "type": "object",
    "required": ["equipmentId", "equipmentCode", "equipmentName"],
    "description": "예비품이 쓰이는 설비 한 대. 예비품과 설비는 다대다다",
    "x-internal-note": MODEL_GAP,
    "properties": {
        "equipmentId": prop("integer", 1001, format="int64"),
        "equipmentCode": prop("string", "PRS-01", maxLength=50),
        "equipmentName": prop("string", "프레스 1호기", maxLength=200),
    },
}
SCHEMAS["SparePartEquipmentMappingList"] = {
    "type": "object",
    "required": ["items"],
    "properties": {
        "items": {"type": "array",
                  "items": {"$ref": "#/components/schemas/SparePartEquipmentMapping"}},
    },
}
SCHEMAS["SparePartEquipmentMappingUpdate"] = {
    "type": "object",
    "required": ["equipmentIds"],
    "description": "매핑을 통째로 교체한다 — 보내지 않은 설비는 매핑에서 빠진다",
    "properties": {
        "equipmentIds": {"type": "array",
                         "items": {"type": "integer", "format": "int64"}},
    },
}

# ── 작업 캘린더 ──────────────────────────────────────────────────────────────
SCHEMAS["WorkCalendar"] = {
    "type": "object",
    "required": ["workCalendarId", "calendarCode", "calendarName", "isActive"],
    "description": ("작업 캘린더. 가동·휴무를 날짜 단위로 갖고, 어느 공장·설비 그룹이 "
                    "이것을 따르는지는 적용이 정한다. 근거: W-05-09 §5-A · 결정 03"),
    "x-internal-note": MODEL_GAP,
    "properties": {
        "workCalendarId": prop("integer", 1001, format="int64"),
        "calendarCode": prop("string", "CAL-HCM-2026", maxLength=50,
                             description="전역에서 유일하다"),
        "calendarName": prop("string", "호치민공장 2026 기본", maxLength=200),
        "isActive": prop("boolean", True, default=True),
    },
}
SCHEMAS["WorkCalendarCreate"] = {
    "type": "object",
    "required": ["calendarCode", "calendarName"],
    "properties": {
        "calendarCode": prop("string", "CAL-HCM-2026", maxLength=50),
        "calendarName": prop("string", "호치민공장 2026 기본", maxLength=200),
    },
}
SCHEMAS["WorkCalendarUpdate"] = {
    "type": "object",
    "required": ["calendarName"],
    "description": ("calendarCode 는 참조가 0일 때만 보낼 수 있다 — 상세 조회의 "
                    "editability 가 가부와 사유를 함께 내린다. 근거: 공유계약 B-4"),
    "properties": {
        "calendarCode": prop("string", "CAL-HCM-2026", maxLength=50),
        "calendarName": prop("string", "호치민공장 2026 기본", maxLength=200),
    },
}
SCHEMAS["WorkCalendarDetailResponse"] = {
    "type": "object",
    "required": ["workCalendar", "editability", "applicationCount"],
    "properties": {
        "workCalendar": {"$ref": "#/components/schemas/WorkCalendar"},
        "editability": {"$ref": "#/components/schemas/Editability"},
        "applicationCount": prop("integer", 3,
                                 description="이 캘린더를 따르는 공장·설비 그룹 수"),
    },
}
DAY_PROPS = {
    "calendarDate": prop("string", "2026-08-15", format="date"),
    "dayTypeCode": prop(
        "string", "HOLIDAY",
        enum=["WORKING", "HOLIDAY", "PARTIAL"],
        description=("가동 · 휴무 · 부분 가동. 부분 가동은 반일 근무를 담는다 — 휴무로 "
                     "처리하면 조업시간이 통째로 빠져 가동률이 틀린다")),
    "startTime": nullable("string", "08:00", description="부분 가동일 때만 쓴다"),
    "endTime": nullable("string", "12:00", description="부분 가동일 때만 쓴다"),
    "reasonCode": nullable("string", "PUBLIC_HOLIDAY", maxLength=50,
                           description="공통코드 — 값 목록이 확정되지 않았다"),
    "remarks": nullable("string", "독립기념일"),
}
SCHEMAS["WorkCalendarDay"] = {
    "type": "object",
    "required": ["calendarDate", "dayTypeCode"],
    "description": "캘린더 하루. 키는 캘린더와 일자다 — 결정 03",
    "x-internal-note": MODEL_GAP,
    "properties": dict(DAY_PROPS),
}
SCHEMAS["WorkCalendarDayList"] = {
    "type": "object",
    "required": ["items"],
    "properties": {
        "items": {"type": "array",
                  "items": {"$ref": "#/components/schemas/WorkCalendarDay"}},
    },
}
SCHEMAS["WorkCalendarDayUpdate"] = {
    "type": "object",
    "required": ["days"],
    "description": ("보낸 날짜만 덮어쓴다 — 보내지 않은 날은 그대로 둔다. 요일 일괄과 "
                    "기간 일괄도 이 경로를 쓴다. 화면이 바뀔 날짜를 미리 펼쳐 보이고 "
                    "확인을 받으므로, 규칙(「매주 일요일」)이 아니라 날짜 목록을 보낸다"),
    "properties": {
        "days": {"type": "array",
                 "items": {"$ref": "#/components/schemas/WorkCalendarDay"}},
    },
}
SCHEMAS["WorkCalendarDayUpdateResult"] = {
    "type": "object",
    "required": ["appliedCount"],
    "properties": {
        "appliedCount": prop("integer", 52, description="덮어쓴 날짜 수"),
    },
}
SCHEMAS["WorkCalendarApplication"] = {
    "type": "object",
    "required": ["targetTypeCode", "targetId", "targetName", "workCalendarId",
                 "calendarCode"],
    "description": ("어느 대상이 어느 캘린더를 따르는가. 대상은 공장 또는 설비 그룹이며 "
                    "설비 단위는 두지 않는다. 한 공장의 기본 캘린더는 하나뿐이고 "
                    "바꾸는 것은 서버가 한 트랜잭션으로 처리한다. 근거: W-05-09 §5-C·§5-2"),
    "x-internal-note": MODEL_GAP,
    "properties": {
        "targetTypeCode": prop(
            "string", "PLANT", enum=["PLANT", "EQUIPMENT_GROUP"],
            description=("대상 유형. 한 칸이 상황에 따라 다른 표를 가리키므로 대응을 "
                         "계약이 정한다 — PLANT → mdm.plant · "
                         "EQUIPMENT_GROUP → mdm.production_line")),
        "targetId": prop("integer", 1001, format="int64",
                         description="PLANT 이면 공장, EQUIPMENT_GROUP 이면 설비 그룹"),
        "targetName": prop("string", "호치민공장"),
        "workCalendarId": prop("integer", 1001, format="int64"),
        "calendarCode": prop("string", "CAL-HCM-2026", maxLength=50),
    },
}
SCHEMAS["WorkCalendarApplicationUpdate"] = {
    "type": "object",
    "required": ["targetTypeCode", "targetId"],
    "description": ("대상 하나의 적용을 지정하거나 해제한다. workCalendarId 를 비우면 "
                    "해제이며 그 대상은 상위 층을 따르게 된다"),
    "properties": {
        "targetTypeCode": prop(
            "string", "PLANT", enum=["PLANT", "EQUIPMENT_GROUP"],
            description=("PLANT → mdm.plant · EQUIPMENT_GROUP → mdm.production_line")),
        "targetId": prop("integer", 1001, format="int64"),
        "workCalendarId": nullable("integer", 1001, format="int64"),
    },
}
SCHEMAS["WorkCalendarResolutionStep"] = {
    "type": "object",
    "required": ["levelCode", "targetId", "targetName", "hasApplication"],
    "description": "해석이 훑은 층 하나. 가까운 층부터 차례로 담긴다",
    "properties": {
        "levelCode": prop("string", "EQUIPMENT_GROUP",
                          enum=["EQUIPMENT_GROUP", "PLANT"]),
        "targetId": prop("integer", 1001, format="int64"),
        "targetName": prop("string", "프레스라인 A"),
        "hasApplication": prop("boolean", False,
                               description="이 층에 지정이 있으면 여기서 멈춘다"),
    },
}
SCHEMAS["WorkCalendarEffectiveResponse"] = {
    "type": "object",
    "required": ["equipmentId", "equipmentName", "steps"],
    "description": ("이 설비가 결국 어느 캘린더를 따르는가와 그렇게 정해진 경로. "
                    "설계 규칙은 「가장 가까운 것이 이긴다」이며, 규칙만으로는 결과가 "
                    "안 보여 화면이 이것을 그린다. 근거: W-05-09 §5-3 · 공유계약 B-17"),
    "properties": {
        "equipmentId": prop("integer", 1001, format="int64"),
        "equipmentName": prop("string", "프레스 1호기"),
        "steps": {"type": "array",
                  "items": {"$ref": "#/components/schemas/WorkCalendarResolutionStep"}},
        "workCalendarId": nullable("integer", 1001, format="int64",
                                   description="어느 층에도 지정이 없으면 null 이다"),
        "calendarCode": nullable("string", "CAL-HCM-2026", maxLength=50),
        "resolvedFromLevelCode": nullable(
            "string", "PLANT",
            description=("EQUIPMENT_GROUP 또는 PLANT. null 이면 어느 층에도 지정이 없어 "
                         "따르는 캘린더가 없다 — 화면이 그 사실을 밝힌다")),
    },
}

# ── 엑셀 업로드 ──────────────────────────────────────────────────────────────
# ⭐ 결과 스키마를 새로 만들지 않는다 — BatchResult 가 이미 「부분 실패를 허용하고
#    거부 건만 사유와 함께 돌려준다」를 담고 있다. 같은 것을 두 벌 두면 갱신이
#    두 곳에 필요해진다.
IMPORT_RESULT_DESC = ("처리 결과. BatchResult.failed[].index 는 엑셀 자료 행의 순번이다"
                      "(머리글 제외 0부터)")


def import_body(what: str) -> dict:
    return {"required": True,
            "content": {"multipart/form-data": {"schema": {
                "type": "object",
                "required": ["file"],
                "properties": {
                    "file": {"type": "string", "format": "binary",
                             "description": "%s 엑셀 파일" % what},
                }}}}}


# ─────────────────────────────────────────────────────────────────────────────
# 경로
# ─────────────────────────────────────────────────────────────────────────────

def master_collection(tag, title, list_schema, create_schema, basis,
                      extra_params=None, internal=None) -> dict:
    params = [{"name": "q", "in": "query", "schema": {"type": "string"},
               "description": "코드·명칭 검색"}]
    params += (extra_params or [])
    params += [{"name": "includeInactive", "in": "query",
                "schema": {"type": "boolean", "default": False}}]
    params += paging_params()
    get = {"tags": [tag], "summary": "%s 목록" % title,
           "description": "유효성 판정은 서버가 하며 기본은 유효한 것만 내린다. 근거: %s" % basis,
           "parameters": params,
           "responses": {"200": page_response(list_schema)}}
    post = {"tags": [tag], "summary": "%s 등록" % title,
            "description": "근거: %s" % basis,
            "parameters": [IDEM],
            "requestBody": {"required": True,
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/%s" % create_schema}}}},
            "responses": {"201": ok("등록됨", list_schema),
                          "400": err("검증 실패 — 유일 위반이면 유일 범위를 담아 돌려준다"),
                          "403": err("권한 없음")}}
    out = {"get": get, "post": post}
    if internal:
        out["get"]["x-internal-note"] = internal
        out["post"]["x-internal-note"] = internal
    return out


def master_item(tag, title, id_param, detail_schema, update_schema, row_schema,
                basis, internal=None) -> dict:
    out = {
        "parameters": [path_param(id_param)],
        "get": {"tags": [tag], "summary": "%s 상세" % title,
                "description": ("코드 수정 가부와 사유를 응답이 함께 내린다 — 화면이 "
                                "따로 세지 않는다. 근거: %s" % basis),
                "responses": {"200": ok("상세", detail_schema, etag=True)}},
        "put": {"tags": [tag], "summary": "%s 수정" % title,
                "description": "근거: %s" % basis,
                "parameters": [IDEM, IFMATCH],
                "requestBody": {"required": True,
                                "content": {"application/json": {
                                    "schema": {"$ref": "#/components/schemas/%s" % update_schema}}}},
                "responses": {"200": ok("수정됨", row_schema, etag=True),
                              "400": err("검증 실패"),
                              "403": err("권한 없음"),
                              "409": conflict()}},
    }
    if internal:
        out["get"]["x-internal-note"] = internal
        out["put"]["x-internal-note"] = internal
    return out


def verb(tag, summary, id_param, row_schema, description) -> dict:
    return {
        "parameters": [path_param(id_param)],
        "post": {"tags": [tag], "summary": summary,
                 "description": description,
                 "parameters": [IDEM, IFMATCH],
                 "responses": {"200": ok("처리됨", row_schema, etag=True),
                               "400": err("업무 규칙 위반 — 상태 잠김·참조 존재"),
                               "403": err("권한 없음"),
                               "409": conflict()}},
    }


DEACTIVATE_DESC = ("물리 삭제는 제공하지 않는다. 참조가 있으면 확인 문구에 건수를 함께 "
                   "보인 뒤 부른다. 근거: 공유계약 B-4")
DISPOSE_DESC = ("자산을 폐기 처리한다. 사용 중지와 «다른 축»이다 — 사용 중지는 목록에서 "
                "감추는 것이고 폐기는 자산이 끝난 것이다. 폐기된 뒤에는 다시 불러와도 "
                "편집이 풀리지 않는다. 근거: 공유계약 B-16")

PATHS = {}

# 설비 그룹
PATHS["/mdm/equipment-groups"] = master_collection(
    "mdm", "설비 그룹", "EquipmentGroup", "EquipmentGroupCreate", "W-05-12 §5-1",
    extra_params=[{"name": "plantId", "in": "query",
                   "schema": {"type": "integer", "format": "int64"}},
                  {"name": "parentGroupId", "in": "query",
                   "schema": {"type": "integer", "format": "int64"},
                   "description": "하위 그룹만 본다"}])
PATHS["/mdm/equipment-groups/{equipmentGroupId}"] = master_item(
    "mdm", "설비 그룹", "equipmentGroupId", "EquipmentGroupDetailResponse",
    "EquipmentGroupUpdate", "EquipmentGroup", "W-05-12 §4-A",
    internal=("상위 그룹 순환(A→B→A)은 물리 제약이 막지 않는다 — 직계 자기참조만 막힌다. "
              "서버가 진다(공유계약 A-9 등급 2). mdm.department 도 같은 형태라 서버 공통 "
              "검증으로 한 번에 간다."))
PATHS["/mdm/equipment-groups/{equipmentGroupId}:deactivate"] = verb(
    "mdm", "설비 그룹 사용 중지", "equipmentGroupId", "EquipmentGroup", DEACTIVATE_DESC)

# 설비
PATHS["/mdm/equipments/{equipmentId}"] = master_item(
    "mdm", "설비", "equipmentId", "EquipmentDetailResponse", "EquipmentUpdate",
    "Equipment", "W-05-12 §4-B · W-05-11 §4-A")
PATHS["/mdm/equipments/{equipmentId}:deactivate"] = verb(
    "mdm", "설비 사용 중지", "equipmentId", "Equipment", DEACTIVATE_DESC)
PATHS["/mdm/equipments/{equipmentId}:dispose"] = verb(
    "mdm", "설비 폐기 처리", "equipmentId", "Equipment", DISPOSE_DESC)

# 점검 항목 마스터
PATHS["/mdm/equipment-inspection-items"] = master_collection(
    "mdm", "설비 점검 항목", "EquipmentInspectionItem", "EquipmentInspectionItemCreate",
    "W-05-12 §4-C-1",
    extra_params=[{"name": "plantId", "in": "query",
                   "schema": {"type": "integer", "format": "int64"}},
                  {"name": "inspectionTypeCode", "in": "query",
                   "schema": {"type": "string"},
                   "description": "점검 유형으로 거른다"}],
    internal=("품질 검사 항목과 경로를 나눈 이유는 W-05-12 §4-C-1 — 소유·대상·쓰임이 다르다. "
              "2단계 규약은 /mdm/inspection-items 로 적었으나 이 계약에 품질 검사 항목이 "
              "이미 있어 이름을 갈랐다."))
PATHS["/mdm/equipment-inspection-items/{equipmentInspectionItemId}"] = master_item(
    "mdm", "설비 점검 항목", "equipmentInspectionItemId",
    "EquipmentInspectionItemDetailResponse", "EquipmentInspectionItemUpdate",
    "EquipmentInspectionItem", "W-05-12 §4-C-1",
    internal="사용 중지는 별도 경로를 두지 않고 isActive 로 받는다 — 화면에 버튼이 없다.")

# 점검 항목 부여
PATHS["/mdm/equipment-groups/{equipmentGroupId}/inspection-items"] = {
    "parameters": [path_param("equipmentGroupId")],
    "get": {"tags": ["mdm"], "summary": "설비 그룹의 점검 항목 부여",
            "description": "근거: W-05-12 §4-C-2",
            "responses": {"200": ok("부여 목록", "InspectionItemAssignmentList", etag=True)}},
    "put": {"tags": ["mdm"], "summary": "설비 그룹의 점검 항목 부여 교체",
            "description": ("묶음을 통째로 교체한다. 설비·그룹을 오가며 편집하는 자리라 "
                            "저장 충돌 보호를 붙인다. 토큰은 같은 경로의 조회가 내려주는 "
                            "ETag 다. 근거: W-05-12 §5-1 · 공유계약 G-30"),
            "parameters": [IDEM, IFMATCH],
            "requestBody": {"required": True,
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/InspectionItemAssignmentUpdate"}}}},
            "responses": {"200": ok("교체됨", "InspectionItemAssignmentList", etag=True),
                          "400": err("검증 실패"),
                          "403": err("권한 없음"),
                          "409": conflict()}},
}
PATHS["/mdm/equipments/{equipmentId}/inspection-items"] = {
    "parameters": [path_param("equipmentId")],
    "get": {"tags": ["mdm"], "summary": "설비의 점검 항목 — 직접 부여와 해석 결과",
            "description": ("설비 점검 입력 화면이 이 경로의 effective 를 읽는다. "
                            "근거: W-05-12 §4-C-2 · M-05-01 §4"),
            "responses": {"200": ok("부여와 해석 결과",
                                    "EquipmentInspectionItemAssignmentsResponse", etag=True)}},
    "put": {"tags": ["mdm"], "summary": "설비의 점검 항목 부여 교체",
            "description": ("묶음을 통째로 교체한다. 빈 목록을 보내면 이 설비의 직접 부여가 "
                            "사라지고 소속 그룹의 것을 따르게 된다. 토큰은 같은 경로의 "
                            "조회가 내려주는 ETag 다. 근거: W-05-12 §5-1 · 공유계약 G-30"),
            "parameters": [IDEM, IFMATCH],
            "requestBody": {"required": True,
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/InspectionItemAssignmentUpdate"}}}},
            "responses": {"200": ok("교체됨", "EquipmentInspectionItemAssignmentsResponse",
                                    etag=True),
                          "400": err("검증 실패"),
                          "403": err("권한 없음"),
                          "409": conflict()}},
}

# 툴
PATHS["/mdm/molds"] = master_collection(
    "mdm", "툴", "Mold", "MoldCreate", "W-05-13 §5-1",
    extra_params=[{"name": "plantId", "in": "query",
                   "schema": {"type": "integer", "format": "int64"}},
                  {"name": "toolTypeCode", "in": "query", "schema": {"type": "string"},
                   "description": "도구 유형으로 거른다"},
                  {"name": "guaranteedShotCountMissing", "in": "query",
                   "schema": {"type": "boolean"},
                   "description": ("적정타수가 비어 있는 것만 본다. 비어 있으면 예방보전이 "
                                   "돌지 않으므로 채울 것을 한눈에 세는 자리다")}])
PATHS["/mdm/molds/{moldId}"] = master_item(
    "mdm", "툴", "moldId", "MoldDetailResponse", "MoldUpdate", "Mold", "W-05-13 §4-A")
PATHS["/mdm/molds/{moldId}:deactivate"] = verb(
    "mdm", "툴 사용 중지", "moldId", "Mold", DEACTIVATE_DESC)
PATHS["/mdm/molds/{moldId}:dispose"] = verb(
    "mdm", "툴 폐기 처리", "moldId", "Mold", DISPOSE_DESC)
PATHS["/mdm/molds:import"] = {
    "post": {"tags": ["mdm"], "summary": "툴 엑셀 올리기",
             "description": ("현행 엑셀 대장을 옮기는 경로다. 통째로 되돌리지 않고 "
                             "성공·실패 건수와 실패 행 목록을 돌려준다. 올리기가 만드는 "
                             "것은 마스터 행뿐이며 라벨을 자동으로 발행하지 않는다. "
                             "근거: W-05-13 §5-5"),
             "parameters": [IDEM],
             "requestBody": import_body("툴"),
             "responses": {"200": ok(IMPORT_RESULT_DESC, "BatchResult"),
                           "400": err("파일을 읽을 수 없다"),
                           "403": err("권한 없음")},
             "x-internal-note": ("전 계약에서 처음 두는 파일 올리기 경로다. 첨부(app.attachment)와 "
                                 "«다른 자리»로 정했다 — 첨부는 보관되는 파일이고 이것은 읽고 "
                                 "버리는 입력이다. 2단계 §12·3단계 §7 이 남긴 자리의 답이다.")},
}

# 예비품
PATHS["/mdm/spare-parts"] = master_collection(
    "mdm", "예비품", "SparePart", "SparePartCreate", "W-06-08 §5",
    extra_params=[{"name": "plantId", "in": "query",
                   "schema": {"type": "integer", "format": "int64"}},
                  {"name": "equipmentId", "in": "query",
                   "schema": {"type": "integer", "format": "int64"},
                   "description": "이 설비에 매핑된 예비품만 본다"}])
PATHS["/mdm/spare-parts/{sparePartId}"] = master_item(
    "mdm", "예비품", "sparePartId", "SparePartDetailResponse", "SparePartUpdate",
    "SparePart", "W-06-08 §4-A")
PATHS["/mdm/spare-parts/{sparePartId}:deactivate"] = verb(
    "mdm", "예비품 사용 중지", "sparePartId", "SparePart", DEACTIVATE_DESC)
PATHS["/mdm/spare-parts/{sparePartId}/equipments"] = {
    "parameters": [path_param("sparePartId")],
    "get": {"tags": ["mdm"], "summary": "예비품-설비 매핑",
            "description": "근거: W-06-08 §4-B",
            "responses": {"200": ok("매핑 목록", "SparePartEquipmentMappingList", etag=True)}},
    "put": {"tags": ["mdm"], "summary": "예비품-설비 매핑 교체",
            "description": ("묶음을 통째로 교체한다. 예비품을 오가며 편집하는 자리라 저장 "
                            "충돌 보호를 붙인다. 토큰은 같은 경로의 조회가 내려주는 ETag 다. "
                            "근거: 공유계약 G-30"),
            "parameters": [IDEM, IFMATCH],
            "requestBody": {"required": True,
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/SparePartEquipmentMappingUpdate"}}}},
            "responses": {"200": ok("교체됨", "SparePartEquipmentMappingList", etag=True),
                          "400": err("검증 실패"),
                          "403": err("권한 없음"),
                          "409": conflict()}},
}
PATHS["/mdm/spare-parts:import"] = {
    "post": {"tags": ["mdm"], "summary": "예비품 엑셀 올리기",
             "description": ("현행 엑셀 대장을 옮기는 경로다. 통째로 되돌리지 않고 성공·실패 "
                             "건수와 실패 행 목록을 돌려준다. 근거: W-06-08 §5"),
             "parameters": [IDEM],
             "requestBody": import_body("예비품"),
             "responses": {"200": ok(IMPORT_RESULT_DESC, "BatchResult"),
                           "400": err("파일을 읽을 수 없다"),
                           "403": err("권한 없음")},
             "x-internal-note": ("받을 열은 현행 예비품 엑셀 실물을 수집해야 정해진다"
                                 "(W-06-08 §4-A). 지금은 코드·명칭만 확실하다.")},
}

# 작업 캘린더
PATHS["/mdm/work-calendars"] = master_collection(
    "mdm", "작업 캘린더", "WorkCalendar", "WorkCalendarCreate", "W-05-09 §5-A")
PATHS["/mdm/work-calendars/{workCalendarId}"] = master_item(
    "mdm", "작업 캘린더", "workCalendarId", "WorkCalendarDetailResponse",
    "WorkCalendarUpdate", "WorkCalendar", "W-05-09 §5-A")
PATHS["/mdm/work-calendars/{workCalendarId}:deactivate"] = verb(
    "mdm", "작업 캘린더 사용 중지", "workCalendarId", "WorkCalendar", DEACTIVATE_DESC)
PATHS["/mdm/work-calendars/{workCalendarId}/days"] = {
    "parameters": [path_param("workCalendarId")],
    "get": {"tags": ["mdm"], "summary": "캘린더 일자 조회",
            "description": ("기간을 반드시 지정해 부른다 — 한 해가 365행이라 전량을 "
                            "내리지 않는다. 근거: W-05-09 §5-B · 공유계약 L-3"),
            "parameters": [
                {"name": "from", "in": "query", "required": True,
                 "schema": {"type": "string", "format": "date"}},
                {"name": "to", "in": "query", "required": True,
                 "schema": {"type": "string", "format": "date"}},
            ],
            "responses": {"200": ok("일자 목록", "WorkCalendarDayList")}},
    "put": {"tags": ["mdm"], "summary": "캘린더 일자 덮어쓰기",
            "description": ("보낸 날짜만 덮어쓴다. 「이 날 적용」·「요일 일괄」·「기간 일괄」이 "
                            "모두 이 경로를 쓴다. 근거: W-05-09 §5-5"),
            "parameters": [IDEM],
            "requestBody": {"required": True,
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/WorkCalendarDayUpdate"}}}},
            "responses": {"200": ok("덮어씀", "WorkCalendarDayUpdateResult"),
                          "400": err("검증 실패 — 부분 가동인데 시각이 비었거나 종료가 시작보다 빠르다"),
                          "403": err("권한 없음")},
            "x-internal-note": ("저장 충돌 보호를 붙이지 않았다 — 통째로 교체하는 저장이 "
                                "아니라 지정한 날만 덮어쓰는 형태라 공유계약 G-30 의 두 조건에 "
                                "닿지 않는다.")},
}
PATHS["/mdm/work-calendar-applications"] = {
    "get": {"tags": ["mdm"], "summary": "캘린더 적용 목록",
            "description": "근거: W-05-09 §5-C",
            "parameters": [
                {"name": "workCalendarId", "in": "query",
                 "schema": {"type": "integer", "format": "int64"}},
                {"name": "targetTypeCode", "in": "query",
                 "schema": {"type": "string", "enum": ["PLANT", "EQUIPMENT_GROUP"]}},
                {"name": "plantId", "in": "query",
                 "schema": {"type": "integer", "format": "int64"}},
            ] + paging_params(),
            "responses": {"200": page_response("WorkCalendarApplication", "적용 목록")}},
    "put": {"tags": ["mdm"], "summary": "캘린더 적용 지정·해제",
            "description": ("대상 하나의 적용을 정한다. 공장 기본을 바꾸면 옛 지정 해제와 새 "
                            "지정을 서버가 한 트랜잭션으로 처리한다 — 화면이 두 번 부르지 "
                            "않는다. 근거: W-05-09 §5-2 · 공유계약 A-6"),
            "parameters": [IDEM],
            "requestBody": {"required": True,
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/WorkCalendarApplicationUpdate"}}}},
            "responses": {"200": ok("지정됨", "WorkCalendarApplication"),
                          "204": {"description": "해제됨 — workCalendarId 를 비워 보냈을 때"},
                          "400": err("검증 실패"),
                          "403": err("권한 없음")}},
}
PATHS["/mdm/work-calendar-applications/effective"] = {
    "get": {"tags": ["mdm"], "summary": "이 설비가 따르는 캘린더와 그 경로",
            "description": ("설정 화면의 해석 미리보기가 쓴다. 근거: W-05-09 §5-3"),
            "parameters": [
                {"name": "equipmentId", "in": "query", "required": True,
                 "schema": {"type": "integer", "format": "int64"}},
            ],
            "responses": {"200": ok("해석 결과", "WorkCalendarEffectiveResponse")}},
}


# ─────────────────────────────────────────────────────────────────────────────
# 기존 스키마 손질
# ─────────────────────────────────────────────────────────────────────────────

EQUIPMENT_DESC = (
    "설비 마스터. 계측기도 설비의 한 종류이며 equipmentTypeCode 가 가른다 — "
    "계측기 전용 자원을 두지 않는 이유는 한 행을 두 경로가 쓰게 되기 때문이다"
    "(W-05-11 §3-2). 유효성 판정은 서버가 하며 기본은 유효한 것만 내린다. 과거 "
    "데이터 표시용은 includeInactive=true 로 켜고 isActive 표식을 함께 본다. "
    "statusCode 는 운용·폐기 두 값이다 — 고장·보전 중·비가동은 거래가 만드는 "
    "조건이라 마스터에 적지 않는다(W-05-12 §5-2). lastCalibrationDate·"
    "calibrationDueDate 는 읽기 전용이며 검교정 이력 등록이 정한다. "
    "근거: W-05-12 §4-B · W-05-11 §4-A · W-06-02 §4-C")

EQUIPMENT_ADDED = {
    "calibrationCycleTypeCode": nullable(
        "string", "MONTH", maxLength=50,
        description=("검교정 주기 단위. calibrationRequired 가 참이면 주기 두 칸이 "
                     "함께 필요하다 — 주기 없이는 차기 예정일을 산출할 수 없다")),
    "calibrationCycleInterval": nullable("integer", 12, minimum=1,
                                         description="검교정 주기 간격"),
    "precisionValue": nullable("number", 0.01, description="정밀도 수치"),
    "precisionUomId": nullable("integer", 1001, format="int64", description="정밀도 단위"),
}

EQUIPMENT_INTERNAL = (
    "검교정 주기·정밀도는 물리 모델에 없다 — 둘 다 개념모델 §4 가 명시한 계측기 속성이고 "
    "결정 06 의 「차기 검교정 예정일」이 성립하려면 주기가 반드시 필요하다. 계약이 먼저 "
    "선다. 작업 통지 = omf-mes#67. 조건부 필수(calibrationRequired 가 참이면 주기 필요)를 "
    "물리 제약이 막지 않아 서버가 진다 — 공유계약 A-9 등급 2.")

LINE_ID_DESC = ("소속 설비 그룹. /mdm/equipment-groups 의 equipmentGroupId 와 같은 값이다 — "
                "물리 모델의 이름이 production_line 이라 필드 이름이 그것을 따르고 있다. "
                "비어 있으면 계층 표시가 공장까지만 나온다")


def patch_equipment(spec: dict) -> None:
    eq = spec["components"]["schemas"]["Equipment"]
    eq["description"] = EQUIPMENT_DESC
    eq["x-internal-note"] = EQUIPMENT_INTERNAL
    eq["properties"]["productionLineId"]["description"] = LINE_ID_DESC
    eq["properties"]["statusCode"]["description"] = (
        "자산 수명주기 — 운용 또는 폐기 두 값")
    for name, definition in EQUIPMENT_ADDED.items():
        eq["properties"][name] = definition

    # 목록 조회에 계측기 화면이 쓸 거르개를 더한다.
    get = spec["paths"]["/mdm/equipments"]["get"]
    get["description"] = (
        "설비 선택 목록과 설비 마스터 화면이 함께 쓴다. 유효성 판정은 서버가 하며 기본은 "
        "유효한 것만 내린다. 과거 데이터 표시용은 includeInactive=true 로 켜고 isActive "
        "표식을 함께 본다. 계측기 화면은 equipmentTypeCode 로 거른다. "
        "근거: W-05-12 §5-1 · W-05-11 §3-2 · W-06-02 §4-C 지정 검사장비")
    names = {p["name"] for p in get["parameters"]}
    for extra in (
        {"name": "productionLineId", "in": "query",
         "schema": {"type": "integer", "format": "int64"},
         "description": "소속 설비 그룹으로 거른다"},
        {"name": "equipmentTypeCode", "in": "query", "schema": {"type": "string"},
         "description": "설비 유형으로 거른다 — 계측기 화면이 이것을 쓴다"},
        {"name": "calibrationRequired", "in": "query", "schema": {"type": "boolean"},
         "description": "검교정 대상만 본다"},
    ):
        if extra["name"] not in names:
            # includeInactive 앞에 끼운다 — 거르개는 거르개끼리 모은다.
            at = next((i for i, p in enumerate(get["parameters"])
                       if p["name"] == "includeInactive"), len(get["parameters"]))
            get["parameters"].insert(at, extra)
            names.add(extra["name"])

    spec["paths"]["/mdm/equipments"]["post"] = {
        "tags": ["mdm"], "summary": "설비 등록",
        "description": "근거: W-05-12 §5-1 「설비 추가」",
        "parameters": [IDEM],
        "requestBody": {"required": True,
                        "content": {"application/json": {
                            "schema": {"$ref": "#/components/schemas/EquipmentCreate"}}}},
        "responses": {"201": ok("등록됨", "Equipment"),
                      "400": err("검증 실패 — 유일 위반이면 유일 범위를 담아 돌려준다"),
                      "403": err("권한 없음")},
    }


def patch_editability(spec: dict) -> None:
    """라벨이 나간 코드는 참조가 0이어도 잠근다 — 사유 값을 하나 더한다."""
    reason = spec["components"]["schemas"]["Editability"]["properties"]["reason"]
    if "LABEL_ISSUED" not in reason["enum"]:
        reason["enum"].append("LABEL_ISSUED")
    reason["description"] = (
        "NOT_COUNTABLE = 참조가 FK 가 아니라 세지 못함(의도적 비-FK 또는 코드 문자열 참조) "
        "→ 화면은 무조건 잠근다. RECEIVED_FROM_ERP = 수신본이라 항상 읽기 전용. "
        "LABEL_ISSUED = 코드가 라벨로 발행돼 현장에 물리적으로 나가 있다 → 참조 건수가 "
        "0이어도 잠근다")


def main() -> int:
    with open(CONTRACT, encoding="utf-8") as fh:
        spec = json.load(fh)
    before = json.dumps(spec, ensure_ascii=False, sort_keys=True)

    spec["components"]["schemas"].update(SCHEMAS)
    spec["paths"].update(PATHS)
    patch_equipment(spec)
    patch_editability(spec)

    after = json.dumps(spec, ensure_ascii=False, sort_keys=True)
    with open(CONTRACT, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(spec, ensure_ascii=False, indent=2) + "\n")

    print("경로 %d · 스키마 %d" % (len(spec["paths"]), len(spec["components"]["schemas"])))
    print("바뀐 것이 %s" % ("없다 — 이미 반영돼 있다" if before == after else "있다"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
