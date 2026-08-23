#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""운영 정책(`/app/operation-policies/{id}`)에 저장 충돌 보호를 붙인다. 멱등.

무엇을 고치나
-------------
    GET  /app/operation-policies/{id}   → 200 에 `ETag` 응답 헤더
    PUT  /app/operation-policies/{id}   → `If-Match` 요청 헤더 · 200 에 `ETag` · `409`

⭐ 왜 — 구현팀 질의 `omf-mes#210` 이 옳았다
-------------------------------------------
타발수 환산 파라미터 설정 화면(`W-05-01`)의 스펙은 저장 충돌을 이미 확정해
두었다 — §5-5 상태 그래프에 「충돌(B-1)」이 있고 §6 예외표에 「저장 충돌 →
배너 + 다시 불러오기(B-1)」가 있다. **계약에만 없었다.**

⛔ 원래 붙어 있던 내부 주석의 «근거가 틀렸다»
---------------------------------------------
그 자리에는 이런 주석이 있었다.

    「저장 충돌 보호를 붙이지 않았다 — 2단계 §7 이 정한 여섯 곳에 정책이 없다.
      목록에서 한 행씩 고치는 형태이고 대상을 오가며 묶음을 교체하지 않아
      공유계약 G-30 의 두 조건에 닿지 않는다.」

**두 가지가 어긋난다.**

① **`G-30` 의 주어가 다르다.** `G-30` 은 「**나가는 중인 저장** — 막는 범위와
   보이는 범위가 다르다」이다. 저장 요청이 서버로 나가는 동안 **화면을 어디까지
   잠그고 진행 표시를 어디에 그리는가**를 정하는 조항이지, **낙관적 잠금**
   (저장할 때 판을 대조해 남이 먼저 고쳤는지 잡는 것)을 어디에 붙일지 정하는
   조항이 아니다. 낙관적 잠금의 정본은 **`B-1`**(✓확정 2026-08-02)이고,
   그 주어는 「**`version_no` 를 가진 모든 화면**」이다.

② **같은 표 안에서 기준이 다르게 적용됐다.** 2단계 §7 이 「붙인다」로 든
   `/mdm/molds/{id}` · `/mdm/equipments/{id}` · `/mdm/spare-parts/{id}` 는
   **묶음을 통째로 교체하지 않는다**(조건 ①에 안 걸린다). 사유란도
   「목록에서 대상을 골라 옆에서 고친다」 — **조건 ②만** 적었다. 운영 정책은
   생김새가 똑같다(`W-05-01` §4 — ② 비율 정책 목록 + 「정책 추가」 + 행 편집).
   **같은 형태에 다른 잣대를 댔다.**

⭐ 실측이 갈랐다 — `version_no` 가 있다
---------------------------------------
    app.operation_policy.version_no   integer NOT NULL DEFAULT 1 CHECK (> 0)
    (물리 모델 `mes_postgresql_physical_model.sql`)

`B-1` 의 주어에 그대로 들어간다. **추론이 아니라 실측으로 닫힌다.**

⚠ 전수로 봤다 — 이 자리 하나다
-------------------------------
계약 일곱 벌의 **단일 행 자원 `PUT`** 중 `If-Match` 가 없는 곳은 **둘**이었다.
나머지 하나(`/logistics/shipment-lot-allocations/{id}`)는 **정당하다** —
`logistics.shipment_lot_allocation` 에 `version_no` 가 **없고**(실측), 계약도
그 사실을 주석에 적어 두었다. **고칠 곳은 운영 정책 하나뿐이다.**

⛔ 문구를 손으로 쓰지 않는다
---------------------------
`ETag`·`409` 의 설명문은 **같은 계약 안에 이미 있는 선언을 베낀다.** 손으로
쓰면 30곳과 갈리고, 갈린 것은 나중에 아무도 못 찾는다.

쓰기
----
    python3 deliverables/openapi/patch-210-operation-policy-lock.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "app-공통.json")
PATH = "/app/operation-policies/{operationPolicyId}"

NOTE = (
    "저장 충돌 보호를 붙였다(omf-mes#210). app.operation_policy 에 version_no 가 "
    "실재하므로 공유계약 B-1(version_no 를 가진 «모든» 화면)의 주어에 그대로 들어간다. "
    "⚠ 이전 주석은 G-30 의 두 조건을 근거로 붙이지 않았는데 «주어가 다른 조항»이었다 — "
    "G-30 은 「나가는 중인 저장」의 화면 잠금 범위를 정하는 조항이고 낙관적 잠금의 "
    "정본은 B-1 이다. 정책은 설비담당·생산관리가 «같은 표»를 보고 고치며 이 값이 "
    "타발수 계산의 입력이라, 없으면 나중 저장이 앞 사람 값을 조용히 덮는다. "
    "근거: W-05-01 §5-5·§6"
)


def find_decl(doc: dict, code: str, kind: str):
    """이 계약 안에 이미 있는 선언을 찾아 베낀다."""
    for path, ops in doc.get("paths", {}).items():
        for name, op in ops.items():
            if not isinstance(op, dict) or name not in ("get", "put", "post"):
                continue
            resp = (op.get("responses") or {}).get(code) or {}
            if kind == "headers" and "ETag" in (resp.get("headers") or {}):
                return resp["headers"]
            if kind == "response" and resp.get("content"):
                ref = resp["content"].get("application/json", {}).get("schema", {})
                if ref.get("$ref", "").endswith("/ConflictResponse"):
                    return resp
    return None


def detect_indent(original: str, doc: dict):
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
        print("⛔ 들여쓰기를 알아낼 수 없다 — 덮어쓰지 않는다", file=sys.stderr)
        return 1
    tail = original[len(original.rstrip("\n")):]

    etag = find_decl(doc, "200", "headers")
    conflict = find_decl(doc, "409", "response")
    if not etag or not conflict:
        print("⛔ 베낄 선언을 이 계약에서 못 찾았다", file=sys.stderr)
        return 1

    node = doc["paths"].get(PATH)
    if node is None:
        print(f"⛔ {PATH} 가 없다", file=sys.stderr)
        return 1

    # ① 조회 — 토큰을 «받을 곳»
    node["get"]["responses"]["200"]["headers"] = json.loads(json.dumps(etag))

    # ② 수정 — 토큰을 «싣는 곳» · 되받는 곳 · 충돌 응답
    put = node["put"]
    params = put.setdefault("parameters", [])
    if not any(p.get("$ref", "").endswith("/IfMatchVersion") for p in params):
        params.append({"$ref": "#/components/parameters/IfMatchVersion"})
    put["responses"]["200"]["headers"] = json.loads(json.dumps(etag))
    put["responses"]["409"] = json.loads(json.dumps(conflict))
    put["x-internal-note"] = NOTE

    updated = json.dumps(doc, ensure_ascii=False, indent=indent) + tail
    if updated == original:
        print("  이미 반영돼 있다 — 변경 없음")
        return 0
    open(CONTRACT, "w", encoding="utf-8").write(updated)
    print("  ✅ app-공통.json — 운영 정책 조회·수정에 ETag · If-Match · 409")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
