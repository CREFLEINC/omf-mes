#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""귀속 사번을 «받을 곳»이 계약에 있는가.

왜 필요한가
-----------
공유계약 **D-5**(귀속 정보는 세션이 아니다)가 「현장 단말·모바일의 **쓰기
요청에 사번이 필수**」라고 정해 두었다. 서버는 사번 세션을 갖지 않으므로
단말이 매 쓰기 요청에 `X-Worker-No` 헤더로 싣는다.

**그런데 그 사번을 받을 자리가 계약에 선언돼 있지 않았다** — 전 계약 검색
0건(이슈 #178). ⛔ 저장 충돌 토큰(`If-Match`)에서 겪은 것과 **같은 형태**다.
필수로 받아 놓고 받을 곳을 선언하지 않아 구현이 19건 막혔다(2026-08-17).

무엇을 보나
-----------
① 요구서(`06-API-요구서-*.md`)의 화면별 §3 소절에서 **현장 단말(P-)·모바일(M-)
   화면이 부르는 쓰기 오퍼레이션**을 뽑는다.
② 그 오퍼레이션마다 귀속 헤더 파라미터를 `$ref` 로 선언하는지 본다.
③ **관리웹(W-)도 «같은 오퍼레이션»을 부르면 선택판**이어야 한다 — 필수로 걸면
   관리웹이 «없는 사번»을 지어내게 된다.

    현장·모바일 전용   →  WorkerNo           (required: true)
    관리웹도 부른다    →  WorkerNoOptional   (required: false)

⭐ 선례를 그대로 따랐다 — `IfMatchVersion` / `IfMatchVersionOptional` 두 벌.

⚠ 이 검사기가 «안» 보는 것 (§2-4 — 적게 세면 그것을 믿고 놓친다)
----------------------------------------------------------------
  - **소절 밖**(문서 머리말·역방향 점검 표)에만 적힌 호출 — 못 본다
  - **메서드를 안 적고 경로만** 쓴 줄 — 못 본다
  - 한 소절이 **여러 화면을 겹쳐** 다룰 때의 화면별 귀속 — 소절 전체로 뭉갠다
  - 요구서에 **아직 안 적힌** 화면의 호출 — 없는 것으로 친다
  - 사번 값이 **맞는 사람인지** — 계약이 답할 수 있는 물음이 아니다(도용 리스크
    수용, 공유계약 D-1). 검사기는 «받을 자리»가 있는지만 본다
  - 관리웹 전용 오퍼레이션의 헤더 선언 — **막지 않고 알리기만** 한다
  - 요구서가 **한글 자리표시**로 여러 리소스를 접어 적은 줄(`/logistics/{문서}/…`) — 경로가 잘린 채 잡힌다
  - **`…` 로 앞을 줄인 경로**(`POST …:report-print`) — 못 본다. ⛔ #178 이 `:report-print` 를 놓친 자리가 여기다

⇒ 그래서 이 수치는 **하한**이다. 「전부 덮었다」가 아니라 「여기까지는 덮었다」.

쓰기
----
    python3 design/schema/generators/openapi/check-worker-no.py
    python3 design/schema/generators/openapi/check-worker-no.py --list   실측 목록만 찍는다
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
# Tier 0 — OpenAPI JSON 정본. Phase 5 컷오버(2026-08-25)로 design/wiki/api-contracts/openapi/가 정본 위치다.
CONTRACTS_DIR = os.path.join(ROOT, "design", "wiki", "api-contracts", "openapi")

REQUIRED_REF = "#/components/parameters/WorkerNo"
OPTIONAL_REF = "#/components/parameters/WorkerNoOptional"

HEAD = re.compile(r"^###\s+§?3-\d+[.\s]")
SID = re.compile(r"\b([PMW]-\d{2}-\d{2})\b")
CALL = re.compile(r"\b(POST|PUT|PATCH|DELETE)\s+(/[A-Za-z0-9_{}/:.\-]+)")
HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")


def norm(path: str) -> str:
    """경로 파라미터 «이름»의 차이를 지운다.

    요구서가 같은 경로를 `{id}` 와 `{putawayTaskId}` 로 달리 적은 자리가 있어,
    이름을 그대로 두고 세면 한 오퍼레이션을 둘로 «많게» 센다.
    """
    return re.sub(r"\{[^}]*\}", "{}", path)


def load_contracts() -> tuple[dict, dict]:
    """계약 실물을 읽는다 → (정규경로 → (파일, 실경로, {메서드})), (파일 → 문서)."""
    real, docs = {}, {}
    for f in sorted(glob.glob(os.path.join(CONTRACTS_DIR, "*.json"))):
        name = os.path.basename(f)
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh)
        docs[name] = d
        for p, item in d.get("paths", {}).items():
            methods = {m.upper() for m in item if m.lower() in HTTP_METHODS}
            real[norm(p)] = (name, p, methods)
    return real, docs


