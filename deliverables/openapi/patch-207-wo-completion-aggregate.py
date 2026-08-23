#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W/O 마감 화면이 쓸 «실적 누계»와 «선발행 LOT 슬롯 집계»를 계약에 앉힌다. 멱등.

무엇을 고치나
-------------
    WorkOrder.progress          실적 누계 5수량 + 달성률 + 마감 3분류 판정 + 잔량
    WorkOrder.preIssuedLots     선발행 LOT 슬롯 — 전체 · 실적 있음 · 실적 없음
    GET /production/work-orders/{id}  → `withPreIssuedLots` 질의 파라미터
    GET /trace/lots                   → `workOrderId` 질의 파라미터

⭐ 왜 — 구현팀 질의 `omf-mes#207`
----------------------------------
W/O 마감·ERP 실적 송신 화면(`W-02-05`)은 **W/O 하나의 실적 «전체» 합계**로
마감 판정을 보이고, 선발행 LOT 슬롯의 전체·실적 있음·실적 없음 건수를 보여야
한다(`W-02-05` §3 레이아웃). 그런데 목록 조회는 **한 «쪽»만** 돌려주고,
쪽을 합산하면 두 번째 쪽부터 조용히 빠진다. 구현팀이 「불완전한 쪽에서
계산하지 않겠다」고 멈춘 것이 옳다.

⛔ 없던 것이 아니라 «앉을 자리»가 없었다
----------------------------------------
W/O 목록 조회에는 이미 이런 것이 선언돼 있었다.

    withProgress   (boolean, 기본 true)  「실적 누계를 함께 받는다」
    설명            「집계 열(실적 누계)을 함께 내려준다. 근거: W-02-08 §3·§5」

**그런데 `WorkOrder` 스키마에 수량 칸이 하나도 없다**(실측 — `orderQty` 뿐).
켜도 담길 곳이 없으니 **약속만 있고 물건이 없는 상태**였다. 이 패치는 새
기능을 더하는 것이 아니라 **이미 한 약속을 착지시킨다.**

⭐⭐ 판정을 서버가 «한 곳에서» 낸다 — 정본이 그렇게 정해 두었다
---------------------------------------------------------------
`W-02-08` §5-2 원문:

    ⚠ `W-02-05`(마감)와 같은 식을 써야 한다 — 조회에서 95%인데 마감에서 미달
      판정이 다르게 나오면 신뢰를 잃는다. **서버가 한 곳에서 계산**하는 이유다.

그래서 달성률과 3분류 판정을 **응답에 싣는다.** 화면이 각자 계산하면
관리웹·POP·모바일 세 벌이 조금씩 다르게 반올림한다.

