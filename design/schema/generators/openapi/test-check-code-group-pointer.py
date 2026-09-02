#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# check-code-group-pointer.py 의 단위 테스트. 표준 라이브러리만 쓴다(저장소 관행).
#
# ⛔ 이 파일이 잠그는 사고는 하나다 — **검사기가 초록인데 구멍이 있었다.**
# 두 번 났다: ① 프로퍼티 설명만 보다가 JUDGMENT_TYPE 을 놓쳤고, ② 그 고침이
# 「자리 다섯」을 손으로 열거해 components/parameters·requestBody 를 또 빠뜨렸다.
# 지금은 자리를 «열거하지 않고» 문서를 훑는다 — 그래서 깊이·구조에 상한이 없다.
# 2026-09-01 실측에서 `JUDGMENT_TYPE`(등록부 밖 이름)이 «스키마» 설명과
# «오퍼레이션» 설명에만 적혀 있어 그대로 통과했다. 그때 이 검사기의 초록이
# 「계약이 가리킨 이름은 전부 등록부 안」의 근거로 쓰이고 있었으므로,
# 구멍이 그대로 신뢰가 됐다. 자리마다 표본을 하나씩 잠근다.
import importlib
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
cg = importlib.import_module("check-code-group-pointer")

P = "값 목록은 GET /mdm/code-values?codeGroupCode=%s 로 받는다"


def found(doc):
    """문서에서 뽑힌 그룹 이름 집합."""
    return {n for _, desc in cg.descriptions(doc) for n in cg.POINTER.findall(desc)}


class 자리마다_찾는다(unittest.TestCase):
    def test_프로퍼티_설명(self):
        d = {"components": {"schemas": {"A": {"properties": {
            "reasonCode": {"description": P % "GOODS_ISSUE_REASON"}}}}}}
        self.assertEqual(found(d), {"GOODS_ISSUE_REASON"})

    def test_스키마_설명(self):
        # ⛔ 이것이 JUDGMENT_TYPE 을 놓쳤던 자리다.
        d = {"components": {"schemas": {"JudgmentTypeControl": {
            "description": "판정유형(codeGroupCode=JUDGMENT_TYPE)의 물류 통제 속성"}}}}
        self.assertEqual(found(d), {"JUDGMENT_TYPE"})

    def test_오퍼레이션_설명(self):
        d = {"paths": {"/mdm/judgment-type-controls": {"get": {
            "description": "codeGroupCode=JUDGMENT_TYPE 으로 고정해 연다"}}}}
        self.assertEqual(found(d), {"JUDGMENT_TYPE"})

    def test_파라미터_설명_오퍼레이션_안(self):
        d = {"paths": {"/x": {"get": {"parameters": [
            {"name": "reasonCode", "description": P % "DOWNTIME_REASON"}]}}}}
        self.assertEqual(found(d), {"DOWNTIME_REASON"})

    def test_파라미터_설명_경로_수준(self):
        d = {"paths": {"/x": {"parameters": [
            {"name": "statusCode", "description": P % "LOT_STATUS"}]}}}
        self.assertEqual(found(d), {"LOT_STATUS"})

    def test_응답_설명(self):
        d = {"paths": {"/x": {"post": {"responses": {
            "400": {"description": P % "VARIANCE_REASON"}}}}}}
        self.assertEqual(found(d), {"VARIANCE_REASON"})

    # ⛔ 아래 셋은 «자리를 열거하던» 판이 못 보던 자리다(2026-09-01 리뷰).
    #    실측으로 components/parameters 27자리 · requestBody 인라인 스키마 24자리가 있었다.
    def test_components_parameters(self):
        d = {"components": {"parameters": {"ReasonCode": {
            "name": "reasonCode", "in": "query", "description": P % "DOWNTIME_REASON"}}}}
        self.assertEqual(found(d), {"DOWNTIME_REASON"})

    def test_requestBody_인라인_스키마_프로퍼티(self):
        d = {"paths": {"/x": {"put": {"requestBody": {"content": {"application/json": {
            "schema": {"type": "object", "properties": {
                "reasonCode": {"description": P % "GOODS_ISSUE_REASON"}}}}}}}}}}
        self.assertEqual(found(d), {"GOODS_ISSUE_REASON"})

    def test_components_responses(self):
        d = {"components": {"responses": {
            "Conflict": {"description": P % "LOT_HOLD_RELEASE_REASON"}}}}
        self.assertEqual(found(d), {"LOT_HOLD_RELEASE_REASON"})

    def test_아무리_깊어도_찾는다(self):
        # 자리를 열거하지 않고 훑으므로 깊이에 상한이 없다.
        d = {"a": {"b": {"c": [{"d": {"description": P % "PICKING_TYPE"}}]}}}
        self.assertEqual(found(d), {"PICKING_TYPE"})


