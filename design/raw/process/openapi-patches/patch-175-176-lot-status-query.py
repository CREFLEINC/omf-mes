#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`W-03-01` 조회 입력 계약을 채운다. 멱등. — 이슈 #175 · #176

무엇이 막혔나
-------------
구현팀이 `W-03-01`(Lot Status 현황·변경이력 조회)을 만들다 **네 자리가 계약에
없어** 화면을 완결할 수 없다고 알려 왔다. 두 이슈가 한 화면을 다룬다.

    #175  요약이 목록 필터를 못 받는다  → 두 결과의 «모집단»이 갈린다
    #176  ①선택지 ②정렬 ③LOT 번호 ④사건 이력

⚠ #175 는 «양방향» 이었다 — 구현팀은 요약에 셋이 없다고 짚었는데, 반대로
**목록에만 없는 축**(`plantId`)도 있었다. 「요약에 셋을 더한다」로 끝나지 않는다.

무엇을 하나
-----------
**①  #175 — 목록과 요약이 «같은 필터»를 받는다**
    요약에 `lotStatusCode`·`locationId`·`q`·`heldOnly`·`excludeFullyHeld` 신설
    목록에 `plantId` 신설  ⇒ 페이지 조건을 뺀 나머지가 양쪽 같다(공유계약 L-1)

**②  #176 ① — 선택지를 이름으로 부른다**
    `LOT_STATUS`(정상·불량·검사 대기·폐기) · `LOT_TYPE`(자재·생산·제품)
    → #179 가 연 `codeGroupCode` 로 받는다

**③  #176 ② — 정렬을 계약이 «제한»한다**
    `sort` 신설 — 허용 키 셋(LOT·품목·최근 전이) × 방향. 공유계약 L-4

**④  #176 ③④ — 보류 «사건» 목록을 신설한다**
    GET /quality/lot-hold-events — 등록·해제를 «행»으로 낸다
    `lot-holds` 에 `lotNo` 신설 · `open` 의 뜻을 못박는다

⭐ 왜 「사건 목록」인가 — 화면이 이미 그렇게 그려져 있었다
----------------------------------------------------------
`W-03-01` §3 「이력으로 찾기」 모드가 **사건별 행**을 그리고 있다.

    일시           LOT      전이            행위자   사유
    08-03 14:02    …0012    → 보류          김품질   수입검사 대기
    08-02 11:30    …0007    보류 → (해제)   박품질   —

**보류 «문서» 목록으로는 이 표를 만들 수 없다** — 한 행에 등록과 해제가 함께
있어서, 「기간 전에 등록되고 기간 안에 해제된 보류」를 기간 필터로 집을 수 없다.
구현팀이 짚은 그대로다.

⚠ **새 테이블을 요구하지 않는다** — `trace.lot_hold` 한 행이 `held_by`/`held_at`
와 `released_by`/`released_at` 를 **둘 다** 갖는다. 서버가 한 행을 **최대 두
사건으로 편다.** 파생은 서버가 낸다(공유계약 L-2) — 이미 `heldQty`·
`latestTransitionAt` 이 같은 방식이다.

⛔ 없는 것을 있는 것처럼 만들지 않는다 — A-11
----------------------------------------------
`W-03-01` §5-1 실측 — **전이 9건 중 2건만 온전히 남고 5건은 사라진다.** 변경이력
테이블이 없어서다. 그래서 이 경로 이름은 **`lot-status-events` 가 아니라
`lot-hold-events`** 다. 「보류 등록·해제」만 낸다는 것을 **이름이 말하게** 했고,
설명에도 못박았다. **전체 전이 이력으로 읽히면 화면이 거짓을 그린다.**

⭐ 값 이름 — 지어내지 않고 확정된 뜻을 규약대로 옮겼다
-------------------------------------------------------
LOT 상태 4값과 유형 3종은 **뜻이 이미 확정**돼 있었다(회신 E-3 종결 2026-08-07 ·
결정 10). 코드 문자열은 **영문 대문자 SNAKE** 규약을 따랐다(시드 선례
`AVAILABLE`·`IN_TRANSIT` · 1차 제안안 §5 표기 규약).

    정상       NORMAL              자재  MATERIAL
    불량       DEFECTIVE           생산  PRODUCTION
    검사 대기  INSPECTION_PENDING  제품  PRODUCT
    폐기       SCRAPPED            ← 「폐기」의 기존 표기 SCRAP(issueTypeCode)를 따랐다

