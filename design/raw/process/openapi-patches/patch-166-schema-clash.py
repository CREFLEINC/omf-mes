#!/usr/bin/env python3
"""계약 7벌을 한 문서로 병합할 때 멈추는 자리를 없앤다 — 구현팀 회신 omf-mes#166.

## 왜

클라이언트는 도메인별 계약을 **한 문서로 병합해** 타입을 만든다. 같은 이름의
스키마가 형태까지 다르면 병합기가 멈춘다(덮으면 어느 계약의 타입이 살았는지
알 수 없어지므로 멈추는 것이 설계 의도다). 형태 충돌 **4건**을 없앤다.

## 무엇을 한다 — 다섯 갈래

1. **`ConflictResponse` 는 두 가지를 한 이름으로 부르고 있었다** — 이름을 가른다
   · 앞 계열(공통·자재창고·기준정보) = **저장 충돌의 원인**(다른 사용자·ERP 재동기화·
     워커 리스). 공유계약 B-1 이 요구한 축이다 → **이름·형태 그대로 둔다**
     (구현팀이 이미 이 셋으로 코드를 만들었다)
   · 뒤 계열(생산실행·품질·제품출하) = **거부의 업무 사유**로 도메인마다 값이 다르다
     → 도메인별 이름으로 바꾸고, B-1 이 요구하는 `conflictCause` 를 **선택**으로 더한다
2. **`ErrorItem` 을 한 형태로** — 05설비툴이 `message` 만 필수인 축소형이었다.
   생산실행·품질·제품출하에는 `uniqueScope`(어느 유일키 범위에서 중복인지)가 없었다.
   ⭐ 선택 필드 추가라 기존 구현이 깨지지 않는다
3. **`ErrorResponse` 를 한 형태로** — 05설비툴만 `{code, message, details}` 라는
   다른 오류 봉투를 썼다. 나머지 여섯 벌의 `{errors:[…]}` 로 맞춘다
4. **`LotHold` 를 한 형태로** — 같은 자원(`trace.lot_hold`)을 두 벌이 따로 적고 있었다.
   · 자재창고 쪽 = **물리 모델에 착지한 정의**(원천 표·컬럼 표기 · nullable · 길이 제약)
   · 품질 쪽 = 그것을 손으로 옮긴 얇은 사본 — ⛔ **nullable 을 잃었다.**
     해제 시각·해제자·해제 조건·비고·단위를 「항상 있다」고 말하는데,
     **보류 중인 건은 해제 관련 칸이 비어 있다**(공유계약 G-9 — 모르는 값과 없는 값)
   → 자재창고 정의를 정본으로 삼고, 품질 쪽 표시용 3필드를 그 위에 얹는다
5. **05설비툴에 저장 충돌 보호를 신설** — 오퍼레이션 35개 중 `If-Match` 가 0건이었다

## 저장 충돌 보호를 «어디에» 다는가 — 자동으로 붙이지 않는다

⛔ 전수 부착은 틀린다. **잠그는 대상과 버전 축이 일치하는 곳**에만 단다.

| 갈래 | 다는가 | 왜 |
| --- | :-: | --- |
| 갱신(`PUT`) | ✅ | 자원 자신을 고쳐 쓰므로 버전 축이 자원과 일치한다 |
| 상태 전이(`:동사`) | ✅ | 전이는 「현재 상태」를 전제로 한다 — 남이 먼저 전이했으면 막아야 한다 |
| 신규 생성(`POST`) | ⛔ | 아직 자원이 없어 버전 축이 없다. 재전송 방어는 멱등 키가 맡는다 |
| 조회(`GET`) | ⛔ | 쓰지 않는다 |

⭐ **토큰을 «받을 곳»까지가 한 세트다**(2026-08-17 구현팀 지적 — 19건이 그랬다).
`If-Match` 를 요구하는 자원의 **상세 조회 200 에 `ETag` 응답 헤더**를 함께 선언한다.

## ⚠ 물리 모델에 보전 표가 없다

`mes_postgresql_physical_model.sql` 에 고장·보전오더·보전실적·비가동·툴사용
표가 없다(있는 것은 `quality.equipment_calibration` 하나 — 이슈 #67 「설비보전이
물리 모델 선언 Scope 밖」). **그것을 이유로 계약을 물리지 않는다** — 데이터
모델은 설계 결정을 앞설 수 없다(사용자 확정 2026-08-18). 모델 결손은 #67 이 이미
들고 있다.

쓰기: python3 deliverables/openapi/patch-166-schema-clash.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

COMMON = "app-공통.json"
LOGISTICS = "logistics-01자재창고.json"
MDM = "mdm-기준정보.json"
PRODUCTION = "production-02생산실행.json"
QUALITY = "quality-03품질.json"
SHIPMENT = "shipment-04제품출하.json"
EQUIPMENT = "equipment-05설비툴.json"

# 뒤 계열 — 개명할 이름
RENAME = {
    PRODUCTION: "ProductionConflictResponse",
    QUALITY: "QualityConflictResponse",
    SHIPMENT: "ShipmentConflictResponse",
}

# 앞 계열이 쓰는 정본 형태 (기준정보 계약에서 가져온 것)
CONFLICT_CAUSE = {
    "type": "string",
    "enum": ["user", "erpSync", "workerLease"],
    "description": (
        "충돌 원인. 근거: 공유계약 B-1 확장 — user=다른 사용자, erpSync=ERP 재동기화 배치, "
        "workerLease=워커가 처리 중. 구분 없이 내려주면 화면이 「다른 사용자가 먼저 "
        "수정했습니다」라는 사실과 다른 안내를 하게 된다"
    ),
    "example": "user",
}

UNIQUE_SCOPE = {
    "type": "array",
    "items": {"type": "string"},
    "description": (
        "code=UNIQUE_VIOLATION 일 때 어느 유일키 범위에서 중복인지. 근거: 공유계약 A-1 — "
        "범위 없이 「중복」만 오면 화면이 문구를 만들 수 없다"
    ),
}

LOTHOLD_EXTRAS = {
    "lotNo": {"type": "string", "example": "값"},
    "itemId": {"type": "integer", "format": "int64", "example": 1001},
    "lotStatusCode": {
        "type": "string",
        "description": "이 보류가 걸었을 때 LOT 이 간 상태",
        "example": "IQC",
    },
}

ETAG_HEADER = {
    "description": (
        "낙관적 잠금 토큰 — 이 행의 version_no. 다음 쓰기의 If-Match 에 그대로 담는다. "
        "본문 필드로는 내리지 않는다 — 표시하지 않되 전달한다"
    ),
    "schema": {"type": "string"},
    "x-internal-note": (
        "본문 필드로 내리지 않는 이유는 공유계약 A-4(version_no 는 화면에 노출하지 "
        "않는다)이고, 전송 자체는 A-4 가 함께 요구하는 B-1(낙관적 잠금) 구현에 필요하다"
    ),
}

IF_MATCH_PARAM = {
    "name": "If-Match",
    "in": "header",
    "required": True,
    "schema": {"type": "string"},
    "description": (
        "낙관적 잠금용 version_no. 값은 같은 리소스의 상세 GET 200 이 내려주는 ETag "
        "응답 헤더에서 받는다 — version_no 는 공유계약 A-4 에 따라 본문 필드로 "
        "노출하지 않는다. 근거: 공유계약 B-1"
    ),
}

CONFLICT_409 = {
    "description": (
        "저장 충돌 — 다른 사용자가 먼저 고쳤다. 업무 규칙 위반(상태 잠김·참조 존재)은 "
        "409 가 아니라 400 이다"
    ),
    "content": {
        "application/json": {"schema": {"$ref": "#/components/schemas/ConflictResponse"}}
    },
}

# 05설비툴 — 저장 충돌 보호를 다는 자리 (경로, 메서드)
EQUIP_LOCKED = [
    ("/maintenance/breakdowns/{breakdownId}", "put"),
    ("/maintenance/breakdowns/{breakdownId}:start-handling", "post"),
    ("/maintenance/breakdowns/{breakdownId}:complete", "post"),
    ("/maintenance/orders/{maintenanceOrderId}:cancel", "post"),
    ("/maintenance/results/{maintenanceResultId}", "put"),
    ("/maintenance/downtimes/{downtimeId}", "put"),
    ("/maintenance/downtimes/{downtimeId}:close", "post"),
    ("/maintenance/collection-channels/{collectionChannelId}", "put"),
]

# 05설비툴 — 토큰을 내려줄 상세 조회
EQUIP_ETAG_GETS = [
    "/maintenance/breakdowns/{breakdownId}",
    "/maintenance/orders/{maintenanceOrderId}",
    "/maintenance/results/{maintenanceResultId}",
    "/maintenance/downtimes/{downtimeId}",
    "/maintenance/collection-channels/{collectionChannelId}",
]


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
    """⚠ 원본과 «같은 직렬화»로 쓴다 — 들여쓰기 폭도 끝 개행도 파일마다 다르다.

    형식이 어긋나면 손대지 않은 자리까지 diff 에 들어와 검토가 불가능해지고,
    구현팀이 생성물을 SHA-256 으로 재현 대조하는 절차도 헛돈다.
    실제로 한 번 어긋나 28,000줄이 diff 에 들어왔다.
    """
    fmt = FORMAT.get(name) or {"indent": 1, "newline": False}
    body = json.dumps(spec, ensure_ascii=False, indent=fmt["indent"])
    if fmt["newline"]:
        body += "\n"
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as fh:
        fh.write(body)


def canonical_error_schemas():
    """앞 계열의 오류 봉투 정본을 기준정보 계약에서 그대로 가져온다."""
    schemas = load(MDM)["components"]["schemas"]
    return schemas["ErrorResponse"], schemas["ErrorItem"]


def rename_conflict(name, new_name, log):
    spec = load(name)
    schemas = spec["components"]["schemas"]
    if new_name in schemas:
        log.append("  %-26s 이미 %s — 건너뜀" % (name, new_name))
        return
    schema = schemas.pop("ConflictResponse")

    # B-1 이 요구하는 원인 축을 선택으로 더한다 (필수로 두면 기존 서버 구현이 틀린다)
    props = schema.setdefault("properties", {})
    if "conflictCause" not in props:
        props["conflictCause"] = dict(CONFLICT_CAUSE)
        props["conflictCause"]["description"] += (
            " — code=VERSION_CONFLICT 일 때 함께 내린다"
        )
    schema["x-internal-note"] = (
        "이름을 가른 이유: 앞 계열(app-공통·logistics-01·mdm)의 ConflictResponse 는 "
        "저장 충돌의 «원인»만 말하고, 이쪽은 거부의 «업무 사유»를 말한다. 두 축은 "
        "직교하며 겹치는 지점은 VERSION_CONFLICT ↔ conflictCause=user 하나다. "
        "한 이름으로 두면 계약 병합이 멈춘다(구현팀 회신 omf-mes#166)."
    )
    schemas[new_name] = schema

    # 문서 안의 모든 참조를 새 이름으로
    blob = json.dumps(spec, ensure_ascii=False)
    blob = blob.replace(
        '"#/components/schemas/ConflictResponse"',
        '"#/components/schemas/%s"' % new_name,
    )
    spec = json.loads(blob)
    save(name, spec)
    refs = blob.count('"#/components/schemas/%s"' % new_name)
    log.append("  %-26s ConflictResponse → %s · 참조 %d곳 · conflictCause 선택 추가"
               % (name, new_name, refs))


def add_unique_scope(name, log):
    spec = load(name)
    item = spec["components"]["schemas"]["ErrorItem"]
    props = item.setdefault("properties", {})
    if "uniqueScope" in props:
        log.append("  %-26s uniqueScope 이미 있음 — 건너뜀" % name)
        return
    # message 앞에 끼워 넣어 앞 계열과 프로퍼티 순서를 맞춘다
    rebuilt = {}
    for key, value in props.items():
        if key == "message":
            rebuilt["uniqueScope"] = dict(UNIQUE_SCOPE)
        rebuilt[key] = value
    if "uniqueScope" not in rebuilt:
        rebuilt["uniqueScope"] = dict(UNIQUE_SCOPE)
    item["properties"] = rebuilt
    save(name, spec)
    log.append("  %-26s ErrorItem 에 uniqueScope 선택 추가" % name)


def unify_lothold(log):
    """자재창고의 모델 착지 정의를 정본으로 삼아 품질 쪽을 그것과 같게 만든다.

    ⚠ 두 벌의 `x-internal-note` 가 서로 다르면 그것만으로도 병합이 멈춘다
    (병합기는 description·example·examples·title 만 걷어낸다). 두 주석을 **합쳐**
    양쪽에 같이 실어 «내용을 잃지 않으면서» 형태를 하나로 만든다.
    """
    logistics = load(LOGISTICS)
    quality = load(QUALITY)
    hold = logistics["components"]["schemas"]["LotHold"]
    q_hold = quality["components"]["schemas"]["LotHold"]

    props = hold.setdefault("properties", {})
    added = [k for k in LOTHOLD_EXTRAS if k not in props]
    if added:
        rebuilt = {}
        for key, value in props.items():
            rebuilt[key] = value
            if key == "lotId":
                for extra in ("lotNo", "itemId"):
                    if extra not in props:
                        rebuilt[extra] = dict(LOTHOLD_EXTRAS[extra])
        if "lotStatusCode" not in rebuilt:
            rebuilt["lotStatusCode"] = dict(LOTHOLD_EXTRAS["lotStatusCode"])
        hold["properties"] = rebuilt

    # 두 주석을 합친다 — 어느 쪽 근거도 버리지 않는다
    notes = []
    for source in (hold, q_hold):
        note = (source.get("x-internal-note") or "").strip()
        if note and note not in notes:
            notes.append(note)
    if notes:
        hold["x-internal-note"] = " / ".join(notes)

    if q_hold == hold:
        log.append("  %-26s LotHold 이미 한 형태 — 건너뜀" % QUALITY)
        return

    save(LOGISTICS, logistics)
    quality["components"]["schemas"]["LotHold"] = json.loads(
        json.dumps(hold, ensure_ascii=False)
    )
    save(QUALITY, quality)
    log.append("  %-26s LotHold 에 %s 선택 추가 · 주석 합침"
               % (LOGISTICS, " · ".join(added) if added else "(없음)"))
    log.append("  %-26s LotHold 를 모델 착지 정의로 교체 — nullable 5칸 회복"
               % QUALITY)


def fix_equipment_errors(log):
    spec = load(EQUIPMENT)
    schemas = spec["components"]["schemas"]
    canon_response, canon_item = canonical_error_schemas()
    changed = []
    if schemas.get("ErrorResponse") != canon_response:
        schemas["ErrorResponse"] = canon_response
        changed.append("ErrorResponse")
    if schemas.get("ErrorItem") != canon_item:
        schemas["ErrorItem"] = canon_item
        changed.append("ErrorItem")
    if not changed:
        log.append("  %-26s 오류 봉투 이미 정합 — 건너뜀" % EQUIPMENT)
        return
    save(EQUIPMENT, spec)
    log.append("  %-26s %s 를 여섯 벌 형태로 교체" % (EQUIPMENT, " · ".join(changed)))


def add_equipment_locking(log):
    spec = load(EQUIPMENT)
    components = spec.setdefault("components", {})
    params = components.setdefault("parameters", {})
    schemas = components.setdefault("schemas", {})

    if "IfMatchVersion" not in params:
        params["IfMatchVersion"] = dict(IF_MATCH_PARAM)
    if "ConflictResponse" not in schemas:
        conflict = load(MDM)["components"]["schemas"]["ConflictResponse"]
        schemas["ConflictResponse"] = conflict

    attached, etagged, missing = 0, 0, []
    for path, method in EQUIP_LOCKED:
        op = (spec["paths"].get(path) or {}).get(method)
        if op is None:
            missing.append("%s %s" % (method.upper(), path))
            continue
        plist = op.setdefault("parameters", [])
        ref = {"$ref": "#/components/parameters/IfMatchVersion"}
        if ref not in plist:
            plist.append(ref)
            attached += 1
        op.setdefault("responses", {}).setdefault("409", dict(CONFLICT_409))

    for path in EQUIP_ETAG_GETS:
        op = (spec["paths"].get(path) or {}).get("get")
        if op is None:
            missing.append("GET %s" % path)
            continue
        ok = (op.get("responses") or {}).get("200")
        if ok is None:
            missing.append("GET %s 200없음" % path)
            continue
        headers = ok.setdefault("headers", {})
        if "ETag" not in headers:
            headers["ETag"] = dict(ETAG_HEADER)
            etagged += 1

    save(EQUIPMENT, spec)
    log.append("  %-26s If-Match %d곳 · 409 부착 · ETag 응답 헤더 %d곳"
               % (EQUIPMENT, attached, etagged))
    if missing:
        log.append("  ⛔ 못 찾은 자리: %s" % " / ".join(missing))


def roundtrip_guard():
    """계약 7벌을 읽고 그대로 다시 써서 «바이트 동일»한지 먼저 본다.

    하나라도 어긋나면 여기서 멈춘다 — 실제로 한 번 어긋나 28,000줄이 diff 에
    들어왔다(파일마다 들여쓰기가 1칸·2칸으로 다르고 끝 개행도 갈린다).
    """
    bad = []
    for name in (COMMON, LOGISTICS, MDM, PRODUCTION, QUALITY, SHIPMENT, EQUIPMENT):
        path = os.path.join(HERE, name)
        with open(path, encoding="utf-8") as fh:
            before = fh.read()
        fmt = measure(before)
        after = json.dumps(json.loads(before), ensure_ascii=False, indent=fmt["indent"])
        if fmt["newline"]:
            after += "\n"
        if before != after:
            bad.append("%s (원본 %d자 ↔ 재직렬화 %d자)" % (name, len(before), len(after)))
    if bad:
        raise SystemExit(
            "⛔ 직렬화가 원본과 다르다 — 손대지 않은 자리까지 diff 에 들어간다.\n   "
            + "\n   ".join(bad)
        )
    print("✅ 왕복 검사 — 계약 7벌 모두 재직렬화가 원본과 바이트 동일하다")


def main():
    roundtrip_guard()
    log = []
    print("== 1. ConflictResponse — 이름을 가른다 ==")
    for name, new_name in RENAME.items():
        rename_conflict(name, new_name, log)

    print("== 2. ErrorItem — 한 형태로 ==")
    for name in (PRODUCTION, QUALITY, SHIPMENT):
        add_unique_scope(name, log)

    print("== 3. ErrorResponse·ErrorItem — 05설비툴을 여섯 벌 형태로 ==")
    fix_equipment_errors(log)

    print("== 4. LotHold — 상위집합 한 형태로 ==")
    unify_lothold(log)

    print("== 5. 05설비툴 저장 충돌 보호 신설 ==")
    add_equipment_locking(log)

    print()
    for line in log:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
