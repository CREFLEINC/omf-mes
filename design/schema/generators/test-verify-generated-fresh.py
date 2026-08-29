#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# verify-generated-fresh.py 의 단위 테스트. 표준 라이브러리만 쓴다.
#
# 이 검사기는 「커밋된 생성물이 원본과 갈렸는가」를 본다. 2026-08-27 까지 «마크다운
# 축»만 있었고 HTML 배포본 9건은 아무도 안 봤다(omf-mes#248) — 그래서 PR #288 안에서
# 배포본이 낡은 채로 초록이 났다. 그 축을 여기서 잠근다. 잠그는 것은 셋이다:
#   ① 짝 표를 «생성기의 선언»에서 가져온다 — 파일명 매칭이면 이름이 다른 짝을 놓친다
#   ② 04 두 건의 SRC/DST 를 정규식으로 «정적으로» 읽는다 — 생성기가 바뀌면 여기서 깨진다
#   ③ 배포본을 다시 만들어 비교한 뒤 «어떤 경우에도» 되돌린다
#
# ⛔ ③ 은 저장소의 실제 배포본을 쓰지 않는다 — 19.6MB 를 9번 다시 만들 이유도 없고,
#    시험이 저장소를 건드리면 안 된다. html_targets() 를 임시 트리로 갈아 끼워 돌린다.
import hashlib
import importlib
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
fresh = importlib.import_module("verify-generated-fresh")


def _sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class HtmlTargetsTest(unittest.TestCase):
    def test_짝이_아홉이다(self):
        # build-doc-html.py CONFIG 7 + 04 생성기 2 = 9.
        self.assertEqual(len(fresh.html_targets()), 9)

    def test_이름이_다른_짝을_담는다(self):
        # ⛔ 파일명 매칭으로는 못 잡는 짝 — 00-요구사항명세서.md → 01-요구사항명세서.html
        pairs = {(os.path.basename(src), os.path.basename(dst))
                 for src, dst, _ in fresh.html_targets()}
        self.assertIn(("00-요구사항명세서.md", "01-요구사항명세서.html"), pairs)

    def test_재생성_명령이_붙어_있다(self):
        for src, dst, cmd in fresh.html_targets():
            self.assertTrue(cmd[0] and cmd[1].endswith(".py"), cmd)

    def test_배포본_경로가_실재한다(self):
        for _, dst, _ in fresh.html_targets():
            self.assertTrue(os.path.exists(dst), dst)


class IaPairTest(unittest.TestCase):
    def test_도식본_짝을_소스에서_읽는다(self):
        # 정규식이 생성기 변경에 깨지면 여기서 잡힌다.
        self.assertEqual(fresh._ia_pair("build-04-ia-도식본.py"),
                         ("04-통합-IA.md", "04-통합-IA-도식본.html"))

    def test_html판_짝도_읽는다(self):
        self.assertEqual(fresh._ia_pair("build-04-ia-html.py"),
                         ("04-통합-IA.md", "04-통합-IA.html"))


class CheckHtmlTest(unittest.TestCase):
    """배포본을 1바이트 바꿔 두고 — 낡은 것을 세고, 되돌리는가."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.src = os.path.join(self.tmp, "원본.md")
        self.dst = os.path.join(self.tmp, "배포본.html")
        # 「생성기」 — 원본에서 배포본을 만든다. 결정적이다.
        self.gen = os.path.join(self.tmp, "가짜생성기.py")
        io.open(self.gen, "w", encoding="utf-8").write(
            "import io\n"
            "io.open(%r, 'w', encoding='utf-8').write("
            "'<html>' + io.open(%r, encoding='utf-8').read() + '</html>')\n"
            % (self.dst, self.src))
        io.open(self.src, "w", encoding="utf-8").write("본문")
        self._원래대로()

        self._saved = fresh.html_targets
        fresh.html_targets = lambda: [(self.src, self.dst,
                                       [sys.executable, self.gen])]
        self.addCleanup(setattr, fresh, "html_targets", self._saved)

    def _원래대로(self):
        io.open(self.dst, "w", encoding="utf-8").write("<html>본문</html>")

    def test_같으면_0을_돌려준다(self):
        self.assertEqual(fresh.check_html(), 0)

    def test_한_바이트_다르면_1을_돌려준다(self):
        io.open(self.dst, "w", encoding="utf-8").write("<html>본문 </html>")
        self.assertEqual(fresh.check_html(), 1)

    def test_검사_뒤_파일이_원래대로다(self):
        io.open(self.dst, "w", encoding="utf-8").write("<html>본문 </html>")
        before = _sha(self.dst)
        fresh.check_html()
        self.assertEqual(_sha(self.dst), before)   # ⛔ 저장소를 바꾸지 않는다

    def test_배포본이_없으면_낡은_것으로_센다(self):
        os.remove(self.dst)
        self.assertEqual(fresh.check_html(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
