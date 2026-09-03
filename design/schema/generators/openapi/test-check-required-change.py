#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# check-required-change.py 의 단위 테스트. 표준 라이브러리만 쓴다(저장소 관행).
#
# 이 검사기가 가르는 것은 «누가 그 값을 읽는가» 하나다. 그 판정이 통지 등급을
# 정하므로, 판정표 네 칸(요청·응답 × 추가·제거)을 표본으로 잠근다.
#
# ⛔ 왜 필요했나 — PR #307 2차 리뷰가 잡았다. 초판은 requestBody·responses 에서
#    «직접» 참조된 스키마만 방향을 매겨 중첩 스키마 99개(495 중 20%)가 「미상」이
#    됐고, 미상은 ⛔ 로 울므로 «요청 계열 완화»까지 거짓 ⛔ 가 됐다. 실행만으로는
#    안 드러났다 — 그때 돌린 기준에서 미상이 0건이었기 때문이다. 판정표를 고정하는
#    테스트가 있었으면 잡혔을 자리라 여기 잠근다.
import importlib
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
crc = importlib.import_module("check-required-change")


def doc(paths=None, **schemas):
    return {"paths": paths or {}, "components": {"schemas": dict(schemas)}}


def op(kind: str, schema: str):
    """kind = requestBody | responses — 그 자리에서 schema 를 가리키는 오퍼레이션."""
    ref = {"$ref": f"#/components/schemas/{schema}"}
    if kind == "requestBody":
        return {"post": {"requestBody": {"content": {"application/json": {"schema": ref}}}}}
    return {"get": {"responses": {"200": {"content": {"application/json": {"schema": ref}}}}}}


class RoleTest(unittest.TestCase):
    def test_요청으로_직접_참조되면_요청이다(self):
        d = doc(paths={"/x": op("requestBody", "A")}, A={"type": "object"})
        self.assertEqual(crc.role_of("A", crc.roles(d)), "요청")

    def test_응답으로_직접_참조되면_응답이다(self):
        d = doc(paths={"/x": op("responses", "A")}, A={"type": "object"})
        self.assertEqual(crc.role_of("A", crc.roles(d)), "응답")

    # ⛔ 이 셋이 초판의 결손이다 — 중첩은 부모의 방향을 물려받아야 한다.
    def test_중첩된_자식이_부모의_방향을_물려받는다(self):
        d = doc(
            paths={"/x": op("responses", "Parent")},
            Parent={"type": "object",
                    "properties": {"child": {"$ref": "#/components/schemas/Child"}}},
            Child={"type": "object"},
        )
        self.assertEqual(crc.role_of("Child", crc.roles(d)), "응답")

    def test_두_겹_아래까지_물려받는다(self):
        d = doc(
            paths={"/x": op("requestBody", "A")},
            A={"properties": {"b": {"$ref": "#/components/schemas/B"}}},
            B={"properties": {"c": {"$ref": "#/components/schemas/C"}}},
            C={"type": "object"},
        )
        self.assertEqual(crc.role_of("C", crc.roles(d)), "요청")

    def test_순환_참조에서_멈춘다(self):
        d = doc(
            paths={"/x": op("responses", "A")},
            A={"properties": {"b": {"$ref": "#/components/schemas/B"}}},
            B={"properties": {"a": {"$ref": "#/components/schemas/A"}}},
        )
        self.assertEqual(crc.role_of("B", crc.roles(d)), "응답")   # 무한 루프가 아니라 값이 나온다

    def test_양쪽에_걸리면_요청_응답이다(self):
        d = doc(paths={"/x": op("requestBody", "A"), "/y": op("responses", "A")},
                A={"type": "object"})
        self.assertEqual(crc.role_of("A", crc.roles(d)), "요청·응답")

    def test_아무_데서도_안_쓰이면_미상이다(self):
        d = doc(A={"type": "object"})
        self.assertEqual(crc.role_of("A", crc.roles(d)), "미상")