def scope(real: dict) -> tuple[dict, dict]:
    """요구서에서 귀속 헤더가 필요한 오퍼레이션을 뽑는다.

    반환 → ({(파일, 경로, 메서드): {'field': {화면}, 'web': {화면}}}, 못 찾은 호출)
    """
    calls: dict = collections.defaultdict(lambda: {"field": set(), "web": set()})
    unresolved: dict = collections.defaultdict(set)

    def absorb(ids: list[str], lines: list[str]) -> None:
        if not ids:
            return
        field = {i for i in ids if i[0] in "PM"}
        web = {i for i in ids if i[0] == "W"}
        for method, raw in CALL.findall("\n".join(lines)):
            raw = raw.rstrip(".,·")
            key = norm(raw)
            if key not in real:
                if field:
                    unresolved[raw].update(ids)
                continue
            fname, path, methods = real[key]
            if method not in methods:
                if field:
                    unresolved["%s %s" % (method, path)].update(ids)
                continue
            op = (fname, path, method)
            calls[op]["field"] |= field
            calls[op]["web"] |= web

    for f in sorted(glob.glob(os.path.join(ROOT, "design", "wiki", "api-contracts",
                                           "06-API-요구서-*.md"))):
        ids: list[str] = []
        buf: list[str] = []
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                if HEAD.match(line):
                    absorb(ids, buf)
                    ids, buf = SID.findall(line), []
                else:
                    buf.append(line)
        absorb(ids, buf)

    targets = {op: v for op, v in calls.items() if v["field"]}
    return targets, unresolved


def declared_refs(doc: dict, path: str, method: str) -> set[str]:
    """그 오퍼레이션이 선언한 파라미터 «참조»를 모은다(경로 단위 + 오퍼레이션 단위)."""
    item = doc.get("paths", {}).get(path, {})
    params = list(item.get("parameters") or [])
    params += list((item.get(method.lower()) or {}).get("parameters") or [])
    return {p["$ref"] for p in params if isinstance(p, dict) and "$ref" in p}


