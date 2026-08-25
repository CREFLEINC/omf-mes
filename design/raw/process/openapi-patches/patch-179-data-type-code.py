#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""측정치 데이터 유형을 확정하고 «어느 칸에 담기는지»를 못박는다. 멱등. — 이슈 #179 (후속)

무엇이 막혔나
-------------
구현팀이 측정치 그리드(`P-02-13` §4-C)를 세우다 **같은 형태를 또 만났다**고
`#179` 에 덧붙였다. `InspectionItemSpec.dataTypeCode` 가 그리드의 **입력 종류**를
정하는데, 계약이 이렇게만 적고 있었다.

    "공통코드 — 수치/텍스트/불리언 [추정]"          ← 계약이 «스스로» [추정] 이라 적었다
    example: "STANDARD"                            ← ⛔ 데이터 유형이 아니다

측정치는 `numeric_value`·`text_value`·`boolean_value` 세 칸 중 **하나만** 채울 수
있으므로(`num_nonnulls ≤ 1`), 항목마다 **어느 칸을 쓰는지** 알아야 입력을 그린다.

⭐ 구현팀이 값의 «모양»으로 추론하지 않았다
--------------------------------------------
「상하한·단위가 있으면 수치, 없으면 텍스트」로 가르면 **불리언 항목이 텍스트로
떨어져** 사용자가 `OK`/`NG` 를 `text_value` 에 적게 된다. **자료의 모양이 틀어진다.**

⛔ 뿌리 — 분류가 틀렸다
------------------------
`dataTypeCode` 는 **「고객사가 자기 분류 체계를 정해야 하는 값」 46종**에 들어
있었다(`deliverables/99-인계대장.md` §2). 그런데 **바로 그 자리의 가르는 기준**과
어긋난다.

    「화면·계약의 «동작»이 그 값에 걸리는가.
     걸리면(상태 전이·분기·검증) 설계가 정하고, 안 걸리면(사유·분류) 마스터다.」
                                              — 공유계약 G-31

⇒ 이 값은 **입력 위젯의 종류**와 **저장할 칸**을 정한다. **동작이 정면으로 걸린다.**
따라서 고객이 정할 마스터가 아니라 **설계가 정할 값**이다.

⭐ 값을 지어내지 않았다 — 물리 모델이 세 칸을 이미 이름 짓고 있다
-------------------------------------------------------------------
    inspection_measurement.numeric_value   →  NUMERIC
    inspection_measurement.text_value      →  TEXT
    inspection_measurement.boolean_value   →  BOOLEAN

⭐ **값 이름이 곧 칸 이름이라 대응표가 따로 필요 없다.** 구현팀의 물음 ②(어느 칸에
대응하나)가 이 이름 짓기로 **구조적으로** 풀린다. 판정 셋을 수량 세 칸에서 딴 것
(`ACCEPTED`·`REJECTED`·`HELD`)과 **같은 원리**다.

⚠ **세 값뿐인 것도 구조가 정한다** — 담을 칸이 셋이라 넷째 값을 만들면 담을 곳이
없다. `ck_inspection_measurement` 의 `num_nonnulls ≤ 1` 이 그 울타리다.

그룹 이름 — 공유계약 `G-32` 규칙을 그대로 적용했다
---------------------------------------------------
    data_type_code  →  DATA_TYPE          ← ⛔ 「무엇의」 데이터 유형인지 모른다
                    →  INSPECTION_ITEM_SPEC_DATA_TYPE   (테이블 이름을 앞에)

⛔ 하지 «않은» 것
------------------
- **`enum` 을 넣지 않았다** — 판정과 같은 방식이다(G-2·G-6). 넣으면 자유 문자열이
  값 목록으로 좁아져 **⛔ 등급 통지**가 되고, 이미 만든 코드가 틀린다.
  ⚠ 대신 **모르는 값이 왔을 때 화면이 무엇을 하는지**를 설명에 적었다.
- **값을 «반드시» 채우게 만들지 않았다** — 세 칸 다 선택이고 DB 도 강제하지 않는다
  (`num_nonnulls ≤ 1` 은 「많아야 하나」이지 「적어도 하나」가 아니다).
  ⭐ **육안 항목은 판정만으로 성립한다**(`P-02-13` §5-9 「항목 판정(합격/불합격) |
  육안 항목」). 판정(`judgmentCode`)은 이미 필수다.
- **나머지 45종을 다시 가르지 않았다** — 이 건의 범위 밖이다. ⚠ 다만 **같은 기준으로
  한 번 훑을 값어치가 있다**(아래).

⚠ 이것이 마지막이 아닐 수 있다
-------------------------------
46종은 **「enum 이 없다」는 기계적 기준**으로 뽑은 목록이고, 「고객이 정할 값인가」로
가른 것이 아니다. `dataTypeCode` 가 그래서 섞여 들어갔다. 목록에는 `fifoPolicyCode`·
`lotControlTypeCode`·`serialControlTypeCode`·`samplingMethodCode` 처럼 **동작이 걸릴
법한 이름**이 더 있다. **G-31 기준으로 한 번 훑는 것을 후속으로 남긴다.**

쓰기
----
    python3 deliverables/openapi/patch-179-data-type-code.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

MDM = "mdm-기준정보.json"
QUALITY = "quality-03품질.json"

GROUP = "INSPECTION_ITEM_SPEC_DATA_TYPE"

