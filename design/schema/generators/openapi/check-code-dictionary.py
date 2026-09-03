#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""코드 사전(`design/schema/code-dictionary.md`)이 계약과 맞는가 — **시험판**.

왜 필요한가
-----------
한 코드 값이 저장소 100곳 안팎에 흩어져 있고, 그중 **판단이 적히는 자리는 산문**이라
아무도 안 본다. 사전은 그 판단(소유·자리·근거)을 표로 꺼내 «기계가 셀 수 있게» 한다.

⛔ 그런데 사전이 «또 하나의 사본»이 되면 문제가 재생산된다 — 지금 등록부가 정확히
   그 상태다(공유계약 조항 3,079자 한 줄 + `check-code-group-pointer.py` 의 REGISTRY
   상수, 손으로 동기화). **그래서 이 검사기가 사전을 «읽고» 계약과 대조한다.**

무엇을 보나
-----------
① 사전이 적은 «자리 수»가 계약 실물과 같은가
   ⚠ 소유 값 넷 — enum · registry · registry-system · derived.
     registry-system 은 「설계가 정한 값을 마스터에 싣는다」이고 계약에서는
     registry 와 같이 포인터다. 갈리는 곳은 W-06-06 편집 가부다(미결 9).
② 사전이 `enum` 이라 한 키가 정말 계약에 값 목록을 갖는가
③ 사전이 `registry` 라 한 키가 정말 `codeGroupCode=` 포인터를 갖는가
④ ⭐ **형제 자리가 갈리지 않았는가** — 같은 이름이 어떤 자리에는 값이 있고 어떤
   자리에는 «맨몸»이면 그 맨몸을 보는 사람은 「값 목록이 없다」로 읽는다.
   ⚠ 이것을 보는 검사기가 지금 «없다» — check-code-group-pointer 는 가리킨 이름이
   등록부 안인가만, check-code-group-reachable 은 화면이 닿는가만 본다.
⑤ ⭐ **키(`x-code-key`)가 사전과 맞는가** — 2026-09-02 신설. 아래 ⑤절 참조.

⑤ 값 대조에서 «키 대조»로 (2026-09-02)
---------------------------------------
⛔ 값집합으로 자리를 찾으면 **값이 우연히 같은 다른 코드를 못 가른다.** 실물이
   있다 — `CD-PICKING-TYPE`(`MATERIAL`·`SHIPMENT`)과 `CD-RESERVATION-TYPE`
   (`MATERIAL`·`SHIPMENT`·`PRODUCTION`)은 앞의 둘이 겹친다. 값으로 세는 한
   「이 자리가 어느 키인가」는 **검사기가 답할 수 없는 물음**이었다.

⇒ 계약이 `*Code` 자리에 `x-code-key: "CD-…"` 를 «직접» 적는다(2026-09-02).
   ⭐ 값은 문자열 «또는 배열»이다 — 한 자리가 두 «계열»을 함께 받는 경우가 있다
   (`equipment_type_code` = 설비 계열 ＋ 계측기 계열 · `omf-mes#219`).
   스키마 프로퍼티는 프로퍼티 객체 안에, 쿼리 파라미터는 파라미터 객체 안에 둔다.
   그러면 판정이 **자리 자신이 말하는 것**이 되고 검사기는 대조만 한다.

| 규칙 | 무엇 | 게이트 |
| :-: | --- | :-: |
| ㉠ | `x-code-key` 가 사전에 **없는 키** | ⛔ 막는다 |
| ㉡ | 키는 있는데 그 자리의 `enum` 값집합이 **사전의 값과 다르다** | ⛔ 막는다 |
| ㉢ | 키는 있는데 그 자리의 `codeGroupCode=` 포인터가 **사전의 그룹과 다르다** | ⛔ 막는다 |
| ㉣ | 착지한(`x-source-column` 있는) `*Code` 자리에 **키가 없다** | ⚠ 계수만 |
| ㉤ | 사전이 **소유 = `enum`** 이라 적었는데 그 자리에 `enum` 이 **없다** | ⛔ 막는다 |
| ㉥ | 사전이 **소유 = `registry*`** 라 적었는데 계약이 `enum` 으로 **닫았다** | ⛔ 막는다 |
| ㉦ | 그 자리의 `example` 이 **사전 값집합 밖**이다 | ⛔ 막는다 |
| ㉧ | 산문이 「값 목록이 아직 없다」인데 **사전은 값을 갖는다** | ⛔ 막는다 |
| ㉨ | `*Code(s)` 자리에 **판정이 «전혀» 없다**(키도 `x-no-code-key` 도) | ⛔ 막는다 |
| ⑦ | 사전 머리말이 **자기 계수를 틀리게** 적었다 | ⛔ 막는다 |

⭐ **㉦㉧㉨⑦ 은 2026-09-03 신설.** ㉡ 는 `enum` 만 봤는데 값을 «나르는» 자리는 셋이다 —
`enum` · `example` · 산문. 뒤 둘은 아무도 안 보고 있었다(실측 83자리가 낡아 있었다).
⭐ **㉨ 는 ㉣ 의 사각지대를 없앤다** — ㉣ 는 «착지»를 문턱으로 삼아, 경로 안에 인라인으로
정의된 스키마와 배열 `items` 안의 자리를 **아예 안 봤다.** 「639/639 = 100%」로 보고한
그 분모가 바로 그 자리들을 빼고 낸 수였고, 실제로 9자리가 판정 없이 남아 있었다.

⭐ **㉤㉥ 는 2026-09-03 신설** — 소유는 「값이 어디 사나」를 말한다. `enum` 이면 값이
계약 안에 살아 생성 타입의 유니온으로 가고, `registry*` 면 공통코드 마스터에 살아
표시명(`nameKo`·`nameVi`)·정렬(`displayOrder`)과 함께 온다. 어긋나면 사전이 「계약이
닫는다」고 말하는데 그 자리는 열려 있거나, 마스터의 값을 계약이 또 갖는다(**두 벌**).
⛔ **어느 검사기도 이것을 안 보고 있었다** — ㉡ 는 `enum` 이 «있을 때만» 값을 비교하고
없다는 사실 자체는 안 본다. 그래서 소유가 `enum` 인 키를 자리에 붙이면서 `enum` 배열을
빠뜨려도 전부 초록이었다(실측 11자리 · `omf-mes#400` 3회차에서 7자리를 그렇게 냈다).

⭐ ㉣ 에서 빠지는 자리 — `x-no-code-key: "<이유>"` 가 적힌 자리. 인스턴스 식별자
(마스터 «한 건»을 가리키는 코드)와 표준값(ISO 국가·IANA 시간대)이 그것이다.
⛔ **이유 없이 빼는 길은 없다.**

