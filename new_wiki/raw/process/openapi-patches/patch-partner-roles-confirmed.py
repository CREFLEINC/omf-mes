#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""프론트 회신 4건을 계약에 반영한다 — 역할 어휘 확정 · 단건 경로 · 저장 충돌 보호. 멱등.

무엇을 고치나
-------------
2026-08-16 프론트 정리보고(client#128)와 그에 대한 사용자 확정을 반영한다.

  ① 역할 어휘 다섯을 enum 으로 못박는다   업무 확정 — 더 이상 미확정이 아니다
  ② 거래처 단건 조회 경로를 만든다        「지금 목록에 있는 행」에 매여 있었다
  ③ 역할 교체에 저장 충돌 보호를 붙인다    빠뜨린 것이지 의도가 아니었다

⭐ ①은 「값 목록 미확정이면 enum 을 못박지 않는다」(G-2)의 **해제**다
--------------------------------------------------------------------
G-2 는 «미확정일 때» 규칙이다. 업무가 어휘를 확정했으므로 계약이 그것을
말해야 한다. 침묵하면 계약과 구현이 갈린 채로 남는다 — 프론트는 이미 이
다섯으로 동작 중이다.

⚠ 셋(`CUSTOMER`·`SUBCONTRACTOR`·`OTHER`)은 **철자가 잠정**이다. 뜻은
확정이고 영문 표기만 바뀔 수 있다. 그래도 박는 쪽을 골랐다(2026-08-16
사용자 확정) — 계약이 침묵하는 위험이 철자가 바뀔 위험보다 크다.
바뀌면 ⛔ 변경 통지 대상이다.

⛔ ③을 붙이면 프론트가 이미 만든 것이 틀린다
--------------------------------------------
지금 저장 충돌 토큰 없이 보내고 있다. 그래도 붙이는 쪽을 골랐다 —
**동시 편집 보호가 없는 마스터를 남길 수 없다.** ⛔ 변경 통지로 알린다.

쓰기
----
    python3 deliverables/openapi/patch-partner-roles-confirmed.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "mdm-기준정보.json")

ROLES = ["CUSTOMER", "SUPPLIER", "SUBCONTRACTOR", "DISPOSAL", "OTHER"]
ROLE_DESC = (
    "거래처 역할. 고객사(CUSTOMER) · 공급사(SUPPLIER) · 외주 제작사(SUBCONTRACTOR) · "
    "폐기 업체(DISPOSAL) · 기타(OTHER) 다섯이다. 한 거래처가 여러 역할을 가질 수 있다. "
    "⭐ 2026-08-16 업무 확정 — 어휘 밖 값은 400 이다."
)
ROLE_NOTE = (
    "값 목록이 확정돼 enum 을 못박았다(2026-08-16). 그 전에는 「미확정이면 못박지 "
    "않는다」(공유계약 G-2)로 비워 두었으나, G-2 는 «미확정일 때» 규칙이고 업무가 "
    "확정했으므로 계약이 말해야 한다. ⚠ CUSTOMER·SUBCONTRACTOR·OTHER 는 뜻이 확정이고 "
    "«철자»가 잠정이다 — 다른 표기로 확정되면 ⛔ 변경 통지 대상이다."
)


def detect_indent(original: str, doc: dict) -> int | None:
    body = original.rstrip("\n")
    for candidate in (1, 2, 4):
        if json.dumps(doc, ensure_ascii=False, indent=candidate) == body:
            return candidate
    return None