class ShapeTest(unittest.TestCase):
    def test_required_와_널_허용을_읽는다(self):
        d = doc(A={"required": ["x"],
                   "properties": {"x": {"type": "string"},
                                  "y": {"type": ["string", "null"]}}})
        s = crc.shape(d)
        self.assertEqual(s["A.x"], {"required": True, "nullable": False})
        self.assertEqual(s["A.y"], {"required": False, "nullable": True})

    def test_properties_없는_스키마에서_죽지_않는다(self):
        self.assertEqual(crc.shape(doc(A={"type": "string"})), {})


class GradeTableTest(unittest.TestCase):
    """판정표 네 칸 — 등급 정본은 design-change-notice/references/change-grades.md."""

    CASES = [
        # (방향, 변화,            ⛔ 인가)
        ("응답", "required 제거", True),    # 항상 있던 값이 사라질 수 있다
        ("요청", "required 제거", False),   # 덜 보내도 된다
        ("요청", "required 추가", True),    # 안 보내던 쪽이 400
        ("응답", "required 추가", False),   # 더 보장한다
        ("미상", "required 제거", True),    # 판정 못 한 것을 통과시키지 않는다
        ("미상", "required 추가", True),
        ("요청·응답", "required 제거", True),
        ("요청·응답", "required 추가", True),
    ]

    def test_판정표가_등급표와_같다(self):
        for role, change, expect_blocking in self.CASES:
            with self.subTest(role=role, change=change):
                if change == "required 제거":
                    got = role in ("응답", "요청·응답", "미상")
                else:
                    got = role in ("요청", "요청·응답", "미상")
                self.assertEqual(got, expect_blocking)

    def test_응답의_널_허용_확대는_차단이다(self):
        # required 에 남아 있어도 값이 null 로 오면 같은 사고다.
        self.assertTrue("응답" in ("응답", "요청·응답", "미상"))
        self.assertFalse("요청" in ("응답", "요청·응답", "미상"))


# ─────────────────────────────────────────────────────────────────────────────
# 두 번째 축 — 파라미터(`omf-mes#359`)
#
# ⛔ 왜 필요했나 — `#350` 이 `POST /logistics/stock-transfers` 의 귀속 사번 헤더를
#    `WorkerNoOptional`(선택) → `WorkerNo`(필수)로 올렸는데 **3216필드를 대조하고
#    초록을 냈다.** 검사기에 `parameters` 를 다루는 코드가 0줄이었기 때문이다.
#    파라미터는 «전부 요청»이라 방향을 물을 것이 없다 — 판정표가 한 줄짜리다.
# ─────────────────────────────────────────────────────────────────────────────

WORKER_REQ = {"name": "X-Worker-No", "in": "header", "required": True,
              "schema": {"type": "string"}}
WORKER_OPT = {"name": "X-Worker-No", "in": "header", "required": False,
              "schema": {"type": "string"}}


def pdoc(paths, params=None):
    """파라미터 축 전용 문서 — `components.parameters` 를 함께 세운다."""
    return {"paths": paths,
            "components": {"schemas": {}, "parameters": dict(params or {})}}


def hdr(name, required):
    return {"name": name, "in": "header", "required": required,
            "schema": {"type": "string"}}


def qry(name, required):
    return {"name": name, "in": "query", "required": required,
            "schema": {"type": "string"}}


def pref(name):
    return {"$ref": f"#/components/parameters/{name}"}


def diff(old, new):
    """(⛔ 목록, ⚠ 목록) — 파일 이름은 판정에 안 쓰이므로 고정한다."""
    blocking, notice, _ = crc.compare_params("t.json", old, new)
    return blocking, notice


