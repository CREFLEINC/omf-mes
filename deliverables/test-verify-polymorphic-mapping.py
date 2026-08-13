#!/usr/bin/env python3
"""verify-polymorphic-mapping.py 단위 테스트.

⚠ 검사기를 테스트 없이 내지 않는다 — 03 트랙에서 새 검사기에 테스트를 붙이자마자
**세 번째 오탐**이 나왔다. 검사기는 「무엇을 잡느냐」보다 **「무엇을 안 잡느냐」**가
틀리기 쉽다.

여기서 특히 잠그는 것 — **다형 판별**이다. 이름만 보면 `itemTypeCode` + `itemId`
도 짝처럼 보이지만 다형이 아니다. 잘못 잡으면 8종이 오탐으로 쏟아진다.
"""
from __future__ import annotations

import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "poly", os.path.join(HERE, "verify-polymorphic-mapping.py")
)
poly = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(poly)


class SnakeTest(unittest.TestCase):
    def test_camel을_snake로(self):
        self.assertEqual(poly.snake("destination"), "destination")
        self.assertEqual(poly.snake("sourceDocument"), "source_document")
        self.assertEqual(poly.snake("workOrder"), "work_order")

    def test_첫글자가_대문자여도_앞에_밑줄이_안_붙는다(self):
        self.assertEqual(poly.snake("Target"), "target")


class PolymorphicTest(unittest.TestCase):
    """같은 이름의 테이블이 있으면 다형이 아니다 — 이 판별이 핵심이다."""

    TABLES = {"item", "location", "warehouse", "work_order", "lot",
              "equipment", "process", "handling_unit", "partner"}

    def test_같은_이름_테이블이_있으면_다형이_아니다(self):
        for base in ("item", "location", "warehouse", "workOrder",
                     "lot", "equipment", "process", "handlingUnit"):
            with self.subTest(base=base):
                self.assertFalse(poly.is_polymorphic(base, self.TABLES))

    def test_같은_이름_테이블이_없으면_다형이다(self):
        for base in ("destination", "target", "source", "sourceDocument",
                     "document", "successor"):
            with self.subTest(base=base):
                self.assertTrue(poly.is_polymorphic(base, self.TABLES))

    def test_snake_변환을_거쳐_비교한다(self):
        # workOrder 는 work_order 로 바꿔 봐야 잡힌다. 안 바꾸면 다형으로 오판한다.
        self.assertFalse(poly.is_polymorphic("workOrder", {"work_order"}))
        self.assertTrue(poly.is_polymorphic("workOrder", {"workorder"}))


class MappingTest(unittest.TestCase):
    def test_대응표가_두_갈래_이상이면_통과(self):
        self.assertTrue(poly.has_mapping({
            "description": "LOCATION → mdm.location · PARTNER → mdm.partner"}))

    def test_한_갈래뿐이면_대응표가_아니다(self):
        # 하나만 가리키면 애초에 다형일 이유가 없다 — 적다 만 것이다.
        self.assertFalse(poly.has_mapping({
            "description": "PARTNER → mdm.partner"}))

    def test_값_나열만으로는_통과하지_못한다(self):
        self.assertFalse(poly.has_mapping({
            "description": "LOCATION · PARTNER · PROCESS · WORK_ORDER"}))

    def test_x_internal_note_에_있어도_인정한다(self):
        self.assertTrue(poly.has_mapping({
            "description": "도착지 유형.",
            "x-internal-note": "A → mdm.location · B → mdm.partner"}))

    def test_설명이_비어_있으면_없는_것이다(self):
        self.assertFalse(poly.has_mapping({}))

    def test_스키마_점_테이블_꼴이_아니면_인정하지_않는다(self):
        # 「→ 거래처」처럼 한국어로만 적으면 어느 표인지 기계가 못 잇는다.
        self.assertFalse(poly.has_mapping({
            "description": "A → 거래처 · B → 위치"}))


class RealContractTest(unittest.TestCase):
    """실물 계약과 물리 모델로 돌려 계수를 잠근다."""

    def setUp(self):
        self.tables = poly.model_tables()
        self.hits = poly.scan(self.tables)

    def test_물리_모델_테이블이_읽힌다(self):
        self.assertGreater(len(self.tables), 100)
        self.assertIn("goods_issue", self.tables)

    def test_다형_이름은_여섯종이다(self):
        bases = {h["base"] for h in self.hits}
        self.assertEqual(bases, {"destination", "document", "source",
                                 "sourceDocument", "successor", "target"})

    def test_오탐이_섞이지_않는다(self):
        bases = {h["base"] for h in self.hits}
        for wrong in ("item", "location", "warehouse", "workOrder",
                      "lot", "equipment", "process", "handlingUnit"):
            self.assertNotIn(wrong, bases)

    def test_도착지는_대응표를_갖고_있다(self):
        # DR-013 으로 채운 곳. 여기가 깨지면 채운 것이 지워진 것이다.
        dest = [h for h in self.hits if h["base"] == "destination"]
        self.assertEqual(len(dest), 2)
        self.assertTrue(all(h["ok"] for h in dest))


if __name__ == "__main__":
    unittest.main(verbosity=2)
