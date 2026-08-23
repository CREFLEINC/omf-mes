#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""작업 세션의 구간 모델을 계약에 맞춘다. 멱등.

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

무엇을 하나 — 다섯
------------------
① `WorkSession.sessionNo` 설명 정정 — 「세션을 새로 열 때마다 는다」
② `stopReasonCode` 두 자리에 「쓰지 않는다」를 적는다 — 실측으로 이 칸이 있는 스키마는
   **`WorkSession`·`WorkSessionEnd`** 둘이다(루프는 없는 이름도 방어적으로 돈다)
   — 값 목록을 안 정한 게 아니라 **비우기로 정했다**(공유계약 A-21·A-25)
③ ⛔ **그 서술을 x-internal-note 로 옮긴다** — description 은 공개된다
④ `endedAt`·`:end` 에 「이 표는 상태 컬럼을 함께 갖는다」 단서를 단다 — G-16 v2.0 보완
⑤ `statusCode` 에 설명을 넣고, events 오퍼레이션에 사건 유형 다섯과 **적재 주체**를 적는다

⛔ **필드를 지우지 않는다** — 물리 컬럼이 실재하므로 계약에서 빼면 「없는 칸」으로
읽힌다. **있는데 안 쓴다**를 설명으로 적는 것이 A-21 이 말하는 방식이다.

