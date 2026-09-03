#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""목록·요약 응답이 표준형인가 — 공유계약 §L(조회·집계) 게이트.

왜 필요한가
-----------
2026-08-29 실측에서 목록 응답의 «봉투»가 다섯 형태로 갈려 있었다. 화면마다
같은 것을 다르게 받으면 프론트가 자원마다 다른 코드를 쓴다. §L 에 다섯 소절
(L-1-1·L-2-1·L-3-2·L-4-1·L-5-1)을 세우면서, 그 조항을 지키는지 매번 볼
검사기를 함께 둔다 — 조항만 세우면 다음 판에서 다시 갈린다.

⛔ 가장 먼저 지킬 것 — `$ref` 를 «해소한 뒤에» 센다
---------------------------------------------------
해소하지 않으면 최상위 목록형 GET 이 **131 → 94** 로 줄고 `{items}` 35자리 중
32자리를 못 본다(2026-08-29 · 두 방식으로 다 돌려 확인). 응답 스키마를 이름으로
가리키는 자리가 훨씬 많기 때문이다.

무엇을 보나 (여섯)
------------------
① 최상위 목록형 200 이 `{items,page}`·`{items}`·`{items,page,summary}` 중 하나인가
   — 그 밖의 형은 ⚠. 기준선 = `{items,totalCount}` 9자리(전부 equipment-05설비툴).
② `page` 가 있으면 그 `$ref` 가 `PageMeta` 인가.
③ 요약 전용 경로와 그 «짝» 목록 경로의 질의 집합이 `page`·`size`·`sort` 를 뺀
   나머지에서 같은가 — 다르면 ⛔. 어느 쪽에만 있는 축인지 이름을 찍는다.
④ 집계 페이로드에 `asOf` 가 `required` 로 있는가 — 없으면 ⚠.
   `calculatedAt`·`snapshotAt`·`generatedAt` 이 쓰였으면 ⛔(L-5-1 · 기준선 0건).
⑤ `sort` 파라미터에 `enum` 이 있는가 — 없으면 ⚠. 있는데 `키Asc`/`키Desc` 표기가
   아니면 ℹ(L-4-1).
⑥ 기간 쌍(`*From`/`*To`)이 둘 다 optional 이고 상위 경로 변수도 없으면
   「무계 목록 후보」 ⚠(L-3-2). 그리고 끝 경계를 「이하」로 적거나
   `23:59:59` 를 예시로 든 자리는 ⛔(L-3-1 · `date-time` 은 반열림이다).

⚠ 이 검사기가 «안» 보는 것
--------------------------
  - **요약 «값»이 맞는지는 안 본다** — 형만 본다. 「필터 전체를 셌는가」는
    계약이 답할 수 있는 물음이 아니다
  - **어느 화면이 요약 칸을 갖는지 모른다** — 그것은 화면 스펙에 있다. 그래서
    「`summary` 가 없다」를 결손으로 세지 않고 「형이 표준형 밖이다」만 센다
  - `check-enum-narrowing.py` 와 «겹치는 협착 판정은 하지 않는다** — ⑤는 `enum`
    이 있는가·표기가 무엇인가만 보고, 값이 좁아졌는지는 그쪽이 본다
  - `$ref` 가 파일을 넘는 자리(`외부.json#/…`) — 해소하지 않고 건너뛴다
  - 요약 전용 경로의 «짝»을 기계로 못 찾는 자리(마지막 조각이 `-summary` 처럼
    낱말에 붙어 있는 것) — ③의 대조 대상 밖이고 목록으로만 낸다

쓰기
----
    python3 design/schema/generators/openapi/check-query-envelope.py
