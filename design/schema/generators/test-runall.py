#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runall.py 의 시험. 표준 라이브러리만 쓴다(저장소 관행).

⛔ 여기서 잠그는 것은 «실행기가 지키기로 한 약속» 셋이다.
   ① 쓰는 검사기는 기본 실행에 «없다» — 있으면 검사한 줄 알고 저장소를 바꾼다
   ② 종료 코드가 «합산»된다 — 한 건이라도 빨간데 0 으로 나가면 게이트가 아니다
   ③ 대상이 0건이면 «건너뛴 사실»을 출력한다 — 조용히 빠지면 안 돈 줄 모른다
   ④ 등록부가 실제 검사기 전건을 덮는다 — 등록부가 낡으면 실행기가 «덜» 돈다
"""
from __future__ import annotations

import contextlib
import importlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
runall = importlib.import_module("runall")


def _script(dirpath: str, name: str, body: str) -> str:
    p = os.path.join(dirpath, name)
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(body)
    return p


@contextlib.contextmanager
def _registry(readers=None, targeted=None, writers=None, root=None):
    """등록부를 갈아 끼운다 — 실제 검사기 30종을 돌리지 않고 «실행기»만 본다."""
    keep = (runall.READERS, runall.TARGETED, runall.WRITERS, runall.ROOT)
    runall.READERS = readers if readers is not None else []
    runall.TARGETED = targeted if targeted is not None else []
    runall.WRITERS = writers if writers is not None else []
    if root:
        runall.ROOT = root
    try:
        yield
    finally:
        runall.READERS, runall.TARGETED, runall.WRITERS, runall.ROOT = keep


def _main(argv: list[str]) -> tuple[int, str]:
    keep = sys.argv
    sys.argv = ["runall.py"] + argv
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = runall.main()
    finally:
        sys.argv = keep
    return rc, buf.getvalue()


class WriterExclusionTest(unittest.TestCase):
    """① 쓰는 검사기는 기본 실행에 «없다»."""

    def test_기본_실행은_쓰는_검사기를_돌리지_않는다(self):
        with tempfile.TemporaryDirectory() as d:
            mark = os.path.join(d, "썼다.txt")
            _script(d, "writer.py",
                    "open(%r, 'w').write('x')\n" % mark)
            with _registry(writers=[("writer.py", [], "✍ 시험용")], root=d):
                rc, out = _main([])
            self.assertFalse(os.path.exists(mark),
                             "기본 실행이 쓰는 검사기를 돌렸다 — 저장소가 조용히 바뀐다")
            self.assertEqual(rc, 0)
            self.assertIn("건너뛴 것", out)
            self.assertIn("writer.py", out)

    def test_include_writers_를_주면_돌린다(self):
        with tempfile.TemporaryDirectory() as d:
            mark = os.path.join(d, "썼다.txt")
            _script(d, "writer.py", "open(%r, 'w').write('x')\n" % mark)
            with _registry(writers=[("writer.py", [], "✍ 시험용")], root=d):
                _main(["--include-writers"])
            self.assertTrue(os.path.exists(mark))

    def test_실제_등록부에서_verify_generated_fresh_는_쓰는_쪽이다(self):
        # 이 검사기는 다시 만들어 보고 되돌린다 — 도중에 작업 트리를 쓴다.
        readers = {p for p, _a, _n in runall.READERS}
        writers = {p for p, _a, _n in runall.WRITERS}
        rel = "design/schema/generators/verify-generated-fresh.py"
        self.assertIn(rel, writers)
        self.assertNotIn(rel, readers)

    def test_실제_등록부에서_verify_ui_coverage_에_write_를_주지_않는다(self):
        # ⛔ --write 를 주면 검사기가 아니라 생성기가 된다.
        for rel, args, _n in runall.READERS:
            if rel.endswith("verify-ui-coverage.py"):
                self.assertNotIn("--write", args)
                break
        else:
            self.fail("verify-ui-coverage.py 가 읽기 전용 목록에 없다")

    def test_실제_등록부에서_collect_open_items_에_check_를_준다(self):
        # ⛔ 인자 없이 돌리면 미결 대장을 덮어쓴다.
        for rel, args, _n in runall.READERS:
            if rel.endswith("collect-open-items.py"):
                self.assertIn("--check", args)
                break
        else:
            self.fail("collect-open-items.py 가 읽기 전용 목록에 없다")


class ExitCodeSumTest(unittest.TestCase):
    """② 종료 코드가 «합산»된다."""

    def test_종료_코드를_합산한다(self):
        with tempfile.TemporaryDirectory() as d:
            _script(d, "a.py", "import sys; sys.exit(2)\n")
            _script(d, "b.py", "import sys; sys.exit(3)\n")
            _script(d, "c.py", "print('ok')\n")
            with _registry(readers=[("a.py", [], ""), ("b.py", [], ""),
                                    ("c.py", [], "")], root=d):
                rc, out = _main([])
            self.assertEqual(rc, 5, out)
            self.assertIn("종료 코드 합 = 5", out)
            self.assertIn("⛔ 실패 2", out)

    def test_전부_초록이면_0_이다(self):
        with tempfile.TemporaryDirectory() as d:
            _script(d, "a.py", "print('✅')\n")
            with _registry(readers=[("a.py", [], "")], root=d):
                rc, _out = _main([])
            self.assertEqual(rc, 0)

    def test_합이_125_를_넘으면_자른다(self):
        # 셸 종료 코드는 1바이트다 — 넘치면 0 으로 «되감겨» 거짓 초록이 난다.
        with tempfile.TemporaryDirectory() as d:
            for i in range(3):
                _script(d, "x%d.py" % i, "import sys; sys.exit(100)\n")
            with _registry(readers=[("x%d.py" % i, [], "") for i in range(3)], root=d):
                rc, out = _main([])
            self.assertEqual(rc, 125)
            self.assertIn("종료 코드 합 = 300", out)

    def test_파일이_없으면_실패로_센다(self):
        with tempfile.TemporaryDirectory() as d:
            with _registry(readers=[("없다.py", [], "")], root=d):
                rc, out = _main([])
            self.assertEqual(rc, 1)
            self.assertIn("등록부가 낡았다", out)

    def test_경고_건수를_센다(self):
        with tempfile.TemporaryDirectory() as d:
            _script(d, "w.py", "print('⚠ 하나')\nprint('⚠ 둘')\nprint('보통 줄')\n")
            with _registry(readers=[("w.py", [], "")], root=d):
                rc, out = _main([])
            self.assertEqual(rc, 0)
            self.assertIn("⚠ 2건", out)


class SkipIsLoudTest(unittest.TestCase):
    """③ 대상이 0건이면 «건너뛴 사실»을 출력한다."""

    def test_대상이_0건이면_건너뛴_사실을_출력한다(self):
        with tempfile.TemporaryDirectory() as d:
            _script(d, "t.py", "print('돌았다')\n")
            with _registry(targeted=[("t.py", ["없는폴더/*.md"], "시험용")], root=d):
                rc, out = _main([])
            self.assertEqual(rc, 0)
            self.assertIn("건너뛴 것 1건", out)
            self.assertIn("대상 0건", out)
            self.assertNotIn("돌았다", out)

    def test_대상이_있으면_인자로_넘긴다(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "대상"))
            _script(d, os.path.join("대상", "a.md"), "본문\n")
            _script(d, "t.py", "import sys; print('받은 인자:', sys.argv[1:])\n")
            with _registry(targeted=[("t.py", ["대상/*.md"], "시험용")], root=d):
                rc, out = _main([])
            self.assertEqual(rc, 0)
            self.assertIn("대상/a.md", out)


class RegistryCoverageTest(unittest.TestCase):
    """④ 등록부가 실제 검사기 전건을 덮는다."""

    def test_등록부에_없는_검사기가_없다(self):
        miss = runall.unregistered()
        self.assertEqual(miss, [], "등록부에 없는 검사기: %s" % miss)

    def test_등록된_파일이_전부_실재한다(self):
        for rel in sorted(runall.registered_paths()):
            self.assertTrue(os.path.exists(os.path.join(runall.ROOT, rel)), rel)

    def test_design_raw_는_등록부에_없다(self):
        # ⛔ raw/ 는 시점 고착본이다 — 돌리지 않는다(design/README.md).
        for rel in runall.registered_paths():
            self.assertFalse(rel.startswith("design/raw/"), rel)


if __name__ == "__main__":
    unittest.main(verbosity=2)
