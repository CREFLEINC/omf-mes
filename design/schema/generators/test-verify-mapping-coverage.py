#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# verify-mapping-coverage.py 의 단위 테스트. 표준 라이브러리만 쓴다.
#
# 이 검사기가 커버리지를 최종 판정하므로, 잘못 통과시키는 쪽(위양성)을
# 특히 잠근다 — 빠진 액션을 ✅ 로 넘기면 프론트가 부를 수 없는 화면이 나간다.
import os, sys, unittest, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
mc = importlib.import_module("verify-mapping-coverage")

LIST = """# UI 요구 목록

## W-01-03

| 액션 | 활성 조건 |
| --- | --- |
| 분리 등록 | 필수 충족 |
| 취소 | 항상 |
"""

DOC_OK = """### 3-2. `W-01-03` 초과 입하 분리

| 화면 액션 | 엔드포인트 | 근거 |
| --- | --- | --- |
| **분리 등록** | `POST /logistics/inbound-receipts:split` | §5-1 |
| 취소 | **API 불필요** | §5-1 |
"""

# 「취소」가 매핑표에는 없고 산문에만 있다. 소절 본문 전체를 대조하면 통과한다.
DOC_PROSE_ONLY = """### 3-2. `W-01-03` 초과 입하 분리

| 화면 액션 | 엔드포인트 | 근거 |
| --- | --- | --- |
| **분리 등록** | `POST /logistics/inbound-receipts:split` | §5-1 |

- 취소는 화면 이탈이라 서버를 부르지 않는다.
"""


def _write(tmpdir, name, text):
    path = os.path.join(tmpdir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


class ParseTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()

    def test_요구목록에서_화면과_액션을_읽는다(self):
        path = _write(self.tmp, "list.md", LIST)
        self.assertEqual(mc.list_actions(path),
                         [("W-01-03", "분리 등록"), ("W-01-03", "취소")])

    def test_헤더행과_구분선은_액션이_아니다(self):
        path = _write(self.tmp, "list.md", LIST)
        acts = [a for _, a in mc.list_actions(path)]
        self.assertNotIn("액션", acts)
        self.assertFalse(any(a.startswith("---") for a in acts))

    def test_요구서에서_화면별_소절을_가른다(self):
        path = _write(self.tmp, "doc.md", DOC_OK)
        sections = mc.doc_sections(path)
        self.assertEqual(list(sections), ["W-01-03"])


class MatchTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()
        self.list_path = _write(self.tmp, "list.md", LIST)

    def _missing(self, doc_text):
        doc = _write(self.tmp, "doc.md", doc_text)
        return mc.missing(mc.list_actions(self.list_path), mc.doc_sections(doc))

    def test_매핑표에_있으면_통과한다(self):
        self.assertEqual(self._missing(DOC_OK), [])

    def test_산문에만_있으면_통과시키지_않는다(self):
        # 위양성 잠금 — 소절 본문 전체를 대조하는 코드로는 실패해야 한다.
        gaps = self._missing(DOC_PROSE_ONLY)
        self.assertEqual([(s, a) for s, a, _ in gaps], [("W-01-03", "취소")])

    def test_굵은표기를_넘어서_대조한다(self):
        # 요구서는 「**분리 등록**」, 목록은 「분리 등록」이다.
        self.assertEqual([a for _, a, _ in self._missing(DOC_OK)], [])

    def test_슬래시로_묶은_행을_인정한다(self):
        doc = """### 3-2. `W-01-03` 초과 입하 분리

| 화면 액션 | 엔드포인트 | 근거 |
| --- | --- | --- |
| 분리 등록 / 취소 | 각각 | §5-1 |
"""
        self.assertEqual(self._missing(doc), [])

    def test_화면_소절이_통째로_없으면_결손이다(self):
        gaps = self._missing("### 3-1. `W-01-09` 입하 예정 조회\n")
        self.assertEqual(len(gaps), 2)
        self.assertTrue(all("소절이 없다" in why for _, _, why in gaps))


class RealArtifactTest(unittest.TestCase):
    # 저장소의 실제 산출물이 통과 상태인지 잠근다.
    def test_세_도메인_모두_전건_다뤘다(self):
        for domain in ("mdm", "01", "app"):
            with self.subTest(domain=domain):
                self.assertEqual(mc.check(domain), 0)

    def test_기본_도메인이_짝과_같다(self):
        cov = importlib.import_module("verify-ui-coverage")
        self.assertIn(mc.DEFAULT_DOMAIN, cov.DOMAINS)
        self.assertEqual(mc.DEFAULT_DOMAIN, "mdm")

    def test_도메인_등록부를_한_곳에서_읽는다(self):
        cov = importlib.import_module("verify-ui-coverage")
        self.assertEqual(sorted(mc.DOMAINS), sorted(cov.DOMAINS))


if __name__ == "__main__":
    unittest.main(verbosity=2)
