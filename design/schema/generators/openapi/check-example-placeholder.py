#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""계약의 `example` 이 «확정값 목록 밖»인가 — 예시도 구현이 읽는다.

왜 있는가
---------
2026-08-21 `omf-mes#185`. 설비 상태 칸의 `example` 이 `"ACTIVE"` 였고, 구현팀은
그 값을 보고 코드를 만들었다. **시험은 전부 통과했다**(`omf-mes-client#297`) —
계약이 그 값을 확정한 적이 없었는데도.

    description 은 `openapi-typescript` 가 JSDoc 으로 옮기고,
    example 도 생성 타입·목 서버에 그대로 실린다.

⭐ **설명이 맞아도 예시가 틀리면, 설명을 «읽지 않는 한» 아무도 못 잡는다.**
`PRINT_FAILED` ↔ `PRINT_FAILURE` 는 한 낱말 차이였다(`omf-mes#191`).

무엇을 보나
-----------
이름이 `Code` 로 끝나는 프로퍼티의 `example` 을 다섯 축으로 본다.

    ① 자리채움 상수   example 이 "STANDARD"·"값" 이면 무조건 운다
    ② 쌍둥이 모순     같은 계약의 X ↔ XCreate/XUpdate 가 같은 이름의 칸을 갖는데
                      한쪽에만 enum 이 있고 다른 쪽 example 이 그 enum 밖이다
    ③ 확정 그룹 밖    description 이 codeGroupCode=<G> 를 가리키는데 example 이
                      G 의 확정값 목록 밖이다
    ④ 자기 스키마 위반 example 이 자기 maxLength·minLength 를 어긴다 ·
                      type 이 string 인데 문자열이 아니다
    ⑤ 자기모순        description 이 「확정되지 않았다」·「미확정」·「미정」을 적으면서
                      구체 example 을 든다

통과 조건
---------
- `x-no-example` 이 있으면 통과 — **불리언·문자열 둘 다** 통과로 본다
  (기존 불리언 21자리를 건드리지 않기 위해서다).
- `example` 이 그 자리의 `enum` 안이면 통과.
- `example` 이 description 이 가리킨 «확정» 그룹의 값 목록 안이면 통과.

⚠ 이 검사기가 못 보는 것
------------------------
- **이름이 `Code` 로 끝나지 않는 자리를 안 본다.** `Concession.nonconformanceNo` 의
  example 이 다른 계약과 어긋나 있었는데(`omf-mes#191` B-2) 이 검사기도 못 본다.
- **`x-source-column` 을 필터로 «쓰지 않는다».** 쓰면 안 되기 때문이다 — 주석률이
  계약마다 **0~68%** 라(실측: equipment 0/257 · shipment 1/182 · quality 12/296 ·
  production 21/385 · app-공통 64/232 · mdm 526/995 · logistics 522/765) 그 필터는
  설비·출하·품질·생산을 **통째로** 뺀다. 「미착지 = 대상 아님」은 상태값에는 틀린다.
- **`NORMAL` 을 무조건 자리채움으로 보지 않는다** — `LOT_STATUS` 에서는 진짜 맞는
  값이다(`omf-mes#191` 코멘트 제안 2번). ③ 으로만 걸린다.
- **하이픈을 무조건 오류로 보지 않는다** — 하이픈 example 상위는 코드값이 아니라
  식별자다(실측: `PRS-01` 9 · `SL-2026-0001` 5 · `WH-01` 3).
- **값 목록이 «옳은지»는 안 본다.** 확정 그룹 값표는 아래 상수이고, 그 출처는
  공유계약 `G-32` 다. 조항이 바뀌면 이 표도 손으로 따라가야 한다.
- **그룹 이름이 등록부에 있는지는 안 본다** — `check-code-group-pointer.py` 몫이다.

⛔ 지금은 게이트가 «아니다» — 종료 코드는 언제나 0
--------------------------------------------------
기준선이 빨갛다. `omf-mes#191` 【A】【B】【C】 반영이 끝나기 전에 게이트로 걸면
사람이 매번 손으로 넘기게 되고, 그러면 검사기가 신뢰를 잃는다(`omf-mes#212` §4 가
같은 이유로 짝 스크립트를 미뤘다). **막지 않고 알린다.** 0건이 되면 그때
`raise SystemExit(1)` 로 올린다.

쓰기
----
    python3 design/schema/generators/openapi/check-example-placeholder.py
    python3 design/schema/generators/openapi/check-example-placeholder.py <파일…>
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Tier 0 — OpenAPI JSON 정본. Phase 5 컷오버(2026-08-25)로 design/wiki/api-contracts/openapi/가 정본 위치다.
CONTRACTS_DIR = os.path.join(HERE, "..", "..", "..", "wiki", "api-contracts", "openapi")

