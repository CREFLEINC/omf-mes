#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""계약의 «오프라인 표기»가 그 오퍼레이션을 부르는 화면의 판정과 같은가.

왜 필요한가
-----------
공유계약 **C-5** 는 「오프라인 허용 여부는 **화면 속성**이고 계약이 목록을
갖는다」로 정해 두었다. 그런데 **옮겨 적은 것이 원본과 같은지를 아무도 보지
않았다** — 같은 형태가 2026-08 에 네 번 났다(C-5-1).

    POST /production/work-sessions        오프라인 대상  ↔  P-02-01 ⛔ 온라인 전용
    POST /production/repair-executions    오프라인 대상  ↔  M-02-02 ⛔ 온라인 전용
    POST /production/operation-handovers  오프라인 대상  ↔  M-02-01 ⛔ 온라인 전용
    POST /logistics/material-issue-requests 오프라인 대상 ↔ W-02-10 ⛔ 해당 없음(관리웹)

⚠ **오프라인 표기가 셋을 함께 끌고 온다** — ① `IfMatchVersionOptional` 완화(C-9)
② 본문 `businessDate` 필수(C-8) ③ 셸 outbox 적재. **표기가 틀리면 셋이 함께
틀린다.**

무엇을 보나
-----------
입력 셋을 맞댄다.

  1. 계약 7벌 — 오퍼레이션의 `description`·`x-internal-note` 에 「오프라인 대상
     오퍼레이션이다」가 있는가(=표기 있음) · `IfMatchVersionOptional` 참조가
     있는가(=완화됨)
  2. 화면→API 매핑 — 요구서 `06-API-요구서-*.md` 의 §3-N 소절
     ⛔ 파서를 새로 쓰지 않는다 — `verify-mapping-coverage.py` 의 `_DOC_SCREEN`
     정규식과 `verify-ui-coverage.DOMAINS` 를 그대로 재사용한다
  3. 화면 판정 — `design/wiki/screens/**/<화면ID>-*.md` 의 「오프라인」 표 행

  ⛔ **위반 A** — 표기가 있는 오퍼레이션인데 그것을 부르는 화면이 **하나도
     오프라인이 아닌** 경우. 종료 코드 1.
  ⚠ **위반 B** — `IfMatchVersionOptional` 을 쓰는데 표기가 어디에도 없는 경우.
     «판단이 필요한 자리»를 드러내는 것이라 종료 코드를 바꾸지 않는다
     (`omf-mes#247` 이 표기를 «의도적으로» 걷고 완화만 남긴 자리가 있다).

⚠ 이 검사기가 못 보는 것
------------------------
  - 요구서 §3-N 에 매핑이 «없는» 오퍼레이션은 아예 안 본다
    (`POST /production/material-returns` 가 그 예다)
  - `logistics-01자재창고.json` 은 표기를 `x-internal-note` 에 · 나머지 계약은
    `description` 에 둔다. 이 검사기는 둘 다 보지만 **어느 쪽이 옳은 자리인지는
    판정하지 않는다**
  - 화면 스펙의 오프라인 표기 «어휘»가 통일돼 있지 않다 — 문자열 매칭이라
    **새 어휘가 생기면 놓친다.** 그래서 판정을 셋으로 둔다(오프라인·온라인·모름)
    이고, «모름»만 있는 자리는 위반 A 로 세지 않는다
  - 화면이 실제로 outbox 에 담는지 — 구현 소관이다

쓰기
----
    python3 design/schema/generators/openapi/check-offline-consistency.py
