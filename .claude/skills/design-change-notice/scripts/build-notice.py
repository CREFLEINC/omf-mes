#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""설계 변동 공지 초안 생성기 — 직전 공지(태그) → HEAD 사이의 «달라진 지점»을 뽑는다.

왜 생성기인가
-------------
V3(2026-09-03) 규칙 5 — 공지는 「변동 사항이 있다는 사실」만 알린다. 「무슨 내용이 어떻게
변경되었는지 작성하지마라」. 손으로 초안을 쓰면 내용이 섞인다 — 쓰는 사람이 바로 그 변경을 한
사람이라 «왜 바꿨는지»가 손끝에 남아 있기 때문이다. 그래서 초안은 **git 이력에서 기계가 뽑는다.**
생성기는 값·문장·diff 본문을 «읽되 옮기지 않는다» — 이름·키·절 제목까지만 낸다.

무엇을 뽑나 — 「달라진 지점」의 입자
------------------------------------
  화면설계서     파일명의 화면 ID + 바뀐 절(`##`/`###` 제목의 §n·§n-m 토큰)
  API 요구서     갈래 이름(03품질 · 본편 …) + 바뀐 절
  API 계약서     paths.<경로>.<메서드> · components.schemas.<이름> · 그 밖의 components.<type>.<이름>
                 (양쪽 버전을 json.loads 해 서브트리를 비교한다 — 텍스트 diff 가 아니다)
  코드 사전      바뀐 행의 `CD-*` 키
  공유계약       바뀐 절
  사양서·요구사항 파일 이름 + 바뀐 절

  ⛔ 값·문장·diff 본문은 절대 옮기지 않는다. 신설 파일은 「(신설)」, 삭제는 「(삭제)」 — 절 없이.
  ⛔ 갈래 6줄에 속하지 않는 파일(검사기·규약·handover/·.html 배포본)은 싣지 않는다 — 개발팀
     열람 대상이 아니다.

갈래 분류 규칙은 `design/schema/generators/build-change-digest.py` 의 `where()` 와 같다
(경로 → 화면/계약/요구서/공유계약/코드 사전/사양서). 그 함수를 import 하지 않는 이유 —
이 생성기는 `--repo-root` 로 임의 저장소(시험용 임시 저장소 포함)에서 돌아야 하고, 「달라진
지점」은 `where()` 보다 한 단계 아래 입자라 대부분을 직접 구현하게 된다.

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
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
REPO = "CREFLEINC/omf-mes"
LINE_MAX = 160          # 4항 한 항목의 길이 상한 — check-notice.py N5 와 같은 수

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

SCREEN_ID = re.compile(r"[WMP]-(?:CO|\d{2})-\d{2}")
CD_KEY = re.compile(r"CD-[A-Z0-9]+(?:-[A-Z0-9]+)*")
HEADING = re.compile(r"^(#{2,3})\s+(.*?)\s*$")
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
METHODS = ("get", "post", "put", "patch", "delete", "head", "options", "trace")

# 절 토큰 — 제목 «머리»의 §n·§n-m·§n.m(§4-A·§I-11 도) 또는 번호(3-1. · 1.1 · A-4 · REQ-PR-0001 · L1)
SECT = re.compile(r"§[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)*")
GLYPHS = "⭐⚠⛔✅✓✗❌🔒·"
LEAD = re.compile(
    r"^[\s" + GLYPHS + r"]*("
    r"[A-Z]{1,4}(?:-[A-Z]{1,4})?-\d+(?:-\d+)*"     # REQ-PR-0001 · DR-008
    r"|[A-Z]-\d+(?:-\d+)*"                         # A-4 · A-4-1
    r"|[A-Z]\d+"                                   # L1
    r"|\d+(?:[.-]\d+)*"                            # 3 · 3-1 · 1.1 · 3.2.1
    r")\.?(?=\s|$)")
SECT_AT_HEAD = re.compile(r"^[\s" + GLYPHS + r"]*(" + SECT.pattern + r")")


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


