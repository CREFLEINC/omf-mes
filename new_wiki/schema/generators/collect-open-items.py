#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""화면 스펙 §8 을 전수로 훑어 «미결 대장»을 생성한다.

왜 필요한가
-----------
미결이 태어나는 자리는 화면 스펙 §8 하나인데, **전체를 담은 대장이 없었다.**
그래서 「확정이 내려왔을 때 어느 화면이 걸리나」를 사람이 118파일을 훑어야
답할 수 있었고, 실제로 두 번 못 찾았다.

    2026-08-16  「MES 는 품의서를 기안하지 않는다」 확정
                → 확정문이 예로 든 W-01-06 만 보고 W-04-10 을 못 봤다
    2026-08-16  재고 상태 값 목록 협착
                → 어느 통지가 걸리는지 안 보고 계약을 좁혔다

⭐ **그래서 사람이 적는 대장을 만들지 않는다.** 손으로 쓴 대장은 이 저장소에서
예외 없이 낡았다(요구서 머리말 6/8 · README 6수치 · ds-gap 진도 …).
**스펙이 정본이고 대장은 뽑는 것**이어야 한다.

무엇을 하나
-----------
1. `new_wiki/wiki/screens/*/` 아래 화면 스펙(`W-`·`P-`·`M-` 로 시작)을 전부 찾는다.
2. 각 파일에서 「미결」 절의 표를 찾아 행을 뽑는다. 서식은 두 판이 섞여 있다.

       5열 판  | # | 항목 | 성격 | 등급 | 처리 |
       4열 판  | # | 항목 | 성격 | 처리 |

   열 이름으로 가르므로 열 순서가 바뀌어도 따라간다.
3. 행마다 **추적 표지**를 뽑는다 — 이슈 `#N` · 의사결정 요청 `DR-00N` ·
   공유계약 조항 `X-N` · 고객 회신 `E-N`. 하나도 없으면 그 행은 **답이 왔을 때
   기계로 찾을 수 없다.**
4. **해소 표시**(✅ · 해소 · 종결 · 취소선)가 붙은 행을 갈라 센다.
5. `new_wiki/wiki/handover/미결-대장.md` 로 쓴다.

⚠ 이 생성기가 못 보는 것
------------------------
- **미결의 «내용»이 맞는지는 안 본다.** 표에 적힌 것을 옮길 뿐이다.
- **추적 표지가 «가리키는 곳»이 살아 있는지 안 본다.** `#54` 처럼 이미 닫힌
  이슈를 가리켜도 표지가 있는 것으로 센다. 닫힌 이슈 되짚기는 별도 절차다.
- **표 밖에 적힌 미결은 못 잡는다.** 확대 1차는 미결 상세를 공유계약 §I 묶음
  표에 두어, 스펙 행만으로는 무엇을 기다리는지 알 수 없다(`--warn` 이 알린다).
- **「차단」 판정이 맞는지 안 본다.** 4열 판에는 등급 열이 아예 없다.

쓰기
----
    python3 new_wiki/schema/generators/collect-open-items.py              # 대장을 다시 만든다
    python3 new_wiki/schema/generators/collect-open-items.py --check      # 무변경인지만 본다(종료 1 = 갈렸다)
    python3 new_wiki/schema/generators/collect-open-items.py --warn       # 추적 표지 없는 행을 나열
    python3 new_wiki/schema/generators/collect-open-items.py --issue 64   # 그 표지가 걸린 화면만
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "new_wiki", "wiki", "handover", "미결-대장.md")

SPEC_GLOB = os.path.join(ROOT, "new_wiki", "wiki", "screens", "*", "[WPM]-*.md")
SCREEN_ID = re.compile(r"^([WPM]-(?:CO|\d{2})-\d{2})")

# 「미결」이 제목에 들어간 절. §8 이 표준이나 차수마다 번호가 다를 수 있어
# 번호로 찾지 않는다.
HEAD = re.compile(r"^(#{2,4})\s+.*미결", re.M)
ANY_HEAD = re.compile(r"^#{1,4}\s", re.M)

# 추적 표지 — 이 넷 중 하나라도 있으면 「답이 왔을 때 되짚을 수 있다」.
TRACKS = (
    ("이슈", re.compile(r"#(\d{1,3})\b")),
    ("DR", re.compile(r"\bDR-(\d{3})\b")),
    ("조항", re.compile(r"\b([A-J]-\d{1,2})\b")),
    ("회신", re.compile(r"\b(E-\d{1,2})\b")),
)
DONE = re.compile(r"✅|해소|종결|~~")


def cells(line: str) -> list[str]:
    """마크다운 표 한 줄을 칸으로 가른다 — 양끝 파이프는 버린다."""
    if not line.startswith("|"):
        return []
    return [c.strip() for c in line.strip().strip("|").split("|")]