⭐ **㉠㉢ 셋만 막는 이유** — 이 셋은 「이미 붙인 키가 «틀렸다»」이고, 틀린 키는
   고치는 데 다른 결정이 필요 없다. 반면 ㉣ 는 「아직 안 붙였다」이고 기준선이
   크다(2026-09-02 실측 109). 게이트로 걸면 초록을 기준선으로 쓸 수 없다.

⛔ **㉣ 는 래칫도 아닌 «단순 계수»다.** `check-code-group-reachable.py` 는 같은
   자리에서 래칫(`BASELINE`)을 쓰지만, ㉣ 는 **지금 여러 손이 동시에 줄이는 중인
   수**라 래칫을 걸면 서로 방해한다 — 한쪽이 줄여 기준선을 낮추면 다른 쪽의
   작업 트리가 곧바로 ⛔ 가 된다. 줄어드는 것이 확실한 수는 세기만 한다.

⚠ 이 검사기가 못 보는 것
------------------------
- **키가 «맞는지»는 안 본다.** 계약이 「이 자리는 이 키」라 적은 것을 믿는다 —
  ⑤ 는 그 선언이 사전과 어긋나지 않는가만 본다. 「이 자리에 이 코드가 맞나」는
  사람이 `A-16` 으로 판정한다.
- **④ 의 두 갈래를 못 가른다** — (a) 같은 코드인데 값이 빠졌다 / (b) 원래 다른
  코드인데 이름이 같다. **그 구분이 곧 사전이 할 일**이고, 사전에 없는 이름은
  일단 (?) 로 낸다. ⭐ 키가 붙은 자리에서는 ⑤ 가 이 구분을 대신한다.
- **물리 모델·프론트·서버 시드는 안 본다.** 우리 계약 7벌만 본다.

쓰기
----
    python3 design/schema/generators/openapi/check-code-dictionary.py
    python3 design/schema/generators/openapi/check-code-dictionary.py --split   # ④ 만

⛔ **⓪ 와 ⑤㉠㉡㉢ 을 막는다**(2026-09-02) — 등록부↔사전 1:1 · 소유 일치 ·
그룹이 등록부 안 · 키가 사전과 어긋나지 않음.
계수 규칙(①②④㉣)은 여전히 막지 않는다 — 닫을 수 없는 수라 흐름만 본다.
옛 서술: ~~시험판이라 종료 코드는 언제나 0 이다.~~ 사전이 계약 527자리를
   다 덮고 ④ 가 0 이 되면 게이트로 올린다.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import defaultdict
import importlib

# ⭐ 등록부는 **읽어 온다** — 여기에 그룹 이름 목록을 다시 적으면 그 순간 셋째 사본이 되고,
#    그것이 정확히 이 사전이 고치려는 병이다(2026-09-02 이관). 파서는 저장소에 하나뿐이다.
_ptr = importlib.import_module("check-code-group-pointer")
load_registry = _ptr.load_registry
load_registry_owners = _ptr.load_registry_owners

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
DICT = os.path.join(ROOT, "design", "schema", "code-dictionary.md")
CONTRACTS = os.path.join(ROOT, "design", "wiki", "api-contracts", "openapi", "*.json")

POINTER = re.compile(r"codeGroupCode=([A-Z_]+)")
KEY = re.compile(r"^`(CD-[A-Z0-9-]+)`$")
CODE_NAME = re.compile(r"`([a-zA-Z]+Codes?)`")
VALUE = re.compile(r"`([A-Z][A-Z0-9_]+)`")     # 코드 문자열·그룹 이름은 SCREAMING 이다


# ── 사전 읽기 ─────────────────────────────────────────────────────────────

def read_dictionary(path: str) -> list[dict]:
    """사전 표를 읽는다. 「| 키 | 값 | 그룹 | 프로퍼티 | 소유 | 자리 | 근거 |」 표만 본다.

    ⭐ 값 열은 «언제나» 실제 코드 문자열이다. 그룹(codeGroupCode)은 따로 둔다 —
       한 열에 두 종류를 섞으면 읽는 사람이 헷갈리고, registry 갈래의 실제 값이
       «산문에만» 남는다(2026-09-02 사용자 지적으로 갈랐다).
    """
    rows: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.startswith("|"):
                continue
            cs = [c.strip() for c in line.strip().strip("|").split("|")]
            # ⛔ 열이 «정확히 일곱»인 표만 본다 — 같은 문서의 결과·설명 표가 첫 칸에
            #    같은 키를 다시 적어 사전 행으로 세어졌다(2026-09-02 · 10 → 13).
            if len(cs) != 7:
                continue
            m = KEY.match(cs[0])
            if not m:
                continue                      # 머리·구분선·다른 표
            rows.append({
                "key": m.group(1),
                # ⭐ 값 — «언제나» 실제 코드 문자열이다. 그룹 이름은 따로 둔다.
                #    ⛔ 첫 판은 enum 갈래만 코드 문자열이고 registry 갈래는 그룹 이름이라
                #    한 열에 두 종류가 섞였고, registry 쪽 실제 값이 «산문에만» 남았다.
                "values": VALUE.findall(cs[1]),
                "group": VALUE.findall(cs[2]),
                "names": CODE_NAME.findall(cs[3]),
                "owner": cs[4].strip("`"),
                "places": int(cs[5]) if cs[5].isdigit() else None,
                "basis": cs[6],
            })
    return rows


# ── 계약 훑기 ─────────────────────────────────────────────────────────────

def state(node: dict, desc: str | None) -> str:
    """이 자리가 값 목록을 갖는가 — enum · ptr · bare."""
    src = node.get("items") or node
    if src.get("enum"):
        return "enum"
    if POINTER.search(desc or ""):
        return "ptr"
    return "bare"


