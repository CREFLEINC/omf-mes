#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""생성기를 돌리면 «잃는 것»이 있는지 본다 — 재생성 전에 반드시 돌린다.

왜 필요한가
-----------
02·03·04 계약은 `build-0N-openapi.py` 가 정본이고 JSON 은 생성물이다.
그런데 **JSON 을 직접 고친 패치들이 생성기에 안 반영돼 있어**, 지금
재생성하면 그것들이 조용히 사라진다.

실측(2026-08-18) — `build-03-openapi.py` 를 돌리면 —

    ETag 응답 헤더 선언   2곳  →  0곳     ⛔ 사라진다
                                          (patch-lock-token-sources.py 가 넣은 것)

`check-lock-token-source.py` 가 그때야 실패로 잡지만, **그 사이 커밋되면
공개 계약에서 저장 충돌 토큰을 받을 곳이 없어진다.**

⚠ 이것은 정리보고 §3-1-①(「생성물이 정본 자리에 앉았다」)의 **거울상**이다.
그쪽은 «생성물을 원본처럼 읽는» 문제였고, 이쪽은 «원본을 안 고치고 생성물만
고친» 문제다. 둘 다 같은 뿌리 — **어느 쪽이 정본인지 안 정했다.**

무엇을 하나
-----------
JSON 을 백업하고 생성기를 돌린 뒤 **무엇이 달라지는지 세고 원래대로 되돌린다.**
저장소 상태는 바꾸지 않는다.

⚠ 이 검사기가 못 보는 것
------------------------
- **어느 쪽이 옳은지 판정하지 않는다.** 「달라진다」까지만 말한다. 생성기가
  낡은 것일 수도 있고 JSON 이 손으로 잘못 고쳐진 것일 수도 있다.
- 생성기가 없는 계약(`mdm`·`logistics`·`app-공통`)은 대상이 아니다.

쓰기
----
    python3 deliverables/openapi/check-generator-drift.py
"""
from __future__ import annotations

import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
# 생성기 파일 이름의 도메인 조각 → 그 도메인 계약 JSON 을 이름으로 찾는다
GEN = sorted(glob.glob(os.path.join(HERE, "build-*-openapi.py")))


def target_json(gen_path: str) -> str | None:
    m = re.search(r"build-(\d\d)-openapi\.py$", os.path.basename(gen_path))
    if not m:
        return None
    hits = [p for p in glob.glob(os.path.join(HERE, "*.json"))
            if f"-{m.group(1)}" in os.path.basename(p)]
    return hits[0] if len(hits) == 1 else None


def main() -> int:
    drifted = []
    for gen in GEN:
        js = target_json(gen)
        if not js:
            print(f"⚠ {os.path.basename(gen)} — 대상 JSON 을 못 찾았다", file=sys.stderr)
            continue
        before = open(js, encoding="utf-8").read()
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as bak:
            bak.write(before)
            bak_path = bak.name
        try:
            r = subprocess.run([sys.executable, gen], capture_output=True, text=True)
            if r.returncode != 0:
                print(f"⛔ {os.path.basename(gen)} 실행 실패\n{r.stderr[:400]}", file=sys.stderr)
                return 1
            after = open(js, encoding="utf-8").read()
        finally:
            shutil.copyfile(bak_path, js)      # ⭐ 무슨 일이 있어도 되돌린다
            os.unlink(bak_path)

        if after == before:
            print(f"  ✅ {os.path.basename(gen):24} 재생성해도 같다")
            continue

        # 무엇을 잃는지 «이름»으로 센다 — 줄 수만으로는 뜻을 모른다
        lost = []
        for key in ('"ETag"', '"headers"', "If-Match", "x-internal-note"):
            b, a = before.count(key), after.count(key)
            if a < b:
                lost.append(f"{key} {b} → {a}")
        drifted.append((os.path.basename(gen), os.path.basename(js), lost))
        print(f"  ⛔ {os.path.basename(gen):24} 재생성하면 달라진다"
              + (f" — 잃는 것: {' · '.join(lost)}" if lost else ""))

    if not drifted:
        print("\n✅ 생성기와 계약이 일치합니다 — 재생성해도 안전합니다")
        return 0

    print(f"\n⛔ 생성기와 계약이 갈렸습니다 — {len(drifted)}종")
    print("→ **재생성하지 마십시오.** 먼저 생성기에 빠진 것을 넣거나,")
    print("   JSON 을 정본으로 삼기로 정하고 생성기를 버리십시오.")
    print("   ⚠ 지금은 어느 쪽이 정본인지 정해져 있지 않습니다.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
