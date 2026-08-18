#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 매핑 커버리지 대조 — UI 요구 목록의 액션이 요구서 §3 에 다 있는가.
#
# verify-ui-coverage.py 가 「화면이 무엇을 요구하는가」를 뽑고, 이 스크립트가
# 「요구서가 그것을 다 다뤘는가」를 대조한다. 두 개가 짝이다.
#
# 왜 필요한가
#   요구서의 「전건 소화」는 사람이 세어 주장하는 값이었다. 액션이 109건이면
#   눈으로는 몇 건이 빠져도 모른다. 빠진 액션은 그대로 프론트가 부를 수 없는
#   화면이 된다.
#
# 대조 방법
#   화면별로 요구서 §3 소절을 찾고, 그 소절 매핑표의 **첫 열**에 액션 문구가
#   있는지 본다. 소절 본문 전체를 대조하면 「조회」·「취소」처럼 짧은 액션이
#   산문에 우연히 등장하기만 해도 통과한다 — 매핑표에 없는데 ✅ 가 나온다.
#   요구서는 액션 여러 개를 한 행에 묶어 적으므로(「스캔(암묵) / 직접 입력」)
#   슬래시로 나뉜 조각이 하나라도 있으면 다뤄진 것으로 친다.
#
# 표준 라이브러리만 쓴다(저장소 관행).
import importlib
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# 도메인 등록부는 verify-ui-coverage.py 가 갖는다 — 두 곳에 적으면 갈린다.
sys.path.insert(0, HERE)
_COV = importlib.import_module("verify-ui-coverage")
DOMAINS = {name: (files[1], files[2]) for name, files in _COV.DOMAINS.items()}
DEFAULT_DOMAIN = "mdm"  # 짝인 verify-ui-coverage.py 와 같은 기본값을 쓴다

_LIST_SCREEN = re.compile(r"^## ([WMP]-(?:CO|\d{2})-\d{2})\s*$", re.M)
# ⛔ 번호와 화면 ID 사이에 «꾸밈»이 들어간다 — 실제로 `### 3-8. ⭐ `W-03-10` …` 이
#    있었고, 옛 정규식이 `\s*` 만 허용해 그 소절을 «없는 것»으로 봤다(2026-08-18).
#    그래서 다뤄진 액션 5건이 결손으로 잡혀 게이트가 빨간 채 방치됐다.
#    ⭐ 같은 줄에서 «첫» 백틱 화면 ID 를 집는다 — 백틱이 없는 제목(커버리지 집계)은
#    여전히 안 잡힌다.
_DOC_SCREEN = re.compile(
    r"^### 3-\d+\.[^\n`]*`([WMP]-(?:CO|\d{2})-\d{2})`", re.M)

# 대조에서 지우는 것 — ① 공백과 마크다운 표기(`**` `` ` `` `~~`)는 같은 액션을
# 두 문서가 다르게 꾸며 적어서, ② 판정 기호(⚠⛔✅❌)와 괄호·중점은 요구서가
# 강조·묶음으로 덧붙여서 생기는 차이다. 뜻을 담은 글자는 지우지 않는다.
_NOISE = re.compile(r"[\s·⚠⛔✅❌「」（）()\[\]§*`~]+")
_ACTION_SPLIT = re.compile(r"[/·]")


def _norm(text):
    # 표기 차이를 지운다. 굵게·코드·기호·공백은 대조에 방해만 된다.
    return _NOISE.sub("", text)


def _first_column(block):
    # 표 행의 첫 열만 이어 붙인다. 산문은 대조 대상이 아니다.
    cells = []
    for line in block.split("\n"):
        if not line.startswith("|"):
            continue
        head = line.strip("|").split("|")[0].strip()
        if head and not head.startswith("---"):
            cells.append(head)
    return _norm(" ".join(cells))


def read(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def list_actions(path):
    # 요구 목록에서 [(화면, 액션)] 을 읽는다.
    text = read(path)
    out = []
    screen = None
    for line in text.split("\n"):
        m = _LIST_SCREEN.match(line)
        if m:
            screen = m.group(1)
            continue
        if screen and line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2 and cells[0] not in ("액션",) and not cells[0].startswith("---"):
                out.append((screen, cells[0]))
    return out


def doc_sections(path):
    # 요구서에서 {화면: §3 소절 본문} 을 읽는다.
    text = read(path)
    marks = [(m.group(1), m.start()) for m in _DOC_SCREEN.finditer(text)]
    out = {}
    for i, (screen, start) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(text)
        out[screen] = text[start:end]
    return out


def missing(actions, sections):
    # 다뤄지지 않은 (화면, 액션). 화면 소절 자체가 없으면 그것도 결손이다.
    out = []
    columns = {screen: _first_column(block) for screen, block in sections.items()}
    for screen, action in actions:
        if screen not in columns:
            out.append((screen, action, "요구서에 §3 소절이 없다"))
            continue
        haystack = columns[screen]
        parts = [p for p in _ACTION_SPLIT.split(action) if _norm(p)] or [action]
        if not any(_norm(p) in haystack for p in parts):
            out.append((screen, action, "매핑표 첫 열에 없다"))
    return out


def check(domain):
    # 요구 목록은 openapi/ 아래, 요구서는 deliverables/ 바로 아래다.
    list_name, doc_name = DOMAINS[domain]
    actions = list_actions(os.path.join(HERE, "openapi", list_name))
    sections = doc_sections(os.path.join(HERE, doc_name))
    gaps = missing(actions, sections)

    print("%s — 액션 %d · 요구서 §3 소절 %d" % (domain, len(actions), len(sections)))
    if not gaps:
        print("✅ 전건 다뤘습니다.")
        return 0
    print("⛔ 빠진 액션 %d건" % len(gaps))
    for screen, action, why in gaps:
        print("  %s — %s (%s)" % (screen, action, why))
    return 1


def main():
    domain = DEFAULT_DOMAIN
    if "--domain" in sys.argv:
        domain = sys.argv[sys.argv.index("--domain") + 1]
    if domain not in DOMAINS:
        print("모르는 도메인: %s (%s 중 하나)" % (domain, " · ".join(DOMAINS)))
        return 1
    return check(domain)


if __name__ == "__main__":
    sys.exit(main())