class 등록부_대조(unittest.TestCase):
    def test_등록부에_있는_이름은_통과한다(self):
        self.assertIn("JUDGMENT_TYPE", cg.REGISTRY)
        self.assertIn("APP_USER_STATUS", cg.REGISTRY)

    def test_등록부_밖_이름은_걸린다(self):
        # 짓기 규칙으로 «도출»할 수 있어도 그 행이 «있는» 것은 다른 문제다(G-32).
        d = {"components": {"schemas": {"A": {"properties": {
            "statusCode": {"description": P % "WORK_ORDER_STATUS"}}}}}}
        names = found(d)
        self.assertEqual(names, {"WORK_ORDER_STATUS"})
        self.assertTrue(names - cg.REGISTRY, "등록부 밖이어야 한다")

    def test_등록부는_공유계약의_사본이다(self):
        # 사본이 정본보다 커지면 「검사기만 늘려 초록을 만든」 것이다.
        root = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
        p = os.path.join(root, "design", "wiki", "decisions-policy", "공유계약.md")
        with open(p, encoding="utf-8") as fh:
            body = fh.read()
        빠진 = sorted(n for n in cg.REGISTRY if n not in body)
        self.assertEqual(빠진, [], "공유계약 G-32 에 없는 이름이 REGISTRY 에 있다")


class 빈_설명(unittest.TestCase):
    def test_설명이_없어도_터지지_않는다(self):
        d = {"components": {"schemas": {"A": {"properties": {"x": {}}}}},
             "paths": {"/y": {"get": {}}}}
        self.assertEqual(found(d), set())

    def test_스키마가_리스트여도_건너뛴다(self):
        d = {"components": {"schemas": {"A": []}}, "paths": {"/y": []}}
        self.assertEqual(found(d), set())



class 등록부를_조항_표에서_읽는다(unittest.TestCase):
    """⛔ 2026-09-02 이관 — 이 목록의 사본은 저장소에 없다.

    이관 전 실측: 조항 산문 **52** · 계수 괄호 고유 **4** · 검사기 상수 **56** — 세 벌이
    갈려 있었다. `RECEIPT_TYPE` 등 넷은 「확정된 것 —」 문장에 아예 없었는데 계약 9자리가
    그 넷을 가리켰다. 사본이 갈라지는 것을 막는 법은 사본을 없애는 것뿐이다.
    """

    HEAD = ("#### \u2b50 \ub4f1\ub85d\ubd80 \u2014 \uc774\ub984\uc774 \u00ab\uc788\ub294\u00bb "
            "\uadf8\ub8f9 (**\uc815\ubcf8 \ud45c**)\n\n"
            "| \uc5f4 | \ubb34\uc5c7 |\n| --- | --- |\n| **\uadf8\ub8f9** | \uc774\ub984 |\n\n"
            "| \uadf8\ub8f9 | \uc18c\uc720 | \ub4f1\uc7ac | \uadfc\uac70 |\n"
            "| --- | --- | --- | --- |\n")

    @staticmethod
    def write(text):
        import tempfile
        p = os.path.join(tempfile.mkdtemp(), "clause.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p

    def test_첫_칸만_읽는다(self):
        # ⛔ 근거 칸의 «값»(RETEST_PASS)이나 다른 그룹 상호참조를 주우면 산문 시절로 되돌아간다.
        md = self.HEAD + (
            "| `LOT_HOLD_RELEASE_REASON` | `registry` | 2026-08-31 | "
            "`RETEST_PASS`·`MANAGER_OVERRIDE` — `WAREHOUSE_TYPE` 과 같은 근거 |\n")
        self.assertEqual(cg.load_registry(self.write(md)), {"LOT_HOLD_RELEASE_REASON"})

    def test_열_설명표를_안_삼킨다(self):
        # 바로 위 2열 표가 있어도 «4열» 행만 읽는다.
        md = self.HEAD + "| `LOT_STATUS` | ⬜ | G-32 확정 | `omf-mes#176` |\n"
        self.assertEqual(cg.load_registry(self.write(md)), {"LOT_STATUS"})

    def test_다음_소제목에서_멈춘다(self):
        md = (self.HEAD + "| `LOT_STATUS` | ⬜ | G-32 확정 | 근거 |\n"
              "\n#### 다른 절\n\n| 그룹 | 소유 | 등재 | 근거 |\n| --- | --- | --- | --- |\n"
              "| `NOT_A_GROUP` | ⬜ | — | — |\n")
        self.assertEqual(cg.load_registry(self.write(md)), {"LOT_STATUS"})

    def test_표가_없으면_죽는다(self):
        # ⛔ 조용히 빈 등록부가 되면 계약의 «모든» 포인터가 빨강이 되고 원인이 오독된다.
        with self.assertRaises(SystemExit):
            cg.load_registry(self.write("## 아무 표도 없다\n"))

    def test_행이_하나도_없어도_죽는다(self):
        with self.assertRaises(SystemExit):
            cg.load_registry(self.write(self.HEAD))

    def test_실물_조항에서_56이_나온다(self):
        self.assertEqual(len(cg.load_registry()), 56)

    def test_계약이_가리키는_넷이_들어_있다(self):
        # ⛔ 이관 전 「확정된 것 —」 문단에 없던 넷 — 사라지면 계약 9자리가 빨강이 된다.
        got = cg.load_registry()
        for n in ("RECEIPT_TYPE", "ISSUE_TYPE", "MANAGEMENT_LEVEL", "GOODS_RECEIPT_REASON"):
            self.assertIn(n, got)


if __name__ == "__main__":
    unittest.main(verbosity=1)