class ParamCollectTest(unittest.TestCase):
    """`params()` — 무엇을 «파라미터 하나»로 세는가."""

    def test_인라인_파라미터를_읽는다(self):
        d = pdoc({"/x": {"post": {"parameters": [hdr("X-Worker-No", True)]}}})
        got = crc.params(d)["POST /x"]["header:X-Worker-No"]
        self.assertTrue(got["required"])
        self.assertIsNone(got["ref"])

    def test_ref_를_풀어_실제_이름과_필수를_읽는다(self):
        d = pdoc({"/x": {"post": {"parameters": [pref("WorkerNo")]}}},
                 {"WorkerNo": WORKER_REQ})
        got = crc.params(d)["POST /x"]["header:X-Worker-No"]
        self.assertTrue(got["required"])
        self.assertEqual(got["ref"], "WorkerNo")

    def test_참조가_참조를_가리키는_사슬도_따라간다(self):
        d = pdoc({"/x": {"post": {"parameters": [pref("A")]}}},
                 {"A": pref("B"), "B": WORKER_REQ})
        got = crc.params(d)["POST /x"]["header:X-Worker-No"]
        self.assertTrue(got["required"])
        self.assertEqual(got["ref"], "A")      # 오퍼레이션이 «적은» 이름을 남긴다

    def test_순환_참조에서_멈춘다(self):
        d = pdoc({"/x": {"post": {"parameters": [pref("A")]}}},
                 {"A": pref("B"), "B": pref("A")})
        bucket = crc.params(d)["POST /x"]
        self.assertEqual(list(bucket), ["미해소:A"])   # 무한 루프가 아니라 값이 나온다

    def test_없는_공용_파라미터를_가리키면_미해소다(self):
        d = pdoc({"/x": {"post": {"parameters": [pref("Missing")]}}})
        self.assertEqual(crc.params(d)["POST /x"]["미해소:Missing"]["required"], None)

    def test_경로_레벨_파라미터가_모든_메서드로_상속된다(self):
        d = pdoc({"/x": {"parameters": [qry("plant", True)], "get": {}, "post": {}}})
        got = crc.params(d)
        self.assertTrue(got["GET /x"]["query:plant"]["required"])
        self.assertTrue(got["POST /x"]["query:plant"]["required"])

    def test_메서드_레벨이_경로_레벨을_덮는다(self):
        # OpenAPI 3 — 같은 name+in 이면 오퍼레이션 쪽이 이긴다.
        d = pdoc({"/x": {"parameters": [qry("plant", True)],
                         "get": {"parameters": [qry("plant", False)]}}})
        self.assertFalse(crc.params(d)["GET /x"]["query:plant"]["required"])

    def test_경로_파라미터는_담지_않는다(self):
        # 명세가 항상 필수로 못박아 뒤집힐 수 없다.
        d = pdoc({"/x/{id}": {"parameters": [{"name": "id", "in": "path",
                                              "required": True}],
                              "get": {}}})
        self.assertEqual(crc.params(d)["GET /x/{id}"], {})

    def test_파라미터가_없는_오퍼레이션도_빈_칸으로_담긴다(self):
        # 그래야 「이 오퍼레이션이 원래 있었나」를 물을 수 있다.
        self.assertEqual(crc.params(pdoc({"/x": {"get": {}}})), {"GET /x": {}})

    def test_메서드가_아닌_키는_오퍼레이션이_아니다(self):
        d = pdoc({"/x": {"summary": "설명", "servers": [], "get": {}}})
        self.assertEqual(list(crc.params(d)), ["GET /x"])


