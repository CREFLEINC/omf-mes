"""#452: 검사 모드가 원본 변경을 감지하고 생성물을 덮어쓰지 않는다."""

import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from generated_output import emit


class GeneratedOutputTest(unittest.TestCase):
    def test_missing_stale_and_fresh(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "output.md"
            self.assertEqual(emit(str(path), "new", True), 1)
            self.assertFalse(path.exists())
            path.write_text("old", encoding="utf-8")
            self.assertEqual(emit(str(path), "new", True), 1)
            self.assertEqual(path.read_text(encoding="utf-8"), "old")
            self.assertEqual(emit(str(path), "new"), 0)
            self.assertEqual(emit(str(path), "new", True), 0)

    def test_all_generator_checks_detect_stale_outputs(self):
        for name in ("build-screen-progress", "build-progress-ledger", "build-change-digest"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                module = importlib.import_module(name)
                path = Path(directory) / "output.md"
                path.write_text("stale", encoding="utf-8")
                with patch.object(module, "OUT", str(path)), patch("sys.argv", [name, "--check"]):
                    self.assertEqual(module.main(), 1)
                    self.assertEqual(path.read_text(encoding="utf-8"), "stale")
                with patch.object(module, "OUT", str(path)), patch("sys.argv", [name]):
                    self.assertEqual(module.main(), 0)
                with patch.object(module, "OUT", str(path)), patch("sys.argv", [name, "--check"]):
                    self.assertEqual(module.main(), 0)

    def test_screen_source_change_invalidates_output(self):
        module = importlib.import_module("build-screen-progress")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "screen.md"
            path.write_text(module.generate(), encoding="utf-8")
            before = path.read_bytes()
            names = module.screens_with_names()
            changed = [(sid, name + " 수정") for sid, name in names]
            with patch.object(module, "OUT", str(path)), \
                 patch.object(module, "screens_with_names", return_value=changed), \
                 patch("sys.argv", ["build-screen-progress", "--check"]):
                self.assertEqual(module.main(), 1)
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
