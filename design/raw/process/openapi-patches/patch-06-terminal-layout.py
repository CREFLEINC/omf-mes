#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""기준정보 계약에 단말·단말 기능 구성·창고 배치도를 더한다. 멱등.

왜 필요한가
-----------
`W-CO-06` 단말기-공정 매핑 설정과 `W-CO-08` 창고 적재 위치 배치도가 부를
경로가 없었다.

⭐ **실측 — 단말 경로가 0건이었다.** 기준정보 계약 79경로에 `terminal` 이
하나도 없다. `W-CO-06` 은 통째로 신설이다.

✅ **이미 있어서 안 만드는 것** — 창고·위치(`/mdm/warehouses`·`/mdm/locations`)는
실재하므로 `W-CO-08` 은 **배치도(도면 + 좌표)만** 더한다.

⛔ 왜 단말이 기준정보인가
-------------------------
「소유는 쓰기를 가진 쪽」이고 쓰는 화면이 `W-CO-06`(기준정보 성격의 마스터
관리)이다. 네임스페이스도 물리 스키마를 따라 `mdm` 이다(`mdm.terminal`).

⭐ 세 층이 갈려 있다 (2026-07-28 확정)
--------------------------------------
    인증       우리가 설치한 단말에서 온 요청인가   →  단말 토큰   ← 유일한 보안 경계
    기능 구성   이 단말에 이 기능을 열어 둘 것인가    →  8플래그
    귀속       누가 한 일로 기록할 것인가           →  사번

이 패치는 **첫째·둘째 층**을 만든다. 셋째 층(사번)은 작업자 조회
(`/mdm/workers`)가 이미 덮는다 — 세션을 만들지 않는다.

⭐ 토큰 주입 경로 = **B안**(2026-08-13 사용자 확정)
---------------------------------------------------
관리웹이 등록용 토큰을 발급해 화면에 QR 로 보이고, 기기가 그것을 스캔해
읽는다. **무인증 엔드포인트가 생기지 않는다** — 발급은 이미 인증된 관리웹이
부르고 기기는 읽기만 한다.

⛔ 채택하지 않은 안 — 1회용 코드를 기기에 입력해 서버가 토큰으로 바꿔 주는
방식(`:redeem-code`). 토큰 없이 서버를 부르는 경로가 하나 생기고 만료·재사용
통제가 따라온다.

쓰기
----
    python3 deliverables/openapi/patch-06-terminal-layout.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "mdm-기준정보.json")

I64 = {"type": "integer", "format": "int64", "example": 1001}
STR = {"type": "string"}
TS = {"type": "string", "format": "date-time", "example": "2026-08-13T09:12:00+09:00"}
TAG = ["mdm"]

FLAGS = [
    ("canScanIn", "입고 스캔"), ("canScanOut", "출고 스캔"),
    ("canRegisterResult", "실적 등록"), ("canInspect", "검사 입력"),
    ("canPrintLabel", "라벨 발행"), ("canMoveStock", "재고 이동"),
    ("canHold", "작업 중단 등록"), ("canApprove", "현장 승인"),
]


def ref(n: str) -> dict:
    return {"$ref": f"#/components/schemas/{n}"}


def err(*codes: str) -> dict:
    msg = {"400": "검증 실패. 고쳐야 풀린다", "403": "권한에 막혔다",
           "404": "없다", "409": "충돌"}
    out = {}
    for c in codes:
        s = ref("ConflictResponse") if c == "409" else ref("ErrorResponse")
        out[c] = {"description": msg[c], "content": {"application/json": {"schema": s}}}
    return out


def one(name: str, code: str = "200", desc: str = "상세") -> dict:
    return {code: {"description": desc,
                   "content": {"application/json": {"schema": ref(name)}}}}


def q(name: str, schema: dict, desc: str | None = None) -> dict:
    d = {"name": name, "in": "query", "schema": schema}
    if desc:
        d["description"] = desc
    return d