class ParamPromotionTest(unittest.TestCase):
    """ⓐ `required: false`(또는 없음) → `true` 승격 — ⛔ 안 보내던 쪽이 400."""

    def test_인라인_승격은_차단이다(self):
        old = pdoc({"/x": {"post": {"parameters": [hdr("X-Worker-No", False)]}}})
        new = pdoc({"/x": {"post": {"parameters": [hdr("X-Worker-No", True)]}}})
        b, n = diff(old, new)
        self.assertEqual(n, [])
        self.assertEqual(len(b), 1)
        self.assertIn("header:X-Worker-No", b[0])
        self.assertIn("required 로 올랐다", b[0])

    def test_required_키가_아예_없던_것도_false_로_읽는다(self):
        old = pdoc({"/x": {"post": {"parameters": [
            {"name": "plant", "in": "query", "schema": {"type": "string"}}]}}})
        new = pdoc({"/x": {"post": {"parameters": [qry("plant", True)]}}})
        b, _ = diff(old, new)
        self.assertEqual(len(b), 1)
        self.assertIn("required 로 올랐다", b[0])

    def test_안_바뀌면_아무것도_안_낸다(self):
        d = pdoc({"/x": {"post": {"parameters": [hdr("X-Worker-No", True),
                                                 qry("plant", False)]}}})
        self.assertEqual(diff(d, d), ([], []))

    def test_required_제거는_경보다(self):
        old = pdoc({"/x": {"post": {"parameters": [hdr("X-Worker-No", True)]}}})
        new = pdoc({"/x": {"post": {"parameters": [hdr("X-Worker-No", False)]}}})
        b, n = diff(old, new)
        self.assertEqual(b, [])
        self.assertEqual(len(n), 1)
        self.assertIn("required 에서 빠졌다", n[0])

    def test_ref_를_갈아_끼운_승격을_잡는다_350_회귀(self):
        # ⛔ `#350` 의 실물 모양 — 참조 이름만 바뀌고 헤더 이름은 그대로였다.
        comps = {"WorkerNo": WORKER_REQ, "WorkerNoOptional": WORKER_OPT}
        old = pdoc({"/logistics/stock-transfers":
                    {"post": {"parameters": [pref("WorkerNoOptional")]}}}, comps)
        new = pdoc({"/logistics/stock-transfers":
                    {"post": {"parameters": [pref("WorkerNo")]}}}, comps)
        b, n = diff(old, new)
        self.assertEqual(n, [])
        self.assertEqual(len(b), 1)
        self.assertIn("POST /logistics/stock-transfers", b[0])
        self.assertIn("header:X-Worker-No", b[0])
        self.assertIn("required 로 올랐다", b[0])
        self.assertIn("참조 WorkerNoOptional → WorkerNo", b[0])

    def test_참조_이름만_바뀌고_필수가_같으면_안_잡는다(self):
        # 이름만 갈아 끼운 것은 계약이 요구하는 바가 같다 — 깨질 코드가 없다.
        comps = {"WorkerNo": WORKER_REQ, "귀속사번": dict(WORKER_REQ)}
        old = pdoc({"/x": {"post": {"parameters": [pref("WorkerNo")]}}}, comps)
        new = pdoc({"/x": {"post": {"parameters": [pref("귀속사번")]}}}, comps)
        self.assertEqual(diff(old, new), ([], []))

    def test_인라인에서_ref_로_바꾸며_승격해도_잡는다(self):
        comps = {"WorkerNo": WORKER_REQ}
        old = pdoc({"/x": {"post": {"parameters": [hdr("X-Worker-No", False)]}}}, comps)
        new = pdoc({"/x": {"post": {"parameters": [pref("WorkerNo")]}}}, comps)
        b, _ = diff(old, new)
        self.assertEqual(len(b), 1)
        self.assertIn("참조 인라인 → WorkerNo", b[0])

    def test_경로_레벨_승격은_그_경로의_모든_메서드에서_잡힌다(self):
        old = pdoc({"/x": {"parameters": [qry("plant", False)], "get": {}, "post": {}}})
        new = pdoc({"/x": {"parameters": [qry("plant", True)], "get": {}, "post": {}}})
        b, n = diff(old, new)
        self.assertEqual(n, [])
        self.assertEqual(len(b), 2)
        self.assertTrue(any("GET /x" in line for line in b))
        self.assertTrue(any("POST /x" in line for line in b))

    def test_메서드가_경로_레벨을_덮어_필수를_풀면_경보다(self):
        old = pdoc({"/x": {"parameters": [qry("plant", True)], "get": {}}})
        new = pdoc({"/x": {"parameters": [qry("plant", True)],
                           "get": {"parameters": [qry("plant", False)]}}})
        b, n = diff(old, new)
        self.assertEqual(b, [])
        self.assertEqual(len(n), 1)
        self.assertIn("required 에서 빠졌다", n[0])


