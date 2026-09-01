#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""계약 스키마의 `required` 프로퍼티가 그 화면 스펙 §4 필드표에 «행»으로 있는가.

왜 필요한가
-----------
2026-09-01 `omf-mes#336`. 제품 폐기 요청(`W-04-10`)·자재 폐기 요청·기타출고
(`W-01-06`) 둘 다 `GoodsIssueCreate.sourceDocumentTypeCode`·`sourceDocumentId`
(둘 다 `required`)가 §4 필드표에 «행 자체가 없었다.** 계약에는 있었지만 스펙이
안 세니 **착수 통지 §4 에도 안 실렸고**, 개발팀은 코딩하다가야 그 자리가
필수인 것을 알았다.

`check-structure.py` 는 계약 스키마가 성립하는지만 본다. 어떤 검사기도 「계약의
필수 칸 ↔ 스펙 필드표」를 대조하지 않았다 — **검사기가 낡은 것이 아니라 «없었다».**

무엇을 보나
-----------
계약 7벌에서 **요청(쓰기) 스키마**이면서 `x-source-table`(물리 테이블 이름)과
`required` 를 함께 가진 스키마를 모은다. 「요청」 판정은 `check-required-change.py`
의 `roles()`(requestBody·responses 에서 `$ref` 를 고정점까지 전이시키는 판정)를
그대로 재사용한다 — 판정 로직을 두 곳에 따로 두면 갈린다.

화면 스펙(`design/wiki/screens/**/*.md`)에서 `### §4-X. … `물리.테이블`` 형태의
소절 제목을 찾는다(백틱으로 감싼 `스키마.테이블` 토큰). 그 테이블을 가리키는
소절이 있으면, 그 스키마의 필수 칸 각각의 **원본 컬럼 이름**(`x-source-column`,
없으면 camelCase→snake_case 로 변환)이 그 소절 본문 어딘가에 «문자열로» 있는지
본다. 없으면 결손이다 — 필드표에 행이 없다는 뜻이다.

⚠ 왜 게이트로 걸지 않고 «래칫»으로 거나
----------------------------------------
지금 기준선이 이미 크다(`BASELINE` 참조 — 시스템 컬럼·라인 배열처럼 관행상
필드표에 개별 행으로 안 올리는 자리가 섞여 있다). 이 회차의 어떤 반영으로도
한 번에 닫히는 수가 아니라, 게이트로 걸면 초록을 기준선으로 못 쓴다. 그래서
**늘면 ⛔, 줄면 「기준선을 낮추라」**로 두었다 — 새로 만드는 필드표가 같은
구멍을 반복하는 것만 막는다.

⚠ 이 검사기가 못 보는 것
------------------------
- **관행상 필드표에 안 올리는 시스템 칸을 가른다.** `businessDate`·`occurredAt`·
  `lines`(라인 배열)처럼 화면마다 다른 자리에 적히는 필드는 여기서도 걸린다 —
  실제 결손과 관행상 생략을 사람이 갈라야 한다.
- **필드표 «칸 위치»는 안 본다.** 소절 본문 어딘가에 그 컬럼 이름 문자열이
  있으면 통과한다(다른 표·산문에 우연히 등장해도 통과) — `verify-mapping-
  coverage.py` 의 `_first_column` 처럼 표 열까지 좁히지 않는다.
- **읽기 전용 스키마는 안 본다.** 요청(쓰기) 스키마만 본다 — 응답에만 있는
  `required` 는 화면이 채울 의무가 없다.
- **§4 소절 자체가 없는 화면**은 「결손 0건」으로 조용히 넘어간다 — 그 화면이
  아직 §4 를 안 썼다는 뜻이지 이 검사기가 확인한 것이 아니다.

쓰기
----
    python3 design/schema/generators/openapi/check-required-in-fieldtable.py
