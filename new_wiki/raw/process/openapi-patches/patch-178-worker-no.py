#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""귀속 사번(`X-Worker-No`)을 «받을 자리»를 계약에 선언한다. 멱등. — 이슈 #178

왜 필요한가
-----------
공유계약 **D-5**(귀속 정보는 세션이 아니다)가 「현장 단말·모바일의 **쓰기
요청에 사번이 필수** — 없으면 서버가 거부」라고 정해 두었다. 서버는 사번
세션을 갖지 않으므로 단말이 매 쓰기 요청에 헤더로 싣는다.

    Authorization: Bearer <단말 토큰>       ← 인증
    X-Worker-No: 900028                     ← 귀속. 인증 아님

**그런데 그 사번을 받을 자리가 계약 일곱 벌 어디에도 없었다**(전수 검색 0건).

⛔ 저장 충돌 토큰에서 겪은 것과 **같은 형태**다 — `If-Match` 를 필수로 받아
놓고 그 값을 어디서 받는지 선언하지 않아 구현이 **19건** 막혔다(2026-08-17).
**받을 자리를 계약이 선언해야 한 세트가 된다.**

드러난 경위 — 구현팀 질의 **#173**(검사자를 화면이 채울 수 없다)을 풀면서
「검사자는 서버가 인증 주체에서 푼다」로 확정했는데, **현장 단말에는 계정
로그인이 없다.** 서버가 작업자를 풀 유일한 근거가 이 헤더인데 계약에 없었다.

무엇을 하나
-----------
① `components.parameters` 에 귀속 헤더를 **두 벌** 신설한다.

       WorkerNo           required: true    현장 단말·모바일 «전용» 오퍼레이션
       WorkerNoOptional   required: false   관리웹도 «같은 오퍼레이션»을 부른다

② 대상 오퍼레이션마다 `$ref` 로 건다.

⭐ 선례를 그대로 따랐다 — `IfMatchVersion` / `IfMatchVersionOptional` 두 벌.
   ⚠ 「어느 파일에 무엇을 두나」는 **쓰는 곳에만** 둔다(그 선례도 일곱 벌 중
   네 벌에만 있다).

⭐ 왜 여섯을 «선택»으로 두나 — 이 건의 핵심 판단
------------------------------------------------
서른여섯 중 **여섯은 관리웹 화면도 «같은 경로·같은 메서드»를 부른다.** 일괄로
필수를 걸면 **관리웹이 없는 사번을 지어내게 된다** — 관리웹은 계정 토큰으로
오고 사번 입력 자리가 없다.

그래서 **서버가 인증 토큰의 종류로 가른다.**

    계정 토큰(app_user)     → 헤더 없이 와도 된다. 인증 주체에서 행위자를 푼다
    단말 토큰(mdm.terminal) → 헤더가 없으면 거부한다(D-5)

이 규칙은 **#173 에서 확정한 「검사자는 서버가 인증 주체에서 푼다」의 확장**이다.
관리웹에서는 인증 주체가 곧 사람이고, 현장 단말에서는 인증 주체가 단말이라
사람을 헤더가 지목한다.

⚠ **OpenAPI 로는 「단말 토큰이면 필수」를 표현할 수 없다.** 선택으로 두고 그
규칙을 설명문에 적는다 — `IfMatchVersionOptional` 이 이미 같은 방식이다.

⛔ 하지 «않은» 것
------------------
- **관리웹 전용 쓰기 오퍼레이션에는 달지 않는다** — 계정 토큰이 곧 귀속이다
- **`mdm-기준정보.json` 은 대상이 아니다** — 기준정보는 관리웹 전용(대상 0건)
- **단말 토큰 세대 번호(`token_version` · 공유계약 §I-31 · F-4)는 별건이다**
  — 같은 인증 층이지만 그쪽은 **물리 모델 결손**이라 우리 소관이 아니다.
  헤더는 계약 소관이라 먼저 넣는다. 기다리면 둘 다 안 된다(§1-2).