def plain(text: str) -> str:
    """표기를 걷어 낸다 — 대장에서 다시 표로 쓰므로 파이프는 이스케이프한다."""
    t = re.sub(r"\*\*|~~|`", "", text)
    return t.replace("|", "\\|").strip()


def section(body: str) -> str | None:
    """미결 절 본문. 다음 «같거나 더 높은 수준» 헤딩까지.

    ⚠ 제목에 「미결」이 든 헤딩이 여럿일 수 있다 — 「`W-04-08` 미결 해소」처럼
    §5 소절이 남의 미결을 «언급»하기도 한다. 그래서 첫 헤딩을 집지 않고,
    **미결 표(`| # | 항목 …`)를 실제로 가진 절**을 고른다.
    """
    fallback = None
    for m in HEAD.finditer(body):
        level = len(m.group(1))
        rest = body[m.end():]
        sec = rest
        for nxt in ANY_HEAD.finditer(rest):
            if len(nxt.group(0).split()[0]) <= level:
                sec = rest[: nxt.start()]
                break
        if any(cells(l)[:1] in (["#"], ["번호"]) and any("항목" in c for c in cells(l))
               for l in sec.splitlines() if l.startswith("|")):
            return sec
        if fallback is None:
            fallback = sec
    return fallback


def parse(path: str) -> dict | None:
    sid = SCREEN_ID.match(os.path.basename(path))
    if not sid:
        return None
    body = open(path, encoding="utf-8").read()
    sec = section(body)
    if sec is None:
        return {"screen": sid.group(1), "path": path, "rows": [], "table": False,
                "declared": None}

    rows, header = [], None
    for line in sec.splitlines():
        cs = cells(line)
        if not cs:
            continue
        if header is None:
            if cs[0] in ("#", "번호") and any("항목" in c for c in cs):
                header = cs
            continue
        if set("".join(cs)) <= set("-: "):        # 구분선
            continue
        if len(cs) < len(header) - 1:             # 표가 끝났다
            break
        col = dict(zip(header, cs))
        item = next((v for k, v in col.items() if "항목" in k), cs[1] if len(cs) > 1 else "")
        handling = next((v for k, v in col.items() if "처리" in k), "")
        nature = next((v for k, v in col.items() if "성격" in k), "")
        grade = next((v for k, v in col.items() if "등급" in k), "")
        whole = " ".join(cs)
        marks = []
        for kind, pat in TRACKS:
            for hit in pat.findall(whole):
                tag = f"#{hit}" if kind == "이슈" else (
                    f"DR-{hit}" if kind == "DR" else hit)
                if tag not in marks:
                    marks.append(tag)
        rows.append({
            "no": cs[0].strip("*# "), "item": item, "nature": nature,
            "grade": grade, "handling": handling, "marks": marks,
            "done": bool(DONE.search(whole)),
        })

    declared = None
    m = re.search(r"차단\s*(\d+)\s*건", sec)
    if m:
        declared = int(m.group(1))
    return {"screen": sid.group(1), "path": path, "rows": rows,
            "table": header is not None, "declared": declared}


def collect() -> list[dict]:
    out = [parse(p) for p in sorted(glob.glob(SPEC_GLOB))]
    return sorted([s for s in out if s], key=lambda s: s["screen"])


