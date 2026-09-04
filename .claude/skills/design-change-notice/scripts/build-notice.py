#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""설계 변동 공지 초안 생성기 — 직전 공지(태그) → HEAD 사이에 «바뀐 파일»을 뽑는다.

왜 생성기인가
-------------
V3(2026-09-03) 규칙 5 — 공지는 「변동 사항이 있다는 사실」만 알린다. 「무슨 내용이 어떻게
변경되었는지 작성하지마라」. 손으로 초안을 쓰면 내용이 섞인다 — 쓰는 사람이 바로 그 변경을 한
사람이라 «왜 바꿨는지»가 손끝에 남아 있기 때문이다. 그래서 초안은 **git 이력에서 기계가 뽑는다.**

무엇을 뽑나 — 「달라진 지점」의 입자 = 파일
------------------------------------------
2026-09-03 사용자 확정 — 「변경 점은 파일 단위로, API 계약서 내에 어떤 게 바뀌었는지 나열하지
말 것」. 첫 공지 초안(642지점·171행)이 화면의 절·계약의 경로·스키마·코드 사전의 키까지 냈는데,
그것은 개발팀이 저장소를 열어 볼 자리를 «미리» 골라 주는 일이었다 — 규칙 5 가 금지한 「자세한
내용」의 초입이다. 지점은 파일 하나가 한 줄이다.

  - 화면설계서 `design/wiki/screens/01/M-01-01-입하등록.md`
  - 코드 사전 `design/schema/code-dictionary.md` (신설)
  - 화면설계서 `design/wiki/screens/…/새이름.md` (경로 변경 · 이전 `design/wiki/screens/…/옛이름.md`)

  ⛔ 파일 «안»의 무엇이 바뀌었는지(절·경로·스키마·키·값·문장)는 내지 않는다 — 개발팀이 파일을 연다.
  ⛔ 갈래 6줄에 속하지 않는 파일(검사기·규약·progress/·색인·.html 배포본)은 싣지 않는다 — 개발팀
     열람 대상이 아니다.

갈래 분류 규칙은 `design/schema/generators/build-change-digest.py` 의 `where()` 와 같다
(경로 → 화면/계약/요구서/공유계약/코드 사전/사양서). 그 함수를 import 하지 않는 이유 —
이 생성기는 `--repo-root` 로 임의 저장소(시험용 임시 저장소 포함)에서 돌아야 한다.

쓰기
----
    python3 build-notice.py                          # 최신 notice/* 태그 → HEAD
    python3 build-notice.py --since de4203a          # 기준 해시 지정(첫 공지)
    python3 build-notice.py --since notice/20260903 --head <해시> --out tmp/notices/x.md
    python3 build-notice.py --date 2026-09-03 --repo-root <경로>   # 시험용

종료 코드  0 생성 · 1 공지할 것이 없다 · 2 인자·저장소 오류
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
REPO = "CREFLEINC/omf-mes"

# 갈래 6줄 — 계획 「공통 어휘」 그대로. (이름, 표에 적는 경로, git pathspec)
BRANCHES = [
    ("화면설계서", "`design/wiki/screens/`",
     ["design/wiki/screens/"]),
    ("API 요구서", "`design/wiki/api-contracts/06-API-요구서*.md`",
     ["design/wiki/api-contracts/06-API-요구서*.md"]),
    ("API 계약서", "`design/wiki/api-contracts/openapi/*.json`",
     ["design/wiki/api-contracts/openapi/*.json"]),
    ("코드 사전", "`design/schema/code-dictionary.md`",
     ["design/schema/code-dictionary.md"]),
    ("공유계약", "`design/wiki/decisions-policy/공유계약.md`",
     ["design/wiki/decisions-policy/공유계약.md"]),
    ("사양서·요구사항", "`design/wiki/project-spec/` · `design/wiki/requirements/`",
     ["design/wiki/project-spec/", "design/wiki/requirements/"]),
]
BRANCH_ORDER = [b[0] for b in BRANCHES]
SCAN = ["design/wiki", "design/schema/code-dictionary.md"]


class GitError(RuntimeError):
    pass


