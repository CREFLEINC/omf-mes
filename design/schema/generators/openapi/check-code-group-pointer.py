#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""계약이 가리킨 공통코드 «그룹 이름»이 등록부 안의 것인가.

왜 필요한가
-----------
공유계약 **G-32** — 화면이 값 목록을 부를 때 그룹을 `codeGroupCode`(문자열)로
가리킨다. 채번 식별자(`codeGroupId`)는 환경마다 달라 하드코딩하면 다른
환경에서 «조용히 빈 목록»을 받고 그 화면의 주 기능이 막힌다.

⛔ **오류가 나지 않아 눈에 안 띈다.** 등록부(`mdm.code_group` 에 그 행이
«있는» 이름)에 없는 이름을 계약에 적으면 화면은 오류 없이 빈 목록을 받는다 —
그것이 G-32 가 막으려던 바로 그 실패다.

⚠ **이름을 «도출»할 수 있는 것과 그 행이 «있는» 것은 다른 문제다.**
G-32 의 「그룹 이름 짓는 규칙」은 이름을 *짓는* 법이고, 이 등록부는 이름이
*있는가* 다. 규칙만 보고 지어낸 이름은 이 검사기가 잡는다.

⭐ **등록부 목록은 이 파일에 없다**(2026-09-02 이관) — 공유계약 G-32 의
«등록부 표»를 읽는다. 조항이 정본이고 **사본이 없다.**

무엇을 보나
-----------
① ⛔ **`codeGroupCode=<이름>` 포인터가 등록부 밖**인 자리 — 문서 안의 모든
   `description` 을 본다(자리를 열거하지 않고 훑는다).
   2026-09-01 확장 — 프로퍼티만 보다가 `JUDGMENT_TYPE` 을 놓쳤다.
   전건 출력하고 종료 코드 1 을 낸다.
② ⚠ `enum` 도 `codeGroupCode=` 포인터도 `x-no-example` 도 없는 `*Code` 자리.
   **개수와 상위 파일만** 찍고 종료 코드를 바꾸지 않는다.

⛔ 왜 ②를 게이트로 걸지 않나
----------------------------
「`enum` 없는 `*Code` 는 포인터나 `x-no-example` 중 하나를 반드시 가진다」를
게이트로 걸면 **기준선이 361자리 빨강**이다(2026-08-29 실측). 이 회차의 어떤
반영으로도 닫히지 않는 수라, 걸면 «초록을 기준선으로 쓸 수 없게» 된다.
그래서 **닫을 수 있는 것만** 게이트로 건다. ②는 흐름을 보는 계수기다.

⚠ 이 검사기가 못 보는 것
------------------------
  - 등록부에 «있는» 이름을 «틀린 자리»에 쓴 것 — 이름이 맞으면 통과한다
  - `description` **밖**(예시·`x-` 확장·본문 산문)에 적힌 그룹 이름 — `description`
    키만 보고, 그 안에서도 포인터 형태만 본다
  - 그룹에 실제로 «값이 들어 있는가» — 계약이 답할 수 있는 물음이 아니다

쓰기
----
    python3 design/schema/generators/openapi/check-code-group-pointer.py
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
# Tier 0 — OpenAPI JSON 정본. Phase 5 컷오버(2026-08-25)로 design/wiki/api-contracts/openapi/가 정본 위치다.
CONTRACTS_DIR = os.path.join(HERE, "..", "..", "..", "wiki", "api-contracts", "openapi")

# 등록부 — ⭐ **여기에 목록이 없다.** 공유계약 G-32 의 «등록부 표»를 읽는다.
# 2026-09-02 이관 전까지 이 자리에는 56개를 손으로 적은 집합이 있었고, 조항 산문과
# «따로» 갈라져 있었다. 실측 — 조항의 「확정된 것 —」 문장은 그중 52 만 담고 있었고
# RECEIPT_TYPE·ISSUE_TYPE·MANAGEMENT_LEVEL·GOODS_RECEIPT_REASON 넷은 계수 괄호에만
# 있었다(계약 9자리가 그 넷을 가리키는데도). 사본이 갈라지는 것을 막는 법은 사본을
# 없애는 것뿐이다.
CLAUSE = os.path.join(HERE, "..", "..", "..", "wiki", "decisions-policy", "공유계약.md")

# 표 머리 — 조항의 소제목. 바뀌면 «조용히» 비는 대신 ⛔ 로 죽는다(load_registry 참조).
REGISTRY_HEAD = re.compile(r"^#### .*등록부 — 이름이 «있는» 그룹", re.M)
GROUP_CELL = re.compile(r"^`([A-Z][A-Z0-9_]+)`$")


