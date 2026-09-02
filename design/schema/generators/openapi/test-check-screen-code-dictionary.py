#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# check-screen-code-dictionary.py 의 단위 테스트. 표준 라이브러리만 쓴다(저장소 관행).
#
# ⛔ 이 검사기가 새로 잠그는 사고 — 2026-09-02 에 코드 사전이 닫혔는데(639/639)
# 화면 스펙 25행이 여전히 「⚠ 값 목록 미확정」이라 적고 있었다. 프론트는 그 문면을
# 보고 선택칸을 «비활성 + 사유»로 만들고(`G-2`), 착수 통지가 그것을 그대로 옮긴다.
#
# ⭐ 검사기 «자신»이 낸 사고도 함께 잠근다 — 첫 실행이 거짓 양성 6건을 냈다.
# 한 (테이블·컬럼) 짝이 «키 둘»에 닿는데(`mdm.equipment.equipment_type_code` →
# 설비 유형 · 계측기 유형) 키를 하나씩 보고 값을 비교해, 형제 키의 값이 전부
# 「사전 밖」으로 잡혔다. `judge_row` 가 짝 단위 «합집합»으로 판정하는지 잠근다.
import importlib
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
scd = importlib.import_module("check-screen-code-dictionary")

REGISTRY = {"INBOUND_VARIANCE_TYPE", "EQUIPMENT_TYPE", "INSTRUMENT_TYPE"}


def entry(values, owner="registry", group=()):
    return {"values": list(values), "owner": owner, "group": list(group)}


def contract(**schemas):
    return {"components": {"schemas": dict(schemas)}}


# ── 다리 — 계약 (테이블·컬럼) → 사전 키 ──────────────────────────────────

class ColumnsFromDocTest(unittest.TestCase):
    def test_테이블과_컬럼과_키가_다_있으면_짝을_만든다(self):
        doc = contract(InboundVariance={
            "x-source-table": "logistics.inbound_variance",
            "properties": {"varianceTypeCode": {
                "x-source-column": "variance_type_code",
                "x-code-key": "CD-INBOUND-VARIANCE-TYPE"}}})
        self.assertEqual(
            scd.columns_from_doc(doc),
            {("logistics.inbound_variance", "variance_type_code"):
             {"CD-INBOUND-VARIANCE-TYPE"}})

    def test_x_source_table이_없으면_다리가_끊긴다(self):
        doc = contract(Foo={"properties": {"aCode": {
            "x-source-column": "a_code", "x-code-key": "CD-A"}}})
        self.assertEqual(scd.columns_from_doc(doc), {})

    def test_x_source_column이_없으면_추측하지_않는다(self):
        # ⛔ camelCase→snake 변환으로 «보충하지 않는다» — 추측으로 이으면 틀린 자리를 ⛔ 로 센다.
        doc = contract(Foo={"x-source-table": "t.foo", "properties": {
            "aCode": {"x-code-key": "CD-A"}}})
        self.assertEqual(scd.columns_from_doc(doc), {})

    def test_x_code_key가_없으면_다리가_끊긴다(self):
        doc = contract(Foo={"x-source-table": "t.foo", "properties": {
            "aCode": {"x-source-column": "a_code"}}})
        self.assertEqual(scd.columns_from_doc(doc), {})

    def test_테이블이_목록이면_전부_편다(self):
        doc = contract(Foo={"x-source-table": ["t.a", "t.b"], "properties": {
            "aCode": {"x-source-column": "a_code", "x-code-key": "CD-A"}}})
        self.assertEqual(set(scd.columns_from_doc(doc)),
                         {("t.a", "a_code"), ("t.b", "a_code")})

    def test_컬럼과_키가_목록이어도_편다(self):
        doc = contract(Foo={"x-source-table": "t.a", "properties": {
            "aCode": {"x-source-column": ["a_code", "b_code"],
                      "x-code-key": ["CD-A", "CD-B"]}}})
        self.assertEqual(scd.columns_from_doc(doc),
                         {("t.a", "a_code"): {"CD-A", "CD-B"},
                          ("t.a", "b_code"): {"CD-A", "CD-B"}})

    def test_같은_짝을_두_스키마가_가리키면_합친다(self):
        doc = contract(
            A={"x-source-table": "t.a", "properties": {
                "aCode": {"x-source-column": "a_code", "x-code-key": "CD-A"}}},
            ACreate={"x-source-table": "t.a", "properties": {
                "aCode": {"x-source-column": "a_code", "x-code-key": "CD-A2"}}})
        self.assertEqual(scd.columns_from_doc(doc),
                         {("t.a", "a_code"): {"CD-A", "CD-A2"}})


