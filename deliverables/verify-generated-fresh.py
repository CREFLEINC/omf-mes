#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""생성물이 정본과 갈렸는지 본다 — 다시 만들어 보고 «되돌린다». 저장소를 바꾸지 않는다.

무엇을 보나
-----------
`openapi/ui-요구목록*.md` 는 **화면 상세 스펙 §5 액션 표에서 생성한 파생물**이다.
그런데 커밋돼 있어서 **정본처럼 읽힌다.** 스펙이 바뀌었는데 다시 만들지 않으면
파일이 조용히 낡고, 그것을 읽는 `verify-mapping-coverage.py` 가 **거짓 초록**을 낸다.

이 검사는 도메인마다 생성기를 돌려 **바뀌는 것이 있는지**만 보고 **원래대로 되돌린다.**

⛔ 왜 만들었나 — 실제로 일어났다
--------------------------------
2026-08-18 실측:

    커버리지 게이트          04 — 액션 147 · ✅ 전건 다뤘습니다
    스냅숏을 다시 만들면      04 — 액션 149          ← 둘이 더 있었다

늘어난 둘은 2026-08-13 확정(DR-013)이 낳은 폐기 거래처 액션이었고, **04 요구서에
그 낱말이 0건**이었다. 게이트는 초록인데 요구서는 그 동작을 몰랐다.

⭐ 뿌리는 「어느 쪽이 정본인지 안 정한 것」이다 — **정본은 화면 스펙이고 이 목록은
파생물이다.** 계약 쪽은 같은 뿌리의 문제를 「JSON 이 정본」으로 정해 끝냈고,
여기는 이 검사가 그 자리를 대신한다.

⚠ 무엇을 «안» 보나
-------------------
- **목록의 내용이 맞는지** — 스펙이 틀렸으면 생성물도 똑같이 틀린다. 같이 틀린다.
- **요구서가 그 액션을 다뤘는지** — 그것은 `verify-mapping-coverage.py` 몫이다.
  이 검사가 초록이어도 게이트는 빨갈 수 있다(그것이 정상이다).
- **생성기 자체가 옳은지** — 생성기가 액션을 빠뜨리면 양쪽이 함께 빠진다.

쓰기
----
    python3 deliverables/verify-generated-fresh.py           # 전 도메인
    python3 deliverables/verify-generated-fresh.py --domain 04

갈린 것이 있으면 종료 코드 1. 되돌리기는 **어떤 경우에도** 수행한다.
"""
from __future__ import annotations

import argparse
import importlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_COV = importlib.import_module("verify-ui-coverage")

DOMAINS = list(_COV.DOMAINS)
GENERATOR = os.path.join(HERE, "verify-ui-coverage.py")


def target_of(domain: str) -> str:
    return os.path.join(HERE, "openapi", _COV.DOMAINS[domain][1])


def regenerate(domain: str) -> None:
    cmd = [sys.executable, GENERATOR]
    if domain != "mdm":  # mdm 은 생성기의 기본값이라 --domain 을 주지 않는다
        cmd += ["--domain", domain]
    subprocess.run(cmd, cwd=HERE, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--domain", choices=DOMAINS)
    args = ap.parse_args()

    domains = [args.domain] if args.domain else DOMAINS
    before: dict[str, bytes] = {}
    stale: list[str] = []

    try:
        for d in domains:
            path = target_of(d)
            if not os.path.exists(path):
                print(f"⛔ 생성물이 없다 — {os.path.relpath(path, HERE)}")
                stale.append(d)
                continue
            before[path] = open(path, "rb").read()
            regenerate(d)
            after = open(path, "rb").read()
            if after != before[path]:
                stale.append(d)
                print(f"⛔ {d} — 다시 만들면 달라진다 · "
                      f"{os.path.relpath(path, HERE)}")
    finally:
        # ⛔ 어떤 경우에도 되돌린다 — 이 검사는 저장소를 바꾸지 않는다.
        for path, body in before.items():
            open(path, "wb").write(body)

    print()
    if stale:
        print(f"⛔ 낡은 생성물 {len(stale)}건 — {' · '.join(stale)}")
        print("→ 다시 만들고, 늘어난 액션을 요구서 §3 매핑표에 넣는다.")
        print("   (이 검사는 되돌려 두었으므로 저장소는 그대로다)")
        return 1
    print(f"✅ 생성물 {len(domains)}건이 스펙과 같습니다 — 다시 만들어도 안 바뀝니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