"""
from __future__ import annotations

import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
# Tier 0 — OpenAPI JSON 정본. Phase 5 컷오버(2026-08-25)로 design/wiki/api-contracts/openapi/가 정본 위치다.
CONTRACTS_DIR = os.path.join(HERE, "..", "..", "..", "wiki", "api-contracts", "openapi")

HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")

STANDARD_SHAPES = (
    frozenset({"items", "page"}),
    frozenset({"items"}),
    frozenset({"items", "page", "summary"}),
)
# 기준선 — 2026-09-03 실측. ⛔ 늘리지 않는다. 줄었으면 그 수를 낮춘다.
#
# ⭐ 왜 게이트가 아니라 래칫인가 — ⑥ 무계 목록 47건처럼 한 회차에 닫히는 수가
#    아닌 축이 섞여 있다(닫으려면 화면마다 「무엇으로 범위를 좁히나」를 정해야
#    한다). 게이트로 걸면 초록을 기준선으로 못 쓴다. 그래서 **늘면 ⛔, 줄면
#    「기준선을 낮추라」**로 둔다 — 새로 만드는 목록이 같은 구멍을 반복하는
#    것만 막는다. 축을 «따로» 세는 이유는, 합계 하나로 두면 한 축이 줄고 다른
#    축이 느는 것이 상쇄되어 안 보이기 때문이다.
BASELINE_OFF_SHAPE = 13   # (1) 표준형 밖의 목록 응답
BASELINE_NO_ASOF = 11     # (4) 집계인데 `asOf` 가 required 가 아니다
BASELINE_SORT_FREE = 5    # (5) `sort` 에 enum 이 없다
BASELINE_UNBOUNDED = 47   # (6) 무계 목록 후보

SUMMARY_WORDS = ("summary", "distribution", "trend")
PAGING_AXES = frozenset({"page", "size", "sort"})
BANNED_ASOF = ("calculatedAt", "snapshotAt", "generatedAt")
AGG_SUFFIX = ("Summary", "Distribution", "Trend")

SORT_TOKEN = re.compile(r"^[a-z][A-Za-z0-9]*(Asc|Desc)$")
PERIOD_FROM = re.compile(r"^(.+)From$")
PERIOD_TO = re.compile(r"^(.+)To$")


# ── $ref 해소 ────────────────────────────────────────────────────────────────
def deref(node, doc, seen=None):
    """`#/…` 로컬 참조를 해소한다. 파일을 넘는 참조와 순환은 빈 사전으로 낸다."""
    seen = seen or set()
    while isinstance(node, dict) and "$ref" in node:
        ref = node["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/") or ref in seen:
            return {}
        seen.add(ref)
        cur = doc
        for part in ref[2:].split("/"):
            if not isinstance(cur, dict):
                return {}
            cur = cur.get(part.replace("~1", "/").replace("~0", "~"))
        node = cur
    return node if isinstance(node, dict) else {}


def properties(schema, doc, depth=0):
    """해소한 스키마의 최상위 프로퍼티. `allOf` 는 얕게 합친다."""
    schema = deref(schema, doc)
    if depth > 4 or not schema:
        return {}
    out = dict(schema.get("properties") or {})
    for part in schema.get("allOf") or []:
        out.update(properties(part, doc, depth + 1))
    return out


def required_of(schema, doc, depth=0):
    schema = deref(schema, doc)
    if depth > 4 or not schema:
        return set()
    out = set(schema.get("required") or [])
    for part in schema.get("allOf") or []:
        out |= required_of(part, doc, depth + 1)
    return out


def ok_schema(op, doc):
    """200 응답의 `application/json` 스키마(해소 전 노드)."""
    body = ((op.get("responses") or {}).get("200") or {})
    body = deref(body, doc)
    content = (body.get("content") or {}).get("application/json") or {}
    return content.get("schema")


# ── 파라미터 ────────────────────────────────────────────────────────────────
def params_of(item, op, doc):
    """경로 단위 ＋ 오퍼레이션 단위 질의 파라미터 → {이름: 파라미터}."""
    out = {}
    for raw in list(item.get("parameters") or []) + list(op.get("parameters") or []):
        p = deref(raw, doc)
        if p.get("in") == "query" and p.get("name"):
            out[p["name"]] = p
    return out


# ── 판정 조각(테스트가 직접 부른다) ──────────────────────────────────────────
def is_standard_shape(names) -> bool:
    return frozenset(names) in STANDARD_SHAPES


def is_summary_path(path: str) -> bool:
    last = path.rstrip("/").rsplit("/", 1)[-1].lower()
    return any(last.endswith(w) for w in SUMMARY_WORDS)


def pair_path(path: str):
    """요약 전용 경로의 «짝» 목록 경로. 기계로 못 찾으면 None."""
    base = path.rstrip("/")
    last = base.rsplit("/", 1)[-1].lower()
    if last not in SUMMARY_WORDS:
        return None                     # `-summary` 처럼 낱말에 붙은 것 — 대조 밖
    parent = base.rsplit("/", 1)[0]
    return parent or None


def sort_style(values) -> str:
    """`키Asc`/`키Desc` 표기인가 — 'ok' · 'other'."""
    return "ok" if values and all(SORT_TOKEN.match(str(v)) for v in values) else "other"


def boundary_violation(param) -> bool:
    """끝 경계를 「이하」로 적거나 `23:59:59` 를 예시로 든 자리인가(L-3-1)."""
    desc = param.get("description") or ""
    example = str((param.get("schema") or {}).get("example") or "")
    example += " " + str(param.get("example") or "")
    # ⚠ 「23:59:59 가 «아니라» 익일 00:00:00」은 규약을 «옳게» 설명하는 문장이다.
    #    그 문형을 위반으로 세면 규약을 지킨 자리가 빨갛게 된다.
    if "23:59:59" in desc and "아니라" not in desc:
        return True
    if "23:59:59" in example:
        return True
    if re.search(r"(이 시각|그 시각|끝)[^.。]{0,12}이하", desc):
        return True
    return False


def is_agg_schema_name(name: str) -> bool:
    return any(name.endswith(s) for s in AGG_SUFFIX)


# ── 본체 ────────────────────────────────────────────────────────────────────
def main() -> int:
    docs, ops, merged = {}, [], {}
    for f in sorted(glob.glob(os.path.join(CONTRACTS_DIR, "*.json"))):
        name = os.path.basename(f)
        with open(f, encoding="utf-8") as fh:
            docs[name] = json.load(fh)
        for path, item in (docs[name].get("paths") or {}).items():
            if not isinstance(item, dict):
                continue
            merged.setdefault(path, (name, item))
            for method in [m for m in item if m.lower() in HTTP_METHODS]:
                if isinstance(item[method], dict):
                    ops.append((name, path, method, item[method], item))

    off_shape, bad_page = [], []                          # ①②  ⚠
    query_gap, unpaired, exempt = [], [], []               # ③    ⛔ / 목록 / 선언된 면제
    no_asof, banned = [], []                              # ④    ⚠ / ⛔
    sort_free, sort_style_odd = [], []                    # ⑤    ⚠ / ℹ
    unbounded, boundary = [], []                          # ⑥    ⚠ / ⛔
    list_total = 0
    shapes = {}

    # ①②④⑤⑥ — 오퍼레이션 축
    for name, path, method, op, item in ops:
        doc = docs[name]
        qs = params_of(item, op, doc)

        # ⑤ 정렬 키
        sp = qs.get("sort")
        if sp is not None:
            values = (sp.get("schema") or {}).get("enum")
            if not values:
                sort_free.append((name, method.upper(), path))
            elif sort_style(values) != "ok":
                sort_style_odd.append((name, method.upper(), path, list(values)))

        # ⑥ 기간 쌍
        froms = {m.group(1): n for n in qs for m in [PERIOD_FROM.match(n)] if m}
        tos = {m.group(1): n for n in qs for m in [PERIOD_TO.match(n)] if m}
        for stem in sorted(set(froms) & set(tos)):
            a, b = qs[froms[stem]], qs[tos[stem]]
            if method.lower() == "get" and not a.get("required") \
                    and not b.get("required") and "{" not in path:
                unbounded.append((name, method.upper(), path, stem))
            for p in (a, b):
                if boundary_violation(p):
                    boundary.append((name, method.upper(), path, p.get("name")))

        if method.lower() != "get":
            continue

        schema = ok_schema(op, doc)
        if schema is None:
            continue
        props = properties(schema, doc)
        if "items" not in props:
            continue
        list_total += 1
        names = frozenset(props)
        shapes[names] = shapes.get(names, 0) + 1
        if not is_standard_shape(names):
            off_shape.append((name, method.upper(), path, sorted(names)))
        # ② page 는 PageMeta 인가
        if "page" in props:
            ref = (props["page"] or {}).get("$ref") or ""
            if not ref.endswith("/PageMeta"):
                bad_page.append((name, method.upper(), path, ref or "(인라인)"))

    # ④ 집계 페이로드 — asOf 가 required 인가 · 금지 이름을 쓰지 않았나
    for name, doc in docs.items():
        for sname, schema in (doc.get("components", {}).get("schemas") or {}).items():
            if not isinstance(schema, dict) or not is_agg_schema_name(sname):
                continue
            props = properties(schema, doc)
            req = required_of(schema, doc)
            for bad in BANNED_ASOF:
                if bad in props:
                    banned.append((name, sname, bad))
            if "asOf" not in props or "asOf" not in req:
                no_asof.append((name, sname,
                                "없음" if "asOf" not in props else "required 아님"))

    # ③ 요약 전용 경로 ↔ 짝 목록 경로의 질의 집합
    summary_paths = [p for p in merged if is_summary_path(p)]
    for path in sorted(summary_paths):
        sname, sitem = merged[path]
        sop = sitem.get("get")
        if not isinstance(sop, dict):
            continue
        # ⛔ 「모집단이 애초에 다르다」고 계약이 «선언한» 자리는 대조 밖이다.
        #    선례: /quality/defect-records/distribution — 원천이 검사 결과가 아니라
        #    불량 레코드라 판정·최종회차·교정만료 축이 없다(omf-mes#192·#229 확정).
        #    질의 축을 맞추면 그 확정을 뒤집는다.
        #    ⚠ 검사기에 목록을 박지 않는다 — 계약이 x-envelope-exempt 로 사유를 적는다.
        if sop.get("x-envelope-exempt"):
            exempt.append((sname, path, str(sop["x-envelope-exempt"])))
            continue
        pair = pair_path(path)
        if pair is None or pair not in merged:
            unpaired.append((sname, path, "짝을 기계로 못 찾음" if pair is None
                             else "짝 경로 %s 가 계약에 없다" % pair))
            continue
        lname, litem = merged[pair]
        lop = litem.get("get")
        if not isinstance(lop, dict):
            unpaired.append((sname, path, "짝 경로에 GET 이 없다"))
            continue
        a = set(params_of(sitem, sop, docs[sname])) - PAGING_AXES
        b = set(params_of(litem, lop, docs[lname])) - PAGING_AXES
        if a != b:
            query_gap.append((sname, path, pair, sorted(b - a), sorted(a - b)))

    # ── 출력 (⛔ 전건 · 자르지 않는다) ──────────────────────────────────────
    print("최상위 목록형 200 %d자리 검사 ($ref 해소 후) — 형 분포" % list_total)
    for names, n in sorted(shapes.items(), key=lambda kv: (-kv[1], sorted(kv[0]))):
        mark = "✅" if is_standard_shape(names) else "⚠ "
        print("   %s {%s} %d" % (mark, ", ".join(sorted(names)), n))
    print()

    if off_shape:
        print("⚠ ① 표준형 밖의 목록 응답 %d자리 — 공유계약 L-1-1 ⑴" % len(off_shape))
        for f, m, p, names in off_shape:
            print("   %-26s %-6s %-52s {%s}" % (f, m, p[:52], ", ".join(names)))
        print()
    if bad_page:
        print("⚠ ② `page` 가 `PageMeta` 가 아닌 자리 %d건" % len(bad_page))
        for f, m, p, ref in bad_page:
            print("   %-26s %-6s %-46s %s" % (f, m, p[:46], ref))
        print()
    if query_gap:
        print("⛔ ③ 요약 전용 경로와 짝 목록의 질의 축이 다릅니다 %d건 — 공유계약 L-1-1 ⑶"
              % len(query_gap))
        for f, sp, lp, only_list, only_sum in query_gap:
            print("   %-26s %s" % (f, sp))
            print("   %-26s   ↔ %s" % ("", lp))
            if only_list:
                print("   %-26s   목록에만: %s" % ("", " · ".join(only_list)))
            if only_sum:
                print("   %-26s   요약에만: %s" % ("", " · ".join(only_sum)))
        print("\n   ⭐ 목록에 질의를 더할 때 짝을 «같은 판»에서 고친다.\n")
    if exempt:
        print("ℹ  ③ 계약이 «모집단이 다르다»를 선언해 대조 밖인 경로 %d건" % len(exempt))
        for sname, path, why in exempt:
            print("   %-28s %-46s %s" % (sname[:28], path[:46], why[:70]))
        print()

    if unpaired:
        print("ℹ  ③ 짝을 기계로 못 찾은 요약 전용 경로 %d건 (대조 밖 · 사람이 본다)"
              % len(unpaired))
        for f, p, why in unpaired:
            print("   %-26s %-52s %s" % (f, p[:52], why))
        print()
    if banned:
        print("⛔ ④ 기준 시각에 금지된 이름을 썼습니다 %d건 — 이름은 `asOf` 하나다"
              "(공유계약 L-5-1 ⑵)" % len(banned))
        for f, s, b in banned:
            print("   %-26s %-30s %s" % (f, s, b))
        print()
    if no_asof:
        print("⚠ ④ 집계 페이로드인데 `asOf` 가 `required` 가 아닌 스키마 %d건 — L-5-1 ⑴"
              % len(no_asof))
        for f, s, why in no_asof:
            print("   %-26s %-34s %s" % (f, s, why))
        print()
    if sort_free:
        print("⚠ ⑤ `sort` 에 `enum` 이 없는 자리 %d건 — 제한을 `description` 에만 적으면"
              " 구현이 «못 본다»(L-4-1 ⑴)" % len(sort_free))
        for f, m, p in sort_free:
            print("   %-26s %-6s %s" % (f, m, p[:52]))
        print()
    if sort_style_odd:
        print("ℹ  ⑤ `키Asc`/`키Desc` 표기가 아닌 `sort` %d건 — L-4-1 ⑵"
              % len(sort_style_odd))
        for f, m, p, vals in sort_style_odd:
            print("   %-26s %-6s %-40s %s" % (f, m, p[:40], " · ".join(map(str, vals))))
        print()
    if unbounded:
        print("⚠ ⑥ 무계 목록 후보 %d건 — 기간 쌍이 둘 다 optional 이고 상위 식별자도 없다"
              "(L-3-2 ⑶)" % len(unbounded))
        for f, m, p, stem in unbounded:
            print("   %-26s %-6s %-46s %sFrom/%sTo" % (f, m, p[:46], stem, stem))
        print()
    if boundary:
        print("⛔ ⑥ 끝 경계 규약을 어긴 자리 %d건 — `date-time` 은 «반열림»이라"
              " `23:59:59` 를 보내면 마지막 1초가 빠진다(공유계약 L-3-1)" % len(boundary))
        for f, m, p, pname in boundary:
            print("   %-26s %-6s %-46s %s" % (f, m, p[:46], pname))
        print("\n   ⭐ 「그날까지」는 «익일 00:00:00» 을 보낸다.\n")

    grew = False
    for label, got, base, name in (
            ("① 표준형 밖", len(off_shape), BASELINE_OFF_SHAPE, "BASELINE_OFF_SHAPE"),
            ("④ `asOf` 미필수", len(no_asof), BASELINE_NO_ASOF, "BASELINE_NO_ASOF"),
            ("⑤ `sort` enum 없음", len(sort_free), BASELINE_SORT_FREE, "BASELINE_SORT_FREE"),
            ("⑥ 무계 목록", len(unbounded), BASELINE_UNBOUNDED, "BASELINE_UNBOUNDED")):
        if got > base:
            print("⛔ %s 기준선 %d 보다 %d 늘었다 — 새로 만든 목록이 같은 구멍을 반복했다."
                  % (label, base, got - base))
            grew = True
        elif got < base:
            print("⭐ %s 기준선 %d → %d 로 줄었다. 이 파일의 `%s` 을 %d 로 낮추세요."
                  % (label, base, got, name, got))
        else:
            print("✅ %s 기준선 %d 유지 — 늘지 않았다." % (label, base))
    print()

    hard = len(query_gap) + len(banned) + len(boundary)
    if hard:
        print("⛔ 막는 항목 %d건 (③ %d · ④금지이름 %d · ⑥경계 %d)"
              % (hard, len(query_gap), len(banned), len(boundary)))
        return 1
    if grew:
        return 1
    print("✅ 막는 항목 0건 — 목록형 %d자리 검사" % list_total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