⚠ **`lot.status_code` 와 `lot_hold.status_code` 는 다른 축이다**(§5-3) — 이 그룹은
앞의 것이다. 보류 «건»의 진행 상태는 `released_at` 의 유무로 갈리며 별개다.

⛔ 하지 «않은» 것
------------------
- **`enum` 을 코드 필드에 넣지 않았다** — 좁히면 ⛔ 등급 통지가 된다(G-2·G-6).
  ⚠ 다만 **`sort` 에는 넣었다** — 새 파라미터라 좁힐 기존 값이 없고, #176 의
  완료 조건이 「생성 타입만 읽어도 모호하지 않다」를 요구한다.
- **`lot-holds` 에 해제 쪽 기간·행위자 필터를 더하지 않았다** — 사건 목록이 그
  물음에 답한다. 두 곳에 같은 질의를 두면 **어느 것이 정본인지 갈린다.**

쓰기
----
    python3 deliverables/openapi/patch-175-176-lot-status-query.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
QUALITY = "quality-03품질.json"

LOT_STATUS_GROUP = "LOT_STATUS"
LOT_TYPE_GROUP = "LOT_TYPE"

STATUS_DESC = (
    "품질 판정 축 — 정상·불량·검사 대기·폐기. ⭐ 값 목록은 "
    "GET /mdm/code-values?codeGroupCode=%s 로 받는다"
    "(NORMAL·DEFECTIVE·INSPECTION_PENDING·SCRAPPED). "
    "⚠ 보류 건의 진행 상태와 다른 축이다(W-03-01 §5-3). 근거: 회신 E-3 종결 "
    "2026-08-07 · omf-mes#176" % LOT_STATUS_GROUP
)
TYPE_DESC = (
    "자재·생산·제품 3종(결정 10). ⭐ 값 목록은 "
    "GET /mdm/code-values?codeGroupCode=%s 로 받는다"
    "(MATERIAL·PRODUCTION·PRODUCT). ⚠ 셋을 합쳐 집계하지 않는다"
    "(공유계약 L-7) — 같은 「보류 38건」이라도 자재와 제품은 대응이 다르다. "
    "근거: omf-mes#176" % LOT_TYPE_GROUP
)

SORT_PARAM = {
    "name": "sort",
    "in": "query",
    "schema": {
        "type": "string",
        "enum": ["lotNoAsc", "lotNoDesc", "itemAsc", "itemDesc",
                 "latestTransitionAsc", "latestTransitionDesc"],
        "default": "latestTransitionDesc",
    },
    "description": (
        "정렬. ⛔ 허용 키는 셋뿐이다 — LOT 번호·품목·최근 전이(공유계약 L-4). "
        "기본은 최근 전이 내림차순. ⚠ 화면이 현재 페이지만 다시 정렬하면 "
        "서버 전체를 정렬한 것처럼 보이면서 결과가 틀린다. 근거: omf-mes#176"
    ),
}

PLANT_PARAM = {
    "name": "plantId",
    "in": "query",
    "schema": {"type": "integer", "format": "int64"},
    "description": (
        "공장. ⭐ 요약(/quality/lot-status-summary)에만 있고 목록에 없어 "
        "두 결과의 모집단이 갈렸다 — 맞춘다. 근거: omf-mes#175"
    ),
}

LOT_NO_PARAM = {
    "name": "lotNo",
    "in": "query",
    "schema": {"type": "string"},
    "description": (
        "LOT 번호로 찾는다(정확히 일치). ⭐ 화면 입력이 LOT 번호인데 lotId "
        "만 받아, 화면이 /trace/lots?q= 의 첫 결과를 임의로 골라야 했다 — "
        "부분 일치나 다른 범위의 LOT 을 잘못 가리킬 수 있다. 근거: omf-mes#176"
    ),
}