def label_of(branch: str, path: str) -> str:
    """갈래 안에서 이 파일을 부르는 이름 — 4항 항목의 「갈래 [이름]」 자리."""
    base = os.path.basename(path)
    stem = re.sub(r"\.(?:md|json)$", "", base)
    if branch == "화면설계서":
        m = SCREEN_ID.search(base)
        return "`%s`" % (m.group(0) if m else stem)
    if branch == "API 계약서":
        return stem.split("-", 1)[-1]                        # quality-03품질 → 03품질
    if branch == "API 요구서":
        return stem.replace("06-API-요구서", "").lstrip("-") or "본편"
    if branch in ("코드 사전", "공유계약"):
        return ""                                            # 파일이 하나뿐이라 이름을 되풀이하지 않는다
    return "`%s`" % stem                                     # 사양서·요구사항


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


# ───────────────────────── .md — 바뀐 절

def headings_of(text: str):
    """[(행번호, 제목)] — `##`/`###` 만. 코드 펜스 안의 「제목」은 세지 않는다."""
    rows, fence = [], False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        m = HEADING.match(line)
        if m:
            rows.append((n, m.group(2)))
    return rows


def hunk_starts(diff_text: str):
    return [int(m.group(1)) for m in (HUNK.match(l) for l in diff_text.splitlines()) if m]


def clean_title(title: str) -> str:
    """절 토큰이 없는 제목 — 부제·강조·화살표·콜론을 걷어 «이름»만 남긴다(80자)."""
    t = re.sub(r"\*+|~~", "", title)                         # 강조·취소선 표식만 — `~`·`_` 는 제목의 일부일 수 있다
    t = re.sub(r"^[\s" + GLYPHS + r"]+", "", t)
    t = re.split(r"\s[—–]\s", t, 1)[0]                     # 「— 부제」는 설명이다
    t = re.sub(r"\s*(?:→|->|=>|←|↔)\s*", " · ", t)
    t = t.replace(":", "")
    t = re.sub(r"\s+", " ", t).strip()
    return t[:80]


def section_token(title: str) -> str:
    """제목 → 지점 이름. §토큰 › 머리 번호 › 본문 어딘가의 §토큰 › 제목 전문(정제)."""
    m = SECT_AT_HEAD.match(title)
    if m:
        return m.group(1)
    m = LEAD.match(title)
    if m:
        tok = m.group(1)
        return ("§" + tok) if tok[0].isdigit() else tok
    m = SECT.search(title)
    if m:
        return m.group(0)
    return clean_title(title) or "(제목 없음)"


def nearest_headings(root: str, since: str, head: str, old: str, new: str):
    """(diff 본문, [(행, 제목 | None)…]) — 바뀐 hunk 마다 그 위로 가장 가까운 절 제목.
    문서 순서, 중복 제거. 제목이 없으면 None(머리말). hunk 가 없으면 빈 목록."""
    diff = git(root, "diff", "-U0", "%s:%s" % (since, old), "%s:%s" % (head, new))
    starts = hunk_starts(diff)
    if not starts:
        return diff, []
    heads = headings_of(git(root, "show", "%s:%s" % (head, new)))
    found = []
    for s in starts:
        above = [(n, t) for n, t in heads if n <= s]
        key = above[-1] if above else (0, None)
        if key not in found:
            found.append(key)
    found.sort()
    return diff, found


def md_sections(root: str, since: str, head: str, old: str, new: str):
    """바뀐 hunk 마다 그 위로 가장 가까운 절 제목 → 지점 목록(문서 순서, 중복 제거)."""
    _, found = nearest_headings(root, since, head, old, new)
    if not found:
        return ["(변경)"] if old == new else ["(경로 변경)"]
    return [section_token(t) if t is not None else "(머리말)" for _, t in found]


# ───────────────────────── 계약 JSON — 키 단위 비교

