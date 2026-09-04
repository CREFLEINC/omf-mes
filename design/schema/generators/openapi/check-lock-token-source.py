#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""저장 충돌 토큰을 «받을 곳»이 계약에 있는가.

왜 필요한가
-----------
2026-08-17 구현팀이 물어 드러났다 — 거래처 역할 저장이 `If-Match` 를
필수로 받는데 **그 값을 어디서 받는지가 계약에 없었다.** 「응답 헤더에서
받는다」라고 설명문에만 적고 그 헤더를 «선언하지 않았다».

⚠ 한 건이 아니었다. 실측하니 같은 형태가 **28곳** 더 있었다.

무엇을 보나
-----------
`If-Match` 를 필수로 받는 오퍼레이션마다, **그 값을 받을 조회가 `ETag` 를
선언하는지** 본다. 후보를 둘 본다.

    ① 같은 경로의 GET                  /mdm/warehouses/{id}
    ② 부모 경로의 GET                  /…/{id}/lines  →  /…/{id}

②로만 풀리는 자리(부모의 토큰을 «빌리는» 자리)는 **그 사실을 오퍼레이션
`description` 이 적었는지**까지 본다 — 공유계약 **B-1-1** ②.

세 번째로, **현장 단말·모바일 전용 오퍼레이션에 잠금 토큰이 «필수»로
걸렸는지** 본다. 오프라인 큐 전송은 토큰을 싣지 않는다(공유계약 **C-9**).

⛔ 자동으로 붙이지 않는다 — «어느 쪽이 원천인가»는 판단이다
-----------------------------------------------------------
거래처 역할이 그 예다. 부모(거래처 본체)는 기간계 수신 자료라 동기화마다
버전이 바뀌어, **역할을 고치지 않은 사용자까지 저장 충돌을 본다.**
그래서 원천을 자식 집합(역할 목록)으로 잡았다.

**잠그는 대상과 버전 축을 일치시킨다** — 이 판단을 기계가 대신할 수 없다.
검사기는 «판단이 필요한 자리»를 드러내기만 한다.

⚠ 이 검사기가 못 보는 것
------------------------
**원천이 «맞는지»는 안 본다.** 선언이 있으면 통과한다. 거래처 역할도
잘못된 원천(거래처 단건)을 가리킨 채로 통과했을 것이다.

계약 파일을 넘는 원천도 본다 — 원천이 다른 계약에 있는 자리가 실재한다
(POST /quality/nonconformances/{nonconformanceId}/disposition-decisions 의
원천은 shipment-04제품출하.json 이 갖는다). 7벌을 병합해 찾는다.

⛔ **`IfMatchVersionOptional` 은 검사 대상이 «아니다».** `refs` 를 마지막 경로 조각으로
비교하므로 `IfMatchVersionOptional` 은 `IfMatchVersion` 과 다른 이름으로 걸러진다.
즉 **오프라인 완화가 그대로 검사 이탈**이다.

⛔ **빨간불을 «완화»로 끄지 마라.** `IfMatchVersionOptional` 로 바꾸면 이 검사기는
초록이 되지만 **결손은 그대로 남는다.** 원천(ETag 를 내는 GET)을 세우는 것이 옳은 해소다.

⭐ **완화가 옳은 자리인지는 `check-offline-consistency.py` 가 본다** — 그쪽이
「이 오퍼레이션을 부르는 화면이 실제로 오프라인인가」를 대조한다.

쓰기
----
    python3 design/schema/generators/openapi/check-lock-token-source.py
