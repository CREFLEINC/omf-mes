#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""화면 하나를 «스펙 · 요구서 · 계약» 으로 잇는 진도표를 만든다.

⚠ 2026-09-03 개정 — 착수 통지 폐지로 «통지 열»을 걷었다
------------------------------------------------------
설계팀은 개발팀의 업무 진행에 **직접 정보를 보유하지 않는다**(업무 방식 개정
2026-09-03). 「착수 가능 통지」가 폐지됐으므로 **상대 저장소 조회도 함께 없앴다** —
남은 세 열(스펙 · 요구서 §3 · 계약)은 **설계팀 자신의 진행**이라 그대로 둔다.
⇒ 이제 이 표는 **로컬 정본만 읽는다.** 언제 돌려도 같은 값이 나오고,
   `--no-remote` 는 볼 것이 없어져 없앴다.

왜 필요한가
-----------
⛔ **화면 번호에서 상세 스펙 파일로 가는 길이 하나도 없었다.**

    grep -c '화면상세스펙' deliverables/04-통합-IA.md   →  0
    스펙 118장이 흩어진 폴더                          →  20

개발이 화면 하나의 스펙을 찾으려면 **날짜 폴더 스무 곳을 뒤져야** 했다. 통합 정보
구조 문서는 화면 번호만 적고 파일 경로를 안 적는다.

⭐ **개발 인수용 세트에서 이것이 빠지면 나머지가 아무리 정확해도 안 읽힌다.**

무엇을 잇나 — 세 축의 «차집합» 이 목적이다
-------------------------------------------
    화면 (통합 정보구조)  ↔  스펙 파일  ↔  요구서 §3 소절  ↔  계약

**구멍이 자동으로 뜬다** — 스펙이 없는 화면 · 요구서가 안 다룬 화면이 각각 목록으로
나온다. 손으로 세면 차수가 쌓일수록 틀린다.

⛔ 손으로 쓰지 않는다
---------------------
스펙이 새 차수 폴더로 늘 때마다 낡기 때문이다. 이 저장소에서 **손으로 쓴 수치는
예외 없이 낡았고 스크립트가 정본인 자리는 하나도 안 갈렸다.**

⚠ 이 생성기가 «안» 보는 것
--------------------------
- **스펙의 내용이 맞는지** — 파일이 있으면 있다고만 한다
- **요구서가 그 액션을 다 다뤘는지** — `verify-mapping-coverage.py` 몫이다
- **개발팀이 그 화면을 어디까지 만들었는지** — 우리 소관이 아니다(2026-09-03 개정)

쓰기
----
    python3 design/schema/generators/build-screen-progress.py
