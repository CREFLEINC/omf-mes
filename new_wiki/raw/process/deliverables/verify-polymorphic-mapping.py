#!/usr/bin/env python3
"""다형 참조에 **대응표**가 적혀 있는가 — 공유계약 A-10 검사기.

왜 필요한가
-----------
`{X}_type_code` + `{X}_id` 처럼 **두 칸으로 하나를 가리키는 자리**가 있다.
앞칸이 「어느 표를 가리키는가」를, 뒷칸이 「그중 어느 것인가」를 말한다.

⛔ **이런 자리에는 FK 를 걸 수 없다.** FK 는 「이 칸은 **항상** 저 표를
가리킨다」일 때만 성립하는데, 여기서는 가리키는 표가 앞칸 값에 따라 바뀐다.

그래서 **DB 가 무결성을 지켜 주지 않는다.** 「거래처를 가리킨다」고 적고
창고 번호를 넣어도 저장된다. 실패가 **조용하다** — 저장은 성공하고, 나중에
화면이 그것을 풀어 보이려 할 때 엉뚱한 이름이 뜨거나 아무것도 안 뜬다.

**공유계약 A-10** 이 그래서 이렇게 정했다.

    다형 참조는 **유형 코드 ↔ 대상 테이블 대응표**를 **계약이 정한다.**

대응표가 **유일한 근거**다. 서버도 화면도 거기서 읽는다.

무엇을 검사하나
---------------
① 계약에서 다형 짝을 찾는다 — **응답·요청 스키마와 쿼리 파라미터 둘 다**
② 그 유형 코드 필드에 **대응표가 적혀 있는가**를 본다
③ 없는 것을 낸다

다형 짝을 어떻게 가리나 — ⭐ **이름만으로는 못 가린다**
------------------------------------------------------
`itemTypeCode` + `itemId` 는 짝처럼 보이지만 **다형이 아니다.** 유형은 품목의
**속성**일 뿐이고 `itemId` 는 언제나 `mdm.item` 을 가리킨다.

**판별** — 기준 이름과 **같은 이름의 테이블이 물리 모델에 있는가.**

    itemTypeCode        → mdm.item 이 있다        → 속성 + 고정 참조 (다형 아님)
    destinationTypeCode → destination 표가 없다   → ⭐ 다형 참조

이 기준으로 물리 모델을 세면 **16쌍 / 15테이블**이 나온다. 확대 4차에 사람이
손으로 센 값과 정확히 같다.

⚠ 이 검사기가 못 보는 것
------------------------
**대응표가 「있는가」만 본다. 「맞는가」는 못 본다.** 틀린 대응을 적어도 통과한다.
맞는지는 사람이 본다 — 이 저장소의 「검사기는 구조를 보고 그릴 수 있나는
사람이 본다」 경계 그대로다.

쓰기
----
    python3 verify-polymorphic-mapping.py           # 검사
    python3 verify-polymorphic-mapping.py --list    # 다형 짝 전체를 보인다

⛔ 위반이 있으면 종료 코드 1.
"""
from __future__ import annotations

import collections
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SQL = os.path.join(
    HERE, "..", "docs", "research", "2026-07-23-데이터모델링",
    "mes_postgresql_physical_model.sql",
)
CONTRACTS = os.path.join(HERE, "openapi", "*.json")

# 대응표로 인정하는 표시 — 「이 값 → 저 테이블」이 실제로 적혀 있어야 한다.
# 화살표와 스키마.테이블 꼴을 함께 요구한다. 값 나열만으로는 통과하지 못한다.
MAPPING = re.compile(r"→\s*[a-z_]+\.[a-z_]+")
MIN_TARGETS = 2   # 대응표라면 최소 두 갈래는 적힌다. 하나면 다형일 이유가 없다.


