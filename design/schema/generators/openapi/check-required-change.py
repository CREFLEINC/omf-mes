#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""계약에서 «필수 여부»가 바뀐 자리를 찾아 통지 등급을 묻는다.

왜 필요한가
-----------
2026-08-31 PR #307 리뷰가 잡았다 — `GoodsReceipt`·`GoodsReceiptCreate` 의
`sourceDocumentTypeCode`·`sourceDocumentId` 가 `required` 에서 빠졌는데
**어느 검사기도 잡지 못했다.** `check-enum-narrowing` 은 값 목록만 보고,
`check-structure` 는 계약이 성립하는지만 본다. 등급표도 「필수 승격」만 ⛔ 로
적어 두고 **반대 방향에는 항목이 없었다.** 사람 눈에만 걸렸다.

⛔ 가르는 기준은 «방향»이 아니라 «누가 그 값을 읽는가»다
--------------------------------------------------------
같은 「필수 해제」라도 요청과 응답에서 뜻이 정반대다.

    요청 스키마에서 required 제거   →  ⚠  보내는 쪽이 덜 보내도 된다. 안 깨진다
    요청 스키마에 required 추가     →  ⛔  안 보내던 쪽이 400 을 받는다
    응답 스키마에서 required 제거   →  ⛔  «항상 있던 값이 없어질 수 있다»
                                        널 가드 없는 소비자가 깨진다
    응답 스키마에 required 추가     →  ⚠  더 보장하는 것이라 안 깨진다

`type` 이 nullable 로 넓어지는 것(`"string"` → `["string","null"]`)도 응답에서는
같은 사고다 — required 에 남아 있어도 값이 `null` 로 온다.

⛔ 두 번째 축 — «파라미터»(2026-09-03 신설, `omf-mes#359`)
---------------------------------------------------------
초판은 `components.schemas` 만 훑어 **헤더·질의 파라미터를 통째로 빠뜨렸다.**
`#350` 이 `POST /logistics/stock-transfers` 의 귀속 사번 헤더를
`WorkerNoOptional`(선택) → `WorkerNo`(**필수**)로 올렸는데 **3216필드를 대조하고
초록을 냈다.** 안 보내던 쪽은 400 을 받는다.

파라미터는 «전부 요청»이라 방향을 물을 것이 없다. 판정표는 한 줄짜리다.

    요청 파라미터에 required 추가·신설  →  ⛔  안 보내던 쪽이 400 을 받는다
    요청 파라미터에서 required 제거     →  ⚠  덜 보내도 된다
    기존 필수 파라미터의 이름·위치 변경 →  ⛔  보내던 이름으로는 안 닿는다

⚠ 잡으려면 **`$ref` 를 풀어야** 한다 — `#350` 의 모양이 그것이다. 참조 이름만
`WorkerNoOptional → WorkerNo` 로 바뀌고 헤더 «이름»(`X-Worker-No`)은 그대로였다.
그래서 파라미터의 신원을 참조 이름이 아니라 **풀어낸 `<in>:<name>`** 으로 잡는다.

⚠ `components.parameters.<이름>` 자체가 뒤집히면 **그것을 가리키는 오퍼레이션이
한꺼번에** 뒤집힌다. 그 자리는 오퍼레이션마다 한 줄씩 내지 않고 **공용 파라미터 한
줄 + 참조 오퍼레이션 수(파급)** 로 낸다 — 한 곳을 고치면 몇 개가 깨지는지가 값어치다.
실측 — `mdm-기준정보.json` 의 `IdempotencyKey` 는 **123 오퍼레이션**이 가리킨다.
파급이 **0 이면 ⚠ 로 내린다** — 아무도 안 가리키는 것을 고쳐도 깨질 코드가 없고,
거짓 경보가 쌓이면 검사기를 무시하게 된다(`check-enum-narrowing` 과 같은 기준).

⚠ 스키마 축과 같은 이유로 **없던 것은 세지 않는다** — 「기준에 없던 오퍼레이션」에
붙은 필수 파라미터는 깨질 코드가 없다. 반대로 **있던 오퍼레이션에 필수 파라미터를
새로 다는 것은 ⛔ 다** — 그 경로를 이미 부르던 쪽이 400 을 받는다.