"""
from __future__ import annotations

import argparse
import glob
import importlib
import io
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "design", "wiki", "handover", "화면-진도표.md")
PROJECT_SPEC = os.path.join(ROOT, "design", "wiki", "project-spec")
API_CONTRACTS = os.path.join(ROOT, "design", "wiki", "api-contracts")
SCREENS_ROOT = os.path.join(ROOT, "design", "wiki", "screens")

sys.path.insert(0, HERE)
_INV = importlib.import_module("verify-screen-inventory")
# ⭐ 「폐지 확정 스펙인가」 판정은 **한 곳에만 둔다** — `collect-open-items.retired()`.
#    같은 판정을 두 곳에 적으면 그 순간 갈린다. 실제로 갈려 있었다(2026-09-03):
#    이 진도표는 정본 인벤토리로 117 을 세고, 미결·인계 대장은 스펙 «파일»로 118 을
#    세어 **인도물 두 장이 다른 수를 말했다.** 지금은 둘 다 같은 함수를 쓴다.
_OPEN = importlib.import_module("collect-open-items")

SCREEN = re.compile(r"([WMP]-(?:CO|\d{2})-\d{2})")
PROGRAM = {"W": "관리웹", "P": "POP", "M": "모바일"}
# 요구서 §3 소절 — 꾸밈이 붙어도 첫 백틱 화면 ID 를 집는다.
DOC_SECTION = re.compile(r"^### 3-\d+\.[^\n`]*`([WMP]-(?:CO|\d{2})-\d{2})`", re.M)
# 요구서 머리의 계약 파일.
DOC_CONTRACT = re.compile(r"openapi/([\w가-힣\-]+)\.json")


def read(path: str) -> str:
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def screens_with_names() -> list[tuple[str, str]]:
    """통합 정보구조의 화면 표에서 (ID, 이름) 을 순서대로 모은다."""
    text = read(os.path.join(PROJECT_SPEC, "04-통합-IA.md"))
    out: list[tuple[str, str]] = []
    for start, end in ((r"^## §3\. ", r"^## §4\. "),
                       (r"^## §4\. ", r"^## §5\. "),
                       (r"^## §5\. ", r"^## §6\. ")):
        for line in _INV.section(text, start, end).split("\n"):
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            found = SCREEN.findall(cells[0])
            if found:
                name = cells[1].strip("*` ") if len(cells) > 1 else ""
                out.append((found[0], name))
    return out


def spec_paths() -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    """화면 ID → 상세 스펙 파일 경로(저장소 상대). 여럿이면 여럿 그대로.

    ⛔ **폐지 확정 스펙은 «스펙이 있다»로 세지 않는다** — 파일은 남아 있어도 서 있는
       화면이 아니다. 판정은 `collect-open-items.retired()` 하나를 쓴다.
       조용히 지우지 않고 «뺀 것»을 같이 돌려준다(생성물 문면에 적는다).
    """
    out: dict[str, list[str]] = {}
    gone: list[tuple[str, str]] = []
    for path in sorted(glob.glob(os.path.join(SCREENS_ROOT, "*", "[WMP]-*.md"))):
        base = os.path.basename(path)
        m = SCREEN.match(base)
        if not m:
            continue
        rel = os.path.relpath(path, ROOT)
        if _OPEN.retired(read(path)):
            gone.append((m.group(1), rel))
            continue
        out.setdefault(m.group(1), []).append(rel)
    return out, gone


def doc_coverage() -> tuple[dict[str, str], dict[str, str]]:
    """화면 ID → (요구서 파일명, 계약 파일명). 요구서 §3 소절이 근거다."""
    docs: dict[str, str] = {}
    contracts: dict[str, str] = {}
    for path in sorted(glob.glob(os.path.join(API_CONTRACTS, "06-API-요구서*.md"))):
        text = read(path)
        name = os.path.basename(path)
        # 머리(§1 앞)에서만 계약 파일을 읽는다 — 본문의 인용까지 세면 남의 계약이 섞인다.
        head = text.split("## §1.")[0]
        found = [m + ".json" for m in dict.fromkeys(DOC_CONTRACT.findall(head))]
        for sid in DOC_SECTION.findall(text):
            docs[sid] = name
            if found:
                contracts[sid] = " · ".join(found)
    return docs, contracts


def render(rows, gaps, gone) -> str:
    counted = Counter(sid[0] for sid, *_ in rows)
    lines = [
        "# 화면 진도표 — 화면 하나를 스펙·요구서·계약으로 잇는다",
        "",
        "> ⛔ **생성물이다. 손으로 고치지 마라.** `python3 design/schema/generators/build-screen-progress.py` 가 다시 만든다.",
        ">",
        "> 이 표가 답하는 질문 = **「이 화면의 상세 스펙은 어느 파일인가」** 와 **「어디가 비어 있나」**.",
        "> 통합 정보구조 문서는 화면 번호만 적고 **파일 경로를 안 적어**, 스펙 %d장이 흩어진 폴더 스무 곳을 뒤져야 했다."
        % (len(rows) + len(gone)),
        ">",
        "> ⚠ **2026-09-03 개정 — 착수 통지 폐지로 「통지」 열을 걷었다.** 남은 세 열은 **설계팀 자신의 진행**이다.",
        "> 개발팀이 그 화면을 어디까지 만들었는지는 **우리가 갖는 정보가 아니다** — 개발팀이 이 자료를 직접 열람한다.",
        ">",
        "> ⭐ 이제 **로컬 정본만 읽는다** — 스펙·요구서를 고치지 않는 한 언제 돌려도 같은 값이 나온다.",
        "> 스펙이나 요구서를 고쳤으면 **그 자리에서 다시 만든다.**",
        "",
        "## 요약",
        "",
        "| 무엇 | 값 |",
        "| --- | :-: |",
        "| 화면 | **%d** (%s) " % (
            len(rows), " · ".join("%s %d" % (PROGRAM[k], counted[k]) for k in "WPM")) + "|",
        "| └ 폐지 확정으로 세지 않은 스펙 파일 | %d%s |" % (
            len(gone),
            (" — " + " · ".join("`%s`" % s for s, _ in gone)) if gone else ""),
        "| 상세 스펙이 있는 화면 | **%d** |" % (len(rows) - len(gaps["스펙"])),
        "| 요구서 §3 이 다룬 화면 | **%d** |" % (len(rows) - len(gaps["요구서"])),
        "",
    ]

    if gone:
        lines += [
            "⛔ **폐지 확정 스펙은 「스펙이 있다」로 세지 않는다** — 파일은 남아 있어도 **서 있는 화면이 아니다.**",
            "폐지가 확정돼도 문서를 지우지 않는 것은 **폐지 판단의 근거가 그 안에 있기** 때문이다.",
            "그래서 스펙 파일은 **%d벌**이고 화면은 **%d**이다. 판정은 `collect-open-items.retired()` 하나를 쓰므로"
            % (len(rows) + len(gone), len(rows)),
            "**미결 대장·인계 대장도 같은 수를 말한다**(전에는 이 표가 %d, 두 대장이 %d 로 갈려 있었다)."
            % (len(rows), len(rows) + len(gone)),
            "",
            "| 세지 않은 스펙 | 파일 |", "| --- | --- |",
        ]
        lines += ["| `%s` | `%s` |" % (sid, rel) for sid, rel in gone]
        lines += [""]

    for label, ids in (("스펙", gaps["스펙"]), ("요구서", gaps["요구서"])):
        head = {"스펙": "⛔ 상세 스펙이 없는 화면",
                "요구서": "⛔ 요구서 §3 이 다루지 않은 화면"}[label]
        lines += ["### %s — %d건" % (head, len(ids)), ""]
        lines += ["없다." if not ids else " · ".join("`%s`" % s for s in ids), ""]

    lines += ["---", "", "## 전건", "",
              "| 화면 | 이름 | 프로그램 | 상세 스펙 | 요구서 §3 | 계약 |",
              "| --- | --- | :-: | --- | --- | --- |"]
    for sid, name, specs, doc, contract in rows:
        spec_cell = "<br>".join("`%s`" % p for p in specs) if specs else "⛔ **없다**"
        lines.append("| `%s` | %s | %s | %s | %s | %s |" % (
            sid, name, PROGRAM[sid[0]], spec_cell,
            "`%s`" % doc if doc else "⛔ **없다**",
            "`%s`" % contract if contract else "—"))
    lines += ["", "---", "",
              "⚠ **이 표가 안 보는 것** — 스펙의 «내용» 이 맞는지 · 요구서가 그 액션을 다 다뤘는지"
              "(`verify-mapping-coverage.py` 몫) · **개발팀의 진행 상태**(우리 소관이 아니다).", ""]
    return "\n".join(lines)


def main() -> int:
    # ⛔ `--no-remote`·`--stamp` 는 없앴다(2026-09-03) — 상대 저장소를 조회하던 통지
    #    열이 사라져 「조회 시점」이라는 것이 없다. 이 표는 로컬 정본만 읽는다.
    argparse.ArgumentParser(add_help=True).parse_args()

    names = screens_with_names()
    specs, gone = spec_paths()
    docs, contracts = doc_coverage()

    rows = []
    gaps = {"스펙": [], "요구서": []}
    for sid, name in names:
        s = specs.get(sid, [])
        d = docs.get(sid, "")
        rows.append((sid, name, s, d, contracts.get(sid, "")))
        if not s:
            gaps["스펙"].append(sid)
        if not d:
            gaps["요구서"].append(sid)

    io.open(OUT, "w", encoding="utf-8").write(render(rows, gaps, gone))
    print("생성: %s" % os.path.relpath(OUT, ROOT))
    print("화면 %d (폐지 스펙 제외 %d) · 스펙 없음 %d · 요구서 없음 %d" % (
        len(rows), len(gone), len(gaps["스펙"]), len(gaps["요구서"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
