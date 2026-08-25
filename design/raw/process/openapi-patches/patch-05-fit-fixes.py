#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""적합성 되짚기에서 나온 정정 여섯. 멱등.

「이 계약으로 이 화면을 그릴 수 있는가」를 17화면에 대해 되짚다 드러난 것들이다.
여섯 다 **계약이 화면 요구를 덜 담고 있던** 자리다. ⭐ 「이 계약으로 그릴 수
있는가」를 묻지 않았으면 통지가 나간 «뒤에» 드러났을 것들이다.

① ⛔ `gaugeId` 가 가리킬 곳이 없어졌다 — 이름을 바로잡는다
------------------------------------------------------------
계측기 이력이 `gaugeId`·`gaugeCode` 를 받는다. 2단계는 `/mdm/gauges` 를 둘
예정이었으나 **4단계에서 두지 않기로 했다** — 계측기는 설비의 한 종류이고
두 경로에 쓰기를 두면 한 행을 두 계약이 쓴다.

⛔ **그 결과 `gaugeId` 가 가리킬 자원이 사라졌다.** 구현팀이 `/mdm/gauges` 를
찾다 막힌다 — 저장 충돌 토큰을 「응답 헤더에서 받는다」고 적고 헤더를
선언하지 않아 19곳이 막혔던 것과 **같은 형태**다.

    gaugeId   → equipmentId       gaugeCode → equipmentCode

⭐ **05 계약은 아직 착수 통지 전이라 지금 고치는 것이 공짜다.** 통지가 나간
뒤였으면 ⛔ 변경 통지 대상이었다.

② 폐기된 설비를 목록에서 뺄 방법이 없었다
------------------------------------------
고장 현장보고 화면(`M-05-02` §6-1)이 「폐기 설비는 목록에서 제외」를 요구하는데
설비 목록에 그 거르개가 없었다. `includeInactive` 는 **사용 여부** 축이고 폐기는
**자산 수명주기** 축이라 다른 것이다(공유계약 B-16).

③ 집계 탭이 셋인데 응답에 담을 곳이 하나뿐이었다
-------------------------------------------------
비가동 집계 화면(`W-05-08` §4)이 **사유별 · 설비별 · 추이** 세 탭을 그린다.
`groupBy` 파라미터는 있었는데 **응답에는 사유별 배열 하나뿐**이었다.
설비별과 추이는 담을 곳이 없어 화면이 그릴 수 없다.

④ 「설비 미지정 세션」을 셀 곳이 없었다
---------------------------------------
같은 화면 §5 가 실측으로 남긴 것 — 조업시간의 원천인 작업 세션은 설비가
비어 있을 수 있고, **그런 세션은 설비별 집계에서 빠진다.** 그 건수를 요약에
보여야 한다(공유계약 G-9 — 모르는 값과 없는 값을 같은 모양으로 그리지 않는다).

⑤ ⛔ 툴의 «날짜 주기» 축이 통째로 없었다 — 화면 하나가 성립하지 않는다
------------------------------------------------------------------------
예방보전 도래 조회 화면(`W-05-02` §3-1)이 확정한 것 —

> 확정 QA #11: 예방보전 트리거 = **타발수 + 날짜 주기 겸용 설정형**

계약에는 **타발수 축만** 있었다(적정타수·누계). 날짜 축의 재료 셋(주기 유형·
주기 간격·마지막 시행일)이 없어 **「예방보전 도래 목록」이 절반만 나온다.**

⭐ 파생 둘은 저장하지 않는다 — 다음 예정일과 도래 여부는 **서버가 계산한다.**
「아무도 아무것도 하지 않아도 값이 바뀌는가」에 「예」이므로 컬럼에 넣지 않는다
(공유계약 A-15).

⑥ 보전 지시에 기준일이 없었다
------------------------------
같은 화면이 인용한 WF05 S8 이 「보전 지시 생성(**BaseDate**)」이라 적었고 그
화면 §5-A 가 **필수**로 두었는데 계약에 칸이 없었다.

