#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""설비 자산 상태·점검 유형·판정 방식의 코드 그룹을 확정한다. 멱등. — 이슈 #185 · #186

무엇이 막혔나
-------------
`W-05-12`(설비·설비그룹 마스터)를 만들던 구현팀이 **세 자리에서 같은 벽**을 만났다.

    Equipment.statusCode                「운용 또는 폐기 두 값」 — 그룹 이름 없음
    EquipmentInspectionItem.inspectionTypeCode   「일상·정기·보전」 — 그룹 이름 없음
    EquipmentInspectionItem.judgmentMethodCode   「육안·측정값」   — 그룹 이름 없음

⛔ **우리가 「등록 요청하겠다」고 적어 놓고 안 했다** — 화면 스펙 `W-05-12` §8 미결 3:

    「status_code 는 §5-2 에서 «우리가 2값을 정했으므로» 그 2값을 등록 요청한다」

**뜻은 정했고 식별자를 안 만들었다.** `#176`·`#179` 와 **같은 형태**다.

⚠ 판정 방식은 «짝 제약»을 몰고 있다
------------------------------------
계약이 「측정값이면 단위·상하한이 함께 필요하다」고 정했는데 **「측정값」의 코드값을
모르면 화면이 그 제약을 걸 수 없다.** 자리표시로 두면 등록·수정이 **반드시 실패하는
경로**가 된다 — 구현팀이 그대로 짚었다.

⭐ 값 이름을 지어내지 않았다 — 계약과 확정이 이미 부르고 있었다
----------------------------------------------------------------
    일상  DAILY        ← equipment-05 Inspection 설명 「일상(DAILY) 또는 정기(MONTHLY)」
    정기  MONTHLY      ←  같은 자리 · WF05 S2 「점검유형 Daily/Monthly」 · ✓확정 QA #10
    육안  VISUAL       ← EquipmentInspectionItem.judgmentMethodCode 의 example
    측정값 MEASUREMENT  ← 짝 이름으로 새로 정했다(위 셋과 달리 선례가 없었다)

⚠ **「정기 = MONTHLY」가 어색해도 바꾸지 않는다** — 확정 문서와 계약이 이미 그렇게
부르고 있고, 여기서 갈면 **어휘가 두 벌** 생긴다.

⭐ 보전이 셋째 값인 근거 — 실제로 쓰인다
-----------------------------------------
`W-05-12` §4-C 는 「점검·**보전** 항목 마스터」 하나로 정의했고, **`W-05-05`(보전지시
발행) §4 가 그 마스터를 FK 로 참조**한다 — 「보전 항목이 부여돼 있지 않다 → ⛔ 발행
불가」. 값을 만들 자리가 실재한다(§2-2 사용처 세기).

⚠ 점검 «입력» 화면(`M-05-01`)은 앞 둘만 보인다 — 보전 항목은 보전 흐름이 쓴다.

⛔ 같은 이름이 «다른 값 집합»을 갖는다 — 그래서 그룹을 가른다
--------------------------------------------------------------
`inspectionTypeCode` 는 두 도메인에 있고 **값이 완전히 다르다.**

    품질 검사   IQC · PQC · OQC          InspectionPlan · InspectionRequest · InspectionResult
    설비 점검   DAILY · MONTHLY · 보전    EquipmentInspectionItem · Inspection

⇒ 그룹 이름을 **도메인으로 가른다**(`B-28` 과 같은 원리). 품질 쪽도 함께 이름을
붙였다 — 안 붙이면 구현팀이 **다음 화면에서 같은 것을 또 묻는다.**

⛔ `ACTIVE` 를 쓰지 않는다 — 「사용 여부」와 축이 다르다
--------------------------------------------------------
계약의 example 이 `ACTIVE` 였는데, **계약 자신이 「사용 여부(`includeInactive`)와
다른 축이다」라고 적어 두었다.** `ACTIVE` 를 자산 상태 코드로 쓰면 두 축이 같은 낱말을
갖게 되어 **정확히 그 혼동을 부른다.** `IN_SERVICE`(운용)·`DISPOSED`(폐기)로 둔다 —
`DISPOSED` 는 이미 있는 액션 이름(`:dispose`)과 짝이 맞는다.

⛔ 하지 «않은» 것
------------------
- **`enum` 을 넣지 않았다** — 좁히면 ⛔ 등급 통지가 된다(G-2·G-6). 다른 코드와 같다.
- **점검 항목 마스터의 «범위»를 계약에서 바꾸지 않았다** — 범위는 원래 맞았고
  (요구서 05 §4 「점검 항목 마스터 CRUD — W-05-12 가 쓴다」) **착수 이슈가 덜 적었다.**
  그건 통지로 바로잡을 일이지 계약을 고칠 일이 아니다.

