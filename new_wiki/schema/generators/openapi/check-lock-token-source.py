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

쓰기
----
    python3 deliverables/openapi/check-lock-token-source.py
"""
from __future__ import annotations

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Tier 0 — OpenAPI JSON 정본. Phase 5 컷오버(2026-08-25)로 new_wiki/wiki/api-contracts/openapi/가 정본 위치다.
CONTRACTS_DIR = os.path.join(HERE, "..", "..", "..", "wiki", "api-contracts", "openapi")


def has_etag(op: dict | None) -> bool:
    if not isinstance(op, dict):
        return False
    return "ETag" in ((op.get("responses", {}).get("200", {}) or {})
                      .get("headers") or {})


def sources(paths: dict, path: str) -> list[str]:
    """이 경로의 토큰을 받을 만한 조회 후보."""
    base = path.split(":")[0]
    out = [base]
    if base.endswith("}"):
        return out
    parent = base.rsplit("/", 1)[0]      # /…/{id}/lines → /…/{id}
    if parent and parent != base:
        out.append(parent)
    return out


def main() -> int:
    missing: list[tuple[str, str, str]] = []
    total = 0

    for f in sorted(glob.glob(os.path.join(CONTRACTS_DIR, "*.json"))):
        name = os.path.basename(f)
        with open(f, encoding="utf-8") as fh:
            doc = json.load(fh)
        paths = doc.get("paths", {})
        for path, ops in paths.items():
            for method, op in ops.items():
                if not isinstance(op, dict):
                    continue
                refs = [p.get("$ref", "").split("/")[-1]
                        for p in op.get("parameters", [])]
                if "IfMatchVersion" not in refs:
                    continue
                total += 1
                if any(has_etag((paths.get(c) or {}).get("get"))
                       for c in sources(paths, path)):
                    continue
                missing.append((name, method.upper(), path))

    if not missing:
        print(f"✅ 저장 충돌 토큰을 받을 곳이 전부 선언돼 있습니다 — {total}곳 검사")
        return 0

    print(f"⚠ 토큰을 받을 곳이 선언되지 않은 오퍼레이션 {len(missing)}건 "
          f"(검사 {total}곳)\n")
    for name, method, path in missing:
        print(f"  {name:<24} {method:<6} {path}")
    print(
        "\n⛔ 자동으로 붙이지 마세요 — 원천이 «부모 자원인가 자식 집합인가»는 판단입니다.\n"
        "   부모가 외부 수신 자료면 동기화마다 버전이 바뀌어, 고치지도 않은\n"
        "   사용자가 저장 충돌을 봅니다(거래처 역할이 그 사례).\n"
        "   ⭐ 기준 — 잠그는 «대상»과 버전 축을 일치시킨다.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
