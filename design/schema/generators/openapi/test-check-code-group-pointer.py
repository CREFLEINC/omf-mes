#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# check-code-group-pointer.py 의 단위 테스트. 표준 라이브러리만 쓴다(저장소 관행).
#
# ⛔ 이 파일이 잠그는 사고는 하나다 — **검사기가 초록인데 구멍이 있었다.**
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


if __name__ == "__main__":
    unittest.main(verbosity=1)
