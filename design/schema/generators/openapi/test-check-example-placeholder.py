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


class ParameterExampleReviewTest(unittest.TestCase):
    """#471 리뷰: 명시 enum 우선 및 예시 위치별 스키마 적용."""

    def check(self, parameter):
        doc = {"paths": {"/test": {"get": {"parameters": [parameter]}}}}
        return ep.check_parameters(doc, "test.json")

    def parameter(self):
        return {
            "name": "statusCodes",
            "in": "query",
            "x-code-key": "CD-SHIPMENT-STATUS",
            "schema": {"type": "array", "items": {"type": "string"}},
        }

    def test_partial_enum_rejects_dictionary_value(self):
        for location in ("parameter", "schema", "items"):
            with self.subTest(location=location):
                parameter = self.parameter()
                parameter["schema"]["items"]["enum"] = ["CONFIRMED"]
                owner = {
                    "parameter": parameter,
                    "schema": parameter["schema"],
                    "items": parameter["schema"]["items"],
                }[location]
                owner["example"] = (
                    "UNCONFIRMED" if location == "items" else ["UNCONFIRMED"]
                )
                findings = self.check(parameter)
                self.assertEqual(len(findings), 1)
                self.assertIn("⑥ 자기 enum 밖", findings[0])

    def test_scalar_partial_enum_rejects_dictionary_value(self):
        parameter = {
            "name": "statusCode",
            "in": "query",
            "x-code-key": "CD-SHIPMENT-STATUS",
            "example": "UNCONFIRMED",
            "schema": {"type": "string", "enum": ["CONFIRMED"]},
        }
        self.assertIn("⑥ 자기 enum 밖", self.check(parameter)[0])

    def test_valid_examples_in_all_three_locations(self):
        for with_enum in (False, True):
            for location in ("parameter", "schema", "items"):
                with self.subTest(with_enum=with_enum, location=location):
                    parameter = self.parameter()
                    if with_enum:
                        parameter["schema"]["items"]["enum"] = ["CONFIRMED"]
                    owner = {
                        "parameter": parameter,
                        "schema": parameter["schema"],
                        "items": parameter["schema"]["items"],
                    }[location]
                    owner["example"] = (
                        "CONFIRMED" if location == "items" else ["CONFIRMED"]
                    )
                    self.assertEqual(self.check(parameter), [])

    def test_invalid_dictionary_examples_in_all_three_locations(self):
        for location in ("parameter", "schema", "items"):
            parameter = self.parameter()
            owner = {
                "parameter": parameter,
                "schema": parameter["schema"],
                "items": parameter["schema"]["items"],
            }[location]
            owner["example"] = "BAD" if location == "items" else ["BAD"]
            self.assertIn("③ 확정 그룹 밖", self.check(parameter)[0])

    def test_valid_parent_does_not_hide_invalid_item(self):
        parameter = self.parameter()
        parameter["example"] = ["CONFIRMED"]
        parameter["schema"]["example"] = ["CONFIRMED"]
        parameter["schema"]["items"]["example"] = "BAD"
        findings = self.check(parameter)
        self.assertEqual(len(findings), 1)
        self.assertIn("schema.items.example", findings[0])

    def test_array_examples_must_be_arrays(self):
        parameter = self.parameter()
        parameter["example"] = "CONFIRMED"
        self.assertIn("③ 확정 그룹 밖", self.check(parameter)[0])

    def test_item_exemption_does_not_exempt_invalid_parent(self):
        parameter = self.parameter()
        parameter["example"] = ["BAD"]
        parameter["schema"]["items"].update({"example": "BAD", "x-no-example": True})
        findings = self.check(parameter)
        self.assertEqual(len(findings), 1)
        self.assertIn("③ 확정 그룹 밖", findings[0])


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


