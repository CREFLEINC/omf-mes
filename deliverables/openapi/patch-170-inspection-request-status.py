#!/usr/bin/env python3
"""검사 의뢰 상태 값 목록을 계약에 싣는다 — 확정 2026-08-21 · omf-mes#170.

## 왜

`quality.inspection_request.status_code` 는 **값 목록이 없었다.** 계약은
`{"type":"string","example":"값"}` 자리표시였고, 물리 모델 시드 코드그룹에도
없었다(있는 것은 `OPERATION_POLICY`·`INVENTORY_STATUS` 둘뿐). §8-1 이 종결한 것은
**판정 3값·LOT 상태 4값**이지 **의뢰 상태**가 아니다.

⚠ **이것이 구현팀을 막고 있지는 않았다** — 앞선 패치가 `pendingOnly` 를 신설해
화면이 코드값을 몰라도 큐를 그리게 했다. 이 패치는 **그 다음 것**이다:
큐에서 「대기」와 「진행」을 배지로 가르려면 값이 있어야 한다.

## 확정 — 5값 (전문 근거 = uiux/2026-08-21-검사의뢰상태-확정/)

    REQUESTED    대기   의뢰가 만들어졌고 아직 아무도 손대지 않았다
    IN_PROGRESS  진행   검사가 시작됐다 — 임시 저장이 있다
    COMPLETED    완료   판정이 확정됐다
    SKIPPED      생략   검사를 하지 않기로 «승인»되어 종결됐다
    CANCELLED    취소   의뢰 자체가 «무효»가 됐다

⭐ **새 경로가 0이다** — 다섯 전이 전부 이미 있는 액션의 부수 효과다.

## 무엇을 한다 — 세 갈래

1. **`InspectionRequest.statusCode`** — 값 목록·전이·소관을 설명에 싣고
   자리표시 `example: "값"` 을 실제 값으로 바꾼다
2. **질의 `statusCode`** — 값 목록을 적되 「안 끝난 것」은 `pendingOnly` 를 쓰라는
   안내를 유지한다
3. **질의 `pendingOnly`** — ⭐ **정의를 값으로 못박는다.** 서버 구현이 기준으로 삼는다

        pendingOnly=true  ⇔  status_code ∈ { REQUESTED, IN_PROGRESS }

## ⛔ enum 으로 못박지 않는다

확정했지만 `enum` 을 넣지 않는다 — 값 목록은 공통코드가 갖고 늘 수 있다
(공유계약 **G-2**·**G-6**). ⭐ **선례가 정확히 같다**: 판정 3값도 2026-08-07 에
확정됐지만 `overallJudgmentCode` 는 「⛔ enum 으로 못박지 않는다」로 적혀 있다.

## ⚠ 표기가 형제 필드와 갈린다 — 알고 그렇게 둔다

`inspection_result.statusCode` 는 `["작성중","확정"]` 로 **한글**이다. 계약 7벌
enum **76개 중 한글은 그 1개뿐**이고 나머지 75개가 영문 대문자 스네이크다 —
**한글이 관례가 아니라 예외다.** 그렇다고 지금 고치면 **⛔ 이미 만든 것이 틀린다**
(그 필드의 `x-internal-note` 가 client#102·2026-08-12 를 인용한다). 예외는 두고
새로 정하는 것만 관례를 따른다. #170 회신에서 **먼저 밝혀** 두 번째 질의를 막는다.

쓰기: python3 deliverables/openapi/patch-170-inspection-request-status.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

QUALITY = "quality-03품질.json"
REQUESTS = "/quality/inspection-requests"

FORMAT = {}


def measure(raw):
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


# ── 확정 값 ─────────────────────────────────────────────────────────────────
VALUES = "REQUESTED(대기) · IN_PROGRESS(진행) · COMPLETED(완료) · SKIPPED(생략) · CANCELLED(취소)"

SCHEMA_DESC = (
    "검사 의뢰의 진행 상태 — 확정 5값: " + VALUES + ". "
    "⛔ enum 으로 못박지 않는다 — 값 목록은 공통코드가 갖고 늘 수 있다"
    "(공유계약 G-2·G-6). 표시명은 06 계약 GET /mdm/code-values 로 채운다. "
    "⭐ 전이는 전부 «이미 있는 액션의 부수 효과»다 — 새 경로가 없다: "
    "서버가 입하·실적·출하 시점에 REQUESTED 로 만들고 · 첫 임시 저장이 IN_PROGRESS "
    "(⛔ 「검사 시작」 액션을 두지 않는다 — 화면에 시작 버튼이 없다) · "
    ":confirm 이 COMPLETED · 재검사 회차 추가가 다시 IN_PROGRESS · "
    "W-01-02 긴급 IQC 생략 한도승인이 SKIPPED · 입고 취소(FR-IM-076)가 CANCELLED. "
    "⚠ SKIPPED 와 CANCELLED 를 합치지 않는다 — 앞은 검사를 안 하기로 «승인»된 정상 "
    "종결이고(LOT 은 Release 로 입고된다) 뒤는 의뢰가 «무효»가 된 것이다. "
    "합치면 「검사를 몇 건 생략했나」를 셀 수 없다. "
    "⚠ LOT 품질 상태(정상·불량·검사 대기·폐기)와 «다른 축»이다 — 같이 움직이지 않는다. "
    "근거: 확정 2026-08-21 · FR-QM-050 · omf-mes#170"
)

QUERY_STATUS_DESC = (
    "검사 의뢰 상태로 좁힌다 — 확정 5값: " + VALUES + ". "
    "⛔ 값 목록을 화면에 고정하지 않는다 — 표시명은 06 계약 GET /mdm/code-values 로 "
    "채운다(공유계약 G-6). ⚠ 「아직 안 끝난 것」을 보려면 이것이 아니라 pendingOnly 를 "
    "쓴다 — 큐는 상태 하나가 아니다. 근거: W-01-01 §3 · 확정 2026-08-21"
)

PENDING_ONLY_DESC = (
    "참이면 아직 끝나지 않은 의뢰만. ⭐ 정의를 값으로 못박는다 — "
    "pendingOnly=true ⇔ statusCode ∈ { REQUESTED, IN_PROGRESS }. "
    "⭐ 검사 대기 큐가 이것이다(W-01-01 §3 좌단은 「대기」와 「진행」을 함께 보인다 — "
    "상태 하나로는 못 고른다). ⛔ 화면이 상태 코드값을 고정하지 않게 하려는 것이 "
    "목적이다(공유계약 G-6). 선례: /app/approval-requests pendingOnly · "
    "/logistics/stock-transfers inTransitOnly. "
    "근거: W-01-01 §3 · omf-mes#170 · 확정 2026-08-21"
)

EXAMPLE = "REQUESTED"


def patch_schema(spec, log):
    prop = spec["components"]["schemas"]["InspectionRequest"]["properties"]["statusCode"]
    prop["description"] = SCHEMA_DESC
    prop["example"] = EXAMPLE
    # ⚠ 확정기록 «경로»는 공개 설명에 두지 않는다 — description 은 api.d.ts 로 나간다
    #    (check-public-safe.py 가 잡았다. 비공개 문서 경로는 x-internal-note 로 옮긴다)
    prop["x-internal-note"] = (
        "확정 전문: uiux/2026-08-21-검사의뢰상태-확정/검사의뢰상태-확정기록.md — "
        "표기 근거(계약 enum 76개 중 한글 1개) · SKIPPED/CANCELLED 분리 이유 · "
        "공통코드 시드 요청문이 그 문서에 있다"
    )
    assert "enum" not in prop, "⛔ enum 이 들어갔다 — G-2·G-6 위반"
    log.append("   ✎ InspectionRequest.statusCode — 값 5 · 전이 · 축 구분 (example: 값 → %s)" % EXAMPLE)


def patch_query(spec, log):
    params = spec["paths"][REQUESTS]["get"]["parameters"]
    for p in params:
        if p.get("name") == "statusCode":
            p["description"] = QUERY_STATUS_DESC
            p["schema"]["example"] = EXAMPLE
            assert "enum" not in p["schema"], "⛔ enum 이 들어갔다"
            log.append("   ✎ 질의 statusCode — 값 5")
        elif p.get("name") == "pendingOnly":
            p["description"] = PENDING_ONLY_DESC
            log.append("   ✎ 질의 pendingOnly — 정의를 값으로 못박는다")


def roundtrip():
    path = os.path.join(HERE, QUALITY)
    with open(path, encoding="utf-8") as fh:
        before = fh.read()
    fmt = measure(before)
    after = json.dumps(json.loads(before), ensure_ascii=False, indent=fmt["indent"])
    if fmt["newline"]:
        after += "\n"
    if before != after:
        raise SystemExit("⛔ 직렬화가 원본과 다르다")
    print("✅ 왕복 검사 — 재직렬화가 원본과 바이트 동일하다")


def korean_enum_census():
    """⚠ 「한글 enum 은 예외다」를 «세어서» 말한다 — 기준 없는 수치는 근거가 못 된다."""
    import glob
    import re

    ko = re.compile(r"[가-힣]")
    total = korean = 0
    for f in sorted(glob.glob(os.path.join(HERE, "*.json"))):
        def walk(o):
            nonlocal total, korean
            if isinstance(o, dict):
                if isinstance(o.get("enum"), list):
                    total += 1
                    if any(isinstance(v, str) and ko.search(v) for v in o["enum"]):
                        korean += 1
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        with open(f, encoding="utf-8") as fh:
            walk(json.load(fh))
    print("   enum 총 %d개 · 한글값 포함 %d개 — 한글은 관례가 아니라 예외다" % (total, korean))


def main():
    log = []
    spec = load(QUALITY)

    print("== 검사 의뢰 상태 5값을 싣는다 (enum 은 못박지 않는다) ==")
    patch_schema(spec, log)
    patch_query(spec, log)

    save(QUALITY, spec)
    roundtrip()

    print()
    for line in log:
        print(line)

    print("\n== 표기 근거 — 실측 ==")
    korean_enum_census()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
