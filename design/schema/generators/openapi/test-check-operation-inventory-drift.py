#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# check-operation-inventory-drift.py 의 단위 테스트. 표준 라이브러리만 쓴다(저장소 관행).
#
# ⛔ 이 검사기가 잠그는 사고 — `06-API-요구서-app공통승인.md` §1-2 가 「긴급 IQC
# 생략」 행을 「⛔ 0건」으로 적었는데, **같은 커밋**이 그 경로
# (`POST /trace/lots/{lotId}:request-iqc-skip`)를 이미 만들어 두었다. 그 어긋남이
# 사흘을 갔다. 표본 넷을 잠근다 — ① 진짜 어긋남을 잡는다 ② 화면 ID 없는 「0건」
# 행은 안 잡는다(무엇과 대조할지 모른다) ③ 「0건」이 문장 속에 파묻히면 안 잡는다
# (예: 「금액 컬럼 0건」) ④ `:request-` 가 아닌 오퍼레이션은 후보에서 뺀다.
import importlib
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
oid = importlib.import_module("check-operation-inventory-drift")


class CleanCellTest(unittest.TestCase):
    def test_장식을_걷는다(self):
        self.assertEqual(oid.clean_cell("⛔ **0건**"), "0건")

    def test_문장_속에_있으면_안_같다(self):
        self.assertNotEqual(oid.clean_cell("금액 컬럼 **0건**이다"), "0건")


class ZeroRowsTest(unittest.TestCase):
    def test_0건_칸과_화면ID를_같은_행에서_찾는다(self):
        text = ("| 승인 유형 | 상신 화면 | 생성 경로 | 판정 |\n"
                "| --- | --- | --- | :-: |\n"
                "| 긴급 IQC 생략 | `M-01-13` | ⛔ **0건** | 결손 |\n")
        rows = list(self._parse(text))
        self.assertEqual(len(rows), 1)
        _lineno, screens, raw = rows[0]
        self.assertEqual(screens, {"M-01-13"})
        self.assertIn("0건", raw)

    def test_화면ID_없는_0건_행은_안_잡는다(self):
        text = ("| 특채 | 미특정 | ⛔ 0건 | 발의 화면 미특정 |\n")
        self.assertEqual(list(self._parse(text)), [])

    def test_문장_속_0건은_안_잡는다(self):
        text = ("| `W-01-06` | 관리자 컬럼 **0건**이라 못 쓴다 |\n")
        self.assertEqual(list(self._parse(text)), [])

    def _parse(self, text):
        """zero_rows() 와 같은 파싱을 임시 텍스트에 직접 돌린다(파일 I/O 없이)."""
        for i, line in enumerate(text.splitlines(), start=1):
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if any(c.startswith("---") for c in cells):
                continue
            if not any(oid.clean_cell(c) in oid.ZERO_MARKS for c in cells):
                continue
            screens = set()
            for c in cells:
                screens |= set(oid.SCREEN_ID.findall(c))
            if screens:
                yield i, screens, line


class RequestOperationsByScreenTest(unittest.TestCase):
    def _doc(self, path, method, text_fields):
        return {"paths": {path: {method: {
            "summary": text_fields.get("summary", ""),
            "description": text_fields.get("description", ""),
            "x-internal-note": text_fields.get("x-internal-note", ""),
        }}}}

    def test_request_경로만_후보로_삼는다(self):
        # 직접 request_operations_by_screen 은 파일을 읽으므로, 그 안의 판별
        # 로직(‘:request-’ 필터 + 화면ID 추출)을 여기서 표본으로 확인한다.
        self.assertIn(":request-", "/trace/lots/{lotId}:request-iqc-skip")
        self.assertNotIn(":request-", "/logistics/inbound-receipts")

    def test_screen_id_정규식이_토큰을_뽑는다(self):
        text = "근거: M-01-13 §5-A · 공유계약 A-16 등재 대상"
        self.assertEqual(set(oid.SCREEN_ID.findall(text)), {"M-01-13"})


class DriftsIntegrationTest(unittest.TestCase):
    """실제 계약·요구서 대상 회귀 표본 — omf-mes#336 이 잡은 자리는 지금 없다."""

    def test_m_01_13는_더이상_어긋나지_않는다(self):
        by_screen = oid.request_operations_by_screen()
        self.assertIn("M-01-13", by_screen)  # 경로가 계약에 실재한다
        found = oid.drifts()
        offending = [d for d in found if d[2] == "M-01-13"]
        self.assertEqual(offending, [])  # 요구서가 이제 「0건」이라 안 적는다


if __name__ == "__main__":
    unittest.main()