def scan() -> dict[str, list[tuple]]:
    """계약 7벌의 *Code(s) 자리를 이름별로 모은다.

    반환 — 이름 -> [(계약, 자리종류, 경로, 상태, enum튜플, 포인터튜플, 키, 착지)]

    ⭐ 뒤 두 칸은 2026-09-02 «키 대조»로 넘어오며 붙였다 —
       `키`   = 그 자리에 적힌 `x-code-key`(없으면 None)
       `착지` = 그 자리에 `x-source-column` 이 있는가(물리 컬럼에 내려앉았는가).
    ⚠ 칸을 «뒤에» 붙인 것은 뜻이 있다 — 앞 여섯 칸을 읽던 자리(split_siblings ·
       기존 테스트)가 그대로 돈다. 튜플을 앞에서 늘리면 그 전부를 같이 고쳐야 한다.
    """
    out: dict[str, list[tuple]] = defaultdict(list)
    for path in sorted(glob.glob(CONTRACTS)):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        name = os.path.basename(path).replace(".json", "")

        def walk(node, where):
            if isinstance(node, dict):
                for k, v in node.items():
                    # ⛔ 스키마 «이름»이 Code 로 끝나는 object 는 코드 «자리»가 아니다 —
                    #    `ItemExternalCode`·`DefectCode`·`CauseCode` 셋이 그렇다.
                    #    2026-09-03 까지 이 셋이 「판정 없는 자리」로 세어졌다.
                    if (k.endswith("Code") or k.endswith("Codes")) and \
                            isinstance(v, dict) and ("type" in v or "enum" in v) \
                            and v.get("type") != "object":
                        src = v.get("items") or v
                        out[k].append((name, "스키마", where + "/" + k,
                                       state(v, v.get("description")),
                                       tuple(src.get("enum") or ()),
                                       tuple(POINTER.findall(v.get("description") or "")),
                                       v.get("x-code-key"),
                                       "x-source-column" in v,
                                       v.get("x-no-code-key")))
                    if k == "name" and isinstance(v, str) and \
                            (v.endswith("Code") or v.endswith("Codes")) and "schema" in node:
                        sc = node.get("schema") or {}
                        # ⭐ 쿼리는 키가 «파라미터 객체» 안에 있다 — 스키마 안이 아니다.
                        #    파라미터에는 물리 컬럼이 없으므로 착지는 언제나 거짓이다.
                        # ⚠ 배열 파라미터는 enum 이 items 안에 산다 — 스키마 쪽과 같게 본다.
                        qsrc = sc.get("items") or sc
                        # ⛔ 아홉째 칸(`x-no-code-key`)을 «반드시» 함께 넣는다 —
                        #    2026-09-03 까지 쿼리 갈래만 여덟 칸이라 `place_excused`
                        #    가 늘 None 을 냈다. 「코드 아님」으로 이유를 적어 둔
                        #    쿼리 파라미터 19자리가 «판정 없음»으로 보였다.
                        out[v].append((name, "쿼리", where,
                                       state(sc, node.get("description")),
                                       tuple(qsrc.get("enum") or ()),
                                       tuple(POINTER.findall(node.get("description") or "")),
                                       node.get("x-code-key"),
                                       False,
                                       node.get("x-no-code-key")))
                    walk(v, where + "/" + str(k))
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    walk(v, where + "/%d" % i)

        walk(doc, "")
    return out


# ── ⑤ 키 대조 ─────────────────────────────────────────────────────────────
#
# ⭐ 아래 넷은 «순수 함수»다 — 파일을 읽지 않는다. 테스트가 지어낸 자리·사전으로
#    부를 수 있어야 ㉠㉡㉢ 이 실제로 ⛔ 를 내는지 잠글 수 있다.

def place_key(place: tuple):
    """이 자리에 적힌 `x-code-key`. 옛 여섯 칸 튜플이면 None 이다.

    ⭐ 문자열 «또는 배열»이다(2026-09-02 확장). 한 자리가 두 «계열»을 함께 받는 경우가
    실재한다 — `mdm.equipment.equipment_type_code` 는 설비 계열과 계측기 계열 둘 다에서
    값이 온다(`G-32` · `omf-mes#219`). 1:1 을 전제하면 그 자리는 «영영» 키를 못 갖는다.
    """
    return place[6] if len(place) > 6 else None


def key_list(key) -> list:
    """키를 언제나 목록으로 — 문자열 하나든 배열이든."""
    if key is None:
        return []
    return list(key) if isinstance(key, (list, tuple)) else [key]


def place_landed(place: tuple) -> bool:
    """이 자리가 물리 컬럼에 «착지»했는가(`x-source-column`)."""
    return bool(place[7]) if len(place) > 7 else False


def key_sites(found: dict[str, list[tuple]]) -> list[tuple]:
    """키가 붙은 자리만 뽑는다 — (이름, 계약, 자리종류, 경로, enum, 포인터, 키)."""
    out = []
    for name, places in found.items():
        for p in places:
            key = place_key(p)
            if key:
                out.append((name, p[0], p[1], p[2], p[4], p[5], key))
    # ⚠ 키가 «배열»일 수 있어 그대로 정렬하면 list < str 로 터진다 — 문자열로 눕힌다.
    return sorted(out, key=lambda x: (" + ".join(key_list(x[6])), x[1], x[3]))


def check_keys(sites: list[tuple], entries: list[dict]) -> tuple[list, list, list]:
    """㉠㉡㉢ — 계약이 선언한 키를 사전과 대조한다. 셋 다 ⛔ 다.

    반환 — (㉠ 사전에 없는 키, ㉡ 값집합 어긋남, ㉢ 그룹 포인터 어긋남)

    ⭐ 왜 셋을 막나 — 전부 「이미 붙인 키가 «틀렸다»」이기 때문이다. 틀린 키는
       맞는 자리를 가리키는 척하면서 값·그룹을 남의 것으로 읽게 만든다. 고치는 데
       다른 결정이 필요 없으므로 기준선을 둘 이유가 없다.
    ⚠ 사전의 값 열이 비어 있으면(⬜ 로 세어서 남긴 키) ㉡ 를 건너뛴다 — 대조할
       것이 없는 자리를 ⛔ 로 내면 「값을 모른다」가 「키가 틀렸다」로 둔갑한다.
    """
    by_key = {e["key"]: e for e in entries}
    unknown: list = []
    enum_gap: list = []
    ptr_gap: list = []
    for name, f, kind, path, enum, ptr, key in sites:
        keys = key_list(key)
        es = [by_key.get(k) for k in keys]
        if any(e is None for e in es):
            unknown.append((name, f, kind, path,
                            " + ".join(k for k, e in zip(keys, es) if e is None)))
            continue
        # ⭐ 키가 여럿이면 «합집합» 으로 본다 — 「이 자리는 이 키들 중 하나다」이므로
        #    값도 그룹도 그 합이 그 자리가 받을 수 있는 전부다.
        shown = " + ".join(keys)
        if enum:
            want = set().union(*(set(e["values"]) for e in es))
            got = {x for x in enum if x is not None}   # nullable 자리는 None 이 섞인다
            if want and want != got:
                enum_gap.append((name, f, kind, path, shown, sorted(want), sorted(got)))
        if ptr:
            want_g = set().union(*(set(e["group"]) for e in es))
            got_g = set(ptr)
            if want_g != got_g:
                ptr_gap.append((name, f, kind, path, shown,
                                sorted(want_g), sorted(got_g)))
    return unknown, enum_gap, ptr_gap


