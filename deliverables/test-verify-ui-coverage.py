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


# §5-1 표의 열 구성이 화면마다 다르다 — 대상 10개 중 9개는
# 「액션|위치|활성 조건|비고」 4열이지만 W-06-10 만 「액션|활성 조건|비고」
# 3열(위치 열이 없다). 열 위치를 고정 인덱스(cells[2]=활성 조건,
# cells[3]=비고)로 읽으면 W-06-10 에서 활성 조건과 비고가 뒤바뀐다.
# 이 클래스는 그 회귀를 잠근다 — 고정 인덱스 코드로는 실패하고
# 헤더 이름 기반 조회에서는 통과해야 한다.
class ColumnMappingRegressionTest(unittest.TestCase):
    W0610 = os.path.join(HERE, "..", "uiux", "2026-08-03-화면상세스펙-확대1차",
                          "W-06-10-연계동기화현황실패재처리.md")

    def test_3열_표에서_활성조건과_비고를_바르게_읽는다(self):
        # W-06-10 원문(3열): "| 조회 | **기간 지정됨** | 로그 규약 |"
        # 고정 인덱스(cells[2]) 로 읽으면 activation 대신 비고 텍스트가
        # condition 에 들어가고 note 는 항상 빈 문자열이 된다.
        rows = cov.extract_actions(self.W0610)
        row = next(r for r in rows if r["action"] == "조회")
        self.assertEqual(row["condition"], "기간 지정됨")
        self.assertEqual(row["note"], "로그 규약")

    def test_4열_표에서_활성조건과_비고를_바르게_읽는다(self):
        # W-06-07 원문(4열): "| 창고 추가 | 헤더 | 항상 | |"
        rows = cov.extract_actions(W0607)
        row = next(r for r in rows if r["action"] == "창고 추가")
        self.assertEqual(row["condition"], "항상")
        self.assertEqual(row["note"], "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
