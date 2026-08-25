#!/usr/bin/env python3
"""check-report-language.py 단위 테스트.

⚠ 검사기는 「무엇을 잡느냐」보다 **「무엇을 안 잡느냐」**가 틀리기 쉽다.
여기서 특히 잠그는 것 — **병기한 것을 오탐으로 잡지 않는가.** 오탐이 많으면
검사기를 꺼 버리게 되고, 그러면 없느니만 못하다.

실제로 첫 판이 뒤 괄호 병기를 오탐으로 잡았다 —
`W-06-06`(공통코드·조직·작업자 마스터) 를 「뜻 없이 썼다」고 했다.
"""
from __future__ import annotations

import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "chk", os.path.join(HERE, "check-report-language.py")
)
chk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chk)


def kinds(text: str) -> list[str]:
    return [k for _, k, _ in chk.scan_text(text)]


def tokens(text: str) -> list[str]:
    return [t for _, _, t in chk.scan_text(text)]


class ExplainedTest(unittest.TestCase):
    """병기를 인정하는가 — 앞·뒤 두 모양 다."""

    def test_앞에_설명이_있으면_통과(self):
        self.assertTrue(chk.explained("자재 폐기 화면(W-01-06)", "W-01-06"))

    def test_뒤_괄호에_설명이_있으면_통과(self):
        self.assertTrue(
            chk.explained("`W-06-06`(공통코드·조직 마스터) 를 고친다", "W-06-06"))

    def test_설명이_없으면_잡는다(self):
        self.assertFalse(chk.explained("W-01-06 을 고쳤다", "W-01-06"))

    def test_줄_뒤쪽_한글은_설명이_아니다(self):
        # 「W-01-06 과 W-04-10 을 고쳤다」가 통과하면 안 된다.
        self.assertFalse(chk.explained("W-01-06 과 W-04-10 을 고쳤다", "W-01-06"))

    def test_빈_괄호는_설명이_아니다(self):
        self.assertFalse(chk.explained("W-01-06() 을 고친다", "W-01-06"))


class ScanTest(unittest.TestCase):
    def test_화면_번호_나열을_잡는다(self):
        t = "본문\n\nW-01-06 과 W-04-10 을 고쳤다.\n"
        self.assertEqual(tokens(t), ["W-01-06", "W-04-10"])

    def test_조항_번호를_잡는다(self):
        self.assertIn("조항 번호", kinds("본문\n\nA-10 을 적용한다.\n"))

    def test_회신_번호를_잡는다(self):
        self.assertIn("회신 번호", kinds("본문\n\nE-4 가 풀린다.\n"))

    def test_병기한_것은_안_잡는다(self):
        t = "자재 폐기 화면(W-01-06)에 다형 참조 대응표 조항(A-10)을 적용한다.\n"
        self.assertEqual(chk.scan_text(t), [])

    def test_전문_용어_첫_등장에_풀이가_없으면_잡는다(self):
        self.assertIn("전문 용어(첫 등장)", kinds("본문\n\n다형 구조를 바꾼다.\n"))

    def test_전문_용어에_풀이가_붙으면_안_잡는다(self):
        t = "다형(한 칸이 여러 표를 가리킨다) 구조를 바꾼다.\n"
        self.assertNotIn("전문 용어(첫 등장)", kinds(t))

    def test_전문_용어는_첫_등장만_본다(self):
        # 한 번 풀었으면 그 뒤로는 그냥 써도 된다.
        t = "다형(한 칸이 여러 표를 가리킨다)이다.\n\n다형 구조를 바꾼다.\n"
        self.assertNotIn("전문 용어(첫 등장)", kinds(t))


class CountTest(unittest.TestCase):
    """⚠ 세는 도구가 부풀려 세면 그것을 믿고 규모를 잘못 잡는다."""

    def test_한_줄에_같은_기호가_두_번_나와도_한_번만_센다(self):
        t = "본문\n\nE-3 선례를 따른다. E-3 는 그 방식으로 풀었다.\n"
        self.assertEqual(len(chk.scan_text(t)), 1)

    def test_회신_번호를_조항으로도_세지_않는다(self):
        # E-3 는 회신 번호다. 조항 패턴에도 걸리면 한 기호를 두 번 센다.
        self.assertEqual(kinds("본문\n\nE-3 를 따른다.\n"), ["회신 번호"])

    def test_조항은_E_말고_다른_접두를_잡는다(self):
        for tok in ("A-10", "B-8", "C-2", "G-16", "L-3"):
            with self.subTest(tok=tok):
                self.assertEqual(kinds(f"본문\n\n{tok} 을 적용한다.\n"),
                                 ["조항 번호"])


class DefinedTermTest(unittest.TestCase):
    """⚠ 정의를 표에 적으면 본 검사는 표를 건너뛰어 못 본다 —
    그래서 규칙 문서 자신이 「뜻 없이 썼다」로 걸렸다. 정의는 표까지 훑는다."""

    def test_표에_적은_정의를_인정한다(self):
        t = ("| 말 | 뜻 |\n| --- | --- |\n"
             "| **다형**(참조) | 한 칸이 여러 표를 가리킨다 |\n\n"
             "다형 구조를 바꾼다.\n")
        self.assertNotIn("전문 용어(첫 등장)", kinds(t))

    def test_줄표로_적은_정의도_인정한다(self):
        t = "다형 — 한 칸이 여러 표를 가리킨다.\n\n다형 구조를 바꾼다.\n"
        self.assertNotIn("전문 용어(첫 등장)", kinds(t))

    def test_정의가_없으면_여전히_잡는다(self):
        self.assertIn("전문 용어(첫 등장)", kinds("본문\n\n다형 구조를 바꾼다.\n"))

    def test_기호만_있고_한글_풀이가_없으면_정의가_아니다(self):
        self.assertNotIn("다형", chk.defined_terms("| 다형 | polymorphic |\n"))


class SkipTest(unittest.TestCase):
    """검사하지 않는 자리 — 여기서 잡으면 오탐이 쏟아진다."""

    def test_표는_건너뛴다(self):
        self.assertEqual(chk.scan_text("| W-01-06 | 무엇 |\n"), [])

    def test_코드블록은_건너뛴다(self):
        self.assertEqual(chk.scan_text("```\nW-01-06 A-10 E-4\n```\n"), [])

    def test_제목은_건너뛴다(self):
        self.assertEqual(chk.scan_text("## W-01-06 폐기 품의\n"), [])

    def test_근거_줄은_건너뛴다(self):
        self.assertEqual(chk.scan_text("근거: W-01-06 · A-10\n"), [])

    def test_파일_경로_목록은_건너뛴다(self):
        self.assertEqual(chk.scan_text("- `design/wiki/project-spec/04-통합-IA.md`\n"), [])


class RealDocTest(unittest.TestCase):
    """이번 트랙에서 쓴 실물 문서로 돌려 본다."""

    ROOT = os.path.join(HERE, "..", "..", "..", "..")

    def test_확정_요청서가_통과한다(self):
        path = os.path.join(
            self.ROOT, "design", "raw", "decision-requests",
            "DR-013-폐기거래처와-역할관리.md")
        if not os.path.exists(path):
            self.skipTest("문서 없음")
        with open(path, encoding="utf-8") as f:
            hits = chk.scan_text(f.read())
        self.assertEqual(hits, [], f"오탐: {hits[:5]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
