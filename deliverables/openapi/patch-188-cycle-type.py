#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""주기 단위 코드 그룹을 확정하고, 정밀도 두 칸의 소관을 계약에 적는다. 멱등. — 이슈 #188

무엇이 막혔나
-------------
`#185` 회신에서 **추기로 온 두 물음을 빠뜨렸다.** 구현팀이 08:37 에 코멘트로 올렸는데
11:49 회신이 「세 물음에 다 답합니다」로 나갔고, 병합의 `Closes` 가 이슈를 닫아 묻혔다.

⛔ **원인은 읽는 방식이었다** — 이슈를 `gh issue view --json body` 로 «본문만» 읽고
**코멘트를 안 봤다.** `#179` 에서도 같은 일이 있었다(4번 물음이 답 없이 닫혔다).

무엇을 하나
-----------
① 주기 단위의 코드 그룹을 확정한다 — 두 자리가 «같은 그룹»이다
② 정밀도 두 칸의 «소관»을 계약에 적는다 — 이 화면이 안 건드리되 지우지도 않는다

⭐ 왜 «한» 그룹인가 — 값이 같은 «종류»다
-----------------------------------------
    Equipment.calibrationCycleTypeCode          검교정 주기 단위   example MONTH
    InspectionItemAssignment.cycleTypeCode      점검 부여 주기     example DAY

⚠ **스펙 두 곳의 목록이 미세하게 달랐다** — `W-05-11` §4-A 는 「일/월/년」, `W-05-12`
§4-C-2 는 「일/주/월」. **둘 다 확정이 아니다** — 라벨이 `*(미정)*` 이고 타입 칸에 적힌
예시다. 개념모델도 「검교정 주기」라고만 적고 값을 열거하지 않았다.

⇒ **넷의 합집합으로 한 그룹**을 둔다. 같은 개념에 **어휘를 두 벌 만들지 않는다.**

⛔ `inspectionTypeCode` 와 무엇이 다른가 — **가르는 기준을 세운다.**

    값이 같은 «종류»인가.
      같은 종류(주기 단위: 일·주·월·년)         → 한 그룹.  ⭐ 이번 건
      다른 종류(수입·공정·출하 ↔ 일상·정기·보전) → 가른다.  #186

⚠ 「비슷해 보인다」로 합치지 않는다 — 구현팀이 **확인 없이 합치지 않겠다**고 물어온 것이
옳았다. 실제로 확인해 보니 이번은 합쳐도 되는 자리였다.

⭐ 값 이름을 지어내지 않았다 — 계약 예시가 이미 부르고 있었다
--------------------------------------------------------------
    일  DAY     ← InspectionItemAssignment.cycleTypeCode 의 example
    월  MONTH   ← Equipment.calibrationCycleTypeCode 의 example
    주  WEEK    ← 위 둘과 같은 어휘(단수형)로 맞췄다
    년  YEAR    ← 같음

② 정밀도 두 칸 — 소관을 계약이 말하게 한다
-------------------------------------------
`Equipment.precisionValue`·`precisionUomId` 는 **계측기 마스터(`W-05-11`) 소관**이다.
`W-05-12` §4-B 필드 목록에 **없고**(전수 확인) `W-05-11` §4-A 가 「정밀도 — 수치 +
단위」로 갖는다.

⭐ 구현팀 처리가 맞다 — **보이지도 고치지도 않되 상세에서 받은 값을 그대로 되돌려
보낸다.** 전체 교체 PUT 이라 빼면 지워진다. ⚠ 이 화면에는 **이미 같은 규칙의 자리가
있다** — `lastCalibrationDate`·`calibrationDueDate` 가 「다른 화면이 정한다」로 읽기
전용이다(`W-05-12` §4-B · 공유계약 `B-13`).

⇒ **계약이 그 사실을 말하게 한다.** 설명에 없으면 다음 사람이 또 묻는다.

⛔ 하지 «않은» 것
------------------
- **`enum` 을 넣지 않았다** — 다른 코드와 같다(G-2·G-6).
- **정밀도를 읽기 전용으로 «바꾸지» 않았다** — 계측기 마스터에서는 편집한다.
  「어느 화면이 편집하나」는 화면 스펙이 정하지 계약이 정하지 않는다.

쓰기
----
    python3 deliverables/openapi/patch-188-cycle-type.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MDM = "mdm-기준정보.json"