def main() -> int:
    original = open(CONTRACT, encoding="utf-8").read()
    doc = json.loads(original)
    indent = detect_indent(original, doc)
    if indent is None:
        print("⛔ 원본 들여쓰기를 알아낼 수 없다 — 덮어쓰지 않는다", file=sys.stderr)
        return 1
    tail = original[len(original.rstrip("\n")):]

    schemas = doc["components"]["schemas"]
    paths = doc["paths"]
    for dep in ("Partner", "PartnerRole", "PartnerRolesReplace",
                "ErrorResponse", "ConflictResponse"):
        if dep not in schemas:
            print(f"⛔ 의존 스키마가 없다: {dep}", file=sys.stderr)
            return 1

    was_sorted = list(paths) == sorted(paths)

    # ── ① 역할 어휘 enum
    r = schemas["PartnerRole"]["properties"]["roleTypeCode"]
    r.pop("x-no-example", None)
    r.update({"enum": ROLES, "example": "SUPPLIER",
              "description": ROLE_DESC, "x-internal-note": ROLE_NOTE})
    rep = schemas["PartnerRolesReplace"]["properties"]["roleTypeCodes"]
    rep["items"] = {"type": "string", "enum": ROLES, "example": "SUPPLIER"}

    # 목록 필터도 같은 어휘로 좁힌다 — 화면이 폐기 역할만 고를 때 쓴다
    for prm in paths["/mdm/partners"]["get"]["parameters"]:
        if prm.get("name") == "roleTypeCode":
            prm["schema"] = {"type": "string", "enum": ROLES, "example": "DISPOSAL"}

    # ── ② 거래처 단건 조회
    paths["/mdm/partners/{partnerId}"] = {"get": {
        "tags": ["mdm", "lookup"],
        "summary": "거래처 한 건",
        "description": (
            "⭐ 2026-08-16 신설. 그전에는 목록만 있어 화면의 기본 정보가 "
            "«지금 목록에 실려 있는 행»에 매여 있었다 — 목록을 다시 부르거나 "
            "검색어를 바꾸면 보고 있던 거래처가 사라진다. "
            "⛔ 거래처 본체는 ERP 수신 마스터라 이 경로도 읽기 전용이다 — "
            "고치는 것은 역할뿐이다. 근거: W-06-06 「거래처 역할」 탭 · client#128"),
        "parameters": [{"name": "partnerId", "in": "path", "required": True,
                        "schema": {"type": "integer", "format": "int64",
                                   "example": 1001}}],
        "responses": {
            "200": {"description": "상세", "content": {"application/json": {
                "schema": {"$ref": "#/components/schemas/Partner"}}}},
            "404": {"description": "없다", "content": {"application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorResponse"}}}}}}}

    # ── ③ 역할 교체에 저장 충돌 보호
    put = paths["/mdm/partners/{partnerId}/roles"]["put"]
    names = [p.get("$ref", "").split("/")[-1] for p in put["parameters"]]
    if "IfMatchVersion" not in names:
        put["parameters"].append(
            {"$ref": "#/components/parameters/IfMatchVersion"})
    put["responses"]["409"] = {
        "description": "충돌 — 남이 먼저 고쳤다",
        "content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/ConflictResponse"}}}}
    # ⛔⛔ «덧붙이기»를 하지 않는다. 앞서 「없을 때만 더한다」로 막았는데,
    #    덧붙일 «문구 자체를 고치자» 가드가 못 알아보고 또 붙였다 —
    #    옛 문장(틀린 원천을 가리키는)과 새 문장이 «공존»했고 그것이
    #    공개 계약에 나갔다(구현팀이 읽고 지적했다).
    #    → 머리만 남기고 «통째로 다시 조립»한다. 몇 번을 돌려도 같다.
    MARK = " ⭐ 2026-08-16 보완 —"
    ADDED = (MARK + " 저장 충돌 보호를 붙였다. 통째로 교체하는 저장이라 "
             "보호가 없으면 «남이 방금 붙인 역할»이 조용히 사라진다. "
             "값은 «역할 목록 조회»(GET …/roles)의 ETag 응답 헤더에서 받는다. "
             "⛔ 거래처 단건 조회 쪽이 아니다 — 거래처 본체는 기간계 수신 자료라 동기화마다 "
             "버전이 바뀌어 «역할을 고치지 않은 사용자»까지 저장 충돌을 보게 된다. "
             "잠그는 대상(역할 집합)과 버전 축을 일치시킨다.")
    head = put["description"].split(MARK)[0].rstrip()
    put["description"] = head + ADDED
    put["x-internal-note"] = (
        "빠뜨린 것이지 의도가 아니었다(client#128 이 물어 드러났다). "
        "⛔ 붙이면 프론트가 이미 만든 것이 틀린다 — 지금 토큰 없이 보내고 있어 "
        "⛔ 변경 통지로 알린다. 물리 모델의 mdm.partner_role 에 버전 칸이 있는지는 "
        "확인되지 않았다 — 없으면 계약이 앞서 있는 것이고 모델이 따라온다.")

    # ── ④ ETag 응답 헤더 선언
    #    ⛔ 「응답 헤더에서 받는다」고 써 놓고 그 헤더를 «선언하지 않았다».
    #       partners 전 경로에 0건이었는데 다른 자원 30곳에는 있었다 —
    #       관행이 있는데 안 따른 것이고, 구현팀이 물어서 드러났다(client#174).
    etag = None
    for probe in ("/mdm/warehouses/{warehouseId}", "/mdm/locations/{locationId}"):
        h = ((paths.get(probe, {}).get("get", {}) or {})
             .get("responses", {}).get("200", {}) or {}).get("headers")
        if h and "ETag" in h:
            etag = json.loads(json.dumps(h))   # 관행을 그대로 베낀다
            break
    if etag is None:
        print("⛔ 기존 ETag 선언을 못 찾았다 — 관행을 베낄 수 없다", file=sys.stderr)
        return 1
    roles = paths["/mdm/partners/{partnerId}/roles"]
    roles["get"]["responses"]["200"]["headers"] = etag
    roles["put"]["responses"]["200"]["headers"] = json.loads(json.dumps(etag))

    if was_sorted:
        doc["paths"] = dict(sorted(paths.items()))

    updated = json.dumps(doc, ensure_ascii=False, indent=indent) + tail
    if updated == original:
        print("  이미 반영돼 있다 — 변경 없음")
        return 0
    open(CONTRACT, "w", encoding="utf-8").write(updated)
    print(f"  ✅ 역할 어휘 {len(ROLES)} · 단건 경로 · 저장 충돌 보호 — 경로 {len(doc['paths'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
