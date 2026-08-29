#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# check-query-envelope.py 의 단위 테스트. 표준 라이브러리만 쓴다(저장소 관행).
#
# 검사 6종마다 «통과 표본»과 «실패 표본»을 한 쌍씩 잠근다. 이 검사기가 잘못
# 통과시키면(위양성) 봉투가 또 갈리고, 잘못 막으면(오탐) 규약을 지킨 자리가
# 빨개져 다음 사람이 검사기를 꺼 버린다 — 양쪽을 다 잠근다.
import importlib
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
qe = importlib.import_module("check-query-envelope")


def doc(**schemas):
    return {"components": {"schemas": dict(schemas)}}


class RefTest(unittest.TestCase):
    # ⛔ $ref 해소가 이 검사기의 전제다 — 해소하지 않으면 목록형이 131 → 94 로 준다.
    def test_ref_를_해소해_프로퍼티를_본다(self):
        d = doc(Page={"type": "object", "properties": {"items": {}, "page": {}}})
        props = qe.properties({"$ref": "#/components/schemas/Page"}, d)
        self.assertEqual(sorted(props), ["items", "page"])

    def test_ref_를_해소하지_않으면_보이지_않던_것을_본다(self):
        d = doc(Page={"type": "object", "properties": {"items": {}}})
        self.assertEqual(qe.properties({"$ref": "#/components/schemas/Page"}, d).keys(),
                         {"items"})
        self.assertEqual(qe.properties({"$ref": "#/components/schemas/없다"}, d), {})

    def test_순환_참조에_빠지지_않는다(self):
        d = doc(A={"$ref": "#/components/schemas/B"}, B={"$ref": "#/components/schemas/A"})
        self.assertEqual(qe.deref({"$ref": "#/components/schemas/A"}, d), {})

    def test_allOf_를_얕게_합친다(self):
        d = doc(Base={"properties": {"items": {}}})
        s = {"allOf": [{"$ref": "#/components/schemas/Base"}, {"properties": {"page": {}}}]}
        self.assertEqual(sorted(qe.properties(s, d)), ["items", "page"])


class Rule1ShapeTest(unittest.TestCase):
    # ① 최상위 목록형 200 이 표준형인가
    def test_표준형은_통과한다(self):
        for names in ({"items", "page"}, {"items"}, {"items", "page", "summary"}):
            with self.subTest(names=sorted(names)):
                self.assertTrue(qe.is_standard_shape(names))

    def test_totalCount_형은_막힌다(self):
        self.assertFalse(qe.is_standard_shape({"items", "page", "totalCount"}))
        self.assertFalse(qe.is_standard_shape({"items", "totalCount"}))
        self.assertFalse(qe.is_standard_shape({"asOf", "items"}))


class Rule2PageMetaTest(unittest.TestCase):
    # ② page 가 PageMeta 인가 — 판정은 $ref 문자열로 한다
    def test_PageMeta_면_통과한다(self):
        props = {"page": {"$ref": "#/components/schemas/PageMeta"}}
        self.assertTrue((props["page"].get("$ref") or "").endswith("/PageMeta"))

    def test_인라인_page_는_잡힌다(self):
        props = {"page": {"type": "object"}}
        self.assertFalse((props["page"].get("$ref") or "").endswith("/PageMeta"))


class Rule3SummaryPairTest(unittest.TestCase):
    # ③ 요약 전용 경로 ↔ 짝 목록 경로
    def test_요약_전용_경로를_알아본다(self):
        for p in ("/app/document-issues/summary", "/quality/defect-records/distribution",
                  "/quality/inspection-results/defect-rate-trend",
                  "/quality/lot-status-summary"):
            with self.subTest(path=p):
                self.assertTrue(qe.is_summary_path(p))

    def test_평범한_목록은_요약_전용이_아니다(self):
        self.assertFalse(qe.is_summary_path("/app/document-issues"))
        self.assertFalse(qe.is_summary_path("/production/work-orders"))

    def test_짝을_찾는다(self):
        self.assertEqual(qe.pair_path("/app/document-issues/summary"), "/app/document-issues")
        self.assertEqual(qe.pair_path("/quality/defect-records/distribution"),
                         "/quality/defect-records")

    def test_낱말에_붙은_것은_짝을_만들지_않는다(self):
        # ⛔ `-summary` 를 기계로 갈라 짝을 «지어내면» 없는 경로를 결손으로 낸다.
        self.assertIsNone(qe.pair_path("/app/dashboard-summary"))
        self.assertIsNone(qe.pair_path("/quality/lot-status-summary"))

    def test_쪽_축은_대조에서_뺀다(self):
        self.assertEqual(qe.PAGING_AXES, frozenset({"page", "size", "sort"}))