def load_registry(path: str = CLAUSE) -> set:
    """공유계약 G-32 등록부 표의 **첫 칸**을 읽는다.

    ⛔ **첫 칸만 읽는다.** 「근거」 칸에는 값(`RETEST_PASS`·`MORNING` …)과 다른 그룹
    상호참조가 들어간다 — 줄 전체를 훑으면 산문 시절의 「값과 이름이 같은 모양으로
    섞인다」가 그대로 재발한다. 그것이 이 이관이 없앤 병이다.

    ⛔ 표를 못 찾거나 0행이면 **죽는다.** 조용히 빈 등록부가 되면 계약의 모든 포인터가
    빨강이 되고, 그 빨강의 원인이 「계약이 틀렸다」로 읽힌다.
    """
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    head = REGISTRY_HEAD.search(text)
    if not head:
        raise SystemExit("⛔ 공유계약 G-32 의 등록부 표 머리를 못 찾았습니다 — %s" % path)
    tail = text[head.end():]
    nxt = re.search(r"^#{2,4} ", tail, re.M)      # 다음 소제목 전까지가 이 절이다
    body = tail[:nxt.start()] if nxt else tail

    names = set()
    for line in body.split("\n"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4:                        # 열 설명표(2열)를 삼키지 않는다
            continue
        m = GROUP_CELL.match(cells[0])
        if m:
            names.add(m.group(1))
    if not names:
        raise SystemExit("⛔ 등록부 표에서 그룹 이름을 하나도 못 읽었습니다 — %s" % path)
    return names


REGISTRY = load_registry()

POINTER = re.compile(r"codeGroupCode=([A-Z][A-Z0-9_]*)")


def schemas(doc: dict):
    """(스키마 이름, 필드 이름, 프로퍼티) 를 전건 낸다 — `*Code` 계수용."""
    for name, schema in (doc.get("components", {}).get("schemas") or {}).items():
        if not isinstance(schema, dict):
            continue
        for field, prop in (schema.get("properties") or {}).items():
            if isinstance(prop, dict):
                yield name, field, prop


def descriptions(doc: dict) -> "Iterator[tuple[str, str]]":
    """`description` 이 적힌 자리를 **전건** 낸다 — (자리 이름, 설명).

    ⛔ **자리를 «열거»하지 않는다 — 문서를 훑는다.**
    처음에는 스키마·프로퍼티·오퍼레이션·파라미터·응답 다섯을 손으로 적었는데,
    그러면 적지 않은 자리가 그대로 구멍이 된다. 실측(2026-09-01)으로
    `components/parameters` **27자리** · `requestBody` 인라인 스키마 **24자리** 가
    그 밖에 있었다. 지금은 그 자리에 포인터가 없지만, 「지금 없다」와
    「앞으로도 안 생긴다」는 다르다.

    ⛔ 이 검사기가 놓쳤던 사고가 정확히 그 형태다 — `JUDGMENT_TYPE` 이 «스키마»
    설명과 «오퍼레이션» 설명에만 있어 프로퍼티만 보던 검사기를 그대로 통과했다.
    등록부 밖 이름이었는데도 초록이었고, 그 초록이 근거로 쓰이고 있었다.

    ⚠ 그래서 `x-` 확장·예시·산문은 여전히 못 본다 — `description` 키만 본다.
    """
    def walk(node, path: str):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "description" and isinstance(value, str):
                    yield path or "(문서)", value
                else:
                    yield from walk(value, "%s/%s" % (path, key))
        elif isinstance(node, list):
            for idx, value in enumerate(node):
                yield from walk(value, "%s[%d]" % (path, idx))

    yield from walk(doc, "")


def main() -> int:
    stray: list[tuple[str, str, str]] = []
    bare = collections.Counter()
    total_code = 0
    pointers = 0

    for f in sorted(glob.glob(os.path.join(CONTRACTS_DIR, "*.json"))):
        fname = os.path.basename(f)
        with open(f, encoding="utf-8") as fh:
            doc = json.load(fh)
        # ① 포인터는 «적힐 수 있는 자리 전부»에서 본다 — 프로퍼티만 보면 놓친다.
        for where, desc in descriptions(doc):
            names = POINTER.findall(desc)
            pointers += len(names)
            for n in names:
                if n not in REGISTRY:
                    stray.append((fname, where, n))
        # ② 「포인터도 enum 도 없는 `*Code`」 계수는 프로퍼티 축이다.
        for sname, field, prop in schemas(doc):
            if not field.endswith("Code"):
                continue
            total_code += 1
            desc = prop.get("description") or ""
            if "enum" in prop or POINTER.search(desc) or "x-no-example" in prop:
                continue
            bare[fname] += 1

    if bare:
        print("⚠ `enum` 도 그룹 포인터도 `x-no-example` 도 없는 `*Code` 자리 "
              "%d건 (전체 `*Code` %d) — 계수만 낸다(EXIT 를 바꾸지 않는다)"
              % (sum(bare.values()), total_code))
        for fname, n in sorted(bare.items(), key=lambda kv: (-kv[1], kv[0])):
            print("   %-30s %4d" % (fname, n))
        print()

    if not stray:
        print("✅ 계약이 가리킨 그룹 이름이 전부 등록부 안입니다 — 포인터 %d자리 검사"
              " (등록부 %d개)" % (pointers, len(REGISTRY)))
        return 0

    print("⛔ 등록부 밖 그룹 이름을 가리키는 자리 %d건 (포인터 %d자리 검사 · 등록부 %d개)\n"
          % (len(stray), pointers, len(REGISTRY)))
    for fname, where, name in stray:
        print("   %-26s %-46s → %s" % (fname, where, name))
    print("\n   ⭐ 둘 중 하나를 «정해서» 닫는다 —\n"
          "      ① 그 이름을 공유계약 G-32 등록부에 올린다(마스터에 행이 실재해야 한다)\n"
          "      ② 등록부에 있는 이름으로 포인터를 고친다\n"
          "   ⛔ 이 검사기에는 늘릴 목록이 없습니다 — 공유계약 G-32 의 «등록부 표»에 행을 더하세요.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
