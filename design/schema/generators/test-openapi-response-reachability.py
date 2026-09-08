#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""POP이 읽는 생산 LOT 순번 필드의 실제 응답 도달성을 검증한다."""
from __future__ import annotations

import json
import os
import unittest
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
OPENAPI = os.path.join(
    HERE,
    "..",
    "..",
    "wiki",
    "api-contracts",
    "openapi",
    "logistics-01자재창고.json",
)
SEQUENCE_FIELDS = {"workOrderSequenceNo", "workOrderLotCount"}


def _resolve_local_ref(document: dict[str, Any], ref: str) -> dict[str, Any]:
    """OpenAPI 문서 내부의 JSON Pointer 참조를 따라간다."""
    if not ref.startswith("#/"):
        raise ValueError(f"로컬 참조가 아니다: {ref}")

    current: Any = document
    for raw_part in ref[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        current = current[part]
    if not isinstance(current, dict):
        raise TypeError(f"객체 스키마를 가리키지 않는다: {ref}")
    return current


class ProductionLotSequenceReachabilityTest(unittest.TestCase):
    """목록·상세 응답 모두에서 LOT 순번 정보를 읽을 수 있어야 한다."""

    @classmethod
    def setUpClass(cls) -> None:
        with open(OPENAPI, encoding="utf-8") as openapi_file:
            cls.document = json.load(openapi_file)

    def test_lot_list_items에서_순번_필드에_도달한다(self) -> None:
        response_schema = self.document["paths"]["/trace/lots"]["get"]["responses"][
            "200"
        ]["content"]["application/json"]["schema"]
        item_ref = response_schema["properties"]["items"]["items"]["$ref"]
        lot_schema = _resolve_local_ref(self.document, item_ref)

        self.assertTrue(SEQUENCE_FIELDS <= lot_schema["properties"].keys())
        self.assertTrue(SEQUENCE_FIELDS <= set(lot_schema["required"]))

    def test_lot_detail에서도_같은_필드에_도달한다(self) -> None:
        detail_schema = self.document["components"]["schemas"]["LotDetailResponse"]
        lot_schema = _resolve_local_ref(
            self.document, detail_schema["properties"]["lot"]["$ref"]
        )

        self.assertTrue(SEQUENCE_FIELDS <= lot_schema["properties"].keys())

    def test_문서_진행현황에는_생산_lot_필드가_없다(self) -> None:
        progress_properties = self.document["components"]["schemas"][
            "DocumentProgressDetail"
        ]["properties"]

        self.assertTrue(SEQUENCE_FIELDS.isdisjoint(progress_properties))


if __name__ == "__main__":
    unittest.main(verbosity=2)
