#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""공개 `description` 에서 «비공개 문서 이름»만 걷어 `x-internal-note` 로 옮긴다. 멱등.

왜 필요한가
-----------
구현팀이 물었다(`omf-mes-client#102`) — 그쪽 경계 검사기가 «경로 형태»는
잡는데 **맨 문서명 표기**는 통과시킨다. 실물이 생성물에 실려 있고 출처가
**우리 계약의 `description`** 이다.

    「… 근거: 없음 — 이 10화면 중 어느 화면도 직접 쓰지 않는다(06-API-요구서 §4-3)」

⭐ 판단 — **정본(우리)을 고친다.** 그쪽 검사기에 패턴을 먼저 더하면 우리
description 이 걸려 코드 생성이 깨진다. 정본이 먼저 정리돼야 검사기를
조일 수 있다 — 구현팀 판단이 맞다.

⛔⛔ 무엇을 «안» 옮기는가가 더 중요하다
--------------------------------------
처음에 「근거: …」 꼬리를 통째로 옮기게 썼다가 **314곳·781줄**이 바뀌었다.
구현팀이 말한 것은 **1건**이다. 되돌리고 대상을 좁혔다.

    ✅ 남긴다  화면 ID + 절     `근거: W-06-02 §4-A`
              → 공개 저장소 규약이 화면 ID 를 «명시적으로 허용»한다
    ✅ 남긴다  공유계약 조항 번호  `공유계약 B-1`
              → 번호만 부르고 조항 «내용»은 안 옮긴다. 규약이 요구하는 형태다
    ⛔ 걷는다  문서 «파일명» 형태  `06-API-요구서 §4-3` · `01 요구서 §7`
              → 비공개 저장소의 «파일 구조»가 드러난다. 번호가 아니다

⚠ 뜻은 하나도 안 버린다 — 걷은 표기를 `x-internal-note` 로 옮긴다. 구현팀은
우리 비공개 문서를 어차피 못 읽으므로 공개 쪽에서 잃는 것이 없다.

쓰기
----
    python3 deliverables/openapi/patch-public-doc-refs.py
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ⛔ 문서 «파일명» 형태만. 화면 ID(W-·P-·M-)와 「공유계약 X-N」은 대상이 아니다.
DOC_NAME = re.compile(
    r"\s*[(·]?\s*(?:\d\d[\s\-]?)?API[\s\-]?요구서[\w가-힣\-]*\s*§[\d\-A-Za-z]+\)?"
    r"|\s*[(·]?\s*\d\d\s요구서\s*§[\d\-A-Za-z]+\)?"
    r"|\s*[(·]?\s*\d\d\s계약\s\d단계\s*§[\d\-A-Za-z]+\)?")
MARK = " ⧉ 공개 설명에서 걷은 근거 표기(client#102 · 2026-08-12): "


def detect_indent(original: str, doc: dict) -> int | None:
    body = original.rstrip("\n")
    for c in (1, 2, 4):
        if json.dumps(doc, ensure_ascii=False, indent=c) == body:
            return c
    return None


def main() -> int:
    total = 0
    for path in sorted(glob.glob(os.path.join(HERE, "*.json"))):
        original = open(path, encoding="utf-8").read()
        doc = json.loads(original)
        indent = detect_indent(original, doc)
        if indent is None:
            print(f"⛔ {os.path.basename(path)} — 들여쓰기 불명", file=sys.stderr)
            return 1
        tail = original[len(original.rstrip("\n")):]
        was_sorted = list(doc.get("paths", {})) == sorted(doc.get("paths", {}))
        moved = []

        def walk(node):
            if isinstance(node, dict):
                d = node.get("description")
                if isinstance(d, str) and DOC_NAME.search(d):
                    taken = [m.group(0).strip(" ·()") for m in DOC_NAME.finditer(d)]
                    left = DOC_NAME.sub("", d).replace("  ", " ").strip()
                    # ⚠ 걷은 것이 근거의 «전부»면 「근거:」가 홀로 남는다 — 함께 뗀다
                    left = re.sub(r"\s*근거:\s*[·\s]*$", "", left).rstrip(" ·,")
                    node["description"] = left
                    note = node.get("x-internal-note")
                    # ⛔ 덧붙이기를 하지 않는다 — 머리만 남기고 다시 조립
                    base = (note or "").split(MARK)[0].rstrip()
                    node["x-internal-note"] = (
                        (base if base else "") + MARK + " · ".join(taken))
                    moved.extend(taken)
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(doc)
        if was_sorted and "paths" in doc:
            doc["paths"] = dict(sorted(doc["paths"].items()))
        updated = json.dumps(doc, ensure_ascii=False, indent=indent) + tail
        if updated != original:
            open(path, "w", encoding="utf-8").write(updated)
            print(f"  · {os.path.basename(path)} — {len(moved)}곳: {' · '.join(moved)}")
            total += len(moved)

    print(f"  ✅ 공개 설명에서 문서 이름 {total}곳을 걷었다" if total
          else "  이미 반영돼 있다 — 변경 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
