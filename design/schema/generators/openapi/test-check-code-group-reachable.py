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


class FieldConsumptionTest(unittest.TestCase):
    """같은 테이블의 비소비 코드 필드가 가짜 호출을 만들지 않게 한다."""

    def setUp(self):
        self.gap = ("W-01-01", "trace.lot", "MES_CATEGORY")
        self.fields = {("trace.lot", "MES_CATEGORY"): {
            "mesCategoryCode", "mes_category_code"}}

    def classify(self, body, fields=None):
        return ccgr.split_consumed_gaps(
            [self.gap], self.fields if fields is None else fields,
            {("W-01-01", "trace.lot"): body})

    def test_비소비는_별도후보이며_선택필드소비는_결손이다(self):
        self.assertEqual(self.classify("| LOT | `lotNo` |"), ([], [self.gap]))
        for name in ["mesCategoryCode", "mes_category_code"]:
            self.assertEqual(self.classify("| 선택 | `%s` |" % name),
                             ([self.gap], []))

    def test_부분이름은_소비가_아니다(self):
        self.assertEqual(self.classify("| 과거 | `old_mes_category_code` |"),
                         ([], [self.gap]))

    def test_파싱실패와_귀속불명은_기존검사로_남긴다(self):
        self.assertEqual(self.classify("필드표 없음"), ([self.gap], []))
        self.assertEqual(self.classify("| LOT | `lotNo` |", {}),
                         ([self.gap], []))

    def test_요구서소절이_없어도_실제소비면_검출한다(self):
        gaps = ccgr.gaps_from(
            {"trace.lot": {"MES_CATEGORY"}},
            {"trace.lot": {"W-01-01", "W-01-02"}},
            {"W-01-02": P % "MES_CATEGORY"})
        self.assertEqual(ccgr.split_consumed_gaps(
            gaps, self.fields,
            {("W-01-01", "trace.lot"): "| 구분 | `mesCategoryCode` |"})[0],
            [self.gap])

    def test_명시컬럼과_약어_camel_case를_지원한다(self):
        self.assertEqual(ccgr.field_aliases("ERPCode", {"x-source-column": "code"}),
                         {"ERPCode", "erp_code", "code"})

    def test_같은그룹_여러스키마는_필드를_합친다(self):
        doc = contract(
            First=write_schema("trace.lot", [("firstCode", "MES_CATEGORY")]),
            Second=write_schema("trace.lot", [("secondCode", "MES_CATEGORY")]))
        self.assertEqual(ccgr.group_fields_from_doc(doc)[("trace.lot", "MES_CATEGORY")],
                         {"firstCode", "first_code", "secondCode", "second_code"})

    def test_스키마포인터가_있으면_필드귀속불명으로_유지한다(self):
        schema = write_schema("trace.lot", [("mesCategoryCode", "MES_CATEGORY")])
        schema["description"] = P % "MES_CATEGORY"
        fields = ccgr.group_fields_from_doc(contract(Lot=schema))
        self.assertIsNone(fields[("trace.lot", "MES_CATEGORY")])
        self.assertEqual(self.classify("| LOT | `lotNo` |", fields),
                         ([self.gap], []))

    def test_명시적인_동일테이블_필드참조를_해석한다(self):
        bodies = {("W-01-01", "trace.lot"): "필드는 `W-01-02` §4-A 참조",
                  ("W-01-02", "trace.lot"): "| 번호 | `lotNo` |"}
        self.assertEqual(ccgr.split_consumed_gaps([self.gap], self.fields, bodies),
                         ([], [self.gap]))
        bodies[("W-01-02", "trace.lot")] = "| 구분 | `mesCategoryCode` |"
        self.assertEqual(ccgr.split_consumed_gaps([self.gap], self.fields, bodies),
                         ([self.gap], []))

    def test_참조누락_다른테이블_순환은_보수적으로_남긴다(self):
        bodies = {("W-01-01", "trace.lot"): "`W-01-02` §4-A 참조",
                  ("W-01-02", "mdm.item"): "| ID | `itemId` |"}
        self.assertEqual(ccgr.split_consumed_gaps([self.gap], self.fields, bodies)[0],
                         [self.gap])
        bodies[("W-01-02", "trace.lot")] = "`W-01-01` §4-A 참조"
        self.assertEqual(ccgr.split_consumed_gaps([self.gap], self.fields, bodies)[0],
                         [self.gap])


class IntegrationTest(unittest.TestCase):
    """실제 계약·스펙·요구서를 대상으로 한 회귀 표본 — omf-mes#336 이 잡은 자리는 지금 없다."""

    def test_실제_폐기화면의_필요한_포인터를_지우면_여전히_검출한다(self):
        sections = ccgr.screen_sections()
        sections["W-04-10"] = sections["W-04-10"].replace(
            "codeGroupCode=GOODS_ISSUE_REASON", "removedGroupPointer")
        raw = ccgr.gaps_from(ccgr.table_groups(), ccgr.table_screens(), sections)
        gaps, _candidates = ccgr.split_consumed_gaps(
            raw, ccgr.group_fields(), ccgr.screen_field_bodies())
        self.assertIn(("W-04-10", "logistics.goods_issue", "GOODS_ISSUE_REASON"), gaps)

    def test_goods_issue_reason이_W_04_10에서_더이상_결손이_아니다(self):
        gaps = ccgr.screen_axis_gaps()
        offending = [g for g in gaps if g[0] == "W-04-10" and g[2] == "GOODS_ISSUE_REASON"]
        self.assertEqual(offending, [])

    def test_새_LOT구분을_소비하지않는_일곱화면은_가짜호출을_요구하지않는다(self):
        screens = {"M-04-04", "P-01-01", "W-02-04", "W-03-01", "W-03-02",
                   "W-03-03", "W-04-08"}
        raw = ccgr.gaps_from(ccgr.table_groups(), ccgr.table_screens(),
                             ccgr.screen_sections())
        gaps, candidates = ccgr.split_consumed_gaps(
            raw, ccgr.group_fields(), ccgr.screen_field_bodies())
        self.assertEqual({screen for screen, table, group in candidates
                          if table == "trace.lot" and group == "MES_CATEGORY"}, screens)
        self.assertFalse(any(group == "MES_CATEGORY" for _, _, group in gaps))


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