DATA_TYPE_DESC = (
    "측정치를 «어느 칸에» 담는지 정한다. ⭐ 값 목록은 "
    "GET /mdm/code-values?codeGroupCode=%s 로 받는다. "
    "값은 NUMERIC(수치)·TEXT(텍스트)·BOOLEAN(불리언) 셋이고 "
    "각각 InspectionMeasurement 의 numericValue·textValue·booleanValue 에 "
    "대응한다 — 값 이름이 곧 칸 이름이다. ⛔ 셋 중 «하나만» 채운다"
    "(ck_inspection_measurement num_nonnulls ≤ 1). "
    "⚠ 모르는 값이 오면 화면은 그 항목의 입력을 «비활성 + 사유»로 둔다"
    "(공유계약 G-2) — 담을 칸을 고를 수 없으므로 추측해서 그리지 않는다. "
    "근거: 공유계약 G-31·G-32 · omf-mes#179"
    % GROUP
)

DATA_TYPE_NOTE = (
    "⛔ 값의 «모양»으로 유형을 추론하지 않는다 — 「상하한·단위가 있으면 수치, "
    "없으면 텍스트」로 가르면 불리언 항목이 텍스트로 떨어져 사용자가 OK/NG 를 "
    "text_value 에 적게 되고 자료의 모양이 틀어진다(구현팀 실측 · #179). "
    "⭐ 이 값은 «설계»가 정한다 — 화면의 입력 위젯과 저장 칸이 걸리므로 "
    "G-31 의 가르는 기준상 고객이 정할 마스터가 아니다. 99-인계대장 §2 의 "
    "46종에 섞여 있던 것을 이번에 걷어냈다. "
    "⚠ enum 을 두지 않는다 — 좁히면 ⛔ 등급 통지가 되고 이미 만든 코드가 틀린다."
)

VALUE_DESCS = {
    "numericValue": (
        "dataTypeCode=NUMERIC 인 항목만 채운다. 상하한(lowerLimit·upperLimit)과 "
        "단위(uomId)가 의미를 갖는 유일한 유형이다. 근거: omf-mes#179"
    ),
    "textValue": (
        "dataTypeCode=TEXT 인 항목만 채운다. 근거: omf-mes#179"
    ),
    "booleanValue": (
        "dataTypeCode=BOOLEAN 인 항목만 채운다. ⚠ 판정(judgmentCode)과 다른 "
        "축이다 — 이 칸은 «측정 결과»이고 판정은 그것을 보고 사람이 정한다"
        "(규격 밖이어도 자동 불합격이 아니다 · P-02-13 §6). 근거: omf-mes#179"
    ),
}

SHARED_NOTE = (
    "⛔ 세 칸 중 «하나만» 채운다(ck_inspection_measurement num_nonnulls ≤ 1). "
    "어느 칸인지는 그 항목의 InspectionItemSpec.dataTypeCode 가 정한다. "
    "⚠ 셋 다 비어도 된다 — 육안 항목은 판정만으로 성립한다"
    "(P-02-13 §5-9). 판정(judgmentCode)은 언제나 필수다."
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


def main() -> int:
    log: list = []
    for name in (MDM, QUALITY):
        roundtrip(name)

    spec = load(MDM)
    schemas = spec["components"]["schemas"]
    for name in ("InspectionItemSpec", "InspectionItemSpecUpsert"):
        prop = schemas[name]["properties"]["dataTypeCode"]
        want = (DATA_TYPE_DESC, DATA_TYPE_NOTE, "NUMERIC")
        got = (prop.get("description"), prop.get("x-internal-note"),
               prop.get("example"))
        if got == want:
            log.append("  · %-26s dataTypeCode 이미 되어 있다" % name)
        else:
            note = "  ⛔ 예시값 STANDARD 는 데이터 유형이 아니었다" \
                if got[2] == "STANDARD" else ""
            prop["description"], prop["x-internal-note"], prop["example"] = want
            log.append("  ✅ %-26s dataTypeCode → %s · 칸 대응 명시%s"
                       % (name, GROUP, note))
    save(MDM, spec)

    spec = load(QUALITY)
    schemas = spec["components"]["schemas"]
    for name in ("InspectionMeasurement", "InspectionMeasurementInput"):
        props = schemas[name]["properties"]
        for key, desc in VALUE_DESCS.items():
            if props[key].get("description") == desc:
                log.append("  · %-26s %-13s 이미 되어 있다" % (name, key))
            else:
                props[key]["description"] = desc
                log.append("  ✅ %-26s %-13s → 대응 유형 명시" % (name, key))
        if schemas[name].get("x-internal-note") == SHARED_NOTE:
            log.append("  · %-26s 셋 중 하나 규칙 이미 있다" % name)
        else:
            schemas[name]["x-internal-note"] = SHARED_NOTE
            log.append("  ⭐ %-26s 셋 중 하나 규칙 신설" % name)
    save(QUALITY, spec)

    print("== 측정치 데이터 유형을 확정한다 — 이슈 #179 후속 ==\n")
    print("\n".join(log))

    print("\n== 최종 ==")
    print("   그룹  %s" % GROUP)
    print("   값    NUMERIC → numericValue")
    print("         TEXT    → textValue")
    print("         BOOLEAN → booleanValue")
    print("\n⭐ 값 이름이 곧 칸 이름이라 대응표가 따로 없다.")
    print("⚠ 셋 다 비어도 된다 — 육안 항목은 판정만으로 성립한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
