#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# verify-stale-terms.py 의 단위 테스트. 표준 라이브러리만 쓴다.
#
# 이 검사기는 「표기를 바꾼 뒤 옛 이름이 남았는가」를 본다(omf-mes#250). 판정이 정규식
# 넷 + diff 라 오탐·미탐이 조용히 난다. 잠그는 것은 다섯이다:
#   ① 삭제줄에만 있는 구가 다른 파일에 남아 있으면 잡는다
#   ② 잔존 표기가 더 길어도 잡는다(구 「스캐너 연결」 ⊆ 「스캐너 연결 상태」) — 비대칭 대조
#   ③ ⛔ 취소선을 «추가줄에서도» 걷어낸다 — 안 걷으면 옛 이름이 되살아나 미탐이 된다
#   ④ 정합주·상세 이력 절·구표기 보존은 보고하지 않는다
#   ⑤ 조사·어미로 끝나는 조각은 후보에 들어오지 않는다
#
# ⛔ omf-mes#244 의 커밋 SHA 에 의존하지 않는다 — 스쿼시 병합이라 그 6건이 로컬 클론에
#    없다(git cat-file -t 실패). 아래 줄 내용을 그대로 옮긴 임시 트리로 만든다.
# ⛔ 임시 git 저장소도 만들지 않는다 — at_ref() 를 갈아 끼워 기준 시점을 흉내 낸다.
import importlib
import io
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
stale = importlib.import_module("verify-stale-terms")

# ── 픽스처 — omf-mes#244 회귀의 실제 줄이다 ───────────────────────────────
바뀐줄_기준 = "| 언어 전환 · 스캐너 연결 | ⛔ 저장하지 않는 것이 맞다 — 공용 장비다 | §5-3·§5-4 |"
바뀐줄_지금 = "| 언어 전환 · 스캐너 준비 상태 | ⛔ 저장하지 않는 것이 맞다 — 공용 장비다 | §5-3·§5-4 |"
# ⭐ 취소선 회귀 — 추가줄의 ~~…~~ 안에서 옛 이름이 되살아난다.
취소선_기준 = ("| 12 | 모바일 디바이스 기종 선정 — 베트남 현지 구매·OS=Android 확정 "
               "🔹·부착형 스캐너 호환성 | CREFLE·고객 | HW 스펙 §7 #4 |")
취소선_지금 = ("| 12 | 모바일 디바이스 기종 선정 — 베트남 현지 구매·OS=Android 확정 "
               "🔹·~~부착형 스캐너 호환성~~ → **일체형 단말의 스캔값 도착 형태** "
               "| CREFLE·고객 | HW 스펙 §7 #4 |")

기준트리 = {
    os.path.join("design", "wiki", "screens", "공통", "M-CO-01.md"):
        "# 기기 등록\n" + 바뀐줄_기준 + "\n",
    os.path.join("design", "wiki", "project-spec", "02-SW설계사양서.md"):
        "# SW 설계\n" + 취소선_기준 + "\n",
}

작업트리 = {
    os.path.join("design", "wiki", "screens", "공통", "M-CO-01.md"):
        "# 기기 등록\n" + 바뀐줄_지금 + "\n",
    os.path.join("design", "wiki", "project-spec", "02-SW설계사양서.md"):
        "# SW 설계\n" + 취소선_지금 + "\n",
    # 안 바뀐 파일 — 여기에 옛 이름이 남아 있다(잔존줄 셋).
    os.path.join("design", "wiki", "screens", "01", "M-01-02.md"):
        "# 자재 LOT 스캔\n"
        + 바뀐줄_기준 + "\n"
        + "| 스캐너 연결 상태 = `Chip` | a |\n"
        + "| 현지 조달 기종 조사(부착형 스캐너 호환성). 제안서 #6과 동일 계열 |\n",
    # 보고되면 안 되는 자리들.
    os.path.join("design", "wiki", "decisions-policy", "공유계약.md"):
        "# 공유계약\n"
        "- 스캐너 연결 상태 표시 «(정합주: 2026-08-26 준비 상태로 바꿨다 · #442)»\n"
        "- 스캐너 연결 상태 표시 «(구표기 보존)»\n"
        "- ~~스캐너 연결~~ → **스캐너 준비 상태**\n"
        "### 상세 이력 (v3.0~v4.4, 행 분리 대기)\n"
        "- 스캐너 연결 상태 표시 신설(v3.1)\n",
}