class 스키마_자리도_운다(unittest.TestCase):
    """⛔ 「배열 사각을 닫았다」가 «절반만» 참이었다(2026-09-02 검증).

    in_enum() 에 배열 분기를 더한 것은 오탐을 막을 뿐이고, check_one 에는 «울릴
    규칙»이 없었다. 그래서 Printer.supportedDocumentTypeCodes.example 을
    ["LABEL"] 로 되돌려도 findings 가 0 이었다 — 검사기는 초록인데 구멍이 그대로다.
    ⑥ 규칙을 check_one 에도 두고, 그 회귀를 여기서 잠근다.
    """

    @staticmethod
    def one(prop):
        import json, os, tempfile
        doc = {"components": {"schemas": {"Printer": {"properties": {
            "supportedDocumentTypeCodes": prop}}}}}
        path = os.path.join(tempfile.mkdtemp(), "x.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False)
        return ep.check_one(path)

    def test_배열_example이_items_enum_밖이면_운다(self):
        # ⛔ 이것이 실제로 놓쳤던 자리다.
        out = self.one({"type": "array", "items": {"type": "string", "enum": ENUM9},
                        "example": ["LABEL"]})
        self.assertEqual(len(out), 1, out)
        self.assertIn("자기 enum 밖", out[0])

    def test_배열_example이_안이면_통과(self):
        out = self.one({"type": "array", "items": {"type": "string", "enum": ENUM9},
                        "example": ["PACKING_LABEL", "DELIVERY_LABEL"]})
        self.assertEqual(out, [])

    def test_enum이_없으면_안_운다(self):
        # 「enum 이 없다」와 「enum 이 있는데 밖」을 가른다 — 없으면 ⑥ 대상이 아니다.
        out = self.one({"type": "array", "items": {"type": "string"},
                        "example": ["아무거나"]})
        self.assertEqual([o for o in out if "자기 enum 밖" in o], [])

    def test_단수도_enum_밖이면_운다(self):
        out = self.one({"type": "string", "enum": ENUM9, "example": "LABEL"})
        self.assertEqual(len(out), 1, out)
        self.assertIn("자기 enum 밖", out[0])


class enum_of는_단수와_배열을_가른다(unittest.TestCase):
    def test_단수(self):
        self.assertEqual(ep.enum_of({"type": "string", "enum": ENUM9}), ENUM9)

    def test_배열은_items에서_꺼낸다(self):
        self.assertEqual(
            ep.enum_of({"type": "array", "items": {"type": "string", "enum": ENUM9}}), ENUM9)

    def test_없으면_None(self):
        self.assertIsNone(ep.enum_of({"type": "string"}))
        self.assertIsNone(ep.enum_of({"type": "array", "items": {"type": "string"}}))


class 단수는_그대로_본다(unittest.TestCase):
    """기존 동작이 안 깨졌는지 — 배열 갈래를 더하며 단수를 건드리지 않았다."""

    def test_enum_안(self):
        self.assertTrue(ep.in_enum({"type": "string", "enum": ENUM9}, "PACKING_LABEL"))

    def test_enum_밖(self):
        self.assertFalse(ep.in_enum({"type": "string", "enum": ENUM9}, "LABEL"))

    def test_enum이_없으면_False(self):
        self.assertFalse(ep.in_enum({"type": "string"}, "무엇이든"))


class GateTest(unittest.TestCase):
    def test_multiple_dictionary_keys_and_array_examples(self):
        prop = {"x-code-key": ["CD-EQUIPMENT-TYPE", "CD-INSTRUMENT-TYPE"]}
        expected = set(ep.dictionary_values()["CD-EQUIPMENT-TYPE"]) | set(ep.dictionary_values()["CD-INSTRUMENT-TYPE"])
        self.assertEqual(set(ep.known_values(prop)), expected)
        document = param_doc("statusCodes", ["CONFIRMED"], {
            "type": "array", "items": {"type": "string"}, "x-code-key": "CD-SHIPMENT-STATUS"})
        self.assertEqual(ep.check_parameters(document, "fixture.json"), [])
        document["paths"]["/app/document-issues/summary"]["get"]["parameters"][0]["example"] = ["WRONG"]
        self.assertTrue(ep.check_parameters(document, "fixture.json"))

    def test_confirmed_state_label_is_not_an_undecided_value(self):
        prop = {"type": "string", "x-code-key": "CD-SHIPMENT-STATUS",
                "description": "미확정(UNCONFIRMED)·확정·취소", "example": "UNCONFIRMED"}
        self.assertIn(prop["example"], ep.known_values(prop))

    def test_real_contracts_have_no_example_violations(self):
        import glob
        files = glob.glob(os.path.join(ep.CONTRACTS_DIR, "*.json"))
        self.assertEqual(len(files), 7)
        for path in files:
            with self.subTest(path=path):
                self.assertEqual(ep.check_one(path), [])

    def test_lot_example_is_preserved_despite_other_numbering_pattern_being_undecided(self):
        import json
        path = os.path.join(ep.CONTRACTS_DIR, "logistics-01자재창고.json")
        with open(path, encoding="utf-8") as stream:
            prop = json.load(stream)["components"]["schemas"]["LotCreate"]["properties"]["lotNo"]
        self.assertEqual(len(prop["example"]), 34)
        self.assertTrue(prop["example"].isdigit())
        self.assertNotIn("x-no-example", prop)
        self.assertFalse(any("LotCreate.lotNo" in line for line in ep.check_one(path)))

    def test_cli_rejects_invalid_example_and_accepts_valid_example(self):
        import json
        import subprocess
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            for example, expected in (("값", 1), ("READY", 0)):
                with self.subTest(example=example):
                    doc = {"components": {"schemas": {"Entry": {"properties": {
                        "statusCode": {"type": "string", "enum": ["READY"], "example": example}
                    }}}}}
                    path.write_text(json.dumps(doc), encoding="utf-8")
                    result = subprocess.run([sys.executable, ep.__file__, str(path)],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, expected, result.stdout + result.stderr)

    def test_missing_default_contracts_fails(self):
        from unittest.mock import patch
        with patch.object(sys, "argv", [ep.__file__]), patch.object(ep.glob, "glob", return_value=[]):
            self.assertEqual(ep.main(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
