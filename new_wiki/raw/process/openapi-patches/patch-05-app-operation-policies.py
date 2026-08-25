#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""운영 정책 경로를 공통 계약에 더한다 — 타발수 환산이 첫 사용처다. 멱등.

무엇을 더하나
-------------
    /app/operation-policies              조회 · 등록
    /app/operation-policies/{id}         상세 · 수정
    /app/operation-policies/effective    ⭐ 「지금 무엇이 적용되나」 해석

⛔ 삭제 경로를 두지 않는다
--------------------------
「정책 종료」는 유효 종료일을 지정하는 수정이다. **과거 실적이 그 비율로
계산됐다** — 지우면 그때 왜 그 값이 나왔는지 설명할 수 없게 된다.
근거: W-05-01 §5-5.

⭐ 범용 정책 테이블은 «코드 목록» 이 계약이다
---------------------------------------------
표 하나를 여러 화면이 쓴다 — 뜻은 `policyCode` 가 정한다. **코드가 겹치거나
뜻이 갈리면 조용히 틀린다.** 그래서 계약이 목록을 갖는다(W-05-01 §9-1).

    SHOT_CONVERSION_ENABLED     환산을 쓰는가        boolean   품목·공정·공장
    SHOT_CONVERSION_RATIO       수량 대비 타발수     numeric   품목·공정·공장
    MINOR_STOP_THRESHOLD_MINUTES  경미 정지 임계     numeric   공장

⚠ 목록은 늘어난다 — 작업 전 점검 통제 3단계가 이 표를 쓰기로 돼 있으나
**소유 화면이 아직 정해지지 않았다**(P-02-02 소관). 값이 늘어나는 것은 기존
코드를 깨지 않으므로 ⚠ 등급이다.

⛔ 화면이 코드를 자유 입력하게 두지 않는다
------------------------------------------
사용자는 「환산 사용」 체크와 「비율」만 본다. **코드는 화면이 붙인다.**
기계가 정할 수 있는 것을 사람에게 묻지 않는다.

⭐ 범위 해석은 «더 좁은 것이 이긴다» — 서버가 판정한다
------------------------------------------------------
네 축이 전부 비어 있을 수 있어 여러 정책이 동시에 맞는다. 축 우선순위는
**품목 > 공정 > 공장 > 사업부**로 못박았다(W-05-01 §5-2 · 공유계약 B-17).

⛔ **화면이 이 규칙을 다시 구현하게 두지 않는다** — `effective` 경로가 「어느
정책이 이겼는가」와 「왜 그렇게 됐는가」를 함께 내린다. 화면마다 구현하면
같은 표가 화면마다 다르게 읽힌다.

⭐ 비율은 0보다 커야 한다 — 물리 제약이 막지 않는다
---------------------------------------------------
0 이면 타발수가 늘 0이라 **예방보전이 영영 오지 않고**, 음수면 누계가 줄어든다.
서버가 진다(공유계약 A-9 등급 2). 1 을 넘는 것은 막지 않고 경고만 한다 — 한 번에
여러 번 타발하는 공정이 있을 수 있다.

📨 물리 표는 실재한다 — 없는 것은 «경로» 였다
---------------------------------------------
`app.operation_policy` 는 있고 형태가 맞는다(W-05-01 §3-1 이 여섯 항목을 단계별로
확인했고 툴 축만 없었으며 그것은 캐비티 수가 이미 담는다). **1단계가 「계약에
없다」로 잡은 넷 중 하나**다.

쓰기
----
    python3 deliverables/openapi/patch-05-app-operation-policies.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "app-공통.json")

POLICY_CODES = ["SHOT_CONVERSION_ENABLED", "SHOT_CONVERSION_RATIO",
                "MINOR_STOP_THRESHOLD_MINUTES"]

POLICY_CODE_DESC = (
    "무엇을 정하는 정책인가. SHOT_CONVERSION_ENABLED = 생산 수량으로 타발수를 "
    "환산할지(valueBoolean). SHOT_CONVERSION_RATIO = 수량 대비 타발수 비율"
    "(valueNumeric · 0 보다 커야 한다). MINOR_STOP_THRESHOLD_MINUTES = 경미 정지로 "
    "볼 시간 임계(valueNumeric · 기본 5). 코드는 화면이 붙인다 — 사용자가 만들지 않는다"
)

VALUE_NOTE = (
    "값 칸은 셋 중 하나만 쓴다. 물리 제약은 「셋 중 하나 이상」이라 셋 다 채워도 "
    "통과하지만, 어느 칸을 쓰는지는 정책 코드가 정한다 — 쓰지 않는 칸을 채우면 읽는 "
    "쪽이 헷갈린다"
)

SCOPE_NOTE = (
    "범위 축은 넷 다 비울 수 있고 비면 전체를 뜻한다. 여럿이 동시에 맞으면 "
    "더 좁은 것이 이기며 축 우선순위는 품목 · 공정 · 공장 · 사업부 차례다. "
    "이 판정은 서버가 하고 화면은 effective 경로로 결과를 받는다"
)