쓰기
----
    python3 deliverables/openapi/patch-185-186-equipment-codes.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MDM = "mdm-기준정보.json"
EQUIP = "equipment-05설비툴.json"
QUALITY = "quality-03품질.json"

G_STATUS = "EQUIPMENT_STATUS"
G_INSP_TYPE = "EQUIPMENT_INSPECTION_TYPE"
G_JUDGE = "EQUIPMENT_INSPECTION_JUDGMENT_METHOD"
G_QUALITY_TYPE = "QUALITY_INSPECTION_TYPE"

STATUS_DESC = (
    "자산 수명주기 — 운용 또는 폐기 두 값. ⭐ 값 목록은 "
    "GET /mdm/code-values?codeGroupCode=%s 로 받는다"
    "(IN_SERVICE·DISPOSED). ⚠ 사용 여부(is_active·includeInactive)와 «다른 축» "
    "이다 — 그래서 ACTIVE 라는 낱말을 쓰지 않는다. 두 축이 같은 낱말을 가지면 "
    "혼동한다. ⛔ 값을 늘리지 않는다 — 고장·보전중·비가동은 트랜잭션 조건이지 "
    "자산 상태가 아니다(공유계약 A-14 · W-05-12 §5-2). 근거: omf-mes#185"
    % G_STATUS
)
STATUS_QUERY_DESC = (
    "자산 수명주기로 거른다 — 운용(IN_SERVICE) 또는 폐기(DISPOSED). "
    "사용 여부(includeInactive)와 «다른 축» 이다. 현장 화면은 폐기된 설비를 "
    "목록에서 뺀다 — statusCode=IN_SERVICE 로 부른다. ⭐ 값 목록은 "
    "GET /mdm/code-values?codeGroupCode=%s. 근거: omf-mes#185" % G_STATUS
)
INSP_TYPE_DESC = (
    "점검 유형 — 일상(DAILY)·정기(MONTHLY)·보전(MAINTENANCE). ⭐ 값 목록은 "
    "GET /mdm/code-values?codeGroupCode=%s 로 받는다. ⚠ 품질 검사의 "
    "inspectionTypeCode(IQC·PQC·OQC)와 «같은 이름 다른 값» 이다 — 그룹을 "
    "가른다(공유계약 B-28 과 같은 원리). ⭐ 보전 항목은 이 마스터에 함께 있고 "
    "보전 지시(W-05-05)가 FK 로 참조한다 — 점검 입력 화면은 앞 둘만 보인다. "
    "근거: 확정 QA #10 · omf-mes#186" % G_INSP_TYPE
)
JUDGE_DESC = (
    "판정 방식 — 육안(VISUAL) 또는 측정값(MEASUREMENT). ⛔ 측정값이면 "
    "단위(uomId)·상하한(lowerLimit·upperLimit)이 «함께 필요하다». ⭐ 값 목록은 "
    "GET /mdm/code-values?codeGroupCode=%s 로 받는다 — 이 값을 모르면 화면이 "
    "짝 제약을 걸 수 없어 등록·수정이 반드시 실패하는 경로가 된다"
    "(구현팀 실측 · omf-mes#186). 근거: WF05 S2" % G_JUDGE
)
QUALITY_TYPE_ADD = (
    " ⭐ 값 목록은 GET /mdm/code-values?codeGroupCode=%s 로 받는다"
    "(IQC·PQC·OQC). ⚠ 설비 점검의 inspectionTypeCode(DAILY·MONTHLY·MAINTENANCE)와 "
    "«같은 이름 다른 값» 이라 그룹을 가른다. 근거: omf-mes#186" % G_QUALITY_TYPE
)

FORMAT: dict[str, dict] = {}


def measure(raw: str) -> dict:
    second = raw.split("\n")[1] if "\n" in raw else ""
    return {"indent": len(second) - len(second.lstrip(" ")) or 1,
            "newline": raw.endswith("\n")}


def load(name: str) -> dict:
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        raw = fh.read()
    FORMAT[name] = measure(raw)
    return json.loads(raw)


def save(name: str, spec: dict) -> None:
    fmt = FORMAT[name]
    body = json.dumps(spec, ensure_ascii=False, indent=fmt["indent"])
    if fmt["newline"]:
        body += "\n"
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as fh:
        fh.write(body)


def roundtrip(name: str) -> None:
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        before = fh.read()
    fmt = measure(before)
    after = json.dumps(json.loads(before), ensure_ascii=False, indent=fmt["indent"])
    if fmt["newline"]:
        after += "\n"
    if before != after:
        sys.exit("⛔ %s — 직렬화가 원본과 다릅니다." % name)