OPEN_DESC = (
    "기본 true — 아직 해제되지 않은 보류만. ⛔ false 는 「해제된 것만」이 "
    "아니라 «전체»(해제된 것 + 진행 중)다. ⚠ 등록·해제를 «사건»으로 시간순 "
    "보려면 이 목록이 아니라 GET /quality/lot-hold-events 를 쓴다 — 이 목록은 "
    "보류 «문서» 한 건이 한 행이라 등록과 해제가 같은 행에 있다. "
    "근거: omf-mes#176"
)

# 요약이 목록과 같은 필터를 받게 한다 — 페이지 조건만 뺀다
SUMMARY_ADD = [
    {"name": "lotStatusCode", "in": "query", "schema": {"type": "string"},
     "description": STATUS_DESC},
    {"name": "locationId", "in": "query",
     "schema": {"type": "integer", "format": "int64"}},
    {"name": "heldOnly", "in": "query", "schema": {"type": "boolean"},
     "description": "미해제 보류가 있는 것만"},
    {"name": "excludeFullyHeld", "in": "query", "schema": {"type": "boolean"},
     "description": "이미 전량 보류인 것을 뺀다"},
    {"name": "q", "in": "query", "schema": {"type": "string"},
     "description": "LOT 번호 검색"},
]

SUMMARY_NOTE = (
    "⭐ 질의는 목록(/quality/lot-statuses)과 «같다» — page·size·sort 만 뺀다. "
    "요약은 필터 전체 기준, 목록은 페이지 기준이라(공유계약 L-1) 두 요청이 "
    "같은 모집단을 봐야 한다. ⛔ 한쪽에만 있는 필터를 두지 않는다 — "
    "화면이 필터를 걸면 카드와 목록이 서로 다른 것을 세게 된다(omf-mes#175)."
)

EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "lotHoldId": {"type": "integer", "format": "int64", "example": 1001},
        "eventTypeCode": {
            "type": "string",
            "enum": ["HELD", "RELEASED"],
            "description": "등록(HELD) 또는 해제(RELEASED). 한 보류 문서가 최대 두 사건을 낸다",
            "example": "HELD",
        },
        "occurredAt": {
            "type": "string", "format": "date-time",
            "description": "등록이면 held_at, 해제면 released_at",
            "example": "2026-08-06T09:12:00+09:00",
        },
        "lotId": {"type": "integer", "format": "int64", "example": 1001},
        "lotNo": {"type": "string", "example": "값"},
        "itemId": {"type": "integer", "format": "int64", "example": 1001},
        "actorId": {
            "type": "integer", "format": "int64",
            "description": "등록이면 held_by, 해제면 released_by",
            "example": 1001,
        },
        "actorName": {
            "type": "string",
            "description": "화면이 사람 이름을 보인다 — 서버가 푼다(requestedByName 과 같은 방식)",
            "example": "값",
        },
        "reasonCode": {
            "type": ["string", "null"],
            "description": "보류 사유. ⚠ 해제 사건에는 없을 수 있다",
            "example": "QUALITY_HOLD",
        },
        "holdQty": {"type": ["number", "null"],
                    "description": "NULL = 전량 보류", "example": 50.0},
        "uomId": {"type": ["integer", "null"], "format": "int64",
                  "example": 1001},
        "releaseCondition": {"type": ["string", "null"],
                             "description": "「수입검사 합격」 같은 문장",
                             "example": "비고 문자열"},
        "targetLotStatusCode": {
            "type": ["string", "null"],
            "description": "해제 사건이 LOT 을 어느 상태로 보냈나. 값 목록은 LOT_STATUS",
            "example": "NORMAL",
        },
    },
    "required": ["lotHoldId", "eventTypeCode", "occurredAt", "lotId", "lotNo",
                 "actorId"],
    "x-internal-note": (
        "⛔ 이것은 «전체 전이 이력이 아니다» — 보류 등록·해제만이다. 변경이력 "
        "테이블이 물리 모델에 없어 전이 9건 중 5건이 아예 남지 않는다"
        "(W-03-01 §5-1 실측). 그래서 경로 이름이 lot-status-events 가 아니라 "
        "lot-hold-events 이고, 화면은 A-11 대로 「보류 이력만 보입니다」를 "
        "문구로 밝힌다. ⭐ 새 테이블을 요구하지 않는다 — trace.lot_hold 한 행이 "
        "held_by/held_at 와 released_by/released_at 를 둘 다 가지므로 서버가 "
        "한 행을 최대 두 사건으로 편다(공유계약 L-2 파생은 서버 계산). "
        "이슈 #176."
    ),
}

