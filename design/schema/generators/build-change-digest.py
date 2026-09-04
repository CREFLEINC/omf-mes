#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""변경 요약 — 「설계가 무엇이 언제 바뀌었나」를 한자리에 모은다.

왜 필요한가
-----------
2026-09-03 업무 방식 개정(사용자 확정)으로 **설계팀은 개발팀의 업무에 관여하지 않는다.**
설계팀이 하는 것은 「**무엇이 언제 바뀌었는지만 핵심 요약해서 전달**」이고, 개발팀은
**설계 자료를 직접 열람**해 내용을 확인하고 처리 방식도 스스로 정한다.

⛔ 그런데 그 「무엇이 언제」를 볼 자리가 없었다 — 변경 이력이 화면 스펙 118벌·계약 7벌·
요구서 9벌·공유계약에 **흩어져 있어**, 열람하려 해도 **어디를 봐야 하는지** 알 수 없었다.

⭐ 정본을 새로 만들지 않는다 — **git 이력이 정본**이다
--------------------------------------------------------
이 저장소의 커밋 제목은 이미 요약의 형태다(「분류: 제목 — 부제 (#PR)」). 손으로 요약을
다시 쓰면 **두 벌이 되고 한쪽이 낡는다**(이 저장소가 여러 번 겪은 뿌리). 그래서 이
생성기는 **git 이력을 읽어 옮길 뿐** 아무것도 판단하지 않는다.

무엇을 보나
-----------
`design/wiki` 와 `design/schema` 를 건드린 커밋 전건. 커밋마다 —

  · 날짜 · 제목(그대로) · PR 번호
  · **어디를 보나** — 바뀐 파일을 사람이 읽는 이름으로(화면 ID · 계약 · 요구서 …)

⚠ 무엇을 «안» 보나
-------------------
- **왜 바뀌었는지** — 커밋 본문에 있다. 이 표는 «어디를 볼지»까지만 안내한다.
- **바뀐 내용이 맞는지** — 이력을 옮길 뿐 판정하지 않는다.
- `design/raw/`·`.claude/` — 설계 산출물이 아니다(전자는 시점 고착 자료, 후자는 하네스).
- `design/wiki/progress/` 만 건드린 커밋 — 생성물 갱신이라 «설계»가 바뀐 회차가 아니다.
  ⭐ 이 표 자신도 거기 있어, 빼지 않으면 「표를 갱신한 커밋」이 다음 회차에 또 한 행이 된다.

⭐ V3(2026-09-03) — 이 표는 설계팀 «내부» 이력이다
--------------------------------------------------
개발팀에 「무엇이 바뀌었나」를 알리는 창구는 **설계 변동 공지**(`.claude/skills/design-change-notice/`)
하나다 — 직전 공지(git tag `notice/*`)와 HEAD 사이의 «달라진 지점»을 개발팀 저장소에 이슈로 낸다.
이 표는 그 공지를 만들 때 `where()` 를 빌려 주고, 설계팀이 자기 이력을 되짚을 때 읽는다.

쓰기
----
    python3 design/schema/generators/build-change-digest.py
    python3 design/schema/generators/build-change-digest.py --limit 30   최근 30건만
"""
from __future__ import annotations

import argparse
import collections
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..", "..")
OUT = os.path.join(ROOT, "design", "wiki", "progress", "변경-요약.md")
WATCH = ["design/wiki", "design/schema"]
SELF_DIR = "design/wiki/progress/"   # 생성물 자리 — 이 표 자신을 포함한다

SCREEN = re.compile(r"([WMP]-(?:CO|\d{2})-\d{2})")
PR = re.compile(r"\(#(\d+)\)\s*$")


def run(args: list[str]) -> str:
    """git 을 부른다. ⭐ quotepath=false 라야 한글 경로가 그대로 온다."""
    return subprocess.run(["git", "-c", "core.quotepath=false"] + args,
                          cwd=os.path.join(HERE, "..", "..", ".."),
                          capture_output=True, text=True, check=True).stdout


def where(paths: list[str]) -> str:
    """바뀐 파일들 → 「어디를 보나」 한 줄. 사람이 읽는 이름으로 묶는다."""
    screens, buckets = [], collections.OrderedDict()

    def add(k, v=None):
        buckets.setdefault(k, set())
        if v:
            buckets[k].add(v)

    ours = 0          # ⭐ 설계팀 «내부» 파일 — 개발팀이 읽을 것이 아니다
    for p in paths:
        base = os.path.basename(p)
        # ⛔ 배포본(.html)은 세지 않는다 — 원본 .md 가 정본이고 둘이 같은 변경이다
        if base.endswith(".html"):
            continue
        if "/screens/" in p:
            m = SCREEN.search(base)
            if m:
                screens.append(m.group(1))
            continue
        if "/openapi/" in p and p.endswith(".json"):
            add("계약", base.replace(".json", "").split("-", 1)[-1])
        elif base.startswith("06-API-요구서"):
            add("요구서", base.replace("06-API-요구서", "").replace(".md", "").lstrip("-") or "본편")
        elif base == "공유계약.md":
            add("공유계약")
        elif base == "code-dictionary.md":
            add("코드 사전")
        elif "/project-spec/" in p or "/requirements/" in p:
            add("사양서·요구사항")
        else:
            # 검사기·생성기 · 진행 관리 문서 · 작성 규약 … — 설계팀이 자기 일을
            # 하려고 두는 것이라 개발팀의 열람 대상이 아니다. 수만 알린다.
            ours += 1

    out = []
    if screens:
        uniq = sorted(set(screens))
        head = " · ".join("`%s`" % s for s in uniq[:6])
        if len(uniq) > 6:
            head += " 외 %d" % (len(uniq) - 6)
        out.append("화면 " + head)
    for k, v in buckets.items():
        out.append(("%s(%s)" % (k, "·".join(sorted(v)))) if v else k)
    if not out:
        # 개발팀이 볼 산출물이 하나도 안 바뀐 회차다(검사기·규약만 손댔다)
        return "— *(설계팀 내부 %d)*" % ours if ours else "—"
    if ours:
        out.append("*(내부 %d)*" % ours)
    return " · ".join(out)


def commits(limit: int | None) -> list[dict]:
    sep = "\x1f"
    fmt = sep.join(["%H", "%ad", "%s"])
    args = ["log", "--date=short", "--format=" + fmt, "--no-merges"]
    if limit:
        args += ["-%d" % limit]
    args += ["--"] + WATCH
    rows = []
    for line in run(args).splitlines():
        if not line.strip():
            continue
        sha, date, subject = line.split(sep, 2)
        files = [f for f in run(["show", "--name-only", "--format=", sha,
                                 "--"] + WATCH).splitlines() if f.strip()]
        # ⛔ 자기 출력을 세지 않는다 — progress/ 는 생성물이라 「이 표를 갱신한 커밋」이
        # 다음 회차에 또 한 행이 되어 표가 영원히 수렴하지 않았다(2026-09-03 실측 93→94).
        files = [f for f in files if not f.startswith(SELF_DIR)]
        if not files:
            continue
        m = PR.search(subject)
        rows.append({
            "sha": sha[:7],
            "date": date,
            "subject": PR.sub("", subject).strip(),
            "pr": m.group(1) if m else None,
            "where": where(files),
            "n": len(files),
        })
    return rows


def render(rows: list[dict]) -> str:
    by_date = collections.OrderedDict()
    for r in rows:
        by_date.setdefault(r["date"], []).append(r)

    L = [
        "# 변경 요약 — 설계가 무엇이 언제 바뀌었나",
        "",
        "> ⛔ **생성물이다. 손으로 고치지 마라.** "
        "`python3 design/schema/generators/build-change-digest.py` 가 다시 만든다.",
        ">",
        "> ⭐ **이 표는 「무엇이 언제」까지만 말한다.** 바뀐 «내용»은 「어디를 보나」가 "
        "가리키는 파일을 직접 읽는다 — 그것이 정본이다.",
        ">",
        "> ⭐ **정본은 git 이력이다.** 요약을 손으로 다시 쓰면 두 벌이 되고 한쪽이 낡는다.",
        "",
        "2026-09-03 업무 방식 개정(사용자 확정) — 설계팀은 개발팀의 업무에 관여하지 않는다.",
        "설계팀이 하는 것은 **「무엇이 언제 바뀌었는지」를 전하는 것**이고, 개발팀은 설계",
        "자료를 **직접 열람**해 내용을 확인하고 처리 방식도 스스로 정한다.",
        "",
        "⭐ V3(2026-09-03) — 개발팀에 알리는 창구는 **설계 변동 공지** 하나다(직전 공지 태그",
        "`notice/*` → HEAD 의 «달라진 지점»을 개발팀 저장소 이슈로). 이 표는 설계팀 **내부** 이력이다.",
        "",
        "| 무엇 | 값 |",
        "| --- | :-: |",
        "| 변경 회차 | **%d** |" % len(rows),
        "| 기간 | %s ~ %s |" % (rows[-1]["date"] if rows else "—",
                                rows[0]["date"] if rows else "—"),
        "",
        "---",
        "",
    ]
    for date, group in by_date.items():
        L.append("## %s" % date)
        L.append("")
        L.append("| 무엇이 바뀌었나 | 어디를 보나 | PR |")
        L.append("| --- | --- | :-: |")
        for r in group:
            pr = ("#%s" % r["pr"]) if r["pr"] else "`%s`" % r["sha"]
            L.append("| %s | %s | %s |" % (r["subject"], r["where"], pr))
        L.append("")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="최근 N 회차만")
    args = ap.parse_args()

    rows = commits(args.limit)
    if not rows:
        print("⛔ 변경 회차가 없다 — git 이력을 못 읽었다")
        return 1
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(render(rows))
    print("생성: %s" % os.path.relpath(OUT, os.path.join(HERE, "..", "..", "..")))
    print("변경 회차 %d · %s ~ %s" % (len(rows), rows[-1]["date"], rows[0]["date"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
