#!/usr/bin/env python3
"""06 계약에 거래처 역할을 붙인다 — 멱등.

왜 필요한가
-----------
폐기 출고가 **폐기 거래처**를 기록하게 됐다(DR-013 확정 2026-08-13). 그러려면
「이 거래처가 폐기처리를 한다」를 어딘가에서 말해야 하는데, 06 계약은
`GET /mdm/partners` 하나뿐이고 역할을 다루지 않았다.

⭐ **테이블은 이미 있었다** — `mdm.partner_role(partner_id, role_type_code)`,
UNIQUE 짝. 한 거래처가 여러 역할을 갖는 N:M 구조다. 스펙·계약이 이 테이블을
한 번도 쓰지 않아 아무도 보지 못했다.

소유 경계 (DR-013 Q2)
---------------------
  ERP  →  거래처 본체(코드·명·국가·ERP 코드)   수신 · MES 는 읽기만
  MES  →  거래처 역할(partner_role)            ⭐ MES 가 편집한다

⭐ `W-06-06` 「작업자」 탭이 같은 선례다 — 「ERP 수신 후 확장 속성만」.
거래처 역할을 네 번째 탭으로 얹는다(화면 신설 0).

무엇을 넣나
-----------
  GET    /mdm/partners                      역할 필터 추가(roleTypeCode)
  GET    /mdm/partners/{partnerId}/roles    이 거래처의 역할
  PUT    /mdm/partners/{partnerId}/roles    역할 목록 통째 교체

⭐ PUT 으로 통째 교체하는 이유 — 역할은 **집합**이다. 개별 추가·삭제로 두면
화면이 두 번 부르고 중간 상태가 생긴다. `uq_partner_role` 이 (거래처, 역할)
유일이라 집합 교체가 자연스럽다. 수정은 PUT 이라는 URL 규약과도 맞는다.

⚠ `roleTypeCode` 값 목록은 미확정이다 — omf-mes#145(공통코드 값 목록).
G-2 대로 enum 을 못박지 않는다.

바이트 보존
-----------
이 파일은 indent=2 · 끝줄 있음으로 직렬화돼 있다. 같은 형식으로 다시 쓰고
**정렬하지 않는다** — 원본이 정렬돼 있지 않아 재정렬하면 파일 전체가 바뀐다.
"""
from __future__ import annotations

import json
import sys

CONTRACT = "deliverables/openapi/mdm-기준정보.json"

ROLE_SCHEMA = {
    "type": "object",
    "required": ["roleTypeCode"],
    "properties": {
        "roleTypeCode": {
            "x-source-column": "role_type_code",
            "type": "string",
            "maxLength": 50,
            "description": (
                "거래처 역할. 공급사 · 고객 · 외주처 · 폐기처리 등. "
                "한 거래처가 여러 역할을 가질 수 있다."
            ),
            "x-no-example": "값 목록 미확정 — 공통코드 값 목록(omf-mes#145) 대상",
        },
        "roleTypeName": {
            "type": ["string", "null"],
            "maxLength": 200,
            "description": "역할 표시명. 화면이 그대로 보인다",
            "example": "폐기처리",
        },
    },
    "description": (
        "거래처 역할. ⭐ 거래처 본체는 ERP 수신 마스터이고 역할은 MES 가 관리한다 — "
        "ERP 가 주지 않는 구분을 MES 가 덧붙이는 형태다(W-06-06 「작업자」 탭과 같은 원리)."
    ),
    "x-source-table": "mdm.partner_role",
}

ROLES_REPLACE = {
    "type": "object",
    "required": ["roleTypeCodes"],
    "properties": {
        "roleTypeCodes": {
            "type": "array",
            "items": {"type": "string", "maxLength": 50},
            "description": (
                "이 거래처가 갖는 역할 전부. ⭐ 통째로 교체한다 — 목록에 없는 역할은 "
                "해제된다. 역할은 집합이라 개별 추가·삭제로 두면 화면이 두 번 부르고 "
                "중간 상태가 생긴다."
            ),
            "example": ["SUPPLIER", "DISPOSAL"],
        }
    },
    "description": "거래처 역할 통째 교체. 빈 배열이면 역할을 모두 해제한다.",
}