"""
from __future__ import annotations

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Tier 0 — OpenAPI JSON 정본. Phase 5 컷오버(2026-08-25)로 design/wiki/api-contracts/openapi/가 정본 위치다.
CONTRACTS_DIR = os.path.join(HERE, "..", "..", "..", "wiki", "api-contracts", "openapi")

HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")

LOCK_REF = "IfMatchVersion"          # ⛔ IfMatchVersionOptional 은 다른 이름이라 걸러진다
WORKER_REF = "WorkerNo"              # ⛔ WorkerNoOptional 은 대상이 아니다


def has_etag(op: dict | None) -> bool:
    if not isinstance(op, dict):
        return False
    return "ETag" in ((op.get("responses", {}).get("200", {}) or {})
                      .get("headers") or {})


def named_sources(desc: str, merged: dict) -> list[str]:
    """description 이 «이름으로 지목한» 조회 경로 중 실제로 ETag 를 내는 것.

    ⛔ 자동 추론이 아니다 — 설계가 **문장으로 적은 것만** 인정한다. 이 검사기의
       ⛔ 안내(「원천이 부모 자원인가 자식 집합인가는 판단입니다」)를 그대로 지킨다.
    ⭐ 왜 필요한가 — 토큰 원천이 «판별자로 갈리는» 경로가 생겼다(2026-09-04 ·
       `omf-mes#352`). `POST /logistics/document-progress/{documentTypeCode}/{documentId}:cancel`
       의 원천은 `documentTypeCode` 값에 따라 **세 리소스**로 갈린다. `sources()` 는
       「자기 경로 · 한 단계 부모」 둘만 보므로 그런 자리를 «선언할 방법이 없었다» —
       설계가 description 에 원천을 또박또박 적어도 검사기가 못 읽고 ⛔ 를 냈다.
    ⚠ 느슨해지지 않는다 — 지목한 경로가 **실재하고 그 GET 이 ETag 를 내야** 인정한다.
       존재하지 않는 경로를 적으면 여전히 걸린다.
    """
    return [p for p in merged
            if p in desc and has_etag((merged.get(p) or {}).get("get"))]


def sources(path: str) -> list[str]:
    """이 경로의 토큰을 받을 만한 조회 후보. [0]=자기 경로 · [1:]=부모."""
    base = path.split(":")[0]
    out = [base]
    if base.endswith("}"):
        return out
    parent = base.rsplit("/", 1)[0]      # /…/{id}/lines → /…/{id}
    if parent and parent != base:
        out.append(parent)
    return out


def load_contracts() -> tuple[dict, list]:
    """계약 7벌을 «하나의 paths 사전»으로 병합한다.

    ⭐ 병합이 핵심이다 — 원천(ETag 를 내는 GET)이 «다른 계약 파일»에 있는 자리가
    실재한다. 파일마다 따로 보면 그 자리를 오탐으로 낸다.

    반환 → (병합 paths, [(파일, 경로, 메서드, 오퍼레이션, 경로항목)])
    위반 보고의 파일명은 «오퍼레이션이 있는 파일»을 그대로 쓴다.
    """
    merged: dict = {}
    ops: list = []
    for f in sorted(glob.glob(os.path.join(CONTRACTS_DIR, "*.json"))):
        name = os.path.basename(f)
        with open(f, encoding="utf-8") as fh:
            doc = json.load(fh)
        for path, item in (doc.get("paths") or {}).items():
            if not isinstance(item, dict):
                continue
            merged.setdefault(path, {}).update(item)
            for method in [m for m in item if m.lower() in HTTP_METHODS]:
                op = item[method]
                if isinstance(op, dict):
                    ops.append((name, path, method, op, item))
    return merged, ops


def param_names(item: dict, op: dict) -> set[str]:
    """경로 단위 ＋ 오퍼레이션 단위 파라미터 참조의 마지막 조각."""
    params = list(item.get("parameters") or []) + list(op.get("parameters") or [])
    return {p.get("$ref", "").split("/")[-1]
            for p in params if isinstance(p, dict) and "$ref" in p}


def main() -> int:
    merged, ops = load_contracts()

    missing: list[tuple[str, str, str]] = []
    unnamed: list[tuple[str, str, str, str]] = []
    offline_locked: list[tuple[str, str, str]] = []
    borrowed = 0
    declared = 0
    total = 0

    for name, path, method, op, item in ops:
        refs = param_names(item, op)

        # ③ 현장 단말·모바일 «전용» 쓰기에 잠금 토큰이 필수로 걸렸는가
        #    판정 근거 — WorkerNo(required) 컴포넌트의 x-internal-note 가
        #    「현장 단말·모바일 전용 오퍼레이션에는 WorkerNo(required)를 그대로
        #    쓴다」로 그 뜻을 이미 못박고 있다. 즉 WorkerNo 필수 = 현장 전용이고
        #    거기에 IfMatchVersion(필수)이 걸리면 C-9 위반이다.
        #    WorkerNoOptional(관리웹 겸용)은 대상이 아니다.
        if LOCK_REF in refs and WORKER_REF in refs:
            offline_locked.append((name, method.upper(), path))

        if LOCK_REF not in refs:
            continue
        total += 1

        cands = sources(path)
        if has_etag((merged.get(cands[0]) or {}).get("get")):
            continue
        desc = op.get("description") or ""
        parent = next((c for c in cands[1:]
                       if has_etag((merged.get(c) or {}).get("get"))), None)
        if parent is None:
            # ④ 판별자로 «갈리는» 원천 — 부모가 하나가 아니라 sources() 로는 못 찾는다.
            #    설계가 description 에 이름으로 지목했고 그 경로가 실제로 ETag 를 내면
            #    그것을 원천 선언으로 인정한다(named_sources 주석 참조).
            if named_sources(desc, merged) and "ETag" in desc:
                declared += 1
                continue
            missing.append((name, method.upper(), path))
            continue

        # ② 부모의 토큰을 «빌리는» 자리 — 어느 축인지 description 이 적었나
        borrowed += 1
        if parent not in desc or "ETag" not in desc:
            unnamed.append((name, method.upper(), path, parent))

    if not (missing or unnamed or offline_locked):
        print(f"✅ 저장 충돌 토큰을 받을 곳이 전부 선언돼 있습니다 — {total}곳 검사"
              f" (부모 빌림 {borrowed}곳 · 판별자로 갈려 «이름으로 지목» {declared}곳"
              f" · 축 전건 명시)")
        return 0

    if missing:
        print(f"⚠ 토큰을 받을 곳이 선언되지 않은 오퍼레이션 {len(missing)}건 "
              f"(검사 {total}곳)\n")
        for name, method, path in missing:
            print(f"  {name:<24} {method:<6} {path}")
        print(
            "\n⛔ 자동으로 붙이지 마세요 — 원천이 «부모 자원인가 자식 집합인가»는 판단입니다.\n"
            "   부모가 외부 수신 자료면 동기화마다 버전이 바뀌어, 고치지도 않은\n"
            "   사용자가 저장 충돌을 봅니다(거래처 역할이 그 사례).\n"
            "   ⭐ 기준 — 잠그는 «대상»과 버전 축을 일치시킨다.\n")

    if unnamed:
        print("⚠ 부모 자원의 토큰을 빌리면서 어느 축인지 적지 않은 오퍼레이션 "
              f"{len(unnamed)}건 — 공유계약 B-1-1\n")
        for name, method, path, parent in unnamed:
            print(f"  {name:<24} {method:<6} {path}")
            print(f"  {'':<24} {'':<6}   ↳ 원천 = GET {parent}")
        print("\n   ⭐ 오퍼레이션 description 에 «부모 경로»와 «ETag» 를 한 문장으로 적는다.\n"
              "   ⛔ x-internal-note 에만 적지 않는다 — 구현팀은 pnpm gen:api 가 옮기는\n"
              "      description 을 읽고 내부 주석은 공개되지 않는다.\n")

    if offline_locked:
        print("⛔ 현장 단말·모바일 전용 오퍼레이션에 잠금 토큰이 «필수»로 걸려 있습니다 "
              f"{len(offline_locked)}건 — 오프라인 큐 전송은 토큰을 싣지 않습니다"
              "(공유계약 C-9). IfMatchVersionOptional 로 바꾸세요.\n")
        for name, method, path in offline_locked:
            print(f"  {name:<24} {method:<6} {path}")
        print()

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
