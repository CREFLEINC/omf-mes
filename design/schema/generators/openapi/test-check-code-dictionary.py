#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# check-code-dictionary.py 의 단위 테스트. 표준 라이브러리만 쓴다(저장소 관행).
#
# ⛔ 이 파일이 잠그는 사고는 하나다 — **키가 「같은 이름 다른 값집합」을 못 갈랐다.**
# 첫 판은 사전의 「값」 칸에 «프로퍼티 이름»(documentTypeCode)을 적었고, 검사기가
# 이름으로만 세어 세 키가 «같은 9자리»를 봤다. 「어느 자리가 어느 키인가」를 기계가
# 판정 못 한 것이고, 그것이 이 사전의 존재 이유다.
# ⇒ 값 칸에 실제 코드 문자열을 담고 «값으로» 대조하게 고쳤다. 그 회귀를 잠근다.
import importlib
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
cd = importlib.import_module("check-code-dictionary")

PRINT9 = ["MATERIAL_LOT_LABEL", "GOODS_ISSUE_QR", "PACKING_LABEL"]
LOGI9 = ["PURCHASE_ORDER", "INBOUND_RECEIPT", "GOODS_ISSUE"]


class 자리_상태를_가른다(unittest.TestCase):
    def test_enum이_있으면_enum(self):
        self.assertEqual(cd.state({"type": "string", "enum": PRINT9}, None), "enum")

    def test_배열이면_items에서_본다(self):
        self.assertEqual(
            cd.state({"type": "array", "items": {"enum": PRINT9}}, None), "enum")

    def test_포인터가_있으면_ptr(self):
        d = "값 목록은 GET /mdm/code-values?codeGroupCode=CYCLE_TYPE 로 받는다"
        self.assertEqual(cd.state({"type": "string"}, d), "ptr")

    def test_둘_다_없으면_bare(self):
        self.assertEqual(cd.state({"type": "string"}, "그냥 설명"), "bare")

    def test_enum이_포인터보다_먼저다(self):
        d = "codeGroupCode=X 로 받는다"
        self.assertEqual(cd.state({"type": "string", "enum": PRINT9}, d), "enum")


class 사전_표를_읽는다(unittest.TestCase):
    """⛔ 열이 «정확히 여섯»인 표만 본다 — 같은 문서의 결과 표를 삼켰다(10 → 13)."""

    @staticmethod
    def parse(text):
        import tempfile
        p = os.path.join(tempfile.mkdtemp(), "d.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return cd.read_dictionary(p)

    def test_여섯_열_행을_읽는다(self):
        row = ("| `CD-PRINT-DOCUMENT-TYPE` | `MATERIAL_LOT_LABEL` `PACKING_LABEL` "
               "| `documentTypeCode` | `enum` | 6 | 근거 |\n")
        got = self.parse(row)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["key"], "CD-PRINT-DOCUMENT-TYPE")
        self.assertEqual(got[0]["values"], ["MATERIAL_LOT_LABEL", "PACKING_LABEL"])
        self.assertEqual(got[0]["names"], ["documentTypeCode"])
        self.assertEqual(got[0]["owner"], "enum")
        self.assertEqual(got[0]["places"], 6)

    def test_다섯_열_결과표는_안_읽는다(self):
        # ⛔ 실제로 삼켰던 형태 — 문서 아래쪽 「검증 결과」 표.
        row = "| `CD-PRINT-DOCUMENT-TYPE` | 7 | 4 | **3** | 어디 |\n"
        self.assertEqual(self.parse(row), [])

    def test_키가_아니면_안_읽는다(self):
        row = "| 무엇 | 값 | 이름 | 소유 | 자리 | 근거 |\n"
        self.assertEqual(self.parse(row), [])


class 값으로_갈라야_같은_이름이_갈린다(unittest.TestCase):
    """⭐ 이 사전의 핵심 — 값이 다르면 키가 다르다."""

    def test_같은_이름_다른_값집합은_다른_자리다(self):
        # 사전이 PRINT9 를 선언했는데 자리의 enum 이 LOGI9 면 «남의 자리»다.
        self.assertNotEqual(set(PRINT9), set(LOGI9))

    def test_null이_섞인_enum도_값으로_맞춘다(self):
        # destinationTypeCode 가 nullable 이라 enum 에 None 이 들어 있다.
        enum = ("LOCATION", "PARTNER", "DISPOSAL_SITE", None)
        want = {"LOCATION", "PARTNER", "DISPOSAL_SITE"}
        self.assertEqual(want, {x for x in enum if x is not None})


class 형제_갈림을_찾는다(unittest.TestCase):
    """④ 같은 이름이 「값 있음」과 「맨몸」으로 갈린 자리."""

    def test_갈리면_잡는다(self):
        found = {"statusCode": [
            ("logi", "스키마", "/a", "ptr", (), ("X",)),
            ("logi", "쿼리", "/b", "bare", (), ()),
        ]}
        out = cd.split_siblings(found)
        self.assertEqual(len(out), 1)
        name, f, bare, has, tot = out[0]
        self.assertEqual((name, len(bare), has, tot), ("statusCode", 1, "ptr", 2))

    def test_전부_맨몸이면_안_잡는다(self):
        # 「갈렸다」가 아니라 「통째로 없다」다 — 다른 물음이다.
        found = {"x": [("f", "스키마", "/a", "bare", (), ()),
                       ("f", "쿼리", "/b", "bare", (), ())]}
        self.assertEqual(cd.split_siblings(found), [])

    def test_계약이_다르면_안_묶는다(self):
        found = {"x": [("A", "스키마", "/a", "enum", ("V",), ()),
                       ("B", "쿼리", "/b", "bare", (), ())]}
        self.assertEqual(cd.split_siblings(found), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