대상은 어떻게 정하나
--------------------
**세지 않는다 — `check-worker-no.py` 가 실측한 것을 그대로 가져다 쓴다.**
목록을 이 파일에 베껴 두면 요구서가 바뀔 때 두 벌이 조용히 갈린다.

쓰기
----
    python3 deliverables/openapi/patch-178-worker-no.py
    python3 deliverables/openapi/check-worker-no.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

REQUIRED_KEY = "WorkerNo"
OPTIONAL_KEY = "WorkerNoOptional"
REQUIRED_REF = "#/components/parameters/" + REQUIRED_KEY
OPTIONAL_REF = "#/components/parameters/" + OPTIONAL_KEY

PARAMS = {
    REQUIRED_KEY: {
        "name": "X-Worker-No",
        "in": "header",
        "required": True,
        "schema": {"type": "string", "maxLength": 50},
        "description": (
            "귀속용 사번 — 이 쓰기를 「누가 한 일」로 기록할 것인가. "
            "인증이 아니다. 현장 단말·모바일은 계정 로그인이 없어 서버가 "
            "행위자를 풀 근거가 이 헤더뿐이다. 없으면 서버가 거부한다. "
            "값은 작업자 사번(전역 유일). 근거: 공유계약 D-5 · F-2"
        ),
        "x-internal-note": (
            "⛔ 귀속을 인증으로 승격시키지 않는다 — 사번에 비밀번호·실패 잠금·"
            "세션 만료를 붙이면 REQ-PR-0023 이 요구한 「로그인 생략」을 우회로 "
            "되살리는 것이다(공유계약 F-2 단서 · P-CO-01 §5-1). 도용 리스크는 "
            "수용하고, 화면이 현재 귀속 대상을 상시 보이는 것으로 방어한다(D-5). "
            "원천 컬럼은 mdm.worker.worker_no. 이슈 #178."
        ),
    },
    OPTIONAL_KEY: {
        "name": "X-Worker-No",
        "in": "header",
        "required": False,
        "schema": {"type": "string", "maxLength": 50},
        "description": (
            "관리웹도 같은 오퍼레이션을 부르는 자리에서는 선택이다 — 관리웹은 "
            "계정 토큰으로 오므로 서버가 인증 주체에서 행위자를 푼다. "
            "단말 토큰으로 온 요청에 이 헤더가 없으면 서버가 거부한다. "
            "근거: 공유계약 D-5 · F-2"
        ),
        "x-internal-note": (
            "현장 단말·모바일 전용 오퍼레이션에는 WorkerNo(required)를 그대로 "
            "쓴다 — 이 완화는 두 셸이 함께 부르는 오퍼레이션에만 적용한다. "
            "OpenAPI 로는 「단말 토큰이면 필수」를 표현할 수 없어 선택으로 두고 "
            "규칙을 설명에 적는다. 판정 근거는 인증 토큰의 종류(app_user / "
            "mdm.terminal)이지 헤더의 유무가 아니다. 이슈 #178."
        ),
    },
}

FORMAT: dict[str, dict] = {}