EVENT_PATH = {
    "get": {
        "tags": ["quality"],
        "summary": "보류 등록·해제 사건 조회",
        "description": (
            "보류 등록·해제를 «사건별 행»으로 시간순 낸다 — W-03-01 「이력으로 "
            "찾기」 모드. ⛔ 전체 전이 이력이 아니다 — 합격·불합격·재판정 전이는 "
            "저장되는 곳이 없어 이 목록에 없다(W-03-01 §5-1 · A-11). "
            "⭐ 보류 «문서» 목록(/quality/lot-holds)으로는 이 표를 만들 수 없다 — "
            "한 행에 등록과 해제가 함께 있어 「기간 전에 등록되고 기간 안에 "
            "해제된 보류」를 기간으로 집을 수 없다. 근거: omf-mes#176"
        ),
        "parameters": [
            {"name": "occurredFrom", "in": "query", "required": True,
             "schema": {"type": "string", "format": "date-time"},
             "description": "사건 기간 시작. ⛔ 필수다 — 감사 조회는 기간을 강제한다(공유계약 L-3)"},
            {"name": "occurredTo", "in": "query", "required": True,
             "schema": {"type": "string", "format": "date-time"},
             "description": "사건 기간 끝"},
            {"name": "eventTypeCode", "in": "query",
             "schema": {"type": "string", "enum": ["HELD", "RELEASED"]},
             "description": "등록만 / 해제만. 비우면 둘 다"},
            {"name": "actorId", "in": "query",
             "schema": {"type": "integer", "format": "int64"},
             "description": "행위자 — 등록자와 해제자를 «함께» 본다. ⭐ 「그 사람이 해제한 건」이 빠지지 않는다"},
            {"name": "lotNo", "in": "query", "schema": {"type": "string"},
             "description": "LOT 번호(정확히 일치) — 화면 입력이 번호다"},
            {"name": "lotId", "in": "query",
             "schema": {"type": "integer", "format": "int64"}},
            {"name": "itemId", "in": "query",
             "schema": {"type": "integer", "format": "int64"}},
            {"name": "reasonCode", "in": "query", "schema": {"type": "string"}},
            {"name": "lotTypeCode", "in": "query", "schema": {"type": "string"},
             "description": TYPE_DESC},
            {"name": "sort", "in": "query",
             "schema": {"type": "string",
                        "enum": ["occurredAsc", "occurredDesc"],
                        "default": "occurredDesc"},
             "description": "시간순만 허용한다 — 사건 목록의 축은 시각 하나다"},
            {"name": "page", "in": "query",
             "schema": {"type": "integer", "default": 1}},
            {"name": "size", "in": "query",
             "schema": {"type": "integer", "default": 50}},
        ],
        "responses": {
            "200": {
                "description": "사건 목록",
                "content": {"application/json": {"schema": {
                    "type": "object",
                    "properties": {
                        "items": {"type": "array", "items": {
                            "$ref": "#/components/schemas/LotHoldEvent"}},
                        "page": {"$ref": "#/components/schemas/PageMeta"},
                    },
                    "required": ["items", "page"],
                }}},
            },
            "400": {
                "description": "기간 미지정 — 조회 버튼 비활성 + 사유",
                "content": {"application/json": {"schema": {
                    "$ref": "#/components/schemas/ErrorResponse"}}},
            },
        },
    }
}

