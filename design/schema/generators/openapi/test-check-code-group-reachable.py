#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# check-code-group-reachable.py 의 단위 테스트. 표준 라이브러리만 쓴다(저장소 관행).
#
# ⛔ 이 검사기가 새로 잠그는 사고 — `omf-mes#336`. `GOODS_ISSUE_REASON` 이
# 공급사 반품(W-01-05)·자재 폐기(W-01-06) 요구서에는 있어 그룹 «단위»(①)로는
# 이미 초록이었는데, 같은 `logistics.goods_issue` 전표를 만드는 제품 폐기
# (W-04-10)는 빠져 있었다. 그 결손을 표본 셋으로 잠근다 — ① 형제가 부르는데
# 이 화면은 안 부르면 잡는다 ② 형제가 하나도 없으면(그 테이블을 쓰는 화면이
# 하나뿐) 안 잡는다 ③ 전부 부르면 안 잡는다.
import importlib
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ccgr = importlib.import_module("check-code-group-reachable")

P = "값 목록은 GET /mdm/code-values?codeGroupCode=%s 로 받는다"


def contract(**schemas):
    return {"components": {"schemas": dict(schemas)}}


def write_schema(table, field_group_pairs):
    props = {field: {"description": P % group} for field, group in field_group_pairs}
    return {"x-source-table": table, "properties": props}


class TableGroupsFromDocTest(unittest.TestCase):
    def test_x_source_table이_있는_스키마의_그룹을_모은다(self):
        doc = contract(GoodsIssue=write_schema(
            "logistics.goods_issue", [("reasonCode", "GOODS_ISSUE_REASON")]))
        self.assertEqual(ccgr.table_groups_from_doc(doc),
                          {"logistics.goods_issue": {"GOODS_ISSUE_REASON"}})

    def test_x_source_table이_없으면_보지_않는다(self):
        doc = contract(Foo={"properties": {
            "barCode": {"description": P % "SOME_GROUP"}}})
        self.assertEqual(ccgr.table_groups_from_doc(doc), {})

    def test_같은_테이블의_두_스키마를_합친다(self):
        doc = contract(
            GoodsIssue=write_schema("logistics.goods_issue", [("reasonCode", "GOODS_ISSUE_REASON")]),
            GoodsIssueCreate=write_schema("logistics.goods_issue", [("issueTypeCode", "ISSUE_TYPE")]))
        self.assertEqual(ccgr.table_groups_from_doc(doc),
                          {"logistics.goods_issue": {"GOODS_ISSUE_REASON", "ISSUE_TYPE"}})


class GapsFromTest(unittest.TestCase):
    def test_형제는_부르는데_이_화면은_안_부르면_잡는다(self):
        tg = {"logistics.goods_issue": {"GOODS_ISSUE_REASON"}}
        ts = {"logistics.goods_issue": {"W-01-06", "W-04-10"}}
        sections = {
            "W-01-06": "GET /mdm/code-values?codeGroupCode=GOODS_ISSUE_REASON",
            "W-04-10": "여기는 안 부른다",
        }
        gaps = ccgr.gaps_from(tg, ts, sections)
        self.assertIn(("W-04-10", "logistics.goods_issue", "GOODS_ISSUE_REASON"), gaps)
        self.assertNotIn(("W-01-06", "logistics.goods_issue", "GOODS_ISSUE_REASON"), gaps)

    def test_형제가_하나뿐이면_안_잡는다(self):
        tg = {"logistics.goods_issue": {"GOODS_ISSUE_REASON"}}
        ts = {"logistics.goods_issue": {"W-04-10"}}
        sections = {"W-04-10": "여기도 안 부른다"}
        self.assertEqual(ccgr.gaps_from(tg, ts, sections), [])

    def test_전부_부르면_안_잡는다(self):
        tg = {"logistics.goods_issue": {"GOODS_ISSUE_REASON"}}
        ts = {"logistics.goods_issue": {"W-01-06", "W-04-10"}}
        sections = {
            "W-01-06": "codeGroupCode=GOODS_ISSUE_REASON",
            "W-04-10": "codeGroupCode=GOODS_ISSUE_REASON",
        }
        self.assertEqual(ccgr.gaps_from(tg, ts, sections), [])

    def test_요구서_소절이_아예_없는_화면도_잡는다(self):
        tg = {"logistics.goods_issue": {"GOODS_ISSUE_REASON"}}
        ts = {"logistics.goods_issue": {"W-01-06", "W-04-10"}}
        sections = {"W-01-06": "codeGroupCode=GOODS_ISSUE_REASON"}  # W-04-10 없음
        gaps = ccgr.gaps_from(tg, ts, sections)
        self.assertIn(("W-04-10", "logistics.goods_issue", "GOODS_ISSUE_REASON"), gaps)


class IntegrationTest(unittest.TestCase):
    """실제 계약·스펙·요구서를 대상으로 한 회귀 표본 — omf-mes#336 이 잡은 자리는 지금 없다."""

    def test_goods_issue_reason이_W_04_10에서_더이상_결손이_아니다(self):
        gaps = ccgr.screen_axis_gaps()
        offending = [g for g in gaps if g[0] == "W-04-10" and g[2] == "GOODS_ISSUE_REASON"]
        self.assertEqual(offending, [])


# ── 절 «경계» — 꼬리 절이 직전 화면에 흡수되면 안 된다 ────────────────────
#
# ⛔ 2026-09-03 신설. `end = len(text)` 라 파일 «마지막» 화면 절이 꼬리 절
# (「커버리지 집계」·「대상 유형 대응표」·「변경 이력」)을 통째로 삼켰다. 그 안의
# 경로·그룹이 그 화면의 것으로 세어져, 실제로는 안 부르는 화면이 초록이 됐다.

DOC = "\n".join([
    "# 06 API 요구서",
    "",
    "### 3-1. `W-01-01` 첫 화면",
    "| 액션 | API |",
    "| 조회 | GET /a?codeGroupCode=ALPHA |",
    "",
    "### 3-2. `W-01-02` 마지막 화면",
    "| 액션 | API |",
    "| 조회 | GET /b?codeGroupCode=BETA |",
    "",
    "### 커버리지 집계",
    "",
    "| 경로 | 화면 |",
    "| GET /c?codeGroupCode=GAMMA | 여러 화면 |",
    "",
    "## 변경 이력",
    "",
    "| v0.1 | codeGroupCode=DELTA 를 적었다 |",
])


class SectionBoundaryTest(unittest.TestCase):
    def test_화면_절을_화면_코드로_가른다(self):
        out = ccgr.sections_from_text(DOC)
        self.assertEqual(set(out), {"W-01-01", "W-01-02"})

    def test_첫_화면은_다음_화면_절에서_끊는다(self):
        out = ccgr.sections_from_text(DOC)
        self.assertIn("ALPHA", out["W-01-01"])
        self.assertNotIn("BETA", out["W-01-01"])

    def test_마지막_화면이_꼬리_절을_삼키지_않는다(self):
        # ⛔ 이것이 2026-09-03 에 고친 결함이다.
        out = ccgr.sections_from_text(DOC)
        self.assertIn("BETA", out["W-01-02"])
        self.assertNotIn("GAMMA", out["W-01-02"], "「커버리지 집계」를 삼켰다")
        self.assertNotIn("DELTA", out["W-01-02"], "「변경 이력」을 삼켰다")

    def test_화면_절이_없으면_빈다(self):
        self.assertEqual(dict(ccgr.sections_from_text("## 아무 제목\n본문")), {})


if __name__ == "__main__":
    unittest.main()