# ── 확정 그룹 값표 ────────────────────────────────────────────────────────
# ⛔ 값을 지어내지 않는다. 줄마다 근거를 단다 — 정본은 공유계약 G-32 다.
#    「그룹 이름이 확정」과 「값 목록까지 확정」은 다른 산출물이다(G-32 v3.4).
CONFIRMED_GROUPS: dict[str, tuple[str, ...]] = {
    # 공유계약 G-32 v3.4 · omf-mes#176 — 뜻은 2026-08-07 확정, 식별자는 그때 정했다
    "LOT_STATUS": ("NORMAL", "DEFECTIVE", "INSPECTION_PENDING", "SCRAPPED"),
    "LOT_TYPE": ("MATERIAL", "PRODUCTION", "PRODUCT"),                      # 결정 10 · omf-mes#176
    # 공유계약 G-32 v3.5 · omf-mes#185 — ⛔ 「사용 여부」와 「수명주기」에 같은 낱말을 쓰지 않는다
    "EQUIPMENT_STATUS": ("IN_SERVICE", "DISPOSED"),
    # 공유계약 G-32 v3.5 · omf-mes#186 — 품질 검사 유형과 «같은 이름 다른 값» 이라 갈랐다
    "EQUIPMENT_INSPECTION_TYPE": ("DAILY", "MONTHLY", "MAINTENANCE"),
    "EQUIPMENT_INSPECTION_JUDGMENT_METHOD": ("VISUAL", "MEASUREMENT"),      # omf-mes#186
    "QUALITY_INSPECTION_TYPE": ("IQC", "PQC", "OQC"),                       # omf-mes#186 · 계약 실측
    # 공유계약 G-32 v3.6 · omf-mes#188 — 검교정 주기 ↔ 점검 부여 주기를 한 그룹으로 합쳤다
    "CYCLE_TYPE": ("DAY", "WEEK", "MONTH", "YEAR"),
    # 공유계약 G-32 v3.3 · omf-mes#179 — 값 이름이 곧 물리 칸 이름이라 넷째 값을 만들 수 없다
    "INSPECTION_ITEM_SPEC_DATA_TYPE": ("NUMERIC", "TEXT", "BOOLEAN"),
    # 공유계약 A-25 v3.9 — 4값에 START 를 더해 5값(논리 모델 §9.7 「시작·중지·재개·종료」)
    "WORK_SESSION_EVENT_TYPE": ("START", "STOP", "RESUME", "END", "CONTROL_OVERRIDE"),
}

# 그룹 «이름»은 확정 · 값 목록은 아직 정해지지 않았다 — ③ 대조에 쓰지 않는다.
# 여기에 있는 그룹을 가리키는 자리는 example 을 무엇으로 두든 이 검사기가 판정하지 못한다.
GROUP_ONLY = {
    "INSPECTION_REQUEST_STATUS",             # omf-mes#170 — 이름만 확정
    "INSPECTION_RESULT_OVERALL_JUDGMENT",    # omf-mes#179 — 판정 컬럼이 둘이라 이름을 안 줄였다
    "INSPECTION_MEASUREMENT_JUDGMENT",       # omf-mes#179
    "INSTRUMENT_TYPE",                       # omf-mes#219 — 등록부 등재 여부는 별건이다
    "EQUIPMENT_TYPE",                        # omf-mes#219
    "WORK_SESSION_EVENT_REASON",             # 공유계약 A-25 — 조항이 한글 라벨로만 적었다(7값)
    "CONTROL_OVERRIDE_REASON",               # 공유계약 A-25 — 동상(2값)
}

PLACEHOLDER = ("STANDARD", "값")     # ⚠ NORMAL·IQC 는 넣지 않는다 — 맞는 자리가 실재한다
GROUP_POINTER = re.compile(r"codeGroupCode=([A-Z][A-Z0-9_]*)")
UNDECIDED = ("확정되지 않았다", "미확정", "미정", "아직 정해지지 않았다", "확정된 값 목록이 아직 없다")
TWIN_SUFFIXES = ("Create", "Update", "Upsert", "Input")