# ⛔ 예시값이 «뜻과 어긋나는» 자리 — 이 화면이 읽는 LOT 상태·유형만 고친다
#
# 전수로 훑으니 example 이 "IQC"·"STANDARD" 인 자리가 74곳이다. 대부분은
# 인스턴스 식별자(routingCode·bomCode…)라 「STANDARD」가 그냥 자리채움이지만,
# LOT 상태·유형처럼 «값 목록이 정해진» 자리에 "IQC"(검사 «유형»)가 들어가 있으면
# 구현팀이 생성 타입에서 그 값을 보고 만든다. 실제로 #179 에서 그렇게 드러났다.
# ⚠ 나머지는 이 건의 범위 밖이라 완료보고에 남긴다.
BAD_EXAMPLES = {
    "LotHold": {"lotStatusCode": "NORMAL"},
    "LotHoldCreate": {"targetLotStatusCode": "NORMAL"},
    "LotHoldRelease": {"targetLotStatusCode": "NORMAL"},
    "LotQualityStatus": {"lotStatusCode": "NORMAL"},
    "LotStatusCount": {"statusCode": "NORMAL", "lotTypeCode": "MATERIAL"},
}

FORMAT: dict[str, dict] = {}


def measure(raw: str) -> dict:
    second = raw.split("\n")[1] if "\n" in raw else ""
    return {"indent": len(second) - len(second.lstrip(" ")) or 1,
            "newline": raw.endswith("\n")}


def load(name: str) -> dict:
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        raw = fh.read()
    FORMAT[name] = measure(raw)
    return json.loads(raw)


def save(name: str, spec: dict) -> None:
    """⚠ 원본과 «같은 직렬화»로 쓴다."""
    fmt = FORMAT[name]
    body = json.dumps(spec, ensure_ascii=False, indent=fmt["indent"])
    if fmt["newline"]:
        body += "\n"
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as fh:
        fh.write(body)


def roundtrip(name: str) -> None:
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        before = fh.read()
    fmt = measure(before)
    after = json.dumps(json.loads(before), ensure_ascii=False,
                       indent=fmt["indent"])
    if fmt["newline"]:
        after += "\n"
    if before != after:
        sys.exit("⛔ %s — 직렬화가 원본과 다릅니다." % name)


def put_param(op: dict, param: dict, log: list, where: str) -> None:
    """이름으로 갈음한다 — 멱등."""
    params = op.setdefault("parameters", [])
    for i, p in enumerate(params):
        if isinstance(p, dict) and p.get("name") == param["name"]:
            if p == param:
                log.append("  · %-34s %s 이미 되어 있다" % (where, param["name"]))
            else:
                params[i] = json.loads(json.dumps(param))
                log.append("  ✅ %-34s %s 갱신" % (where, param["name"]))
            return
    params.append(json.loads(json.dumps(param)))
    log.append("  ⭐ %-34s %s 신설" % (where, param["name"]))


def set_desc(op: dict, name: str, desc: str, log: list, where: str) -> None:
    for p in op.get("parameters", []):
        if isinstance(p, dict) and p.get("name") == name:
            if p.get("description") == desc:
                log.append("  · %-34s %s 설명 이미 되어 있다" % (where, name))
            else:
                p["description"] = desc
                log.append("  ✅ %-34s %s 설명 갱신" % (where, name))
            return


