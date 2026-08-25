#!/usr/bin/env python3
"""검사 대기 큐의 조회 조건을 화면이 실제로 부르는 대로 고친다 — 구현팀 질의 omf-mes#170.

## 왜

`W-01-01`(IQC 수입검사·판정) 착수 중 구현팀이 멈췄다. 검사 대기 큐(좌측 1/3)의
조회 조건에서 **스펙과 계약이 서로 다른 말을 한다**고 물었고, 실측하니 둘 다 맞았다.

## 무엇을 한다 — 네 갈래

### 1. `requestedFrom`·`requestedTo` 를 **뺀다** — 부르는 화면이 0이다

`GET /quality/inspection-requests` 를 부르는 자리를 요구서 전수로 짚으면 **두 곳뿐이고
둘 다 `W-01-01` 이며 둘 다 기간을 보내지 않는다**(요구서 §3-1 — 대기 큐는
`inspectionTypeCode`+`statusCode`, LOT 스캔은 `lotId`).

⚠ **계약 설명이 함께 적은 `W-03-05` 는 이 경로를 목록 조회로 부르지 않는다.**
그 화면의 필터·조회는 `GET /quality/inspection-results` 이고(요구서 §3-5),
§3 의 「기간 ⚠필수」는 **`inspectedFrom`/`inspectedTo` — 검사일 축**이다.
「검사 목록의 1층」은 **의뢰가 결과의 상위 계층**이라는 데이터 구조를 가리킨 말이지
호출이 아니었는데, 그 문장이 기간 파라미터와 나란히 놓여 오해를 낳았다.

⭐ **그럼 왜 있었나 — 패턴 상속이다.** `inspection_request` 를 「업무 문서 형」으로
분류하면서 그 형이 가진 성질 「조회 = 기간 필터(L-3)」이 화면 확인 없이 따라 내려왔다
(`uiux/2026-08-12-API스펙-03품질/01-리소스도출.md` §2-1). 그래서 이 계약에서
**유일하게 근거가 화면이 아니라 조항인 파라미터**였다 — 다른 질의는 전부
`근거: W-xx §n` 을 달고 있다. **근거 자리에 화면이 없는 것 자체가 증상이었다.**

⛔ **공유계약 L-3 의 강제 근거도 이 경로에 성립하지 않는다.** L-3 이 「가능/불가의
문제」라 못박은 대상은 **파티션 테이블**인데, 물리 모델 전체에서 `PARTITION BY` 는
`inventory.inventory_transaction`·`audit.audit_event` **둘뿐이고**
`quality.inspection_request` 는 파티션 테이블이 아니다(DDL 실측).

무제한 조회 위험도 없다 — 대기 큐는 아래 `pendingOnly` 로 유계이고 `page`·`size` 가 있다.

### 2. `pendingOnly` 를 **신설**한다 — 큐는 상태 «하나»가 아니다

스펙 §3 의 좌측 큐는 **「대기」와 「진행」을 함께** 보인다. `statusCode` 하나로는
못 고른다. 게다가 **검사 의뢰 상태 코드값은 아직 확정되지 않았고**(물리 모델 시드
코드그룹은 `OPERATION_POLICY`·`INVENTORY_STATUS` 둘뿐 · §8-1 이 종결한 것은
판정 3값·LOT 상태 4값이지 의뢰 상태가 아니다), 확정되더라도 **화면이 값을 고정하는
것은 금지**다(공유계약 G-6 · client#85 §6 「판정 값 목록을 화면에 고정하지 말 것」).

⭐ **선례가 둘 있다** — 「아직 안 끝난 것」을 코드값 열거 없이 불리언으로 표현한다.

    GET /app/approval-requests      pendingOnly    「참이면 아직 끝나지 않은 요청만」
    GET /logistics/stock-transfers  inTransitOnly  「반출됐으나 도착하지 않은 건만」

이러면 **화면이 상태 코드값을 몰라도 큐를 그린다** — 코드값 확정을 기다리지 않는다.

### 3. `supplierId` 를 **신설**한다 — 화면이 스스로 못 건다

스펙 §3 좌측 큐 필터가 「품목·공급사」인데 계약에 공급사 질의가 없었다.
품목은 `itemId` 로 걸리지만 **공급사는 화면이 걸 수 없다** — `trace.lot` 에 공급사
컬럼이 없고, `lot.source_type_code`/`source_id`(다형 참조 = 한 칸이 상황에 따라
여러 표를 가리킨다) → `logistics.inbound_receipt.supplier_id` 로 **2단 조인**해야 닿는다.
서버가 푸는 수밖에 없다.

⭐ 이름·타입은 선례 그대로다 — `logistics-01자재창고.json` 이 이미 네 경로
(`/logistics/asns`·`/goods-issues`·`/inbound-receipts`·`/purchase-orders`)에서
`supplierId: integer(int64)` 를 쓴다.

⛔ **`q` 를 넓히지 않는다.** 구현팀이 제시한 셋째 안(「`q` 가 공급사도 훑는다」)은
택하지 않았다 — `q` 는 「의뢰번호 검색」으로 이미 좁게 정의돼 있고, 범위를 넓히면
**인덱스 없는 다형 조인이 검색어마다 돈다**. 대신 `q` 의 검색 범위를 설명에
명시한다(구현팀이 「그렇다면 범위를 적어 달라」고 요청한 자리다).

### 4. `inspectedFrom`·`inspectedTo` — **필수로 «올리지» 않는다.** 조건부다

같은 결함(설명은 「기간 필수」인데 스키마에 `required` 없음)이 `GET
/quality/inspection-results` 에도 있다. ⚠ **다만 성격이 다르다** — 이쪽은
`W-03-05` §3 에 「기간 ⚠필수」가 실제로 그려져 있어 **화면 요구가 진짜 있다.**

⛔ **그렇다고 `required: true` 로 올리면 다른 화면이 깨진다.** `W-01-01` §5-3
(재검사 — 이전 회차를 읽기 전용으로 보인다)이 이 목록을 `inspectionRequestId` 로
부르는데, `GET /quality/inspection-requests/{id}` 는 회차를 품지 않고
`InspectionRequest` 만 내린다(실측). **한 의뢰의 회차를 읽는 데 기간을 지어내게 된다** —
#170 이 지적한 것과 정확히 같은 사고다.

⭐ **그래서 「둘 중 하나는 있어야 한다」로 적는다.** 형이 표현하지 못하는 조건부
필수라 **설명이 말하고 서버가 400 으로 막는다.**

    inspectionRequestId 가 있으면  → 한 의뢰의 회차. 기간을 보내지 않는다
    없으면(전 이력 조회)          → 기간이 필수다 (W-03-05 §3 · L-3 일반 층)
    둘 다 없으면                  → 400

쓰기: python3 deliverables/openapi/patch-170-inspection-request-query.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

QUALITY = "quality-03품질.json"
REQUESTS = "/quality/inspection-requests"
RESULTS = "/quality/inspection-results"

# 파일마다 직렬화 형식이 다르다 — 읽을 때 재어 두고 쓸 때 그대로 돌려준다
FORMAT = {}


def measure(raw):
    """원본에서 들여쓰기 폭과 끝 개행 여부를 잰다."""
    second = raw.split("\n")[1] if "\n" in raw else ""
    return {
        "indent": len(second) - len(second.lstrip(" ")) or 1,
        "newline": raw.endswith("\n"),
    }


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        raw = fh.read()
    FORMAT[name] = measure(raw)
    return json.loads(raw)


def save(name, spec):
    """⚠ 원본과 «같은 직렬화»로 쓴다 — 형식이 어긋나면 손대지 않은 자리까지 diff 에 든다."""
    fmt = FORMAT.get(name) or {"indent": 1, "newline": False}
    body = json.dumps(spec, ensure_ascii=False, indent=fmt["indent"])
    if fmt["newline"]:
        body += "\n"
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as fh:
        fh.write(body)


def params_of(spec, path):
    return spec["paths"][path]["get"]["parameters"]


def find(params, name):
    for idx, p in enumerate(params):
        if p.get("name") == name:
            return idx, p
    return -1, None


# ── 1. 뺄 것 ────────────────────────────────────────────────────────────────
DROP = ("requestedFrom", "requestedTo")


def drop_period(spec, log):
    params = params_of(spec, REQUESTS)
    for name in DROP:
        idx, _ = find(params, name)
        if idx < 0:
            log.append("   · %s — 이미 없다" % name)
            continue
        params.pop(idx)
        log.append("   ✂ %s 제거 — 부르는 화면 0" % name)


# ── 2·3. 더할 것 ────────────────────────────────────────────────────────────
PENDING_ONLY = {
    "name": "pendingOnly",
    "in": "query",
    # ⚠ example 은 schema «안»에 둔다 — 이 계약 파일의 지역 관례다
    "schema": {"type": "boolean", "default": False, "example": True},
    "description": (
        "참이면 아직 끝나지 않은 의뢰만 — 대기·진행이 함께 들어온다. "
        "⭐ 검사 대기 큐가 이것이다(W-01-01 §3 좌단은 「대기」와 「진행」을 함께 보인다 — "
        "상태 하나로는 못 고른다). ⛔ 화면이 상태 코드값을 고정하지 않게 하려는 것이 "
        "목적이다(공유계약 G-6). 선례: /app/approval-requests pendingOnly · "
        "/logistics/stock-transfers inTransitOnly. 근거: W-01-01 §3 · omf-mes#170"
    ),
}

SUPPLIER_ID = {
    "name": "supplierId",
    "in": "query",
    "schema": {"type": "integer", "format": "int64", "example": 1001},
    "description": (
        "공급사. ⚠ 서버가 푼다 — trace.lot 에 공급사 컬럼이 없어 "
        "lot.source_type_code/source_id(다형 참조 = 한 칸이 상황에 따라 여러 표를 "
        "가리킨다) → logistics.inbound_receipt.supplier_id 로 2단 조인이다. "
        "화면은 걸 수 없다. 근거: W-01-01 §3 좌단 필터 「품목·공급사」 · omf-mes#170"
    ),
}

# ⚠ 「어디에」 넣는가 — 질의는 화면이 읽는 순서로 둔다(유형 → 상태 → 대상 → 검색 → 페이지)
INSERT_AFTER = {
    "pendingOnly": "statusCode",
    "supplierId": "itemId",
}


def add_params(spec, log):
    params = params_of(spec, REQUESTS)
    for new in (PENDING_ONLY, SUPPLIER_ID):
        idx, _ = find(params, new["name"])
        if idx >= 0:
            params[idx] = new
            log.append("   ↻ %s 갱신" % new["name"])
            continue
        anchor, _ = find(params, INSERT_AFTER[new["name"]])
        at = anchor + 1 if anchor >= 0 else len(params)
        params.insert(at, new)
        log.append("   ＋ %s 신설 (%s 뒤)" % (new["name"], INSERT_AFTER[new["name"]]))


# ── 설명을 고칠 것 ──────────────────────────────────────────────────────────
STATUS_CODE_DESC = (
    "검사 의뢰 상태로 좁힌다. ⛔ 값 목록을 화면에 고정하지 않는다 — 06 계약 "
    "GET /mdm/code-values 로 채운다(공유계약 G-6). ⚠ 「아직 안 끝난 것」을 보려면 "
    "이것이 아니라 pendingOnly 를 쓴다 — 큐는 상태 하나가 아니다. 근거: W-01-01 §3"
)

Q_DESC = (
    "의뢰번호 검색. ⛔ 범위는 inspection_request_no «하나»다 — 공급사·품목은 훑지 "
    "않는다(넓히면 인덱스 없는 다형 조인이 검색어마다 돈다). 공급사로 좁히려면 "
    "supplierId 를, 품목은 itemId 를 쓴다. 근거: omf-mes#170 질문 2"
)

REQUESTS_OP_DESC = (
    "W-01-01 검사 대기 큐가 부른다 — inspectionTypeCode+pendingOnly 로 큐를 그리고, "
    "LOT 스캔 뒤에는 lotId 로 한 건을 집는다. "
    "⚠ W-03-05 검사 목록은 이 경로가 아니라 GET /quality/inspection-results 를 부른다 "
    "— 여기서 말한 「1층」은 의뢰가 결과의 상위 계층이라는 데이터 구조이지 호출이 "
    "아니다(그 문장이 기간 파라미터와 나란히 놓여 omf-mes#170 을 낳았다). "
    "근거: W-01-01 §3 · 요구서 §3-1 · W-03-05 §5-1"
)

INSPECTED_FROM_DESC = (
    "기간 시작. ⭐ 조건부 필수 — inspectionRequestId 없이 전 이력을 훑을 때는 "
    "«반드시» 보낸다(W-03-05 §3 이 화면에서 「기간 ⚠필수」로 강제한다 · 공유계약 L-3 "
    "일반 층 — 무제한이면 원장이 누적된 뒤 화면이 멎는다). "
    "⛔ inspectionRequestId 로 «한 의뢰의 회차»를 읽을 때는 보내지 않는다 — "
    "W-01-01 §5-3(재검사 이전 회차 표시)이 그 경로이고, 거기에 기간을 요구하면 "
    "화면이 없는 기간을 지어내게 된다. 형이 조건부 필수를 표현하지 못해 설명이 말한다"
)

INSPECTED_TO_DESC = (
    "기간 끝. inspectedFrom 과 한 쌍이다 — 함께 보내거나 함께 생략한다"
)

RESULTS_OP_DESC_TAIL = (
    " ⛔ inspectionRequestId 도 기간(inspectedFrom·inspectedTo)도 없으면 400 이다 "
    "— 둘 중 하나로 반드시 유계여야 한다(공유계약 L-3 · omf-mes#170)."
)


def retouch(spec, log):
    reqs = params_of(spec, REQUESTS)
    for name, desc in (("statusCode", STATUS_CODE_DESC), ("q", Q_DESC)):
        idx, p = find(reqs, name)
        if idx < 0:
            log.append("   ⚠ %s 없음 — 건너뜀" % name)
            continue
        p["description"] = desc
        log.append("   ✎ %s 설명" % name)

    spec["paths"][REQUESTS]["get"]["description"] = REQUESTS_OP_DESC
    log.append("   ✎ %s 오퍼레이션 설명 — 「1층」의 뜻을 푼다" % REQUESTS)

    res = params_of(spec, RESULTS)
    for name, desc in (
        ("inspectedFrom", INSPECTED_FROM_DESC),
        ("inspectedTo", INSPECTED_TO_DESC),
    ):
        idx, p = find(res, name)
        if idx < 0:
            log.append("   ⚠ %s 없음 — 건너뜀" % name)
            continue
        p["description"] = desc
        # ⛔ required: true 를 «넣지 않는다» — W-01-01 §5-3 회차 조회가 깨진다
        p.pop("required", None)
        log.append("   ✎ %s 설명 — 조건부 필수임을 적는다" % name)

    op = spec["paths"][RESULTS]["get"]
    base = op.get("description", "")
    if RESULTS_OP_DESC_TAIL.strip() not in base:
        op["description"] = (base.rstrip() + RESULTS_OP_DESC_TAIL).strip()
        log.append("   ✎ %s 오퍼레이션 설명 — 400 규칙" % RESULTS)


# ── 왕복 검사 ───────────────────────────────────────────────────────────────
def roundtrip():
    """직렬화가 원본과 바이트 동일한지 본다 — 어긋나면 손대지 않은 자리까지 diff 에 든다."""
    path = os.path.join(HERE, QUALITY)
    with open(path, encoding="utf-8") as fh:
        before = fh.read()
    fmt = measure(before)
    after = json.dumps(json.loads(before), ensure_ascii=False, indent=fmt["indent"])
    if fmt["newline"]:
        after += "\n"
    if before != after:
        raise SystemExit(
            "⛔ 직렬화가 원본과 다르다 (원본 %d자 ↔ 재직렬화 %d자)" % (len(before), len(after))
        )
    print("✅ 왕복 검사 — 재직렬화가 원본과 바이트 동일하다")


def main():
    log = []
    spec = load(QUALITY)

    print("== 1. requestedFrom·requestedTo 제거 — 부르는 화면 0 ==")
    drop_period(spec, log)

    print("== 2·3. pendingOnly·supplierId 신설 ==")
    add_params(spec, log)

    print("== 4. 설명 정정 — statusCode·q·기간·오퍼레이션 ==")
    retouch(spec, log)

    save(QUALITY, spec)
    roundtrip()

    print()
    for line in log:
        print(line)

    # 최종 상태를 그대로 보인다 — 「무엇을 셌는가」가 보고에 남아야 한다
    print("\n== 최종 질의 — GET %s ==" % REQUESTS)
    for p in params_of(load(QUALITY), REQUESTS):
        print("   %-20s %s" % (p["name"], p.get("description", "")[:60]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
