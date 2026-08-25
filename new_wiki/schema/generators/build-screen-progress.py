#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""화면 하나를 «스펙 · 요구서 · 계약 · 통지» 로 잇는 진도표를 만든다.

왜 필요한가
-----------
⛔ **화면 번호에서 상세 스펙 파일로 가는 길이 하나도 없었다.**

    grep -c '화면상세스펙' deliverables/04-통합-IA.md   →  0
    스펙 118장이 흩어진 폴더                          →  20

개발이 화면 하나의 스펙을 찾으려면 **날짜 폴더 스무 곳을 뒤져야** 했다. 통합 정보
구조 문서는 화면 번호만 적고 파일 경로를 안 적는다.

⭐ **개발 인수용 세트에서 이것이 빠지면 나머지가 아무리 정확해도 안 읽힌다.**

무엇을 잇나 — 네 축의 «차집합» 이 목적이다
-------------------------------------------
    화면 (통합 정보구조)  ↔  스펙 파일  ↔  요구서 §3 소절  ↔  계약  ↔  착수 통지

**구멍이 자동으로 뜬다** — 스펙이 없는 화면 · 요구서가 안 다룬 화면 · 통지가 안 나간
화면이 각각 목록으로 나온다. 손으로 세면 차수가 쌓일수록 틀린다.

⛔ 손으로 쓰지 않는다
---------------------
스펙이 새 차수 폴더로 늘 때마다 낡기 때문이다. 이 저장소에서 **손으로 쓴 수치는
예외 없이 낡았고 스크립트가 정본인 자리는 하나도 안 갈렸다.**

⚠ 통지 열만 «조회 시점 값» 이다
-------------------------------
나머지 넷은 로컬 정본에서 뽑아 언제 돌려도 같다. **통지는 상대 저장소가 정본**이라
돌리는 시점에 따라 달라진다 — 그래서 표 머리에 **조회 시각**을 함께 적는다.
`--no-remote` 를 주면 조회하지 않고 그 사실을 적는다.

⚠ 이 생성기가 «안» 보는 것
--------------------------
- **스펙의 내용이 맞는지** — 파일이 있으면 있다고만 한다
- **요구서가 그 액션을 다 다뤘는지** — `verify-mapping-coverage.py` 몫이다
- **통지 본문이 최신인지** — 발행 여부만 본다

쓰기
----
    python3 new_wiki/schema/generators/build-screen-progress.py
    python3 new_wiki/schema/generators/build-screen-progress.py --no-remote
