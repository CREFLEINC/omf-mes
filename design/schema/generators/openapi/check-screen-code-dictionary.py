#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""화면 스펙 §4 필드표가 **코드 사전과 같은 말을 하는가**.

왜 필요한가
-----------
2026-09-02 에 코드 사전이 닫혔다 — 계약 `*Code(s)` 자리 **639/639 전건 판정**.
그런데 그 사실이 **화면 스펙까지 가지 않았다.** 사전이 값을 정한 칸을 화면
스펙은 여전히 「⚠ 값 목록 미확정」이라 적어 두고 있었다(실측 26행).

그것이 그냥 낡은 문면으로 끝나지 않는다:

  ① 프론트는 그 문면을 보고 선택칸을 **비활성 + 사유**로 만든다(`G-2`) —
     값이 이미 있는데도 화면이 굳는다.
  ② 착수·변경 통지 §4 가 스펙에서 필드표를 옮겨 뜨므로 **「이 화면은 코드가
     미정이라 막혀 있다」로 나간다.**
  ③ 사전을 채운 사실이 **전달되는 경로가 없다.**

⛔ 그리고 그 어긋남을 **보는 검사기가 하나도 없었다.** `check-code-dictionary.py`
는 계약 ↔ 사전만 보고, `check-code-group-reachable.py` 는 요구서 ↔ 계약만 본다.
화면 스펙은 «코드 축»으로 아무도 읽지 않았다 — 검사기가 낡은 것이 아니라 «없었다».

무엇을 다리로 삼나
------------------
**새 다리를 만들지 않는다.** `check-required-in-fieldtable.py` 가 이미 쓰는 다리를
그대로 쓴다:

    화면 §4-X 소절 제목의 `스키마.테이블`  +  그 행의 「출처 컬럼」
      → 계약 스키마의 `x-source-table` · 프로퍼티의 `x-source-column`
      → 그 프로퍼티의 `x-code-key`
      → 코드 사전의 그 키 행(값·그룹·소유)

⭐ 이 다리는 **계약과 화면 스펙이 스스로 적어 둔 포인터**다. 데이터 모델을 훑어
만든 목록이 아니다 — 물리 이름이 등장하지만 그것은 «재판정의 입력»이지 결론이
아니다(2026-08-30 명명 규약 회차).

무엇을 보나
-----------
  ㉮ ⛔ **낡은 「값 목록 미확정」** — 그 행이 사전 키에 닿고 사전이 «값을 정했는데»
        행이 아직 「값 목록 미확정」이라 적었다. 게이트다(0 이어야 한다).
  ㉯ ⛔ **사전 밖 값** — 그 행이 백틱으로 적은 코드 문자열이 사전 값집합에도
        등록부 그룹 이름에도 없다. 화면이 «다른 말»을 하고 있다.
  ㉰ ⛔ **등록부 밖 포인터** — 화면이 적은 `codeGroupCode=X` 의 X 가 `G-32`
        등록부에 없다. 프론트가 그대로 호출하면 «빈 목록»을 받는다
        (`W-01-12` 의 `ADJUST_REASON` 이 실제로 그랬다).
  ㉲ ⛔ **「코드 아님」도 판정이다** — 계약이 `x-no-code-key` 로 「이 자리는 코드
        그룹이 아니다」라고 «판정»했는데 화면이 아직 「값 목록 미확정」이라 적는다.
        ⭐ 화면이 기다릴 값 목록이 **영영 오지 않는다** — ㉮ 와 똑같이 프론트를 굳힌다.
        ⛔ 2026-09-03 실측 4건. `W-01-09` 가 대표다 — `Asn.statusCode` 는 「코드
        그룹을 세우지 않는다 … 사용자 결정 2026-09-02」로 이미 판정됐는데 §8-1 이
        「회신 대기」로 남아 **오지 않을 회신을 기다리고 있었다.**
  ㉱ ⚠  **래칫** — 화면 스펙 전체에 남은 「값 목록 미확정」류 줄 수. 다리가 안 닿는
        자리(§3 목업·§8 미결·산문)까지 센다. 게이트로 못 거는 이유는 아래.
        ⛔ **이력·회고 절은 세지 않는다** — 「v0.3 이 무엇을 고쳤나」는 «그때의
        기록»이라 지금 낡은 문면이 아니다(작성 규칙 5 · `verify-stale-terms.py` 와
        같은 판정 함수를 그대로 쓴다).