"""
from __future__ import annotations

import collections
import glob
import importlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.normpath(os.path.join(HERE, ".."))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
# Tier 0 — OpenAPI JSON 정본. Phase 5 컷오버(2026-08-25)로 design/wiki/api-contracts/openapi/가 정본 위치다.
CONTRACTS_DIR = os.path.join(ROOT, "design", "wiki", "api-contracts", "openapi")
DOCS_DIR = os.path.join(ROOT, "design", "wiki", "api-contracts")
SCREENS_DIR = os.path.join(ROOT, "design", "wiki", "screens")

# ⛔ 매핑 파서를 새로 쓰지 않는다 — 두 곳에 적으면 갈린다.
sys.path.insert(0, GEN)
_MC = importlib.import_module("verify-mapping-coverage")

MARK = "오프라인 대상 오퍼레이션이다"
# ⛔ 「…」 안에 든 것은 «인용»이지 표기가 아니다. 2026-08-29 PR #288 리뷰에서 드러났다 —
#    /production/operation-handovers 는 description 이 이미 「⛔ 오프라인 대상이 아니다」
#    인데, x-internal-note 가 client#102 근거를 옮겨 적으며 상용구를 「」 안에 인용했고
#    검사기가 그것을 표기로 세어 위반으로 냈다(오탐).
QUOTED_MARK = "「" + MARK + "」"


def marked(text: str) -> bool:
    """상용구가 «표기»로 쓰였나 — 인용은 세지 않는다."""
    return MARK in text.replace(QUOTED_MARK, "")
OPTIONAL_LOCK = "IfMatchVersionOptional"
HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")

CALL = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+(/[A-Za-z0-9_{}/:.\-]+)")
OFFLINE_ROW = re.compile(r"^\|\s*\**\s*오프라인\s*\**\s*\|")
# 「오프라인이 아니다」쪽 어휘. ⚠ 통일돼 있지 않아 문자열로 센다.
ONLINE_WORDS = ("해당 없음", "온라인 전용", "금지", "진입 차단", "규약 밖")


def norm(path: str) -> str:
    """경로 파라미터 «이름»의 차이를 지운다(요구서와 계약이 달리 적는다)."""
    return re.sub(r"\{[^}]*\}", "{}", path.rstrip(".,·"))


def contract_ops():
    """계약 7벌 → {(정규경로, 메서드): {파일·경로·표기·완화}}."""
    out = {}
    for f in sorted(glob.glob(os.path.join(CONTRACTS_DIR, "*.json"))):
        name = os.path.basename(f)
        with open(f, encoding="utf-8") as fh:
            doc = json.load(fh)
        for path, item in (doc.get("paths") or {}).items():
            if not isinstance(item, dict):
                continue
            for method in [m for m in item if m.lower() in HTTP_METHODS]:
                op = item[method]
                if not isinstance(op, dict):
                    continue
                text = (op.get("description") or "") + "\n" + str(op.get("x-internal-note") or "")
                refs = {p.get("$ref", "").split("/")[-1]
                        for p in list(item.get("parameters") or []) + list(op.get("parameters") or [])
                        if isinstance(p, dict)}
                out[(norm(path), method.upper())] = {
                    "file": name, "path": path,
                    "marked": marked(text),
                    "relaxed": OPTIONAL_LOCK in refs,
                }
    return out


def doc_callers():
    """요구서 §3-N → {(정규경로, 메서드): {화면 ID}}."""
    out = collections.defaultdict(set)
    for _domain, (_list_name, doc_name) in _MC.DOMAINS.items():
        doc_path = os.path.join(DOCS_DIR, doc_name)
        if not os.path.exists(doc_path):
            continue
        for screen, block in _MC.doc_sections(doc_path).items():
            for method, raw in CALL.findall(block):
                out[(norm(raw), method.upper())].add(screen)
    return out


def screen_verdict(screen: str) -> str:
    """화면 스펙의 오프라인 판정 — 'offline' · 'online' · 'unknown'."""
    hits = glob.glob(os.path.join(SCREENS_DIR, "*", "%s-*.md" % screen))
    if not hits:
        return "unknown"
    for path in sorted(hits):
        with io.open(path, encoding="utf-8") as fh:
            for line in fh:
                if not OFFLINE_ROW.match(line.strip()):
                    continue
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) < 2:
                    continue
                cell = cells[1]
                return "online" if any(w in cell for w in ONLINE_WORDS) else "offline"
    return "unknown"


def main() -> int:
    ops = contract_ops()
    callers = doc_callers()

    violation_a, violation_b, unreadable = [], [], []
    marked = 0

    for key, info in sorted(ops.items(), key=lambda kv: (kv[1]["file"], kv[0])):
        screens = sorted(callers.get(key) or ())
        if info["marked"]:
            marked += 1
            if not screens:
                continue                       # 매핑이 없는 자리는 안 본다
            verdicts = {s: screen_verdict(s) for s in screens}
            if any(v == "offline" for v in verdicts.values()):
                continue
            if any(v == "online" for v in verdicts.values()):
                violation_a.append((info["file"], key[1], info["path"], verdicts))
            else:
                unreadable.append((info["file"], key[1], info["path"], verdicts))
        elif info["relaxed"]:
            violation_b.append((info["file"], key[1], info["path"], screens))

    print("계약 오퍼레이션 %d개 검사 — 오프라인 표기 %d자리 · 요구서 매핑 %d자리"
          % (len(ops), marked, len(callers)))
    print()

    if violation_a:
        print("⛔ 위반 A — 계약은 「오프라인 대상」이라 적었는데 부르는 화면이 "
              "하나도 오프라인이 아닙니다 %d건 (공유계약 C-5-1)\n" % len(violation_a))
        for f, m, p, verdicts in violation_a:
            print("   %-26s %-6s %s" % (f, m, p))
            for s, v in sorted(verdicts.items()):
                print("   %-26s %-6s   ↳ %s = %s" % ("", "", s, v))
        print("\n   ⭐ 정본은 화면 스펙의 §1 식별표·§6 예외표다. 계약은 그 판정을\n"
              "      «옮겨 적을» 뿐 새로 판정하지 않는다.\n"
              "   ⚠ 지울 때 「오프라인 대상이 아니다 ＋ 왜」를 남긴다 — 지우기만 하면\n"
              "      다음 판에서 상용구가 되돌아온다.\n"
              "   ⛔ 형제 오퍼레이션(…/events·/workers·:leave·:end)도 함께 본다.\n")

    if unreadable:
        print("ℹ  화면 판정을 못 읽어 A 로 세지 않은 자리 %d건 — 어휘가 새로 생겼을 수 있다"
              % len(unreadable))
        for f, m, p, verdicts in unreadable:
            print("   %-26s %-6s %-46s %s"
                  % (f, m, p[:46], " · ".join("%s=%s" % kv for kv in sorted(verdicts.items()))))
        print()

    if violation_b:
        print("⚠ 위반 B — `IfMatchVersionOptional` 로 완화했는데 오프라인 표기가 없습니다 "
              "%d건 (EXIT 를 바꾸지 않는다 — 판단이 필요한 자리다)\n" % len(violation_b))
        for f, m, p, screens in violation_b:
            print("   %-26s %-6s %-46s %s"
                  % (f, m, p[:46], "·".join(screens) if screens else "(요구서 매핑 없음)"))
        print("\n   ⭐ 둘 중 하나다 — ⓐ 표기를 되살린다 ⓑ 완화가 다른 근거를 갖는다\n"
              "      (`omf-mes#247` 은 ⓑ 로 «의도적으로» 표기를 걷은 자리다).\n")

    if violation_a:
        print("⛔ 막는 항목 %d건" % len(violation_a))
        return 1
    print("✅ 오프라인 표기가 화면 판정과 어긋난 자리 0건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