def contract_points(root: str, since: str, head: str, old: str, new: str):
    try:
        a = json.loads(git(root, "show", "%s:%s" % (since, old)))
        b = json.loads(git(root, "show", "%s:%s" % (head, new)))
    except (ValueError, GitError):
        return ["(JSON 해석 불가)"]
    items = []

    pa, pb = a.get("paths") or {}, b.get("paths") or {}
    for p in sorted(set(pa) | set(pb)):
        oa, ob = pa.get(p) or {}, pb.get(p) or {}
        for m in METHODS:
            if m in oa or m in ob:
                mark = _mark(m in oa, m in ob)
                if mark or oa[m] != ob[m]:
                    items.append("`%s %s`%s" % (m.upper(), p, mark))
        if p in pa and p in pb:                               # 경로 자체가 신설·삭제면 메서드 줄이 이미 말한다
            ka = {k: v for k, v in oa.items() if k not in METHODS}
            kb = {k: v for k, v in ob.items() if k not in METHODS}
            if ka != kb:
                items.append("`%s`" % p)                      # 경로 공통(parameters 등)

    ca, cb = a.get("components") or {}, b.get("components") or {}
    for typ in sorted(set(ca) | set(cb)):
        ta, tb = ca.get(typ) or {}, cb.get(typ) or {}
        word = "스키마" if typ == "schemas" else typ
        for name in sorted(set(ta) | set(tb)):
            mark = _mark(name in ta, name in tb)
            if mark or ta[name] != tb[name]:
                items.append("%s `%s`%s" % (word, name, mark))

    for k in sorted(set(a) | set(b)):
        if k in ("paths", "components"):
            continue
        if a.get(k) != b.get(k):
            items.append("`%s`" % k)
    return items or ["(변경)"]


def _mark(in_old: bool, in_new: bool):
    if in_old and in_new:
        return ""
    return "(신설)" if in_new else "(삭제)"


# ───────────────────────── 코드 사전 — 바뀐 CD-* 키

def dictionary_points(root: str, since: str, head: str, old: str, new: str):
    """바뀐 줄에 든 `CD-*` 키 + 바뀐 hunk 위의 절 제목에 든 키. 키가 하나도 없으면 절 단위."""
    diff, found = nearest_headings(root, since, head, old, new)
    keys = set()
    for line in diff.splitlines():
        if (line.startswith("+") or line.startswith("-")) \
                and not line.startswith("+++") and not line.startswith("---"):
            keys.update(CD_KEY.findall(line))
    for _, title in found:
        if title:
            keys.update(CD_KEY.findall(title))
    if keys:
        return ["`%s`" % k for k in sorted(keys)]
    return md_sections(root, since, head, old, new)


# ───────────────────────── 조립

def collect(root: str, since: str, head: str):
    """{갈래: [(이름, [지점…])]} — 갈래 순서는 표와 같게, 갈래 안은 이름순."""
    per = {b: {} for b in BRANCH_ORDER}
    for st, old, new in changed_files(root, since, head):
        branch = branch_of(new)
        if branch is None:
            continue
        label = label_of(branch, new)
        if st == "A":
            pts = ["(신설)"]
        elif st == "D":
            pts = ["(삭제)"]
        elif branch == "API 계약서":
            pts = contract_points(root, since, head, old, new)
        elif branch == "코드 사전":
            pts = dictionary_points(root, since, head, old, new)
        else:
            pts = md_sections(root, since, head, old, new)
        bucket = per[branch].setdefault(label, [])
        for p in pts:
            if p not in bucket:
                bucket.append(p)
    return {b: sorted(v.items()) for b, v in per.items()}


def wrap_items(prefix: str, items: list) -> list:
    """한 항목이 LINE_MAX 를 넘으면 같은 머리로 줄을 나눈다 — 항목은 «지점 목록»이지 설명이 아니다."""
    lines, cur = [], []
    for it in items:
        cand = prefix + " · ".join(cur + [it])
        if cur and len(cand) > LINE_MAX:
            lines.append(prefix + " · ".join(cur))
            cur = [it]
        else:
            cur.append(it)
    if cur:
        lines.append(prefix + " · ".join(cur))
    return lines


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
    L += ["", "4. **이전 버전(`%s`)과 달라진 지점**" % since7, ""]
    for name in BRANCH_ORDER:
        for label, pts in points[name]:
            prefix = "- %s%s — " % (name, (" " + label) if label else "")
            L += wrap_items(prefix, pts)
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
    n = sum(len(p) for rows in points.values() for _, p in rows)
    if n == 0:
        print("공지할 것이 없다 — %s..%s 사이에 개발팀 열람 갈래 변경 없음" % (since7, head7))
        return 1

    text = render(date, since7, head, head7, versions(root, head), points)
    out = a.out or os.path.join(root, "tmp", "notices", "%s-%s.md" % (date, head7))
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    shown = os.path.relpath(out, root) if os.path.abspath(out).startswith(root) else out
    print("생성: %s · 지점 %d건 · %s..%s" % (shown, n, since7, head7))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