def check_owner_shape(sites: list[tuple], entries: list[dict]) -> tuple[list, list]:
    """㉤㉥ — 사전이 적은 «소유» 와 그 자리의 «모양» 이 맞는가. 둘 다 ⛔ 다.

    반환 — (㉤ 소유가 enum 인데 자리에 enum 이 없다, ㉥ 소유가 registry* 인데 enum 이 있다)

    ⭐ 왜 막나 — 소유는 「값이 어디 사나」를 말한다.
       `enum`      → 값이 «계약 안»에 산다. 프론트는 생성 타입의 유니온으로 받는다.
       `registry*` → 값이 «공통코드 마스터»에 산다. `GET /mdm/code-values` 로 받고
                     표시명(nameKo·nameVi)·정렬(displayOrder)이 함께 온다.
       어긋나면 사전이 「계약이 닫는다」고 말하는데 그 자리는 열려 있거나, 반대로
       마스터에 사는 값을 계약이 또 갖는다 — «두 벌» 이 된다(L-2-1).
    ⛔ 어느 검사기도 이것을 안 보고 있었다(2026-09-03 신설) — ㉡ 는 enum 이 «있을 때만»
       값을 비교하지, 없다는 사실 자체는 안 본다. 그래서 소유가 enum 인 키에 자리를
       붙이면서 enum 배열을 빠뜨려도 전부 초록이었다.
    ⚠ 값 열이 비어 있는 키(⬜)는 ㉤ 를 건너뛴다 — 넣을 값이 없는데 요구할 수 없다.
    """
    by_key = {e["key"]: e for e in entries}
    missing: list = []
    surplus: list = []
    for name, f, kind, path, enum, _ptr, key in sites:
        es = [by_key.get(k) for k in key_list(key)]
        if any(e is None for e in es):
            continue                      # ㉠ 가 이미 잡는다
        owners = {e["owner"] for e in es}
        if owners == {"enum"}:
            if not enum and any(e["values"] for e in es):
                missing.append((name, f, kind, path, " + ".join(key_list(key))))
        elif owners and owners <= {"registry", "registry-system"}:
            if enum:
                surplus.append((name, f, kind, path, " + ".join(key_list(key)),
                                sorted(x for x in enum if x is not None)))
    return missing, surplus


def place_excused(place: tuple):
    """이 자리가 「코드 그룹이 아니다」로 «명시»됐는가 — `x-no-code-key` 의 이유."""
    return place[8] if len(place) > 8 else None


def keyless_landed(found: dict[str, list[tuple]]) -> list[tuple]:
    """㉣ — 착지했는데 키가 «없는» 자리. ⚠ 막지 않는다, 센다.

    ⭐ 착지(`x-source-column`)를 문턱으로 삼는 이유 — 물리 컬럼이 정해진 자리는
       「어느 코드인가」가 이미 판정된 자리다. 아직 착지 안 한 자리에 키를 요구하면
       판정 전에 이름을 붙이라는 말이 된다.
    """
    out = []
    for name, places in found.items():
        for p in places:
            if place_landed(p) and not place_key(p) and not place_excused(p):
                # ⛔ `x-no-code-key` 로 «이유를 적어» 뺀 자리는 세지 않는다.
                #    이유 없이 빼는 길은 없다 — 빈 문자열도 이유가 아니다.
                out.append((name, p[0], p[1], p[2]))
    return sorted(out)


def undecided(found: dict[str, list[tuple]]) -> list[tuple]:
    """㉨ — 판정이 «전혀» 없는 자리. ⛔ 게이트다(0 이어야 한다).

    ⭐ ㉣ 와 무엇이 다른가 — ㉣ 는 «착지(`x-source-column`)»를 문턱으로 삼는다.
       사전을 채워 가는 동안에는 그 문턱이 옳았다(판정 전에 이름을 붙이라는 말이
       되지 않게). **사전이 닫힌 지금은 문턱이 곧 사각지대다.**

    ⛔ 2026-09-03 실측이 그것을 드러냈다 — 「639/639 = 100%」로 보고한 그 분모가
       **경로 안에 «인라인»으로 정의된 스키마와 배열 `items` 안의 자리를 아예 세지
       않았다.** 그 자리 9곳이 판정 없이 남아 있었고, 그중 첨부 등록(POST) 본문의
       `targetTypeCode` 는 **읽는 쪽이 값·근거를 다 갖는데 쓰는 쪽만 맨몸**이었다.
       프론트가 «보내는» 자리에 아무 안내가 없었다는 뜻이다.

    ⭐ 이 저장소가 같은 뿌리를 다섯 번째 겪었다 — `B-6`(부여·회수 9테이블) ·
       `A-10`(16쌍) · `#198`(28그룹) · 사전 머리말(⑦) · 그리고 이 분모.
       **실측 «결과»를 규칙의 «범위»로 쓰면 모델이 자라는 동안 조항이 조용히 좁아진다.**
       그래서 이 축은 «모양»으로 적는다 — 어디에 있든 `*Code(s)` 자리면 판정을 요구한다.
    """
    out = []
    for name, places in found.items():
        for p in places:
            if not place_key(p) and not place_excused(p):
                out.append((name, p[0], p[1], p[2]))
    return sorted(out)


def matches(e: dict, place: tuple) -> bool:
    """이 자리가 이 사전 행의 것인가 — ③ 「사전이 «키로» 자리를 센다」.

    ⭐ 키가 붙었으면 **키로만** 판정한다. 값집합이 우연히 같아도 키가 다르면
       남의 자리다 — `CD-PICKING-TYPE`(MATERIAL·SHIPMENT)과
       `CD-RESERVATION-TYPE`(MATERIAL·SHIPMENT·PRODUCTION)이 실물이다.
    ⚠ 키가 «아직» 안 붙은 자리는 옛 방식(값집합·그룹)으로 짚는다 — 부착이
       진행될수록 그 갈래가 줄고 계수가 정확해진다.
    """
    key = place_key(place)
    if key:
        return key == e["key"]
    enum, ptr = place[4], place[5]
    if e["owner"] == "enum":
        return bool(enum) and set(e["values"]) == {x for x in enum if x is not None}
    # registry 갈래는 «그룹 이름»으로 자리를 찾는다 — 값은 계약에 없고 서버 마스터에
    # 있기 때문이다. 값 열은 사람이 읽고 나중에 서버 시드와 대조할 근거다.
    return bool(ptr) and bool(set(e["group"]) & set(ptr))


# ── ④ 형제 자리가 갈렸는가 ────────────────────────────────────────────────

def split_siblings(found: dict[str, list[tuple]]) -> list[tuple]:
    """같은 계약 안에서 같은 이름이 「값 있음」과 「맨몸」으로 갈린 자리.

    ⛔ **「코드가 아니다」로 이미 판정한 자리는 맨몸으로 세지 않는다**(2026-09-03).
       `x-no-code-key` 가 붙은 자리는 값 목록이 없는 것이 «정상»이다 — 그것을 갈린
       형제로 세면 ④ 가 「고칠 것」을 말하는 수인지 「판정된 것」을 말하는 수인지
       뜻을 잃는다. 실측 — 57자리 중 **27이 그런 자리**였고 전부 `statusCode` 였다
       (`HandlingUnit` 「전표가 아니라 물건이다」 · `InventoryReservation` 「수량 축이
       담고 이 칸을 움직이는 오퍼레이션이 없다(A-21)」 · `Asn` 「ERP 수신본이라 이 칸을
       올릴 주체가 없다」 — **이유까지 계약에 적혀 있었다**).
    ⚠ 자리 튜플을 «앞 네 칸»과 «맨 끝 칸»(x-no-code-key)만 읽는다.
    """
    out = []
    for name, places in found.items():
        by_file = defaultdict(list)
        for p in places:
            f, kind, path, st = p[0], p[1], p[2], p[3]
            if len(p) > 8 and p[8]:          # ⛔ 「코드 아님」 판정이 붙은 자리
                continue
            by_file[f].append((kind, path, st))
        for f, ps in by_file.items():
            sts = {s for _, _, s in ps}
            if "bare" in sts and (sts - {"bare"}):
                bare = [(k, p) for k, p, s in ps if s == "bare"]
                has = [s for _, _, s in ps if s != "bare"]
                out.append((name, f, bare, has[0], len(ps)))
    return sorted(out, key=lambda x: -len(x[2]))