class 픽스처(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        for rel, body in 작업트리.items():
            path = os.path.join(self.tmp, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write(body)

        self._root, self._at_ref = stale.ROOT, stale.at_ref
        stale.ROOT = self.tmp
        stale.at_ref = lambda ref, rel: 기준트리.get(rel)
        self.addCleanup(setattr, stale, "ROOT", self._root)
        self.addCleanup(setattr, stale, "at_ref", self._at_ref)

    def 보고(self):
        gone, _ = stale.gone_phrases("기준")
        return stale.scan(gone), gone


class 검출Test(픽스처):
    def test_삭제줄에만_있는_구가_남아_있으면_잡는다(self):
        findings, gone = self.보고()
        self.assertIn("스캐너 연결", gone)
        자리 = {(rel, number) for rel, number, phrase in findings
                if phrase == "스캐너 연결"}
        self.assertIn((os.path.join("design", "wiki", "screens", "01", "M-01-02.md"), 2),
                      자리)

    def test_잔존_표기가_더_길어도_잡는다(self):
        # ⛔ 구 단위 완전일치로 하면 「스캐너 연결 상태」를 놓친다 — 2단계는 부분문자열이다.
        findings, _ = self.보고()
        self.assertIn(
            (os.path.join("design", "wiki", "screens", "01", "M-01-02.md"), 3,
             "스캐너 연결"), findings)

    def test_추가줄의_취소선을_걷어야_잡힌다(self):
        findings, gone = self.보고()
        self.assertIn("부착형 스캐너 호환성", gone)
        self.assertIn(
            (os.path.join("design", "wiki", "screens", "01", "M-01-02.md"), 4,
             "부착형 스캐너 호환성"), findings)

    def test_안_걷으면_미탐이_된다(self):
        # 이 시험이 ③ 의 «이유»다 — 걷어내기를 끄면 옛 이름이 추가줄에서 되살아나
        # 삭제-전용 집합에서 탈락한다(프로토타입 실측 2/3).
        원래 = stale.strip_spans
        stale.strip_spans = lambda line: stale.NOTE_SPAN.sub(" ", line)
        try:
            gone, _ = stale.gone_phrases("기준")
        finally:
            stale.strip_spans = 원래
        self.assertNotIn("부착형 스캐너 호환성", gone)


class 오탐잠금Test(픽스처):
    def 공유계약_보고(self):
        findings, _ = self.보고()
        rel = os.path.join("design", "wiki", "decisions-policy", "공유계약.md")
        return {number for f, number, _ in findings if f == rel}

    def test_정합주가_붙은_줄은_보고하지_않는다(self):
        self.assertNotIn(2, self.공유계약_보고())

    def test_구표기_보존이_붙은_줄은_보고하지_않는다(self):
        self.assertNotIn(3, self.공유계약_보고())

    def test_취소선_안에만_있으면_보고하지_않는다(self):
        self.assertNotIn(4, self.공유계약_보고())

    def test_상세_이력_절은_보고하지_않는다(self):
        # 제목에 부기(v3.0~v4.4, 행 분리 대기)가 붙어 있어도 걸러야 한다.
        self.assertNotIn(6, self.공유계약_보고())

    def test_바뀐_줄_자신은_보고하지_않는다(self):
        # 새 표기(스캐너 준비 상태)는 gone 이 아니다.
        findings, _ = self.보고()
        self.assertEqual([], [f for f in findings if "준비" in f[2]])

    def test_양쪽에_다_있는_구는_gone_이_아니다(self):
        _, gone = self.보고()
        self.assertNotIn("언어 전환", gone)


class 구뽑기Test(unittest.TestCase):
    def test_조사_어미로_끝나는_조각은_후보가_아니다(self):
        뽑힌 = stale.phrases("| 값 확정 시 | 지금은 | 표시만 | 반영이 된다 |")
        self.assertEqual(set(), 뽑힌)

    def test_토큰_두개는_후보다(self):
        self.assertIn("스캐너 연결", stale.phrases("| 언어 전환 · 스캐너 연결 |"))

    def test_토큰_셋이면_뒤_두토큰도_후보다(self):
        뽑힌 = stale.phrases("| 부착형 스캐너 호환성 |")
        self.assertIn("부착형 스캐너 호환성", 뽑힌)
        self.assertIn("스캐너 호환성", 뽑힌)

    def test_토큰_여섯은_후보가_아니다(self):
        # 잡음이 상위를 덮으면 사람이 검사기를 끈다 — 긴 조각은 안 쓴다.
        self.assertEqual(set(), stale.phrases(
            "| 모바일 디바이스 부착형 바코드 스캐너 세트 |"))

    def test_취소선_스팬은_구에서_빠진다(self):
        self.assertEqual(set(), stale.phrases("~~부착형 스캐너 호환성~~"))


class 기준시점읽기Test(unittest.TestCase):
    """at_ref() 는 git 을 부른다 — 읽기 전용이라 저장소를 바꾸지 않는다."""

    def test_추적되는_파일을_읽는다(self):
        body = stale.at_ref("HEAD", os.path.join("design", "wiki", "00-index.md"))
        self.assertTrue(body and body.strip())

    def test_없는_파일은_None(self):
        self.assertIsNone(stale.at_ref("HEAD", "없는-파일-입니다.md"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