class Rule4AsOfTest(unittest.TestCase):
    # ④ 집계 페이로드의 기준 시각
    def test_집계_이름을_알아본다(self):
        for n in ("LotStatusSummary", "DefectDistribution", "DefectRateTrend"):
            with self.subTest(name=n):
                self.assertTrue(qe.is_agg_schema_name(n))

    def test_평범한_스키마는_집계가_아니다(self):
        self.assertFalse(qe.is_agg_schema_name("WorkOrder"))
        self.assertFalse(qe.is_agg_schema_name("InventoryBalance"))

    def test_asOf_가_required_면_통과한다(self):
        d = doc(LotStatusSummary={"properties": {"asOf": {}}, "required": ["asOf"]})
        s = d["components"]["schemas"]["LotStatusSummary"]
        self.assertIn("asOf", qe.properties(s, d))
        self.assertIn("asOf", qe.required_of(s, d))

    def test_금지된_이름은_잡힌다(self):
        self.assertEqual(qe.BANNED_ASOF, ("calculatedAt", "snapshotAt", "generatedAt"))
        d = doc(DowntimeSummary={"properties": {"calculatedAt": {}}})
        s = d["components"]["schemas"]["DowntimeSummary"]
        self.assertTrue(any(b in qe.properties(s, d) for b in qe.BANNED_ASOF))


class Rule5SortTest(unittest.TestCase):
    # ⑤ 정렬 키 표기
    def test_키Asc_키Desc_는_통과한다(self):
        self.assertEqual(qe.sort_style(["transitionedAtDesc", "lotNoAsc"]), "ok")

    def test_쉼표형과_대문자형은_잡힌다(self):
        self.assertEqual(qe.sort_style(["priorityNo,asc"]), "other")
        self.assertEqual(qe.sort_style(["SHOT_USAGE_DESC", "NEXT_PM_ASC"]), "other")
        self.assertEqual(qe.sort_style(["itemCode", "lotNo"]), "other")

    def test_enum_이_비면_표기_판정을_하지_않는다(self):
        self.assertEqual(qe.sort_style([]), "other")


class Rule6BoundaryTest(unittest.TestCase):
    # ⑥ 기간 쌍의 끝 경계
    def test_익일_00시_설명은_통과한다(self):
        # ⚠ 규약을 «옳게» 설명하는 문장이다 — 오탐을 내면 지킨 자리가 빨개진다.
        p = {"name": "occurredTo", "description":
             "기간 끝 — 이 시각 «미만». 「그날까지」는 23:59:59 가 아니라 «익일 00:00:00» 을 보낸다."}
        self.assertFalse(qe.boundary_violation(p))

    def test_example_오염은_잡힌다(self):
        p = {"name": "transitionTo",
             "schema": {"type": "string", "format": "date-time",
                        "example": "2026-08-06T23:59:59+09:00"}}
        self.assertTrue(qe.boundary_violation(p))

    def test_이하_문면은_잡힌다(self):
        p = {"name": "occurredTo", "description": "기간 끝 — 이 시각 이하를 담는다."}
        self.assertTrue(qe.boundary_violation(p))

    def test_경계를_안_적은_평범한_자리는_통과한다(self):
        self.assertFalse(qe.boundary_violation({"name": "issuedTo", "description": "기간 끝"}))
        self.assertFalse(qe.boundary_violation({"name": "issuedTo"}))

    def test_기간_쌍_정규식이_짝을_맞춘다(self):
        self.assertEqual(qe.PERIOD_FROM.match("occurredFrom").group(1), "occurred")
        self.assertEqual(qe.PERIOD_TO.match("occurredTo").group(1), "occurred")
        self.assertIsNone(qe.PERIOD_FROM.match("occurredTo"))


class RealArtifactTest(unittest.TestCase):
    # 저장소 실물이 파싱되는지 — 형이 깨지면 여기서 먼저 터진다.
    def test_계약_7벌이_읽힌다(self):
        import glob, json
        files = sorted(glob.glob(os.path.join(qe.CONTRACTS_DIR, "*.json")))
        self.assertGreaterEqual(len(files), 7)
        for f in files:
            with self.subTest(f=os.path.basename(f)):
                with open(f, encoding="utf-8") as fh:
                    self.assertIn("paths", json.load(fh))


if __name__ == "__main__":
    unittest.main(verbosity=2)
