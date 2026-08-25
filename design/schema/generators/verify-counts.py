#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""문서에 «박힌» 수치가 실물과 같은가 — 낡은 숫자를 기계가 잡는다.

왜 필요한가
-----------
이 저장소의 판정 하나가 이 검사기를 낳았다.

    ⭐⭐ 스크립트가 정본인 자리는 하나도 안 갈렸고, 손으로 쓴 수치는 예외 없이 낡았다.

편람 8종은 「전량 신규 작성」 3주 만에 머리말 6/8 이 실물과 어긋났다. 원인은 복사다 —
**원본이 바뀌어도 복사본에는 갱신 의무가 아무에게도 없다.**

⭐ 그래서 서식을 정했다 — **숫자 + 실측일 + 세는 명령.** 셋이 다 있으면 낡아도
낡은 것이 «보인다». **이 검사기는 그 「보인다」를 기계로 만든다.**

무엇을 보나
-----------
아래 등록부의 각 줄이 「어느 파일의 어느 자리에 적힌 숫자를, 무엇으로 재는가」다.
적힌 값과 잰 값이 다르면 종료 코드 1.

⛔ 무엇을 «안» 보나
-------------------
- **등록되지 않은 숫자** — 문서에 숫자를 새로 박으면 여기 등록해야 잡힌다.
  ⚠ 그래서 **숫자를 박지 않는 것이 여전히 제일 낫다.** 이 검사기는 차선이다.
- **숫자가 «뜻하는 것»이 맞는지** — 「화면 117」이 맞아도 그 문장이 옳다는 뜻은 아니다
- **생성물** — 다시 만들면 되므로 대상이 아니다(진도표 · 인계 대장 · 미결 대장)

쓰기
----
    python3 design/schema/generators/verify-counts.py