쓰기
----
    python3 deliverables/openapi/patch-05-fit-fixes.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EQUIPMENT = os.path.join(HERE, "equipment-05설비툴.json")
MDM = os.path.join(HERE, "mdm-기준정보.json")

EQUIPMENT_ID_DESC = ("계측기. 계측기는 설비의 한 종류라 /mdm/equipments 의 equipmentId "
                     "그대로다 — 계측기 전용 자원을 두지 않는다")


def rename_gauge(spec: dict) -> None:
    """gaugeId·gaugeCode 를 equipmentId·equipmentCode 로 바꾼다."""
    for name in ("Calibration", "CalibrationCreate"):
        schema = spec["components"]["schemas"].get(name)
        if not schema:
            continue
        props = schema["properties"]
        for old, new, desc in (("gaugeId", "equipmentId", EQUIPMENT_ID_DESC),
                               ("gaugeCode", "equipmentCode", None)):
            if old in props:
                props[new] = props.pop(old)
                # 순서를 되돌린다 — 첫 칸이던 것이 뒤로 밀리지 않게.
                if new == "equipmentId":
                    props[new]["example"] = 1001
            if new in props and desc:
                props[new]["description"] = desc
            if new == "equipmentCode" and new in props:
                props[new]["example"] = "GAU-0031"
        schema["required"] = [{"gaugeId": "equipmentId",
                               "gaugeCode": "equipmentCode"}.get(r, r)
                              for r in schema.get("required", [])]

    for param in spec["paths"]["/maintenance/calibrations"]["get"]["parameters"]:
        if param.get("name") == "gaugeId":
            param["name"] = "equipmentId"
            param["description"] = EQUIPMENT_ID_DESC


def add_summary_views(spec: dict) -> None:
    """집계 응답에 설비별·추이를 담을 곳을 만든다."""
    schemas = spec["components"]["schemas"]

    schemas["DowntimeEquipmentSummary"] = {
        "type": "object",
        "required": ["equipmentId", "equipmentCode", "count", "totalMinutes"],
        "description": "설비별 묶음 한 줄. 근거: W-05-08 §4 ③ 설비별 탭",
        "properties": {
            "equipmentId": {"type": "integer", "format": "int64", "example": 1001},
            "equipmentCode": {"type": "string", "example": "PRS-01"},
            "equipmentName": {"type": ["string", "null"], "example": "프레스 1호기"},
            "count": {"type": "integer", "example": 12},
            "totalMinutes": {"type": "integer", "example": 3130},
            "sharePercent": {"type": "number", "format": "double", "example": 40.7},
            "averageMinutes": {"type": "number", "format": "double", "example": 260.8},
        },
    }
    schemas["DowntimePeriodSummary"] = {
        "type": "object",
        "required": ["periodStart", "count", "totalMinutes"],
        "description": ("추이 한 칸. 칸의 크기는 요청의 bucket 이 정한다. "
                        "근거: W-05-08 §4 ③ 추이 탭"),
        "properties": {
            "periodStart": {"type": "string", "format": "date", "example": "2026-08-01",
                            "description": "이 칸이 시작하는 날"},
            "count": {"type": "integer", "example": 9},
            "totalMinutes": {"type": "integer", "example": 640},
        },
    }

    summary = schemas["DowntimeSummary"]
    summary["properties"]["byEquipment"] = {
        "type": "array",
        "items": {"$ref": "#/components/schemas/DowntimeEquipmentSummary"},
        "description": "groupBy=EQUIPMENT 일 때 채워진다",
    }
    summary["properties"]["byPeriod"] = {
        "type": "array",
        "items": {"$ref": "#/components/schemas/DowntimePeriodSummary"},
        "description": "groupBy=PERIOD 일 때 채워진다",
    }
    summary["properties"]["sessionsWithoutEquipmentCount"] = {
        "type": "integer",
        "example": 4,
        "description": ("설비가 붙지 않은 작업 세션 수. 조업 시간에는 들어가지만 "
                        "설비별 묶음에서는 빠진다 — 화면이 그 사실을 요약에 보인다. "
                        "0 과 「모른다」를 같은 모양으로 그리지 않기 위해 «건수» 로 내린다"),
    }

    for param in spec["paths"]["/maintenance/downtimes/summary"]["get"]["parameters"]:
        if param.get("name") == "groupBy":
            param["schema"] = {"type": "string",
                               "enum": ["REASON", "EQUIPMENT", "PERIOD"],
                               "default": "REASON",
                               "example": "EQUIPMENT"}
            param["description"] = ("사유별 · 설비별 · 추이. 화면의 세 탭에 하나씩 "
                                    "대응하며 응답의 by… 배열 하나만 채워진다")
    names = {p.get("name") for p in
             spec["paths"]["/maintenance/downtimes/summary"]["get"]["parameters"]}
    if "bucket" not in names:
        spec["paths"]["/maintenance/downtimes/summary"]["get"]["parameters"].append({
            "name": "bucket", "in": "query",
            "schema": {"type": "string", "enum": ["DAY", "WEEK", "MONTH"],
                       "default": "DAY", "example": "DAY"},
            "description": "groupBy=PERIOD 일 때 칸의 크기. 그 밖에는 무시된다",
        })


