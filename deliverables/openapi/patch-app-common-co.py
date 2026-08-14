#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""공통 계약에 인증·알림·공지·집계를 더한다 — 공통 10화면 트랙. 멱등.

왜 필요한가
-----------
착수 통지 **79장**이 나갔는데 클라이언트에 `auth`·`login`·`session` 파일이
**0건**이다(실측). 그중 31장(POP 17 · 모바일 14)은 셸조차 없다.
**이미 내보낸 통지가 돌아갈 최소 조건**이 빠져 있었다.

무엇을 더하나 — 리소스 6
------------------------
    세션                POST/GET/DELETE /app/sessions …
    내 계정             POST /app/users/me:change-password
    알림                GET /app/notifications · :read · :read-all
    알림 수신자 설정      GET/PUT /app/notification-subscriptions
    공지                /app/notices + :publish · :close · :acknowledge
    대시보드 집계         GET /app/dashboard-summary

⭐ 방향 — 모델이 계약을 따라온다
--------------------------------
비밀번호 3컬럼 · 알림 표 · 수신자 설정 표 · 공지 표 · 알림 수신처가 물리
모델에 **없다**. 그것을 이유로 계약을 물리지 않는다(2026-08-10 확정).
모델 요청은 일곱을 묶어 한 이슈로 낸다.

쓰기
----
    python3 deliverables/openapi/patch-app-common-co.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.join(HERE, "app-공통.json")

I64 = {"type": "integer", "format": "int64", "example": 1001}
STR = {"type": "string"}
TS = {"type": "string", "format": "date-time", "example": "2026-08-13T09:12:00+09:00"}
DT = {"type": "string", "format": "date", "example": "2026-08-13"}
TAG = ["app"]


def ref(n: str) -> dict:
    return {"$ref": f"#/components/schemas/{n}"}


def err(*codes: str) -> dict:
    msg = {"400": "검증 실패. 고쳐야 풀린다", "401": "아이디 또는 비밀번호가 맞지 않는다",
           "403": "권한·단말 게이팅에 막혔다", "404": "없다", "409": "충돌",
           "423": "실패가 쌓여 잠겼다 — 스스로 풀 수 없다"}
    out = {}
    for c in codes:
        s = ref("ConflictResponse") if c == "409" else ref("ErrorResponse")
        out[c] = {"description": msg[c], "content": {"application/json": {"schema": s}}}
    return out


def one(name: str, code: str = "200", desc: str = "상세") -> dict:
    return {code: {"description": desc,
                   "content": {"application/json": {"schema": ref(name)}}}}


def listed(name: str, desc: str = "목록") -> dict:
    return {"200": {"description": desc, "content": {"application/json": {"schema": {
        "type": "object", "required": ["items", "page"],
        "properties": {"items": {"type": "array", "items": ref(name)},
                       "page": ref("PageMeta")}}}}}}


def q(name: str, schema: dict, desc: str | None = None, required: bool = False) -> dict:
    d = {"name": name, "in": "query", "schema": schema}
    if desc:
        d["description"] = desc
    if required:
        d["required"] = True
    return d


PAGE = [q("page", {"type": "integer", "default": 1}),
        q("size", {"type": "integer", "default": 50})]


def pathparam(name: str) -> dict:
    return {"name": name, "in": "path", "required": True, "schema": I64}


def idem() -> dict:
    return {"$ref": "#/components/parameters/IdempotencyKey"}