PAGE = [q("page", {"type": "integer", "default": 1}),
        q("size", {"type": "integer", "default": 50})]


def pathparam(name: str) -> dict:
    return {"name": name, "in": "path", "required": True, "schema": I64}


def idem() -> dict:
    return {"$ref": "#/components/parameters/IdempotencyKey"}


def ifmatch() -> dict:
    return {"$ref": "#/components/parameters/IfMatchVersion"}


def flag_props(with_desc: bool) -> dict:
    out = {}
    for key, label in FLAGS:
        d = {"type": "boolean", "example": False}
        if with_desc:
            d["description"] = f"{label}을 이 단말에서 할 수 있나. 기본은 닫힘이다"
        out[key] = d
    return out


SCHEMAS: dict = {
    "Terminal": {
        "x-source-table": "mdm.terminal",
        "type": "object",
        "required": ["terminalId", "terminalCode", "plantId", "terminalTypeCode",
                     "statusCode", "isActive"],
        "description": "설치된 단말 하나. 근거: W-CO-06 §4",
        "properties": {
            "terminalId": I64,
            "terminalCode": {"x-source-column": "terminal_code", **STR, "maxLength": 50,
                             "example": "POP-A-01",
                             "description": "설치 후에는 바꾸지 않는다 — 키다"},
            "plantId": I64,
            "locationId": {**I64, "description": "설치 위치. 비어 있을 수 있다"},
            "terminalTypeCode": {
                "x-source-column": "terminal_type_code", **STR, "x-no-example": True,
                "description": ("어떤 단말인가 — 고정 스테이션과 손에 드는 기기가 "
                                "여기서 갈린다. 값 목록은 아직 확정 전이다")},
            "statusCode": {"x-source-column": "status_code", **STR, "x-no-example": True},
            "isActive": {"type": "boolean", "example": True},
            "tokenIssuedAt": {**TS, "description": "마지막으로 토큰을 발급한 시각"},
            "versionNo": {"type": "integer", "example": 1}},
        "x-internal-note": (
            "토큰 세대(token_version)와 기기 식별자가 물리 모델에 없다 "
            "(W-CO-06 §5-4 · M-CO-01 §5-2). 그래서 잃어버린 기기를 영구히 끊을 수 "
            "없다 — 화면도 그 기능을 그리지 않는다(A-11). 공통 트랙 묶음 이슈로 요청."),
    },
    "TerminalCreate": {
        "type": "object",
        "required": ["terminalCode", "plantId", "terminalTypeCode", "statusCode"],
        "properties": {
            "terminalCode": {**STR, "maxLength": 50, "example": "POP-A-01"},
            "plantId": I64, "locationId": I64,
            "terminalTypeCode": {**STR, "x-no-example": True},
            "statusCode": {**STR, "x-no-example": True}},
    },
    "TerminalUpdate": {
        "type": "object", "required": ["plantId", "terminalTypeCode", "statusCode"],
        "description": "⛔ 단말 코드는 받지 않는다 — 키는 바꾸지 않는다(공유계약 B-4).",
        "properties": {
            "plantId": I64, "locationId": I64,
            "terminalTypeCode": {**STR, "x-no-example": True},
            "statusCode": {**STR, "x-no-example": True}},
    },
    "TerminalRegistrationToken": {
        "type": "object", "required": ["terminalId", "token", "issuedAt"],
        "description": (
            "기기에 넣을 등록용 토큰. ⭐ 관리웹이 이것을 받아 «QR 로 그려» 보이고 "
            "기기가 스캔해 읽는다 — 기기는 서버를 부르지 않는다. "
            "그래서 토큰 없이 열리는 경로가 생기지 않는다. 근거: M-CO-01 §5-2 B안"),
        "properties": {
            "terminalId": I64,
            "token": {**STR, "x-no-example": "실제 토큰 모양을 공개 계약에 남기지 않는다",
                      "description": "기기가 저장한다. 관리웹은 화면에 QR 로만 보인다"},
            "issuedAt": TS,
            "expiresAt": {**TS, "description": "만료 1년"}},
        "x-internal-note": (
            "⛔ 재발급해도 이전 기기가 끊기지 않는다 — token_version 이 없어 "
            "세대를 올릴 수 없다. 화면이 「이전 기기를 끊는다」를 «그리지 않는» 이유다 "
            "(A-11 — 할 수 없는 것을 할 수 있는 것처럼 그리지 않는다)."),
    },
    "TerminalProcess": {
        "x-source-table": "mdm.terminal_process",
        "type": "object", "required": ["processId"],
        "description": (
            "이 단말에서 이 공정의 무엇을 열어 둘 것인가. ⭐ 이것은 «인증이 아니라 "
            "기능 구성»이다 — 오조작을 막는 것이지 보안 경계가 아니다. "
            "보안 경계는 단말 토큰 하나뿐이다. 근거: P-CO-01 §5-1"),
        "properties": {"processId": I64, "processName": {**STR, "example": "사출"},
                       **flag_props(True)},
    },
    "TerminalProcessReplace": {
        "type": "object", "required": ["items"],
        "description": (
            "단말 하나의 공정 구성을 통째로 바꾼다 — 화면의 저장이 단말 단위 한 "
            "트랜잭션이기 때문이다. 빠진 공정은 지워진다. 근거: W-CO-06 §5-3"),
        "properties": {"items": {"type": "array", "items": ref("TerminalProcessLine")}},
    },
    "TerminalProcessLine": {
        "type": "object", "required": ["processId"],
        "properties": {"processId": I64, **flag_props(False)},
    },
    "WarehouseLayout": {
        "type": "object", "required": ["warehouseId", "markers"],
        "description": (
            "창고 도면 한 장과 그 위에 찍은 위치 점들. 근거: W-CO-08 §5"),
        "properties": {
            "warehouseId": I64,
            "drawingAttachmentId": {
                **I64,
                "description": ("도면 이미지. 첨부의 다형 참조를 그대로 쓴다 — "
                                "대상 유형은 창고다. 비어 있으면 화면이 「도면을 "
                                "올리세요」를 보인다")},
            "markers": {"type": "array", "items": ref("WarehouseLayoutMarker")},
            "versionNo": {"type": "integer", "example": 1}},
    },
    "WarehouseLayoutMarker": {
        "type": "object", "required": ["locationId", "x", "y"],
        "description": (
            "위치 하나가 도면 어디에 있나. ⭐ 좌표는 도면 «비율»이다 — 0 과 1 사이. "
            "픽셀로 두면 도면을 바꿀 때 점이 전부 어긋난다"),
        "properties": {
            "locationId": I64,
            "x": {"type": "number", "minimum": 0, "maximum": 1, "example": 0.42},
            "y": {"type": "number", "minimum": 0, "maximum": 1, "example": 0.18}},
    },
    "WarehouseLayoutReplace": {
        "type": "object", "required": ["markers"],
        "description": "도면과 점을 통째로 바꾼다 — 화면의 저장이 그 단위다.",
        "properties": {
            "drawingAttachmentId": I64,
            "markers": {"type": "array", "items": ref("WarehouseLayoutMarker")}},
    },
}


