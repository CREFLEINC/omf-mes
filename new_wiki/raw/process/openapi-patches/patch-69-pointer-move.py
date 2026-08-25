#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`#69` 를 가리키는 내부 주석 네 곳을 정리한다 — 그 이슈를 닫기 전 선행 작업. 멱등.

왜 필요한가
-----------
`omf-mes#69`(사용자 인증 수단 부재 · 권한의 「법인」 축 부재)를 닫으려는데,
**계약이 그 번호를 네 곳에서 가리키고 있다.** 그냥 닫으면 공개 계약에
**없는 이슈를 가리키는 주석**이 남는다.

⛔ 둘은 «전제가 죽었고» 둘은 «번호만 바뀐다» — 처리가 다르다.

    법인 축 2곳   DR-002 2-C 가 「권한 범위에 법인 축을 두지 않는다」로 확정했다.
                  요구 자체가 사라졌으므로 «주석을 지운다».
    인증 2곳      요구는 살아 있고 #155 §1 이 더 넓게 이어받았다.
                  «번호를 #155 로 바꾼다».

⚠ 셋째 자리(`/app/users/{appUserId}` 조회)는 «#69 와 B-4 를 함께» 적는다.
`#69` 부분만 갈고 B-4(참조 건수를 응답에 담는다) 서술은 그대로 둔다.

⭐ 이 주석은 `x-internal-note` 라 공개 문서에 안 나간다(`description` 이 아니다).
그래도 고치는 이유는 **우리가 그 번호로 결손을 되짚기 때문**이다.

⛔⛔ 그런데 «공개되는» description 두 곳도 같은 번호를 쓰고 있었다
--------------------------------------------------------------
`/mdm/legal-entities` 와 `LegalEntity` 가 이렇게 적는다 —

    「법인 축 부재(#69)가 «해소되면» 데이터 접근범위가 첫 사용처가 된다」

**DR-002 2-C 는 그 축을 두지 «않기로» 확정했다.** 즉 이 문장은 오지 않을 일을
기다린다고 공개 계약이 말하는 것이다. 번호를 옮기는 문제가 아니라 **뜻이
반대인 문장**이라 함께 고친다.

⚠ 확정은 2026-08-10 인데 계약은 그대로였다 — 「확정이 하류에 안 퍼진다」가
비공개 문서만의 문제가 아니라는 실증이다.

쓰기
----
    python3 deliverables/openapi/patch-69-pointer-move.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "mdm-기준정보.json")

# (자리, 옛 조각, 새 조각) — 옛 조각이 없으면 이미 반영된 것으로 본다.
MOVES = [
    ("법인 축(legal_entity_id) 부재 — #69",
     "법인 축(legal_entity_id)을 두지 않는다 — DR-002 2-C 확정(2026-08-10). "
     "권한 범위는 창고·공정 축으로만 가른다"),
    ("인증 수단(password_hash·last_login_at·failed_login_count) 전무 — #69",
     "인증 수단(password_hash·last_login_at·failed_login_count) 전무 — #155 §1"),
    ("미착지 #69 /", "미착지 #155 §1 /"),
    # ⛔ 공개 description — 뜻이 반대라 문장째 바꾼다
    ("W-CO-02 §9-3 의 법인 축 부재(#69)가 해소되면 데이터 접근범위가 첫 사용처가 된다",
     "「법인」 축은 권한 범위에 두지 않기로 확정됐다(DR-002 2-C · 2026-08-10) — "
     "접근범위는 창고·공정 축으로만 가른다. 따라서 이 자원은 이름 풀이 전용으로 "
     "남는다"),
]


def detect_indent(original: str, doc: dict) -> int | None:
    body = original.rstrip("\n")
    for candidate in (1, 2, 4):
        if json.dumps(doc, ensure_ascii=False, indent=candidate) == body:
            return candidate
    return None


def walk(node, fn):
    if isinstance(node, dict):
        for k, v in list(node.items()):
            if k in ("x-internal-note", "description") and isinstance(v, str):
                node[k] = fn(v)
            else:
                walk(v, fn)
    elif isinstance(node, list):
        for v in node:
            walk(v, fn)


def main() -> int:
    original = open(CONTRACT, encoding="utf-8").read()
    doc = json.loads(original)
    indent = detect_indent(original, doc)
    if indent is None:
        print("⛔ 원본 들여쓰기를 알아낼 수 없다 — 덮어쓰지 않는다", file=sys.stderr)
        return 1
    tail = original[len(original.rstrip("\n")):]
    was_sorted = list(doc["paths"]) == sorted(doc["paths"])

    hits = {old: 0 for old, _ in ((m[0], m[1]) for m in MOVES)}

    def fix(text: str) -> str:
        for old, new in MOVES:
            if old in text:
                hits[old] += text.count(old)
                text = text.replace(old, new)
        return text

    walk(doc, fix)

    if was_sorted:
        doc["paths"] = dict(sorted(doc["paths"].items()))
    updated = json.dumps(doc, ensure_ascii=False, indent=indent) + tail

    if updated == original:
        print("  이미 반영돼 있다 — 변경 없음")
        return 0

    # 남은 #69 가 없는지 확인한다 — 있으면 닫으면 안 된다
    open(CONTRACT, "w", encoding="utf-8").write(updated)
    left = updated.count("#69")
    for old, n in hits.items():
        print(f"  · {n}곳  {old[:52]}…")
    print(f"  ✅ 옮겼다 — 남은 «#69» 참조 {left}건")
    return 0 if left == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
