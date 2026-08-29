#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# check-dead-path-citations.py 의 --fix 단위 테스트. 표준 라이브러리만 쓴다.
#
# 왜 이 셋인가 — 2026-08-29 실측 사고 때문이다. --fix 가 파일 전체 str.replace 를 써서
# 스캔의 안전장치 «둘 다» 무시했고, 중첩 경로 18건을 만들었다. 손으로 복구했으나 원인
# 코드는 그대로였고 PR #288 리뷰 둘이 각각 같은 자리를 짚었다. 잠그는 것은 셋이다:
#   ① 경계 — 앞 글자가 경로 조각이면 바꾸지 않는다(이미 옮긴 경로를 다시 옮기지 않는다)
#   ② 예외 — 출처 꼬리표·변경 이력 표의 줄은 바꾸지 않는다(시점 기록이라 보존한다)
#   ③ 멱등 — 두 번 돌려도 같다
#
# ⛔ 실제 저장소를 고치지 않는다 — 임시 트리를 만들고 모듈의 ROOT 를 갈아 끼운다.
import importlib
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
dead = importlib.import_module("check-dead-path-citations")

# 지도에 등재된 실제 한 쌍 — 이 경로는 redirect-map 에 있다.
구 = "uiux/2026-08-10-의사결정요청/DR-001-설비툴보전범위.md"
신 = "design/raw/decision-requests/DR-001-설비툴보전범위.md"

본문줄 = "근거: `%s` 를 본다.\n" % 구
경계줄 = "이미 옮겼다: `design/raw/process/%s` 는 그대로 둔다.\n" % 구
출처줄 = "> 출처: `%s` · 최종 대조일: 2026-08-25\n" % 구
이력머리 = "## 변경 이력\n"
이력줄 = "| 2026-01-01 | `%s` 를 지웠다 |\n" % 구


class FixTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.doc = os.path.join(self.tmp, "design", "wiki", "project-spec", "샘플.md")
        os.makedirs(os.path.dirname(self.doc))
        # redirect-map 은 실물을 쓴다 — 지도 형식이 바뀌면 이 테스트도 같이 깨져야 한다.
        os.makedirs(os.path.join(self.tmp, "design", "schema"))
        shutil.copy(os.path.join(dead.ROOT, "design", "schema", "redirect-map.md"),
                    os.path.join(self.tmp, "design", "schema", "redirect-map.md"))
        # 신경로가 실재해야 fixable 로 잡힌다.
        os.makedirs(os.path.join(self.tmp, os.path.dirname(신)))
        with io.open(os.path.join(self.tmp, 신), "w", encoding="utf-8") as fh:
            fh.write("x\n")
        # ⛔ ROOT 만 갈아 끼우면 안 된다 — WIKI·MAP 이 모듈 적재 시점에 ROOT 로부터
        #    계산돼 고정된다. 셋을 함께 바꾼다.
        self._saved = (dead.ROOT, dead.WIKI, dead.MAP)
        dead.ROOT = self.tmp
        dead.WIKI = os.path.join(self.tmp, "design", "wiki")
        dead.MAP = os.path.join(self.tmp, "design", "schema", "redirect-map.md")

    def tearDown(self):
        dead.ROOT, dead.WIKI, dead.MAP = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, *lines):
        with io.open(self.doc, "w", encoding="utf-8") as fh:
            fh.write("".join(lines))

    def _fix(self):
        argv = sys.argv
        sys.argv = ["check-dead-path-citations.py", "--fix"]
        try:
            dead.main()
        finally:
            sys.argv = argv
        with io.open(self.doc, encoding="utf-8") as fh:
            return fh.read()

    def test_본문은_바뀐다(self):
        self._write(본문줄)
        self.assertIn(신, self._fix())

    def test_경계_이미_옮긴_경로는_안_바뀐다(self):
        # ⛔ 파일 전체 replace 면 design/raw/process/design/raw/… 중첩이 난다.
        self._write(본문줄, 경계줄)
        out = self._fix()
        self.assertIn("design/raw/process/" + 구, out)
        self.assertNotIn("design/raw/process/design/raw/", out)

    def test_예외_출처_꼬리표와_변경_이력은_안_바뀐다(self):
        self._write(본문줄, 출처줄, 이력머리, 이력줄)
        out = self._fix()
        self.assertIn(신, out)                      # 본문은 바뀌고
        self.assertIn(출처줄.strip(), out)          # 출처 꼬리표는 그대로
        self.assertIn(이력줄.strip(), out)          # 변경 이력도 그대로

    def test_멱등_두_번_돌려도_같다(self):
        self._write(본문줄, 경계줄, 출처줄)
        once = self._fix()
        self.assertEqual(once, self._fix())


if __name__ == "__main__":
    unittest.main(verbosity=2)
