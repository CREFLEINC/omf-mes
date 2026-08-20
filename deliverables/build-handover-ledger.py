#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""인계 대장 — 「최종」인데 아직 안 정해진 것을 한자리에 모은다.

왜 필요한가
-----------
최종 인도물에 **「아직 안 정해진 것」의 자리가 없으면 그것이 조용히 사라진다.**
개발은 「다 정해졌다」로 읽고 만들고, 나중에 그 자리에서 멈춘다.

⭐ **동시에 반대쪽도 말한다** — 살아 있는 미결이 수백 행이어도 **차단 등급이 0** 이면
「전 화면 지금 지어도 된다」가 사실이다. 그 둘을 함께 보이지 않으면 숫자만 보고
겁먹거나, 숫자를 감추고 다 됐다고 말하게 된다.

⛔ 복사하지 않는다 — «합류» 시킨다
----------------------------------
네 정본이 이미 각자 답을 낸다. 이 대장은 **그 넷을 돌려 결과를 잇는다.**

    collect-open-items.py        화면 스펙 §8 미결
    count-undecided-codes.py     확정되지 않은 업무 코드
    verify-polymorphic-mapping.py  한 칸이 여러 표를 가리키는 자리의 대응표 결손
    build-screen-progress.py     화면 축의 구멍(스펙·요구서·통지)

**수치를 이 파일에 손으로 적지 않는다.** 원본이 바뀌면 복사본에는 갱신 의무가
아무에게도 없다 — 이 저장소에서 손으로 쓴 수치는 예외 없이 낡았다.

⚠ 이 대장이 «안» 보는 것
------------------------
- **미결의 내용이 맞는지** — 스펙이 틀렸으면 대장도 똑같이 틀린다
- **추적 표지가 가리키는 곳이 살아 있는지** — 닫힌 이슈를 가리켜도 모른다
- **고객·팀 리더 회신 대기** — 그것은 화면 스펙 §8 밖에 있다

쓰기
----
    python3 deliverables/build-handover-ledger.py
    python3 deliverables/build-handover-ledger.py --no-remote
