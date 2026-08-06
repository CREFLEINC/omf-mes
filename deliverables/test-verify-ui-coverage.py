#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# verify-ui-coverage.py 의 단위 테스트. 표준 라이브러리만 쓴다.
import io, os, sys, unittest, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
cov = importlib.import_module("verify-ui-coverage")

W0607 = os.path.join(HERE, "..", "uiux", "2026-07-31-화면상세스펙-파일럿",
                     "W-06-07-창고Location마스터.md")


def _read(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


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


# 01 자재창고는 액션 소절 번호가 화면마다 다르고(§5-2·§5-5~§5-8), 액션 소절이
# §5 의 마지막 소절인 화면이 많다. 두 가정을 잠근다.
class Domain01Test(unittest.TestCase):
    E4 = os.path.join(HERE, "..", "uiux", "2026-08-05-화면상세스펙-확대4차")
    M0104 = os.path.join(E4, "M-01-04-자재위치확인.md")
    W0101 = os.path.join(HERE, "..", "uiux", "2026-07-31-화면상세스펙-파일럿",
                         "W-01-01-IQC수입검사판정.md")

    def test_소절_번호가_1이_아니어도_찾는다(self):
        # M-01-04 의 액션 표는 §5-7 이다. §5-1 로 고정하면 0건이 된다.
        rows = cov.extract_actions(self.M0104)
        self.assertEqual([r["action"] for r in rows],
                         ["스캔(암묵)", "직접 입력", "다음 스캔"])

    def test_액션_소절이_마지막이면_다음_장에서_끊는다(self):
        # 소절의 끝을 「다음 ###」으로만 찾으면 다음 제목이 `## §6` 이라
        # §6·§7·§8 의 표까지 삼킨다. M-01-04 는 3건이어야 한다.
        block = cov.find_action_block(_read(self.M0104))
        self.assertNotIn("§6", block)
        self.assertNotIn("EmptyState", block)

    def test_액션_표가_없으면_None_이다(self):
        # W-01-01 은 §5 에 판정 분기만 있고 액션 표가 없다.
        self.assertIsNone(cov.find_action_block(_read(self.W0101)))
        self.assertEqual(cov.extract_actions(self.W0101), [])

    def test_액션_표_없는_화면을_숨기지_않는다(self):
        missing = cov.screens_without_action_table(HERE, cov.SCREENS_01)
        self.assertEqual(sorted(missing),
                         ["M-01-01", "W-01-01", "W-01-02", "W-01-10"])

    def test_모바일_POP_화면ID도_읽는다(self):
        rows = cov.extract_actions(self.M0104)
        self.assertTrue(all(r["screen"] == "M-01-04" for r in rows))

    def test_기준정보_추출은_그대로다(self):
        # 공용 코드를 고쳤으므로 기존 도메인이 안 흔들리는지 함께 잠근다.
        rows = cov.extract_all(HERE)
        self.assertEqual(len(rows), 71)
        self.assertEqual(len({r["screen"] for r in rows}), 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