# ── 스키마 ────────────────────────────────────────────────────────────
SCHEMAS: dict = {
    "LoginRequest": {
        "type": "object", "required": ["loginId", "password"],
        "description": "근거: W-CO-01 §5-A",
        "properties": {
            "loginId": {**STR, "maxLength": 100, "example": "hong.gd"},
            "password": {**STR, "format": "password", "writeOnly": True,
                         "x-no-example": "예시를 두면 공개 계약에 그럴듯한 비밀번호가 박힌다",
                         "description": "평문은 저장하지도 기록하지도 않는다"}},
        "x-internal-note": (
            "app.app_user 에 password_hash·failed_login_count·last_login_at 이 "
            "셋 다 없다(W-CO-01 §5-B 가 [신설] 로 표시). 계약이 앞서 있고 "
            "모델 요청은 공통 트랙 묶음 이슈로 나간다."),
    },
    "LoginFailure": {
        "type": "object", "required": ["message"],
        "description": (
            "⛔ 아이디가 틀렸는지 비밀번호가 틀렸는지 말하지 않는다 — 계정이 있는지가 "
            "새어 나간다. 근거: W-CO-01 §5-1"),
        "properties": {
            "message": {**STR, "example": "아이디 또는 비밀번호가 맞지 않습니다"},
            "remainingAttempts": {
                "type": "integer", "example": 3,
                "description": (
                    "남은 시도 횟수. 잠긴 뒤에야 알리지 않는다. "
                    "⚠ 없는 계정에는 오지 않는다 — 그래서 계정 존재가 드러나지만 "
                    "「잠길 줄 모르는 것」보다 낫다고 판단했다")}},
    },
    "Session": {
        "type": "object", "required": ["userId", "loginId", "userName", "scopes"],
        "description": "로그인 결과이자 「지금 나는 누구이고 어디까지 보는가」.",
        "properties": {
            "userId": I64, "loginId": {**STR, "example": "hong.gd"},
            "userName": {**STR, "example": "홍길동"},
            "departmentId": I64,
            "lastLoginAt": {**TS, "description": "이번 로그인 «직전» 시각"},
            "scopes": {
                "type": "array", "items": ref("SessionScope"),
                "description": "권한 범위는 사업부·공장 두 축이다. 근거: W-CO-01 §5-3"},
            "roles": {"type": "array", "items": STR}},
    },
    "SessionScope": {
        "type": "object", "required": ["businessUnitId"],
        "properties": {"businessUnitId": I64, "plantId": I64},
    },
    "PasswordChangeRequest": {
        "type": "object", "required": ["currentPassword", "newPassword"],
        "description": (
            "현재 비밀번호를 틀려도 계정을 잠그지 않는다 — 이미 인증된 본인이다. "
            "바꾼 뒤 다시 로그인시키지도 않는다. 근거: W-CO-10 §5-2·§5-3"),
        "properties": {
            "currentPassword": {**STR, "format": "password", "writeOnly": True,
                                "x-no-example": "비밀번호에 예시를 두지 않는다"},
            "newPassword": {**STR, "format": "password", "writeOnly": True,
                            "minLength": 8,
                            "x-no-example": "비밀번호에 예시를 두지 않는다",
                            "description": "최소 길이만 둔다 — 조합 규칙은 두지 않는다"}},
    },
    "Notification": {
        "type": "object",
        "required": ["notificationId", "eventCode", "message", "occurredAt", "read"],
        "properties": {
            "notificationId": I64,
            "eventCode": {**STR, "x-no-example": True,
                          "description": "무슨 일이 일어났나. 목록은 이벤트 조회 경로가 준다"},
            "message": {**STR, "example": "출하검사에서 불합격이 나왔습니다"},
            "occurredAt": TS,
            "read": {"type": "boolean", "example": False},
            "targetTypeCode": {
                **STR, "x-no-example": True,
                "description": (
                    "무엇에 대한 알림인가. LOT → trace.lot · WORK_ORDER → "
                    "production.work_order · NONCONFORMANCE → quality.nonconformance · "
                    "APPROVAL_REQUEST → app.approval_request. ⚠ 대응표에 없는 유형은 "
                    "화면이 「대상으로 이동」을 열지 않는다 — 어디로 갈지 모른다")},
            "targetId": I64},
        "x-internal-note": (
            "알림 표가 물리 모델에 없다(W-CO-03 §2 검색 0건). 개념모델 §6.5 "
            "「알림」이 하류에 착지하지 않았다. 저장된 문장은 «발송 시점 언어»다 — "
            "한/베 사용자가 같은 알림을 보는 경우는 W-CO-11 에서 수신자 언어를 "
            "볼 수 있는지 확인한 뒤 정한다(W-CO-03 §8-2)."),
    },
    "NotificationEvent": {
        "type": "object", "required": ["eventCode", "eventName"],
        "description": (
            "알림 이벤트 목록. ⭐ 이 목록의 정본은 계약이다 — 공통코드 마스터에 두면 "
            "편집 가능해지는데, 코드가 바뀌면 보내는 쪽이 깨진다. 근거: W-CO-03 §8-3"),
        "properties": {
            "eventCode": {**STR, "x-no-example": True},
            "eventName": {**STR, "example": "출하검사 불합격"},
            "description": {**STR, "example": "출하검사에서 불합격 판정이 저장됐을 때"}},
    },
    "NotificationSubscription": {
        "type": "object", "required": ["eventCode", "recipients"],
        "description": "이벤트 하나의 수신자 전체. 근거: W-CO-11 §5-A",
        "properties": {
            "eventCode": {**STR, "x-no-example": True},
            "recipients": {"type": "array", "items": ref("NotificationRecipient")},
            "zaloEnabled": {
                "type": "boolean", "example": False,
                "description": (
                    "⚠ 켜도 보낼 곳이 아직 없다 — 수신처(전화번호)를 담을 자리가 "
                    "사용자 정보에 없다. 화면이 그 사실을 보인다")}},
    },
    "NotificationRecipient": {
        "type": "object", "required": ["recipientTypeCode"],
        "description": (
            "조직×역할로 묶어 지정하거나 사람을 하나씩 지정한다. 근거: W-CO-11 §5"),
        "properties": {
            "recipientTypeCode": {
                **STR, "x-no-example": True,
                "description": ("어떻게 지정했나. ROLE → 조직×역할 묶음 "
                                "(businessUnitId + roleId) · USER → 사람 하나 (userId)")},
            "businessUnitId": I64, "roleId": I64, "userId": I64},
    },
    "NotificationSubscriptionReplace": {
        "type": "object", "required": ["recipients"],
        "description": "이벤트 하나의 수신자를 통째로 바꾼다 — 화면의 저장이 그 단위다.",
        "properties": {
            "recipients": {"type": "array", "items": ref("NotificationRecipient")},
            "zaloEnabled": {"type": "boolean", "example": False}},
    },
    "Notice": {
        "type": "object",
        "required": ["noticeId", "title", "statusCode", "startDate"],
        "properties": {
            "noticeId": I64,
            "title": {**STR, "maxLength": 200, "example": "8월 정기 보전 안내"},
            "body": {**STR, "example": "8월 20일 09:00~12:00 사이 2호기 정기 보전이 있습니다."},
            "statusCode": {**STR, "x-no-example": True,
                           "description": "작성 중 · 게시 중 · 종료"},
            "startDate": DT, "endDate": DT,
            "acknowledgeRequired": {
                "type": "boolean", "example": True,
                "description": "참이면 읽은 사람이 확인을 눌러야 한다"},
            "acknowledgedCount": {"type": "integer", "example": 12},
            "targetCount": {"type": "integer", "example": 30},
            "publishedAt": TS, "createdBy": I64, "versionNo": {"type": "integer", "example": 1}},
        "x-internal-note": (
            "공지 표가 물리 모델에 없다(W-CO-04 §2 — notice·announce·bulletin 검색 0건). "
            "첨부는 app.attachment 의 다형 참조를 그대로 쓴다."),
    },
    "NoticeCreate": {
        "type": "object", "required": ["title", "body", "startDate"],
        "properties": {
            "title": {**STR, "maxLength": 200, "example": "8월 정기 보전 안내"},
            "body": {**STR, "example": "8월 20일 09:00~12:00 사이 2호기 정기 보전이 있습니다."},
            "startDate": DT, "endDate": DT,
            "acknowledgeRequired": {"type": "boolean", "example": True}},
    },
    "NoticeAcknowledgement": {
        "type": "object", "required": ["userId", "userName", "acknowledged"],
        "description": "누가 확인했고 누가 아직 안 했나. 근거: W-CO-04 「미확인자 보기」",
        "properties": {
            "userId": I64, "userName": {**STR, "example": "홍길동"},
            "acknowledged": {"type": "boolean", "example": False},
            "acknowledgedAt": TS},
    },
    "DashboardSummary": {
        "type": "object", "required": ["baseDate", "cards"],
        "description": (
            "경영·생산 한눈 보기. ⭐ 카드마다 소유 화면이 따로 있고 이 경로는 "
            "«숫자만» 모은다 — 클릭하면 그 화면으로 넘어간다. 근거: W-CO-05 §5"),
        "properties": {
            "baseDate": DT,
            "plantId": I64,
            "cards": {"type": "array", "items": ref("DashboardCard")},
            "alerts": {"type": "array", "items": ref("Notification"),
                       "description": "최근 알람 — 클릭하면 알림센터로 간다"}},
        "x-internal-note": (
            "⛔ 설비종합효율(OEE)을 내지 않는다. 계획 조업 시간의 분모가 되는 "
            "휴일·계획 정지를 담을 자리가 물리 모델에 없다(W-CO-05 §8-1). "
            "정책 코드 ALLOW_PRODUCTION_ON_HOLIDAYS 는 시드에 있는데 어느 날이 "
            "휴일인지가 없다 — omf-mes#67 코멘트에 올라가 있다. "
            "화면은 교대 기준으로 그리고 주석을 단다 — 자리가 생기면 주석만 뗀다."),
    },
    "DashboardCard": {
        "type": "object", "required": ["cardCode", "label", "value"],
        "properties": {
            "cardCode": {**STR, "x-no-example": True,
                         "description": "어느 지표인가. 화면이 이 코드로 드릴다운 대상을 안다"},
            "label": {**STR, "example": "오늘 생산 수량"},
            "value": {"type": "number", "example": 1240.0},
            "unit": {**STR, "example": "EA"},
            "deltaRatio": {"type": "number", "example": 0.08,
                           "description": "직전 기준일 대비. 비교 대상이 없으면 비운다"}},
    },
}