def relax_partner_list(paths: dict) -> int:
    """GET /mdm/partners 에 역할 필터를 더한다."""
    op = paths.get("/mdm/partners", {}).get("get")
    if op is None:
        return 0
    params = op.setdefault("parameters", [])
    if any(p.get("name") == "roleTypeCode" for p in params):
        return 0
    # q 바로 뒤에 끼운다 — 검색 조건끼리 붙여 읽히게
    at = next((i for i, p in enumerate(params) if p.get("name") == "q"), -1) + 1
    params.insert(at, {
        "name": "roleTypeCode",
        "in": "query",
        "required": False,
        "schema": {"type": "string", "maxLength": 50},
        "description": (
            "역할로 거른다. ⭐ 폐기 출고 화면이 폐기처리 거래처만 고를 때 쓴다"
            "(W-01-06 · W-04-10 · DR-013)."
        ),
    })
    return 1


def add_role_paths(paths: dict) -> int:
    """거래처 역할 읽기·교체 경로를 더한다. 이미 있으면 0."""
    key = "/mdm/partners/{partnerId}/roles"
    if key in paths:
        return 0
    paths[key] = {
        "parameters": [{
            "name": "partnerId", "in": "path", "required": True,
            "schema": {"type": "integer", "format": "int64"},
        }],
        "get": {
            "tags": ["mdm"],
            "summary": "거래처 역할 목록",
            "description": (
                "이 거래처가 갖는 역할 전부. W-06-06 「거래처 역할」 탭이 읽는다. "
                "근거: DR-013 확정 Q2"
            ),
            "responses": {
                "200": {
                    "description": "목록",
                    "content": {"application/json": {"schema": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/PartnerRole"},
                    }}},
                },
                "404": {"description": "없다"},
            },
        },
        "put": {
            "tags": ["mdm"],
            "summary": "거래처 역할 교체",
            "description": (
                "W-06-06 「거래처 역할」 탭의 저장. ⭐ 목록을 통째로 교체한다 — "
                "역할은 집합이고 (거래처, 역할)이 유일하다. "
                "⛔ 거래처 본체는 고치지 않는다 — ERP 수신 마스터라 MES 는 읽기만 한다."
            ),
            "parameters": [
                {"$ref": "#/components/parameters/IdempotencyKey"},
            ],
            "requestBody": {"required": True, "content": {"application/json": {
                "schema": {"$ref": "#/components/schemas/PartnerRolesReplace"},
            }}},
            "responses": {
                "200": {
                    "description": "교체됨",
                    "content": {"application/json": {"schema": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/PartnerRole"},
                    }}},
                },
                "400": {"description": "검증 실패. 고쳐야 풀린다"},
                "403": {"description": "권한·단말 게이팅에 막혔다"},
                "404": {"description": "없다"},
            },
            "x-internal-note": (
                "역할 값 목록이 미확정이라 서버가 알 수 없는 코드를 400 으로 막는지는 "
                "값이 정해진 뒤에 정한다(omf-mes#145). "
                "⛔ 거래처 본체 CRUD 는 두지 않는다 — 06 화면 12개에 거래처 마스터가 "
                "0건이고 거래처는 ERP 수신 마스터다(🔹2026-07-08 확정)."
            ),
        },
    }
    return 1


def main() -> int:
    """06 계약을 읽어 거래처 역할을 붙이고, 바뀐 것이 있을 때만 다시 쓴다."""
    original = open(CONTRACT, encoding="utf-8").read()
    doc = json.loads(original)
    paths, schemas = doc["paths"], doc["components"]["schemas"]

    n = relax_partner_list(paths)
    n += add_role_paths(paths)
    for name, body in (("PartnerRole", ROLE_SCHEMA),
                       ("PartnerRolesReplace", ROLES_REPLACE)):
        if name not in schemas:
            schemas[name] = body
            n += 1

    # ⛔ 여기서 정렬하지 않는다 — 원본이 정렬돼 있지 않아 재정렬하면 파일
    #    전체가 churn 된다(patch-01-missing-ops.py 가 12,320 → 12,773 줄로
    #    부풀린 전례). 새 키는 끝에 붙고, 손대지 않은 곳은 그대로 남는다.

    updated = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if updated == original:
        print("  이미 반영돼 있다 — 변경 없음")
        return 0
    open(CONTRACT, "w", encoding="utf-8").write(updated)
    ops = sum(1 for p in doc["paths"].values() for m in p
              if m in ("get", "post", "put", "patch", "delete"))
    print(f"  ✅ 거래처 역할 추가 ({n}건) — 경로 {len(doc['paths'])} · "
          f"오퍼 {ops} · 스키마 {len(schemas)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
