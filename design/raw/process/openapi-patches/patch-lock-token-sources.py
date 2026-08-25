#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""남은 자원 열 곳의 저장 충돌 토큰 원천을 선언한다. 멱등.

왜 필요한가
-----------
`If-Match` 를 필수로 받으면서 **그 값을 받을 곳이 선언되지 않은** 오퍼레이션이
17건 남아 있었다. 그대로 두면 구현팀이 그 화면에 착수하는 날 막힌다 —
「토큰이 있으면 싣고 없으면 요청을 만들지 않는」 형태로 짓기 때문이다.
거래처 역할과 입고 취소가 그렇게 드러났다.

⭐ 원천 판정 — 기준은 하나다
-----------------------------
**잠그는 «대상»과 버전 축을 일치시킨다**(공유계약 G-30 의 원리).

실제로 갈리는 자리는 **부모가 밖에서 «되받는» 자료일 때**다. 동기화마다
판이 바뀌어 **고치지도 않은 사용자가 충돌을 본다** — 거래처 역할이 그 사례라
자식 집합(역할 목록)을 원천으로 잡았다.

열 곳을 전수로 봤다. **되받는 경로(:resync·:acknowledge·:receive)를 가진
부모는 0곳**이라 **전부 자기 상세 조회가 원천**이다.

⚠ 공지만 한 번 더 봤다
----------------------
`app.notice` 에는 「확인」(:acknowledge) 액션이 있어 되받는 것처럼 보인다.
**아니다** — 읽은 사람이 «스스로» 누르는 것이고 밖에서 오지 않는다.

다만 **판이 움직이면 안 되는 자리**가 하나 있다. 공지 수정의 잠금 대상은
**본문**인데, 확인이 쌓일 때마다 판이 오르면 **관리자가 본문을 고치려 할 때
「남이 먼저 고쳤다」를 보게 된다.** 고친 사람은 없고 «읽은» 사람만 있는데도.

→ 그래서 계약이 **「확인은 판을 올리지 않는다」**를 명시한다. 모델이 따라온다.

쓰기
----
    python3 deliverables/openapi/patch-lock-token-sources.py
"""
from __future__ import annotations

import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# 파일 → 선언을 붙일 조회 경로. 전부 «자기 상세»다.
TARGETS: dict[str, list[str]] = {
    "app-공통.json": ["/app/notices/{noticeId}", "/app/notification-subscriptions"],
    "mdm-기준정보.json": ["/mdm/terminals/{terminalId}",
                       "/mdm/terminals/{terminalId}/processes"],
    "production-02생산실행.json": ["/planning/production-plans/{productionPlanId}",
                                "/production/work-orders/{workOrderId}"],
    "quality-03품질.json": ["/quality/inspection-results/{inspectionResultId}",
                          "/quality/lot-holds/{lotHoldId}"],
    "shipment-04제품출하.json": ["/logistics/shipments/{shipmentId}",
                              "/quality/nonconformances/{nonconformanceId}"],
}

# 공지에만 붙는 단서 — 확인이 판을 올리면 「고친 사람 없는 충돌」이 난다.
NOTICE_NOTE = (
    " ⭐ 확인(:acknowledge)은 이 판을 «올리지 않는다» — 잠그는 대상은 공지 «본문»이고 "
    "확인은 별개 기록이다. 확인이 쌓일 때마다 판이 오르면 관리자가 본문을 고치려 할 때 "
    "「남이 먼저 고쳤다」를 보게 된다. 고친 사람은 없고 읽은 사람만 있는데도. "
    "근거: 공유계약 G-30 — 잠그는 대상과 버전 축을 일치시킨다."
)


def find_model(doc: dict) -> dict | None:
    """이 계약 안에 이미 있는 ETag 선언을 찾아 베낀다.

    ⛔ 문구를 손으로 쓰지 않는다 — 30곳과 갈리고, 갈린 것은 나중에 아무도
    못 찾는다.
    """
    for ops in doc.get("paths", {}).values():
        for op in ops.values():
            if not isinstance(op, dict):
                continue
            h = (op.get("responses", {}).get("200", {}) or {}).get("headers")
            if h and "ETag" in h:
                return h
    return None


def detect_indent(original: str, doc: dict) -> int | None:
    body = original.rstrip("\n")
    for candidate in (1, 2, 4):
        if json.dumps(doc, ensure_ascii=False, indent=candidate) == body:
            return candidate
    return None


def canonical_model() -> dict | None:
    """어느 계약에도 선언이 없을 때 쓸 원본 — 자재창고에서 가져온다."""
    path = os.path.join(HERE, "logistics-01자재창고.json")
    with open(path, encoding="utf-8") as f:
        return find_model(json.load(f))


def main() -> int:
    fallback = canonical_model()
    if not fallback:
        print("⛔ 베낄 선언을 어디서도 못 찾았다", file=sys.stderr)
        return 1

    changed = 0
    for name, paths_to_touch in TARGETS.items():
        full = os.path.join(HERE, name)
        original = open(full, encoding="utf-8").read()
        doc = json.loads(original)
        indent = detect_indent(original, doc)
        if indent is None:
            print(f"⛔ {name} 들여쓰기를 알아낼 수 없다 — 덮어쓰지 않는다",
                  file=sys.stderr)
            return 1
        tail = original[len(original.rstrip("\n")):]

        model = find_model(doc) or fallback
        for path in paths_to_touch:
            op = (doc["paths"].get(path) or {}).get("get")
            if op is None:
                print(f"⛔ {name} 에 {path} GET 이 없다", file=sys.stderr)
                return 1
            headers = json.loads(json.dumps(model))
            if path == "/app/notices/{noticeId}":
                # ⛔ 덧붙이지 않고 «통째로 다시 조립»한다 — 덧붙이기는 문구를
                #    고치는 순간 멱등이 무너진다(실제로 그렇게 깨졌다).
                base = headers["ETag"]["description"].split(" ⭐ 확인(")[0]
                headers["ETag"]["description"] = base + NOTICE_NOTE
            op["responses"]["200"]["headers"] = headers

        updated = json.dumps(doc, ensure_ascii=False, indent=indent) + tail
        if updated != original:
            open(full, "w", encoding="utf-8").write(updated)
            changed += 1
            print(f"  ✅ {name} — {len(paths_to_touch)}곳")

    if not changed:
        print("  이미 반영돼 있다 — 변경 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