"""
from __future__ import annotations

import argparse
import glob
import importlib
import io
import json
import os
import re
import subprocess
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "new_wiki", "wiki", "handover", "화면-진도표.md")
PROJECT_SPEC = os.path.join(ROOT, "new_wiki", "wiki", "project-spec")
API_CONTRACTS = os.path.join(ROOT, "new_wiki", "wiki", "api-contracts")
SCREENS_ROOT = os.path.join(ROOT, "new_wiki", "wiki", "screens")
REPO = "CREFLEINC/omf-mes-client"

sys.path.insert(0, HERE)
_INV = importlib.import_module("verify-screen-inventory")

SCREEN = re.compile(r"([WMP]-(?:CO|\d{2})-\d{2})")
PROGRAM = {"W": "관리웹", "P": "POP", "M": "모바일"}
# 요구서 §3 소절 — 꾸밈이 붙어도 첫 백틱 화면 ID 를 집는다.
DOC_SECTION = re.compile(r"^### 3-\d+\.[^\n`]*`([WMP]-(?:CO|\d{2})-\d{2})`", re.M)
# 요구서 머리의 계약 파일.
DOC_CONTRACT = re.compile(r"openapi/([\w가-힣\-]+)\.json")
ISSUE_LINE = re.compile(r"^\s*#(\d+)\s+\S+(?:\s\S+)?\s+([WMP]-(?:CO|\d{2})-\d{2})\s")


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


def spec_paths() -> dict[str, list[str]]:
    """화면 ID → 상세 스펙 파일 경로(저장소 상대). 여럿이면 여럿 그대로."""
    out: dict[str, list[str]] = {}
    for path in sorted(glob.glob(os.path.join(SCREENS_ROOT, "*", "[WMP]-*.md"))):
        base = os.path.basename(path)
        m = SCREEN.match(base)
        if m:
            out.setdefault(m.group(1), []).append(os.path.relpath(path, ROOT))
    return out


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


def issued(no_remote: bool) -> tuple[dict[str, str], str]:
    """화면 ID → 통지 이슈 번호. 조회 못 하면 빈 표와 사유를 돌려준다."""
    if no_remote:
        return {}, "조회하지 않음(--no-remote)"
    script = os.path.join(ROOT, ".claude", "skills", "uiux-client-handoff",
                          "scripts", "check-issue.py")
    if not os.path.exists(script):
        return {}, "조회 스크립트를 찾지 못함"
    try:
        r = subprocess.run([sys.executable, script, "--status"],
                           capture_output=True, text=True, cwd=ROOT, timeout=120)
    except Exception as exc:                       # noqa: BLE001
        return {}, "조회 실패 — %s" % type(exc).__name__
    if r.returncode != 0 and not r.stdout.strip():
        return {}, "조회 실패"
    out: dict[str, str] = {}
    for line in r.stdout.split("\n"):
        m = ISSUE_LINE.match(line)
        if m:
            out.setdefault(m.group(2), "#" + m.group(1))
    return out, "" if out else "조회 결과 0건"


def render(rows, gaps, note, stamp) -> str:
    counted = Counter(sid[0] for sid, *_ in rows)
    lines = [
        "# 화면 진도표 — 화면 하나를 스펙·요구서·계약·통지로 잇는다",
        "",
        "> ⛔ **생성물이다. 손으로 고치지 마라.** `python3 new_wiki/schema/generators/build-screen-progress.py` 가 다시 만든다.",
        ">",
        "> 이 표가 답하는 질문 = **「이 화면의 상세 스펙은 어느 파일인가」** 와 **「어디가 비어 있나」**.",
        "> 통합 정보구조 문서는 화면 번호만 적고 **파일 경로를 안 적어**, 스펙 118장이 흩어진 폴더 스무 곳을 뒤져야 했다.",
        ">",
        "> ⚠ **「재생성 무변경」 검사 대상이 아니다** — 통지 열이 상대 저장소 조회 값이라 돌릴 때마다 달라질 수 있다.",
        "> 스펙이나 요구서를 고쳤으면 **그 자리에서 다시 만든다.**",
        "",
        "## 요약",
        "",
        "| 무엇 | 값 |",
        "| --- | :-: |",
        "| 화면 | **%d** (%s) " % (
            len(rows), " · ".join("%s %d" % (PROGRAM[k], counted[k]) for k in "WPM")) + "|",
        "| 상세 스펙이 있는 화면 | **%d** |" % (len(rows) - len(gaps["스펙"])),
        "| 요구서 §3 이 다룬 화면 | **%d** |" % (len(rows) - len(gaps["요구서"])),
        "| 착수 통지가 나간 화면 | %s |" % (
            "조회 못 함" if note else "**%d**" % (len(rows) - len(gaps["통지"]))),
        "",
        "⚠ **통지 열만 조회 시점 값이다** — 나머지는 로컬 정본에서 뽑아 언제 돌려도 같다.",
        "> 조회: %s" % (note or stamp),
        "",
    ]

    for label, ids in (("스펙", gaps["스펙"]), ("요구서", gaps["요구서"]),
                       ("통지", gaps["통지"])):
        if label == "통지" and note:
            continue
        head = {"스펙": "⛔ 상세 스펙이 없는 화면",
                "요구서": "⛔ 요구서 §3 이 다루지 않은 화면",
                "통지": "⚠ 착수 통지가 아직 안 나간 화면"}[label]
        lines += ["### %s — %d건" % (head, len(ids)), ""]
        lines += ["없다." if not ids else " · ".join("`%s`" % s for s in ids), ""]

    lines += ["---", "", "## 전건", "",
              "| 화면 | 이름 | 프로그램 | 상세 스펙 | 요구서 §3 | 계약 | 통지 |",
              "| --- | --- | :-: | --- | --- | --- | :-: |"]
    for sid, name, specs, doc, contract, issue in rows:
        spec_cell = "<br>".join("`%s`" % p for p in specs) if specs else "⛔ **없다**"
        lines.append("| `%s` | %s | %s | %s | %s | %s | %s |" % (
            sid, name, PROGRAM[sid[0]], spec_cell,
            "`%s`" % doc if doc else "⛔ **없다**",
            "`%s`" % contract if contract else "—",
            issue or ("—" if note else "⚠ 미발행")))
    lines += ["", "---", "",
              "⚠ **이 표가 안 보는 것** — 스펙의 «내용» 이 맞는지 · 요구서가 그 액션을 다 다뤘는지"
              "(`verify-mapping-coverage.py` 몫) · 통지 본문이 최신인지.", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--no-remote", action="store_true", help="착수 통지를 조회하지 않는다")
    ap.add_argument("--stamp", default="", help="조회 시각 표기(생략하면 「방금」)")
    args = ap.parse_args()

    names = screens_with_names()
    specs = spec_paths()
    docs, contracts = doc_coverage()
    issues, note = issued(args.no_remote)

    rows = []
    gaps = {"스펙": [], "요구서": [], "통지": []}
    for sid, name in names:
        s = specs.get(sid, [])
        d = docs.get(sid, "")
        i = issues.get(sid, "")
        rows.append((sid, name, s, d, contracts.get(sid, ""), i))
        if not s:
            gaps["스펙"].append(sid)
        if not d:
            gaps["요구서"].append(sid)
        if not i:
            gaps["통지"].append(sid)

    stamp = args.stamp or "이 파일을 다시 만든 시점"
    io.open(OUT, "w", encoding="utf-8").write(render(rows, gaps, note, stamp))
    print("생성: %s" % os.path.relpath(OUT, ROOT))
    print("화면 %d · 스펙 없음 %d · 요구서 없음 %d · 통지 %s" % (
        len(rows), len(gaps["스펙"]), len(gaps["요구서"]),
        note or "미발행 %d" % len(gaps["통지"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