PM_TRIGGER_DESC = ("예방보전을 무엇으로 판정하는가 — 타발수(SHOT) · 날짜(DATE) · "
                   "둘 다(BOTH) · 하지 않음(NONE). 확정이 「겸용 설정형」이라 "
                   "이 칸이 그 「설정」이다")


def add_mold_pm_axis(spec: dict) -> None:
    """툴에 날짜 주기 축을 더한다 — 타발수 축만 있었다."""
    schemas = spec["components"]["schemas"]

    write = {
        "pmTriggerTypeCode": {"type": "string", "maxLength": 50, "default": "NONE",
                              "example": "BOTH", "description": PM_TRIGGER_DESC},
        "pmCycleInterval": {"type": ["integer", "null"], "minimum": 1, "example": 6,
                            "description": "날짜 주기 간격. 날짜 축을 쓰면 단위와 함께 필요하다"},
        "pmCycleUnitCode": {"type": ["string", "null"], "maxLength": 50, "example": "MONTH",
                            "description": "날짜 주기 단위 — 일(DAY) 또는 월(MONTH)"},
    }
    derived = {
        "lastPmDate": {"type": ["string", "null"], "format": "date", "example": "2026-05-02",
                       "description": ("마지막 예방보전 시행일이자 다음 주기의 기준일. "
                                       "읽기 전용이다 — 예방보전 실적 등록이 정한다")},
        "nextPmDate": {"type": ["string", "null"], "format": "date", "example": "2026-11-02",
                       "description": ("다음 예방보전 예정일 = 마지막 시행일 + 주기. "
                                       "서버가 계산한다. 기준일이나 주기가 비면 null 이고 "
                                       "화면은 「기준 없음」으로 그린다")},
        "pmDue": {"type": "boolean", "example": True,
                  "description": ("지금 예방보전이 도래했는가. 저장하지 않고 그때그때 "
                                  "계산한다 — 아무도 아무것도 하지 않아도 날짜가 지나면 "
                                  "바뀌는 값이라 컬럼에 넣지 않는다")},
        "pmDueAxisCode": {"type": ["string", "null"], "example": "SHOT",
                          "description": ("먼저 도달한 축 — SHOT 또는 DATE. 둘 다 쓰는 툴이 "
                                          "있어 「왜 도래했는가」를 화면이 밝힌다. "
                                          "도래하지 않았으면 null")},
        "shotUsageRatio": {"type": ["number", "null"], "format": "double", "example": 102.5,
                           "description": ("누계 ÷ 적정타수 백분율. 적정타수가 비면 null 이고 "
                                           "화면은 「산출 불가」로 그린다 — 0 으로 채우지 않는다")},
    }

    for name in ("Mold",):
        props = schemas[name]["properties"]
        for k, v in dict(write, **derived).items():
            props[k] = v
    for name in ("MoldCreate", "MoldUpdate"):
        props = schemas[name]["properties"]
        for k, v in write.items():
            props[k] = v

    get = spec_paths(spec)["/mdm/molds"]["get"] if "/mdm/molds" in spec_paths(spec) else None
    if get is not None:
        names = {p.get("name") for p in get["parameters"]}
        if "pmDueOnly" not in names:
            at = next((i for i, p in enumerate(get["parameters"])
                       if p["name"] == "includeInactive"), len(get["parameters"]))
            get["parameters"].insert(at, {
                "name": "pmDueOnly", "in": "query",
                "schema": {"type": "boolean"},
                "description": ("예방보전이 도래한 것만 본다. 예방보전 도래 조회 화면의 "
                                "기본값이다 — 적체 화면이라 미처리 전건이 먼저 보인다"),
            })
        if "sort" not in names:
            at = next((i for i, p in enumerate(get["parameters"])
                       if p["name"] == "includeInactive"), len(get["parameters"]))
            get["parameters"].insert(at, {
                "name": "sort", "in": "query",
                "schema": {"type": "string", "enum": ["SHOT_USAGE_DESC", "NEXT_PM_ASC", "CODE"],
                           "default": "CODE", "example": "SHOT_USAGE_DESC"},
                "description": ("초과율 높은 순 · 다음 예정일 이른 순 · 코드 순. 적체 화면은 "
                                "초과율 높은 순이 기본이다 — 경과일보다 초과율이 위험 크기다"),
            })


