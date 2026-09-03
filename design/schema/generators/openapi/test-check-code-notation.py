#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`check-code-notation.py` 의 순수 함수 시험.

⭐ 파일을 읽지 않는 함수만 시험한다 — 저장소 상태가 바뀌어도 이 시험은 안 흔들린다.
   저장소 실물에 대한 판정은 검사기 자신의 기준선(래칫)이 맡는다.
"""
from __future__ import annotations

import importlib
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
m = importlib.import_module("check-code-notation")


class PairedTest(unittest.TestCase):
    """`paired()` — 값 뒤에 «한국어 괄호»가 오면 병기다."""

    def test_병기를_센다(self):
        both, solo = m.paired("공정 유형은 `MACHINING`(가공) 이다.", "MACHINING")
        self.assertEqual((both, solo), (1, 0))

    def test_단독을_센다(self):
        both, solo = m.paired("공정 유형은 `MACHINING` 이다.", "MACHINING")
        self.assertEqual((both, solo), (0, 1))

    def test_backtick_이_없어도_본다(self):
        both, _ = m.paired("값 = MACHINING(가공)", "MACHINING")
        self.assertEqual(both, 1)

    def test_영문_괄호는_병기가_아니다(self):
        """⛔ `DAY`(daily) 는 뜻풀이가 아니다 — 한국어가 있어야 병기다."""
        both, solo = m.paired("`DAY`(daily) 로 센다", "DAY")
        self.assertEqual((both, solo), (0, 1))

    def test_전각_괄호도_병기다(self):
        both, _ = m.paired("`MONTH`（월）", "MONTH")
        self.assertEqual(both, 1)

    def test_한_문서의_여러_자리를_각각_센다(self):
        text = "`DAY`(일) 로 두고 뒤에서 `DAY` 를 다시 쓴다."
        both, solo = m.paired(text, "DAY")
        self.assertEqual((both, solo), (1, 1))

    def test_부분_일치는_세지_않는다(self):
        """⛔ `MONTHLY` 안의 `MONTH` 를 세면 안 된다 — 낱말 경계를 본다."""
        both, solo = m.paired("점검 주기는 `MONTHLY` 다", "MONTH")
        self.assertEqual((both, solo), (0, 0))

    def test_멀리_떨어진_괄호는_병기가_아니다(self):
        both, solo = m.paired("`DAY` 를 쓴다. 그런데 이것은 (일) 을 뜻한다", "DAY")
        self.assertEqual((both, solo), (0, 1))


class LiteralKoreanTest(unittest.TestCase):
    """㉠ — 계약 `enum` 에 한국어가 박히면 ⛔."""

    def test_enum_한국어를_잡는다(self):
        doc = {"components": {"schemas": {"S": {"properties": {
            "statusCode": {"enum": ["작성중", "확정"]}}}}}}
        self.assertEqual(len(m.literal_korean(doc)), 2)

    def test_영문_enum_은_통과한다(self):
        doc = {"components": {"schemas": {"S": {"properties": {
            "statusCode": {"enum": ["DRAFT", "CONFIRMED"]}}}}}}
        self.assertEqual(m.literal_korean(doc), [])

    def test_example_은_보지_않는다(self):
        """⛔ 자리채움은 `check-example-placeholder.py` 소관이다 — 게이트를 둘로 두지 않는다."""
        doc = {"components": {"schemas": {"S": {"properties": {
            "reasonCode": {"x-code-key": "CD-X", "example": "값"}}}}}}
        self.assertEqual(m.literal_korean(doc), [])

    def test_설명문의_한국어는_값이_아니다(self):
        doc = {"components": {"schemas": {"S": {"properties": {
            "statusCode": {"description": "상태 — 작성중·확정", "enum": ["DRAFT"]}}}}}}
        self.assertEqual(m.literal_korean(doc), [])

    def test_배열_items_안의_enum_도_본다(self):
        inner = {"type": "array", "items": {"properties": {"c": {"enum": ["보류"]}}}}
        body = {"content": {"application/json": {"schema": inner}}}
        doc = {"paths": {"/x": {"get": {"responses": {"200": body}}}}}
        self.assertEqual(len(m.literal_korean(doc)), 1)


class StripHistoryTest(unittest.TestCase):
    """이력·회고 절은 그 시점의 기록이라 지금 규칙으로 재단하지 않는다."""

    def test_변경_이력_절을_지운다(self):
        text = "## 본문\n`DAY` 를 쓴다\n\n## 변경 이력\n`MONTH` 를 썼었다\n"
        out = m.strip_history(text)
        self.assertIn("DAY", out)
        self.assertNotIn("MONTH", out)

    def test_이력_다음_절은_다시_본다(self):
        text = "## 변경 이력\n`MONTH`\n\n## 부록\n`DAY`\n"
        out = m.strip_history(text)
        self.assertNotIn("MONTH", out)
        self.assertIn("DAY", out)

    def test_이력_절이_없으면_그대로다(self):
        text = "## 본문\n`DAY`\n"
        self.assertIn("DAY", m.strip_history(text))


class DictionaryKoreanTest(unittest.TestCase):
    """사전 「값」 열 — ⬜ 행은 건너뛴다."""

    def _write(self, body):
        p = os.path.join(HERE, "__test_dict.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)
        self.addCleanup(os.remove, p)
        return p

    def test_값_열의_한국어를_잡는다(self):
        p = self._write("| `CD-X` | `정상` `불량` | `G` | `c` | `enum` | 2 | 근거 |\n")
        self.assertEqual(len(m.dictionary_korean(p)), 1)

    def test_영문_값은_통과한다(self):
        p = self._write("| `CD-X` | `NORMAL` `DEFECTIVE` | `G` | `c` | `enum` | 2 | 근거 |\n")
        self.assertEqual(m.dictionary_korean(p), [])

    def test_미상_표시는_건너뛴다(self):
        """⛔ ⬜ 「미상」은 코드가 아니라 «값이 없다»는 상태 표기다."""
        p = self._write("| `CD-X` | ⬜ **미상** | `G` | `c` | `registry` | 0 | 근거 |\n")
        self.assertEqual(m.dictionary_korean(p), [])

    def test_일곱_열이_아닌_표는_보지_않는다(self):
        p = self._write("| `CD-X` | `정상` | 근거 |\n")
        self.assertEqual(m.dictionary_korean(p), [])


class ScanProseTest(unittest.TestCase):
    """`scan_prose()` — want_pair 로 두 방향을 가른다."""

    def _write(self, name, body):
        p = os.path.join(HERE, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(body)
        self.addCleanup(os.remove, p)
        return p

    def test_병기_안_한_자리를_센다(self):
        p = self._write("__t1.md", "`MACHINING` 이다\n")
        got = m.scan_prose([p], {"MACHINING"}, want_pair=True)
        self.assertEqual(got[0][2], 1)

    def test_병기한_자리를_센다(self):
        p = self._write("__t2.md", "`MACHINING`(가공) 이다\n")
        got = m.scan_prose([p], {"MACHINING"}, want_pair=False)
        self.assertEqual(got[0][2], 1)

    def test_없는_값은_안_센다(self):
        p = self._write("__t3.md", "아무것도 없다\n")
        self.assertEqual(m.scan_prose([p], {"MACHINING"}, want_pair=True), [])


class NoiseTest(unittest.TestCase):
    """흔한 약어는 값으로 세지 않는다 — 래칫의 잡음을 줄인다."""

    def test_API_는_잡음_목록에_있다(self):
        self.assertIn("API", m.NOISE)

    def test_실제_코드값은_잡음이_아니다(self):
        for v in ("MACHINING", "EMPLOYED", "NORMAL"):
            self.assertNotIn(v, m.NOISE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