"""
from __future__ import annotations

import glob
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
WIKI = os.path.join(ROOT, "design", "wiki")
# Tier 0 — OpenAPI JSON 정본. Phase 5 컷오버(2026-08-25)로 design/wiki/api-contracts/openapi/가 정본 위치다.
CONTRACTS_DIR = os.path.join(ROOT, "design", "wiki", "api-contracts", "openapi")


def read(path: str) -> str:
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def run(*cmd: str) -> str:
    return subprocess.run(list(cmd), capture_output=True, text=True, cwd=ROOT).stdout


# ── 재는 함수들 — 전부 기존 정본을 그대로 쓴다 ──────────────────────────────
def m_screens() -> int:
    out = run(sys.executable, os.path.join(HERE, "verify-screen-inventory.py"))
    return int(re.search(r"화면 (\d+)", out).group(1))


def _contract_totals() -> tuple[int, int, int]:
    p = o = s = 0
    for f in sorted(glob.glob(os.path.join(CONTRACTS_DIR, "*.json"))):
        d = json.loads(read(f))
        p += len(d["paths"])
        s += len(d["components"]["schemas"])
        o += sum(1 for item in d["paths"].values() for k in item
                 if k in ("get", "post", "put", "patch", "delete"))
    return p, o, s


def m_paths() -> int:
    return _contract_totals()[0]


def m_operations() -> int:
    return _contract_totals()[1]


def m_schemas() -> int:
    return _contract_totals()[2]


def m_contract_files() -> int:
    return len(glob.glob(os.path.join(CONTRACTS_DIR, "*.json")))


def m_doc_files() -> int:
    return len(glob.glob(os.path.join(WIKI, "api-contracts", "06-API-요구서*.md")))


def m_citations() -> int:
    out = run(sys.executable, os.path.join(HERE, "verify-doc-citations.py"))
    return int(re.search(r"인용 (\d+) 건 전부", out).group(1))


def m_clauses() -> int:
    text = read(os.path.join(WIKI, "decisions-policy", "공유계약.md"))
    return len(re.findall(r"^### [A-Z]-\d", text, re.M))


def m_clause_sections() -> int:
    text = read(os.path.join(WIKI, "decisions-policy", "공유계약.md"))
    return len(re.findall(r"^## §[A-Z]\.", text, re.M))


def m_decisions() -> int:
    out = run(sys.executable, os.path.join(HERE, "count-decisions.py"))
    return int(re.search(r"^\s+계\s+(\d+)", out, re.M).group(1))


def m_dr() -> int:
    return len(glob.glob(os.path.join(ROOT, "design", "raw", "decision-requests", "DR-*.md")))


def m_glossary() -> int:
    return len(re.findall(r"^### ", read(os.path.join(WIKI, "glossary", "00-용어사전.md")), re.M))


def m_covered_screens() -> int:
    """요구서 §3 이 다룬 화면 — 진도표 생성기와 같은 근거를 쓴다."""
    ids = set()
    for path in sorted(glob.glob(os.path.join(WIKI, "api-contracts", "06-API-요구서*.md"))):
        ids |= set(re.findall(r"^### 3-\d+\.[^\n`]*`([WMP]-(?:CO|\d{2})-\d{2})`",
                              read(path), re.M))
    return len(ids)


def m_specs() -> int:
    return len(glob.glob(os.path.join(WIKI, "screens", "*", "[WMP]-*.md")))


# ── 등록부 — (파일, 이름, 정규식(캡처 1개), 재는 함수) ──────────────────────
REGISTRY = [
    ("00-index.md", "화면", r"화면 \*\*(\d+)\*\*", m_screens),
    ("00-index.md", "화면 상세 스펙 파일", r"상세 스펙 \*\*(\d+)장\*\*", m_specs),
    ("00-index.md", "계약 파일", r"계약 \*\*(\d+)파일\*\*", m_contract_files),
    ("00-index.md", "계약 경로", r"경로 \*\*(\d+)\*\*", m_paths),
    ("00-index.md", "계약 오퍼레이션", r"오퍼레이션 \*\*(\d+)\*\*", m_operations),
    ("00-index.md", "계약 스키마", r"스키마 \*\*(\d+)\*\*", m_schemas),
    ("00-index.md", "요구서", r"요구서 \*\*(\d+)장\*\*", m_doc_files),
    ("00-index.md", "공유계약 조항", r"조항 \*\*(\d+)\*\*", m_clauses),
    ("00-index.md", "결정 대장", r"결정 대장 \*\*(\d+)행\*\*", m_decisions),
    ("00-index.md", "의사결정 요청서", r"의사결정 요청서 \*\*(\d+)건\*\*", m_dr),
    ("00-index.md", "용어", r"용어 \*\*(\d+)항목\*\*", m_glossary),

    ("decisions-policy/00-index.md", "결정 대장", r"\| (\d+)행 \|", m_decisions),
    ("decisions-policy/00-index.md", "의사결정 요청서", r"DR-001~013 \| (\d+)건", m_dr),
    ("decisions-policy/00-index.md", "공유계약 조항", r"조항 (\d+) · 절 \d+", m_clauses),
    ("decisions-policy/00-index.md", "공유계약 절", r"조항 \d+ · 절 (\d+)", m_clause_sections),

    ("api-contracts/09-API-계약서.md", "계약 파일", r"\*\*(\d+)파일\*\*", m_contract_files),
    ("api-contracts/09-API-계약서.md", "계약 경로", r"경로 (\d+) · 오퍼레이션", m_paths),
    ("api-contracts/09-API-계약서.md", "계약 오퍼레이션", r"오퍼레이션 (\d+) · 스키마", m_operations),
    ("api-contracts/09-API-계약서.md", "계약 스키마", r"스키마 (\d+)\*\*", m_schemas),
    ("api-contracts/09-API-계약서.md", "요구서", r"\*\*(\d+)장\*\*", m_doc_files),
    ("api-contracts/09-API-계약서.md", "인용", r"인용 \*\*(\d+)\*\*", m_citations),
    ("api-contracts/09-API-계약서.md", "덮은 화면", r"\*\*(\d+) / \d+\*\*", m_covered_screens),
]


def main() -> int:
    print("문서에 박힌 수치 ↔ 실물")
    print("─" * 68)
    bad: list[str] = []
    missing: list[str] = []
    for filename, label, pattern, measure in REGISTRY:
        path = os.path.join(WIKI, filename)
        if not os.path.exists(path):
            missing.append("%s — 파일이 없다" % filename)
            continue
        m = re.search(pattern, read(path))
        if not m:
            missing.append("%s · %s — 자리를 찾지 못했다" % (filename, label))
            continue
        written, actual = int(m.group(1)), measure()
        mark = "✅" if written == actual else "⛔"
        print("  %s %-26s %-16s 적힘 %-6d 실물 %d"
              % (mark, filename, label, written, actual))
        if written != actual:
            bad.append("%s · %s — 적힘 %d · 실물 %d" % (filename, label, written, actual))

    if missing:
        print("\n⚠ 자리를 못 찾은 것 %d건 — 문서 서식이 바뀌었는지 본다" % len(missing))
        for x in missing:
            print("   " + x)
    if bad:
        print("\n⛔ 낡은 수치 %d건" % len(bad))
        for x in bad:
            print("   " + x)
        print("\n→ 문서를 고치거나, 세는 기준이 바뀐 것이면 이 등록부를 고친다.")
        return 1
    if missing:
        return 1
    print("\n✅ 등록된 수치 %d건이 전부 실물과 같습니다." % len(REGISTRY))
    return 0


if __name__ == "__main__":
    sys.exit(main())
