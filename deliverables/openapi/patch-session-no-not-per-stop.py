#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`sessionNo` 설명을 바로잡고 `stopReasonCode` 두 자리에 「쓰지 않는다」를 적는다. 멱등.

무엇이 틀렸나
-------------
`WorkSession.sessionNo` 설명이 「**중단·재개마다 는다**」였다. 근거로 적힌
`P-02-01` §5-4 가 「재개하면 새 세션」이라 적었기 때문인데, **그 절이 틀렸다.**

⛔ **화면 둘이 같은 사건을 반대로 설계해 뒀다** — 12일간 아무도 못 봤다.

    P-02-01 §5-4   중단하면 세션이 닫힌다 · 재개하면 새 세션(session_no + 1)
    P-02-10 §5-4   같은 세션의 status 만 바뀐다 · 재개해도 같은 세션

✅ **`P-02-10` 이 맞다 — 실측 다섯**

    ① 이 계약에 `:resume` 액션이 없다 — 세션은 POST 로 열고 `:end` 로 닫는 게 전부다.
       재개를 표현할 길은 `POST …/events`(eventTypeCode=RESUME) 뿐이다
    ② 논리 모델 §9.7 이 work_session_event 를 「작업 시작·중지·재개·종료 이력」으로
       정의했다 — 재개가 새 세션이면 「재개 사건」이 있을 이유가 없다
    ③ work_session.status_code 가 「중단」을 담는다 — 중단이 곧 세션 종료라면 불필요하다
    ④ P-02-10 §3 목업이 한 세션 이력에 시작→중단→재개를 나란히 그린다
    ⑤ P-02-01 자신의 §8 미결 2 가 「ended_at 과 status_code 를 둘 다 쓴다」고 적었다

⚠ **P-02-01 이 근거로 든 결정 14 가 그 결론을 받쳐 주지 않는다** — 「재시작은 상태가
아니라 중단→진행 전이 이벤트」는 ① **작업지시 상태 그래프**에 대한 문장이고 ② 「전이
이벤트」는 **같은 것의 상태가 바뀐다**는 뜻이라 오히려 반대쪽을 지지한다.

무엇을 하나
-----------
① `WorkSession.sessionNo` 설명 정정 — 「세션을 새로 열 때마다 는다」
② `WorkSession.stopReasonCode`·`WorkSessionUpdate.stopReasonCode` 에 「쓰지 않는다」를
   적는다 — 값 목록을 안 정한 게 아니라 **비우기로 정했다**(공유계약 A-21·A-25)

⛔ **필드를 지우지 않는다** — 물리 컬럼이 실재하므로 계약에서 빼면 「없는 칸」으로
읽힌다. **있는데 안 쓴다**를 설명으로 적는 것이 A-21 이 말하는 방식이다.

근거: 공유계약 v3.9 `A-25`·`G-16` 보완 · P-02-01 §5-4(v0.2 정정) · P-02-10 §5-4
"""
import json
import sys

SPEC = "production-02생산실행.json"

SESSION_NO_DESC = (
    "그 작업지시에서 세션을 «새로 열 때마다» 는다(작업 완료·교대 마감으로 :end 한 뒤 다시 시작하는 경우). "
    "⛔ 중단·재개로는 늘지 않는다 — 재개는 같은 세션에 RESUME 사건을 적재하고 status_code 를 되돌린다. "
    "uq(workOrderId, sessionNo). 근거: 공유계약 G-16 보완 · P-02-01 §5-4(v0.2 정정)"
)

STOP_REASON_DESC = (
    "⛔ 쓰지 않는다 — 비운다. 값 목록을 못 정한 것이 아니라 «비우기로 정했다». "
    "세션 종료 사유를 요구한 문서가 없고(요구 원천은 「작업중단 사유」 한 줄이며 그 뜻은 "
    "work_session_event.reason_code 가 받는다) 세션 종료 화면도 인벤토리에 없다. "
    "근거: 공유계약 A-21(자리가 있다고 채우지 않는다) · A-25"
)


def main() -> int:
    with open(SPEC, encoding="utf-8") as f:
        spec = json.load(f)

    schemas = spec["components"]["schemas"]
    changed = []

    ws = schemas.get("WorkSession", {}).get("properties", {})
    if "sessionNo" in ws and ws["sessionNo"].get("description") != SESSION_NO_DESC:
        ws["sessionNo"]["description"] = SESSION_NO_DESC
        changed.append("WorkSession.sessionNo")

    for name in ("WorkSession", "WorkSessionUpdate", "WorkSessionEnd", "WorkSessionCreate"):
        props = schemas.get(name, {}).get("properties", {})
        if "stopReasonCode" in props and props["stopReasonCode"].get("description") != STOP_REASON_DESC:
            props["stopReasonCode"]["description"] = STOP_REASON_DESC
            changed.append(f"{name}.stopReasonCode")

    if not changed:
        print("이미 반영돼 있다 — 바꾼 것 없음(멱등)")
        return 0

    with open(SPEC, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
        f.write("\n")

    print("고친 자리", len(changed))
    for c in changed:
        print("  -", c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