def main() -> int:
    roundtrip(QUALITY)
    spec = load(QUALITY)
    paths = spec["paths"]
    schemas = spec["components"]["schemas"]
    log: list = []

    print("== W-03-01 조회 입력 계약을 채운다 — #175 · #176 ==\n")

    # ① #175 — 목록과 요약이 같은 필터를 받는다
    print("-- ① 목록 ↔ 요약 필터를 맞춘다 (#175) --")
    lst = paths["/quality/lot-statuses"]["get"]
    put_param(lst, PLANT_PARAM, log, "lot-statuses")
    smry = paths["/quality/lot-status-summary"]["get"]
    for p in SUMMARY_ADD:
        put_param(smry, p, log, "lot-status-summary")
    if smry.get("x-internal-note") == SUMMARY_NOTE:
        log.append("  · %-34s 필터 짝 규칙 이미 있다" % "lot-status-summary")
    else:
        smry["x-internal-note"] = SUMMARY_NOTE
        log.append("  ⭐ %-34s 필터 짝 규칙 신설" % "lot-status-summary")
    print("\n".join(log)); log.clear()

    # ② #176 ① — 선택지
    print("\n-- ② 선택지를 이름으로 부른다 (#176 ①) --")
    for path, op in (("lot-statuses", lst), ("lot-status-summary", smry)):
        set_desc(op, "lotStatusCode", STATUS_DESC, log, path)
        set_desc(op, "lotTypeCode", TYPE_DESC, log, path)
    for sch, key, desc in (("LotQualityStatus", "lotStatusCode", STATUS_DESC),
                           ("LotQualityStatus", "lotTypeCode", TYPE_DESC),
                           ("LotStatusCount", "statusCode", STATUS_DESC),
                           ("LotStatusCount", "lotTypeCode", TYPE_DESC)):
        prop = schemas[sch]["properties"].get(key)
        if prop is None:
            continue
        if prop.get("description") == desc:
            log.append("  · %-34s %s 이미 되어 있다" % (sch, key))
        else:
            prop["description"] = desc
            log.append("  ✅ %-34s %s 설명 갱신" % (sch, key))
    for sch, fixes in BAD_EXAMPLES.items():
        for key, val in fixes.items():
            prop = schemas.get(sch, {}).get("properties", {}).get(key)
            if prop is None:
                continue
            if prop.get("example") == val:
                log.append("  · %-34s %s 예시 이미 맞다" % (sch, key))
            else:
                old = prop.get("example")
                prop["example"] = val
                log.append("  ⛔ %-34s %s 예시 %r → %r (뜻과 어긋났다)"
                           % (sch, key, old, val))
    print("\n".join(log)); log.clear()

    # ③ #176 ② — 정렬
    print("\n-- ③ 정렬을 계약이 제한한다 (#176 ②) --")
    put_param(lst, SORT_PARAM, log, "lot-statuses")
    print("\n".join(log)); log.clear()

    # ④ #176 ③④ — 사건 목록
    print("\n-- ④ 보류 사건 목록을 신설한다 (#176 ③④) --")
    holds = paths["/quality/lot-holds"]["get"]
    put_param(holds, LOT_NO_PARAM, log, "lot-holds")
    set_desc(holds, "open", OPEN_DESC, log, "lot-holds")

    if schemas.get("LotHoldEvent") == EVENT_SCHEMA:
        log.append("  · %-34s 이미 있다" % "LotHoldEvent")
    else:
        schemas["LotHoldEvent"] = json.loads(json.dumps(EVENT_SCHEMA))
        spec["components"]["schemas"] = {k: schemas[k] for k in sorted(schemas)}
        log.append("  ⭐ %-34s 스키마 신설" % "LotHoldEvent")

    if paths.get("/quality/lot-hold-events") == EVENT_PATH:
        log.append("  · %-34s 이미 있다" % "/quality/lot-hold-events")
    else:
        paths["/quality/lot-hold-events"] = json.loads(json.dumps(EVENT_PATH))
        spec["paths"] = {k: paths[k] for k in sorted(paths)}
        log.append("  ⭐ %-34s 경로 신설 (정렬 자리 지킴)" % "/quality/lot-hold-events")
    print("\n".join(log))

    save(QUALITY, spec)

    after = load(QUALITY)
    lst2 = after["paths"]["/quality/lot-statuses"]["get"]["parameters"]
    smr2 = after["paths"]["/quality/lot-status-summary"]["get"]["parameters"]
    names = lambda ps: [p["name"] for p in ps if "name" in p]
    paging = {"page", "size", "sort"}
    print("\n== 최종 ==")
    print("   목록 질의  %s" % names(lst2))
    print("   요약 질의  %s" % names(smr2))
    same = set(names(lst2)) - paging == set(names(smr2)) - paging
    print("   페이지 조건을 뺀 필터가 같은가: %s" % ("✅ 같다" if same else "⛔ 다르다"))
    print("   경로 %d (신설 1) · 스키마 %d (신설 1)"
          % (len(after["paths"]), len(after["components"]["schemas"])))
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
