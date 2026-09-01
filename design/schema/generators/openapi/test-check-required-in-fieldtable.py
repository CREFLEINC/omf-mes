#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# check-required-in-fieldtable.py 의 단위 테스트. 표준 라이브러리만 쓴다(저장소 관행).
#
# ⛔ 이 검사기가 잠그는 사고 — `omf-mes#336`. `GoodsIssueCreate.sourceDocumentTypeCode`
# 가 required 인데 W-04-10 §4-B 필드표에 행 자체가 없었다. 표본 셋을 잠근다 —
# ① 필수인데 §4 소절에 컬럼 이름이 없으면 잡는다 ② 있으면 통과한다 ③ 응답
# 전용(읽기) 스키마의 required 는 보지 않는다(화면이 채울 의무가 없다).
import importlib
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
rift = importlib.import_module("check-required-in-fieldtable")


def contract(**schemas):
    return {"paths": {}, "components": {"schemas": dict(schemas)}}


def write_schema(table, required, properties=None):
    return {"x-source-table": table, "required": required,
            "properties": properties or {}}


class ToSnakeTest(unittest.TestCase):
    def test_camelCase_를_snake_case_로(self):
        self.assertEqual(rift.to_snake("sourceDocumentTypeCode"), "source_document_type_code")

    def test_이미_소문자면_그대로(self):
        self.assertEqual(rift.to_snake("id"), "id")


class ColumnsFromDocTest(unittest.TestCase):
    def test_요청_스키마의_필수_컬럼을_모은다(self):
        doc = contract(GoodsIssueCreate=write_schema(
            "logistics.goods_issue", ["sourceDocumentTypeCode"],
            {"sourceDocumentTypeCode": {"x-source-column": "source_document_type_code"}}))
        doc["paths"]["/logistics/goods-issues"] = {
            "post": {"requestBody": {"content": {"application/json": {
                "schema": {"$ref": "#/components/schemas/GoodsIssueCreate"}}}}}}
        out = rift.columns_from_doc(doc)
        self.assertEqual(out, {"logistics.goods_issue": {"source_document_type_code"}})

    def test_x_source_column_이_없으면_camel을_snake으로_대체한다(self):
        doc = contract(GoodsIssueCreate=write_schema(
            "logistics.goods_issue", ["sourceWarehouseId"]))
        doc["paths"]["/x"] = {"post": {"requestBody": {"content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/GoodsIssueCreate"}}}}}}
        out = rift.columns_from_doc(doc)
        self.assertEqual(out, {"logistics.goods_issue": {"source_warehouse_id"}})

    def test_응답_전용_스키마는_보지_않는다(self):
        doc = contract(GoodsIssue=write_schema(
            "logistics.goods_issue", ["sourceDocumentTypeCode"]))
        doc["paths"]["/x"] = {"get": {"responses": {"200": {"content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/GoodsIssue"}}}}}}}
        self.assertEqual(rift.columns_from_doc(doc), {})

    def test_x_source_table이_없으면_보지_않는다(self):
        doc = contract(Foo={"required": ["barCode"], "properties": {}})
        doc["paths"]["/x"] = {"post": {"requestBody": {"content": {"application/json": {
            "schema": {"$ref": "#/components/schemas/Foo"}}}}}}
        self.assertEqual(rift.columns_from_doc(doc), {})


class FieldSectionsTest(unittest.TestCase):
    def test_소절_제목의_백틱_테이블을_찾는다(self):
        text = (
            "## §4. 필드\n\n"
            "### §4-B. 기타 출고 `logistics.goods_issue`\n\n"
            "내용\n\n"
            "## §5. 액션\n"
        )
        out = rift.field_sections(text)
        self.assertEqual(len(out), 1)
        tables, body = out[0]
        self.assertEqual(tables, ["logistics.goods_issue"])
        self.assertIn("내용", body)
        self.assertNotIn("§5", body)

    def test_다음_소절_전에서_끊는다(self):
        text = (
            "### §4-A. 승인 요청 `app.approval_request`\n\nA 내용\n\n"
            "### §4-B. 기타 출고 `logistics.goods_issue`\n\nB 내용\n"
        )
        out = rift.field_sections(text)
        self.assertEqual(len(out), 2)
        self.assertIn("A 내용", out[0][1])
        self.assertNotIn("B 내용", out[0][1])

    def test_백틱_테이블이_없는_소절은_건너뛴다(self):
        text = "### §4. 필드\n\n표 없음\n"
        self.assertEqual(rift.field_sections(text), [])

    def test_상위_헤딩에서도_끊는다(self):
        # §4-X 다음 소절이 없어도 「## §5」 같은 상위 헤딩이 오면 거기서 끊는다.
        text = (
            "### §4-B. 기타 출고 `logistics.goods_issue`\n\n본문\n\n"
            "## §5. 액션·상태\n\n딴 내용\n"
        )
        tables, body = rift.field_sections(text)[0]
        self.assertIn("본문", body)
        self.assertNotIn("딴 내용", body)


class IntegrationTest(unittest.TestCase):
    """실제 계약·스펙을 대상으로 한 회귀 표본 — omf-mes#336 이 잡은 자리가 지금은 없다."""

    def test_소스문서_타입코드는_W_04_10에서_더이상_결손이_아니다(self):
        table_required = rift.required_columns_by_table()
        cols = table_required.get("logistics.goods_issue", set())
        self.assertIn("source_document_type_code", cols)

        spec_path = os.path.join(
            HERE, "..", "..", "..", "wiki", "screens", "04", "W-04-10-제품폐기요청.md")
        with open(spec_path, encoding="utf-8") as f:
            text = f.read()
        gap_cols = []
        for tables, body in rift.field_sections(text):
            if "logistics.goods_issue" not in tables:
                continue
            for col in ("source_document_type_code", "source_document_id"):
                if col not in body:
                    gap_cols.append(col)
        self.assertEqual(gap_cols, [])


if __name__ == "__main__":
    unittest.main()