IDEM = {"$ref": "#/components/parameters/IdempotencyKey"}


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


def ok(desc: str, schema: str) -> dict:
    return {"description": desc,
            "content": {"application/json":
                        {"schema": {"$ref": "#/components/schemas/%s" % schema}}}}


SCOPE_PROPS = {
    "businessUnitId": nullable("integer", 1001, format="int64",
                               **{"x-source-column": "business_unit_id"}),
    "plantId": nullable("integer", 1001, format="int64",
                        **{"x-source-column": "plant_id"}),
    "itemId": nullable("integer", 1001, format="int64",
                       **{"x-source-column": "item_id"}),
    "processId": nullable("integer", 1001, format="int64",
                          **{"x-source-column": "process_id"}),
}

VALUE_PROPS = {
    "valueText": nullable("string", "표준", maxLength=200,
                          **{"x-source-column": "value_text"}),
    "valueNumeric": nullable("number", 0.25, **{"x-source-column": "value_numeric"}),
    "valueBoolean": nullable("boolean", True, **{"x-source-column": "value_boolean"}),
}

PERIOD_PROPS = {
    "effectiveFrom": prop("string", "2026-01-01", format="date",
                          **{"x-source-column": "effective_from"}),
    "effectiveTo": nullable("string", "2026-12-31", format="date",
                            description="비면 끝이 없다",
                            **{"x-source-column": "effective_to"}),
}

SCHEMAS = {
    "OperationPolicy": {
        "x-source-table": "app.operation_policy",
        "type": "object",
        "required": ["operationPolicyId", "policyCode", "effectiveFrom"],
        "description": ("운영 정책 한 건. 표 하나를 여러 화면이 쓰고 뜻은 policyCode 가 "
                        "정한다. " + SCOPE_NOTE + ". " + VALUE_NOTE +
                        ". 근거: W-05-01 §5-A"),
        "x-internal-note": ("코드 목록이 계약 자산이다 — W-05-01 §9-1. 작업 전 점검 통제 "
                            "3단계도 이 표를 쓰기로 돼 있으나 소유 화면이 정해지지 않아 "
                            "코드를 아직 넣지 않았다(P-02-02 소관 · W-05-12 §8-7)."),
        "properties": dict(
            {"operationPolicyId": prop("integer", 1001, format="int64",
                                       **{"x-source-column": "operation_policy_id"}),
             "policyCode": prop("string", "SHOT_CONVERSION_RATIO", maxLength=50,
                                enum=list(POLICY_CODES),
                                description=POLICY_CODE_DESC,
                                **{"x-source-column": "policy_code"})},
            **dict(SCOPE_PROPS, **dict(VALUE_PROPS, **PERIOD_PROPS))),
    },
    "OperationPolicyCreate": {
        "type": "object",
        "required": ["policyCode", "effectiveFrom"],
        "description": VALUE_NOTE + ". " + SCOPE_NOTE,
        "properties": dict(
            {"policyCode": prop("string", "SHOT_CONVERSION_RATIO", maxLength=50,
                                enum=list(POLICY_CODES),
                                description=POLICY_CODE_DESC)},
            **dict(SCOPE_PROPS, **dict(VALUE_PROPS, **PERIOD_PROPS))),
    },
    "OperationPolicyUpdate": {
        "type": "object",
        "required": ["effectiveFrom"],
        "description": ("정책 코드와 범위 축은 바꾸지 않는다 — 바꾸면 다른 정책이 된다. "
                        "종료는 effectiveTo 를 지정하는 수정이며 삭제 경로는 없다"),
        "properties": dict(VALUE_PROPS, **PERIOD_PROPS),
    },
    "OperationPolicyEffective": {
        "type": "object",
        "required": ["policyCode", "resolved"],
        "description": ("주어진 범위에 결국 무엇이 적용되는가와 그렇게 정해진 근거. "
                        "설정 화면의 미리보기와 계산하는 쪽이 함께 쓴다. "
                        "근거: W-05-01 §5-2 · 공유계약 B-17"),
        "properties": {
            "policyCode": prop("string", "SHOT_CONVERSION_RATIO", maxLength=50,
                               enum=list(POLICY_CODES)),
            "resolved": prop("boolean", True,
                             description=("거짓이면 맞는 정책이 없다. 화면은 기본값을 지어내 "
                                          "그리지 않고 「적용 정책 없음」으로 밝힌다")),
            "operationPolicyId": nullable("integer", 1001, format="int64"),
            "valueText": nullable("string", "표준", maxLength=200),
            "valueNumeric": nullable("number", 0.25),
            "valueBoolean": nullable("boolean", True),
            "matchedScopeCode": nullable(
                "string", "ITEM",
                description=("이긴 정책이 어느 축으로 맞았는가 — ITEM · PROCESS · PLANT · "
                             "BUSINESS_UNIT · ALL 중 하나. resolved 가 거짓이면 비어 있다")),
        },
    },
}

