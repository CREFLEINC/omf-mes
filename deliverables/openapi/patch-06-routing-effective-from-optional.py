#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Routing 의 유효 시작일을 «선택» 으로 되돌린다 — 결정 07 그대로. 멱등.

무엇을 고치나
-------------
  Routing · RoutingCreate · RoutingUpdate   required 에서 effectiveFrom 삭제
  Routing.description                        「하류를 따른다」 문장 제거 + 내부 주석으로 이관

왜 — 설계가 확정을 뒤집고 있었다
--------------------------------
✓설계확정 **결정 07**(2026-07-06 CTO)이 Routing 헤더 속성으로 「**유효 시작일
(선택)**」을 정했다. 그런데 화면 스펙이 「물리 모델이 `NOT NULL` 이니 화면은
하류를 따른다」로 **필수로 뒤집었고**, 그 논리를 「제약은 하류가 정본」이라는
**원칙으로 적어** 두었다(`W-06-01` §8-3 · §9-2 후보 2번). 계약이 그것을 그대로
받아 `required` 에 넣었다.

⛔ **사용자 확정(2026-08-18)** — 물리 데이터 모델은 설계 결정을 앞설 수 없고,
설계 단계에서 물리 모델 자료를 참조하지 않는다. → **결정 07 이 이긴다.**

⚠ 주어를 넘겨 적용하지 않는다
-----------------------------
`effectiveFrom` 은 계약 9곳에서 필수다. 그중 **Routing 계열 셋만** 고친다 —
결정 07 의 주어가 **Routing** 이기 때문이다. 품목 단위 환산 · 사업부 품목 매핑 ·
BOM · 검사기준 버전은 결정 07 이 말한 적이 없으므로 **건드리지 않는다.**

⚠ 등급 — «넓어지는» 변경이다
----------------------------
필수를 푸는 것이라 이미 만든 것이 깨지지 않는다(늘 보내던 쪽은 그대로 통한다).
다만 화면이 「필수」로 표시하고 있으면 그것이 틀리므로 ⚠ 변경 통지 대상이다.
⛔ 이 화면은 **이미 구현돼 병합된 화면**이라 착수 통지를 보내지 않는 대상이다.

description 은 공개된다
-----------------------
「하류를 따른다」 문장은 **틀린 데다 공개**된다(구현팀이 JSDoc 으로 공개
저장소에 커밋한다). 지우고, 남길 값어치가 있는 부분은 `x-internal-note` 로
옮긴다.

쓰기
----
    python3 deliverables/openapi/patch-06-routing-effective-from-optional.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "mdm-기준정보.json")

TARGETS = ("Routing", "RoutingCreate", "RoutingUpdate")

STALE_MARK = "하류를 따른다"

PUBLIC_DESC = (
    "공정 순서(Routing) 헤더. 품목과 개정 번호로 한 건이 정해지며 상태는 "
    "작성중·확정·폐기다. 유효 시작일은 «선택»이다 — 비워 두면 시작 제한이 없다."
)

INTERNAL_NOTE = (
    "① 기본 개정(default Rev) 플래그가 모델에 없어 :set-default 오퍼레이션이 "
    "성립하지 않는다. 유효 기간이 겹치는 개정이 둘일 때 어느 것을 쓸지 정할 수 없다 "
    "— 📨 작업 통지 대상(#64). "
    "② effectiveFrom 은 ✓설계확정 결정 07 이 「선택」이라 했고 «그것이 정본이다». "
    "앞서 「모델이 NOT NULL 이니 하류를 따른다」로 필수로 두었던 것을 2026-08-18 "
    "되돌렸다 — 물리 모델은 설계 결정을 앞설 수 없다(사용자 확정). 모델의 NOT NULL 은 "
    "우리를 막지 않으며 작업 통지로 넘긴다."
)


def detect_indent(original: str, doc: dict) -> int | None:
    body = original.rstrip("\n")
    for candidate in (1, 2, 4):
        if json.dumps(doc, ensure_ascii=False, indent=candidate) == body:
            return candidate
    return None


def main() -> int:
    original = open(CONTRACT, encoding="utf-8").read()
    doc = json.loads(original)
    indent = detect_indent(original, doc)
    if indent is None:
        print("⛔ 원본 들여쓰기를 알아낼 수 없다 — 덮어쓰지 않는다", file=sys.stderr)
        return 1
    tail = original[len(original.rstrip("\n")):]

    schemas = doc["components"]["schemas"]
    for dep in TARGETS:
        if dep not in schemas:
            print(f"⛔ 의존 스키마가 없다: {dep}", file=sys.stderr)
            return 1

    changed = []

    # ── ① 결정 07 그대로 «선택» 으로
    for name in TARGETS:
        s = schemas[name]
        if "effectiveFrom" in s.get("required", []):
            s["required"] = [k for k in s["required"] if k != "effectiveFrom"]
            changed.append(f"{name}.required 에서 effectiveFrom 삭제")

    # ── ② 공개 설명문에서 틀린 문장을 걷고 내부 주석으로 옮긴다
    routing = schemas["Routing"]
    if STALE_MARK in routing.get("description", ""):
        routing["description"] = PUBLIC_DESC
        changed.append("Routing.description — 「하류를 따른다」 제거")
    if routing.get("x-internal-note") != INTERNAL_NOTE:
        routing["x-internal-note"] = INTERNAL_NOTE
        changed.append("Routing.x-internal-note 갱신")

    if not changed:
        print("✅ 이미 반영돼 있다 — 바꾼 것 없음 (멱등)")
        return 0

    open(CONTRACT, "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=indent) + tail
    )
    for line in changed:
        print(f"  · {line}")
    print(f"✅ {len(changed)}곳 반영 — {os.path.basename(CONTRACT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
