#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""기능 권한 목록을 **화면 목록에서 기계로 파생**한다 — `권한목록.md`.

왜 생성기인가
-------------
권한 코드는 «앱 기능 목록»이고 화면과 1:1 이다(입도 = 화면 단위 · 사용자 결정
2026-09-01). 손으로 적으면 화면이 늘 때마다 두 곳이 갈리고, 「지금 권한이 몇
개인가」를 아무도 못 센다. 화면 스펙이 정본이므로 거기서 뽑는다.

⛔ **한 화면 안에서 조회와 편집을 가르지 않는다.** 처음에는 마스터 화면만
둘로 나누는 안을 두었으나 **화면 단위로 확정**됐다 — 「마스터별 편집
권한 매트릭스」의 「조회만 허용」 축은 그때 함께 철회했다(`W-CO-02` §8-8).

무엇을 내나
-----------
  - 권한 — `code`(화면 코드) · `name`(화면 이름) · `groupCode`(도메인 축)
  - 시드 — 역할 4 · 최초 관리자 1 · 사용자 상태 3

이 목록이 `GET /app/permissions` 의 응답이 된다.

쓰기
----
    python3 design/schema/generators/build-permission-catalog.py
"""
from __future__ import annotations

import glob
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SCREENS = os.path.join(HERE, "..", "..", "wiki", "screens")
OUT = os.path.join(HERE, "권한목록.md")

# 제목 서식이 두 벌이다 — `# W-01-03 · 초과 입하 분리` 와 `` # `W-03-10` 처분 판정 처리 `` .
TITLE = re.compile(r"^#\s+`?([A-Z]-[A-Z0-9]+-[0-9]+)`?\s*(?:·\s*)?(.+?)\s*$")
# ⛔ 폐지된 화면은 권한을 갖지 않는다 — 부여해도 갈 곳이 없다.
# ⚠ 「폐지」를 제목 아무 데서나 잡지 않는다 — 취소선(`~~`)으로만 판정한다.
#    「…폐지 이력 조회」 같은 살아 있는 화면을 조용히 빠뜨리지 않기 위해서다.
RETIRED = re.compile(r"~~")

DOMAIN = {
    "01": "자재·창고", "02": "생산 실행", "03": "품질", "04": "제품 출하",
    "05": "설비·툴", "06": "기준정보", "CO": "공통",
}

ROLES = [
    ("ROLE_WORKER", "실무자"),
    ("ROLE_SITE_MGR", "현장 관리자"),
    ("ROLE_EXEC_MGR", "경영 관리자"),
    ("ROLE_SYS_ADMIN", "시스템 운영자"),
]
USER_STATUS = [("ACTIVE", "재직"), ("ON_LEAVE", "휴직"), ("RETIRED", "퇴사")]


def collect() -> "tuple[list, list, list]":
    """(권한 행, 폐지로 제외, 서식 불일치로 제외) 를 «갈라» 돌려준다.

    ⛔ **제외 사유를 뭉뚱그리지 않는다.** 폐지는 정상이고 서식 불일치는 사고인데,
    한 덩어리로 세면 화면 제목 서식이 바뀐 날 그 화면의 권한이 «조용히» 사라진다.
    그러면 그 화면은 아무에게도 부여할 수 없게 되고, 아무 도구도 알리지 않는다 —
    이 저장소가 없애려는 「조용히 빈 목록」과 같은 실패다(2026-09-01 리뷰 지적).
    """
    rows, retired, unmatched = [], [], []
    for p in sorted(glob.glob(os.path.join(SCREENS, "*", "*.md"))):
        with io.open(p, encoding="utf-8") as fh:
            first = fh.readline()
        base = os.path.basename(p)
        if RETIRED.search(first):
            retired.append((base, first.strip()))
            continue
        m = TITLE.match(first)
        if not m:
            unmatched.append((base, first.strip()))
            continue
        code, name = m.group(1), m.group(2)
        axis = code.split("-")[1]          # W-01-03 → 01 · W-CO-02 → CO
        rows.append((code, name, axis))
    return sorted(rows), retired, unmatched


# 정본 화면 목록 — 진도표가 «지금 서 있는» 화면을 센다(2026-09-01 실측 117 —
# `verify-screen-inventory.py` 출력과 같다).
# ⛔ `raw/…/screen-inventory-ia.md`(129)·`04-통합-IA.md`(131)를 쓰지 않는다 —
#    통합·폐지 전 원본이라 지금 서 있는 화면보다 많다.
INVENTORY = os.path.join(HERE, "..", "..", "wiki", "handover", "화면-진도표.md")
SCREEN_CODE = re.compile(r"([WMP]-(?:CO|\d{2})-\d{2})")


def screen_inventory_count() -> "int | None":
    """정본 화면 수.

    ⭐ 대조 상대를 «생성기 자신»이 아니라 인벤토리 정본으로 둔다 — 자기가 센 수를
    자기가 검증하면 화면 스펙 서식이 바뀐 순간 둘 다 같이 틀린다.
    ⛔ 정본을 못 읽으면 `None` 을 내고 «건너뛰지 않고» 호출부가 실패로 다룬다.
    """
    if not os.path.exists(INVENTORY):
        return None
    with io.open(INVENTORY, encoding="utf-8") as fh:
        return len(set(SCREEN_CODE.findall(fh.read())))


def main() -> int:
    rows, retired, unmatched = collect()
    by_axis = {}
    for code, name, axis in rows:
        by_axis.setdefault(axis, []).append((code, name))

    out = []
    out.append("# 기능 권한 목록 — **화면 목록에서 기계 파생**\n")
    out.append("> ⛔ 손으로 고치지 않는다 — `build-permission-catalog.py` 가 만든다.\n")
    out.append("> 입도 = **화면 단위**(사용자 결정 2026-09-01). 값이 화면 코드와 1:1 이고,\n"
               "> 한 화면 안에서 조회와 편집을 가르지 않는다.\n")
    out.append("")
    out.append("## 한 줄\n")
    out.append(f"권한 **{len(rows)}** · 도메인 축 **{len(by_axis)}** · "
               "이 목록이 `GET /app/permissions` 의 응답이다.\n")
    out.append("⛔ **공통코드가 아니다** — 앱 기능 목록이라 고객이 `W-06-06` 에서 늘리거나 "
               "지울 수 없다. 화면이 늘면 이 생성기를 다시 돌려 배포로 는다.\n")

    out.append("## 권한\n")
    for axis in sorted(by_axis):
        label = DOMAIN.get(axis, axis)
        out.append(f"### `{axis}` {label} — {len(by_axis[axis])}\n")
        out.append("| code | name |")
        out.append("| --- | --- |")
        for code, name in by_axis[axis]:
            out.append(f"| `{code}` | {name} |")
        out.append("")

    out.append("## 시드 — 개발용\n")
    out.append("⛔ **반영은 데이터모델 소관이다 — 작업 통지이고 기다리지 않는다**"
               "(`design/schema/data-model-boundary.md`).\n")
    out.append("### 역할 `app.role` — 4\n")
    out.append("고객이 운영 중 늘리고 고치고 지운다(사용자 결정 2026-09-01). "
               "⭐ 화면 동작은 역할 «이름»이 아니라 **권한**에 걸리므로 이 넷은 출발점일 뿐이다.\n")
    out.append("| roleCode | roleName |")
    out.append("| --- | --- |")
    for c, n in ROLES:
        out.append(f"| `{c}` | {n} |")
    out.append("")
    out.append("### 최초 관리자 `app.app_user` — 1\n")
    out.append("⛔ **없으면 아무도 아무 권한을 줄 수 없다.** 마지막 관리자 차단"
               "(`code=LAST_ADMIN`)이 걸려 있어 관리자 교체는 «다른 관리자»가 하고, "
               "그래서 **최초 1명은 시드로 서야 한다**. `ROLE_SYS_ADMIN` 을 부여한 상태로 넣는다.\n")
    out.append("⚠ 운영은 관리자를 **둘 이상** 두어야 한다 — 하나뿐이면 그 사람을 내릴 방법이 없다.\n")
    out.append("### 사용자 상태 `APP_USER_STATUS` — 3\n")
    out.append("⭐ **인사 상태다**(표시용). 계정을 쓸 수 있는가는 `is_active` 가 정한다"
               "(`W-CO-02` §8-4). `G-31` 마스터안전형이라 개발 이후 고객이 `W-06-06` 에서 편집·대체한다.\n")
    out.append("| code | name |")
    out.append("| --- | --- |")
    for c, n in USER_STATUS:
        out.append(f"| `{c}` | {n} |")
    out.append("")
    out.append("---\n")
    out.append(f"출처: `design/wiki/screens/*/*.md` 첫 줄 · 생성: "
               f"`design/schema/generators/build-permission-catalog.py`")

    with io.open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"생성: {OUT}")
    print(f"권한 {len(rows)} · 도메인 축 {len(by_axis)} · "
          f"역할 시드 {len(ROLES)} · 상태 시드 {len(USER_STATUS)}")
    for axis in sorted(by_axis):
        print(f"   {axis} {DOMAIN.get(axis, axis):8s} {len(by_axis[axis]):3d}")

    # ⛔ 제외는 «사유별로» 보인다 — 뭉뚱그리면 사고가 정상으로 읽힌다.
    if retired:
        print(f"\n폐지로 제외 {len(retired)} — 정상이다")
        for base, title in retired:
            print(f"   {base} :: {title[:70]}")
    if unmatched:
        print(f"\n⛔ 제목 서식이 안 맞아 제외 {len(unmatched)} — 권한이 «조용히» 사라진 자리다")
        for base, title in unmatched:
            print(f"   {base} :: {title[:70]}")
        print("   → 제목을 `# <화면코드> · <이름>` 으로 맞추거나, 폐지면 취소선(~~)을 친다")
        return 1

    # ⭐ 정본과 대조한다 — 이 대조가 없으면 위 ⛔ 를 아무도 안 본다.
    expected = screen_inventory_count()
    if expected is None:
        print(f"\n⛔ 정본 인벤토리를 못 읽었다 — {INVENTORY}")
        return 1
    if expected != len(rows):
        print(f"\n⛔ 정본과 어긋난다 — 진도표 {expected} ≠ 권한 {len(rows)}")
        print("   → 화면이 늘거나 줄었는데 한쪽만 따라왔다. 어느 쪽이 맞는지 먼저 정한다")
        return 1
    print(f"\n✅ 정본과 같다 — 진도표 {expected} = 권한 {len(rows)} (폐지 {len(retired)} 제외)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
