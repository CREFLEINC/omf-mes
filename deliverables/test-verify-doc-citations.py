#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# verify-doc-citations.py 의 단위 테스트. 표준 라이브러리만 쓴다.
#
# 이 검사기는 「요구서가 인용한 경로가 계약에 실재하는가」를 본다(역방향 ②).
# 정규식 판정이 넷이라 오탐·미탐이 조용히 난다 — 실제로 두 갈래를 손으로 잡았다:
#   ① 경로 파라미터 이름 차이(`{id}` ↔ `{purchaseOrderId}`)를 결손으로 셌다
#   ② 한글 자리표시(`/logistics/{문서}/…`)에서 정규식이 끊겨 `/logistics/{` 를 경로로 읽었다
# 그 둘을 여기서 잠근다.
import importlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
cite = importlib.import_module("verify-doc-citations")


def _write(text):
    """임시 마크다운 파일을 만들고 경로를 돌려준다."""
    fd, path = tempfile.mkstemp(suffix=".md")
    with io.open(fd, "w", encoding="utf-8") as f:
        f.write(text)
    return path


class NormalizeTest(unittest.TestCase):
    def test_파라미터_이름을_지운다(self):
        self.assertEqual(cite.normalize("/a/{purchaseOrderId}"), "/a/{}")
        self.assertEqual(cite.normalize("/a/{id}"), "/a/{}")

    def test_이름이_달라도_같아진다(self):
        # 요구서는 {id}, 계약은 {purchaseOrderId} 로 쓴다 — 결손이 아니다.
        self.assertEqual(cite.normalize("/a/{id}/b"), cite.normalize("/a/{purchaseOrderId}/b"))

    def test_파라미터가_여럿이어도_각각_지운다(self):
        self.assertEqual(cite.normalize("/a/{x}/b/{y}"), "/a/{}/b/{}")

    def test_액션_동사는_남긴다(self):
        self.assertEqual(cite.normalize("/a/{id}:confirm"), "/a/{}:confirm")


class CitationsTest(unittest.TestCase):
    def _cite(self, text):
        path = _write(text)
        try:
            return list(cite.citations(path))
        finally:
            os.remove(path)

    def test_평범한_인용을_뽑는다(self):
        rows = self._cite("| 조회 | `GET /quality/inspection-results` | 근거 |\n")
        self.assertEqual(rows, [(1, "GET", "/quality/inspection-results")])

    def test_백틱이_없어도_뽑는다(self):
        rows = self._cite("본문에서 POST /a/b 를 부른다\n")
        self.assertEqual(rows, [(1, "POST", "/a/b")])

    def test_쿼리스트링을_떼어낸다(self):
        rows = self._cite("`GET /a/b?itemId=1`\n")
        self.assertEqual(rows, [(1, "GET", "/a/b")])

    def test_코드펜스_안은_세지_않는다(self):
        # 계약 초안·예시 블록이 인용으로 잡히면 안 된다.
        rows = self._cite("```\nGET /inside/fence\n```\n`GET /outside/fence`\n")
        self.assertEqual([r[2] for r in rows], ["/outside/fence"])

    def test_한글_자리표시는_건너뛴다(self):
        # `/logistics/{문서}/{id}:cancel` 은 여러 리소스를 묶어 쓴 산문이다.
        rows = self._cite("| 취소 | `POST /logistics/{문서}/{id}:cancel` | |\n")
        self.assertEqual(rows, [])

    def test_중괄호가_안_맞으면_건너뛴다(self):
        # 정규식이 비ASCII 에서 끊겨 남긴 조각(`/logistics/{`)을 경로로 읽으면 안 된다.
        rows = self._cite("POST /logistics/{문서\n")
        self.assertEqual(rows, [])

    def test_한글_경로_조각을_흘리지_않는다(self):
        # 정규식 문자군이 ASCII 뿐이라 `/quality/한글` 은 `/quality/` 까지만 잡힌다.
        # 끝이 `/` 인 조각을 그대로 내면 없는 경로를 지어낸 오탐이 된다.
        rows = self._cite("`POST /quality/한글리소스`\n")
        self.assertEqual(rows, [])

    def test_줄번호를_1부터_센다(self):
        rows = self._cite("머리말\n\n`GET /a`\n")
        self.assertEqual(rows[0][0], 3)


class LoadContractsTest(unittest.TestCase):
    def test_계약을_읽어_정규화한_키를_만든다(self):
        contracts = cite.load_contracts()
        self.assertGreater(len(contracts), 100, "계약 경로를 못 읽었다")

    def test_실재하는_경로가_들어_있다(self):
        contracts = cite.load_contracts()
        self.assertIn(("GET", "/quality/inspection-results"), contracts)
        self.assertIn(("POST", "/quality/lot-holds"), contracts)
        self.assertIn(("POST", "/quality/inspection-results/{}:confirm"), contracts)

    def test_만들지_않기로_한_경로는_없다(self):
        # 2단계가 「버튼이 0건이라 만들지 않는다」로 판정한 셋. 조용히 생기면 규약 이탈이다.
        contracts = cite.load_contracts()
        self.assertNotIn(("POST", "/quality/inspection-requests"), contracts)
        self.assertNotIn(("POST", "/quality/defect-records"), contracts)
        self.assertNotIn(("POST", "/quality/concessions"), contracts)

    def test_계약이_어느_파일에_있는지_담는다(self):
        contracts = cite.load_contracts()
        self.assertEqual(contracts[("GET", "/quality/lot-holds")], {"quality-03품질.json"})


class DetectionTest(unittest.TestCase):
    # 검사기의 본래 목적 — 있는 것은 통과시키고 없는 것은 잡는다.
    def _missing(self, text):
        contracts = cite.load_contracts()
        path = _write(text)
        try:
            return [c for c in cite.citations(path) if (c[1], c[2]) not in contracts]
        finally:
            os.remove(path)

    def test_실재하는_인용은_통과한다(self):
        self.assertEqual(self._missing("`GET /quality/inspection-results`\n"), [])

    def test_파라미터_이름이_달라도_통과한다(self):
        self.assertEqual(self._missing("`POST /quality/lot-holds/{id}:release`\n"), [])

    def test_없는_경로를_잡는다(self):
        found = self._missing("`POST /quality/no-such-resource`\n")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][2], "/quality/no-such-resource")

    def test_경로는_있는데_메서드가_없으면_잡는다(self):
        # 실제 사고가 이 형태였다 — 01 계약의 목록 경로에 GET 만 있는데 POST 를 인용했다.
        found = self._missing("`POST /quality/inspection-requests`\n")
        self.assertEqual(len(found), 1)

    def test_03_요구서는_전건_통과한다(self):
        doc = os.path.join(HERE, "06-API-요구서-03품질.md")
        contracts = cite.load_contracts()
        missing = [c for c in cite.citations(doc) if (c[1], c[2]) not in contracts]
        self.assertEqual(missing, [], "03 요구서 인용이 허공을 가리킨다")


if __name__ == "__main__":
    unittest.main(verbosity=2)
