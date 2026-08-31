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
    """판정표 네 칸 — 등급 정본은 uiux-client-handoff/SKILL.md 「변경 통지 ⛔/⚠」."""

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