PATHS = {
    "/app/operation-policies": {
        "get": {
            "tags": ["app"], "summary": "운영 정책 목록",
            "description": "근거: W-05-01 §4 ② 비율 정책",
            "parameters": [
                {"name": "policyCode", "in": "query",
                 "schema": {"type": "string", "enum": list(POLICY_CODES)}},
                {"name": "businessUnitId", "in": "query",
                 "schema": {"type": "integer", "format": "int64"}},
                {"name": "plantId", "in": "query",
                 "schema": {"type": "integer", "format": "int64"}},
                {"name": "itemId", "in": "query",
                 "schema": {"type": "integer", "format": "int64"}},
                {"name": "processId", "in": "query",
                 "schema": {"type": "integer", "format": "int64"}},
                {"name": "effectiveOn", "in": "query",
                 "schema": {"type": "string", "format": "date"},
                 "description": "이 날에 유효한 것만 본다. 비우면 끝난 것까지 함께 본다"},
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
                                  "items": {"$ref": "#/components/schemas/OperationPolicy"}},
                        "page": {"$ref": "#/components/schemas/PageMeta"},
                    }}}}}},
        },
        "post": {
            "tags": ["app"], "summary": "운영 정책 등록",
            "description": ("같은 코드·같은 범위·같은 시작일은 한 건만 둔다 — 어긋나면 "
                            "유일 범위를 담아 돌려준다. 근거: W-05-01 §5-5 · 공유계약 A-7"),
            "parameters": [IDEM],
            "requestBody": {"required": True,
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/OperationPolicyCreate"}}}},
            "responses": {
                "201": ok("등록됨", "OperationPolicy"),
                "400": err("검증 실패 — 비율이 0 이하이거나 종료일이 시작일보다 빠르다"),
                "403": err("권한 없음")},
        },
    },
    "/app/operation-policies/effective": {
        "get": {
            "tags": ["app"], "summary": "이 범위에 적용되는 정책",
            "description": ("범위 해석을 서버가 한다 — 화면이 우선순위를 다시 구현하지 "
                            "않는다. 범위 축은 비워서 보내도 되며 비운 축은 「지정 없음」으로 "
                            "친다. 근거: W-05-01 §4 ③ 미리보기"),
            "parameters": [
                {"name": "policyCode", "in": "query", "required": True,
                 "schema": {"type": "string", "enum": list(POLICY_CODES)}},
                {"name": "businessUnitId", "in": "query",
                 "schema": {"type": "integer", "format": "int64"}},
                {"name": "plantId", "in": "query",
                 "schema": {"type": "integer", "format": "int64"}},
                {"name": "itemId", "in": "query",
                 "schema": {"type": "integer", "format": "int64"}},
                {"name": "processId", "in": "query",
                 "schema": {"type": "integer", "format": "int64"}},
                {"name": "on", "in": "query",
                 "schema": {"type": "string", "format": "date"},
                 "description": "판정 기준일. 비우면 오늘"},
            ],
            "responses": {"200": ok("해석 결과", "OperationPolicyEffective")},
        },
    },
    "/app/operation-policies/{operationPolicyId}": {
        "parameters": [{"name": "operationPolicyId", "in": "path", "required": True,
                        "schema": {"type": "integer", "format": "int64"}}],
        "get": {
            "tags": ["app"], "summary": "운영 정책 상세",
            "description": "근거: W-05-01 §5-A",
            "responses": {"200": ok("상세", "OperationPolicy")},
        },
        "put": {
            "tags": ["app"], "summary": "운영 정책 수정",
            "description": ("정책을 끝내려면 effectiveTo 를 지정한다 — 삭제 경로는 없다. "
                            "과거 실적이 그때의 값으로 계산됐기 때문이다. 근거: W-05-01 §5-5"),
            "parameters": [IDEM],
            "requestBody": {"required": True,
                            "content": {"application/json": {
                                "schema": {"$ref": "#/components/schemas/OperationPolicyUpdate"}}}},
            "responses": {
                "200": ok("수정됨", "OperationPolicy"),
                "400": err("검증 실패 — 비율이 0 이하이거나 종료일이 시작일보다 빠르다"),
                "403": err("권한 없음")},
            "x-internal-note": ("저장 충돌 보호를 붙이지 않았다 — 2단계 §7 이 정한 여섯 곳에 "
                                "정책이 없다. 목록에서 한 행씩 고치는 형태이고 대상을 오가며 "
                                "묶음을 교체하지 않아 공유계약 G-30 의 두 조건에 닿지 않는다."),
        },
    },
}


def main() -> int:
    with open(CONTRACT, encoding="utf-8") as fh:
        spec = json.load(fh)
    before = json.dumps(spec, ensure_ascii=False, sort_keys=True)

    spec["components"]["schemas"].update(SCHEMAS)
    spec["paths"].update(PATHS)

    after = json.dumps(spec, ensure_ascii=False, sort_keys=True)
    with open(CONTRACT, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(spec, ensure_ascii=False, indent=2) + "\n")

    print("경로 %d · 스키마 %d" % (len(spec["paths"]), len(spec["components"]["schemas"])))
    print("바뀐 것이 %s" % ("없다 — 이미 반영돼 있다" if before == after else "있다"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