# ── ㉦㉧ 계약의 «예시·산문» 이 사전과 같은 말을 하는가 ──────────────────
#
# ⭐ ㉡ 는 계약의 `enum` 만 사전과 대조한다. 그런데 값을 «나르는» 자리는 셋이다 —
#    `enum` · `example` · `description` 산문. 뒤 둘은 아무도 안 보고 있었다.
#
# ⛔ 2026-09-03 실측 — 사전이 닫힌(639/639) 뒤에도 계약 **83자리**가 낡아 있었다:
#      ㉦ `example` 이 사전 값집합 «밖»  52자리
#         (자리채움 `"값"` 25 · `"STANDARD"` 14 · `"NORMAL"` 3 + 진짜 오값 10)
#      ㉧ 산문이 「확정된 값 목록이 아직 없다」인데 사전은 값을 갖는다  31자리
#
# ⭐ 이것이 왜 무거운가 — `check-example-placeholder.py` 의 머리말이 이미 답했다.
#    「설비 상태 칸의 `example` 이 `"ACTIVE"` 였고, 구현팀은 그 값을 보고 코드를
#    만들었다. **시험은 전부 통과했다** — 계약이 그 값을 확정한 적이 없었는데도.」
#    `description` 은 `openapi-typescript` 가 JSDoc 으로 옮기고 `example` 도 생성
#    타입·목 서버에 그대로 실린다. **설명이 맞아도 예시가 틀리면 아무도 못 잡는다.**
#
# ⚠ 그 검사기와 이 축은 «다른 것»을 본다 — 그쪽은 자기 안에 «손으로 베낀» 확정값
#    표를 들고 있고(자기 머리말이 「조항이 바뀌면 이 표도 손으로 따라가야 한다」고
#    적었다) 게이트가 아니다. 이 축은 **코드 사전을 정본으로 읽는다.**

STALE_PROSE = re.compile(r"확정된 값 목록이 아직 없다|값 목록이 아직 확정|"
                         r"값 목록이 확정되지 않|값 목록 미확정|값 목록 미정")


