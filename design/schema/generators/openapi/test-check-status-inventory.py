#!/usr/bin/env python3
"""상태 인벤토리의 위치 집계·분류·실패 게이트 회귀 시험."""

import contextlib
import importlib
import io
import json
import tempfile
import unittest
from pathlib import Path

MODULE = importlib.import_module("check-status-inventory")
DICTIONARY = {"CD-TEST": {"owner": "registry-system", "values": {"READY"}}}


class StatusInventoryTest(unittest.TestCase):
    def schema(self, **overrides):
        return {
            "type": "string",
            "description": "상태",
            "x-code-key": "CD-TEST",
            **overrides,
        }

    def rows(self, schema):
        return MODULE.inventory({"properties": {"statusCode": schema}}, DICTIONARY)

    def test_dictionary_without_enum_is_classified(self):
        row = self.rows(self.schema())[0]
        self.assertEqual(row["owners"], ["registry-system"])
        self.assertEqual(row["values"], {"CD-TEST": ["READY"]})
        self.assertEqual(row["problems"], [])
        self.assertIsNone(row["enum"])

    def test_exclusion_is_not_claimed_as_resolved(self):
        row = self.rows(
            {"description": "독립 상태 없음", "x-no-code-key": "업무 축 보류"}
        )[0]
        self.assertEqual(row["problems"], [])
        self.assertEqual(row["exclusion_reason"], "업무 축 보류")
        self.assertEqual(row["owners"], [])

    def test_missing_description_and_empty_reason_fail(self):
        self.assertEqual(
            self.rows({"description": " ", "x-no-code-key": " "})[0]["problems"],
            ["설명 누락", "분류 누락"],
        )

    def test_enum_alone_is_not_a_dictionary_decision(self):
        row = self.rows({"description": "상태", "enum": ["READY"]})[0]
        self.assertIn("분류 누락", row["problems"])

    def test_unknown_and_conflicting_keys_fail(self):
        self.assertTrue(
            self.rows(self.schema(**{"x-code-key": "CD-MISSING"}))[0]["problems"]
        )
        self.assertTrue(
            self.rows(self.schema(**{"x-no-code-key": "제외"}))[0]["problems"]
        )

    def test_inline_array_composition_and_parameter_are_counted(self):
        document = {
            "paths": {
                "/test": {
                    "get": {
                        "parameters": [
                            {
                                "name": "statusCode",
                                "in": "query",
                                "schema": {"type": "string"},
                                "description": "필터",
                                "x-code-key": "CD-TEST",
                            }
                        ],
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "array",
                                            "items": {
                                                "allOf": [
                                                    {
                                                        "properties": {
                                                            "toStatusCode": self.schema(),
                                                            "itemCode": self.schema(),
                                                        }
                                                    }
                                                ]
                                            },
                                        }
                                    }
                                }
                            }
                        },
                    }
                }
            }
        }
        rows = MODULE.inventory(document, DICTIONARY)
        self.assertEqual([row["kind"] for row in rows], ["parameter", "property"])
        self.assertIn("/~1test/", rows[0]["pointer"])
        self.assertTrue(all(not row["problems"] for row in rows))

    def test_example_and_extension_objects_are_not_definitions(self):
        fake = {"properties": {"statusCode": {}}}
        document = {
            "example": fake,
            "examples": [fake],
            "default": fake,
            "x-note": fake,
        }
        self.assertEqual(MODULE.inventory(document, DICTIONARY), [])

    def test_local_reference_uses_description_without_expanding_occurrences(self):
        document = {
            "components": {"schemas": {"State": self.schema()}},
            "properties": {"statusCode": {"$ref": "#/components/schemas/State"}},
        }
        rows = MODULE.inventory(document, DICTIONARY)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["problems"], [])

    def test_invalid_and_cyclic_references_fail(self):
        for reference in [
            "#/missing",
            "https://example.test/schema",
            "#/properties/statusCode",
        ]:
            with self.subTest(reference=reference):
                self.assertTrue(self.rows({"$ref": reference})[0]["problems"])

    def test_allof_scalar_inherits_reference_annotations(self):
        document = {
            "components": {"schemas": {"State": self.schema()}},
            "properties": {
                "statusCode": {
                    "allOf": [{"$ref": "#/components/schemas/State"}, {"maxLength": 50}]
                }
            },
        }
        self.assertEqual(MODULE.inventory(document, DICTIONARY)[0]["problems"], [])

    def test_conflicting_allof_and_union_require_review(self):
        for schema in [
            {"allOf": [self.schema(), self.schema(**{"x-code-key": "CD-OTHER"})]},
            {"oneOf": [self.schema()]},
            {"anyOf": [self.schema()]},
        ]:
            self.assertTrue(self.rows(schema)[0]["problems"])

    def test_cli_failure_success_and_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            for schema, expected in [
                ({}, 1),
                ({"description": "독립 상태 없음", "x-no-code-key": "미사용"}, 0),
            ]:
                source = json.dumps({"properties": {"statusCode": schema}})
                path.write_text(source)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(MODULE.main([str(path)]), expected)
                self.assertEqual(path.read_text(), source)

    def test_current_contracts_have_no_gaps(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(MODULE.main([]), 0)


if __name__ == "__main__":
    unittest.main()