G_CYCLE = "CYCLE_TYPE"

CYCLE_BASE = (
    "주기 단위 — 일(DAY)·주(WEEK)·월(MONTH)·년(YEAR). ⭐ 값 목록은 "
    "GET /mdm/code-values?codeGroupCode=%s 로 받는다. ⚠ 검교정 주기와 점검 부여 "
    "주기가 «같은 그룹»이다 — 같은 종류의 값(기간 단위)이라 어휘를 두 벌 만들지 "
    "않는다. ⛔ 검사 «유형»(품질 IQC·PQC·OQC ↔ 설비 DAILY·MONTHLY·MAINTENANCE)은 "
    "종류가 달라 그룹을 가른다 — 공유계약 G-32. 근거: omf-mes#188" % G_CYCLE
)
CALIB_DESC = (
    "검교정 주기 단위. calibrationRequired 가 참이면 주기 두 칸이 함께 필요하다 — "
    "주기 없이는 차기 예정일을 산출할 수 없다. " + CYCLE_BASE
)
ASSIGN_DESC = CYCLE_BASE

PRECISION_NOTE = (
    "⚠ 이 칸은 계측기 마스터(W-05-11)가 소유한다 — 설비·설비그룹 마스터"
    "(W-05-12)는 «보이지도 고치지도 않는다»(그 화면 §4-B 필드 목록에 없다). "
    "⛔ 다만 전체 교체 PUT 이라 «빼면 지워진다» — 상세에서 받은 값을 그대로 "
    "되돌려 보낸다. lastCalibrationDate·calibrationDueDate 가 이미 같은 규칙이다"
    "(공유계약 B-13). 근거: omf-mes#188"
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


def set_desc(props: dict, key: str, desc: str, log: list, where: str,
             note: str | None = None) -> None:
    p = props.get(key)
    if p is None:
        return
    want_note = note if note is not None else p.get("x-internal-note")
    if p.get("description") == desc and p.get("x-internal-note") == want_note:
        log.append("  · %-34s %s 이미 되어 있다" % (where, key))
        return
    p["description"] = desc
    if note is not None:
        p["x-internal-note"] = note
    log.append("  ✅ %-34s %s" % (where, key))


def main() -> int:
    roundtrip(MDM)
    spec = load(MDM)
    s = spec["components"]["schemas"]
    log: list = []

    print("== 주기 단위 그룹 확정 · 정밀도 소관 명시 — 이슈 #188 ==\n")

    print("-- ① 주기 단위는 «한» 그룹이다 (물음 4) --")
    for n in ("Equipment", "EquipmentCreate", "EquipmentUpdate"):
        if n in s:
            set_desc(s[n]["properties"], "calibrationCycleTypeCode",
                     CALIB_DESC, log, n)
    for n in ("InspectionItemAssignment", "InspectionItemAssignmentInput"):
        if n in s:
            set_desc(s[n]["properties"], "cycleTypeCode", ASSIGN_DESC, log, n)
    print("\n".join(log)); log.clear()

    print("\n-- ② 정밀도 두 칸의 소관 (물음 5) --")
    for n in ("Equipment", "EquipmentCreate", "EquipmentUpdate"):
        if n not in s:
            continue
        for key, base in (("precisionValue", "정밀도 수치"),
                          ("precisionUomId", "정밀도 단위")):
            p = s[n]["properties"].get(key)
            if p is None:
                continue
            set_desc(s[n]["properties"], key, base, log, n, note=PRECISION_NOTE)
    print("\n".join(log))

    save(MDM, spec)

    after = load(MDM)["components"]["schemas"]
    print("\n== 최종 ==")
    print("   %-28s DAY · WEEK · MONTH · YEAR" % G_CYCLE)
    print("   쓰는 자리 — 검교정 주기 단위 3 · 점검 부여 주기 2")
    print("   정밀도 소관 주석 — %d자리"
          % sum(1 for n in ("Equipment", "EquipmentCreate", "EquipmentUpdate")
                for k in ("precisionValue", "precisionUomId")
                if after.get(n, {}).get("properties", {}).get(k, {})
                .get("x-internal-note") == PRECISION_NOTE))
    print("\n⭐ 가르는 기준 — 「값이 같은 «종류»인가」. 같으면 한 그룹, 다르면 가른다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
