#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-openapi.py 의 단위 테스트. 표준 라이브러리만 쓴다."""
import io, os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib
verify = importlib.import_module("verify-openapi")

SQL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "docs", "research", "2026-07-23-데이터모델링",
                   "mes_postgresql_physical_model.sql")


class ParseSqlTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tables = verify.parse_sql(SQL)

    def test_창고_테이블을_찾는다(self):
        self.assertIn("mdm.warehouse", self.tables)

    def test_감사컬럼을_제외한_컬럼이_10개다(self):
        cols = self.tables["mdm.warehouse"]["columns"]
        self.assertEqual(len(cols), 10)

    def test_필수여부를_읽는다(self):
        cols = self.tables["mdm.warehouse"]["columns"]
        self.assertTrue(cols["warehouse_code"]["not_null"])
        self.assertFalse(cols["partner_id"]["not_null"])

    def test_도메인_타입을_읽는다(self):
        cols = self.tables["mdm.warehouse"]["columns"]
        self.assertEqual(cols["warehouse_code"]["type"], "app.code_t")

    def test_유일제약을_읽는다(self):
        cons = self.tables["mdm.warehouse"]["constraints"]
        uq = [c for c in cons if c["kind"] == "UNIQUE"]
        self.assertEqual(len(uq), 1)
        self.assertEqual(uq[0]["columns"], ["plant_id", "warehouse_code"])

    def test_CHECK제약을_읽는다(self):
        cons = self.tables["mdm.warehouse"]["constraints"]
        ck = [c for c in cons if c["kind"] == "CHECK"]
        self.assertEqual([c["name"] for c in ck], ["ck_external_warehouse_partner"])

    def test_테이블_수가_129내외다(self):
        self.assertGreater(len(self.tables), 120)


if __name__ == "__main__":
    unittest.main(verbosity=2)