def render(specs: list[dict]) -> str:
    rows = [(s, r) for s in specs for r in s["rows"]]
    open_rows = [(s, r) for s, r in rows if not r["done"]]
    untracked = [(s, r) for s, r in open_rows if not r["marks"]]
    graded = [(s, r) for s, r in rows if r["grade"]]
    blocking = [(s, r) for s, r in open_rows if "차단" in r["grade"]]

    L = [
        "# 미결 대장 — 화면 스펙 §8 전수",
        "",
        "> ⛔ **생성물이다. 손으로 고치지 마라.** 정본은 각 화면 스펙의 「미결」 절이고,",
        "> 이 파일은 `python3 new_wiki/schema/generators/collect-open-items.py` 가 다시 만든다.",
        ">",
        "> 이 대장이 답하는 질문 = **「확정이 내려왔을 때 어느 화면이 걸리나」**.",
        "> 그 답을 못 찾아 두 번 사고가 났다(2026-08-16 품의 개칭 · 재고 상태 협착).",
        "",
        "## 요약",
        "",
        "| 무엇 | 값 |",
        "| --- | :-: |",
        f"| 화면 스펙 | **{len(specs)}** |",
        f"| 미결 절을 못 찾은 스펙 | **{sum(1 for s in specs if not s['table'])}** |",
        f"| 미결 행 | **{len(rows)}** |",
        f"| ├ 해소 표시가 붙은 행 | {len(rows) - len(open_rows)} |",
        f"| └ 살아 있는 행 | **{len(open_rows)}** |",
        f"| 살아 있는 행 중 **추적 표지가 없는 것** | **{len(untracked)}** "
        f"({round(len(untracked) * 100 / max(len(open_rows), 1))}%) |",
        f"| 등급 열을 가진 행 | {len(graded)} |",
        f"| 그중 **차단** | **{len(blocking)}** |",
        "",
        "⚠ **추적 표지가 없다** = 이슈 `#N` · `DR-00N` · 공유계약 조항 `X-N` ·",
        "회신 `E-N` 어느 것도 안 적혀 있다. 그 행은 **답이 와도 기계로 못 찾는다.**",
        "",
    ]

    if blocking:
        L += ["## ⛔ 차단 — 착수 통지를 낼 수 없는 화면", ""]
        L += ["| 화면 | 항목 | 처리 |", "| --- | --- | --- |"]
        L += [f"| `{s['screen']}` | {plain(r['item'])} | {plain(r['handling'])} |"
              for s, r in blocking]
        L += [""]

    # 표지별 역인덱스 — 이 대장의 존재 이유다
    index: dict[str, list[str]] = {}
    for s, r in open_rows:
        for mk in r["marks"]:
            index.setdefault(mk, []).append(s["screen"])
    L += ["## 추적 표지 → 걸리는 화면", "",
          "⭐ **답이 왔을 때 여기를 본다.** 표지 하나가 여러 화면에 걸린다.", "",
          "| 표지 | 화면 수 | 화면 |", "| --- | :-: | --- |"]
    for mk in sorted(index, key=lambda k: (-len(index[k]), k)):
        seen = sorted(set(index[mk]))
        L.append(f"| `{mk}` | {len(seen)} | {' · '.join(f'`{x}`' for x in seen)} |")
    L += [""]

    L += ["## 화면별 미결", ""]
    for s in specs:
        live = [r for r in s["rows"] if not r["done"]]
        if not s["table"]:
            L += [f"### `{s['screen']}`", "", "⚠ **미결 절을 못 찾았다** — "
                  f"`{os.path.relpath(s['path'], ROOT)}`", ""]
            continue
        if not live:
            L += [f"### `{s['screen']}` — 살아 있는 미결 0건", ""]
            continue
        L += [f"### `{s['screen']}` — {len(live)}건", "",
              "| # | 항목 | 성격 | 등급 | 처리 | 표지 |",
              "| :-: | --- | --- | :-: | --- | --- |"]
        for r in live:
            marks = " ".join(f"`{m}`" for m in r["marks"]) or "**없음**"
            L.append(f"| {r['no']} | {plain(r['item'])} | {plain(r['nature'])} | "
                     f"{plain(r['grade']) or '—'} | {plain(r['handling'])} | {marks} |")
        L += [""]
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="다시 만든 것과 같은지만 본다")
    ap.add_argument("--warn", action="store_true", help="추적 표지 없는 행을 나열")
    ap.add_argument("--issue", help="그 표지가 걸린 화면만 (예: 64 · DR-007 · C-12)")
    a = ap.parse_args()

    specs = collect()
    if not specs:
        print("⛔ 화면 스펙을 못 찾았다", file=sys.stderr)
        return 1

    if a.issue:
        want = a.issue if not a.issue.isdigit() else f"#{a.issue}"
        hits = [(s["screen"], r) for s in specs for r in s["rows"]
                if want in r["marks"] and not r["done"]]
        screens = sorted({sid for sid, _ in hits})
        print(f"`{want}` 가 걸린 살아 있는 미결 — **{len(hits)}건 / {len(screens)}화면**")
        for sid, r in hits:
            print(f"  {sid:10} {plain(r['item'])[:90]}")
        return 0

    if a.warn:
        bad = [(s["screen"], r) for s in specs for r in s["rows"]
               if not r["done"] and not r["marks"]]
        print(f"추적 표지 없는 살아 있는 미결 — {len(bad)}건")
        for sid, r in bad:
            print(f"  {sid:10} {plain(r['item'])[:90]}")
        return 1 if bad else 0

    text = render(specs)
    if a.check:
        old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if old == text:
            print(f"✅ 미결 대장이 스펙과 같습니다 — 화면 {len(specs)}")
            return 0
        print("⛔ 미결 대장이 스펙과 갈렸습니다 — 다시 만드십시오", file=sys.stderr)
        return 1

    open(OUT, "w", encoding="utf-8").write(text)
    rows = sum(len(s["rows"]) for s in specs)
    live = sum(1 for s in specs for r in s["rows"] if not r["done"])
    untracked = sum(1 for s in specs for r in s["rows"]
                    if not r["done"] and not r["marks"])
    print(f"  ✅ {os.path.relpath(OUT, ROOT)} — 화면 {len(specs)} · 미결 행 {rows} "
          f"· 살아 있음 {live} · 추적 표지 없음 {untracked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