def paths_to_add() -> dict:
    return {
        "/app/sessions": {"post": {
            "tags": TAG, "summary": "로그인",
            "description": (
                "⛔ 실패해도 아이디와 비밀번호 중 무엇이 틀렸는지 말하지 않는다 — "
                "계정이 있는지가 새어 나간다. 남은 시도 횟수는 알린다(잠긴 뒤에야 "
                "알리지 않기 위해서다). 잠긴 계정은 스스로 풀 수 없다 — 관리자가 푼다. "
                "근거: W-CO-01 §5-1·§5-2"),
            "parameters": [idem()],
            "requestBody": {"required": True, "content": {"application/json": {
                "schema": ref("LoginRequest")}}},
            "responses": {
                **one("Session", "200", "로그인됨"),
                "401": {"description": "아이디 또는 비밀번호가 맞지 않는다",
                        "content": {"application/json": {"schema": ref("LoginFailure")}}},
                **err("400", "423")}}},
        "/app/sessions/current": {
            "get": {"tags": TAG, "summary": "현재 세션",
                    "description": "지금 나는 누구이고 어디까지 보는가. 근거: W-CO-01 §5-3",
                    "responses": {**one("Session"), **err("401")}},
            "delete": {"tags": TAG, "summary": "로그아웃", "parameters": [idem()],
                       "responses": {"204": {"description": "끝났다"}, **err("401")}}},
        "/app/users/me:change-password": {"post": {
            "tags": TAG, "summary": "내 비밀번호 변경",
            "description": (
                "⛔ 현재 비밀번호를 틀려도 계정을 잠그지 않는다 — 로그인과 달리 "
                "이미 인증된 본인이기 때문이다. ⛔ 바꾼 뒤 다시 로그인시키지 않는다 — "
                "작업 중일 수 있다. 근거: W-CO-10 §5-2·§5-3"),
            "parameters": [idem()],
            "requestBody": {"required": True, "content": {"application/json": {
                "schema": ref("PasswordChangeRequest")}}},
            "responses": {"204": {"description": "바뀌었다"}, **err("400", "401")}}},
        "/app/notifications": {"get": {
            "tags": TAG, "summary": "알림 목록",
            "description": (
                "기간을 반드시 받는다 — 알림은 계속 쌓이므로 범위 없이 열면 목록이 "
                "끝나지 않는다(공유계약 L-3). 근거: W-CO-03 §5"),
            "parameters": [
                q("unreadOnly", {"type": "boolean"}, "참이면 안 읽은 것만"),
                q("eventCode", {**STR, "x-no-example": True}),
                q("occurredFrom", TS, "기간 시작", required=True),
                q("occurredTo", TS, "기간 종료", required=True)] + PAGE,
            "responses": listed("Notification")}},
        "/app/notifications/unread-count": {"get": {
            "tags": TAG, "summary": "안 읽은 알림 수",
            "description": (
                "셸의 종 배지가 쓴다. ⚠ 조회 화면의 「자동 갱신을 두지 않는다」 규약은 "
                "여기 걸리지 않는다 — 셸 배지는 다르다. 화면이 바뀔 때 다시 부른다. "
                "근거: W-CO-03 §8-4"),
            "responses": {"200": {"description": "개수", "content": {"application/json": {
                "schema": {"type": "object", "required": ["unreadCount"],
                           "properties": {"unreadCount": {"type": "integer", "example": 3}}}}}},
                **err("401")}}},
        "/app/notifications/{notificationId}:read": {"post": {
            "tags": TAG, "summary": "알림 읽음 처리",
            "description": "목록에서 항목을 열면 자동으로 부른다. 근거: W-CO-03 §5",
            "parameters": [pathparam("notificationId"), idem()],
            "responses": {"204": {"description": "읽음으로 표시됐다"}, **err("403", "404")}}},
        "/app/notifications:read-all": {"post": {
            "tags": TAG, "summary": "모두 읽음",
            "description": "안 읽은 것이 하나라도 있을 때만 화면이 활성한다. 근거: W-CO-03 §5",
            "parameters": [idem()],
            "responses": {"200": {"description": "몇 건을 읽음으로 바꿨나",
                                  "content": {"application/json": {"schema": {
                                      "type": "object", "required": ["readCount"],
                                      "properties": {"readCount": {"type": "integer",
                                                                   "example": 12}}}}}},
                          **err("401")}}},
        "/app/notification-events": {"get": {
            "tags": TAG, "summary": "알림 이벤트 목록",
            "description": (
                "⭐ 이 목록의 정본은 계약이다 — 공통코드 마스터에 두면 편집 가능해지고, "
                "코드가 바뀌면 «보내는 쪽»이 조용히 깨진다. 근거: W-CO-03 §8-3 · W-CO-11 §8-3"),
            "responses": {"200": {"description": "목록", "content": {"application/json": {
                "schema": {"type": "object", "required": ["items"], "properties": {
                    "items": {"type": "array", "items": ref("NotificationEvent")}}}}}},
                **err("401")}}},
        "/app/notification-subscriptions": {
            "get": {"tags": TAG, "summary": "알림 수신자 설정 조회",
                    "description": "근거: W-CO-11 §5",
                    "parameters": [q("eventCode", {**STR, "x-no-example": True})],
                    "responses": {"200": {"description": "목록", "content": {
                        "application/json": {"schema": {
                            "type": "object", "required": ["items"], "properties": {
                                "items": {"type": "array",
                                          "items": ref("NotificationSubscription")}}}}}},
                        **err("401", "403")}},
            "put": {"tags": TAG, "summary": "알림 수신자 설정 저장",
                    "description": (
                        "이벤트 하나의 수신자를 통째로 바꾼다 — 화면의 저장이 그 단위다. "
                        "빠진 수신자는 지워진다. 근거: W-CO-11 §5"),
                    "parameters": [
                        q("eventCode", {**STR, "x-no-example": True}, required=True),
                        idem(), {"$ref": "#/components/parameters/IfMatchVersion"}],
                    "requestBody": {"required": True, "content": {"application/json": {
                        "schema": ref("NotificationSubscriptionReplace")}}},
                    "responses": {**one("NotificationSubscription", "200", "저장됨"),
                                  **err("400", "403", "409")}}},
        "/app/notices": {
            "get": {"tags": TAG, "summary": "공지 목록",
                    "description": "근거: W-CO-04 §5",
                    "parameters": [
                        q("statusCode", {**STR, "x-no-example": True}),
                        q("activeOnly", {"type": "boolean"}, "참이면 게시 중인 것만"),
                        q("q", STR, "제목 검색")] + PAGE,
                    "responses": listed("Notice")},
            "post": {"tags": TAG, "summary": "공지 작성",
                     "description": "작성만 한다 — 게시는 따로 누른다. 근거: W-CO-04 §5",
                     "parameters": [idem()],
                     "requestBody": {"required": True, "content": {"application/json": {
                         "schema": ref("NoticeCreate")}}},
                     "responses": {**one("Notice", "201", "작성됨"), **err("400", "403")}}},
        "/app/notices/{noticeId}": {
            "get": {"tags": TAG, "summary": "공지 한 건",
                    "parameters": [pathparam("noticeId")],
                    "responses": {**one("Notice"), **err("404")}},
            "put": {"tags": TAG, "summary": "공지 수정",
                    "description": (
                        "⛔ 게시 전에만 고칠 수 있다 — 게시 후 본문을 고치면 «이미 확인한 "
                        "사람이 다른 것을 본 것»이 되고, 확인 이력이 무엇에 대한 확인인지 "
                        "알 수 없어진다. 게시된 공지에 PUT 이 오면 409 다. 근거: W-CO-04 §5"),
                    "parameters": [pathparam("noticeId"), idem(),
                                   {"$ref": "#/components/parameters/IfMatchVersion"}],
                    "requestBody": {"required": True, "content": {"application/json": {
                        "schema": ref("NoticeCreate")}}},
                    "responses": {**one("Notice", "200", "수정됨"),
                                  **err("400", "403", "404", "409")}}},
        "/app/notices/{noticeId}:publish": {"post": {
            "tags": TAG, "summary": "공지 게시",
            "description": "게시하면 본문이 잠긴다. 근거: W-CO-04 §5",
            "parameters": [pathparam("noticeId"), idem(),
                           {"$ref": "#/components/parameters/IfMatchVersion"}],
            "responses": {**one("Notice", "200", "게시됨"), **err("403", "404", "409")}}},
        "/app/notices/{noticeId}:close": {"post": {
            "tags": TAG, "summary": "공지 종료",
            "description": (
                "종료일을 앞으로 당긴다. 지우지 않는다 — 확인 이력이 남아야 한다. "
                "근거: W-CO-04 §5"),
            "parameters": [pathparam("noticeId"), idem(),
                           {"$ref": "#/components/parameters/IfMatchVersion"}],
            "responses": {**one("Notice", "200", "종료됨"), **err("403", "404", "409")}}},
        "/app/notices/{noticeId}:acknowledge": {"post": {
            "tags": TAG, "summary": "공지 확인",
            "description": "읽은 사람이 스스로 누른다. 근거: W-CO-04 §5",
            "parameters": [pathparam("noticeId"), idem()],
            "responses": {"204": {"description": "확인됐다"}, **err("403", "404", "409")}}},
        "/app/notices/{noticeId}/acknowledgements": {"get": {
            "tags": TAG, "summary": "공지 확인 현황",
            "description": (
                "누가 확인했고 누가 아직 안 했나. 확인을 요구한 공지에서만 관리자가 본다. "
                "근거: W-CO-04 「미확인자 보기」"),
            "parameters": [pathparam("noticeId"),
                           q("pendingOnly", {"type": "boolean"}, "참이면 아직 안 한 사람만")]
            + PAGE,
            "responses": {**listed("NoticeAcknowledgement"), **err("403", "404")}}},
        "/app/dashboard-summary": {"get": {
            "tags": TAG, "summary": "통합 대시보드 집계",
            "description": (
                "카드마다 소유 화면이 따로 있고 이 경로는 «숫자만» 모은다. "
                "⛔ 자동 갱신을 두지 않는다 — 사람이 「갱신」을 누른다. "
                "⛔ 설비종합효율(OEE)은 내지 않는다: 계획 조업 시간의 분모가 되는 "
                "휴일·계획 정지를 담을 자리가 아직 없다. 근거: W-CO-05 §5·§8-1"),
            "parameters": [q("baseDate", DT, "기준 날짜. 없으면 오늘"),
                           q("plantId", I64)],
            "responses": {**one("DashboardSummary", "200", "집계"), **err("401", "403")}}},
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

    doc["components"]["schemas"].update(SCHEMAS)
    # ⛔ paths 를 정렬하지 않는다 — 이 파일은 정렬돼 있지 않다. 정렬하면
    #    경로를 더한 변경이 파일 전체를 다시 쓴 것으로 나온다.
    doc["paths"].update(paths_to_add())

    updated = json.dumps(doc, ensure_ascii=False, indent=indent) + tail
    if updated == original:
        print("  이미 반영돼 있다 — 변경 없음")
        return 0

    open(CONTRACT, "w", encoding="utf-8").write(updated)
    print(f"  ✅ 공통 6리소스 — 경로 {len(doc['paths'])} · 스키마 "
          f"{len(doc['components']['schemas'])}")
    print("     ⭐ 모델이 계약을 따라온다 — 결손 다섯은 공통 트랙 묶음 이슈로")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