⚠ 왜 ㉱ 만 래칫인가
--------------------
㉮㉯㉰ 는 **다리가 닿은 자리**만 본다 — 기계가 「이 칸이 어느 코드인가」를 알 수
있으므로 판정이 확정적이다. ㉱ 는 §3 목업의 그림 글자나 §8 미결의 산문까지 세는데,
그중에는 **아직 정말로 안 정한 것**(고객이 `W-06-06` 에서 채우기로 한 registry
갈래)이 섞여 있다. 기계가 그 둘을 가르지 못한다. 그래서 **늘면 ⛔, 줄면 기준선을
낮추라**로 둔다.

⚠ 이 검사기가 못 보는 것
------------------------
  - **§4 소절에 테이블 이름을 backtick 으로 안 적은 화면**은 통째로 안 본다
    (2026-09-03 실측 — 118장 중 81장만 적었다). 「결손 0」이 「확인했다」가 아니다.
  - **§3 목업 안의 「⚠ 값 목록 미확정」을 어느 칸의 것인지 가르지 못한다** —
    그림 글자에는 컬럼 이름이 없다. ㉱ 가 줄 수로만 센다.
  - **화면이 그 호출을 실제로 만드는지**는 이 저장소가 답할 물음이 아니다.
  - **요구서 §3 에 그 호출이 실렸는지**는 `check-code-group-reachable.py` 가 본다.
  - `x-source-column` 이 없는 계약 프로퍼티는 다리가 끊긴다 — camelCase→snake
    변환으로 «보충하지 않는다». 추측으로 이으면 틀린 자리를 ⛔ 로 세운다.

쓰기
----
    python3 design/schema/generators/openapi/check-screen-code-dictionary.py
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
_cd = importlib.import_module("check-code-dictionary")
_ptr = importlib.import_module("check-code-group-pointer")
_rift = importlib.import_module("check-required-in-fieldtable")

# ⭐ 이력·회고 절 판정은 `verify-stale-terms.py` 것을 «그대로» 쓴다 — 작성 규칙 5 가
#    「회고·이력을 담은 절에는 표시를 달지 않아도 된다」로 정한 그 절이다. 같은 판정을
#    두 곳에 따로 두면 갈린다.
sys.path.insert(0, os.path.dirname(HERE))
_stale = importlib.import_module("verify-stale-terms")

ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
DICT = os.path.join(ROOT, "design", "schema", "code-dictionary.md")
CONTRACTS = os.path.join(ROOT, "design", "wiki", "api-contracts", "openapi", "*.json")
SPECS = os.path.join(ROOT, "design", "wiki", "screens", "**", "*.md")

SCREEN_ID = re.compile(r"^([WPM]-(?:CO|\d{2})-\d{2})")
SOURCE_COL = re.compile(r"^`([a-z][a-z0-9_]*)`$")
VALUE = re.compile(r"`([A-Z][A-Z0-9_]{2,})`")
POINTER = re.compile(r"codeGroupCode=([A-Za-z_][A-Za-z0-9_]*)")
HEADING = re.compile(r"^#{1,6}\s*(.+?)\s*$")

# 「값 목록이 아직 없다」고 적은 문면. ⛔ 오프라인 「미확정 «표식»」과 갈라야 한다 —
#    그것은 코드와 무관한 동기화 상태 표시다(`M-01-08` §5-3).
STALE = re.compile(
    r"값\s*목록\s*(이\s*)?(아직\s*)?(미확정|미정|확정되지\s*않|정해지지\s*않|없)")

# ⭐ 「이미 판단했다」는 표식. 작성 규칙 5 가 정한 셋(`«(정합주: …)»`·`«(구표기 보존)»`·
#    취소선)과 같은 뜻으로 읽는다 — `verify-stale-terms.py` 도 그 셋이 붙은 줄을
#    보고하지 않는다. 표시를 다는 것은 검사기를 속이는 일이 아니라 **판단 결과를
#    알려 주는 일**이다(`design/schema/00-authoring-rules.md` 규칙 5).
#    여기에 하나를 더한다 — 그 줄이 **값을 받는 곳을 이미 적었으면**(그룹 포인터)
#    낡은 문면이 아니다.
SETTLED = re.compile(r"«\(정합주:|«\(구표기 보존\)»|~~|codeGroupCode=")

