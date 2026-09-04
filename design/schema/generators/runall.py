#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""전 검사기를 한 번에 돌린다 — ⛔ 읽기 전용인 것만.

왜 있는가
---------
검사기가 30종인데 「전부 돌렸다」를 사람이 손으로 세고 있었다. 그래서 두 가지가 났다.

  ① **빠뜨린다.** 하네스가 「`verify-*.py` 를 전부」라고 이름 패턴으로 지시했는데,
     그 패턴은 `openapi/check-*.py` 17종과 스킬 쪽 2종을 아예 안 부른다.
  ② **모르고 쓴다.** 그 패턴에 걸리는 `verify-ui-coverage.py` 는 «검사기 이름을 하고
     생성물을 덮어썼다». 검사한 줄 알았는데 생성물이 조용히 다시 쓰였다
     (2026-09-03 그 스크립트의 기본을 검사로 뒤집었다).

⇒ **이름 패턴으로 추정하지 않는다. 아래 등록부가 정본이다.**

무엇을 돌리나
-------------
`READERS` 에 적힌 것만 기본으로 돌린다. **작업 트리를 건드리는 것**(`WRITERS`)은
등록부에 남겨 두되 **기본 실행에서 뺀다** — `--include-writers` 를 줄 때만 돈다.

    python3 design/schema/generators/runall.py                    # 읽기 전용 전건
    python3 design/schema/generators/runall.py --list             # 등록부만 보인다
    python3 design/schema/generators/runall.py --include-writers  # 쓰는 것까지
    python3 design/schema/generators/runall.py --only code        # 이름에 조각이 든 것만

⛔ 출력을 자르지 않는다
-----------------------
각 검사기의 stdout·stderr 를 **그대로** 흘리고, 맨 끝에 요약표(검사기 · 종료코드 ·
⚠ 건수)를 낸다. `tail -1` 로 마지막 ✅ 만 보다가 위반 6건을 놓친 적이 있다.

종료 코드
---------
**자식들의 종료 코드를 합산**한다(255 를 넘으면 125 로 자른다 — 셸 종료 코드는 1바이트다).
요약표에는 자른 적 없는 «원래 합»을 함께 적는다.

⛔ `design/raw/` 는 탐색 범위 밖이다
------------------------------------
`design/raw/` 아래에 `.py` 가 44개 있지만(2026-09-03 실측) **전부 시점 고착본**이라
돌리지 않는다 — `design/README.md` 「raw/ 안의 실행 가능한 스크립트는 돌리지 않는다」.
  · `raw/process/openapi-patches/patch-*.py` 38개는 **계약 정본을 덮어쓴다**
  · `raw/process/deliverables/verify-polymorphic-mapping.py` 는 **깨져 있고**(사라진
    물리 모델 SQL 을 연다 · 시험 9건 실패) SQL 을 설계 판단의 근거로 읽어
    `schema/data-model-boundary.md` 와 정면 충돌한다
  ⛔ 고치지도 않는다 — 훅이 `raw/` 쓰기를 막고, 고치면 그것은 이미 「그때의 원문」이 아니다.

