#!/usr/bin/env python3
"""검사자·단말을 «서버가 채우는 값»으로 되돌린다 — 구현팀 질의 omf-mes#173.

## 왜

`W-01-01`(IQC 수입검사·판정) 착수 중 구현팀이 멈췄다. 검사 결과 임시 저장을 만들려는데
`InspectionResultCreate.inspectorId` 가 **필수**인데 **화면이 그 값을 만들 수 없다**고 물었다.
실측하니 맞았다.

    mdm.worker.worker_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY
    mdm.worker.app_user_id  bigint REFERENCES app.app_user(app_user_id)   -- [H-1] 작업자↔입력자 구분

두 키는 **다른 채번**이고 `app_user_id` 는 **비어 있을 수 있다**. 그런데 세션(`Session`)이 주는
것은 `userId`(= `app_user_id`)뿐이고, `GET /mdm/workers` 에는 `appUserId` 로 좁히는 질의가 없다.
⛔ **`session.userId` 를 `inspectorId` 로 보내면 품질 감사 기록에 엉뚱한 사람이 검사자로 박히고,
값이 그럴듯한 정수라 아무도 눈치채지 못한다.**

## ⭐ 뿌리 — 공유계약 D-5·F-2 를 계약이 적용하지 않았다

답은 이미 우리 공유계약에 있었다.

**F-2(축은 셋이다 — 인증·기능 구성·귀속)** — 「누가 한 일로 기록하는가」는 셸마다 수단이 다르다.

    관리웹(W-)          계정 토큰(app_user)           ← 인증 주체 그 자체
    현장 단말·모바일(P-·M-)  단말 토큰 + 사번 귀속        ← 로그인이 «없다»

**D-5(귀속 정보는 세션이 아니다)** — 현장 단말은 사번을 헤더로 싣고, **쓰기 요청에 필수**다.

    Authorization: Bearer <단말 토큰>       ← 인증
    X-Worker-No: 900028                     ← 귀속. 인증 아님

⭐ **즉 검사한 사람은 두 셸 모두 서버가 이미 알고 있다.** 관리웹은 계정 토큰의 앱 사용자에서
`mdm.worker.app_user_id` 로, 현장 단말은 `X-Worker-No` 의 사번에서 작업자를 푼다.
계약이 그 위에 본문으로 한 번 더 받고 있었고, **같은 것을 두 경로가 말하면 어긋날 자리만 생긴다.**

## 실측 — 서버가 채우는 것이 이미 관행이었고 검사 결과만 예외였다

    ① 쓰기 본문 148개 전수 — createdBy/updatedBy 를 받는 곳 0건
       (기준: deliverables/openapi/*.json 7벌의 paths 안 requestBody 가 가리키는
        components.schemas = 148개. 그 안의 속성 이름을 센다.
        ⚠ 안 보는 것: 질의 파라미터 · 응답 스키마 · 경로 파라미터 · 설명문 안의 언급)
       물리 모델은 표 129개 중 117개가 created_by 를 갖는데 계약은 한 번도 받지 않는다.

    ② 화면 스펙에서 「로그인 사용자」로 표기된 저장 칸 7건 중
       계약이 본문으로 받는 것은 «검사자 2건»뿐이다.
       나머지 5건은 저장 경로가 실재하는데도 본문에 그 칸이 없다 —
       POST /trace/lots · POST /logistics/inbound-receipts ·
       POST /maintenance/breakdowns · POST /maintenance/breakdowns/{id}:complete

## 무엇을 한다 — 두 갈래

### 1. `InspectionResultCreate` 에서 `inspectorId`(필수)·`terminalId` 를 **뺀다**

⛔ **「선택으로 낮춘다」가 아니라 「뺀다」로 한다.** 선택으로 남기면 **서버가 무시하는 칸**이
되는데, 그러면 누군가 값을 넣어 보내고 서버가 조용히 버린다 — 「내가 보낸 검사자가 안 들어갔다」가
나중에 버그로 온다. 값을 안 쓸 거면 받는 자리를 두지 않는 편이 정직하다.
우리 규칙도 「사용처가 0이면 두지 않는다」이다.

`terminalId` 도 같은 성질이다. **관리웹에는 단말 개념이 없고**(F-2 에서 단말 토큰의 대상은
현장 단말·모바일뿐), 현장 단말에서는 **요청을 인증한 것이 단말 토큰이므로 서버가 이미 안다.**
물리 모델도 `terminal_id` 를 비울 수 있게 두었다(`NOT NULL` 없음).

### 2. `InspectionResultUpdate` 에서 `inspectorId` 를 **뺀다**

같은 이유다. 임시 저장 갱신에서도 검사자는 서버가 정한다.

## ⛔ 응답 스키마 `InspectionResult` 는 «건드리지 않는다»

화면은 「누가 검사했나」를 **보여야** 한다(`W-03-05` 드로어 · `W-01-01` §5-3 재검사 이전 회차).
받는 자리와 보이는 자리는 다른 축이다. `inspectorId`·`terminalId` 는 응답에 그대로 남는다.

## 택하지 않은 안

**세션에 `workerId` 를 싣는다** — 화면이 그 값을 다시 본문에 담아 보내야 하고, 담는 순간
「같은 것을 두 경로가 말한다」로 되돌아간다. 작업자가 연결되지 않은 계정의 사정도 화면이
설명하게 된다. ⭐ 서버가 풀면 그 판단이 서버 한 곳에 모인다.

**`GET /mdm/workers` 에 `appUserId` 질의를 더한다** — 로그인마다 조회가 하나 늘고 그 조회가
실패하면 저장이 통째로 막힌다. ⛔ 게다가 현장 단말(`P-02-13`)에는 앱 사용자가 없어 **아예
통하지 않는다** — 검사 3형 중 하나를 못 덮는 안이다.

## ⚠ 남는 것 — 이 패치가 풀지 않는다

`X-Worker-No` 헤더가 **계약 7벌 어디에도 선언돼 있지 않다**(전수 검색 0건 · 계약이 선언한
헤더 18건은 전부 `If-Match`·`Idempotency-Key`). D-5 가 「쓰기에 필수」라 정했는데 받을 자리가
계약에 없다 — **저장 충돌 토큰 19건과 같은 형태다.** ⛔ 다만 그 범위는 검사 밖으로 넓어
(현장 단말·모바일 39화면의 쓰기 경로 전체) **별건으로 뗀다.**

⭐ **관리웹인 `W-01-01` 은 이 패치만으로 착수 가능하다** — 계정 토큰으로 인증하므로 헤더가
필요 없다.
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

QUALITY = "quality-03품질.json"

# 파일마다 직렬화 형식이 다르다 — 읽을 때 재어 두고 쓸 때 그대로 돌려준다
FORMAT = {}

# 뺄 것 — 스키마별 속성 이름
DROP = {
    "InspectionResultCreate": ("inspectorId", "terminalId"),
    "InspectionResultUpdate": ("inspectorId",),
}

# ⛔ 건드리지 않는다 — 받는 자리와 보이는 자리는 다른 축이다
KEEP = ("InspectionResult",)

NOTE = (
    " ⭐ 검사자·단말은 «보내지 않는다» — 서버가 인증 주체에서 채운다"
    "(관리웹은 계정 토큰, 현장 단말·모바일은 사번 귀속 헤더)."
)

INTERNAL = (
    " ⧉ 공개 설명에서 걷은 근거 표기(client#173 · 2026-08-21): "
    "공유계약 D-5(귀속은 세션이 아니다)·F-2(축은 셋이다) · "
    "mdm.worker.worker_id 와 app.app_user.app_user_id 는 다른 채번"
)


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


def drop_fields(spec, log):
    """멱등 — 이미 빠져 있으면 「이미 없다」만 적는다."""
    schemas = spec["components"]["schemas"]
    for schema_name, fields in DROP.items():
        s = schemas[schema_name]
        props = s.get("properties", {})
        required = s.get("required", [])
        for field in fields:
            if field in props:
                del props[field]
                log.append("  ⛔ %s.%s 속성 제거" % (schema_name, field))
            else:
                log.append("  · %s.%s 이미 없다" % (schema_name, field))
            if field in required:
                required.remove(field)
                log.append("  ⛔ %s.required 에서 %s 제거" % (schema_name, field))


def retouch(spec, log):
    """설명에 「보내지 않는다」를 적는다 — 멱등."""
    schemas = spec["components"]["schemas"]
    for schema_name in DROP:
        s = schemas[schema_name]
        desc = s.get("description", "")
        if NOTE.strip() not in desc:
            s["description"] = (desc + NOTE) if desc else NOTE.strip()
            log.append("  ✎ %s.description 보강" % schema_name)
        else:
            log.append("  · %s.description 이미 적혀 있다" % schema_name)
        note = s.get("x-internal-note", "")
        if "client#173" not in note:
            s["x-internal-note"] = (note + INTERNAL) if note else INTERNAL.strip()
            log.append("  ✎ %s.x-internal-note 근거 표기" % schema_name)


def guard(spec):
    """⛔ 응답 스키마가 상하지 않았는지 본다."""
    schemas = spec["components"]["schemas"]
    for name in KEEP:
        props = schemas[name].get("properties", {})
        for field in ("inspectorId", "terminalId"):
            if field not in props:
                raise SystemExit(
                    "⛔ 응답 스키마 %s 에서 %s 가 사라졌다 — 보이는 자리는 건드리지 않는다"
                    % (name, field)
                )
    print("✅ 응답 스키마 %s — inspectorId·terminalId 그대로다" % ", ".join(KEEP))


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
    roundtrip()
    spec = load(QUALITY)

    print("\n== 1·2. 검사자·단말을 쓰기 본문에서 제거 ==")
    drop_fields(spec, log)

    print("== 3. 설명 정정 — 「보내지 않는다」 ==")
    retouch(spec, log)

    guard(spec)
    save(QUALITY, spec)

    print()
    for line in log:
        print(line)

    after = load(QUALITY)["components"]["schemas"]
    print("\n== 최종 — 검사 결과 쓰기 본문 ==")
    for name in DROP:
        s = after[name]
        print("   %-26s 속성 %2d · 필수 %2d" % (name, len(s.get("properties", {})), len(s.get("required", []))))
        for field in ("inspectorId", "terminalId"):
            state = "남아 있다 ⛔" if field in s.get("properties", {}) else "없다 ✅"
            print("       %-14s %s" % (field, state))


if __name__ == "__main__":
    main()