def main() -> int:
    real, docs = load_contracts()
    targets, unresolved = scope(real)

    if "--list" in sys.argv:
        for op in sorted(targets):
            v = targets[op]
            print("%-32s %-6s %-52s field=%s web=%s"
                  % (op[0], op[2], op[1][:52],
                     "·".join(sorted(v["field"])), "·".join(sorted(v["web"]))))
        print("\n오퍼레이션 %d · 경로 %d · 화면 %d"
              % (len(targets), len({op[1] for op in targets}),
                 len(set().union(*(v["field"] for v in targets.values())))))
        return 0

    missing_param, wrong_grade, missing_component = [], [], []

    for op in sorted(targets):
        fname, path, method = op
        wants_optional = bool(targets[op]["web"])
        want = OPTIONAL_REF if wants_optional else REQUIRED_REF
        refs = declared_refs(docs[fname], path, method)
        if not (refs & {REQUIRED_REF, OPTIONAL_REF}):
            missing_param.append((op, want))
        elif want not in refs:
            wrong_grade.append((op, want, sorted(refs & {REQUIRED_REF, OPTIONAL_REF})))

    # 쓰는 파일은 그 파라미터를 정의해야 한다
    need = collections.defaultdict(set)
    for op in targets:
        need[op[0]].add(OPTIONAL_REF if targets[op]["web"] else REQUIRED_REF)
    for fname, refs in sorted(need.items()):
        defined = docs[fname].get("components", {}).get("parameters", {})
        for r in sorted(refs):
            if r.rsplit("/", 1)[-1] not in defined:
                missing_component.append((fname, r.rsplit("/", 1)[-1]))

    # 관리웹 «전용» 오퍼레이션이 귀속 헤더를 달았나 — 막지 않고 알린다
    stray = []
    for fname, doc in docs.items():
        for path, item in doc.get("paths", {}).items():
            for method in [m for m in item if m.lower() in HTTP_METHODS]:
                if method.lower() == "get":
                    continue
                op = (fname, path, method.upper())
                if op in targets:
                    continue
                if declared_refs(doc, path, method) & {REQUIRED_REF, OPTIONAL_REF}:
                    stray.append(op)

    total = len(targets)
    ok = total - len(missing_param) - len(wrong_grade)

    if missing_param:
        print("⛔ 귀속 헤더를 받을 자리가 없습니다 — %d건" % len(missing_param))
        for op, want in missing_param:
            print("   %-30s %-6s %-46s → %s"
                  % (op[0], op[2], op[1][:46], want.rsplit("/", 1)[-1]))
        print()
    if wrong_grade:
        print("⛔ 필수·선택 등급이 어긋납니다 — %d건" % len(wrong_grade))
        for op, want, got in wrong_grade:
            print("   %-30s %-6s %-40s 선언=%s → %s"
                  % (op[0], op[2], op[1][:40],
                     ",".join(r.rsplit("/", 1)[-1] for r in got),
                     want.rsplit("/", 1)[-1]))
        print()
    if missing_component:
        print("⛔ 파라미터 정의가 없습니다 — %d건" % len(missing_component))
        for fname, key in missing_component:
            print("   %-30s components.parameters.%s" % (fname, key))
        print()
    if stray:
        print("⚠ 현장·모바일이 부르지 않는 오퍼레이션에 귀속 헤더가 있습니다 — %d건"
              % len(stray))
        print("   (막지 않는다 — 요구서에 아직 안 적힌 화면일 수 있다)")
        for op in sorted(stray)[:12]:
            print("   %-30s %-6s %s" % (op[0], op[2], op[1][:46]))
        print()
    if unresolved:
        print("⚠ 계약에서 못 찾은 요구서 호출 — %d건 (이 검사기의 대상 밖)"
              % len(unresolved))
        for p, ids in sorted(unresolved.items())[:12]:
            print("   %-52s %s" % (p[:52], "·".join(sorted(ids))))
        print()

    if missing_param or wrong_grade or missing_component:
        print("실측 %d건 중 %d건 선언됨 — 기준: 요구서 §3 소절의 P-·M- 화면 쓰기 호출"
              % (total, ok))
        print("⚠ 이 수치는 하한이다 — 파일 첫머리 「안 보는 것」을 함께 읽는다")
        return 1

    print("✅ 현장 단말·모바일 쓰기 %d건 전부 귀속 사번을 받을 자리가 있습니다"
          % total)
    print("   경로 %d · 부르는 화면 %d · 계약 %d벌"
          % (len({op[1] for op in targets}),
             len(set().union(*(v["field"] for v in targets.values()))),
             len({op[0] for op in targets})))
    print("   필수 %d · 선택(관리웹 겸용) %d"
          % (sum(1 for v in targets.values() if not v["web"]),
             sum(1 for v in targets.values() if v["web"])))
    print("⚠ 이 수치는 하한이다 — 파일 첫머리 「안 보는 것」을 함께 읽는다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
