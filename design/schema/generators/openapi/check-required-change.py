#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""계약에서 «필수 여부»가 바뀐 자리를 찾아 통지 등급을 묻는다.

왜 필요한가
-----------
2026-08-31 PR #307 리뷰가 잡았다 — `GoodsReceipt`·`GoodsReceiptCreate` 의
`sourceDocumentTypeCode`·`sourceDocumentId` 가 `required` 에서 빠졌는데
**어느 검사기도 잡지 못했다.** `check-enum-narrowing` 은 값 목록만 보고,
`check-structure` 는 계약이 성립하는지만 본다. 등급표도 「필수 승격」만 ⛔ 로
적어 두고 **반대 방향에는 항목이 없었다.** 사람 눈에만 걸렸다.

⛔ 가르는 기준은 «방향»이 아니라 «누가 그 값을 읽는가»다
--------------------------------------------------------
같은 「필수 해제」라도 요청과 응답에서 뜻이 정반대다.

    요청 스키마에서 required 제거   →  ⚠  보내는 쪽이 덜 보내도 된다. 안 깨진다
    요청 스키마에 required 추가     →  ⛔  안 보내던 쪽이 400 을 받는다
    응답 스키마에서 required 제거   →  ⛔  «항상 있던 값이 없어질 수 있다»
                                        널 가드 없는 소비자가 깨진다
    응답 스키마에 required 추가     →  ⚠  더 보장하는 것이라 안 깨진다

`type` 이 nullable 로 넓어지는 것(`"string"` → `["string","null"]`)도 응답에서는
같은 사고다 — required 에 남아 있어도 값이 `null` 로 온다.

⚠ 이 검사기가 «안 보는 것»
--------------------------
- **통지를 실제로 냈는지는 안 본다.** 「필수가 바뀐 자리가 있다」까지만 말한다.
- **요청·응답 판정은 `$ref` 를 한 겹만 따라간다.** 스키마 안에서 다른 스키마를
  품는 중첩(`allOf`·배열 원소)은 그 부모의 방향을 물려받지 못한다 — 그런 자리는
  「방향 미상」으로 내고 사람이 읽는다.
- **새로 생긴 스키마·필드는 세지 않는다.** 없던 것으로는 아무도 코드를 만들지
  않았으므로 깨질 것이 없다(`check-enum-narrowing` 과 같은 기준).
- **서버가 실제로 무엇을 내리는지는 모른다.** 계약이 「비어도 된다」로 바뀐 것과
  서버가 실제로 비워 보내는 것은 다르다. 계약 쪽만 본다.

쓰기
----
    python3 design/schema/generators/openapi/check-required-change.py            # HEAD 대비
    python3 design/schema/generators/openapi/check-required-change.py <기준 커밋>
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                      capture_output=True, text=True, cwd=HERE).stdout.strip()
CONTRACTS_DIR = os.path.join(ROOT, "design", "wiki", "api-contracts", "openapi")

REF = re.compile(r'"#/components/schemas/([^"]+)"')


def roles(doc: dict) -> dict[str, set[str]]:
    """스키마 이름 → {"요청","응답"} — requestBody / responses 에서 한 겹 따라간다."""
    out: dict[str, set[str]] = {}

    def mark(node, role):
        for name in REF.findall(json.dumps(node, ensure_ascii=False)):
            out.setdefault(name, set()).add(role)

    for _path, item in (doc.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for _method, op in item.items():
            if not isinstance(op, dict):
                continue
            if "requestBody" in op:
                mark(op["requestBody"], "요청")
            if "responses" in op:
                mark(op["responses"], "응답")
    return out


def shape(doc: dict) -> dict[str, dict]:
    """스키마.필드 → {"required": bool, "nullable": bool}"""
    out: dict[str, dict] = {}
    for name, schema in (doc.get("components", {}).get("schemas") or {}).items():
        if not isinstance(schema, dict):
            continue
        req = set(schema.get("required") or [])
        for field, prop in (schema.get("properties") or {}).items():
            t = prop.get("type") if isinstance(prop, dict) else None
            nullable = isinstance(t, list) and "null" in t
            out[f"{name}.{field}"] = {"required": field in req, "nullable": nullable}
    return out


def load(ref: str, path: str):
    rel = os.path.relpath(path, ROOT)
    r = subprocess.run(["git", "show", f"{ref}:{rel}"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def role_of(name: str, table: dict[str, set[str]]) -> str:
    r = table.get(name)
    if not r:
        return "미상"
    if r == {"요청"}:
        return "요청"
    if r == {"응답"}:
        return "응답"
    return "요청·응답"


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    blocking: list[str] = []   # ⛔
    notice: list[str] = []     # ⚠
    checked = 0

    for path in sorted(glob.glob(os.path.join(CONTRACTS_DIR, "*.json"))):
        fname = os.path.basename(path)
        old_doc = load(base, path)
        if old_doc is None:
            continue
        with open(path, encoding="utf-8") as f:
            new_doc = json.load(f)

        old, new = shape(old_doc), shape(new_doc)
        table = roles(new_doc)

        for key, now in new.items():
            was = old.get(key)
            if was is None:
                continue                       # 없던 필드 — 깨질 코드가 없다
            checked += 1
            schema_name = key.split(".")[0]
            role = role_of(schema_name, table)

            if was["required"] and not now["required"]:
                line = f"{fname} · {key} [{role}] — required 에서 빠졌다"
                (blocking if role in ("응답", "요청·응답", "미상") else notice).append(line)
            elif not was["required"] and now["required"]:
                line = f"{fname} · {key} [{role}] — required 로 올랐다"
                (blocking if role in ("요청", "요청·응답", "미상") else notice).append(line)

            if not was["nullable"] and now["nullable"]:
                line = f"{fname} · {key} [{role}] — 값이 null 로 올 수 있게 됐다"
                (blocking if role in ("응답", "요청·응답", "미상") else notice).append(line)

    print(f"필수·널 허용 변경 검사 — 기준 {base} · 대조한 필드 {checked}")
    print()

    if blocking:
        print(f"⛔ 변경 통지 «즉시 1건» 대상 {len(blocking)}건 — 이미 만든 것이 틀린다")
        for line in blocking:
            print("   " + line)
        print()
    if notice:
        print(f"⚠ 변경 통지 «차수 마감 묶음» 대상 {len(notice)}건 — 기존은 깨지지 않는다")
        for line in notice:
            print("   " + line)
        print()

    if not blocking and not notice:
        print("✅ 필수 여부·널 허용이 바뀐 자리가 없습니다.")
        return 0

    print("⛔ 이 검사기는 «통지를 냈는지»를 보지 않는다 — 사람이 판단한다.")
    print("   등급 정본: .claude/skills/uiux-client-handoff/SKILL.md 「변경 통지 ⛔/⚠」")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