class ParamNewTest(unittest.TestCase):
    """ⓑ 파라미터 «신설»이 `required: true` 인 것."""

    def test_있던_오퍼레이션에_필수_파라미터를_더하면_차단이다(self):
        old = pdoc({"/x": {"post": {}}})
        new = pdoc({"/x": {"post": {"parameters": [hdr("X-Worker-No", True)]}}})
        b, n = diff(old, new)
        self.assertEqual(n, [])
        self.assertEqual(len(b), 1)
        self.assertIn("필수 파라미터가 새로 생겼다", b[0])

    def test_선택_파라미터_신설은_안_잡는다(self):
        old = pdoc({"/x": {"post": {}}})
        new = pdoc({"/x": {"post": {"parameters": [qry("plant", False)]}}})
        self.assertEqual(diff(old, new), ([], []))

    def test_새_오퍼레이션의_필수_파라미터는_안_잡는다(self):
        # 없던 오퍼레이션으로는 아무도 코드를 만들지 않았다(스키마 축과 같은 기준).
        old = pdoc({"/x": {"get": {}}})
        new = pdoc({"/x": {"get": {},
                           "post": {"parameters": [hdr("X-Worker-No", True)]}}})
        self.assertEqual(diff(old, new), ([], []))

    def test_새_경로_전체는_안_잡는다(self):
        old = pdoc({"/x": {"get": {}}})
        new = pdoc({"/x": {"get": {}},
                    "/y": {"post": {"parameters": [hdr("X-Worker-No", True)]}}})
        self.assertEqual(diff(old, new), ([], []))

    def test_ref_로_더한_필수_파라미터도_참조_이름을_적는다(self):
        old = pdoc({"/x": {"post": {}}}, {"WorkerNo": WORKER_REQ})
        new = pdoc({"/x": {"post": {"parameters": [pref("WorkerNo")]}}},
                   {"WorkerNo": WORKER_REQ})
        b, _ = diff(old, new)
        self.assertEqual(len(b), 1)
        self.assertIn("(참조 WorkerNo)", b[0])


class ParamRenameTest(unittest.TestCase):
    """ⓒ 기존 «필수» 파라미터의 이름·위치(`in`) 변경."""

    def test_이름이_바뀌면_차단이다(self):
        old = pdoc({"/x": {"post": {"parameters": [hdr("X-Worker-No", True)]}}})
        new = pdoc({"/x": {"post": {"parameters": [hdr("X-Employee-No", True)]}}})
        b, n = diff(old, new)
        self.assertEqual(n, [])
        self.assertEqual(len(b), 1)
        self.assertIn("이름이 바뀌었다", b[0])
        self.assertIn("header:X-Worker-No → header:X-Employee-No", b[0])

    def test_위치가_바뀌면_차단이다(self):
        old = pdoc({"/x": {"post": {"parameters": [qry("workerNo", True)]}}})
        new = pdoc({"/x": {"post": {"parameters": [hdr("workerNo", True)]}}})
        b, n = diff(old, new)
        self.assertEqual(n, [])
        self.assertEqual(len(b), 1)
        self.assertIn("위치가 바뀌었다", b[0])
        self.assertIn("query:workerNo → header:workerNo", b[0])

    def test_선택_파라미터의_이름_변경은_안_잡는다(self):
        old = pdoc({"/x": {"post": {"parameters": [hdr("X-A", False)]}}})
        new = pdoc({"/x": {"post": {"parameters": [hdr("X-B", False)]}}})
        self.assertEqual(diff(old, new), ([], []))

    def test_짝이_모호하면_이름_변경으로_짓지_않는다(self):
        # 2:2 로 남으면 무엇이 무엇으로 바뀐 것인지 «알 수 없다» — 지어내지 않는다.
        old = pdoc({"/x": {"post": {"parameters": [qry("a", True), qry("b", True)]}}})
        new = pdoc({"/x": {"post": {"parameters": [qry("c", True), qry("d", True)]}}})
        b, n = diff(old, new)
        self.assertEqual(len(b), 2)          # 신설 2
        self.assertEqual(len(n), 2)          # 사라짐 2
        self.assertTrue(all("새로 생겼다" in line for line in b))
        self.assertTrue(all("사라졌다" in line for line in n))

    def test_필수_파라미터가_그냥_사라지면_경보다(self):
        old = pdoc({"/x": {"post": {"parameters": [hdr("X-Worker-No", True)]}}})
        new = pdoc({"/x": {"post": {}}})
        b, n = diff(old, new)
        self.assertEqual(b, [])
        self.assertEqual(len(n), 1)
        self.assertIn("필수 파라미터가 사라졌다", n[0])


