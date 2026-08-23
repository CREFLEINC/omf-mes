#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""수집채널 매핑 계약에 조건 축·연결된 검사항목의 «읽을 것»을 되돌린다. 멱등.

무엇을 고치나 — 구현팀 질의 `omf-mes#203` 네 가지
--------------------------------------------------
    질문1  itemId · processId          조건 축을 되돌린다 (Create · Update · 응답)
    질문2  inspectionItemName 외        연결된 검사항목을 «읽을 수» 있게 한다
    질문3  inspectionItemIsCurrentRevision   옛 Rev 판정을 서버가 내린다
    질문4  isActive 의 뜻을 계약에 적는다

⭐ 질문1 — 조건 축은 «빼기로 한 것»이 아니라 «빠진 것»이다  → ⓑ
----------------------------------------------------------------
구현팀은 ⓐ(이번 판에서 뺀 것)로 가정하고 진행했다. **정본은 반대다.**

`W-05-07` §5-3 원문:

    **확정 — 유일 제약을 (설비 + 채널명 + 품목 + 공정)으로 넓힌다.**

§5-A 필드표에 「품목 조건」·「공정 조건」이 있고, §8 미결 1도 「조건 축을
A-7 부분 유일로 확정」으로 닫혀 있다. **계약이 그 확정을 안 옮겼다.**

⚠ 왜 조건 축이 필요한가 — 없으면 §5-3 이 든 사례가 저장되지 않는다.
같은 설비의 같은 채널이 「품목 A 면 외경, 품목 B 면 두께」로 갈릴 수 있다.
(설비 + 채널명)만으로 잠그면 **둘째 행이 중복으로 거부된다.**

⛔ 물리 표가 아직 없다고 물러서지 않는다 — `collection_channel` 은 물리 모델에
**없다**(실측 · §8 미결 1 이 `[신설]` 로 정의했다). 규칙 2 그대로다 —
**계약은 화면대로 쓰고**, 모델 결손은 데이터 모델 담당에게 **통지**한다.

⭐ 질문2 — 이름을 실어 내린다  → ⓐ
-----------------------------------
구현팀 지적이 정확하다. `inspectionItemId` 만 내려주는데 `inspection_item_spec`
을 읽는 길은 `GET /quality/inspection-plan-versions/{versionId}/items` 하나뿐이고,
`inspectionItemId` → `versionId` 로 되짚는 길이 계약에 **없다**(전수 실측 재확인).
그래서 §4 레이아웃의 「대상 검사항목」 열을 **그릴 수 없었다.**

ⓑ(단건·다건 조회 신설)를 택하지 않은 이유 — 행마다 한 번씩 불러 N+1 이 된다.
ⓒ(「연결됨」까지만)를 택하지 않은 이유 — **사용자가 무엇에 이었는지 화면에서
확인할 수 없다.** 편집 창을 열어 다시 골라 봐야 아는 것은 조회 화면이 아니다.

⭐ 질문3 — 옛 Rev 판정을 «서버»가 낸다
--------------------------------------
`W-05-07` §6 이 「옛 Rev 항목을 가리킨다 → ⚠ 경고」를 확정해 두었다. 화면이
버전을 따로 불러 `statusCode` 를 해석하면 **판정 규칙을 화면이 소유**하게 된다
— 이 저장소가 되풀이해 막아 온 형태다(전이표·범위 해석·마감 판정 전부 같다).
그래서 **판정 결과를 불리언으로 내린다.** 화면은 거짓일 때 경고만 띄운다.

⭐ 곁들여 — 단위 불일치 경고도 같은 이유로 막혀 있었다
------------------------------------------------------
§6 의 또 다른 예외 「단위 불일치 → ⚠ 경고 + 저장 허용」(§5-5)도 **연결된
검사항목의 단위를 읽을 수 없어** 판정이 불가능했다. 질문2 와 «같은 결손»이라
`inspectionItemUnitCode` 를 함께 내린다. ⚠ 구현팀이 묻지 않은 항목이지만,
고치지 않으면 다음 주에 같은 형태의 질의가 한 건 더 온다.

⭐ 질문4 — 사용 중지하면 «값이 버려진다»  → ⓐ
----------------------------------------------
⛔ ⓑ(목록에서만 빠지고 값은 그대로 담긴다)는 **성립하지 않는다.** 이 매핑 행이
바로 「이 신호를 어느 검사항목에 담을 것인가」의 규칙이다. 규칙을 끄면 담을 곳이
정해지지 않고, §5-2 가 미매핑에 대해 이미 확정한 대로 **버려진다.** ⓑ 는 값이
어디로 가는지 말할 수 없는 안이다.

