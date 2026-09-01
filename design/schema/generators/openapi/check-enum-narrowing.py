#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""계약에서 값 목록이 «좁아진» 자리를 찾아 통지 여부를 묻는다.

왜 필요한가
-----------
2026-08-16 프론트가 알려 왔다 — 재고 상태가 자유 문자열에서 네 값으로
좁아졌는데 **변경 통지가 없었다.** 우리 PR 에서 들어갔고 프론트는 타입이
깨져서야 알았다.

    자유 문자열  →  enum      «이미 만든 것이 틀린다»  =  ⛔ 변경 통지 대상
    enum 값 삭제  →  더 좁게    동상

⚠ 값 목록 44종이 확정될 때마다 같은 협착이 일어난다. 한 번짜리가 아니다.

무엇을 보나
-----------
직전 커밋(또는 지정한 기준)과 지금 계약을 대조해 **enum 이 새로 생겼거나
값이 줄어든 자리**를 찾는다. 찾으면 종료 코드 1 — 통지를 냈는지 사람이
확인하게 한다.

⛔ 「새로 생긴 것」과 「좁아진 것」은 다르다 — 2026-08-18 정정
------------------------------------------------------------
처음 판은 **enum 이 기준에 없으면 무조건 협착**으로 셌다. 그래서 **새로 만든
스키마·새로 더한 필드까지 ⛔ 로 울었다.** 05 설비·툴 마스터를 더할 때 다섯 건이
그렇게 잡혔다.

    없던 필드에 enum          →  ⚠ 새로 만들 것이 생긴다   (이 검사기 밖)
    있던 자유 문자열에 enum   →  ⛔ 이미 만든 것이 틀린다   (이 검사기가 잡는다)
    enum 에서 값이 사라짐     →  ⛔ 동상

**가르는 기준은 「그 필드가 기준에 있었는가」다.** 없던 필드로는 아무도 코드를
만들지 않았으므로 깨질 것이 없다. 거짓 경보가 쌓이면 검사기를 무시하게 되고,
그러면 진짜 협착이 지나간다.

⚠ 이 검사기가 못 보는 것
------------------------
**통지를 실제로 냈는지는 안 본다.** 「좁아진 것이 있다」까지만 말한다.
통지 발행 여부는 사람이 판단한다 — 같은 협착이 여러 계약에 걸쳐 한 통지로
나갈 수도 있기 때문이다.

그리고 **넓어진 것은 안 잡는다.** 값이 늘어나는 것은 기존 코드를 깨지
않는다(⚠ 등급이라 차수 마감 때 묶어 낸다).

쓰기
----
    python3 design/schema/generators/openapi/check-enum-narrowing.py            # HEAD 대비
    python3 design/schema/generators/openapi/check-enum-narrowing.py <기준 커밋>
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                      capture_output=True, text=True, cwd=HERE).stdout.strip()
# Tier 0 — OpenAPI JSON 정본. Phase 5 컷오버(2026-08-25)로 design/wiki/api-contracts/openapi/가 정본 위치다.
CONTRACTS_DIR = os.path.join(ROOT, "design", "wiki", "api-contracts", "openapi")


def enums(doc: dict) -> dict[str, list]:
    """스키마 프로퍼티마다 enum 을 모은다 — 없으면 담지 않는다."""
    out: dict[str, list] = {}
    for name, schema in (doc.get("components", {}).get("schemas") or {}).items():
        for field, prop in (schema.get("properties") or {}).items():
            if isinstance(prop, dict) and "enum" in prop:
                out[f"{name}.{field}"] = prop["enum"]
    return out


def fields(doc: dict) -> set[str]:
    """스키마 프로퍼티 이름 전부 — enum 이 있든 없든."""
    out: set[str] = set()
    for name, schema in (doc.get("components", {}).get("schemas") or {}).items():
        for field in (schema.get("properties") or {}):
            out.add(f"{name}.{field}")
    return out


def load(ref: str, path: str) -> dict | None:
    rel = os.path.relpath(path, ROOT)
    r = subprocess.run(["git", "show", f"{ref}:{rel}"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    findings: list[str] = []

    for path in sorted(glob.glob(os.path.join(CONTRACTS_DIR, "*.json"))):
        name = os.path.basename(path)
        old_doc = load(base, path)
        if old_doc is None:
            continue                      # 새 파일 — 협착이 아니다
        with open(path, encoding="utf-8") as f:
            new_doc = json.load(f)
        old, new = enums(old_doc), enums(new_doc)
        old_fields = fields(old_doc)

        for key, values in new.items():
            if key not in old:
                if key not in old_fields:
                    continue          # 없던 필드 — 깨질 코드가 없다(⚠ 등급)
                findings.append(
                    f"{name} · {key} — 자유 문자열이 값 목록으로 좁아졌다 {values}")
                continue
            gone = [v for v in old[key] if v not in values]
            if gone:
                findings.append(
                    f"{name} · {key} — 값이 줄었다: 사라진 값 {gone}")

    if not findings:
        print(f"✅ 값 목록이 좁아진 자리가 없습니다 — 기준 {base}")
        return 0

    print(f"⚠ 값 목록이 좁아진 자리 {len(findings)}건 — 기준 {base}\n")
    for f in findings:
        print("  " + f)
    print(
        "\n⛔ 좁아지는 것은 «이미 만든 것이 틀린다» 라 ⛔ 변경 통지 대상입니다.\n"
        "   통지를 냈으면 그대로 진행하고, 안 냈으면 내고 진행하세요.\n"
        "   → .claude/skills/uiux-client-handoff/")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