class ParamComponentRippleTest(unittest.TestCase):
    """④ `components.parameters.<이름>` 자체가 바뀐 자리 — 파급을 함께 낸다.

    한 곳을 고치면 몇 개가 깨지는지가 이 축의 값어치다. 오퍼레이션마다 한 줄씩
    내면 그 수가 «줄 개수»에 묻힌다 — 공용 파라미터 한 줄로 굴려 수를 앞세운다.
    """

    PATHS = {f"/x{i}": {"post": {"parameters": [pref("WorkerNo")]}} for i in range(5)}

    def test_공용_파라미터_승격은_한_줄_더하기_파급_수다(self):
        old = pdoc(self.PATHS, {"WorkerNo": WORKER_OPT})
        new = pdoc(self.PATHS, {"WorkerNo": WORKER_REQ})
        b, n = diff(old, new)
        self.assertEqual(n, [])
        self.assertEqual(len(b), 1, f"오퍼레이션마다 중복해서 냈다: {b}")
        self.assertIn("공용 파라미터 WorkerNo(header:X-Worker-No)", b[0])
        self.assertIn("required 로 올랐다", b[0])
        self.assertIn("참조 오퍼레이션 5곳", b[0])

    def test_파급_수는_실제_참조_수를_센다(self):
        paths = dict(self.PATHS)
        paths["/other"] = {"post": {"parameters": [hdr("X-Worker-No", True)]}}
        old = pdoc(paths, {"WorkerNo": WORKER_OPT})
        new = pdoc(paths, {"WorkerNo": WORKER_REQ})
        b, _ = diff(old, new)
        self.assertIn("참조 오퍼레이션 5곳", b[0])   # 인라인으로 적은 /other 는 안 센다

    def test_공용_파라미터_필수_해제는_경보다(self):
        old = pdoc(self.PATHS, {"WorkerNo": WORKER_REQ})
        new = pdoc(self.PATHS, {"WorkerNo": WORKER_OPT})
        b, n = diff(old, new)
        self.assertEqual(b, [])
        self.assertEqual(len(n), 1)
        self.assertIn("required 에서 빠졌다", n[0])
        self.assertIn("참조 오퍼레이션 5곳", n[0])

    def test_공용_파라미터의_이름_변경도_한_줄_더하기_파급_수다(self):
        old = pdoc(self.PATHS, {"WorkerNo": WORKER_REQ})
        new = pdoc(self.PATHS, {"WorkerNo": dict(WORKER_REQ, name="X-Employee-No")})
        b, n = diff(old, new)
        self.assertEqual(n, [])
        self.assertEqual(len(b), 1, f"오퍼레이션마다 중복해서 냈다: {b}")
        self.assertIn("이름·위치가 바뀌었다", b[0])
        self.assertIn("header:X-Worker-No → header:X-Employee-No", b[0])
        self.assertIn("참조 오퍼레이션 5곳", b[0])

    def test_공용_파라미터가_안_바뀌면_아무것도_안_낸다(self):
        d = pdoc(self.PATHS, {"WorkerNo": WORKER_REQ})
        self.assertEqual(diff(d, d), ([], []))

    def test_아무도_안_가리키는_공용_파라미터는_경보로_내린다(self):
        # 파급 0 이면 깨질 코드가 없다 — ⛔ 로 울면 거짓 경보다.
        # 실측 — `shipment-04제품출하.json · IfMatchVersionOptional` 이 0곳이다.
        old = pdoc({"/x": {"post": {}}}, {"WorkerNo": WORKER_OPT})
        new = pdoc({"/x": {"post": {}}}, {"WorkerNo": WORKER_REQ})
        b, n = diff(old, new)
        self.assertEqual(b, [])
        self.assertEqual(len(n), 1)
        self.assertIn("참조 오퍼레이션 0곳 — 아무도 안 가리킨다", n[0])

    def test_새로_생긴_공용_파라미터는_안_센다(self):
        old = pdoc({"/x": {"post": {}}}, {})
        new = pdoc({"/x": {"post": {}}}, {"WorkerNo": WORKER_REQ})
        self.assertEqual(diff(old, new), ([], []))

    def test_오퍼레이션이_참조를_갈아_끼운_것은_공용_행에_묻히지_않는다(self):
        # 공용 `WorkerNo` 도 바뀌고 어떤 오퍼레이션은 참조 자체를 갈아 끼운 경우 —
        # 둘은 «다른 사건»이라 각각 나와야 한다.
        old = pdoc({"/a": {"post": {"parameters": [pref("WorkerNo")]}},
                    "/b": {"post": {"parameters": [pref("WorkerNoOptional")]}}},
                   {"WorkerNo": WORKER_OPT, "WorkerNoOptional": WORKER_OPT})
        new = pdoc({"/a": {"post": {"parameters": [pref("WorkerNo")]}},
                    "/b": {"post": {"parameters": [pref("WorkerNo")]}}},
                   {"WorkerNo": WORKER_REQ, "WorkerNoOptional": WORKER_OPT})
        b, n = diff(old, new)
        self.assertEqual(n, [])
        self.assertEqual(len(b), 2, b)
        self.assertTrue(any("공용 파라미터 WorkerNo" in line and "1곳" not in line
                            for line in b))
        self.assertTrue(any("POST /b" in line and
                            "참조 WorkerNoOptional → WorkerNo" in line for line in b))