# ⛔ 값이 아니라 «제약·타입»을 적은 낱말. ㉯ 가 이것을 코드 값으로 세면 안 된다.
NOT_A_VALUE = {
    "NOT", "NULL", "CHECK", "DEFAULT", "UNIQUE", "GENERATED", "WHERE",
    "AND", "OR", "ONLY", "TRUE", "FALSE", "API", "URL", "UUID", "JSON",
    "GET", "POST", "PUT", "PATCH", "DELETE", "FK", "PK", "ETC", "TODO",
}

# 기준선 — 2026-09-03 실측. ⛔ 늘리지 않는다. 줄었으면 이 수를 낮춘다.
#
# ⭐ 104 → 54 → **4**. 두 회차로 닫았다.
#    ① ㉮ 가 짚은 §4 행 25개 + 그 화면들의 §3 목업·§5 산문·§8 미결(18장) — 104 → 54
#    ② 다리가 «안 닿는» 자리를 사람이 한 줄씩 읽어 판정 — 54 → 4
#       (33장 · §3 목업·§5 산문·§8 미결. 「어느 코드인가」를 계약 조회로 확정한 뒤
#        값이 있으면 값을, 「코드 아님」이면 그 판정 이유를 옮겨 적었다)
#    ⛔ 이력·회고 절을 세지 않게 고치며 2줄이 빠졌다(작성 규칙 5).
#
# ⚠ 남은 4 는 «진짜 미결»이다 — 고치면 안 되는 자리다.
#    · `P-02-03` 3줄 — `allocation_method_code`·`trace_accuracy_code` 는 계약에
#      프로퍼티 «자체»가 없다. `x-code-key` 도 `x-no-code-key` 도 없는 ⬜ 다.
#      판정 전에 이름을 붙이라는 말이 되므로 그대로 둔다.
#    · `P-04-02` 1줄 — 「②로 물러난 이유」의 «인용문»이고 바로 두 줄 뒤가 스스로
#      반박한다. 고치면 반박 대상이 사라진다.
# ⇒ 그래서 0 이 아니다. 새로 쓰는 스펙이 같은 구멍을 반복하는 것만 막는다.
BASELINE_STALE = 4


def norm(x) -> list:
    """계약의 `x-source-table`·`x-source-column`·`x-code-key` 는 목록일 수 있다."""
    if x is None:
        return []
    return list(x) if isinstance(x, list) else [x]


def code_key_by_column() -> dict[tuple[str, str], set[str]]:
    """계약 7벌 → {(물리 테이블, 원본 컬럼): 그 자리에 붙은 사전 키}.

    순수 함수가 아니다(파일을 읽는다). 테스트는 `columns_from_doc` 을 부른다.
    """
    out: dict[tuple[str, str], set[str]] = {}
    for path in sorted(glob.glob(CONTRACTS)):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        for pair, keys in columns_from_doc(doc).items():
            out.setdefault(pair, set()).update(keys)
    return out


def no_code_from_doc(doc: dict) -> dict[tuple[str, str], str]:
    """한 계약 문서 → {(테이블, 컬럼): 「코드 아님」 이유}. 파일을 읽지 않는다.

    ⭐ **「코드 아님」도 판정이다.** 화면이 기다릴 값 목록이 «영영 오지 않는다»는 뜻이라,
       그 자리에 「값 목록 미확정」이 남아 있으면 ㉮ 와 똑같이 프론트를 굳힌다.
       ⛔ 2026-09-03 실측 — `Asn.statusCode` 는 계약이 「코드 그룹을 세우지 않는다 …
       사용자 결정 2026-09-02」로 판정했는데 `W-01-09` 는 여전히 「값 목록 미확정 ·
       §8-1 회신 대기」였다. **오지 않을 회신을 기다리고 있었다.**
    """
    out: dict[tuple[str, str], str] = {}
    for schema in (doc.get("components", {}).get("schemas") or {}).values():
        if not isinstance(schema, dict):
            continue
        tables = norm(schema.get("x-source-table"))
        if not tables:
            continue
        for prop in (schema.get("properties") or {}).values():
            if not isinstance(prop, dict):
                continue
            reason = prop.get("x-no-code-key")
            cols = norm(prop.get("x-source-column"))
            if not reason or not cols:
                continue
            for table in tables:
                for col in cols:
                    out[(table, col)] = reason
    return out


def no_code_by_column() -> dict[tuple[str, str], str]:
    """계약 7벌 → {(테이블, 컬럼): 「코드 아님」 이유}."""
    out: dict[tuple[str, str], str] = {}
    for path in sorted(glob.glob(CONTRACTS)):
        with open(path, encoding="utf-8") as fh:
            out.update(no_code_from_doc(json.load(fh)))
    return out


