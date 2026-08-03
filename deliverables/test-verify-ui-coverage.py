#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# verify-ui-coverage.py 의 단위 테스트. 표준 라이브러리만 쓴다.
import os, sys, unittest, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
cov = importlib.import_module("verify-ui-coverage")

W0607 = os.path.join(HERE, "..", "uiux", "2026-07-31-화면상세스펙-파일럿",
                     "W-06-07-창고Location마스터.md")


class ExtractActionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = cov.extract_actions(W0607)

    def test_화면ID를_파일명에서_읽는다(self):
        self.assertTrue(all(r["screen"] == "W-06-07" for r in self.rows))

    def test_액션을_일곱_뽑는다(self):
        self.assertEqual(len(self.rows), 7)

    def test_첫_액션이_창고_추가다(self):
        self.assertEqual(self.rows[0]["action"], "창고 추가")

    def test_굵은표기를_벗긴다(self):
        acts = [r["action"] for r in self.rows]
        self.assertIn("사용 중지", acts)
        self.assertIn("라벨 이미지 생성", acts)

    def test_구분선과_헤더행은_제외한다(self):
        acts = [r["action"] for r in self.rows]
        self.assertNotIn("액션", acts)
        self.assertFalse(any(a.startswith("---") for a in acts))

    def test_전체_화면을_모으면_10개다(self):
        rows = cov.extract_all(HERE)
        screens = sorted({r["screen"] for r in rows})
        self.assertEqual(len(screens), 10, screens)
        self.assertIn("W-CO-02", screens)
        self.assertIn("W-06-07", screens)
        self.assertNotIn("W-06-13", screens)
        self.assertNotIn("W-06-08", screens)


if __name__ == "__main__":
    unittest.main(verbosity=2)