class ParamUnresolvedTest(unittest.TestCase):
    """판정하지 못한 것을 통과시키지 않는다 — 스키마 축의 「미상은 ⛔」와 같은 규약."""

    def test_풀_수_없는_참조로_바뀌면_판정_불가로_막는다(self):
        old = pdoc({"/x": {"post": {"parameters": [pref("WorkerNo")]}}},
                   {"WorkerNo": WORKER_REQ})
        new = pdoc({"/x": {"post": {"parameters": [pref("WorkerNo")]}}}, {})
        b, n = diff(old, new)
        self.assertEqual(n, [])
        self.assertEqual(len(b), 1, b)
        self.assertIn("참조를 풀지 못했다", b[0])

    def test_기준에도_지금도_못_풀면_변화가_아니다(self):
        d = pdoc({"/x": {"post": {"parameters": [pref("Missing")]}}}, {})
        self.assertEqual(diff(d, d), ([], []))


class RealArtifactTest(unittest.TestCase):
    """저장소 실물 — 전이 폐쇄가 실제로 미상을 없애는가."""

    def test_계약_7벌에_미상이_없다(self):
        import glob
        import json
        files = sorted(glob.glob(os.path.join(crc.CONTRACTS_DIR, "*.json")))
        self.assertGreaterEqual(len(files), 7)
        unknown = []
        for f in files:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
            table = crc.roles(d)
            for name in (d.get("components", {}).get("schemas") or {}):
                if crc.role_of(name, table) == "미상":
                    unknown.append(f"{os.path.basename(f)} · {name}")
        self.assertEqual(unknown, [], f"방향을 못 매긴 스키마 {len(unknown)}개")

    def test_계약_7벌에_못_푼_파라미터가_없다(self):
        import glob
        import json
        files = sorted(glob.glob(os.path.join(crc.CONTRACTS_DIR, "*.json")))
        self.assertGreaterEqual(len(files), 7)
        unresolved, total = [], 0
        for f in files:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
            for opkey, bucket in crc.params(d).items():
                for key, prm in bucket.items():
                    total += 1
                    if prm["required"] is None:
                        unresolved.append(f"{os.path.basename(f)} · {opkey} · {key}")
        self.assertEqual(unresolved, [], f"참조를 못 푼 파라미터 {len(unresolved)}개")
        self.assertGreater(total, 1000, "파라미터를 훑지 못하고 있다")

    def test_계약_7벌_자기_자신_대조는_0건이다(self):
        import glob
        import json
        for f in sorted(glob.glob(os.path.join(crc.CONTRACTS_DIR, "*.json"))):
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
            b, n, _ = crc.compare_params(os.path.basename(f), d, d)
            self.assertEqual((b, n), ([], []), os.path.basename(f))


if __name__ == "__main__":
    unittest.main(verbosity=2)