def git(root: str, *args: str, check: bool = True) -> str:
    """git 을 부른다. ⭐ quotepath=false 라야 한글 경로가 그대로 온다."""
    r = subprocess.run(["git", "-c", "core.quotepath=false", *args],
                       cwd=root, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise GitError((r.stderr or r.stdout).strip() or "git %s 실패" % " ".join(args))
    return r.stdout


def git_ok(root: str, *args: str) -> bool:
    r = subprocess.run(["git", "-c", "core.quotepath=false", *args],
                       cwd=root, capture_output=True)
    return r.returncode == 0


# ───────────────────────── 갈래 분류 — build-change-digest.py where() 와 같은 규칙

def branch_of(path: str):
    """경로 → 갈래 이름. 갈래 6줄 밖이면 None(싣지 않는다)."""
    base = os.path.basename(path)
    if base.endswith(".html"):
        return None                      # 배포본 — 원본 .md 가 정본이고 둘이 같은 변경이다
    if "/screens/" in path:
        return "화면설계서"
    if "/openapi/" in path and path.endswith(".json"):
        return "API 계약서"
    if base.startswith("06-API-요구서"):
        return "API 요구서"
    if base == "공유계약.md":
        return "공유계약"
    if base == "code-dictionary.md":
        return "코드 사전"
    if "/project-spec/" in path or "/requirements/" in path:
        return "사양서·요구사항"
    return None


# ───────────────────────── 변경 파일 목록

def changed_files(root: str, since: str, head: str):
    """[(status, old_path, new_path)] — R/C 는 두 경로, 나머지는 같은 경로 둘."""
    out = git(root, "diff", "--name-status", "-M", "-z", since + ".." + head, "--", *SCAN)
    parts = out.split("\0")
    rows, i = [], 0
    while i < len(parts):
        st = parts[i]
        if not st:
            i += 1
            continue
        if st[0] in "RC":
            rows.append((st[0], parts[i + 1], parts[i + 2]))
            i += 3
        else:
            rows.append((st[0], parts[i + 1], parts[i + 1]))
            i += 2
    return rows


def mark_of(status: str, old: str, new: str) -> str:
    """파일 한 줄 뒤에 붙는 표지 — 바뀐 «사실»의 종류까지만. 내용은 없다."""
    if status == "A" or status == "C":
        return " (신설)"
    if status == "D":
        return " (삭제)"
    if status == "R" and old != new:
        return " (경로 변경 · 이전 `%s`)" % old
    return ""


# ───────────────────────── 조립

def collect(root: str, since: str, head: str):
    """{갈래: [(경로, 표지)]} — 갈래 순서는 표와 같게, 갈래 안은 경로순."""
    per = {b: [] for b in BRANCH_ORDER}
    for st, old, new in changed_files(root, since, head):
        shown = old if st == "D" else new
        branch = branch_of(shown)
        if branch is None:
            continue
        row = (shown, mark_of(st[0], old, new))
        if row not in per[branch]:
            per[branch].append(row)
    return {b: sorted(v) for b, v in per.items()}


def versions(root: str, head: str):
    out = {}
    for name, _, specs in BRANCHES:
        h = git(root, "log", "-1", "--abbrev=7", "--format=%h", head, "--",
                *specs, ":(exclude)*.html").strip()
        out[name] = h or "—"
    return out


def render(date: str, since7: str, head_full: str, head7: str, vers: dict, points: dict) -> str:
    L = [
        "# 설계 변동 공지",
        "",
        "1. **공지 발행 날짜**: %s" % date,
        "2. **배포 버전**: `%s` (`%s`)" % (head_full, head7),
        "3. **설계 자료 목록** — 저장소 `%s`, 버전은 그 갈래를 마지막으로 바꾼 커밋" % REPO,
        "",
        "| 자료 | 경로 | 버전 |",
        "| --- | --- | --- |",
    ]
    for name, shown, _ in BRANCHES:
        v = ("`%s`" % vers[name]) if vers[name] != "—" else "—"      # 이력이 없는 갈래는 빈 칸(—)
        L.append("| %s | %s | %s |" % (name, shown, v))
    L += ["", "4. **이전 버전(`%s`)과 달라진 지점** — 바뀐 파일, 한 파일이 한 줄" % since7, ""]
    for name in BRANCH_ORDER:
        for path, mark in points[name]:
            L.append("- %s `%s`%s" % (name, path, mark))
    return "\n".join(L) + "\n"


def resolve(root: str, rev: str) -> str:
    out = git(root, "rev-parse", "--verify", "--quiet", rev + "^{commit}", check=False).strip()
    if not out:
        raise GitError("커밋을 찾을 수 없다: %s" % rev)
    return out


def latest_notice_tag(root: str):
    tags = git(root, "tag", "-l", "notice/*", "--sort=-creatordate").split()
    return tags[0] if tags else None


def main() -> int:
    ap = argparse.ArgumentParser(description="설계 변동 공지 초안 생성기")
    ap.add_argument("--since", help="이전 공지 태그 또는 해시(없으면 최신 notice/* 태그)")
    ap.add_argument("--head", default="HEAD", help="공지할 배포 버전(기본 HEAD)")
    ap.add_argument("--out", help="초안 경로(기본 tmp/notices/<날짜>-<해시7>.md)")
    ap.add_argument("--date", help="공지 발행 날짜 YYYY-MM-DD(시험용 오버라이드)")
    ap.add_argument("--repo-root", default=DEFAULT_ROOT, help="저장소 루트(시험용)")
    a = ap.parse_args()

    root = os.path.abspath(a.repo_root)
    if not git_ok(root, "rev-parse", "--git-dir"):
        print("⛔ git 저장소가 아니다: %s" % root)
        return 2

    since_ref = a.since
    if not since_ref:
        since_ref = latest_notice_tag(root)
        if not since_ref:
            print("⛔ 첫 공지다 — `--since` 로 기준 해시를 지정하라 (notice/* 태그가 없다)")
            return 2
    try:
        since = resolve(root, since_ref)
        head = resolve(root, a.head)
    except GitError as e:
        print("⛔ %s" % e)
        return 2
    since7, head7 = since[:7], head[:7]
    if not git_ok(root, "merge-base", "--is-ancestor", since, head):
        print("⚠ %s 는 %s 의 조상이 아니다 — 두 트리의 차이를 그대로 낸다" % (since7, head7),
              file=sys.stderr)

    date = a.date or datetime.date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        print("⛔ --date 는 YYYY-MM-DD 형식이다: %s" % date)
        return 2

    points = collect(root, since, head)
    n = sum(len(rows) for rows in points.values())
    if n == 0:
        print("공지할 것이 없다 — %s..%s 사이에 개발팀 열람 갈래 변경 없음" % (since7, head7))
        return 1

    text = render(date, since7, head, head7, versions(root, head), points)
    out = a.out or os.path.join(root, "tmp", "notices", "%s-%s.md" % (date, head7))
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    shown = os.path.relpath(out, root) if os.path.abspath(out).startswith(root) else out
    print("생성: %s · 지점(파일) %d건 · %s..%s" % (shown, n, since7, head7))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
