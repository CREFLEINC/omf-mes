#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""공통코드 그룹을 «이름»으로 가리킬 수 있게 한다. 멱등. — 이슈 #179

무엇이 막혔나
-------------
계약이 종합 판정 값을 공통코드로 넘겨 두었는데(값 목록을 못박지 않는다 —
공유계약 G-2·G-6), **화면이 그 그룹을 가리킬 방법이 없었다.**

    GET /mdm/code-values?codeGroupId={정수}   ← codeGroupId 가 «정수»이고 «필수»
    GET /mdm/code-groups?q=...                ← 검색뿐. 정확히 집을 수 없다

정수 식별자는 **채번된 값**이라 화면이 알 수 없고, 하드코딩하면 환경마다 달라진다.
구현팀이 수입검사 판정(`W-01-01`)의 **확정 회차를 만들지 못한 채 멈췄다**(#179).

⭐ 이것은 «새 문제»가 아니라 이미 적어 둔 미착지다
--------------------------------------------------
`deliverables/06-API-요구서.md` §5 **미착지 14**(공통코드 그룹·값 목록 미정)가
같은 것을 적어 두었다 — 「화면이 그룹 키를 하드코딩할 수 없다」. 창고유형·
관리수준·Location유형·품질구역·보관조건·판정유형·상태코드가 전부 걸려 있다.

**미착지 14 는 두 겹이다.**

    ① «어떻게» 가리키나 — 정수를 화면이 모른다        ← 이 패치가 푼다(전부)
    ② «어느» 그룹인가   — 그룹 이름이 정해지지 않았다  ← 그룹마다 정한다(이번엔 하나)

무엇을 하나
-----------
① `GET /mdm/code-values` 가 **`codeGroupCode`(문자열)** 도 받는다.
   `codeGroupId` 는 **필수에서 선택으로** 내린다 — 둘 중 «정확히 하나»를 준다.
② 종합 판정 필드 넷에 **그룹 코드를 적고**, 잘못된 예시값을 고친다.
③ 측정치 판정 필드 둘에 **「그룹 미정」을 밝힌다** — 지어내지 않는다.

⭐ 왜 A안(값 조회가 이름을 받는다)인가 — 택하지 않은 안
--------------------------------------------------------
| 안 | 왜 |
| B  | `code-groups` 에 정확 일치 질의를 더한다 → **두 걸음**이 된다. 코드값을
|    | 쓰는 화면이 계속 느는데, 그때마다 **그 조회의 실패가 각 화면의 주 기능**을
|    | 막는다. 걸음이 하나 늘면 실패 지점도 하나 는다 |
| C  | 화면이 `q=` 로 검색해 고른다 → ⛔ 검색은 여러 건을 주고 **어느 것이 그
|    | 그룹인지 화면이 판정하게 된다.** 부분 일치로 엉뚱한 그룹을 집을 수 있다 |

⚠ **OpenAPI 로는 「둘 중 정확히 하나」를 표현할 수 없다.** 설명문에 규칙을 적고
**400 을 선언**한다 — 규칙이 계약에 «보이게» 한다.

⭐ 판정 그룹의 이름과 값 — 지어내지 않았다
------------------------------------------
**값 셋은 이미 확정돼 있었다**(합격·불합격·보류 · 2026-08-07 회신 E-3 종결 ·
공유계약 G-2 가 해소로 기록). 빠진 것은 **식별자**뿐이다.

**코드 이름은 물리 모델이 이미 짓고 있다** — 같은 셋을 수량 컬럼이 부른다.

    ck_inspection_result_qty:  accepted_qty + rejected_qty + held_qty = inspected_qty
                               ↓            ↓              ↓
                               ACCEPTED     REJECTED       HELD

⭐ 이 제약이 **「왜 정확히 셋인가」의 구조적 근거**이기도 하다. 값 이름을 따로
지으면 같은 개념에 어휘가 두 벌 생긴다.

**그룹 이름 규칙** — 기존 선례(`INSPECTION_REQUEST_STATUS` ← `inspection_request.
status_code` · #170)에서 뽑았다.

    컬럼 이름에서 `_code` 를 뺀 것을 대문자로 쓴다.
    그것만으로 «무엇의 값인지» 알 수 없으면 테이블 이름을 앞에 붙인다.

        warehouse_type_code          → WAREHOUSE_TYPE          (자기 완결)
        quality_zone_code            → QUALITY_ZONE            (자기 완결)
        inspection_request.status_code → INSPECTION_REQUEST_STATUS
                                        (`STATUS` 만으로는 모호 · 기존 선례와 일치)
        inspection_result.overall_judgment_code
                                     → INSPECTION_RESULT_OVERALL_JUDGMENT

⚠ **판정 컬럼이 둘이라 이름을 줄이지 않았다** — `inspection_result.
overall_judgment_code`(종합)와 `inspection_measurement.judgment_code`(측정치별).
`INSPECTION_JUDGMENT` 로 줄이면 **어느 쪽인지 모른다.** 식별자는 길어도 값이
안 든다. 화면이 엉뚱한 그룹을 부르면 **틀린 선택지를 보인다.**

⭐ 측정치 판정은 «두 값»이다 — 종합 판정과 그룹이 갈린다
--------------------------------------------------------
처음에는 「화면 스펙에 값이 없다」고 보고 미정으로 두려 했다. **틀렸다** —
`P-02-13` 이 §5·§6 에 적어 두었고, 검사 결과 §4-C 에 표가 없었을 뿐이다.

    「항목 판정(합격/불합격)」                        P-02-13 §5
    「정상/불량 단순 선택 + 자유 입력」                P-02-13 §5(검사기준 없을 때)
    「측정값이 규격 밖 → ⚠ 자동 불합격 «아님»」        P-02-13 §6
    「검사 확정 = 합계 일치 AND «전 항목 판정» AND 종합 판정 선택」  P-02-13 §5

⇒ 항목 판정에는 **「보류」가 없다.** 보류는 **검사 «결과» 수준의 개념**이고
(`held_qty`), 항목은 규격에 드는지 아닌지 둘뿐이다.

⛔ **그래서 그룹을 하나로 합치지 않는다.** 합치면 항목 선택칸에 「보류」가
떠서 **화면이 스펙과 어긋난 값을 받게 된다.**

    INSPECTION_RESULT_OVERALL_JUDGMENT       ACCEPTED · REJECTED · HELD
    INSPECTION_MEASUREMENT_JUDGMENT          ACCEPTED · REJECTED

⛔ 하지 «않은» 것
------------------
- **시드를 넣지 않았다** — `mdm.code_group`·`code_value` 는 데이터 모델 소관이다.
  **작업 통지**이고 우리를 막지 않는다(#170 이 같은 방식으로 갔다).
- **나머지 그룹 이름을 정하지 않았다** — 미착지 14 의 ②는 그룹마다 판단이고,
  이번 건의 범위 밖이다. **규칙만 세워 두었다.**

쓰기
----
    python3 deliverables/openapi/patch-179-code-group-by-name.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

MDM = "mdm-기준정보.json"
QUALITY = "quality-03품질.json"

JUDGMENT_GROUP = "INSPECTION_RESULT_OVERALL_JUDGMENT"
MEASUREMENT_GROUP = "INSPECTION_MEASUREMENT_JUDGMENT"

GROUP_ID_DESC = (
    "코드값 그룹의 채번 식별자. ⚠ codeGroupCode 와 «둘 중 정확히 하나»를 준다 — "
    "둘 다 없거나 둘 다 있으면 400 이다. 화면은 대개 codeGroupCode 를 쓴다"
    "(정수는 환경마다 달라 하드코딩할 수 없다). 근거: omf-mes#179"
)

GROUP_CODE_PARAM = {
    "name": "codeGroupCode",
    "in": "query",
    "required": False,
    "schema": {"type": "string", "maxLength": 50},
    "description": (
        "코드값 그룹을 «이름»으로 가리킨다(mdm.code_group.group_code 와 정확히 일치). "
        "⚠ codeGroupId 와 둘 중 정확히 하나를 준다. 화면이 그룹을 안정적으로 "
        "가리킬 수 있는 유일한 수단이다 — 채번 식별자는 환경마다 다르다. "
        "근거: omf-mes#179"
    ),
    "x-internal-note": (
        "그룹 이름 규칙 — 컬럼 이름에서 _code 를 뺀 것을 대문자로 쓰고, 그것만으로 "
        "무엇의 값인지 알 수 없으면 테이블 이름을 앞에 붙인다"
        "(warehouse_type_code → WAREHOUSE_TYPE · inspection_request.status_code "
        "→ INSPECTION_REQUEST_STATUS). 미착지 14 의 ①을 이 파라미터가 푼다. "
        "②(어느 그룹인가)는 그룹마다 따로 정한다."
    ),
}

BAD_REQUEST = {
    "description": "codeGroupId·codeGroupCode 를 둘 다 주었거나 둘 다 주지 않았다",
    "content": {
        "application/json": {
            "schema": {"$ref": "#/components/schemas/ErrorResponse"}
        }
    },
}

# 종합 판정 — 스키마별로 원래 있던 단서를 살린 채 그룹만 못박는다
JUDGMENT_BASE = (
    "합격·불합격·보류 3값. ⛔ enum 으로 못박지 않는다 — 값 목록은 공통코드가 갖고 "
    "늘 수 있다(공유계약 G-2·G-6). ⭐ 값 목록은 "
    "GET /mdm/code-values?codeGroupCode=%s 로 받는다. 값은 "
    "ACCEPTED(합격)·REJECTED(불합격)·HELD(보류) — 검사 결과 수량 세 칸"
    "(accepted/rejected/held)과 같은 이름이다. 근거: 회신 E-3 종결 2026-08-07 · "
    "omf-mes#179" % JUDGMENT_GROUP
)

OVERALL = {
    "InspectionResult": JUDGMENT_BASE,
    "InspectionResultCreate": "statusCode=확정 이면 필수다. " + JUDGMENT_BASE,
    "InspectionResultUpdate": JUDGMENT_BASE,
    "InspectionResultConfirm": "비우면 저장된 값을 쓴다. " + JUDGMENT_BASE,
}

MEASUREMENT_DESC = (
    "항목별 측정치의 판정. ⛔ enum 으로 못박지 않는다(공유계약 G-2·G-6). "
    "⭐ 값 목록은 GET /mdm/code-values?codeGroupCode=%s 로 받는다. 값은 "
    "ACCEPTED(합격)·REJECTED(불합격) «두 개»다. ⚠ 종합 판정과 그룹이 «다르다» — "
    "항목 판정에는 「보류」가 없다. 보류는 검사 결과 수준의 개념이고"
    "(held_qty) 항목은 규격에 드는지 아닌지 둘뿐이다(P-02-13 §5 「항목 "
    "판정(합격/불합격)」). ⛔ 측정값이 규격 밖이어도 «자동 불합격이 아니다» — "
    "표시하고 사람이 판정한다(P-02-13 §6). 근거: omf-mes#179"
    % MEASUREMENT_GROUP
)

FORMAT: dict[str, dict] = {}


def measure(raw: str) -> dict:
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


def patch_mdm(log: list) -> None:
    spec = load(MDM)
    op = spec["paths"]["/mdm/code-values"]["get"]
    params = op.setdefault("parameters", [])

    by_name = {p.get("name"): i for i, p in enumerate(params) if isinstance(p, dict)}

    gid = params[by_name["codeGroupId"]]
    if gid.get("required") is False and gid.get("description") == GROUP_ID_DESC:
        log.append("  · codeGroupId 이미 선택이다")
    else:
        gid["required"] = False
        gid["description"] = GROUP_ID_DESC
        log.append("  ⛔ codeGroupId 필수 → 선택 · 설명 갱신")

    if "codeGroupCode" in by_name:
        if params[by_name["codeGroupCode"]] == GROUP_CODE_PARAM:
            log.append("  · codeGroupCode 이미 있다")
        else:
            params[by_name["codeGroupCode"]] = json.loads(json.dumps(GROUP_CODE_PARAM))
            log.append("  ⭐ codeGroupCode 갱신")
    else:
        params.insert(by_name["codeGroupId"] + 1,
                      json.loads(json.dumps(GROUP_CODE_PARAM)))
        log.append("  ⭐ codeGroupCode 질의 신설 — codeGroupId 바로 뒤")

    resp = op.setdefault("responses", {})
    if resp.get("400") == BAD_REQUEST:
        log.append("  · 400 이미 있다")
    else:
        resp["400"] = json.loads(json.dumps(BAD_REQUEST))
        # 200 뒤에 오도록 키 순서를 정리한다
        op["responses"] = {k: resp[k] for k in sorted(resp)}
        log.append("  ⭐ 400 선언 — 「둘 중 정확히 하나」를 계약이 보이게 한다")

    save(MDM, spec)


def patch_quality(log: list) -> None:
    spec = load(QUALITY)
    schemas = spec["components"]["schemas"]

    for name, desc in OVERALL.items():
        prop = schemas[name]["properties"]["overallJudgmentCode"]
        before = (prop.get("description"), prop.get("example"))
        prop["description"] = desc
        prop["example"] = "ACCEPTED"
        if before == (desc, "ACCEPTED"):
            log.append("  · %-24s overallJudgmentCode 이미 되어 있다" % name)
        else:
            note = ""
            if before[1] == "IQC":
                note = "  ⛔ 예시값 IQC 는 «검사 유형»이지 판정이 아니었다"
            log.append("  ✅ %-24s overallJudgmentCode → 그룹 명시 · 예시 ACCEPTED%s"
                       % (name, note))

    for name in ("InspectionMeasurement", "InspectionMeasurementInput"):
        prop = schemas[name]["properties"]["judgmentCode"]
        if prop.get("description") == MEASUREMENT_DESC:
            log.append("  · %-24s judgmentCode 이미 되어 있다" % name)
        else:
            prop["description"] = MEASUREMENT_DESC
            prop["example"] = "ACCEPTED"
            log.append("  ✅ %-24s judgmentCode → %s (2값 · 보류 없음)"
                       % (name, MEASUREMENT_GROUP))

    save(QUALITY, spec)


def main() -> int:
    log: list = []
    for name in (MDM, QUALITY):
        roundtrip(name)

    print("== 공통코드 그룹을 이름으로 가리킨다 — 이슈 #179 ==\n")
    print("-- 1. 조회 수단 (미착지 14 의 ①) --")
    patch_mdm(log)
    print("\n".join(log))

    log.clear()
    print("\n-- 2. 판정 그룹 (미착지 14 의 ② 중 하나) --")
    patch_quality(log)
    print("\n".join(log))

    print("\n== 최종 ==")
    after = load(MDM)["paths"]["/mdm/code-values"]["get"]
    names = [p["name"] for p in after["parameters"] if "name" in p]
    req = [p["name"] for p in after["parameters"] if p.get("required")]
    print("   GET /mdm/code-values 질의: %s" % names)
    print("   그중 required: %s  ← 「둘 중 하나」라 계약상 필수는 없다" % (req or "없다"))
    print("   응답: %s" % list(after["responses"]))
    print("   종합 판정 : %-36s ACCEPTED·REJECTED·HELD" % JUDGMENT_GROUP)
    print("   항목 판정 : %-36s ACCEPTED·REJECTED" % MEASUREMENT_GROUP)
    print("\n⚠ 그룹을 «둘로» 갈랐다 — 항목 판정에는 「보류」가 없다(P-02-13 §5).")
    print("   합치면 항목 선택칸에 보류가 떠서 화면이 스펙과 어긋난 값을 받는다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