def prose_example_gaps(doc: dict, values_by_key: dict) -> tuple[list, list]:
    """한 계약 문서 → (㉦ example 이 밖인 자리, ㉧ 산문이 낡은 자리).

    순수 함수다 — 파일을 읽지 않는다. `values_by_key` 는 {사전 키: 값 집합}.
    ⭐ 한 자리가 «키 둘»에 닿으면 값은 합집합으로 본다(`G-32` · `omf-mes#219`).
    """
    bad_example: list[tuple] = []
    stale_prose: list[tuple] = []

    def walk(node, where):
        if isinstance(node, dict):
            keys = key_list(node.get("x-code-key"))
            if keys:
                vals: set = set()
                for k in keys:
                    vals |= set(values_by_key.get(k) or ())
                if vals:
                    ex = node.get("example")
                    if isinstance(ex, str) and ex not in vals:
                        bad_example.append((where, " + ".join(sorted(keys)), ex))
                    if STALE_PROSE.search(node.get("description") or ""):
                        stale_prose.append((where, " + ".join(sorted(keys))))
            for k, v in node.items():
                walk(v, where + "/" + str(k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, where + "/%d" % i)

    walk(doc, "")
    return bad_example, stale_prose


# ── ⑦ 사전이 «자기 계수»를 맞게 적었는가 ────────────────────────────────

# ⛔ 볼드 «안에 앞말이 붙은» 꼴을 놓치지 않는다 — `**완성 — 174키 / 491자리.**` 이
#    그렇게 빠져 있었다(2026-09-03. `\*\*(\d+)키` 는 `**` 바로 뒤 숫자만 봤다).
SELF_COUNT = [
    (re.compile(r"\*\*[^*\n]*?(\d+)키 / (\d+)자리"), ("키", "자리")),
    (re.compile(r"등록부 \*\*(\d+)그룹 전부\*\*"), ("그룹",)),
]


def self_count_gaps(text: str, facts: dict) -> list[str]:
    """머리말이 적은 수 ↔ 실물. 파일을 읽지 않는다 — 테스트가 이 함수를 부른다.

    ⭐ 왜 필요한가 — 실측 «결과»를 문면에 박으면 낡는다. 이 저장소가 같은 뿌리를
       네 번 겪었다: `B-6`(부여·회수 9테이블) · `A-10`(16쌍) · `#198`(28그룹) ·
       그리고 이 사전 자신(2026-09-03 — 머리말이 「103키 / 257자리 · 등록부 62그룹」에
       고착돼 실물 174 / 491 / 103 과 갈려 있었다. 「62그룹이 전부다」로 읽혔다).
    """
    gaps: list[str] = []
    for pattern, names in SELF_COUNT:
        for m in pattern.finditer(text):
            for i, name in enumerate(names):
                said = int(m.group(i + 1))
                if said != facts[name]:
                    gaps.append("%s — 문면 %d · 실물 %d" % (name, said, facts[name]))
    return gaps


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", action="store_true", help="④ 형제 갈림만 낸다")
    args = ap.parse_args()

    entries = read_dictionary(DICT)
    found = scan()
    total = sum(len(v) for v in found.values())
    tagged = key_sites(found)

    print("코드 사전 검사 — 시험판")
    print("─" * 70)
    print("사전 %d 키 · 계약 *Code(s) 자리 %d · 그중 키(x-code-key)가 붙은 자리 %d (%d%%)"
          % (len(entries), total, len(tagged),
             round(len(tagged) * 100 / max(total, 1))))
    print()

    # ⓪ 사전이 가리킨 «그룹» 이 등록부 안인가 — 사전이 셋째 사본이 되지 않게 대조한다.
    gate: list[str] = []          # ⛔ 여기에 담긴 것만 종료 코드를 바꾼다
    registry = load_registry()
    outside = sorted({g for e in entries for g in e["group"]} - registry)
    if outside:
        gate.append("사전의 그룹이 등록부 밖 %d" % len(outside))
        print("⛔ 사전의 «그룹» 열이 등록부 밖입니다 %d건 — 공유계약 G-32 표에 없습니다"
              % len(outside))
        for g in outside:
            print("   %s" % g)
    else:
        print("⓪ 사전의 «그룹» 열 %d종 전부 등록부 안 (등록부 %d개)"
              % (len({g for e in entries for g in e["group"]}), len(registry)))

    # ⓪-a ⛔ **게이트** — 등록부에 이름이 올랐으면 사전에도 행이 있어야 한다.
    #     걸어 두지 않으면 새 그룹이 사전을 건너뛰고, 값은 다시 계약 산문으로 흩어진다.
    #     (2026-09-02 1단계로 62/62 가 초록이 된 뒤에 건다)
    covered = {g for e in entries for g in e["group"]}
    orphan = sorted(registry - covered)
    if orphan:
        gate.append("등록부에 있는데 사전에 없는 그룹 %d" % len(orphan))
        print()
        print("⛔ 등록부에 있는데 «사전에 없는» 그룹 %d건 — 값이 어디에도 안 적힌다"
              % len(orphan))
        for g in orphan:
            print("   %s" % g)
        print("   ⭐ 닫는 법 — design/schema/code-dictionary.md 에 행을 더한다.")
        print("      값을 모르면 ⬜ 로 «세어서» 남긴다 — 비워 두지 않는다.")

    # ⓪-b 소유가 «두 곳»에 적힌다 — 갈라지지 않게 기계가 맞춘다.
    #     사람이 맞추게 두면 등록부 이관 전의 병이 소유 축에서 그대로 재발한다.
    owners = load_registry_owners()
    clash = [(e["key"], g, e["owner"], owners[g])
             for e in entries for g in e["group"]
             if g in owners and owners[g] != "미판정" and e["owner"] != owners[g]]
    if clash:
        print()
        gate.append("사전↔등록부 소유 불일치 %d" % len(clash))
        print("⛔ 사전의 «소유» 가 등록부와 다릅니다 %d건 — 정본은 공유계약 G-32 표입니다"
              % len(clash))
        for key, g, mine, theirs in clash:
            print("   %-38s %-38s 사전 %-16s 등록부 %s" % (key, g, mine, theirs))
    print()

    # ⑤ ⛔ **게이트** — 계약이 «자리마다» 적은 키가 사전과 맞는가(2026-09-02 신설).
    #    값집합으로 찾던 것을 키로 바꾸는 자리다 — 값이 우연히 같은 다른 코드를
    #    값으로는 영영 못 가른다(CD-PICKING-TYPE ↔ CD-RESERVATION-TYPE).
    unknown, enum_gap, ptr_gap = check_keys(tagged, entries)
    if unknown:
        gate.append("사전에 없는 키 %d" % len(unknown))
        print("⛔ ㉠ 계약이 «사전에 없는» 키를 적었습니다 %d건 — 대조할 행이 없습니다"
              % len(unknown))
        for name, f, kind, path, key in unknown[:12]:
            print("   %-30s %-20s %-5s %s" % (key, f[:20], kind, name))
        if len(unknown) > 12:
            print("   … 그 밖 %d건" % (len(unknown) - 12))
        print("   ⭐ 닫는 법 — 사전에 행을 세우거나, 자리의 키를 맞는 것으로 고친다.")
    if enum_gap:
        gate.append("키의 값집합 어긋남 %d" % len(enum_gap))
        print("⛔ ㉡ 키는 맞는데 그 자리의 «값집합»이 사전과 다릅니다 %d건"
              % len(enum_gap))
        for name, f, kind, path, key, want, got in enum_gap[:8]:
            print("   %-30s %-20s %-5s %s" % (key, f[:20], kind, path[-42:]))
            print("        사전 %s" % " ".join(want))
            print("        계약 %s" % " ".join(got))
        if len(enum_gap) > 8:
            print("   … 그 밖 %d건" % (len(enum_gap) - 8))
        print("   ⭐ 두 갈래다 — (a) 계약이 값을 빠뜨렸다 → 채운다")
        print("                  (b) 원래 «다른 코드»다      → 키를 가른다")
    if ptr_gap:
        gate.append("키의 그룹 포인터 어긋남 %d" % len(ptr_gap))
        print("⛔ ㉢ 키는 맞는데 그 자리의 «codeGroupCode= 포인터»가 사전과 다릅니다 %d건"
              % len(ptr_gap))
        for name, f, kind, path, key, want, got in ptr_gap[:8]:
            print("   %-30s %-20s %-5s 사전 %s ← 계약 %s"
                  % (key, f[:20], kind, " ".join(want) or "—", " ".join(got) or "—"))
        if len(ptr_gap) > 8:
            print("   … 그 밖 %d건" % (len(ptr_gap) - 8))
    # ㉤㉥ ⛔ **게이트** — 소유와 자리의 «모양» 이 맞는가(2026-09-03 신설).
    shape_missing, shape_surplus = check_owner_shape(tagged, entries)
    if shape_missing:
        gate.append("소유 enum 인데 자리에 enum 없음 %d" % len(shape_missing))
        print("⛔ ㉤ 사전은 «소유 = enum»(계약이 값을 갖는다)이라 적었는데 "
              "그 자리에 enum 이 없습니다 %d건" % len(shape_missing))
        for name, f, kind, path, key in shape_missing[:10]:
            print("   %-38s %-20s %-5s %s" % (key, f[:20], kind, path[-40:]))
        if len(shape_missing) > 10:
            print("   … 그 밖 %d건" % (len(shape_missing) - 10))
        print("   ⭐ 두 갈래다 — (a) enum 을 넣는다(⛔ 변경 통지 대상 — 값이 좁아진다)")
        print("                  (b) 실은 공통코드다 → 사전의 소유를 registry* 로 고치고")
        print("                      산문에 codeGroupCode= 포인터를 적는다")
    if shape_surplus:
        gate.append("소유 registry 인데 enum 있음 %d" % len(shape_surplus))
        print("⛔ ㉥ 사전은 «소유 = registry*»(값이 공통코드 마스터에 산다)라 적었는데 "
              "계약이 enum 으로 닫았습니다 %d건" % len(shape_surplus))
        for name, f, kind, path, key, got in shape_surplus[:10]:
            print("   %-38s %-20s %-5s %s" % (key, f[:20], kind, path[-40:]))
            print("        계약 %s" % " ".join(got))
        if len(shape_surplus) > 10:
            print("   … 그 밖 %d건" % (len(shape_surplus) - 10))
        print("   ⭐ 값이 두 벌이 된다 — 고객이 마스터에 값을 더해도 계약이 막는다.")

    if not (unknown or enum_gap or ptr_gap or shape_missing or shape_surplus):
        print("⑤ ✅ 키가 붙은 %d자리 전부 사전과 맞다 — "
              "㉠ 미등록 0 · ㉡ 값 0 · ㉢ 그룹 0 · ㉤㉥ 소유 모양 0" % len(tagged))

    # ㉣ ⚠ **막지 않는다 — 센다.** 착지했는데 키가 없는 자리.
    #    래칫도 걸지 않는다: 지금 여러 손이 동시에 줄이는 수라 기준선을 두면
    #    한쪽이 줄이는 순간 다른 쪽 작업 트리가 ⛔ 가 되어 서로 방해한다.
    orphan_places = keyless_landed(found)
    by_name = defaultdict(int)
    for name, _f, _kind, _p in orphan_places:
        by_name[name] += 1
    print("㉣ ⚠ 착지(x-source-column)했는데 «키가 없는» 자리: %d — 이름 %d종"
          % (len(orphan_places), len(by_name)))
    for name, n in sorted(by_name.items(), key=lambda x: (-x[1], x[0]))[:8]:
        print("      %-30s %d" % (name, n))
    if len(by_name) > 8:
        print("      … 그 밖 %d종" % (len(by_name) - 8))
    print("   ⭐ 이 수는 «게이트가 아니다» — 줄어드는 중인 수라 세기만 한다.")
    print()

    if not args.split:
        bad = 0
        claimed = 0
        by_this_key = 0                # ③ 그중 «키로» 짚은 자리
        # ⭐ ③ 키가 붙은 자리는 «이름 열»을 거치지 않고 키로 바로 모은다(2026-09-02).
        #    이름 열은 사람이 손으로 적은 사본이라 자리 이름이 늘면 뒤처진다 —
        #    실제로 cycleTypeCode 자리 2개가 CD-CYCLE-TYPE 의 이름 열에 없었다.
        #    키는 계약 «자리 자신»이 말하는 것이라 뒤처질 데가 없다.
        tagged_by_key: dict[str, list] = defaultdict(list)
        for name, places in found.items():
            for p in places:
                # ⭐ 키가 배열이면 그 자리는 «키마다» 센다 — 두 계열을 함께 받는 자리다.
                for k in key_list(place_key(p)):
                    tagged_by_key[k].append((p[0], p[1], p[2], p[3], name))

        for e in entries:
            # ③ ⭐ 키로 짚은 자리가 «먼저»다 — 값집합이 우연히 같아도 남의 자리는 안 센다.
            got = [(f, kind, path, st)
                   for f, kind, path, st, _n in tagged_by_key.get(e["key"], [])]
            by_this_key += len(got)
            bare = []
            # ⛔ 「맨몸」은 «같은 계약 파일» 안에서만 센다(2026-09-02).
            #    statusCode 처럼 이름이 여러 코드에 공유되면 이름으로 세는 순간
            #    «남의 자리»를 삼킨다 — 실제로 맨몸 2 를 80 으로 셌다.
            hit_files = {f for f, _, _, _ in got}
            for n in e["names"]:
                for p in found.get(n, []):
                    if matches(e, p):
                        hit_files.add(p[0])
            for n in e["names"]:
                for p in found.get(n, []):
                    f, kind, path, st = p[0], p[1], p[2], p[3]
                    if place_key(p):
                        # ⭐ 키가 붙은 자리는 위에서 «키로» 이미 셌다 — 두 번 세지 않는다.
                        #    키가 남의 것이면 여기서도 안 센다. 그것이 키 대조의 뜻이다.
                        continue
                    # ⚠ 아직 키가 «안 붙은» 자리만 옛 방식(값·그룹)으로 짚는다.
                    # registry-system 은 registry 와 «계약에서는» 같다 — 포인터다.
                    # 다른 것은 W-06-06 에서 고객이 편집할 수 있는가뿐이고,
                    # 그것은 계약이 아니라 화면·마스터 소관이다(2026-09-02 신설).
                    if matches(e, p):
                        got.append((f, kind, path, st))
                    elif st == "bare" and f in hit_files:
                        # ⛔ 값도 포인터도 없는 «형제» 자리 — 단 이 키가 실제로 걸린
                        #    계약 파일 안에서만 센다. 다른 파일의 같은 이름은 남의 코드다.
                        bare.append((f, kind, path))
            claimed += len(got)
            want_n = e["places"]
            ok = want_n is None or want_n == len(got)
            mark = "✅" if ok else "⛔"
            if not ok:
                bad += 1
            n_key = len(tagged_by_key.get(e["key"], []))
            # ⭐ 두 방향을 가른다 — 「모자란다」와 「넘친다」는 고칠 곳이 다르다.
            #    모자람 = 계약이 비어 있다(맨몸 자리를 채운다)
            #    넘침   = 사전의 «자리» 수가 뒤처졌다(키가 붙으면서 드러난다)
            why = ""
            if not ok:
                why = ("← 맨몸 자리가 그만큼이다" if len(got) < (want_n or 0)
                       else "← 사전의 자리 수가 뒤처졌다(키가 %d자리를 짚는다)" % n_key)
            print("%s %-38s %-9s 사전 %-3s 값있음 %-3d (키 %-3d) 맨몸 %-3d %s"
                  % (mark, e["key"], e["owner"],
                     want_n if want_n is not None else "?", len(got), n_key, len(bare),
                     why))
            if not ok and len(got) < (want_n or 0):
                for f, kind, path in bare[:4]:
                    print("      ⛔ %-20s %-5s %s" % (f[:20], kind, path[-58:]))
            elif not ok:
                # ⭐ 넘칠 때는 «사전의 이름 열에 없는» 자리를 먼저 보인다 —
                #    키가 붙으면서 드러난 자리가 바로 그것이라 고칠 곳을 짚어 준다.
                extra = [x for x in tagged_by_key.get(e["key"], [])
                         if x[4] not in e["names"]]
                for f, kind, path, _st, n in (extra or
                                              tagged_by_key.get(e["key"], []))[:4]:
                    print("      ⚠ %-20s %-5s %-22s %s"
                          % (f[:20], kind, n[:22], path[-40:]))
        print()
        print("① 사전이 선언한 자리 수와 «어긋난» 키: %d" % bad)
        print("   ⭐ 모자라면 검사기 오류가 아니라 «계약이 비어 있다»는 뜻이다 —")
        print("      사전이 「여기도 이 코드다」라 선언해야 그 빈자리가 보인다.")
        print("   ⭐ 넘치면 «사전의 자리 수가 뒤처졌다»는 뜻이다 — 키가 붙으면서")
        print("      이름 열에 없던 자리가 드러난 것이고, 사전 쪽을 고친다.")
        print("② 사전이 짚어 낸 자리: %d / 계약 %d" % (claimed, total))
        print("③ 그중 «키로» 짚은 자리: %d — 나머지 %d 는 값·그룹으로 짚었다"
              % (by_this_key, claimed - by_this_key))
        print("   ⭐ 부착이 진행될수록 이 비율이 오르고 계수가 정확해진다 —")
        print("      값·그룹 매칭은 값집합이 우연히 같은 코드를 못 가른다.")
        print()

    splits = split_siblings(found)
    bare_total = sum(len(b) for _, _, b, _, _ in splits)
    q = sum(1 for _, _, b, _, _ in splits for k, _ in b if k == "쿼리")

    print("④ ⛔ 형제 자리가 갈린 코드: %d 종 · 맨몸 자리 %d (쿼리 %d · %d%%)"
          % (len(splits), bare_total, q, round(q * 100 / max(bare_total, 1))))
    print()
    known = {n for e in entries for n in e["names"]}
    for name, f, bare, has, tot in splits[:12]:
        tag = "사전에 있다" if name in known else "⚠ 사전 밖"
        print("   %-26s %-20s 맨몸 %2d / %2d  (%s → %s)"
              % (name, f[:20], len(bare), tot, has, tag))
    if len(splits) > 12:
        print("   … 그 밖 %d 종" % (len(splits) - 12))
    print()
    print("⚠ 이 수를 그대로 「고칠 것」으로 읽지 않는다 — 두 갈래다.")
    print("   (a) 같은 코드인데 어떤 자리만 값이 빠졌다  → 채운다")
    print("   (b) 원래 «다른 코드»인데 이름이 같다        → 키를 가른다")
    print("   ⭐ 그 구분이 곧 사전이 할 일이다.")
    print()
    # ⑦ ⛔ **게이트** — 사전이 «자기 자신에 대해» 적은 수가 실물과 맞는가.
    #    2026-09-03 실측 — 머리말이 「103키 / 257자리 · 등록부 62그룹」에 고착돼 있었다.
    #    실물은 174키 / 491자리 / 103그룹. 1차 완성 시점의 수가 «완성 선언»의 얼굴로
    #    남아, 읽는 사람에게 「62그룹이 전부다」로 읽혔다.
    #    ⭐ 같은 뿌리를 이 저장소가 세 번 겪었다 — `B-6`(부여·회수 9테이블) ·
    #    `A-10`(16쌍) · `#198`(28그룹). **실측 «결과»를 문면에 박으면 낡는다.**
    #    고치는 방향은 하나다 — 기계가 그 수를 다시 세게 한다.
    facts = {
        "키": len(entries),
        "자리": sum(e["places"] or 0 for e in entries),
        "그룹": len(registry),
    }
    with open(DICT, encoding="utf-8") as fh:
        head = fh.read()
    # ㉨ ⛔ **게이트** — 자리의 «모양»에 관계없이 판정이 있는가.
    #    인라인 스키마·배열 items 안의 자리도 «똑같이» 센다.
    nodec = undecided(found)
    if nodec:
        gate.append("판정이 전혀 없는 자리 %d" % len(nodec))
        print("⛔ ㉨ 판정(x-code-key · x-no-code-key)이 «전혀» 없는 자리 %d" % len(nodec))
        for row in nodec[:20]:
            print("   %-28s %-20s %-6s %s" % (row[0][:28], row[1][:20], row[2], row[3][:70]))
        print("   ⭐ 키를 붙이거나, 「코드 아님」이면 x-no-code-key 에 «이유»를 적는다.")
    else:
        print("㉨ ✅ 자리 %d 전부 판정이 있다 — 인라인 스키마·배열 items 까지 셌다"
              % sum(len(v) for v in found.values()))
    print()

    # ㉦㉧ ⛔ **게이트** — 계약의 예시·산문이 사전과 같은 말을 하는가.
    values_by_key = {e["key"]: set(e["values"]) for e in entries}
    bad_ex: list[tuple] = []
    old_prose: list[tuple] = []
    for cpath in sorted(glob.glob(CONTRACTS)):
        with open(cpath, encoding="utf-8") as fh:
            cdoc = json.load(fh)
        base = os.path.basename(cpath)
        ex, pr = prose_example_gaps(cdoc, values_by_key)
        bad_ex += [(base,) + t for t in ex]
        old_prose += [(base,) + t for t in pr]
    if bad_ex:
        gate.append("example 이 사전 값집합 밖 %d" % len(bad_ex))
        print("⛔ ㉦ `example` 이 사전 값집합 «밖»입니다 %d자리" % len(bad_ex))
        for row in bad_ex[:20]:
            print("   %-26s %s\n      키=%s  example=%s" % (row[0], row[1], row[2], row[3]))
        print("   ⭐ 생성 타입·목 서버에 그대로 실린다 — 틀린 예시는 설명을 읽지 않는 한 안 잡힌다.")
    else:
        print("㉦ ✅ `example` 이 전부 사전 값집합 안이다")
    if old_prose:
        gate.append("산문이 「값 목록이 아직 없다」 %d" % len(old_prose))
        print("⛔ ㉧ 산문이 「값 목록이 아직 없다」인데 사전은 값을 갖습니다 %d자리"
              % len(old_prose))
        for row in old_prose[:20]:
            print("   %-26s %s  (키=%s)" % row)
        print("   ⭐ 프론트는 그 문면을 보고 선택칸을 «비활성 + 사유»로 만든다(G-2).")
    else:
        print("㉧ ✅ 산문에 낡은 「값 목록이 아직 없다」가 없다")
    print()

    stale = self_count_gaps(head, facts)
    if stale:
        gate.append("사전 머리말 계수가 낡음 %d" % len(stale))
        print("⛔ ⑦ 사전이 자기 계수를 «틀리게» 적고 있습니다 %d건" % len(stale))
        for s in stale:
            print("   %s" % s)
        print("   ⭐ 문면을 실물에 맞춘다 — 실측 결과를 손으로 박아 두면 다시 낡는다.")
    else:
        print("⑦ ✅ 사전 머리말 계수가 실물과 같다 — %d키 / %d자리 / 등록부 %d그룹"
              % (facts["키"], facts["자리"], facts["그룹"]))
    print()

    if gate:
        print("⛔ 막는 규칙에 걸렸습니다 — %s" % " · ".join(gate))
        return 1
    print("⭐ 계수 규칙(①②③④㉣)은 «막지 않는다» — 흐름을 보는 수다.")
    print("   ⛔ 막는 것은 ⓪ · ⑤ · ㉨ · ㉦㉧ · ⑦ 이다 — 등록부↔사전 1:1 · 소유 일치 ·")
    print("      계약이 적은 키가 사전과 어긋나지 않는가(㉠㉡㉢) ·")
    print("      소유와 자리의 «모양» 이 맞는가(㉤㉥) ·")
    print("      «모든» 자리에 판정이 있는가 — 인라인·배열 items 포함(㉨) ·")
    print("      계약의 «예시·산문» 이 사전과 같은 말을 하는가(㉦㉧) ·")
    print("      사전이 «자기 계수»를 맞게 적었는가(⑦).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
