#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# check-example-placeholder.py 의 단위 테스트. 표준 라이브러리만 쓴다(저장소 관행).
#
# ⛔ 이 파일이 잠그는 사고는 하나다 — **검사기가 초록인데 구멍이 있었다.**
# 2026-09-02 실측에서 사각지대가 «둘» 드러났다.
#
#   ① 쿼리 파라미터        check_one() 이 components.schemas 만 훑어 paths 아래의
#                          parameters 가 통째로 밖이었다. GET /app/document-issues/summary
#                          의 documentTypeCode example 이 "LABEL" 이었는데, 그 값은
#                          같은 이름의 enum 9종 어디에도 없다. 검사기는 초록이었다.
#   ② 복수형 …Codes        필터가 endswith("Code","No") 라 «배열» 자리를 안 봤다.
#                          Printer.supportedDocumentTypeCodes 의 example ["LABEL"] 이
#                          같은 문제인데 역시 초록이었다.
#
# 둘 다 「example 도 구현이 읽는다」(omf-mes#185·#191)는 이 검사기의 존재 이유를
# 정면으로 비껴간 자리다. 자리마다 표본을 하나씩 잠근다.
import importlib
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ep = importlib.import_module("check-example-placeholder")

ENUM9 = ["MATERIAL_LOT_LABEL", "GOODS_ISSUE_QR", "PACKING_LABEL", "DELIVERY_LABEL"]


def param_doc(name, example, schema):
    """paths 아래 쿼리 파라미터 하나만 가진 최소 문서."""
    return {"paths": {"/app/document-issues/summary": {"get": {
        "operationId": "getSummary",
        "parameters": [{"name": name, "in": "query",
                        "example": example, "schema": schema}]}}}}


class 쿼리_파라미터를_본다(unittest.TestCase):
    """① 사각지대 — components.schemas 밖."""

    def test_enum_밖이면_잡는다(self):
        # ⛔ 이것이 실제로 놓쳤던 자리다 — example "LABEL" 은 enum 9종에 없다.
        d = param_doc("documentTypeCode", "LABEL",
                      {"type": "string", "enum": ENUM9})
        out = ep.check_parameters(d, "app-공통.json")
        self.assertEqual(len(out), 1, out)
        self.assertIn("자기 enum 밖", out[0])
        self.assertIn("?documentTypeCode", out[0])

    def test_enum_안이면_통과(self):
        d = param_doc("documentTypeCode", "PACKING_LABEL",
                      {"type": "string", "enum": ENUM9})
        self.assertEqual(ep.check_parameters(d, "app-공통.json"), [])

    def test_자리채움_상수를_잡는다(self):
        d = param_doc("statusCode", "값", {"type": "string"})
        out = ep.check_parameters(d, "x.json")
        self.assertEqual(len(out), 1, out)
        self.assertIn("자리채움 상수", out[0])

    def test_Code로_안_끝나면_안_본다(self):
        # 범위를 넓히지 않는다 — 이름 규칙 밖은 omf-mes#191 B-2 소관이다.
        d = param_doc("keyword", "값", {"type": "string"})
        self.assertEqual(ep.check_parameters(d, "x.json"), [])

    def test_example이_없으면_안_본다(self):
        d = {"paths": {"/x": {"get": {"parameters": [
            {"name": "statusCode", "in": "query", "schema": {"type": "string"}}]}}}}
        self.assertEqual(ep.check_parameters(d, "x.json"), [])

    def test_경로_공용_parameters도_본다(self):
        # OpenAPI 는 메서드 밖 「parameters」 에도 파라미터를 둘 수 있다.
        d = {"paths": {"/x/{id}": {"parameters": [
            {"name": "typeCode", "in": "path", "example": "값",
             "schema": {"type": "string"}}]}}}
        out = ep.check_parameters(d, "x.json")
        self.assertEqual(len(out), 1, out)
        self.assertIn("자리채움 상수", out[0])


class 복수형_배열을_본다(unittest.TestCase):
    """② 사각지대 — endswith("Code") 가 «Codes» 를 놓쳤다."""

    def test_items_enum_밖이면_False(self):
        # ⛔ Printer.supportedDocumentTypeCodes 가 이 형태였다.
        prop = {"type": "array", "items": {"type": "string", "enum": ENUM9}}
        self.assertFalse(ep.in_enum(prop, ["LABEL"]))

    def test_items_enum_안이면_True(self):
        prop = {"type": "array", "items": {"type": "string", "enum": ENUM9}}
        self.assertTrue(ep.in_enum(prop, ["PACKING_LABEL", "DELIVERY_LABEL"]))

    def test_하나만_밖이어도_False(self):
        prop = {"type": "array", "items": {"type": "string", "enum": ENUM9}}
        self.assertFalse(ep.in_enum(prop, ["PACKING_LABEL", "LABEL"]))

    def test_items에_enum이_없으면_False(self):
        prop = {"type": "array", "items": {"type": "string"}}
        self.assertFalse(ep.in_enum(prop, ["아무거나"]))

    def test_배열인데_example이_목록이_아니면_False(self):
        prop = {"type": "array", "items": {"type": "string", "enum": ENUM9}}
        self.assertFalse(ep.in_enum(prop, "PACKING_LABEL"))


class 단수는_그대로_본다(unittest.TestCase):
    """기존 동작이 안 깨졌는지 — 배열 갈래를 더하며 단수를 건드리지 않았다."""

    def test_enum_안(self):
        self.assertTrue(ep.in_enum({"type": "string", "enum": ENUM9}, "PACKING_LABEL"))

    def test_enum_밖(self):
        self.assertFalse(ep.in_enum({"type": "string", "enum": ENUM9}, "LABEL"))

    def test_enum이_없으면_False(self):
        self.assertFalse(ep.in_enum({"type": "string"}, "무엇이든"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