⚠ **③ 은 리뷰(PR #211)에서 잡혔다** — `check-public-safe.py` 가 「공유계약 X-N(요약문)」의
괄호를 막는다. 공개 저장소 omf-mes-client 의 gen:api 가 description 을 JSDoc 으로
옮겨 생성물이 공개되기 때문이다. **정본을 고친 PR 은 openapi 검사기 5종을 다 돌린다.**

근거: 공유계약 v3.9 A-25·G-16 보완 · P-02-01 §5-4(v0.2 정정) · P-02-10 §5-4
"""
import json
import sys

SPEC = "production-02생산실행.json"

SESSION_NO_DESC = (
    "그 작업지시에서 세션을 «새로 열 때마다» 는다(작업 완료·교대 마감으로 :end 한 뒤 다시 시작하는 경우). "
    "⛔ 중단·재개로는 늘지 않는다 — 재개는 같은 세션에 RESUME 사건을 적재하고 status_code 를 되돌린다. "
    "uq(workOrderId, sessionNo). 근거: 공유계약 G-16 의 보완(구간을 닫는 사건과 구간 안의 사건) · P-02-01 §5-4"
)

STOP_REASON_DESC = "⛔ 쓰지 않는다 — 비운다. 값 목록을 못 정한 것이 아니라 «비우기로 정했다». 근거: 공유계약 A-21 · A-25"

STOP_REASON_NOTE = (
    "세션 종료 사유를 요구한 문서가 없다. 요구 원천은 「비가동 및 작업중단 사유 기록」 한 줄인데 "
    "그 뜻은 work_session_event.reason_code 가 받는다(논리 모델 §9.7 만 설명이 붙어 있다). "
    "데이터모델 CHANGELOG 144행도 「작업 세션 기반 중지는 work_session_event 로 커버」라 적었다. "
    "세션 종료 화면도 인벤토리에 없어 채울 사람이 없다. "
    "다시 여는 조건 — 세션 종료 화면이 생기고 「왜 닫는가」를 사람에게 묻기로 하면 그때 연다."
)

# ④ G-16 은 「진행 중을 상태 컬럼으로 두지 않는다」인데 이 표는 둘 다 갖는다.
#    v2.0 보완이 「이미 있는 것은 고치라는 뜻이 아니다」로 길을 내 뒀으므로 그 단서를 단다.
#
# ⛔ 1차 반영에서 이 문자열을 «근거: 뒤에» 덧붙였다가 2차 리뷰에서 잡혔다 — 이 저장소의
#    description 은 「근거: …」로 끝난다. 뒤에 붙이면 앞 조항이 그 내용을 정한 것처럼 읽힌다.
#    ⇒ 이제 insert_before_evidence() 로 «근거: 앞»에 넣는다.
OLD_G16_CAVEAT = " ⚠ 다만 이 표는 status_code 를 함께 갖는다 — 이미 있는 구조라 화면은 둘 다 쓴다(공유계약 G-16 의 보완)."

ENDED_AT_CAVEAT = (
    "⚠ 다만 이 표는 status_code 를 함께 갖는다 — 「진행 중」을 상태 컬럼으로 두지 않는 것이 원칙이나 "
    "이미 있는 구조라 화면은 둘 다 읽는다."
)

# 「두지 않는다」를 단언한 뒤 곧바로 뒤집으면 읽는 쪽이 어느 쪽인지 모른다.
# 원칙은 단서가 함께 말하므로 첫 문장에서는 뺀다.
ENDED_AT_OLD_SENTENCE = "비어 있으면 진행 중이다 — 상태 컬럼을 두지 않는다."
ENDED_AT_NEW_SENTENCE = "비어 있으면 진행 중이다."

# ⛔ 2차 리뷰 — 「상태 컬럼을 바꾸는 것이 아니다」가 statusCode 설명(「END 가 「종료」로 옮긴다」)과
#    정면으로 갈렸다. 세션을 닫는 유일한 오퍼레이션이 여기이고 END 사건도 이 트랜잭션이 만드니,
#    status_code 를 옮기는 것도 여기다. 「화면은 둘 다 쓴다」는 «읽는 쪽» 이야기라 답이 아니었다.
END_OLD_SENTENCE = "상태 컬럼을 바꾸는 것이 아니다."
END_NEW_SENTENCE = (
    "⚠ 이 표는 status_code 를 함께 갖는다 — 끝 시각을 찍으면서 status_code 도 「종료」로 옮긴다"
    "(공유계약 G-16 의 보완)."
)

# ⛔ 2차 리뷰 — 첫 문장이 「통제 우회를 기록한다」인데 덧붙인 설명은 「따로 보내지 않는다」였다.
#    덧붙인 쪽이 맞다 — CONTROL_OVERRIDE 는 WorkSessionCreate.controlOverride 로 들어온다
#    (계약 설계 3단계가 :override 액션을 지우며 세션 생성의 인자로 확정했다).
#    즉 첫 문장이 처음부터 틀려 있었고 이번 추가가 그것을 드러냈다.
EVENTS_OLD_SENTENCE = "중단·재개·통제 우회를 기록한다."
EVENTS_NEW_SENTENCE = "중단·재개를 기록한다."

STATUS_CODE_DESC = (
    "세션이 지금 어떤 상태인가 — 진행·중단·종료. START·RESUME 이 「진행」, STOP 이 「중단」, "
    "END 가 「종료」로 옮긴다. ⚠ 코드 문자열은 아직 확정되지 않았다 — 뜻과 식별자는 다른 산출물이다. "
    "근거: 공유계약 A-25 · G-16"
)

EVENTS_TYPES = (
    "사건 유형은 다섯이다 — START(시작)·STOP(중단)·RESUME(재개)·END(종료)·CONTROL_OVERRIDE(통제 우회). "
    "⭐ 이 오퍼레이션으로 단말이 적재하는 것은 구간 «안의» 사건인 STOP·RESUME 뿐이다. "
    "구간의 «경계»(START·END)와 통제 우회는 세션을 열고 닫는 오퍼레이션이 같은 트랜잭션으로 만든다 — "
    "따로 보내지 않는다. 유형별로 reasonCode 에 어느 코드 그룹을 쓰는지는 공유계약 A-25 가 정한다."
)


def set_desc(node: dict, key: str, value: str, label: str, changed: list) -> None:
    if key in node and node[key].get("description") != value:
        node[key]["description"] = value
        changed.append(label)


def insert_before_evidence(desc: str, fragment: str) -> str:
    """「근거: …」 앞에 끼워 넣는다. 뒤에 붙이면 그 조항이 정한 내용처럼 읽힌다."""
    idx = desc.rfind("근거:")
    if idx == -1:
        return desc.rstrip() + " " + fragment
    return desc[:idx].rstrip() + " " + fragment + " " + desc[idx:]


def apply_fragment(node: dict, desc_key: str, fragment: str, marker: str,
                   label: str, changed: list) -> None:
    """조각을 「근거:」 앞에 한 번만 둔다. 이전 판이 뒤에 붙여 놨으면 걷어낸다."""
    d = node.get(desc_key, "")
    new = d.replace(OLD_G16_CAVEAT, "")
    if marker in new:
        if new != d:
            node[desc_key] = new
            changed.append(label + "(옛 위치 정리)")
        return
    node[desc_key] = insert_before_evidence(new, fragment)
    changed.append(label)


def replace_sentence(node: dict, desc_key: str, old: str, new: str,
                     label: str, changed: list) -> None:
    d = node.get(desc_key, "")
    if old in d:
        node[desc_key] = d.replace(old, new, 1)
        changed.append(label)


def main() -> int:
    with open(SPEC, encoding="utf-8") as f:
        spec = json.load(f)

    schemas = spec["components"]["schemas"]
    paths = spec["paths"]
    changed: list = []

    ws = schemas.get("WorkSession", {}).get("properties", {})

    # ① sessionNo
    set_desc(ws, "sessionNo", SESSION_NO_DESC, "WorkSession.sessionNo", changed)

    # ②③ stopReasonCode — 설명은 식별자만, 서술은 x-internal-note 로
    for name in ("WorkSession", "WorkSessionUpdate", "WorkSessionEnd", "WorkSessionCreate"):
        props = schemas.get(name, {}).get("properties", {})
        if "stopReasonCode" not in props:
            continue
        p = props["stopReasonCode"]
        if p.get("description") != STOP_REASON_DESC:
            p["description"] = STOP_REASON_DESC
            changed.append(f"{name}.stopReasonCode.description")
        if p.get("x-internal-note") != STOP_REASON_NOTE:
            p["x-internal-note"] = STOP_REASON_NOTE
            changed.append(f"{name}.stopReasonCode.x-internal-note")

    # ④ endedAt 에 G-16 보완 단서 · :end 는 틀린 문장 자체를 고친다
    if "endedAt" in ws:
        replace_sentence(ws["endedAt"], "description",
                         ENDED_AT_OLD_SENTENCE, ENDED_AT_NEW_SENTENCE,
                         "WorkSession.endedAt 문장 정정", changed)
        apply_fragment(ws["endedAt"], "description", ENDED_AT_CAVEAT,
                       "「진행 중」을 상태 컬럼으로 두지 않는 것이 원칙이나",
                       "WorkSession.endedAt", changed)

    end_op = paths.get("/production/work-sessions/{workSessionId}:end", {}).get("post")
    if end_op:
        # 1차 반영이 뒤에 덧붙여 둔 옛 단서를 걷어낸다
        d = end_op.get("description", "")
        if OLD_G16_CAVEAT in d:
            end_op["description"] = d.replace(OLD_G16_CAVEAT, "")
            changed.append(":end(옛 단서 정리)")
        replace_sentence(end_op, "description", END_OLD_SENTENCE, END_NEW_SENTENCE,
                         ":end 문장 정정", changed)

    # ⑤ statusCode 설명 · events 오퍼레이션 첫 문장 정정 + 사건 유형과 적재 주체
    set_desc(ws, "statusCode", STATUS_CODE_DESC, "WorkSession.statusCode", changed)

    ev_op = paths.get("/production/work-sessions/{workSessionId}/events", {}).get("post")
    if ev_op:
        replace_sentence(ev_op, "description", EVENTS_OLD_SENTENCE, EVENTS_NEW_SENTENCE,
                         "events POST 첫 문장 정정", changed)
        # 1차 반영이 「근거:」 뒤에 붙여 둔 것을 걷어내고 앞으로 옮긴다
        d = ev_op.get("description", "").rstrip()
        if d.endswith(EVENTS_TYPES.rstrip()):
            ev_op["description"] = d[: -len(EVENTS_TYPES.rstrip())].rstrip()
            changed.append("events POST(옛 위치 정리)")
        apply_fragment(ev_op, "description", EVENTS_TYPES, "사건 유형은 다섯이다",
                       "events POST", changed)

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