# ── ㉮ 낡은 「값 목록 미확정」 ────────────────────────────────────────────

class StaleTest(unittest.TestCase):
    def test_사전이_값을_정했는데_미확정이라_적으면_잡는다(self):
        line = "| 오류 유형 | `variance_type_code` | `code_t` | ✅ | ⚠ 값 목록 미확정 §8-1 | 선택 |"
        dic = {"CD-A": entry(["SHORTAGE", "ITEM_MISMATCH"])}
        stale, off = scd.judge_row(line, {"CD-A"}, dic, REGISTRY)
        self.assertEqual([k for k, _ in stale], ["CD-A"])
        self.assertEqual(off, [])

    def test_사전_값이_비어_있으면_잡지_않는다(self):
        # ⬜ 갈래는 «진짜» 미결이다 — 고객이 W-06-06 에서 운영 중에 채운다.
        line = "| 사유 | `reason_code` | ⚠ 값 목록 미확정 |"
        stale, _ = scd.judge_row(line, {"CD-A"}, {"CD-A": entry([])}, REGISTRY)
        self.assertEqual(stale, [])

    def test_값_목록_미정도_같은_문면으로_본다(self):
        line = "| 사유 | `reason_code` | 공통코드 — 값 목록 미정 |"
        stale, _ = scd.judge_row(line, {"CD-A"}, {"CD-A": entry(["X"])}, REGISTRY)
        self.assertEqual(len(stale), 1)

    def test_오프라인_미확정_표식은_코드와_무관하다(self):
        # ⛔ `M-01-08` §5-3 의 「미확정 표식」은 동기화 상태 표시다 — 값 목록이 아니다.
        line = "| 출고 확정 | `status_code` | 오프라인이면 「미확정」 표식 유지 |"
        stale, _ = scd.judge_row(line, {"CD-A"}, {"CD-A": entry(["X"])}, REGISTRY)
        self.assertEqual(stale, [])

    def test_정합주가_붙은_줄은_보고하지_않는다(self):
        # 작성 규칙 5 — 표시가 붙은 줄은 「이미 판단했다」로 읽는다(verify-stale-terms 선례).
        line = ("| 사유 | `reason_code` | 값 목록 미정 «(정합주: 2026-09-01 — 옛 상태 "
                "기록이다)» → `GET /mdm/code-values?codeGroupCode=GOODS_ISSUE_REASON` |")
        stale, _ = scd.judge_row(line, {"CD-A"}, {"CD-A": entry(["OTHER"])}, REGISTRY)
        self.assertEqual(stale, [])

    def test_구표기_보존과_취소선도_같다(self):
        for mark in ("«(구표기 보존)»", "~~값 목록 미정~~"):
            line = "| 사유 | `reason_code` | 값 목록 미정 %s |" % mark
            stale, _ = scd.judge_row(line, {"CD-A"}, {"CD-A": entry(["X"])}, REGISTRY)
            self.assertEqual(stale, [], mark)

    def test_그룹_포인터를_이미_적었으면_낡은_문면이_아니다(self):
        line = ("| 사유 | `reason_code` | 값 목록 미정 → "
                "`GET /mdm/code-values?codeGroupCode=INBOUND_VARIANCE_TYPE` |")
        stale, _ = scd.judge_row(line, {"CD-A"}, {"CD-A": entry(["X"])}, REGISTRY)
        self.assertEqual(stale, [])

    def test_미확정_문면이_없으면_잡지_않는다(self):
        line = "| 오류 유형 | `variance_type_code` | `SHORTAGE`·`ITEM_MISMATCH` |"
        stale, _ = scd.judge_row(
            line, {"CD-A"}, {"CD-A": entry(["SHORTAGE", "ITEM_MISMATCH"])}, REGISTRY)
        self.assertEqual(stale, [])


# ── ㉯ 사전 밖 값 · 짝 단위 합집합 ───────────────────────────────────────

