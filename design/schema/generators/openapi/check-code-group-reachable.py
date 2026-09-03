#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""계약이 가리킨 공통코드 그룹에 **화면이 닿을 수 있는가**.

왜 필요한가
-----------
계약(`description`)에 `codeGroupCode=…` 를 적는 것만으로는 **화면이 그 호출을
만들지 않는다.** 프론트가 읽는 것은 요구서 §3 액션표이고, 착수·변경 통지도
거기서 「이 화면이 부르는 경로」를 뽑는다. 계약에만 있고 요구서에 없는 그룹은
**통지가 나를 수 없다.**

⛔ 2026-09-01 에 그 형태가 실측으로 드러났다 — 초과 입하 분리(`W-01-03`)의
예외 유형은 계약에 포인터가 **2026-08-29 에 이미 실렸는데**(`#288`) 요구서
§3 은 그 자리를 「**API 불필요** — 요청 본문을 채우는 일」로 적어 두었다.
프론트는 요구서대로 만들었고, 화면은 오류 없이 **빈 선택칸**으로 섰다.
같은 형태가 8화면이었다. 어떤 검사기도 그것을 보지 않았다.

무엇을 보나 — ① 그룹 축(기존)
------------------------------
계약 7벌의 포인터 그룹 집합 ∖ 요구서 8벌에 적힌 그룹 집합.

⛔ 왜 «전부 초록»을 요구하지 않나
---------------------------------
기준선이 **33그룹**이다(2026-09-01). 이 회차의 어떤 반영으로도 닫히지 않는
수라, 게이트로 걸면 초록을 기준선으로 쓸 수 없게 된다. 대신 **래칫**으로 건다 —
늘면 ⛔, 줄면 「기준선을 낮추라」고 알린다. 새로 만드는 자리가 같은 구멍을
반복하는 것만은 막는다.

무엇을 보나 — ② 화면 축(2026-09-01 `omf-mes#336` 신설)
--------------------------------------------------------
①은 그룹 «단위»로만 센다 — 요구서 8벌 «어디든» 한 번 적히면 그 그룹은 초록이다.
그래서 **형제 화면이 빠져도 가려진다**: `GOODS_ISSUE_REASON` 은 공급사 반품
(`W-01-05`)·자재 폐기(`W-01-06`) 요구서 §3 에 적혀 있어 ①에서 이미 초록인데,
**같은 `logistics.goods_issue` 전표를 만드는 제품 폐기(`W-04-10`)는 빠져 있었다**
(`#336` 이 실측할 때까지 아무도 못 봤다).

이 축은 **물리 테이블을 다리로 삼아** 그 결손을 잡는다:

1. 계약 스키마의 `x-source-table`(물리 테이블)마다, 그 테이블의 스키마가 가리키는
   공통코드 그룹을 모은다 — `check-required-in-fieldtable.py` 의 판정과 같은 다리다.
2. 화면 스펙(`design/wiki/screens/**/*.md`)의 `§4-X. … `테이블`` 소절 제목으로
   「이 테이블을 쓰는 화면」을 모은다.
3. 한 테이블을 **둘 이상의 화면이 함께 쓰면**(형제가 있으면), 그 화면들의 요구서
   §3 소절 각각에 그 그룹의 `codeGroupCode=` 포인터가 있는지 하나씩 본다.
   **형제 하나라도 없으면** 그 화면·그룹 짝이 결손이다.

⚠ 형제가 없는(그 테이블을 쓰는 화면이 하나뿐인) 그룹은 이 축에서 «가려질» 대상이
없으므로 보지 않는다 — ①이 이미 그 자리를 본다.

⛔ 이 축도 «전부 초록»을 요구하지 않는다 — 같은 이유로 래칫이다(`BASELINE_SCREEN`).

⚠ 이 검사기가 못 보는 것
------------------------
  - 요구서에 적혔다고 «그 화면» 절에 적힌 것은 아니다 — ①은 문서 단위로만 센다
  - 화면이 실제로 그 호출을 구현했는지 — 이 저장소가 답할 수 있는 물음이 아니다
  - 그룹 이름이 등록부 안인지 — 그것은 `check-code-group-pointer.py` 가 본다
  - ②는 **§4 필드표에 테이블 이름을 backtick 소절 제목으로 적은 화면만** 본다 —
    아직 §4 를 안 쓴 화면은 «형제 없음»과 구분되지 않는다
  - ②는 그 테이블을 쓰는 스키마가 «필수»로 요구하는 그룹인지는 가르지 않는다 —
    선택 칸이라도 형제가 이미 부르면 결손으로 잡는다(선택 칸도 값 목록은 필요하다)

