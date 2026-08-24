#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LOT 판정 전이의 실행 경로·잠금 토큰·토큰 원천 설명을 고친다. 멱등.

무엇을 고치나 — 구현팀 질의 `omf-mes#190`
------------------------------------------
    질문2  LotStatusTransition.actionCode   어느 쓰기 경로인지 서버가 알려 준다
    질문3  LotQualityStatus.versionNo       대량 보류의 토큰을 목록이 내려 준다
    질문4  lot-holds/{id} 의 ETag 설명       「이 행의 판 번호」가 아니다 — 정정

⭐ 질문2 — 목표 상태만으로는 경로를 못 가른다 (사용자 확정 ⓐ)
--------------------------------------------------------------
「불량」이 **두 경로에서 도달**한다.

    POST /quality/lot-holds/{id}:release   목표=불량   ← C8 재판정 불합격
    POST /quality/lot-holds                목표=불량   ← C9 클레임·리콜 재Hold

화면이 `currentLotStatusCode` 로 추론할 수는 있다. **그것이 문제다** — 그 분기가
곧 전이표이고, 전이가 하나 늘면 관리웹·POP·모바일 **세 벌을 다시 배포**해야 한다.
공유계약 `G-8`(전이 규칙을 화면이 갖지 않는다 — 서버가 판정한다)이 금지한 형태다.

⛔ 택하지 않은 안
    ⓑ 실행 링크를 통째로(method + pathTemplate) — 결합은 더 낮으나 **계약 일곱 벌
      중 이 한 곳만 다른 모양**이 된다. 값 둘짜리 문제에 새 관례를 세우지 않는다
    ⓒ 전이 목록을 「액션 목록」으로 재정의 — 이 응답을 이미 쓰는 조회 화면들이
      함께 바뀐다

⭐ **어느 보류를 풀지는 여기서 정하지 않는다** — `actionCode` 는 「무엇을 하는가」
까지만 말한다. `RELEASE_HOLD` 일 때 «어느» 보류인지는 열린 보류가 여럿일 수 있어
사용자가 고른다(질문5). 그래서 `lotHoldId` 를 이 응답에 싣지 않았다.

⭐ 질문3 — 토큰을 목록이 내려 준다 (사용자 확정 ⓐ)
---------------------------------------------------
대량 보류(`POST /quality/lot-holds`)는 `lots[].versionNo` 를 **정수로 LOT 마다**
받는다. 여러 LOT 을 한 트랜잭션으로 걸어 **하나라도 어긋나면 전체를 거부**하기
때문이다(`W-03-03` §5-1) — 헤더 `If-Match` 하나로는 표현할 수 없다.

**그런데 그 값을 주는 조회가 없었다.** 대상 목록에도 LOT 상세 본문에도 없고,
`ETag` 는 **불투명 문자열**로 정의돼 정수로 파싱할 근거가 없다. 3건을 고르면
상세를 3번 불러야 했고 30건이면 30번이었다.

**대상 목록이 내려 준다** — `GET /quality/lot-statuses` 가 W-03-02·W-03-03 의
대상 목록이라 여기 실으면 **한 번의 조회로 본문이 조립된다.**

⛔ 택하지 않은 안
    ⓑ 단건은 헤더·대량만 본문 — 화면이 «고른 개수»로 요청 형태를 바꾸는 분기가
      생긴다. 질문2 에서 없애려는 것과 같은 종류의 분기다
    ⓒ 대량도 헤더 하나 — 나머지 LOT 이 검증되지 않는다. `W-03-03` §5-1 의
      「하나라도 어긋나면 전체 거부」 확정을 깬다. **확정을 깨는 안은 마지막이다**

⚠ 공유계약 `A-4` 를 함께 손봤다 — 그 조항의 주어는 2026-08-03 확정으로 이미
「화면 «표시»」였으나 단서가 전송 수단을 **헤더로 한정**하고 「본문 필드로 싣는
스키마는 없다」고 적어 두었다. 후자는 이제 사실이 아니다(`LotVersionRef`).

⛔ 질문4 — 설명이 없는 컬럼을 가리키고 있었다
---------------------------------------------
`GET /quality/lot-holds/{lotHoldId}` 의 `ETag` 설명이 「**이 행의** version_no」
였는데, 잠그는 대상은 **보류 행이 아니라 LOT** 이다. 같은 오퍼레이션의 내부
주석은 이미 맞게 적혀 있었다 — 「`If-Match` 는 lot_hold 가 아니라 trace.lot 의
version_no 다」. **공개 설명과 내부 주석이 서로 다른 말을 하고 있었고, 구현팀은
공개 설명을 읽는다.**

⚠ 원인 — 표준 문구를 **베끼는** 규칙(⛔ 문구를 손으로 쓰지 않는다)이 **토큰
원천이 「이 행」이 아닌 자리**에서 틀린 문장을 만들었다. 발산을 막으려던 장치가
여기서는 거꾸로 작동했다. **베낀 뒤 「이 행이 맞는가」를 한 번 보는 것이 빠졌다.**

쓰기
----
    python3 deliverables/openapi/patch-190-lot-status-transition.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "quality-03품질.json")
HOLD_DETAIL = "/quality/lot-holds/{lotHoldId}"