def paths_to_add() -> dict:
    return {
        "/mdm/terminals": {
            "get": {"tags": TAG, "summary": "단말 목록",
                    "description": "근거: W-CO-06 §5",
                    "parameters": [q("plantId", I64),
                                   q("terminalTypeCode", {**STR, "x-no-example": True}),
                                   q("includeInactive", {"type": "boolean"}),
                                   q("q", STR, "단말 코드 검색")] + PAGE,
                    "responses": {"200": {"description": "목록", "content": {
                        "application/json": {"schema": {
                            "type": "object", "required": ["items", "page"], "properties": {
                                "items": {"type": "array", "items": ref("Terminal")},
                                "page": ref("PageMeta")}}}}}}},
            "post": {"tags": TAG, "summary": "단말 등록",
                     "description": "근거: W-CO-06 §5",
                     "parameters": [idem()],
                     "requestBody": {"required": True, "content": {"application/json": {
                         "schema": ref("TerminalCreate")}}},
                     "responses": {**one("Terminal", "201", "등록됨"),
                                   **err("400", "403", "409")}}},
        "/mdm/terminals/{terminalId}": {
            "get": {"tags": TAG, "summary": "단말 한 건",
                    "parameters": [pathparam("terminalId")],
                    "responses": {**one("Terminal"), **err("404")}},
            "put": {"tags": TAG, "summary": "단말 수정",
                    "description": "⛔ 단말 코드는 못 바꾼다 — 키다. 근거: W-CO-06 §5 · B-4",
                    "parameters": [pathparam("terminalId"), idem(), ifmatch()],
                    "requestBody": {"required": True, "content": {"application/json": {
                        "schema": ref("TerminalUpdate")}}},
                    "responses": {**one("Terminal", "200", "수정됨"),
                                  **err("400", "403", "404", "409")}}},
        "/mdm/terminals/{terminalId}:deactivate": {"post": {
            "tags": TAG, "summary": "단말 사용 중지",
            "description": (
                "지우지 않고 끈다 — 그 단말이 남긴 기록이 참조로 남아 있다. "
                "근거: W-CO-06 §5·§6"),
            "parameters": [pathparam("terminalId"), idem(), ifmatch()],
            "responses": {**one("Terminal", "200", "중지됨"), **err("403", "404", "409")}}},
        "/mdm/terminals/{terminalId}:issue-token": {"post": {
            "tags": TAG, "summary": "단말 등록 토큰 발급",
            "description": (
                "⭐ 관리웹이 부르고, 받은 토큰을 화면에 «QR 로» 보인다. 기기는 그것을 "
                "스캔해 저장한다 — 기기가 서버를 부르지 않으므로 토큰 없이 열리는 경로가 "
                "생기지 않는다. ⚠ 재발급해도 «이전 기기가 끊기지 않는다» — 세대를 올릴 "
                "자리가 아직 없다. 화면이 그 사실을 경고한다. "
                "근거: M-CO-01 §5-2 B안(2026-08-13 확정) · W-CO-06 §5-4"),
            "parameters": [pathparam("terminalId"), idem()],
            "responses": {**one("TerminalRegistrationToken", "201", "발급됨"),
                          **err("403", "404")}}},
        "/mdm/terminals/{terminalId}/processes": {
            "get": {"tags": TAG, "summary": "단말 기능 구성 조회",
                    "description": (
                        "이 단말에서 어떤 공정의 무엇이 열려 있나. POP 셸이 화면을 "
                        "그리기 전에 읽는다. 근거: W-CO-06 §5 · P-CO-01 §5-1"),
                    "parameters": [pathparam("terminalId")],
                    "responses": {"200": {"description": "목록", "content": {
                        "application/json": {"schema": {
                            "type": "object", "required": ["items"], "properties": {
                                "items": {"type": "array",
                                          "items": ref("TerminalProcess")}}}}}},
                        **err("404")}},
            "put": {"tags": TAG, "summary": "단말 기능 구성 저장",
                    "description": (
                        "단말 하나의 공정 구성을 통째로 바꾼다 — 화면의 저장이 단말 단위 "
                        "한 트랜잭션이다. 빠진 공정은 지워진다. 근거: W-CO-06 §5-3"),
                    "parameters": [pathparam("terminalId"), idem(), ifmatch()],
                    "requestBody": {"required": True, "content": {"application/json": {
                        "schema": ref("TerminalProcessReplace")}}},
                    "responses": {"200": {"description": "저장됨", "content": {
                        "application/json": {"schema": {
                            "type": "object", "required": ["items"], "properties": {
                                "items": {"type": "array",
                                          "items": ref("TerminalProcess")}}}}}},
                        **err("400", "403", "404", "409")},
                    "x-internal-note": (
                        "mdm.terminal_process 에 version_no 가 없다(W-CO-06 §2 실측). "
                        "낙관적 잠금 토큰은 단말 쪽 version_no 로 받는다 — 저장 단위가 "
                        "단말이기 때문이다. 공통 트랙 묶음 이슈에 함께 올린다.")}},
        "/mdm/warehouses/{warehouseId}/layout": {
            "get": {"tags": TAG, "summary": "창고 배치도 조회",
                    "description": (
                        "도면 한 장과 위치 점들. 도면이 없으면 점만 온다. "
                        "근거: W-CO-08 §5"),
                    "parameters": [pathparam("warehouseId")],
                    "responses": {**one("WarehouseLayout"), **err("404")}},
            "put": {"tags": TAG, "summary": "창고 배치도 저장",
                    "description": (
                        "도면과 점을 통째로 바꾼다 — 화면의 저장이 그 단위다. "
                        "⚠ 도면을 갈면 점이 그대로 남는다: 좌표가 비율이라 새 도면에서도 "
                        "같은 상대 위치를 가리킨다. 그래도 사람이 다시 봐야 하므로 "
                        "화면이 교체 전에 확인을 받는다. 근거: W-CO-08 §5·§7"),
                    "parameters": [pathparam("warehouseId"), idem(), ifmatch()],
                    "requestBody": {"required": True, "content": {"application/json": {
                        "schema": ref("WarehouseLayoutReplace")}}},
                    "responses": {**one("WarehouseLayout", "200", "저장됨"),
                                  **err("400", "403", "404", "409")}}},
    }