쓰기
----
    python3 design/schema/generators/openapi/check-code-group-reachable.py
"""
from __future__ import annotations

import collections
import glob
import importlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_cg = importlib.import_module("check-code-group-pointer")
_rift = importlib.import_module("check-required-in-fieldtable")

CONTRACTS = os.path.join(HERE, "..", "..", "..", "wiki", "api-contracts", "openapi")
REQUIREMENTS = os.path.join(HERE, "..", "..", "..", "wiki", "api-contracts")
SCREENS = os.path.join(HERE, "..", "..", "..", "wiki", "screens", "**", "*.md")

POINTER = re.compile(r"codeGroupCode=([A-Z][A-Z0-9_]*)")
DOC_SCREEN = re.compile(r"^### 3-\d+\.[^\n`]*`([WMP]-(?:CO|\d{2})-\d{2})`", re.M)
# 화면 절은 `###` 이다 — 같은 높이 이상의 다음 제목에서 끊는다.
ANY_HEADING = re.compile(r"^#{1,3}\s", re.M)

# 기준선 — 2026-09-03 실측(직전 2026-09-01 은 31 / 63). ⛔ 늘리지 않는다. 줄었으면 낮춘다.
#
# ⭐ 그룹 축 31 → 1 → **0** (2026-09-03 같은 날 두 번). 코드 사전이 닫히면서 30그룹의
#    표시명 호출을 요구서 §3 액션표에 실어 1 이 됐고, 남은 하나(`PROCESS_TYPE`)는
#    **요구서의 결손이 아니라 «화면의 부재»**였다 — 공정을 «등록»하는 화면이 없었다.
#    다른 화면들은 공정을 «선택 목록»으로 읽을 뿐이라 `GET /mdm/processes` 만 부르고
#    이 그룹의 값 목록은 필요 없다. 그래서 «행을 넣어» 닫지 않았다 — 넣으면 화면이
#    안 하는 호출을 한다고 적는 것이다.
#
# ✅ 그 화면이 섰다 — `W-06-01` 이 공정 마스터를 흡수했다(2026-09-03 사용자 확정 ·
#    최상위 탭 2개 《Routing》/《공정 마스터》). 계약에 CRUD 5오퍼레이션이 서고
#    요구서 §3-2 에 `codeGroupCode=PROCESS_TYPE` 행이 실리면서 **0 이 됐다.**
#    ⭐ 「행을 넣어 닫지 않는다」를 지킨 덕에, 닫힌 자리가 «진짜로» 닫혔다 —
#    화면이 실제로 그 호출을 한다.
#
# ⛔ 이제 0 이므로 이 축은 «전부 초록»을 요구한다. 새로 늘면 그것은 결손이다.
BASELINE = 0
#
# ⭐ 화면 축 58 → 21 (2026-09-03). 두 가지가 함께 일어났다:
#    ① `screen_sections()` 결함을 고치자 «가려져 있던» 결손 하나가 더 드러났다
#       (58 → 59). 파일 마지막 화면 절이 `len(text)` 까지 뻗어 꼬리 절
#       (「커버리지 집계」·「대상 유형 대응표」·「변경 이력」)을 통째로 삼켜,
#       그 안의 경로·그룹이 그 화면의 것으로 세어지고 있었다.
#    ② 그중 «그 칸을 화면이 실제로 §4 에 갖고 있는» 34자리에 표시명 호출을 실었다.
#
# ⚠ 남은 21 을 «전부 결손»으로 읽지 않는다 — **그 칸이 화면 §4 에 «없다».**
#    형제가 같은 테이블을 쓴다고 같은 칸을 보이는 것은 아니다. 예 — `W-04-08`(재고
#    조회)은 `trace.lot_hold` 를 쓰지만 «해제 사유»(`release_reason_code`)를 보이지
#    않는다. 그 화면에 그 호출을 적으면 **화면이 안 하는 일을 적는 것**이다.
#    ⇒ 닫으려면 먼저 「그 칸을 이 화면이 보여야 하는가」를 판정해야 한다 —
#    기계가 못 가르는 물음이라 래칫으로 둔다.
#
# ⭐ 21 → 20 (2026-09-03). `W-05-13`(툴·금형·지그 마스터)의 `CYCLE_TYPE` 이 닫혔다.
#    이 건은 «그 칸이 없어서»가 아니라 **한 행에 두 칸을 담아 다리가 안 이어져서**
#    안 보이던 자리다 — §4-A 가 「PM 날짜 주기 = 간격 + 단위」를 한 행에 적고
#    출처 컬럼을 안 적었다. 계약은 `pmCycleInterval`·`pmCycleUnitCode` 두 프로퍼티다.
#    ⇒ 행을 둘로 가르고 컬럼명을 적자 다리가 이어졌고, 그러자 **단위 값이
#    「일/월」 2값으로 낡아 있던 것**이 함께 드러났다(확정은 `CYCLE_TYPE` 4값 ·
#    계약은 2026-09-02 에 이미 고쳤는데 화면 표만 남아 있었다).
#    ⚠ 교훈 — «한 행에 두 칸»은 검사기의 사각지대다. 형제 자리가 같은 형태로
#    남아 있다(`W-05-11` §4-A 검교정 주기).
BASELINE_SCREEN = 20


def table_groups_from_doc(doc: dict) -> dict[str, set[str]]:
    """한 계약 문서 → {물리 테이블 이름: 그 테이블 스키마가 가리키는 공통코드 그룹}.

    순수 함수다 — 파일을 읽지 않는다(테스트가 고정 문서로 부른다).
    """
    out: dict[str, set[str]] = {}
    for _name, body in (doc.get("components", {}).get("schemas") or {}).items():
        if not isinstance(body, dict):
            continue
        table = body.get("x-source-table")
        if not table:
            continue
        groups = set()
        for _where, desc in _cg.descriptions(body):
            groups |= set(POINTER.findall(desc))
        if groups:
            out.setdefault(table, set()).update(groups)
    return out


def table_groups() -> dict[str, set[str]]:
    """계약 7벌 전건 → 물리 테이블 이름 → 그 테이블의 스키마가 가리키는 그룹."""
    out: dict[str, set[str]] = {}
    for f in sorted(glob.glob(os.path.join(CONTRACTS, "*.json"))):
        with open(f, encoding="utf-8") as fh:
            doc = json.load(fh)
        for table, groups in table_groups_from_doc(doc).items():
            out.setdefault(table, set()).update(groups)
    return out


def table_screens() -> dict[str, set[str]]:
    """물리 테이블 이름 → 그 테이블을 §4 소절 제목에 backtick 으로 적은 화면 집합."""
    out: dict[str, set[str]] = {}
    for path in sorted(glob.glob(SCREENS, recursive=True)):
        m = _rift.SCREEN_ID.match(os.path.basename(path))
        if not m:
            continue
        screen = m.group(1)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        for tables, _body in _rift.field_sections(text):
            for t in tables:
                out.setdefault(t, set()).add(screen)
    return out


def sections_from_text(text: str) -> dict[str, str]:
    """한 요구서 → {화면 ID: §3 소절 본문}. 파일을 읽지 않는다 — 테스트가 부른다.

    ⛔ 절의 «끝»을 다음 «화면» 절이 아니라 «다음 제목»으로 잡는다.
       2026-09-03 실측 — 파일 «마지막» 화면 절이 `len(text)` 까지 뻗어 꼬리 절
       (「커버리지 집계」·「대상 유형 대응표」·「변경 이력」)을 통째로 삼켰다.
       그 안의 경로·그룹이 그 화면의 것으로 세어져, 실제로는 안 부르는 화면이
       「부른다」로 초록이 됐다 — ②축 판정이 그만큼 헐거웠다(고치자 59로 늘었다).
    """
    out: dict[str, str] = collections.defaultdict(str)
    marks = [(m.group(1), m.start()) for m in DOC_SCREEN.finditer(text)]
    heads = [m.start() for m in ANY_HEADING.finditer(text)]
    for screen, start in marks:
        after = [h for h in heads if h > start]
        out[screen] += text[start:min(after) if after else len(text)]
    return out


def screen_sections() -> dict[str, str]:
    """화면 ID → 요구서 §3 소절 본문(전 요구서 병합)."""
    out: dict[str, str] = collections.defaultdict(str)
    for f in sorted(glob.glob(os.path.join(REQUIREMENTS, "06-API-요구서*.md"))):
        with open(f, encoding="utf-8") as fh:
            for screen, body in sections_from_text(fh.read()).items():
                out[screen] += body
    return out


def gaps_from(tg: dict[str, set[str]], ts: dict[str, set[str]],
              sections: dict[str, str]) -> list[tuple[str, str, str]]:
    """[(화면, 테이블, 그룹)] — 형제 화면은 그 그룹을 부르는데 이 화면은 안 부른다.

    순수 함수다 — 세 다리(테이블→그룹 · 테이블→화면 · 화면→요구서 본문)를 직접
    받는다. 테스트가 이 함수를 고정 다리로 부른다.
    """
    gaps: list[tuple[str, str, str]] = []
    for table, groups in tg.items():
        screens = ts.get(table, set())
        if len(screens) < 2:
            continue  # 형제가 없으면 «가려짐» 자체가 성립하지 않는다
        for screen in sorted(screens):
            have = set(POINTER.findall(sections.get(screen, "")))
            for group in sorted(groups):
                if group not in have:
                    gaps.append((screen, table, group))
    return gaps


def screen_axis_gaps() -> list[tuple[str, str, str]]:
    return gaps_from(table_groups(), table_screens(), screen_sections())


def main() -> int:
    sites: dict[str, list[str]] = collections.defaultdict(list)
    for f in sorted(glob.glob(os.path.join(CONTRACTS, "*.json"))):
        fname = os.path.basename(f)
        with open(f, encoding="utf-8") as fh:
            doc = json.load(fh)
        for where, desc in _cg.descriptions(doc):
            for name in POINTER.findall(desc):
                sites[name].append("%s :: %s" % (fname, where))

    in_req: set[str] = set()
    files = sorted(glob.glob(os.path.join(REQUIREMENTS, "06-API-요구서*.md")))
    for f in files:
        with open(f, encoding="utf-8") as fh:
            in_req |= set(POINTER.findall(fh.read()))

    gap = sorted(set(sites) - in_req)
    print("계약 포인터 그룹 %d · 요구서(%d벌)에 적힌 그룹 %d · 닿지 않는 그룹 **%d**"
          % (len(sites), len(files), len(in_req), len(gap)))

    if gap:
        print("\n⚠ 계약은 가리키는데 요구서가 한 번도 적지 않은 그룹 — **통지가 나를 수 없다**")
        for name in gap:
            print("   %-38s %s" % (name, sites[name][0]))
        print("\n   ⭐ 닫는 법 — 그 그룹을 쓰는 화면의 요구서 §3 액션표에")
        print("      `GET /mdm/code-values?codeGroupCode=<이름>` 행을 «추가»한다.")
        print("      ⛔ 「API 불필요」로 적지 않는다 — 선택칸의 값 목록은 API 호출이다.")

    failed = False
    if len(gap) > BASELINE:
        print("\n⛔ 기준선 %d 보다 %d 늘었다 — 새로 만든 자리가 같은 구멍을 반복했다."
              % (BASELINE, len(gap) - BASELINE))
        failed = True
    elif len(gap) < BASELINE:
        print("\n⭐ 기준선 %d → %d 로 줄었다. 이 파일의 `BASELINE` 을 %d 로 낮추세요."
              % (BASELINE, len(gap), len(gap)))
    else:
        print("\n✅ 기준선 %d 유지 — 늘지 않았다." % BASELINE)

    print("\n" + "─" * 60)
    screen_gaps = screen_axis_gaps()
    print("② 화면 축 — 테이블을 함께 쓰는 형제 화면 중 그룹을 안 부르는 화면 **%d**건"
          % len(screen_gaps))
    if screen_gaps:
        print("\n⚠ 형제는 이 그룹을 부르는데 이 화면은 안 부른다 — «가려진» 결손")
        for screen, table, group in screen_gaps:
            print("   %-10s %-32s %s" % (screen, table, group))
        print("\n   ⭐ 닫는 법 — 이 화면의 요구서 §3 액션표에 형제와 같은")
        print("      `GET /mdm/code-values?codeGroupCode=<이름>` 행을 «추가»한다.")

    if len(screen_gaps) > BASELINE_SCREEN:
        print("\n⛔ 화면 축 기준선 %d 보다 %d 늘었다 — 새로 만든 자리가 같은 구멍을 반복했다."
              % (BASELINE_SCREEN, len(screen_gaps) - BASELINE_SCREEN))
        failed = True
    elif len(screen_gaps) < BASELINE_SCREEN:
        print("\n⭐ 화면 축 기준선 %d → %d 로 줄었다. 이 파일의 `BASELINE_SCREEN` 을 %d 로 낮추세요."
              % (BASELINE_SCREEN, len(screen_gaps), len(screen_gaps)))
    else:
        print("\n✅ 화면 축 기준선 %d 유지 — 늘지 않았다." % BASELINE_SCREEN)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