def walk_props(node: object, prefix: str, out: list) -> list:
    """스키마 안의 프로퍼티를 «중첩까지» 모은다 → [(경로, 이름, 정의)].

    ⭐ 중첩을 봐야 하는 이유 — `DocumentIssueCreate.targets.items.properties.targetTypeCode`
    처럼 배열 원소 안에 코드 칸이 있는 자리가 실재한다(omf-mes#191 B-7).
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "properties" and isinstance(value, dict):
                for name, prop in value.items():
                    if not isinstance(prop, dict):
                        continue
                    path = "%s.%s" % (prefix, name) if prefix else name
                    out.append((path, name, prop))
                    walk_props(prop, path, out)
            elif isinstance(value, (dict, list)):
                walk_props(value, prefix, out)
    elif isinstance(node, list):
        for value in node:
            walk_props(value, prefix, out)
    return out


def is_exempt(prop: dict) -> bool:
    """x-no-example 이 있으면 통과 — 불리언·문자열 둘 다."""
    return "x-no-example" in prop


def pointed_group(prop: dict) -> str | None:
    match = GROUP_POINTER.search(prop.get("description") or "")
    return match.group(1) if match else None


def in_enum(prop: dict, example: object) -> bool:
    values = prop.get("enum")
    return isinstance(values, list) and example in values


def check_one(path: str) -> list[str]:
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    name = os.path.basename(path)
    schemas = (doc.get("components") or {}).get("schemas") or {}

    findings: list[str] = []
    top: dict[str, dict] = {}          # 쌍둥이 대조용 — 스키마의 «최상위» 프로퍼티만

    for schema_name, schema in schemas.items():
        if not isinstance(schema, dict):
            continue
        top[schema_name] = {k: v for k, v in (schema.get("properties") or {}).items()
                            if isinstance(v, dict)}

        for prop_path, prop_name, prop in walk_props(schema, "", []):
            if not prop_name.endswith("Code"):
                continue
            where = "%s · %s.%s" % (name, schema_name, prop_path)
            if is_exempt(prop):
                continue
            if "example" not in prop:
                continue
            example = prop["example"]
            desc = prop.get("description") or ""

            # ④ 자기 스키마 위반 — 통과 조건과 무관하게 본다(자기 형태를 어긴다)
            if prop.get("type") == "string" and not isinstance(example, str):
                findings.append("④ 자기 스키마 위반 — %s : type=string 인데 example 이 %s"
                                % (where, type(example).__name__))
            elif isinstance(example, str):
                limit = prop.get("maxLength")
                if isinstance(limit, int) and len(example) > limit:
                    findings.append(
                        "④ 자기 스키마 위반 — %s : example %r 은 %d자, maxLength %d"
                        % (where, example, len(example), limit))
                floor = prop.get("minLength")
                if isinstance(floor, int) and len(example) < floor:
                    findings.append(
                        "④ 자기 스키마 위반 — %s : example %r 은 %d자, minLength %d"
                        % (where, example, len(example), floor))

            if in_enum(prop, example):
                continue                       # 자기 enum 안 — 통과

            group = pointed_group(prop)
            if group in CONFIRMED_GROUPS:
                if example in CONFIRMED_GROUPS[group]:
                    continue                   # 가리킨 확정 그룹 안 — 통과
                findings.append(
                    "③ 확정 그룹 밖 — %s : example %r · %s = %s"
                    % (where, example, group, "·".join(CONFIRMED_GROUPS[group])))
                continue

            # ① 자리채움 상수
            if isinstance(example, str) and example in PLACEHOLDER:
                findings.append("① 자리채움 상수 — %s : example %r" % (where, example))
                continue

            # ⑤ 자기모순 — 「확정되지 않았다」면서 구체 example 을 든다
            if any(word in desc for word in UNDECIDED):
                findings.append(
                    "⑤ 자기모순 — %s : description 이 「미확정」을 적는데 example %r"
                    % (where, example))

    # ② 쌍둥이 모순 — X ↔ XCreate/XUpdate
    for schema_name, props in top.items():
        for suffix in TWIN_SUFFIXES:
            if not schema_name.endswith(suffix):
                continue
            base = schema_name[: -len(suffix)]
            if base not in top:
                continue
            for prop_name in set(props) & set(top[base]):
                if not prop_name.endswith("Code"):
                    continue
                pair = ((props[prop_name], top[base][prop_name], base),
                        (top[base][prop_name], props[prop_name], schema_name))
                for owner, other, other_name in pair:
                    values = owner.get("enum")
                    if not isinstance(values, list) or is_exempt(other):
                        continue
                    if "example" not in other or other["example"] in values:
                        continue
                    findings.append(
                        "② 쌍둥이 모순 — %s · %s.%s : example %r 이 형제 enum %s 밖"
                        % (name, other_name, prop_name, other["example"], values))
    return findings


def main() -> int:
    targets = sys.argv[1:] or sorted(glob.glob(os.path.join(CONTRACTS_DIR, "*.json")))
    if not targets:
        print("검사할 정본이 없습니다.")
        return 0

    total = 0
    for target in targets:
        findings = check_one(target)
        total += len(findings)
        head = os.path.basename(target)
        if not findings:
            print("%s — ✅ example 이 확정값 목록 밖인 자리가 없습니다." % head)
            continue
        print("%s — ⚠ %d건" % (head, len(findings)))
        for finding in sorted(set(findings)):
            print("  %s" % finding)

    print()
    if total:
        print("⚠ 확인이 필요한 자리 %d건 — 확정값이 있으면 그 값으로, 없으면 example 을"
              " 지우고 x-no-example 에 사유를 적습니다(계약 작성 규약 「예시도 계약의"
              " 일부다」)." % total)
        print("⛔ 이 검사기는 «막지 않는다» — omf-mes#191 반영이 끝나 0건이 되면"
              " 게이트로 올립니다.")
    else:
        print("✅ 전건 통과 — 게이트로 올릴 수 있습니다(종료 코드 1 로 바꾼다).")
    return 0          # ⛔ 언제나 0 — 위 「게이트가 아니다」 절을 보라


if __name__ == "__main__":
    raise SystemExit(main())