⚠ 이 검사기가 «안 보는 것»
--------------------------
- **통지를 실제로 냈는지는 안 본다.** 「필수가 바뀐 자리가 있다」까지만 말한다.
- **요청·응답 판정은 «전이 폐쇄»로 한다.** 직접 참조에서 시작해 스키마 안의 `$ref`
  를 따라 부모의 방향을 물려준다(고정점 반복이라 순환 참조에도 멈춘다). 실측상 계약
  7벌 495스키마가 «전건» 판정된다 — 미상 0.
  ⚠ 한 스키마가 **요청·응답 양쪽**에 걸리면 `요청·응답` 으로 내고 어느 방향이든 ⛔ 로
  둔다 — 양쪽으로 깨질 수 있기 때문이다.
- **그래도 미상이 남으면 ⛔ 로 낸다** — 판정하지 못한 것을 통과시키지 않는다.
- **새로 생긴 스키마·필드는 세지 않는다.** 없던 것으로는 아무도 코드를 만들지
  않았으므로 깨질 것이 없다(`check-enum-narrowing` 과 같은 기준).
- **서버가 실제로 무엇을 내리는지는 모른다.** 계약이 「비어도 된다」로 바뀐 것과
  서버가 실제로 비워 보내는 것은 다르다. 계약 쪽만 본다.
- **경로 파라미터(`in: path`)는 등급 대상에서 뺀다.** 명세가 「항상 필수」로
  못박아 뒤집힐 수 없고, 이름이 바뀌면 URL 템플릿 자체가 달라져 «다른 경로»가
  된다(그 자리는 `check-operation-inventory-drift` 가 본다).
- **`requestBody` 자체의 `required` 는 안 본다** — 바디를 통째로 필수로 올리는
  것도 같은 사고인데 이 검사기는 바디 «안»의 필드만 본다(실측 계약 7벌 182건 중
  `false` 는 1건).
- **파라미터의 «값»은 안 본다** — `required` 와 이름·위치만 본다. 파라미터
  `schema` 의 타입·값 목록이 좁아지는 것은 여기서도 `check-enum-narrowing` 에서도
  안 잡힌다(둘 다 `components.schemas` 만 훑는다).
- **`allOf`·`oneOf` 로 합성된 `required` 는 안 본다** — 스키마가 자기 몸에 적은
  `required` 배열만 읽는다(실측 계약 7벌에 그런 파라미터는 없다).
- **파라미터가 가리키는 스키마에는 방향을 물려주지 않는다** — `roles()` 는
  `requestBody`·`responses` 에서만 출발한다.

쓰기
----
    python3 design/schema/generators/openapi/check-required-change.py            # HEAD 대비
    python3 design/schema/generators/openapi/check-required-change.py <기준 커밋>