"""
from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(HERE, "99-인계대장.md")


def run(script: str, *args: str) -> str:
    r = subprocess.run([sys.executable, os.path.join(HERE, script), *args],
                       capture_output=True, text=True, cwd=ROOT)
    return r.stdout


def read(path: str) -> str:
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def _plain(text: str) -> str:
    """굵게·코드 표기와 트리 기호를 벗긴다 — 이름을 «정확히» 맞추기 위해서다."""
    return text.replace("*", "").replace("`", "").lstrip("└├─ ").strip()


def summary_rows(text: str, keys: tuple[str, ...]) -> dict[str, str]:
    """생성물 요약 표에서 「| 이름 | 값 |」을 집어 온다.

    ⛔ 이름을 «시작 일치» 로 맞추지 않는다 — 「살아 있는 행」이 「살아 있는 행 중
    추적 표지가 없는 것」에도 걸려 뒤 값이 앞 값을 덮었다. 정확히 맞춘다.
    """
    want = set(keys)
    out: dict[str, str] = {}
    for line in text.split("\n"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        label = _plain(cells[0])
        if label in want:
            out[label] = _plain(cells[1])
    return out


def undecided_codes() -> tuple[str, list[str]]:
    """확정되지 않은 업무 코드 — 개수와 이름."""
    text = run("openapi/count-undecided-codes.py")
    m = re.search(r"⭐ 업무 코드\s+(\d+)", text)
    count = m.group(1) if m else "?"
    names: list[str] = []
    started = False
    for line in text.split("\n"):
        if line.startswith("⭐ 업무 코드"):
            started = True
            continue
        if started:
            if not line.startswith("   "):
                if names:
                    break
                continue
            names += line.split()
    return count, names


def polymorphic_gaps() -> tuple[str, list[str]]:
    text = run("verify-polymorphic-mapping.py")
    m = re.search(r"⛔ 대응표 없음 (\d+)곳", text)
    rows = [l.strip() for l in text.split("\n") if l.strip().startswith("[")]
    return (m.group(1) if m else "0"), rows


def screen_gaps(no_remote: bool) -> dict[str, str]:
    args = ["--no-remote"] if no_remote else []
    run("build-screen-progress.py", *args)
    text = read(os.path.join(HERE, "화면-진도표.md"))
    out: dict[str, str] = {}
    for head in ("상세 스펙이 없는 화면", "요구서 §3 이 다루지 않은 화면",
                 "착수 통지가 아직 안 나간 화면"):
        m = re.search(r"^### [⛔⚠] %s — (\d+)건\n\n(.*)$" % re.escape(head),
                      text, re.M)
        out[head] = "%s건 — %s" % (m.group(1), m.group(2)) if m else "조회 못 함"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--no-remote", action="store_true")
    args = ap.parse_args()

    run("collect-open-items.py")
    ledger = read(os.path.join(HERE, "미결-대장.md"))
    TRACKLESS = "살아 있는 행 중 추적 표지가 없는 것"
    s = summary_rows(ledger, ("화면 스펙", "미결 행", "살아 있는 행",
                              TRACKLESS, "등급 열을 가진 행", "그중 차단"))
    code_count, code_names = undecided_codes()
    poly_count, poly_rows = polymorphic_gaps()
    gaps = screen_gaps(args.no_remote)

    blocking = s.get("그중 차단", "?")
    verdict = ("✅ **차단 0 — 전 화면을 지금 지어도 된다.**"
               if blocking == "0" else
               "⛔ **차단 %s건 — 그 화면은 골격이 바뀔 수 있다.**" % blocking)

    lines = [
        "# 99 인계 대장 — 「최종」인데 아직 안 정해진 것",
        "",
        "> ⛔ **생성물이다. 손으로 고치지 마라.** `python3 deliverables/build-handover-ledger.py` 가 다시 만든다.",
        ">",
        "> 최종 인도물에 **「아직 안 정해진 것」의 자리가 없으면 그것이 조용히 사라진다.**",
        "> 개발이 「다 정해졌다」로 읽고 만들다 그 자리에서 멈춘다.",
        "",
        "## ⭐ 한 줄 판정",
        "",
        verdict,
        "",
        "살아 있는 미결이 **%s행**이지만 그중 **화면 골격을 바꾸는 것은 %s건**이다."
        % (s.get("살아 있는 행", "?"), blocking),
        "나머지는 **동작·문구가 바뀌거나 표시만 바뀌는 것**이라 지어 놓고 채우면 된다.",
        "",
        "---",
        "",
        "## 1. 화면 스펙 미결",
        "",
        "| 무엇 | 값 |",
        "| --- | :-: |",
    ]
    for k in ("화면 스펙", "미결 행", "살아 있는 행", "등급 열을 가진 행", "그중 차단"):
        if k in s:
            lines.append("| %s | **%s** |" % (k, s[k]))
    if TRACKLESS in s:
        lines.append("| 살아 있는 행 중 **추적 표지가 없는 것** | **%s** |" % s[TRACKLESS])
    lines += [
        "",
        "**전건과 화면별 내역은 `미결-대장.md` 가 정본이다.** 여기 옮기지 않는다.",
        "",
        "⚠ **추적 표지가 없는 행은 「답이 와도 기계로 못 찾는다」**는 뜻이다 — 그 행이 걸린 화면을 사람이 기억해야 한다.",
        "",
        "```",
        "python3 deliverables/collect-open-items.py --issue <표지>   # 그 표지가 걸린 화면",
        "python3 deliverables/collect-open-items.py --warn           # 표지 없는 행",
        "```",
        "",
        "## 2. 확정되지 않은 업무 코드 — **%s종**" % code_count,
        "",
        "고객사가 자기 분류 체계를 정해야 하는 값이다. ⭐ **확정을 기다리지 않는다** — 공통코드 마스터로 관리하고 **구현은 임의 값으로 진행**한다.",
        "",
        "⛔ **가르는 기준** — 「화면·계약의 **동작**이 그 값에 걸리는가」. 걸리면(상태 전이·분기·검증) 설계가 정하고, 안 걸리면(사유·분류) 마스터다.",
        "",
    ]
    if code_names:
        lines += ["```"]
        for i in range(0, len(code_names), 4):
            lines.append("  " + "  ".join("%-30s" % n for n in code_names[i:i + 4]).rstrip())
        lines += ["```", "",
                  "> 다시 세려면 `python3 deliverables/openapi/count-undecided-codes.py`", ""]

    lines += [
        "## 3. 한 칸이 여러 표를 가리키는 자리 — 대응표 결손 **%s곳**" % poly_count,
        "",
        "유형 코드와 대상 표를 잇는 대응표가 **참조 무결성 제약을 대신한다.** 없으면 서버도 화면도 무엇을 가리키는지 모른다.",
        "",
    ]
    if poly_rows:
        lines += ["```"] + ["  " + r for r in poly_rows] + ["```", "",
                  "> 다시 보려면 `python3 deliverables/verify-polymorphic-mapping.py`", ""]

    lines += [
        "## 4. 화면 축의 구멍",
        "",
        "| 무엇 | 값 |",
        "| --- | --- |",
    ]
    for k, v in gaps.items():
        lines.append("| %s | %s |" % (k, v))
    lines += [
        "",
        "> 다시 만들려면 `python3 deliverables/build-screen-progress.py`",
        "",
        "---",
        "",
        "## ⚠ 이 대장이 **안** 보는 것",
        "",
        "| 무엇 | 왜 |",
        "| --- | --- |",
        "| **미결의 내용이 맞는지** | 스펙이 틀렸으면 대장도 똑같이 틀린다 |",
        "| **추적 표지가 가리키는 곳이 살아 있는지** | 닫힌 이슈를 가리켜도 모른다 |",
        "| **고객·팀 리더 회신 대기** | 화면 스펙 §8 밖에 있다 |",
        "| **데이터 모델 결손** | 작업 통지로 나가 있고 우리를 막지 않는다 — `omf-mes#66`·`#67` |",
        "",
    ]
    io.open(OUT, "w", encoding="utf-8").write("\n".join(lines))
    print("생성: %s" % os.path.relpath(OUT, ROOT))
    print("차단 %s · 살아 있는 미결 %s · 업무 코드 %s · 대응표 결손 %s"
          % (blocking, s.get("살아 있는 행", "?"), code_count, poly_count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
