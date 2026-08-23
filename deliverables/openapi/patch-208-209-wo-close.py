#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W/O 마감(`:close`)의 잠금 토큰 자리와 잔량 처분 필수 조건을 고친다. 멱등.

무엇을 고치나
-------------
    #208  POST …:close  → `If-Match` 요청 헤더 (필수)
    #209  WorkOrderClose.remainderDispositionCode → 조건부 필수로 완화 + 검증 규칙 명시

⭐ #208 — 잠금 토큰을 실을 자리가 없었다
----------------------------------------
마감 화면(`W-02-05`) §6 예외표는 **저장 충돌을 이미 확정**해 두었다.

    | **저장 충돌**(B-1) | `409` + 다시 불러오기 |

계약에는 `409` 는 있는데 **`If-Match` 가 없었다.** 충돌을 응답할 자리는 있고
충돌을 «감지할 근거»를 보낼 자리가 없는 상태다 — 서버가 무엇과 무엇을
대조해 409 를 내는지 정해지지 않는다.

**토큰 원천 = `GET /production/work-orders/{workOrderId}` 의 `ETag`** 다.
그 선언은 이미 있다(실측). 구현팀이 `#208` 에서 물은 그대로다.

⭐ 필수다 — 선택이 아니다. 형제 전이 `:hold`·`:resume` 는
`IfMatchVersionOptional` 인데 **그 둘은 POP 오프라인 대상**이라 큐가 토큰을
싣지 않기 때문이다(공유계약 `C-9`). 마감은 **관리웹 온라인 전제**이고
(`W-02-05` §6 — 「오프라인 ⛔ 해당 없음」), **되돌릴 수 없는 전이**다
(재오픈 금지 · R83). 느슨하게 둘 이유가 없다.

⚠ 형제 전이를 함께 손대지 않았다 — 조용히 줄인 것이 아니라 밝혀 둔다.
`:cancel`·`:release` 도 `If-Match` 가 없으나 **그 둘을 요구하는 스펙 줄이
없다.** 저장 충돌 보호는 자동으로 붙이지 않는다(05 계약 2단계 §7) — 근거가
생기면 별건으로 본다.

⭐ #209 — 「이월/소멸」은 미달일 때만 고르는 것이다
--------------------------------------------------
`W-02-05` §5-7 액션표 원문:

    | 잔량 처분 선택(이월/소멸) | **미달 판정일 때만** |
    | 사유 선택                 | 미달·초과일 때 |
    | **마감** | 잔량 처분 선택됨(미달 시) AND 사유 선택됨 |

그런데 계약은 `remainderDispositionCode` 를 **무조건 필수**로 두었다. 정상·
초과 마감에서도 「이월」이나 「소멸」 중 하나를 골라 보내야 하는데 **둘 다
뜻이 맞지 않는다** — 넘길 잔량도 없애 버릴 잔량도 없다. 구현팀이 「추정하지
않겠다」고 멈춘 것이 옳다.

**고친다 — 조건부 필수로 내린다.** 평면적인 `required` 로는 「미달일 때만」을
적을 수 없으므로 목록에서 빼고 **규칙을 설명문과 오퍼레이션 설명에 못박는다.**

⛔ 정상·초과에 쓸 세 번째 값을 만들지 않았다
--------------------------------------------
`NONE`·`NOT_APPLICABLE` 같은 값을 넣으면 **없는 업무 개념이 생긴다.** R81 이
정한 것은 「미달 잔량 = 이월/소멸」 둘뿐이다(✓확정 QA #27). 자리가 있다고
채우지 않는다(공유계약 `A-21`). **정상·초과는 이 칸을 비워 보낸다.**

⭐ 판정은 서버가 낸다 — 그래서 서버가 검증할 수 있다
----------------------------------------------------
`#207` 로 마감 3분류 판정(`completionJudgmentCode`)이 응답에 실린다. 서버가
같은 식으로 판정하므로 **본문 조합 검증이 성립한다** — 화면이 보낸 판정을
믿는 것이 아니라 서버가 스스로 낸 판정과 본문을 대조한다.

⚠ 「정상」의 폭(허용 오차)이 정해지면 **미달의 경계가 움직인다.** 규칙 자체는
그대로고 경계만 서버 정책이 정한다(`W-02-05` §5-1·§8-1).

쓰기
----
    python3 deliverables/openapi/patch-208-209-wo-close.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "production-02생산실행.json")
CLOSE = "/production/work-orders/{workOrderId}:close"