def touch(props: dict, key: str, desc: str, example: str,
          log: list, where: str) -> None:
    p = props.get(key)
    if p is None:
        return
    if p.get("description") == desc and p.get("example") == example:
        log.append("  · %-38s %s 이미 되어 있다" % (where, key))
        return
    old = p.get("example")
    p["description"] = desc
    p["example"] = example
    note = "  ⛔ 예시 %r → %r" % (old, example) if old != example else ""
    log.append("  ✅ %-38s %s%s" % (where, key, note))


def main() -> int:
    for n in (MDM, EQUIP, QUALITY):
        roundtrip(n)
    log: list = []

    print("== 설비 자산 상태·점검 유형·판정 방식을 확정한다 — #185 · #186 ==\n")

    # --- #185 자산 수명주기 ---
    print("-- ① 자산 수명주기 (#185) --")
    spec = load(MDM)
    s = spec["components"]["schemas"]
    for n in ("Equipment", "EquipmentCreate", "EquipmentUpdate"):
        if n in s:
            touch(s[n]["properties"], "statusCode", STATUS_DESC, "IN_SERVICE",
                  log, n)
    for prm in spec["paths"]["/mdm/equipments"]["get"].get("parameters", []):
        if isinstance(prm, dict) and prm.get("name") == "statusCode":
            if prm.get("description") == STATUS_QUERY_DESC:
                log.append("  · %-38s 질의 statusCode 이미 되어 있다" % "/mdm/equipments")
            else:
                prm["description"] = STATUS_QUERY_DESC
                log.append("  ✅ %-38s 질의 statusCode 설명 갱신" % "/mdm/equipments")
    print("\n".join(log)); log.clear()

    # --- #186 점검 유형·판정 방식 ---
    print("\n-- ② 점검 유형·판정 방식 (#186) --")
    for n in ("EquipmentInspectionItem", "EquipmentInspectionItemCreate",
              "EquipmentInspectionItemUpdate", "InspectionItemAssignment"):
        if n not in s:
            continue
        touch(s[n]["properties"], "inspectionTypeCode", INSP_TYPE_DESC, "DAILY",
              log, n)
        touch(s[n]["properties"], "judgmentMethodCode", JUDGE_DESC, "VISUAL",
              log, n)
    # 품질 쪽 검사 유형 — 같은 이름 다른 값이라 그룹을 가른다
    for n in ("InspectionPlan", "InspectionPlanCreate", "InspectionPlanUpdate"):
        if n not in s:
            continue
        p = s[n]["properties"].get("inspectionTypeCode")
        if p is None:
            continue
        base = "공통코드 — IQC/PQC(공정·초중종·자주)/OQC"
        want = base + QUALITY_TYPE_ADD
        if p.get("description") == want:
            log.append("  · %-38s inspectionTypeCode 이미 되어 있다" % n)
        else:
            p["description"] = want
            log.append("  ✅ %-38s inspectionTypeCode → %s" % (n, G_QUALITY_TYPE))
    save(MDM, spec)

    spec = load(EQUIP)
    s2 = spec["components"]["schemas"]
    for n in ("Inspection", "InspectionCreate"):
        if n in s2:
            touch(s2[n]["properties"], "inspectionTypeCode", INSP_TYPE_DESC,
                  "DAILY", log, n)
    save(EQUIP, spec)

    spec = load(QUALITY)
    s3 = spec["components"]["schemas"]
    for n in ("InspectionRequest", "InspectionResult"):
        p = s3.get(n, {}).get("properties", {}).get("inspectionTypeCode")
        if p is None:
            continue
        want = str(p.get("description", "")).split(" ⭐ 값 목록은")[0] + QUALITY_TYPE_ADD
        if p.get("description") == want:
            log.append("  · %-38s inspectionTypeCode 이미 되어 있다" % n)
        else:
            p["description"] = want
            log.append("  ✅ %-38s inspectionTypeCode → %s" % (n, G_QUALITY_TYPE))
    save(QUALITY, spec)
    print("\n".join(log))

    print("\n== 최종 ==")
    for g, vals in ((G_STATUS, "IN_SERVICE · DISPOSED"),
                    (G_INSP_TYPE, "DAILY · MONTHLY · MAINTENANCE"),
                    (G_JUDGE, "VISUAL · MEASUREMENT"),
                    (G_QUALITY_TYPE, "IQC · PQC · OQC")):
        print("   %-40s %s" % (g, vals))
    print("\n⚠ inspectionTypeCode 는 «같은 이름 다른 값» 이라 그룹을 둘로 갈랐다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