⚠ 이 실행기가 «안» 보는 것
---------------------------
- **검사기가 옳은지** — 검사기가 못 보는 자리는 여기서도 안 보인다
- **시험(`test-*.py`)** — 이것은 검사기 실행기다. 시험은 `test-*.py` 를 직접 돌린다
- **생성기(`build-*.py`)** — 만드는 것이지 보는 것이 아니다
"""
from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

TIMEOUT = 600   # 초. 넘으면 그 검사기만 실패로 세고 계속 간다.


# ── 등록부 ─────────────────────────────────────────────────────────
# (저장소 기준 경로, 인자, 인자를 그렇게 주는 이유 / 대상 찾는 법)
#
# ⭐ 인자가 필요한 검사기를 어떻게 다루는지 여기 «전부» 적는다. 조용히 빼지 않는다.
#    대상이 0건이면 「건너뛴 사실」을 출력한다.
READERS: list[tuple[str, list[str], str]] = [
    # ── design/schema/generators/ — 10종
    ("design/schema/generators/check-dead-path-citations.py", [],
     "인자 없음 = 검사. `--fix` 를 주면 치환하므로 «주지 않는다»"),
    ("design/schema/generators/collect-open-items.py", ["--check"],
     "⭐ `--check` 필수 — 인자 없이 돌리면 미결 대장을 «덮어쓴다»"),
    ("design/schema/generators/count-decisions.py", ["--check"],
     "`--check` 는 문서 머리의 「N행」 표기와 대조한다(없으면 세기만 하고 늘 0)"),
    ("design/schema/generators/verify-contract-citation.py", [], "인자 없음"),
    ("design/schema/generators/verify-counts.py", [], "인자 없음"),
    ("design/schema/generators/verify-doc-citations.py", [],
     "`--doc <조각>` 은 한 요구서만 본다 — 전건이 기본"),
    ("design/schema/generators/verify-mapping-coverage.py", [],
     "인자 없으면 전 도메인(2026-08-29 부터). `--domain` 은 한 도메인만 봐서 거짓 초록을 낸다"),
    ("design/schema/generators/verify-screen-inventory.py", [], "인자 없음"),
    ("design/schema/generators/verify-stale-terms.py", [],
     "첫 인자는 대조 기준 git ref — 기본 `HEAD`(작업 트리 ↔ HEAD)"),
    # ⛔ **도메인마다 한 번씩 부른다** — `verify-ui-coverage.py` 는 한 번에 «한 도메인»만
    #    본다(기본 `mdm`). 인자 없이 한 번만 부르면 나머지 8 도메인이 낡아도 ✅ 가 난다.
    #    2026-09-04 실측으로 실제로 그랬다 — 8벌이 낡은 채 이 실행기가 초록을 냈다.
    #    바로 위 `verify-mapping-coverage` 주석이 경고한 것과 같은 함정이다.
] + [
    ("design/schema/generators/verify-ui-coverage.py", ["--domain", _d],
     "도메인 %s — 9 도메인을 각각 본다(한 번만 부르면 거짓 초록)" % _d)
    for _d in ("mdm", "01", "app", "02", "print", "03", "04", "05", "co")
] + [

    # ── design/schema/generators/openapi/ — 17종. 전부 인자 없이 돈다.
    ("design/schema/generators/openapi/check-code-dictionary.py", [],
     "인자 없음(`--split` 은 형제 갈림만 낸다)"),
    ("design/schema/generators/openapi/check-code-group-pointer.py", [], "인자 없음"),
    ("design/schema/generators/openapi/check-code-group-reachable.py", [], "인자 없음"),
    ("design/schema/generators/openapi/check-code-notation.py", [],
     "인자 없음(`--list` 는 자리 전건을 낸다)"),
    ("design/schema/generators/openapi/check-enum-narrowing.py", [],
     "첫 인자는 대조 기준 git ref — 기본 `HEAD`"),
    ("design/schema/generators/openapi/check-example-placeholder.py", [],
     "⭐ 인자 = 검사할 계약 파일. 없으면 **계약 7벌 전건**(기본 글롭)"),
    ("design/schema/generators/openapi/check-lock-token-source.py", [], "인자 없음"),
    ("design/schema/generators/openapi/check-offline-consistency.py", [], "인자 없음"),
    ("design/schema/generators/openapi/check-operation-inventory-drift.py", [], "인자 없음"),
    ("design/schema/generators/openapi/check-public-safe.py", [],
     "⭐ 인자 = 검사할 계약 파일. 없으면 **계약 7벌 전건**(기본 글롭)"),
    ("design/schema/generators/openapi/check-query-envelope.py", [], "인자 없음"),
    ("design/schema/generators/openapi/check-required-change.py", [],
     "첫 인자는 대조 기준 git ref — 기본 `HEAD`"),
    ("design/schema/generators/openapi/check-required-in-fieldtable.py", [], "인자 없음"),
    ("design/schema/generators/openapi/check-screen-code-dictionary.py", [], "인자 없음"),
    ("design/schema/generators/openapi/check-structure.py", [],
     "⭐ 인자 = 검사할 계약 파일. 없으면 **계약 7벌 전건**(기본 글롭)"),
    ("design/schema/generators/openapi/check-worker-no.py", [],
     "인자 없음(`--list` 는 자리 전건을 낸다)"),
    ("design/schema/generators/openapi/count-undecided-codes.py", [],
     "인자 없음. 세기만 한다 — 종료 코드는 늘 0(판정 정본은 코드 사전이다)"),
]

# ⭐ 대상 파일을 받아야만 도는 검사기 — 대상이 0건이면 «건너뛴 사실을 출력»한다.
#    (저장소 기준 경로, 대상 글롭들, 무엇이 대상인가)
TARGETED: list[tuple[str, list[str], str]] = [
    (".claude/skills/uiux-design/scripts/check-report-language.py",
     # ⛔ `tmp/requests/*/*.md` 로 넓히지 않는다 — 같은 폴더의 `요청.md` 는 «개발팀이 쓴 글»이고
     #    Phase 1 이 그대로 저장하라고 정한 시점 고착본이다. 우리 서술 규약(화면 번호 전개)으로
     #    검사하면 «고칠 수 없는 ⛔» 가 남는다. 2026-09-04 실측 — omf-mes#427 요청서를 저장하자
     #    runall 이 그 자리에서 빨개졌고, 고치려면 개발팀의 문장을 우리가 바꿔야 했다.
     ["tmp/requests/*/답변서.md", "tmp/replies/*.md"],
     "완료보고·답변서 초안 — «우리가 쓴 글»만. 정본은 `tmp/` 아래(gitignore)라 평소에는 0건이다"),
    (".claude/skills/design-change-notice/scripts/check-notice.py",
     ["tmp/notices/*.md"],
     "설계 변동 공지 초안. `build-notice.py` 가 만든 뒤에만 있다"),
]

# ✍ 작업 트리를 건드리는 것 — 기본 실행에서 «뺀다». `--include-writers` 로만.
WRITERS: list[tuple[str, list[str], str]] = [
    ("design/schema/generators/verify-generated-fresh.py", [],
     "✍ 생성물 18건을 «다시 만들어 보고 되돌린다». 되돌리므로 결과는 그대로지만 "
     "도중에 작업 트리를 쓴다 — 다른 사람이 같은 트리에서 일하면 그 순간을 본다"),
]

# ⛔ 탐색 범위 밖 — 왜 빼는지 여기 적는다(조용히 빼지 않는다).
EXCLUDED: list[tuple[str, str]] = [
    ("design/raw/**/*.py (44개)",
     "⛔ 시점 고착본이라 돌리지 않는다(`design/README.md`). patch-*.py 38개는 계약 정본을 "
     "덮어쓰고, verify-polymorphic-mapping.py 는 사라진 물리 모델 SQL 을 열어 깨져 있다"),
    ("design/schema/generators/build-*.py",
     "생성기다 — 보는 것이 아니라 만드는 것이라 검사 대상이 아니다"),
    ("**/test-*.py",
     "시험이다 — 검사기를 고친 뒤 직접 돌린다"),
]


def registered_paths() -> set[str]:
    return {p for p, _a, _n in READERS + WRITERS} | {p for p, _g, _n in TARGETED}


def unregistered() -> list[str]:
    """등록부에 없는 검사기 — 등록부가 낡으면 이 실행기가 조용히 덜 돈다."""
    known = registered_paths()
    found = []
    for pat in ("design/schema/generators/*.py",
                "design/schema/generators/openapi/*.py",
                ".claude/skills/*/scripts/*.py"):
        for p in sorted(glob.glob(os.path.join(ROOT, pat))):
            rel = os.path.relpath(p, ROOT)
            base = os.path.basename(rel)
            if base.startswith(("test-", "build-", "runall")):
                continue
            if rel not in known:
                found.append(rel)
    return found


def resolve(globs: list[str]) -> list[str]:
    out: list[str] = []
    for g in globs:
        out += sorted(glob.glob(os.path.join(ROOT, g)))
    return out


def run_one(rel: str, args: list[str]) -> tuple[int, int]:
    """(종료 코드, ⚠ 건수). 출력은 그대로 흘린다 — ⛔ 자르지 않는다."""
    path = os.path.join(ROOT, rel)
    print("\n" + "═" * 78)
    print("▶ %s %s" % (rel, " ".join(args)))
    print("═" * 78)
    if not os.path.exists(path):
        print("⛔ 파일이 없다 — 등록부가 낡았다")
        return 1, 0
    cmd = [sys.executable, path] + args
    try:
        p = subprocess.run(cmd, cwd=os.path.dirname(path), timeout=TIMEOUT,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        body = p.stdout.decode("utf-8", "replace")
        rc = p.returncode
    except subprocess.TimeoutExpired:
        print("⛔ %d초를 넘겨 끊었다" % TIMEOUT)
        return 1, 0
    sys.stdout.write(body)
    if body and not body.endswith("\n"):
        sys.stdout.write("\n")
    return rc, sum(1 for line in body.split("\n") if "⚠" in line)


def show_list() -> int:
    print("등록부 — 이 실행기가 무엇을 돌리나 (이름 패턴이 아니라 «목록»이 정본이다)\n")
    print("■ 읽기 전용 — 기본 실행 (%d)" % len(READERS))
    for rel, args, note in READERS:
        print("  %-72s %s" % (rel + (" " + " ".join(args) if args else ""), note))
    print("\n■ 대상 파일이 있어야 도는 것 (%d) — 0건이면 건너뛴 «사실»을 출력한다"
          % len(TARGETED))
    for rel, globs, note in TARGETED:
        got = resolve(globs)
        print("  %-72s %s" % (rel, note))
        print("      대상 글롭 %s — 지금 %d건" % (" · ".join(globs), len(got)))
    print("\n■ ✍ 쓰는 것 — 기본 실행에서 «뺀다» (%d) · `--include-writers` 로만"
          % len(WRITERS))
    for rel, args, note in WRITERS:
        print("  %-72s %s" % (rel + (" " + " ".join(args) if args else ""), note))
    print("\n■ ⛔ 탐색 범위 밖")
    for what, why in EXCLUDED:
        print("  %-40s %s" % (what, why))
    miss = unregistered()
    print("\n■ 등록부에 없는 검사기 — %d건" % len(miss))
    for rel in miss:
        print("  ⚠ %s" % rel)
    return 1 if miss else 0


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.split("\n")[0])
    ap.add_argument("--list", action="store_true", help="등록부만 보이고 끝낸다")
    ap.add_argument("--include-writers", action="store_true",
                    help="✍ 작업 트리를 건드리는 검사기까지 돌린다")
    ap.add_argument("--only", help="경로에 이 조각이 든 것만 돌린다")
    a = ap.parse_args()

    if a.list:
        return show_list()

    plan: list[tuple[str, list[str]]] = [(r, args) for r, args, _n in READERS]
    skipped: list[tuple[str, str]] = []
    for rel, globs, note in TARGETED:
        got = resolve(globs)
        if got:
            plan.append((rel, [os.path.relpath(g, ROOT) for g in got]))
        else:
            skipped.append((rel, "대상 0건 — 글롭 %s (%s)" % (" · ".join(globs), note)))
    if a.include_writers:
        plan += [(r, args) for r, args, _n in WRITERS]
    else:
        for rel, _args, note in WRITERS:
            skipped.append((rel, "✍ 기본 실행에서 뺐다 — %s" % note))

    if a.only:
        plan = [(r, args) for r, args in plan if a.only in r]

    results: list[tuple[str, int, int]] = []
    for rel, args in plan:
        rc, warns = run_one(rel, args)
        # ⛔ 라벨에 인자를 «싣는다» — 같은 스크립트를 도메인마다 부르는 자리가 있어
        # 경로만 적으면 요약표에 똑같은 줄이 여럿 서고 어느 것이 빨간지 못 읽는다.
        results.append((rel + (" " + " ".join(args) if args else ""), rc, warns))

    total = sum(rc for _r, rc, _w in results)
    bad = [r for r in results if r[1] != 0]

    print("\n" + "═" * 78)
    kinds = len({rel.split(" ")[0] for rel, _c, _w in results})
    print("요약 — 검사기 %d종 · 실행 %d건 · ⛔ 실패 %d · ⚠ %d건"
          % (kinds, len(results), len(bad), sum(w for _r, _c, w in results)))
    print("═" * 78)
    print("%-4s %-62s %5s %5s" % ("", "검사기", "종료", "⚠"))
    for rel, rc, warns in results:
        print("%-4s %-62s %5d %5d" % ("⛔" if rc else "✅", rel, rc, warns))
    if skipped:
        print("\n건너뛴 것 %d건 — ⛔ 조용히 빼지 않는다" % len(skipped))
        for rel, why in skipped:
            print("  · %s\n      %s" % (rel, why))
    miss = unregistered()
    if miss:
        print("\n⚠ 등록부에 없는 검사기 %d건 — 등록부가 낡으면 이 실행기가 «덜» 돈다" % len(miss))
        for rel in miss:
            print("  · %s" % rel)
    print("\n종료 코드 합 = %d" % total)
    return min(total, 125)


if __name__ == "__main__":
    sys.exit(main())