⚠ 「정상」의 «폭»은 아직 미정이다
---------------------------------
3분류(미달·정상·초과) 자체는 확정이다(R80 · ✓확정 QA #27). 다만 2,999개가
미달인지 정상인지 — **허용 오차**는 아직 정해지지 않았다(`W-02-05` §5-1·§8-1).
⭐ **판정을 서버에 둔 것이 이 미결을 더 싸게 만든다** — 나중에 오차 정책이
정해지면 **서버 한 곳**만 고치면 되고, 계약과 화면은 그대로다.

⛔ 「손실」을 만들지 않는다 — `#60` 을 조용히 닫지 않기 위해
-----------------------------------------------------------
`W-02-08` 은 3원(양품·불량·손실)으로 줄여 보이고 `W-02-05` §4-B 는 5컬럼을
읽는다. **그 축약 대응이 `#60` 으로 아직 열려 있다.** 계약은 **물리 컬럼
다섯을 그대로** 내린다 — 여기서 `lossQty` 를 만들면 「손실 = 스크랩 + 재작업」
같은 대응을 **계약이 몰래 확정**해 버린다. 줄이는 것은 화면이 한다.

⛔ 택하지 않은 안
-----------------
① **`production-results` 가 전체 집계를 함께 반환한다** — 실적 «목록» 자원에
   마감 판정 축이 붙는다. 그러면 같은 판정을 내는 곳이 둘(W/O · 실적 목록)이
   되어 `W-02-08` §5-2 가 경고한 「두 곳이 다르게 계산한다」에 정확히 걸린다.
② **마감 전용 read-model 을 새 경로로 신설** — `withProgress` 가 이미 있는데
   같은 것을 두 경로가 내리게 된다. **경로를 늘리지 않고 약속을 채우는 쪽**을
   택했다.

⭐ `trace/lots` 는 «건수»가 아니라 «보기»를 위한 것이다
-------------------------------------------------------
집계 응답에 목록을 넣지 않는다(05 계약 2단계 판정 4) — 건수는 위 요약이 주고,
「그 슬롯들을 보여 달라」는 목록 필터로 간다. 그래서 `workOrderId` 를 더한다.

⛔ `sourceTypeCode` + `sourceId` 짝으로 열지 않았다. 그것이 저장된 형태이긴
하나(`A-10` 다형 참조 — 한 칸이 상황에 따라 여러 표를 가리킨다), **판별자
값 목록이 아직 미확정**이다(2026-08-22 잔여 결정 분류 §3 8번 · 중요도 높음).
값을 모르는 채 필터만 열면 **눌러도 아무것도 안 걸리는 컨트롤**이 된다
(공유계약 `G-23`). `workOrderId` 는 **오늘 바로 쓸 수 있고**, 판별자 값이
정해지면 짝 필터는 그때 별건으로 연다.

쓰기
----
    python3 deliverables/openapi/patch-207-wo-completion-aggregate.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PRODUCTION = os.path.join(HERE, "production-02생산실행.json")
LOGISTICS = os.path.join(HERE, "logistics-01자재창고.json")

QTY = {"type": "number", "format": "double", "example": 2850.0}


def qty(desc: str) -> dict:
    d = dict(QTY)
    d["description"] = desc
    return d


WORK_ORDER_PROGRESS = {
    "type": "object",
    "description": (
        "실적 누계 — 이 W/O 의 생산 실적 «전체» 합계다. 쪽(page)과 무관하며 "
        "정정(상쇄) 실적이 반영된 값이다. withProgress=true 일 때만 채워진다. "
        "근거: W-02-05 §4-B · W-02-08 §4-A"
    ),
    "properties": {
        "goodQty": qty("양품 합계 — production_result.good_qty 의 합"),
        "defectQty": qty("불량 합계"),
        "holdQty": qty("보류 합계"),
        "scrapQty": qty("스크랩 합계"),
        "reworkQty": qty("재작업 합계"),
        "achievementRate": {
            "type": "number",
            "format": "double",
            "description": (
                "달성률 = 양품 합계 / 지시 수량. ⛔ 서버가 계산한다 — 화면이 "
                "각자 계산하면 조회 화면과 마감 화면의 값이 갈린다"
                "(W-02-08 §5-2). 분모는 지시 수량이다(R14 · R80)"
            ),
            "example": 0.95,
        },
        "varianceQty": qty(
            "지시 수량 − 양품 합계. 양수면 미달분, 음수면 초과분이다"
        ),
        "completionJudgmentCode": {
            "type": "string",
            "enum": ["UNDER", "NORMAL", "OVER"],
            "description": (
                "마감 3분류 판정 — 미달 · 정상 · 초과. ⛔ 서버가 판정한다"
                "(W-02-08 §5-2 — 조회와 마감이 다른 값을 내면 안 된다). "
                "⚠ 「정상」의 폭(허용 오차)은 아직 미정이라 서버 정책이 "
                "정해지면 그 기준을 따른다 — 계약과 화면은 그대로다"
                "(W-02-05 §5-1·§8-1). 초과도 실적으로 인정한다(R81)"
            ),
            "example": "UNDER",
        },
    },
    "required": ["goodQty", "achievementRate", "completionJudgmentCode"],
}

PRE_ISSUED_LOT_SUMMARY = {
    "type": "object",
    "description": (
        "선발행 생산LOT 슬롯 집계 — 건수만 내린다. 목록은 넣지 않는다. "
        "「그 슬롯들을 보여 달라」는 GET /trace/lots?workOrderId=… 로 간다. "
        "withPreIssuedLots=true 일 때만 채워진다. 근거: W-02-05 §3·§5-3"
    ),
    "properties": {
        "slotCount": {
            "type": "integer",
            "description": "선발행된 슬롯 전체",
            "example": 6,
        },
        "withResultCount": {
            "type": "integer",
            "description": "실적이 붙은 슬롯 — 마감 후 유지된다",
            "example": 5,
        },
        "withoutResultCount": {
            "type": "integer",
            "description": (
                "실적이 없는 슬롯 — 마감 시점에 자동 폐번 대상이다"
                "(R82 · 마감 시점 «전용»이라 취소 경로는 해당 없다)"
            ),
            "example": 1,
        },
    },
    "required": ["slotCount", "withResultCount", "withoutResultCount"],
}

WITH_PRE_ISSUED_PARAM = {
    "name": "withPreIssuedLots",
    "in": "query",
    "schema": {"type": "boolean", "default": False},
    "description": (
        "선발행 생산LOT 슬롯 집계를 함께 받는다. 마감 화면(W-02-05)이 쓴다 — "
        "목록에서는 W/O 마다 세게 되므로 기본은 끈다"
    ),
}

WORK_ORDER_ID_FILTER = {
    "name": "workOrderId",
    "in": "query",
    "schema": {"type": "integer", "format": "int64"},
    "description": (
        "이 W/O 를 원천으로 발행된 LOT 만. 선발행 슬롯을 빠짐없이 훑는 "
        "경로다(W-02-05 §3). ⭐ 저장된 형태는 다형 참조 짝"
        "(sourceTypeCode + sourceId)이지만 판별자 값 목록이 아직 미확정이라 "
        "짝 필터를 열지 않았다 — 값을 모르는 채 열면 눌러도 아무것도 안 걸린다"
        "(공유계약 G-23). 서버가 W/O 원천으로 풀어 준다"
    ),
}


def detect_indent(original: str, doc: dict):
    body = original.rstrip("\n")
    for candidate in (1, 2, 4):
        if json.dumps(doc, ensure_ascii=False, indent=candidate) == body:
            return candidate
    return None


def load(path: str):
    original = open(path, encoding="utf-8").read()
    doc = json.loads(original)
    indent = detect_indent(original, doc)
    if indent is None:
        print(f"⛔ {os.path.basename(path)} 들여쓰기를 알아낼 수 없다",
              file=sys.stderr)
        sys.exit(1)
    return original, doc, indent, original[len(original.rstrip("\n")):]


def save(path: str, original: str, doc: dict, indent: int, tail: str) -> bool:
    updated = json.dumps(doc, ensure_ascii=False, indent=indent) + tail
    if updated == original:
        return False
    open(path, "w", encoding="utf-8").write(updated)
    return True


def put_param(op: dict, param: dict) -> None:
    params = op.setdefault("parameters", [])
    for i, existing in enumerate(params):
        if existing.get("name") == param["name"]:
            params[i] = param
            return
    params.append(param)


def main() -> int:
    changed = []

    # ── 생산실행 ──────────────────────────────────────────────────────
    original, doc, indent, tail = load(PRODUCTION)
    schemas = doc["components"]["schemas"]
    schemas["WorkOrderProgress"] = json.loads(json.dumps(WORK_ORDER_PROGRESS))
    schemas["PreIssuedLotSummary"] = json.loads(json.dumps(PRE_ISSUED_LOT_SUMMARY))

    props = schemas["WorkOrder"]["properties"]
    props["progress"] = {"$ref": "#/components/schemas/WorkOrderProgress"}
    props["preIssuedLots"] = {"$ref": "#/components/schemas/PreIssuedLotSummary"}

    detail = doc["paths"]["/production/work-orders/{workOrderId}"]["get"]
    # 상세도 목록과 같은 스위치를 갖는다 — 마감 화면은 한 건만 편다.
    for name, model in (("withProgress", None), ("withPreIssuedLots", WITH_PRE_ISSUED_PARAM)):
        if model is None:
            listed = doc["paths"]["/production/work-orders"]["get"]["parameters"]
            model = next(p for p in listed if p.get("name") == name)
        put_param(detail, json.loads(json.dumps(model)))
    put_param(doc["paths"]["/production/work-orders"]["get"],
              json.loads(json.dumps(WITH_PRE_ISSUED_PARAM)))

    if save(PRODUCTION, original, doc, indent, tail):
        changed.append("production-02생산실행.json — 실적 누계·선발행 슬롯 집계")

    # ── 자재창고(LOT) ─────────────────────────────────────────────────
    original, doc, indent, tail = load(LOGISTICS)
    put_param(doc["paths"]["/trace/lots"]["get"],
              json.loads(json.dumps(WORK_ORDER_ID_FILTER)))
    if save(LOGISTICS, original, doc, indent, tail):
        changed.append("logistics-01자재창고.json — /trace/lots workOrderId 필터")

    if not changed:
        print("  이미 반영돼 있다 — 변경 없음")
    for line in changed:
        print(f"  ✅ {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