**확인 창 문구는 이렇게 말할 수 있다** — 구현팀이 임시로 쓴 중립 문면을 대신한다.

    사용 중지하면 이 채널로 들어오는 값은 저장되지 않고 버려집니다.
    채널과 이어 둔 검사 항목은 지워지지 않으며 다시 켤 수 있습니다.

⭐ 양방향으로 만든 것이 맞다 — `:activate` 부재는 의도된 것이다. 이 자원은
`isActive` 가 수정 본문의 한 필드라 끄는 것도 켜는 것도 같은 요청이다(B-4 는
「물리 삭제 금지」이지 「되살리기 금지」가 아니다). 형제 화면(`W-05-11`·
`W-05-13`)에 전용 경로가 있는 것은 그쪽이 `:deactivate` 와 `:dispose` 를 가르는
자원이기 때문이고(B-16 두 축), 여기는 그 축이 없다.

쓰기
----
    python3 deliverables/openapi/patch-203-collection-channel-mapping.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "equipment-05설비툴.json")
COLLECTION = "/maintenance/collection-channels"
ONE = "/maintenance/collection-channels/{collectionChannelId}"

FK = {"type": ["integer", "null"], "format": "int64", "example": 1001}


def fk(desc: str) -> dict:
    d = dict(FK)
    d["description"] = desc
    return d


def text(desc: str, example: str) -> dict:
    return {"type": ["string", "null"], "description": desc, "example": example}


CONDITION_ITEM = (
    "품목 조건 — 비면 「전체」다(이 설비의 이 채널은 언제나 그 항목으로 간다). "
    "지정하면 그 품목을 생산할 때만 적용된다. 유일 범위를 이룬다. "
    "근거: W-05-07 §5-3 · omf-mes#203"
)
CONDITION_PROCESS = (
    "공정 조건 — 비면 「전체」다. 지정하면 그 공정에서만 적용된다. "
    "유일 범위를 이룬다. 근거: W-05-07 §5-3 · omf-mes#203"
)

RESPONSE_FIELDS = {
    "itemId": fk(CONDITION_ITEM),
    "itemCode": text("품목 조건의 표시용 코드 — 비면 「전체」", "ABC-123"),
    "processId": fk(CONDITION_PROCESS),
    "processCode": text("공정 조건의 표시용 코드 — 비면 「전체」", "PRS"),
    "inspectionItemName": text(
        "연결된 검사 항목의 이름. inspectionItemId 가 비면 함께 빈다"
        "(「미매핑」). ⭐ 이 값이 없으면 화면이 「연결됨」까지만 말할 수 있어 "
        "무엇에 이었는지 보일 수 없다. 근거: W-05-07 §4 · omf-mes#203 질문2",
        "사이클타임",
    ),
    "inspectionItemCode": text("연결된 검사 항목의 코드", "CYCLE_TIME"),
    "inspectionItemUnitCode": text(
        "연결된 검사 항목의 «저장» 단위. 이 행의 unitCode(수신값의 단위)와 "
        "다르면 화면이 경고한다 — ⛔ 자동 변환하지 않는다(W-05-07 §5-5 · A-8). "
        "이 값이 없으면 그 경고를 판정할 수 없다",
        "SECOND",
    ),
    "inspectionPlanVersionId": fk(
        "연결된 검사 항목이 속한 검사기준 버전(Rev). 검사기준 Rev 가 오르면 "
        "매핑은 옛 항목을 가리킨 채 남는다(W-05-07 §5-2)"
    ),
    "inspectionPlanVersion": {
        "type": ["integer", "null"],
        "description": "그 버전의 Rev 번호 — 경고 문구에 함께 보인다",
        "example": 2,
    },
    "inspectionItemIsCurrentRevision": {
        "type": ["boolean", "null"],
        "description": (
            "연결된 검사 항목이 «최신» Rev 의 것인가. ⛔ 서버가 판정한다 — "
            "화면이 버전을 따로 불러 statusCode 를 해석하면 판정 규칙을 화면이 "
            "소유하게 된다. 거짓이면 화면이 「이 검사항목은 이전 Rev 입니다」를 "
            "경고한다. ⛔ 자동으로 옮기지 않는다 — 새 Rev 의 어느 항목에 "
            "대응하는지 기계가 모른다(W-05-07 §6·§8-2). "
            "inspectionItemId 가 비면 함께 빈다",
        ),
        "example": True,
    },
}

INPUT_FIELDS = {
    "itemId": fk(CONDITION_ITEM),
    "processId": fk(CONDITION_PROCESS),
}