def detect_indent(original: str, doc: dict) -> int | None:
    """원본이 어떤 들여쓰기로 쓰였는지 되짚는다. 못 알아내면 None 이다."""
    body = original.rstrip("\n")
    for candidate in (1, 2, 4):
        if json.dumps(doc, ensure_ascii=False, indent=candidate) == body:
            return candidate
    return None


def main() -> int:
    original = open(CONTRACT, encoding="utf-8").read()
    doc = json.loads(original)

    indent = detect_indent(original, doc)
    if indent is None:
        print("⛔ 원본 들여쓰기를 알아낼 수 없다 — 덮어쓰지 않는다", file=sys.stderr)
        return 1
    tail = original[len(original.rstrip("\n")):]

    for dep in ("ErrorResponse", "ConflictResponse", "PageMeta"):
        if dep not in doc["components"]["schemas"]:
            print(f"⛔ 의존 스키마가 없다: {dep}", file=sys.stderr)
            return 1
    for dep in ("IdempotencyKey", "IfMatchVersion"):
        if dep not in doc["components"]["parameters"]:
            print(f"⛔ 의존 파라미터가 없다: {dep}", file=sys.stderr)
            return 1

    was_sorted_paths = list(doc["paths"]) == sorted(doc["paths"])
    was_sorted_schemas = (list(doc["components"]["schemas"])
                          == sorted(doc["components"]["schemas"]))

    doc["components"]["schemas"].update(SCHEMAS)
    doc["paths"].update(paths_to_add())

    # ⛔ 원본이 정렬돼 있던 경우에만 다시 정렬한다. 안 그러면 경로를 더한
    #    변경이 파일 전체를 다시 쓴 것으로 나온다.
    if was_sorted_paths:
        doc["paths"] = dict(sorted(doc["paths"].items()))
    if was_sorted_schemas:
        doc["components"]["schemas"] = dict(sorted(doc["components"]["schemas"].items()))

    updated = json.dumps(doc, ensure_ascii=False, indent=indent) + tail
    if updated == original:
        print("  이미 반영돼 있다 — 변경 없음")
        return 0

    open(CONTRACT, "w", encoding="utf-8").write(updated)
    print(f"  ✅ 단말·기능 구성·배치도 — 경로 {len(doc['paths'])} · 스키마 "
          f"{len(doc['components']['schemas'])}")
    print("     ⭐ 토큰 주입은 B안(등록 QR) — 2026-08-13 사용자 확정")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