ACTION_CODE = {
    "type": "string",
    "enum": ["RELEASE_HOLD", "CREATE_HOLD"],
    "description": (
        "이 전이를 «어느 쓰기 경로»로 실행하는가. "
        "RELEASE_HOLD = POST /quality/lot-holds/{lotHoldId}:release "
        "(재판정 — 합격이면 정상 C7, 불합격이면 불량 C8). "
        "CREATE_HOLD = POST /quality/lot-holds "
        "(새 보류를 건다 — 의심자재 등록 C10, 클레임·리콜 재Hold C9). "
        "⭐ 목표 상태만으로는 가를 수 없다 — 「불량」이 두 경로에서 도달한다"
        "(C8 재판정 불합격 · C9 재Hold). 화면이 현재 상태로 추론하면 그 분기가 "
        "곧 전이표가 되어 전이가 하나 늘 때마다 세 셸을 다시 배포해야 한다"
        "(공유계약 G-8 — 전이 규칙을 화면이 갖지 않는다). "
        "⛔ 어느 보류를 풀지는 여기서 정하지 않는다 — 열린 보류가 여럿일 수 있어 "
        "사용자가 GET /quality/lot-holds?lotId=…&open=true 에서 고른다. "
        "근거: W-03-02 §5-1 · omf-mes#190 질문2"
    ),
    "example": "CREATE_HOLD",
}

VERSION_NO = {
    "type": "integer",
    "description": (
        "낙관적 잠금 토큰(저장할 때 판을 대조해 남이 먼저 고쳤는지 잡는다). "
        "⭐ 대량 보류(POST /quality/lot-holds)의 lots[].versionNo 에 그대로 싣는다 — "
        "여러 LOT 을 한 트랜잭션으로 걸어 토큰이 여럿이라 헤더 If-Match 하나로는 "
        "표현할 수 없고, 하나라도 어긋나면 전체를 거부한다(W-03-03 §5-1). "
        "⛔ 화면에 «표시»하지 않는다 — 필드표·폼·목록 열에 드러내지 않는다"
        "(공유계약 A-4). 전달은 막지 않는다는 것이 그 조항의 2026-08-03 확정이고, "
        "헤더 ETag 가 이미 같은 값을 전달하고 있다. "
        "근거: omf-mes#190 질문3"
    ),
    "example": 3,
}

HOLD_ETAG_DESC = (
    "낙관적 잠금 토큰 — ⭐ 이 보류 «행»의 것이 아니라 이 보류가 걸린 «LOT»의 "
    "판 번호(trace.lot.version_no)다. 잠그는 대상이 LOT 이기 때문이다 — 보류 해제는 "
    "LOT 의 품질 상태를 옮기는 일이고, 보류 행 자체는 기록 전용이라 판 번호를 갖지 "
    "않는다. 다음 쓰기(:release)의 If-Match 에 그대로 담는다. 본문 필드로는 내리지 "
    "않는다 — 표시하지 않되 전달한다. "
    "⚠ 이 설명은 2026-08-24 에 정정됐다(omf-mes#190 질문4) — 표준 문구를 베끼면서 "
    "「이 행의 version_no」로 적혀 있었고, 그것은 없는 컬럼을 가리켰다"
)


def detect_indent(original: str, doc: dict):
    body = original.rstrip("\n")
    for candidate in (1, 2, 4):
        if json.dumps(doc, ensure_ascii=False, indent=candidate) == body:
            return candidate
    return None


def put_after(props: dict, key: str, value: dict, after: str) -> None:
    """`after` 바로 뒤에 끼워 넣는다 — 읽는 차례를 지킨다. 멱등."""
    props.pop(key, None)
    rebuilt: dict = {}
    placed = False
    for k, v in props.items():
        rebuilt[k] = v
        if k == after:
            rebuilt[key] = json.loads(json.dumps(value))
            placed = True
    if not placed:
        rebuilt[key] = json.loads(json.dumps(value))
    props.clear()
    props.update(rebuilt)


def main() -> int:
    with open(CONTRACT, encoding="utf-8") as f:
        original = f.read()
    doc = json.loads(original)
    indent = detect_indent(original, doc)
    if indent is None:
        print("⛔ 들여쓰기를 알아낼 수 없다 — 덮어쓰지 않는다", file=sys.stderr)
        return 1
    tail = original[len(original.rstrip("\n")):]

    schemas = doc["components"]["schemas"]

    # ① 질문2 — 실행 경로를 서버가 알려 준다. allowed 뒤에 둔다(갈 수 있는가 → 어떻게).
    transition = schemas["LotStatusTransition"]
    put_after(transition["properties"], "actionCode", ACTION_CODE, after="allowed")
    required = transition.setdefault("required", [])
    if "actionCode" not in required:
        required.append("actionCode")

    # ② 질문3 — 대량 보류의 토큰을 대상 목록이 내려 준다.
    put_after(schemas["LotQualityStatus"]["properties"], "versionNo", VERSION_NO,
              after="lotStatusCode")

    # ③ 질문4 — 토큰 원천 설명 정정. 잠그는 대상은 보류 행이 아니라 LOT 이다.
    etag = doc["paths"][HOLD_DETAIL]["get"]["responses"]["200"]["headers"]["ETag"]
    etag["description"] = HOLD_ETAG_DESC

    updated = json.dumps(doc, ensure_ascii=False, indent=indent) + tail
    if updated == original:
        print("  이미 반영돼 있다 — 변경 없음")
        return 0
    with open(CONTRACT, "w", encoding="utf-8") as f:
        f.write(updated)
    print("  ✅ LotStatusTransition.actionCode — 실행 경로를 서버가 알려 준다 (질문2)")
    print("  ✅ LotQualityStatus.versionNo — 대량 보류의 토큰 (질문3)")
    print("  ✅ lot-holds/{id} ETag 설명 정정 — 잠그는 대상은 LOT 이다 (질문4)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