CLOSE_DESC = (
    "잔량 처분을 함께 정한다. 미달 슬롯은 이 시점에 자동 폐번된다. "
    "ERP 실제 전송만 트랜잭션 밖이다. 근거: W-02-05 §5 · R27·R82\n\n"
    "⭐ 저장 충돌 보호 — If-Match 는 필수다. 토큰은 "
    "GET /production/work-orders/{workOrderId} 의 ETag 를 그대로 싣는다. "
    "마감은 관리웹 온라인 전제이고 되돌릴 수 없는 전이라(재오픈 금지 · R83) "
    "형제 전이 :hold·:resume 처럼 선택으로 두지 않는다 — 그 둘은 POP 오프라인 "
    "대상이라 큐가 토큰을 싣지 못해 선택이다(공유계약 C-9). 근거: W-02-05 §6\n\n"
    "⭐ 본문 검증 — 서버가 스스로 낸 마감 3분류 판정과 본문을 대조한다"
    "(판정은 WorkOrderProgress.completionJudgmentCode 와 같은 식이다).\n"
    "  · 미달인데 remainderDispositionCode 가 없다 → 400\n"
    "  · 정상·초과인데 remainderDispositionCode 가 있다 → 400 "
    "(넘길 잔량도 없앨 잔량도 없다)\n"
    "  · 미달·초과인데 reasonCode 가 없다 → 400 (미달·초과 사유는 R80 이 요구한다)\n"
    "  · 정상은 두 칸을 다 비운다\n"
    "⚠ 「정상」의 폭(허용 오차)은 서버 정책이 정한다 — 규칙은 그대로고 "
    "미달의 경계만 움직인다(W-02-05 §5-1·§8-1)"
)

DISPOSITION_DESC = (
    "잔량 처분 — 이월 / 소멸. ⭐ 미달 판정일 때만 보낸다(조건부 필수). "
    "정상·초과 마감에서는 이 칸을 «비운다» — 넘길 잔량도 없앨 잔량도 없어 "
    "두 값 중 어느 것도 뜻이 맞지 않는다. ⛔ 그래서 정상·초과용 세 번째 값을 "
    "두지 않았다 — 없는 업무 개념을 만들게 된다(공유계약 A-21 · R81 은 "
    "「미달 잔량 = 이월/소멸」 둘만 정했다 · ✓확정 QA #27). "
    "평면적인 required 로는 「미달일 때만」을 적을 수 없어 목록에서 뺐고 "
    "서버가 판정과 대조해 검증한다. 근거: W-02-05 §5-2·§5-7 · omf-mes#209"
)

REASON_DESC = (
    "미달·초과 사유 — work_order.completion_variance_reason_code 에 실린다. "
    "⭐ 미달·초과일 때 조건부 필수이고 정상이면 비운다(W-02-05 §5-7 · R80)"
)


def detect_indent(original: str, doc: dict):
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
        print("⛔ 들여쓰기를 알아낼 수 없다 — 덮어쓰지 않는다", file=sys.stderr)
        return 1
    tail = original[len(original.rstrip("\n")):]

    if "IfMatchVersion" not in doc["components"].get("parameters", {}):
        print("⛔ IfMatchVersion 파라미터 정의가 이 계약에 없다", file=sys.stderr)
        return 1

    # ── #208 잠금 토큰을 실을 자리 ────────────────────────────────────
    close = doc["paths"][CLOSE]["post"]
    params = close.setdefault("parameters", [])
    if not any(p.get("$ref", "").endswith("/IfMatchVersion") for p in params):
        # 멱등키 바로 뒤 — 형제 전이(:hold)와 같은 차례로 둔다.
        idx = max((i for i, p in enumerate(params)
                   if p.get("$ref", "").endswith("/IdempotencyKey")), default=len(params) - 1)
        params.insert(idx + 1, {"$ref": "#/components/parameters/IfMatchVersion"})
    close["description"] = CLOSE_DESC

    # 토큰을 «받을 곳»이 실제로 선언돼 있는지 확인한다 — 19건 사고의 재발 방지.
    src = doc["paths"]["/production/work-orders/{workOrderId}"]["get"]
    if "ETag" not in (src["responses"]["200"].get("headers") or {}):
        print("⛔ 토큰 원천(W/O 상세 조회 ETag)이 선언돼 있지 않다", file=sys.stderr)
        return 1

    # ── #209 잔량 처분을 조건부 필수로 ────────────────────────────────
    schema = doc["components"]["schemas"]["WorkOrderClose"]
    schema["properties"]["remainderDispositionCode"]["description"] = DISPOSITION_DESC
    schema["properties"]["reasonCode"]["description"] = REASON_DESC
    schema["required"] = [r for r in schema.get("required", [])
                          if r != "remainderDispositionCode"]
    if not schema["required"]:
        del schema["required"]

    updated = json.dumps(doc, ensure_ascii=False, indent=indent) + tail
    if updated == original:
        print("  이미 반영돼 있다 — 변경 없음")
        return 0
    open(CONTRACT, "w", encoding="utf-8").write(updated)
    print("  ✅ :close 에 If-Match(필수) · 검증 규칙 명시 (#208)")
    print("  ✅ remainderDispositionCode 조건부 필수로 완화 (#209)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