def add_order_base_date(spec: dict) -> None:
    """보전 지시에 기준일을 더한다."""
    schemas = spec["components"]["schemas"]
    field = {"type": ["string", "null"], "format": "date", "example": "2026-08-18",
             "description": ("주기를 세는 기준일. 다음 주기가 이 날부터 시작한다 — "
                             "예방보전 지시에 필요하고 사후 보전에는 비어 있다")}
    schemas["MaintenanceOrder"]["properties"]["baseDate"] = dict(field)
    schemas["MaintenanceOrderCreate"]["properties"]["baseDate"] = dict(field)


def spec_paths(spec: dict) -> dict:
    return spec.get("paths", {})


def add_status_filter(spec: dict) -> None:
    """설비 목록에서 폐기된 것을 뺄 수 있게 한다."""
    get = spec["paths"]["/mdm/equipments"]["get"]
    names = {p.get("name") for p in get["parameters"]}
    if "statusCode" in names:
        return
    at = next((i for i, p in enumerate(get["parameters"])
               if p["name"] == "includeInactive"), len(get["parameters"]))
    get["parameters"].insert(at, {
        "name": "statusCode", "in": "query",
        "schema": {"type": "string"},
        "description": ("자산 수명주기로 거른다 — 운용 또는 폐기. 사용 여부"
                        "(includeInactive)와 «다른 축» 이다. 현장 화면은 폐기된 설비를 "
                        "목록에서 뺀다"),
    })


def save(path: str, spec: dict, indent: int) -> bool:
    text = json.dumps(spec, ensure_ascii=False, indent=indent) + "\n"
    with open(path, encoding="utf-8") as fh:
        before = fh.read()
    if before == text:
        return False
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return True


def main() -> int:
    with open(EQUIPMENT, encoding="utf-8") as fh:
        eq = json.load(fh)
    rename_gauge(eq)
    add_summary_views(eq)
    add_order_base_date(eq)
    changed_eq = save(EQUIPMENT, eq, 1)

    with open(MDM, encoding="utf-8") as fh:
        mdm = json.load(fh)
    add_status_filter(mdm)
    add_mold_pm_axis(mdm)
    changed_mdm = save(MDM, mdm, 2)

    print("equipment-05설비툴.json — %s" % ("고쳤다" if changed_eq else "이미 반영돼 있다"))
    print("mdm-기준정보.json      — %s" % ("고쳤다" if changed_mdm else "이미 반영돼 있다"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