"""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                      capture_output=True, text=True, cwd=HERE).stdout.strip()
CONTRACTS_DIR = os.path.join(ROOT, "design", "wiki", "api-contracts", "openapi")

REF = re.compile(r'"#/components/schemas/([^"]+)"')
PARAM_REF = re.compile(r"^#/components/parameters/(.+)$")
METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


def roles(doc: dict) -> dict[str, set[str]]:
    """스키마 이름 → {"요청","응답"}.

    ⛔ 직접 참조만 보면 «중첩 스키마»가 통째로 빠진다 — 2026-08-31 실측에서 495 중
    99(20%)가 「미상」이었고, 미상은 ⛔ 로 울므로 요청 계열 완화까지 거짓 ⛔ 가 됐다.
    그래서 부모의 방향을 자식에게 «전이»시킨다. 고정점 반복이라 순환 참조에도 멈춘다.
    """
    out: dict[str, set[str]] = {}

    def mark(node, role: str) -> None:
        for name in REF.findall(json.dumps(node, ensure_ascii=False)):
            out.setdefault(name, set()).add(role)

    for _path, item in (doc.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for _method, op in item.items():
            if not isinstance(op, dict):
                continue
            if "requestBody" in op:
                mark(op["requestBody"], "요청")
            if "responses" in op:
                mark(op["responses"], "응답")

    schemas = doc.get("components", {}).get("schemas") or {}
    changed = True
    while changed:                       # 고정점까지 — 순환 참조에서도 끝난다
        changed = False
        for name, role in list(out.items()):
            body = schemas.get(name)
            if body is None:
                continue
            for child in REF.findall(json.dumps(body, ensure_ascii=False)):
                if child == name:
                    continue
                before = set(out.get(child, ()))
                out.setdefault(child, set()).update(role)
                if out[child] != before:
                    changed = True
    return out


def shape(doc: dict) -> dict[str, dict]:
    """스키마.필드 → {"required": bool, "nullable": bool}"""
    out: dict[str, dict] = {}
    for name, schema in (doc.get("components", {}).get("schemas") or {}).items():
        if not isinstance(schema, dict):
            continue
        req = set(schema.get("required") or [])
        for field, prop in (schema.get("properties") or {}).items():
            t = prop.get("type") if isinstance(prop, dict) else None
            nullable = isinstance(t, list) and "null" in t
            out[f"{name}.{field}"] = {"required": field in req, "nullable": nullable}
    return out


def component_params(doc: dict) -> dict[str, dict]:
    """`components.parameters` — 이름 → 정의(딕셔너리인 것만)."""
    out: dict[str, dict] = {}
    for name, body in ((doc.get("components") or {}).get("parameters") or {}).items():
        if isinstance(body, dict):
            out[name] = body
    return out


def resolve_param(node, comps: dict[str, dict]) -> tuple[dict | None, str | None]:
    """파라미터 하나를 풀어 (정의, 오퍼레이션이 «적은» 참조 이름) 을 돌려준다.

    ⛔ `$ref` 를 풀지 않으면 `#350` 이 안 잡힌다 — 참조 이름만
    `WorkerNoOptional → WorkerNo` 로 바뀌고 헤더 이름은 그대로였다.
    참조가 또 참조를 가리키는 사슬도 따라가되, 같은 이름을 두 번 밟으면 멈춘다.
    풀지 못하면 정의를 `None` 으로 돌려준다 — 판정 불가로 ⛔ 가 된다.
    """
    ref_name: str | None = None
    seen: set[str] = set()
    while isinstance(node, dict) and "$ref" in node:
        m = PARAM_REF.match(str(node["$ref"]))
        if not m:
            return None, ref_name          # 다른 문서·다른 자리를 가리킨다 — 못 푼다
        target = m.group(1)
        if ref_name is None:
            ref_name = target              # 오퍼레이션이 «적은» 이름을 남긴다
        if target in seen:
            return None, ref_name          # 순환 참조
        seen.add(target)
        node = comps.get(target)
    if not isinstance(node, dict):
        return None, ref_name
    return node, ref_name


def params(doc: dict) -> dict[str, dict[str, dict]]:
    """오퍼레이션 → {"<in>:<name>": {"required", "ref", "name", "in"}}

    - **경로 레벨 `paths.<경로>.parameters` 를 먼저 깔고** 메서드 레벨로 덮는다
      (OpenAPI 3 — 같은 `name`+`in` 이면 오퍼레이션 쪽이 이긴다).
    - `$ref` 는 풀어서 «실제 이름·위치·필수»로 비교한다.
    - `in: path` 는 담지 않는다 — 항상 필수라 뒤집힐 수 없다(머리말 「안 보는 것」).
    - 파라미터가 하나도 없는 오퍼레이션도 «빈 칸»으로 담는다 — 그래야 「이 오퍼레이션이
      원래 있었나」를 물어 «신설 필수 파라미터»와 «새 오퍼레이션»을 가를 수 있다.
    """
    comps = component_params(doc)
    out: dict[str, dict[str, dict]] = {}
    for path, item in (doc.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        shared = item.get("parameters")
        shared = list(shared) if isinstance(shared, list) else []
        for method, op in item.items():
            if method.lower() not in METHODS or not isinstance(op, dict):
                continue
            own = op.get("parameters")
            own = list(own) if isinstance(own, list) else []
            bucket: dict[str, dict] = {}
            for node in shared + own:      # 뒤가 앞을 덮는다 = 오퍼레이션이 이긴다
                if not isinstance(node, dict):
                    continue
                body, ref = resolve_param(node, comps)
                if body is None:
                    key = f"미해소:{ref or json.dumps(node, ensure_ascii=False)}"
                    bucket[key] = {"required": None, "ref": ref,
                                   "name": ref, "in": "미해소"}
                    continue
                loc, name = body.get("in"), body.get("name")
                if loc == "path" or not loc or not name:
                    continue
                bucket[f"{loc}:{name}"] = {
                    "required": bool(body.get("required", False)),
                    "ref": ref, "name": name, "in": loc,
                }
            out[f"{method.upper()} {path}"] = bucket
    return out


def _shape_of(body: dict) -> tuple:
    return (body.get("name"), body.get("in"), bool(body.get("required", False)))


def _trail(was: dict, now: dict) -> str:
    """참조가 «갈아 끼워졌으면» 그 사실을 붙인다 — `#350` 의 모양이다."""
    if was.get("ref") == now.get("ref"):
        return ""
    return f" (참조 {was.get('ref') or '인라인'} → {now.get('ref') or '인라인'})"


def compare_params(fname: str, old_doc: dict, new_doc: dict) -> tuple[list, list, int]:
    """파라미터 축 — (⛔ 목록, ⚠ 목록, 대조한 파라미터 수)."""
    old_ops, new_ops = params(old_doc), params(new_doc)
    old_comps, new_comps = component_params(old_doc), component_params(new_doc)
    blocking: list[str] = []
    notice: list[str] = []

    # ── 공용 파라미터 자체가 바뀐 자리 — 파급(참조 오퍼레이션 수)을 함께 낸다
    changed: dict[str, tuple] = {}
    for cname, body in new_comps.items():
        was_body = old_comps.get(cname)
        if not isinstance(was_body, dict):
            continue                        # 없던 공용 파라미터 — 깨질 코드가 없다
        b, _ = resolve_param(was_body, old_comps)
        a, _ = resolve_param(body, new_comps)
        if b is None or a is None or _shape_of(b) == _shape_of(a):
            continue
        changed[cname] = (_shape_of(b), _shape_of(a))

    for cname, (was_s, now_s) in sorted(changed.items()):
        hits = sum(1 for bucket in new_ops.values()
                   if any(p.get("ref") == cname for p in bucket.values()))
        head = f"{fname} · 공용 파라미터 {cname}({now_s[1]}:{now_s[0]}) [요청] — "
        tail = f" · 참조 오퍼레이션 {hits}곳"
        # ⚠ 파급이 0 이면 깨질 코드가 없다 — ⛔ 로 울면 거짓 경보다(실측 계약 7벌에
        #   `shipment-04제품출하.json · IfMatchVersionOptional` 이 0곳이다).
        if hits == 0:
            tail += " — 아무도 안 가리킨다"
        if (was_s[0], was_s[1]) != (now_s[0], now_s[1]):
            line = (f"{head}이름·위치가 바뀌었다 "
                    f"{was_s[1]}:{was_s[0]} → {now_s[1]}:{now_s[0]}{tail}")
            (notice if hits == 0 else blocking).append(line)
        elif now_s[2] and not was_s[2]:
            (notice if hits == 0 else blocking).append(head + "required 로 올랐다" + tail)
        elif was_s[2] and not now_s[2]:
            notice.append(head + "required 에서 빠졌다" + tail)

    # ── 오퍼레이션마다 — 기준에 «있던» 오퍼레이션만 본다(없던 것은 깨질 코드가 없다)
    compared = 0
    for opkey in sorted(set(old_ops) & set(new_ops)):
        was, now = old_ops[opkey], new_ops[opkey]
        compared += len(now)
        both = sorted(set(was) & set(now))

        for key in both:
            b, a = was[key], now[key]
            if b["required"] == a["required"]:
                continue                    # 둘 다 못 푼 자리(None == None)도 여기서 걷힌다
            if a["ref"] and a["ref"] == b["ref"] and a["ref"] in changed:
                continue                    # 공용 파라미터 한 줄이 이미 냈다
            line = f"{fname} · {opkey} · {key} [요청] — "
            if a["required"]:
                blocking.append(line + "required 로 올랐다" + _trail(b, a))
            else:
                notice.append(line + "required 에서 빠졌다" + _trail(b, a))

        rest_old = [k for k in was if k not in both]
        rest_new = [k for k in now if k not in both]

        # 공용 파라미터의 «이름·위치»가 바뀌어 키가 어긋난 자리 — 공용 행이 이미 냈다
        for ko in list(rest_old):
            ref = was[ko].get("ref")
            if not ref or ref not in changed:
                continue
            mate = [kn for kn in rest_new if now[kn].get("ref") == ref]
            if mate:
                rest_old.remove(ko)
                rest_new.remove(mate[0])

        # 지금 판에서 «못 푼» 참조 — 판정하지 못한 것을 통과시키지 않는다(⛔)
        for kn in [k for k in rest_new if now[k]["required"] is None]:
            ref = now[kn].get("ref")
            for ko in list(rest_old):
                if was[ko].get("ref") == ref:
                    rest_old.remove(ko)
                    break
            rest_new.remove(kn)
            blocking.append(f"{fname} · {opkey} · {kn} [요청] — "
                            f"참조를 풀지 못했다 — 판정 불가")
        for ko in [k for k in rest_old if was[k]["required"] is None]:
            rest_old.remove(ko)             # 기준에서 못 풀던 것 — 지금 판으로 매긴다

        gone = [k for k in rest_old if was[k]["required"]]
        added = [k for k in rest_new if now[k]["required"]]

        # 이름은 그대로인데 «위치»만 바뀐 것
        for ko in list(gone):
            for kn in list(added):
                if was[ko]["name"] == now[kn]["name"]:
                    blocking.append(f"{fname} · {opkey} · 필수 파라미터의 위치가 "
                                    f"바뀌었다 {ko} → {kn} [요청]")
                    gone.remove(ko)
                    added.remove(kn)
                    break

        # 같은 위치 안에서 1:1 로 남으면 «이름»이 바뀐 것 — 짝이 모호하면 짓지 않는다
        for loc in sorted({was[k]["in"] for k in gone} | {now[k]["in"] for k in added}):
            go = [k for k in gone if was[k]["in"] == loc]
            ad = [k for k in added if now[k]["in"] == loc]
            if len(go) == 1 and len(ad) == 1:
                blocking.append(f"{fname} · {opkey} · 필수 파라미터의 이름이 "
                                f"바뀌었다 {go[0]} → {ad[0]} [요청]")
                gone.remove(go[0])
                added.remove(ad[0])

        for kn in added:                    # 신설 — 오퍼레이션은 원래 있었다
            ref = now[kn].get("ref")
            note = f" (참조 {ref})" if ref else ""
            blocking.append(f"{fname} · {opkey} · {kn} [요청] — "
                            f"필수 파라미터가 새로 생겼다{note}")
        for ko in gone:
            notice.append(f"{fname} · {opkey} · {ko} [요청] — 필수 파라미터가 사라졌다")

    return blocking, notice, compared


def load(ref: str, path: str) -> dict | None:
    rel = os.path.relpath(path, ROOT)
    r = subprocess.run(["git", "show", f"{ref}:{rel}"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def role_of(name: str, table: dict[str, set[str]]) -> str:
    r = table.get(name)
    if not r:
        return "미상"
    if r == {"요청"}:
        return "요청"
    if r == {"응답"}:
        return "응답"
    return "요청·응답"


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    blocking: list[str] = []   # ⛔
    notice: list[str] = []     # ⚠
    checked = 0
    checked_params = 0

    for path in sorted(glob.glob(os.path.join(CONTRACTS_DIR, "*.json"))):
        fname = os.path.basename(path)
        old_doc = load(base, path)
        if old_doc is None:
            continue
        with open(path, encoding="utf-8") as f:
            new_doc = json.load(f)

        old, new = shape(old_doc), shape(new_doc)
        table = roles(new_doc)

        for key, now in new.items():
            was = old.get(key)
            if was is None:
                continue                       # 없던 필드 — 깨질 코드가 없다
            checked += 1
            schema_name = key.split(".")[0]
            role = role_of(schema_name, table)

            if was["required"] and not now["required"]:
                line = f"{fname} · {key} [{role}] — required 에서 빠졌다"
                (blocking if role in ("응답", "요청·응답", "미상") else notice).append(line)
            elif not was["required"] and now["required"]:
                line = f"{fname} · {key} [{role}] — required 로 올랐다"
                (blocking if role in ("요청", "요청·응답", "미상") else notice).append(line)

            if not was["nullable"] and now["nullable"]:
                line = f"{fname} · {key} [{role}] — 값이 null 로 올 수 있게 됐다"
                (blocking if role in ("응답", "요청·응답", "미상") else notice).append(line)

        # 두 번째 축 — 파라미터(`omf-mes#359`). 전부 요청이라 방향을 묻지 않는다.
        pb, pn, pc = compare_params(fname, old_doc, new_doc)
        blocking.extend(pb)
        notice.extend(pn)
        checked_params += pc

    print(f"필수·널 허용 변경 검사 — 기준 {base} · 대조한 필드 {checked}"
          f" · 대조한 파라미터 {checked_params}")
    print()

    if blocking:
        print(f"⛔ 등급 ⛔ {len(blocking)}건 — 이미 만든 것이 틀린다")
        for line in blocking:
            print("   " + line)
        print()
    if notice:
        print(f"⚠ 등급 ⚠ {len(notice)}건 — 기존은 깨지지 않는다")
        for line in notice:
            print("   " + line)
        print()

    if not blocking and not notice:
        print("✅ 필수 여부·널 허용이 바뀐 자리가 없습니다.")
        return 0

    print("⛔ 이 검사기는 «등급을 채웠는지»를 보지 않는다 — 사람이 판단한다(설계팀 내부).")
    print("   개발팀에는 다음 설계 변동 공지로 «지점»만 나간다 — 등급·내용은 싣지 않는다.")
    print("   등급 정본: .claude/skills/design-change-notice/references/change-grades.md")
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
