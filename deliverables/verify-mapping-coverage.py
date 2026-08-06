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
#   화면별로 요구서 §3 소절을 찾고, 그 소절 안에 액션 문구가 있는지 본다.
#   요구서는 액션 여러 개를 한 행에 묶어 적으므로(「스캔(암묵) / 직접 입력」)
#   슬래시로 나뉜 조각이 하나라도 있으면 다뤄진 것으로 친다.
#
# 표준 라이브러리만 쓴다(저장소 관행).
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOMAINS = {
    "mdm": ("openapi/ui-요구목록.md", "06-API-요구서.md"),
    "01": ("openapi/ui-요구목록-01자재창고.md", "06-API-요구서-01자재창고.md"),
}

_LIST_SCREEN = re.compile(r"^## ([WMP]-(?:CO|\d{2})-\d{2})\s*$", re.M)
_DOC_SCREEN = re.compile(r"^### 3-\d+\.\s*`([WMP]-(?:CO|\d{2})-\d{2})`", re.M)
_NOISE = re.compile(r"[\s·⚠⛔✅❌「」（）()\[\]§*`~]+")


def _norm(text):
    # 표기 차이를 지운다. 굵게·코드·기호·공백은 대조에 방해만 된다.
    return _NOISE.sub("", text)


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
    for screen, action in actions:
        block = sections.get(screen)
        if block is None:
            out.append((screen, action, "요구서에 §3 소절이 없다"))
            continue
        haystack = _norm(block)
        parts = [p for p in re.split(r"[/·]", action) if _norm(p)]
        if not any(_norm(p) in haystack for p in parts or [action]):
            out.append((screen, action, "소절 안에 없다"))
    return out


def check(domain):
    rel_list, rel_doc = DOMAINS[domain]
    actions = list_actions(os.path.join(HERE, rel_list))
    sections = doc_sections(os.path.join(HERE, rel_doc))
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
    domain = "01"
    if "--domain" in sys.argv:
        domain = sys.argv[sys.argv.index("--domain") + 1]
    if domain not in DOMAINS:
        print("모르는 도메인: %s (%s 중 하나)" % (domain, " · ".join(DOMAINS)))
        return 1
    return check(domain)


if __name__ == "__main__":
    sys.exit(main())