class OffValueTest(unittest.TestCase):
    def test_사전에_없는_값을_적으면_잡는다(self):
        line = "| 판정 방식 | `judge_method_code` | `VISUAL`·`MEASURE` |"
        _, off = scd.judge_row(
            line, {"CD-A"}, {"CD-A": entry(["VISUAL", "MEASUREMENT"])}, REGISTRY)
        self.assertEqual(off, ["MEASURE"])

    def test_짝이_키_둘에_닿으면_합집합으로_본다(self):
        # ⛔ 이 검사기의 첫 실행이 여기서 거짓 양성 6건을 냈다.
        line = "| 계측기 유형 | `equipment_type_code` | `CALIPER`·`GAUGE` |"
        dic = {"CD-EQUIPMENT-TYPE": entry(["INJECTION_MOLDING", "PRESS"]),
               "CD-INSTRUMENT-TYPE": entry(["CALIPER", "GAUGE", "MICROMETER"])}
        _, off = scd.judge_row(
            line, {"CD-EQUIPMENT-TYPE", "CD-INSTRUMENT-TYPE"}, dic, REGISTRY)
        self.assertEqual(off, [])

    def test_형제_키만_보면_잡히던_값이_합집합에서는_안_잡힌다(self):
        line = "| 설비유형 | `equipment_type_code` | `PRESS` |"
        dic = {"CD-EQUIPMENT-TYPE": entry(["INJECTION_MOLDING", "PRESS"]),
               "CD-INSTRUMENT-TYPE": entry(["CALIPER"])}
        _, off_one = scd.judge_row(line, {"CD-INSTRUMENT-TYPE"}, dic, REGISTRY)
        _, off_both = scd.judge_row(
            line, {"CD-EQUIPMENT-TYPE", "CD-INSTRUMENT-TYPE"}, dic, REGISTRY)
        self.assertEqual(off_one, ["PRESS"])      # 한 키만 보면 잡힌다
        self.assertEqual(off_both, [])            # 합집합이면 안 잡힌다

    def test_그룹_이름은_값이_아니다(self):
        line = "| 유형 | `a_code` | `GET /mdm/code-values?codeGroupCode=EQUIPMENT_TYPE` `PRESS` |"
        dic = {"CD-A": entry(["PRESS"])}
        _, off = scd.judge_row(line, {"CD-A"}, dic, REGISTRY)
        self.assertEqual(off, [])

    def test_제약_낱말은_값으로_세지_않는다(self):
        line = "| 유형 | `a_code` | `PRESS` · NOT NULL · CHECK · DEFAULT |"
        _, off = scd.judge_row(line, {"CD-A"}, {"CD-A": entry(["PRESS"])}, REGISTRY)
        self.assertEqual(off, [])

    def test_사전_값이_비면_값_판정을_하지_않는다(self):
        line = "| 유형 | `a_code` | `ANYTHING` |"
        _, off = scd.judge_row(line, {"CD-A"}, {"CD-A": entry([])}, REGISTRY)
        self.assertEqual(off, [])


# ── §4 필드표 행 읽기 ───────────────────────────────────────────────────

class FieldRowsTest(unittest.TestCase):
    SPEC = "\n".join([
        "## §4. 필드",
        "",
        "### §4-A. 입하 오류 `logistics.inbound_variance`",
        "",
        "| 라벨 | 출처 컬럼 | 타입 | 필수 | 검증·비고 | 입력 |",
        "| --- | --- | --- | :-: | --- | --- |",
        "| 오류 유형 | `variance_type_code` | `code_t` | ✅ | ⚠ 값 목록 미확정 | 선택 |",
        "| 대상 수량 | `variance_qty` | `qty_t` | ✅ | | 입력 |",
        "",
        "## §5. 액션",
        "",
        "| 지나가는 표 | `not_a_column` | 여기는 §4 밖이다 |",
    ])

    def test_소절_제목의_테이블과_행의_컬럼을_짝짓는다(self):
        rows = list(scd.field_rows(self.SPEC))
        pairs = {(t, c) for t, c, _ in rows}
        self.assertIn(("logistics.inbound_variance", "variance_type_code"), pairs)
        self.assertIn(("logistics.inbound_variance", "variance_qty"), pairs)

    def test_다음_상위_제목에서_끊는다(self):
        # ⛔ §5 의 표가 §4 소절에 흡수되면 엉뚱한 행을 판정한다.
        cols = {c for _, c, _ in scd.field_rows(self.SPEC)}
        self.assertNotIn("not_a_column", cols)

    def test_테이블_이름이_없는_소절은_보지_않는다(self):
        spec = "\n".join([
            "### §4-A. 화면 상태",
            "| 라벨 | 출처 컬럼 |",
            "| 상태 | `status_code` |",
        ])
        self.assertEqual(list(scd.field_rows(spec)), [])


class NormTest(unittest.TestCase):
    def test_스칼라도_목록도_받는다(self):
        self.assertEqual(scd.norm("a"), ["a"])
        self.assertEqual(scd.norm(["a", "b"]), ["a", "b"])
        self.assertEqual(scd.norm(None), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