def load_checker():
    """실측 정본을 불러온다 — 목록을 베끼지 않는다.

    ⚠ 바이트코드를 남기지 않는다 — `__pycache__` 가 저장소에 굴러다니게 된다.
    """
    sys.dont_write_bytecode = True
    path = os.path.join(HERE, "check-worker-no.py")
    spec = importlib.util.spec_from_file_location("check_worker_no", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def measure(raw: str) -> dict:
    """원본에서 들여쓰기 폭과 끝 개행 여부를 잰다."""
    second = raw.split("\n")[1] if "\n" in raw else ""
    return {
        "indent": len(second) - len(second.lstrip(" ")) or 1,
        "newline": raw.endswith("\n"),
    }


def load(name: str) -> dict:
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        raw = fh.read()
    FORMAT[name] = measure(raw)
    return json.loads(raw)


def save(name: str, spec: dict) -> None:
    """⚠ 원본과 «같은 직렬화»로 쓴다 — 형식이 어긋나면 안 고친 자리까지 diff 에 든다."""
    fmt = FORMAT[name]
    body = json.dumps(spec, ensure_ascii=False, indent=fmt["indent"])
    if fmt["newline"]:
        body += "\n"
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as fh:
        fh.write(body)


def roundtrip(name: str) -> None:
    """손대기 «전»에 확인한다 — 읽고 그대로 쓰면 바이트가 같은가."""
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        before = fh.read()
    fmt = measure(before)
    after = json.dumps(json.loads(before), ensure_ascii=False, indent=fmt["indent"])
    if fmt["newline"]:
        after += "\n"
    if before != after:
        sys.exit("⛔ %s — 직렬화가 원본과 다릅니다. 형식을 먼저 맞추세요." % name)


def main() -> int:
    checker = load_checker()
    real, docs = checker.load_contracts()
    targets, _ = checker.scope(real)

    # 파일 → {키} · 파일 → [(경로, 메서드, 참조)]
    need: dict[str, set] = {}
    edits: dict[str, list] = {}
    for (fname, path, method), who in sorted(targets.items()):
        key = OPTIONAL_KEY if who["web"] else REQUIRED_KEY
        need.setdefault(fname, set()).add(key)
        edits.setdefault(fname, []).append((path, method, key))

    log: list[str] = []
    for fname in sorted(edits):
        roundtrip(fname)
        spec = load(fname)

        params = spec.setdefault("components", {}).setdefault("parameters", {})
        for key in sorted(need[fname]):
            if params.get(key) == PARAMS[key]:
                log.append("  · %-28s components.parameters.%s 이미 있다"
                           % (fname, key))
            else:
                params[key] = json.loads(json.dumps(PARAMS[key]))
                log.append("  ⭐ %-28s components.parameters.%s 신설"
                           % (fname, key))

        for path, method, key in edits[fname]:
            op = spec["paths"][path][method.lower()]
            plist = op.setdefault("parameters", [])
            refs = {p["$ref"] for p in plist
                    if isinstance(p, dict) and "$ref" in p}
            ref = "#/components/parameters/" + key
            other = OPTIONAL_REF if key == REQUIRED_KEY else REQUIRED_REF
            if other in refs:
                # 등급이 바뀐 자리 — 낡은 쪽을 걷어낸다(멱등)
                op["parameters"] = [p for p in plist
                                    if not (isinstance(p, dict)
                                            and p.get("$ref") == other)]
                plist = op["parameters"]
                refs.discard(other)
                log.append("  ⛔ %-28s %-6s %-40s 등급 교체"
                           % (fname, method, path[:40]))
            if ref in refs:
                log.append("  · %-28s %-6s %-40s 이미 있다"
                           % (fname, method, path[:40]))
            else:
                plist.append({"$ref": ref})
                log.append("  ✅ %-28s %-6s %-40s → %s"
                           % (fname, method, path[:40], key))

        save(fname, spec)

    print("== 귀속 사번을 받을 자리를 선언한다 — 이슈 #178 ==\n")
    for line in log:
        print(line)

    print("\n== 최종 ==")
    total = sum(len(v) for v in edits.values())
    req = sum(1 for v in targets.values() if not v["web"])
    opt = sum(1 for v in targets.values() if v["web"])
    for fname in sorted(edits):
        print("   %-30s 오퍼레이션 %2d · 정의 %s"
              % (fname, len(edits[fname]), "·".join(sorted(need[fname]))))
    print("   %-30s 오퍼레이션 %2d · 필수 %d · 선택(관리웹 겸용) %d"
          % ("합계", total, req, opt))
    print("\n⚠ 이 수치는 하한이다 — check-worker-no.py 첫머리 「안 보는 것」을 함께 읽는다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