def columns_from_doc(doc: dict) -> dict[tuple[str, str], set[str]]:
    """한 계약 문서 → {(테이블, 컬럼): 사전 키}. 파일을 읽지 않는다."""
    out: dict[tuple[str, str], set[str]] = {}
    for schema in (doc.get("components", {}).get("schemas") or {}).values():
        if not isinstance(schema, dict):
            continue
        tables = norm(schema.get("x-source-table"))
        if not tables:
            continue
        for prop in (schema.get("properties") or {}).values():
            if not isinstance(prop, dict):
                continue
            cols = norm(prop.get("x-source-column"))
            keys = norm(prop.get("x-code-key"))
            if not cols or not keys:
                continue
            for table in tables:
                for col in cols:
                    out.setdefault((table, col), set()).update(keys)
    return out


def dictionary() -> dict[str, dict]:
    """사전 키 → 행. `check-code-dictionary.read_dictionary` 를 그대로 쓴다."""
    return {e["key"]: e for e in _cd.read_dictionary(DICT)}


def field_rows(text: str):
    """[(테이블, 컬럼, 그 행 전문)] — §4-X 소절의 필드표 행마다.

    소절 가르기는 `check-required-in-fieldtable.field_sections` 를 그대로 쓴다 —
    같은 판정을 두 곳에 따로 두면 갈린다.
    """
    for tables, body in _rift.field_sections(text):
        for line in body.split("\n"):
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 3:
                continue
            m = SOURCE_COL.match(cells[1])
            if not m:
                continue                      # 머리·구분선·출처 컬럼이 아닌 행
            for table in tables:
                yield table, m.group(1), line


def judge_row(line: str, keys: set, dic: dict, registry: set) -> tuple[list, list]:
    """한 §4 행 → (㉮ 낡은 키 목록, ㉯ 사전 밖 토큰 목록). 파일을 읽지 않는다.

    ⛔ **값 판정은 «짝 단위 합집합»으로 한다.** 한 (테이블·컬럼) 짝이 키 둘에
       닿을 수 있다 — `mdm.equipment.equipment_type_code` 는 설비 유형과 계측기
       유형 둘 다에 닿는다(`G-32` 2026-08-24 소절이 가른 그 자리다). 키를 하나씩
       보면 **형제 키의 값이 전부 「사전 밖」으로 잡힌다** — 이 검사기의 첫 실행이
       그렇게 거짓 양성 6건을 냈다(2026-09-03).
    """
    settled = bool(SETTLED.search(line))
    stale, union = [], set()
    for key in sorted(keys):
        entry = dic.get(key)
        if not entry:
            continue
        values = set(entry["values"])
        union |= values
        if values and STALE.search(line) and not settled:
            stale.append((key, "·".join(sorted(values))))
    # ⛔ 「이미 판단했다」 표식이 붙은 줄은 ㉯ 도 보지 않는다 — ㉮ 와 같은 이유다.
    #    그 줄은 값을 «주장»하는 것이 아니라 «인용»한다. 작성 규칙 5 가 정한 자리다:
    #    「회고·반박 서술이라 옛 이름을 인용해야 뜻이 통할 때 «(구표기 보존)»」.
    #    ⛔ 2026-09-03 실측 — `W-CO-02` 가 「⛔ `ACTIVE` 를 «쓰지 않는다»」로 적은
    #    부정문의 토큰을 ㉯ 가 값으로 셌다. 폐기한 이름을 «왜 안 쓰는지» 적는 것은
    #    이 저장소가 권장하는 일이라(`G-32` v3.5 선례), 그것을 ⛔ 로 세면 안 된다.
    if not union or settled:
        return stale, []
    off = [t for t in sorted(set(VALUE.findall(line)))
           if t not in union and t not in registry and t not in NOT_A_VALUE]
    return stale, off