UNIQUE_NOTE = (
    "⭐ 유일 범위는 (설비 + 채널명 + 품목 조건 + 공정 조건)이다 — 조건이 비어 "
    "있을 수 있어 일반 UNIQUE 가 아니라 부분 유일 인덱스 형태다(공유계약 A-7 · "
    "COALESCE). 같은 채널에 조건이 다른 행이 여럿 설 수 있다 — 「품목 A 면 외경, "
    "품목 B 면 두께」. 409 문구에 유일 범위를 담는다(A-1): "
    "「이 설비의 <채널명> 채널에 품목·공정 조건이 같은 매핑이 이미 있습니다」. "
    "근거: W-05-07 §5-3·§6 · omf-mes#203 질문1"
)

IS_ACTIVE_NOTE = (
    "⭐ isActive = false 의 뜻 — 매핑이 «적용되지 않는다». 이 채널로 들어오는 "
    "값은 저장되지 않고 버려진다(미매핑과 같아진다 · W-05-07 §5-2). "
    "⛔ 「목록에서만 빠지고 값은 그대로 담긴다」가 아니다 — 이 행이 곧 「이 신호를 "
    "어느 검사항목에 담는가」의 규칙이라, 끄면 담을 곳이 정해지지 않는다. "
    "이어 둔 검사 항목은 지워지지 않으며 같은 요청으로 다시 켤 수 있다 — "
    "끄는 것도 켜는 것도 이 PUT 하나다(:activate 를 따로 두지 않는 이유). "
    "B-4 는 물리 삭제를 금지하는 조항이지 되살리기를 금지하지 않는다. "
    "근거: omf-mes#203 질문4"
)


def detect_indent(original: str, doc: dict):
    body = original.rstrip("\n")
    for candidate in (1, 2, 4):
        if json.dumps(doc, ensure_ascii=False, indent=candidate) == body:
            return candidate
    return None


def merge(props: dict, additions: dict, after: str) -> None:
    """`after` 키 바로 뒤에 끼워 넣는다 — 읽는 차례를 지킨다. 멱등."""
    for key, value in additions.items():
        props.pop(key, None)
    rebuilt: dict = {}
    for key, value in props.items():
        rebuilt[key] = value
        if key == after:
            rebuilt.update(json.loads(json.dumps(additions)))
    if after not in props:
        rebuilt.update(json.loads(json.dumps(additions)))
    props.clear()
    props.update(rebuilt)


def append_note(op: dict, note: str) -> None:
    """⛔ 덧붙이지 않고 통째로 다시 조립한다 — 덧붙이면 멱등이 무너진다."""
    base = (op.get("description") or "").split("\n\n⭐")[0].rstrip()
    op["description"] = f"{base}\n\n⭐{note.lstrip('⭐').lstrip()}" if base else note


def main() -> int:
    original = open(CONTRACT, encoding="utf-8").read()
    doc = json.loads(original)
    indent = detect_indent(original, doc)
    if indent is None:
        print("⛔ 들여쓰기를 알아낼 수 없다 — 덮어쓰지 않는다", file=sys.stderr)
        return 1
    tail = original[len(original.rstrip("\n")):]

    schemas = doc["components"]["schemas"]

    # ① 응답 — 조건 축 + 연결된 검사항목을 읽을 것
    merge(schemas["CollectionChannel"]["properties"], RESPONSE_FIELDS,
          after="inspectionItemId")

    # ② 입력 — 조건 축을 보낼 자리
    merge(schemas["CollectionChannelCreate"]["properties"], INPUT_FIELDS,
          after="inspectionItemId")
    merge(schemas["CollectionChannelUpdate"]["properties"], INPUT_FIELDS,
          after="inspectionItemId")

    # ③ 유일 범위와 사용 중지의 뜻을 계약이 말한다
    append_note(doc["paths"][COLLECTION]["post"], UNIQUE_NOTE)
    put = doc["paths"][ONE]["put"]
    append_note(put, f"{UNIQUE_NOTE}\n\n{IS_ACTIVE_NOTE}")

    updated = json.dumps(doc, ensure_ascii=False, indent=indent) + tail
    if updated == original:
        print("  이미 반영돼 있다 — 변경 없음")
        return 0
    open(CONTRACT, "w", encoding="utf-8").write(updated)
    print("  ✅ 조건 축(품목·공정) 되돌림 — 응답·등록·수정 (질문1)")
    print("  ✅ 연결된 검사항목 이름·코드·단위·버전 (질문2·곁들여)")
    print("  ✅ 옛 Rev 판정을 서버가 내린다 (질문3)")
    print("  ✅ isActive 의 뜻을 계약에 적었다 (질문4)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