def snake(camel: str) -> str:
    """camelCase 를 snake_case 로. destinationType → destination_type."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", camel).lower()


def model_tables() -> set[str]:
    """물리 모델의 테이블 이름(스키마 뺀 것)을 모은다."""
    with io.open(SQL, encoding="utf-8") as f:
        sql = f.read()
    return {
        m.group(1).split(".")[-1]
        for m in re.finditer(r"CREATE TABLE ([a-z_]+\.[a-z_]+)", sql)
    }


# ⛔ 물리 모델만 보면 «표가 아직 없는 도메인» 이 통째로 오탐이 된다 — 2026-08-18
#    05 설비·툴은 점검·고장·보전 표가 하나도 없어, 「점검 유형(일상·정기·보전)」 같은
#    순수 «분류 코드» 까지 다형 참조로 읽혔다. 가리킬 표가 없어서가 아니라
#    **애초에 표를 가리키지 않는** 값이다.
#
# ⚠ 오탐을 그냥 두면 「대응표 없음」 목록이 부풀고, 부푼 목록은 읽히지 않는다.
#    그래서 사람이 판정한 예외만 이름과 이유로 여기 적는다.
#    ⛔ 「대응표를 적기 귀찮아서」 넣지 않는다 — 판정 근거는 「이 값이 무엇을
#       가리키는가」 하나다. 가리키는 것이 있으면 대응표를 적는다.
NOT_POLYMORPHIC = {
    "inspection": ("설비 점검 «유형»(일상·정기·보전) 분류 코드다 — 표를 가리키지 "
                   "않는다. 점검 기록 표가 물리 모델에 없어 이름이 비어 보일 뿐이다"),
}


def is_polymorphic(base: str, tables: set[str]) -> bool:
    """기준 이름과 같은 테이블이 없으면 다형이다.

    있으면 유형 코드는 그 테이블의 **속성**이고 id 는 그 테이블을 고정으로
    가리킨다 — FK 가 걸리므로 A-10 대상이 아니다.

    ⛔ 예외 — 표를 아예 가리키지 않는 분류 코드는 NOT_POLYMORPHIC 에 적는다.
    """
    if base in NOT_POLYMORPHIC:
        return False
    return snake(base) not in tables


def has_mapping(prop: dict) -> bool:
    """이 유형 코드 필드에 대응표가 적혀 있는가."""
    text = " ".join(
        str(prop.get(k, "")) for k in ("description", "x-internal-note")
    )
    return len(MAPPING.findall(text)) >= MIN_TARGETS


def scan_schemas(doc: dict, contract: str, tables: set[str]) -> list[dict]:
    """응답·요청 스키마에서 다형 짝을 찾는다."""
    out = []
    for schema_name, schema in ((doc.get("components") or {}).get("schemas") or {}).items():
        props = schema.get("properties") or {}
        if not props and ("allOf" in schema or "oneOf" in schema):
            # ⚠ 조용히 넘어가지 않는다 — 가지 안에 짝을 직접 쓰면 말없이 빠진다.
            out.append({"contract": contract, "schema": schema_name, "field": "(allOf)",
                        "base": "", "where": "schema", "ok": True, "skipped": True})
            continue
        for prop_name, prop in props.items():
            m = re.match(r"^(.*)TypeCode$", prop_name)
            if not m or not isinstance(prop, dict):
                continue
            base = m.group(1)
            if base + "Id" not in props or not is_polymorphic(base, tables):
                continue
            out.append({"contract": contract, "schema": schema_name, "field": prop_name,
                        "base": base, "where": "schema", "ok": has_mapping(prop),
                        "skipped": False})
    return out


def scan_params(doc: dict, contract: str, tables: set[str]) -> list[dict]:
    """경로의 쿼리 파라미터에서 다형 짝을 찾는다.

    ⭐ 스키마만 보면 여기가 통째로 빠진다. 오히려 **쿼리 쪽이 더 급하다** —
    프런트가 값을 직접 만들어 보내므로 「무슨 값을 넣나」를 알아야 한다.
    """
    out = []
    for path, ops in (doc.get("paths") or {}).items():
        params: dict[str, dict] = {}
        for key, op in ops.items():
            src = op if key == "parameters" else (op.get("parameters") if isinstance(op, dict) else None)
            for prm in (src or []):
                if isinstance(prm, dict) and prm.get("name"):
                    params.setdefault(prm["name"], prm)
        for name, prm in params.items():
            m = re.match(r"^(.*)TypeCode$", name)
            if not m or (m.group(1) + "Id") not in params:
                continue
            base = m.group(1)
            if not is_polymorphic(base, tables):
                continue
            merged = dict(prm)
            merged["description"] = " ".join(
                str(prm.get(k, "")) for k in ("description", "x-internal-note"))
            out.append({"contract": contract, "schema": path, "field": name,
                        "base": base, "where": "query", "ok": has_mapping(merged),
                        "skipped": False})
    return out


def scan(tables: set[str]) -> list[dict]:
    """계약 전체 — 스키마와 쿼리 파라미터 둘 다에서 다형 짝을 모은다."""
    out = []
    for path in sorted(glob.glob(CONTRACTS)):
        name = os.path.basename(path)
        with io.open(path, encoding="utf-8") as f:
            doc = json.load(f)
        out.extend(scan_schemas(doc, name, tables))
        out.extend(scan_params(doc, name, tables))
    return out


def main() -> int:
    tables = model_tables()
    scanned = scan(tables)
    skipped = [h for h in scanned if h.get("skipped")]
    hits = [h for h in scanned if not h.get("skipped")]
    missing = [h for h in hits if not h["ok"]]

    by_base: dict[str, list[dict]] = collections.defaultdict(list)
    for h in hits:
        by_base[h["base"]].append(h)

    print(f"다형 참조 대응표 검사 — 공유계약 A-10")
    print("─" * 66)
    n_q = sum(1 for h in hits if h["where"] == "query")
    print(f"  다형 짝 {len(hits)}곳 (스키마 {len(hits)-n_q} · 쿼리 {n_q}) · "
          f"이름 {len(by_base)}종 (물리 모델 테이블 {len(tables)}개로 판별)")
    if skipped:
        print(f"  ⚠ allOf/oneOf 라 properties 를 못 본 스키마 {len(skipped)}개 — "
              f"가지 안에 짝이 있으면 못 잡는다")
        for sk in skipped:
            print(f"      {sk['contract'].replace('.json','')} · {sk['schema']}")

    if "--list" in sys.argv:
        for base, group in sorted(by_base.items()):
            done = sum(1 for g in group if g["ok"])
            print(f"\n  {base}TypeCode — {done}/{len(group)} 적혀 있다")
            for g in group:
                mark = "✅" if g["ok"] else "⛔"
                print(f"    {mark} {g['contract'].replace('.json',''):<22} {g['schema']}")

    if not missing:
        print(f"\n✅ {len(hits)}곳 전부 대응표가 있습니다.")
        return 0

    print(f"\n⛔ 대응표 없음 {len(missing)}곳")
    shown: set[str] = set()
    for h in missing:
        key = f"{h['contract']}|{h['field']}"
        if key in shown:
            continue
        shown.add(key)
        same = [x for x in missing if x["field"] == h["field"]
                and x["contract"] == h["contract"]]
        where = same[0]["schema"] + (f" 외 {len(same)-1}" if len(same) > 1 else "")
        tag = "쿼리" if h["where"] == "query" else "스키마"
        print(f"  [{tag}] {h['contract'].replace('.json',''):<20} {h['field']:<22} {where}")

    print(
        "\n→ 유형 코드 필드의 description 또는 x-internal-note 에 대응표를 적는다.\n"
        "   예)  LOCATION → mdm.location · PARTNER → mdm.partner\n"
        "   ⛔ 값 나열만으로는 부족하다 — FK 가 없어 이 표가 유일한 무결성 근거다."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
