#!/usr/bin/env python3
"""요구서가 인용한 엔드포인트가 계약에 실재하는지 본다 — 역방향 ②.

02 트랙이 「요구서 ↔ 계약 역방향 검사기」를 후속으로 남겼는데(05-검증 §6),
그때 사람이 짚은 것은 **한 방향뿐**이었다.

    역방향 ①  계약 → 화면    「경로가 있는데 부르는 화면이 없다」   02 가 사람으로 짚었다
    역방향 ②  요구서 → 계약  「인용했는데 그 경로가 없다」          ⭐ 이 검사기

⚠ ①은 자기 계약만 보면 되지만 ②는 **남의 계약을 인용한 것**이 대상이라
   트랙 하나로는 절대 안 잡힌다. 03 트랙이 03 을 쓰다가 02 의 것을 발견했다.

표기 흔들림은 걸러낸다 — 경로 파라미터 이름(`{id}` ↔ `{purchaseOrderId}`)은
정규화하고, 산문 자리표시(`{문서}`)와 코드펜스 안은 세지 않는다.

    python3 verify-doc-citations.py            전 요구서
    python3 verify-doc-citations.py --doc 03   한 요구서
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections.abc import Iterator

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
# ⚠ Tier 0 — OpenAPI JSON 정본은 Phase 5 컷오버 전까지 deliverables/openapi/에 그대로 있다.
OPENAPI_DIR = os.path.join(ROOT, "deliverables", "openapi")
API_CONTRACTS_DIR = os.path.join(ROOT, "new_wiki", "wiki", "api-contracts")

METHODS = ("get", "post", "put", "patch", "delete")

# 「GET /a/b/{c}」 · 「`POST /a:verb`」 둘 다 잡는다.
CITATION = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+`?(/[A-Za-z0-9/{}\-:_]+)")

# 산문 자리표시 — 여러 리소스를 묶어 쓴 것이라 실재 경로가 아니다.
PROSE_PLACEHOLDER = re.compile(r"\{[^}]*[^\x00-\x7F][^}]*\}")


def normalize(path: str) -> str:
    """경로 파라미터 이름을 지운다 — 요구서와 계약의 표기가 흔들려도 같게 본다."""
    return re.sub(r"\{[^}]*\}", "{}", path)


def load_contracts() -> dict[tuple[str, str], set[str]]:
    found: dict[tuple[str, str], set[str]] = {}
    for f in sorted(glob.glob(os.path.join(OPENAPI_DIR, "*.json"))):
        with open(f, encoding="utf-8") as fh:
            doc = json.load(fh)
        for path, item in doc.get("paths", {}).items():
            for method in item:
                if method in METHODS:
                    key = (method.upper(), normalize(path))
                    found.setdefault(key, set()).add(os.path.basename(f))
    return found


def citations(md_path: str) -> Iterator[tuple[int, str, str]]:
    """(줄번호, 메서드, 경로) — 코드펜스 안은 건너뛴다."""
    in_fence = False
    with open(md_path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for method, raw in CITATION.findall(line):
                raw = raw.rstrip("`")
                if PROSE_PLACEHOLDER.search(raw):
                    continue          # `/logistics/{문서}/{id}:cancel`
                if raw.count("{") != raw.count("}"):
                    continue          # 정규식이 한글 자리표시에서 끊긴 조각
                path = normalize(raw.split("?")[0])
                if path.endswith("/"):
                    # 정규식 문자군이 ASCII 뿐이라 `/quality/한글` 은 `/quality/` 까지만
                    # 잡힌다. 끝이 `/` 인 경로는 실재하지 않으므로 조각으로 본다.
                    continue
                yield lineno, method, path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", help="요구서 이름 조각 (예: 03 · 02생산실행)")
    args = ap.parse_args()

    contracts = load_contracts()
    if not contracts:
        print(f"⛔ 계약을 찾지 못했습니다 — {OPENAPI_DIR}")
        return 2

    # ⛔ 접미가 «없는» 06-API-요구서.md(기준정보)를 빼면 안 된다 — 옛 글로브가
    #    `06-API-요구서-*.md` 라 그 한 장이 «한 번도» 검사받지 않았고, 그 사이
    #    기준정보 계약이 73 → 86 경로로 바뀌었다(2026-08-18 확대).
    targets = sorted(glob.glob(os.path.join(API_CONTRACTS_DIR, "06-API-요구서*.md")))
    if args.doc:
        targets = [t for t in targets if args.doc in os.path.basename(t)]
        if not targets:
            print(f"⛔ 요구서를 찾지 못했습니다 — {args.doc}")
            return 2

    total_cited = total_missing = 0
    for md in targets:
        name = os.path.basename(md)
        cited = list(citations(md))
        missing = [c for c in cited if (c[1], c[2]) not in contracts]
        total_cited += len(cited)
        total_missing += len(missing)

        if missing:
            print(f"⛔ {name} — 인용 {len(cited)} 중 계약에 없는 것 {len(missing)}")
            for lineno, method, path in missing:
                others = sorted({m for m, p in contracts if p == path})
                hint = f"  ← 경로는 있다. 있는 메서드: {', '.join(others)}" if others else ""
                print(f"      {lineno:5d}  {method} {path}{hint}")
        else:
            print(f"✅ {name} — 인용 {len(cited)} 전건 계약에 있다")

    print()
    if total_missing:
        print(f"⛔ 계 {total_missing} / {total_cited} 건이 허공을 가리킵니다.")
        print("   요구서 표기가 틀렸거나, 계약에 오퍼레이션이 빠졌거나 둘 중 하나입니다.")
        return 1
    print(f"✅ 인용 {total_cited} 건 전부 계약에 있습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