def main() -> int:
    pairs = code_key_by_column()
    nocode = no_code_by_column()
    dic = dictionary()
    registry = set(_ptr.load_registry())

    nocode_rows: list[tuple] = []
    stale_rows: list[tuple] = []
    off_values: list[tuple] = []
    bad_pointer: list[tuple] = []
    stale_lines = 0
    touched = 0

    for path in sorted(glob.glob(SPECS, recursive=True)):
        base = os.path.basename(path)
        m = SCREEN_ID.match(base)
        if not m:
            continue
        screen = m.group(1)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()

        # ㉰ 화면이 적은 그룹 포인터가 등록부 안인가
        heading = None
        for i, line in enumerate(text.split("\n"), 1):
            hm = HEADING.match(line)
            if hm:
                heading = hm.group(1)
            for group in POINTER.findall(line):
                if group not in registry:
                    bad_pointer.append((screen, i, group))
            # ⛔ 이력·회고 절은 세지 않는다 — 「v0.3 이 무엇을 고쳤나」는 «그때의 기록»이라
            #    지금 낡은 문면이 아니다(작성 규칙 5 · `verify-stale-terms.py` 와 같은 판정).
            if STALE.search(line) and not SETTLED.search(line) \
                    and not _stale.in_history_section(heading):
                stale_lines += 1                          # ㉱ 래칫

        # ㉮㉯㉲ 다리가 닿은 §4 필드표 행
        for table, col, line in field_rows(text):
            # ㉲ 계약이 「코드 아님」으로 «판정»한 자리인데 아직 기다리고 있다
            reason = nocode.get((table, col))
            if reason and STALE.search(line) and not SETTLED.search(line):
                nocode_rows.append((screen, table, col,
                                    " ".join(reason.split())[:60]))
            keys = pairs.get((table, col))
            if not keys:
                continue
            touched += 1
            stale, off = judge_row(line, keys, dic, registry)
            for key, values in stale:
                stale_rows.append((screen, table, col, key, values))
            for tok in off:
                off_values.append((screen, table, col,
                                   "·".join(sorted(keys)), tok))

    print("계약 (테이블·컬럼) → 사전 키 짝 %d · 화면 §4 에서 다리가 닿은 코드 행 %d"
          % (len(pairs), touched))
    print()

    fail = False

    print("㉮ 사전이 값을 정했는데 §4 행이 아직 「값 목록 미확정」 — %d" % len(stale_rows))
    for row in stale_rows:
        print("     %-8s %-34s %-28s %-40s %s" % row)
    if stale_rows:
        fail = True
        print("   ⭐ 닫는 법 — 그 행의 「검증·비고」 칸을 사전 값으로 갈고,")
        print("      값을 어디서 받는지(`GET /mdm/code-values?codeGroupCode=…`)를 함께 적는다.")
    print()

    print("㉯ §4 행이 사전에 «없는» 코드 값을 적음 — %d" % len(off_values))
    for row in off_values:
        print("     %-8s %-34s %-28s %-40s %s" % row)
    if off_values:
        fail = True
        print("   ⭐ 화면과 사전 중 «어느 쪽이 맞는지» 판정한다 — 둘 다 근거가 있으면 사람에게 묻는다.")
    print()

    print("㉲ 계약이 「코드 아님」으로 판정했는데 §4 행이 아직 「값 목록 미확정」 — %d"
          % len(nocode_rows))
    for row in nocode_rows:
        print("     %-8s %-34s %-24s %s" % row)
    if nocode_rows:
        fail = True
        print("   ⛔ 화면이 «오지 않을» 값 목록을 기다리고 있다 — 「코드 아님」도 판정이다.")
        print("   ⭐ 닫는 법 — 그 행에 계약의 판정 이유를 옮겨 적는다(§8 미결도 함께 해소).")
    print()

    print("㉰ 화면이 적은 codeGroupCode 가 등록부(G-32) 밖 — %d" % len(bad_pointer))
    for row in bad_pointer:
        print("     %-8s %5d  %s" % row)
    if bad_pointer:
        fail = True
        print("   ⛔ 프론트가 그대로 부르면 «빈 목록»을 받는다 — 등록부에 올리거나 이름을 고친다.")
    print()

    print("㉱ 화면 스펙에 남은 「값 목록 미확정」류 줄 — %d (기준선 %d)"
          % (stale_lines, BASELINE_STALE))
    if stale_lines > BASELINE_STALE:
        print("⛔ 기준선보다 %d 늘었다 — 새로 쓴 스펙이 같은 구멍을 반복했다."
              % (stale_lines - BASELINE_STALE))
        fail = True
    elif stale_lines < BASELINE_STALE:
        print("⭐ 기준선 %d → %d 로 줄었다. 이 파일의 `BASELINE_STALE` 을 %d 로 낮추세요."
              % (BASELINE_STALE, stale_lines, stale_lines))
    else:
        print("✅ 기준선 유지 — 늘지 않았다.")

    if fail:
        print()
        print("⛔ 화면 스펙이 코드 사전과 다른 말을 하고 있다.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