"""
from __future__ import annotations

import glob
import importlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_rc = importlib.import_module("check-required-change")

CONTRACTS_DIR = os.path.join(HERE, "..", "..", "..", "wiki", "api-contracts", "openapi")
SPECS_GLOB = os.path.join(HERE, "..", "..", "..", "wiki", "screens", "**", "*.md")

SCREEN_ID = re.compile(r"^([WPM]-(?:CO|\d{2})-\d{2})")
SECTION4_HEAD = re.compile(r"^(#{2,4})\s*§4.*$", re.M)
ANY_HEAD = re.compile(r"^#{1,4}\s", re.M)
BACKTICK_TABLE = re.compile(r"`([a-z_]+\.[a-z_]+)`")
CAMEL = re.compile(r"(?<!^)(?=[A-Z])")

# 기준선 — 2026-09-01 실측(`omf-mes#336`). ⛔ 늘리지 않는다. 줄었으면 이 수를 낮춘다.
BASELINE = 122


def to_snake(name: str) -> str:
    return CAMEL.sub("_", name).lower()


def columns_from_doc(doc: dict) -> dict[str, set[str]]:
    """한 계약 문서 → {물리 테이블 이름: 요청 스키마의 필수 컬럼(원본 이름)}.

    순수 함수다 — 파일을 읽지 않는다. 테스트가 이 함수를 고정 문서로 부른다.
    """
    out: dict[str, set[str]] = {}
    roles = _rc.roles(doc)
    schemas = doc.get("components", {}).get("schemas") or {}
    for name, schema in schemas.items():
        if not isinstance(schema, dict):
            continue
        table = schema.get("x-source-table")
        required = schema.get("required")
        if not table or not required:
            continue
        role = roles.get(name)
        if not role or "요청" not in role:
            continue
        props = schema.get("properties") or {}
        cols = out.setdefault(table, set())
        for field in required:
            prop = props.get(field) or {}
            cols.add(prop.get("x-source-column") or to_snake(field))
    return out


def required_columns_by_table() -> dict[str, set[str]]:
    """계약 7벌 전건 → 물리 테이블 이름 → 요청 스키마 필수 컬럼 합집합."""
    out: dict[str, set[str]] = {}
    for path in sorted(glob.glob(os.path.join(CONTRACTS_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        for table, cols in columns_from_doc(doc).items():
            out.setdefault(table, set()).update(cols)
    return out


def field_sections(text: str) -> list[tuple[list[str], str]]:
    """[(그 소절 제목이 가리키는 테이블들, 소절 본문)] — §4-X 소절마다."""
    heads = list(SECTION4_HEAD.finditer(text))
    any_heads = [m.start() for m in ANY_HEAD.finditer(text)]
    out = []
    for i, hm in enumerate(heads):
        tables = BACKTICK_TABLE.findall(hm.group(0))
        if not tables:
            continue
        start = hm.end()
        # 다음 §4-X 소절이나, 그보다 먼저 오는 상위 헤딩(예: ## §5)에서 끊는다.
        candidates = [heads[i + 1].start()] if i + 1 < len(heads) else []
        candidates += [h for h in any_heads if h > start]
        end = min(candidates) if candidates else len(text)
        out.append((tables, text[start:end]))
    return out


def main() -> int:
    table_required = required_columns_by_table()
    gaps: list[tuple[str, str, str]] = []

    for path in sorted(glob.glob(SPECS_GLOB, recursive=True)):
        m = SCREEN_ID.match(os.path.basename(path))
        if not m:
            continue
        screen = m.group(1)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for tables, body in field_sections(text):
            for table in tables:
                cols = table_required.get(table)
                if not cols:
                    continue
                for col in sorted(cols):
                    if col not in body:
                        gaps.append((screen, table, col))

    print("요청 스키마 %d개 테이블의 필수 컬럼을 §4 필드표와 대조 — 결손 %d건"
          % (len(table_required), len(gaps)))

    if gaps:
        print()
        by_screen: dict[str, list[tuple[str, str]]] = {}
        for screen, table, col in gaps:
            by_screen.setdefault(screen, []).append((table, col))
        for screen in sorted(by_screen):
            print("  %s" % screen)
            for table, col in by_screen[screen]:
                print("     %-32s %s" % (table, col))
        print("\n   ⭐ 실제 결손이면 §4 필드표에 행을 신설한다.")
        print("   ⚠ 관행상 생략하는 시스템 칸(예: 라인 배열·감사 컬럼)이면 넘긴다 —")
        print("      이 검사기는 그 둘을 가르지 못한다(파일 첫머리 「안 보는 것」 참조).")

    if len(gaps) > BASELINE:
        print("\n⛔ 기준선 %d 보다 %d 늘었다 — 새로 만든 필드표가 같은 구멍을 반복했다."
              % (BASELINE, len(gaps) - BASELINE))
        return 1
    if len(gaps) < BASELINE:
        print("\n⭐ 기준선 %d → %d 로 줄었다. 이 파일의 `BASELINE` 을 %d 로 낮추세요."
              % (BASELINE, len(gaps), len(gaps)))
    else:
        print("\n✅ 기준선 %d 유지 — 늘지 않았다." % BASELINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
