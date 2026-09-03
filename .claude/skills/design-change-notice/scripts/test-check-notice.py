#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check-notice.py · build-notice.py 시험.

    python3 .claude/skills/design-change-notice/scripts/test-check-notice.py

무엇을 잠그나
-------------
- 공개 안전(P) — 옛 check-issue.py 시험(PublicSafetySplit·DraftResidue)을 **함수 직접 호출**로 옮겼다.
  옛 시험은 `--reply`·`--private`·`--change-notice` 모드를 돌렸는데 그 모드들은 V3 로 사라졌다.
  남은 것은 「같은 본문이 공개 저장소로 나간다」 하나라 스캔 함수만 잠근다.
- 모양(N1~N6·T) — 규칙마다 통과 1 · 위반 ≥1. `use_git=False` 로 해시 실재는 형식만 본다.
- 통합 — 임시 git 저장소에 화면·계약·코드 사전을 두 커밋으로 만들고 build-notice.py 를 돌려
  «지점만 나오고 값은 안 나온다»를 잠근 뒤, 그 결과가 check-notice.py 를 통과하는지 본다.
"""
from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "check-notice.py")
BUILD = os.path.join(HERE, "build-notice.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


chk = _load("chk", CHECK)

FULL = "a" * 40
GOOD = (
    "# 설계 변동 공지\n\n"
    "1. **공지 발행 날짜**: 2026-09-03\n"
    "2. **배포 버전**: `%s` (`%s`)\n"
    "3. **설계 자료 목록** — 저장소 `CREFLEINC/omf-mes`, 버전은 그 갈래를 마지막으로 바꾼 커밋\n\n"
    "| 자료 | 경로 | 버전 |\n| --- | --- | --- |\n"
    "| 화면설계서 | `design/wiki/screens/` | `b96f470` |\n\n"
    "4. **이전 버전(`de4203a`)과 달라진 지점**\n\n"
    "- 화면설계서 `W-04-03` — §3 · §5-1\n"
    "- API 계약서 03품질 — `POST /quality/lot-holds/{lotHoldId}:release` · 스키마 `LotHold`(신설)\n"
) % (FULL, FULL[:7])
TITLE = "[설계 변동 공지] 2026-09-03 · " + FULL[:7]


def codes(text: str, title=None):
    errs, warns = chk.check(text, title, use_git=False)
    return [c for c, _, _ in errs], [c for c, _, _ in warns]


def blocked(text: str):
    return [name for name, _, _ in chk.scan(text, chk.BLOCKING)]


def advised(text: str):
    return [name for name, _, _ in chk.scan(text, chk.ADVISORY)]


def run_main(text: str, *flags: str):
    """main() 을 임시 파일로 돌려 (종료 코드, 출력)."""
    fd, path = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    try:
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(text)
        out, saved = io.StringIO(), sys.stdout
        sys.stdout = out
        try:
            rc = chk.main([path, "--no-git", *flags])
        finally:
            sys.stdout = saved
        return rc, out.getvalue()
    finally:
        os.unlink(path)


# ─────────────────────────────────────────── P — 공개 안전(옛 check-issue.py 이식)

class PublicSafety(unittest.TestCase):
    """omf-mes-client 는 공개 저장소다 — 옛 PublicSafetySplit 의 RISKY 본문을 그대로 쓴다."""

    RISKY = "조달 단가는 629,000원 이고 서버는 10.0.1.24 입니다.\n"

    def test_금액과_인프라는_막는다(self):
        names = blocked(self.RISKY)
        self.assertIn("금액·단가·납기", names)
        self.assertIn("인프라 정보", names)

    def test_같은_본문이_check_에서_P_로_막힌다(self):
        errs, _ = codes(GOOD + "\n" + self.RISKY)
        self.assertIn("P", errs)

    def test_이미지는_막는다(self):
        self.assertIn("이미지", blocked("![화면](https://github.com/user-attachments/assets/x.png)"))

    def test_공유계약_조항_요약은_막고_번호만은_허용(self):
        self.assertIn("공유계약 조항 요약", blocked("공유계약 B-1 (LOT 은 분할 불가) 을 따른다"))
        self.assertEqual(blocked("공유계약 B-1 을 따른다"), [])

    def test_실_사번_실_LOT_의심은_막는다(self):
        self.assertIn("실 사번 의심", blocked("작업자 901234 가 처리"))
        self.assertIn("실 LOT 번호 의심", blocked("LOT AB-20260101-001 확인"))

    def test_긴_블록_인용은_막는다(self):
        self.assertIn("스펙 본문 인용 의심",
                      blocked("> 이 화면은 자재 입고 후 검사 대기 상태의 LOT 을 목록으로 보여 주고 선택한 LOT 을 검사 요청으로 넘긴다\n"))

    def test_해시는_사번_LOT_규칙에_안_걸린다(self):
        """40 hex · 7 hex 는 \\b 경계가 안 생겨 의심 규칙이 안 걸린다 — 공지마다 해시가 둘 있다."""
        self.assertEqual(blocked("`912345abcdef0123456789abcdef0123456789ab` (`912345a`)"), [])


class DraftResidue(unittest.TestCase):
    """초안 잔재 — 옛 DraftResidue 이식. omf-mes-client#602·#603 실측 사고."""

    def test_내부_에이전트_이름은_막는다(self):
        self.assertIn("내부 에이전트·스킬 이름", blocked("발행 전 design-review-analyst 재확인을 권장한다."))

    def test_V3_스킬_이름도_막는다(self):
        self.assertIn("내부 에이전트·스킬 이름", blocked("design-change-notice 가 만든 초안"))
        self.assertIn("내부 에이전트·스킬 이름", blocked("design-request-intake 로 넘긴다"))

    def test_발행_전_지시_잔재는_막는다(self):
        self.assertIn("발행 전 지시 잔재", blocked("확정 범위만 먼저 내고, 발행 전에 다시 검토합니다."))

    def test_미기입_물음표_칸은_막는다(self):
        errs, _ = codes(GOOD + "- 화면설계서 `W-06-05` — (?, #14)\n")
        self.assertIn("N6", errs)

    def test_한계를_알리는_문장은_막지_않는다(self):
        """⚠ 오탐 잠금 — 경고로만 뜨고 발행을 막지 않는다."""
        text = "필드 단위 실사용까지는 확인하지 못했습니다 — 어긋나면 알려 주십시오.\n"
        self.assertEqual(blocked(text), [])
        self.assertIn("자기 미확인 자인", advised(text))

    def test_요구사항_번호는_경고만(self):
        self.assertIn("요구사항 번호", advised("REQ-PR-0001"))
        self.assertEqual(blocked("REQ-PR-0001"), [])


# ─────────────────────────────────────────── N1~N6 · T

class N1Heads(unittest.TestCase):
    def test_통과(self):
        errs, warns = codes(GOOD)
        self.assertEqual(errs, [])
        self.assertEqual(warns, [])

    def test_4항_머리_없으면_막는다(self):
        errs, _ = codes(GOOD.replace("4. **이전 버전(`de4203a`)과 달라진 지점**", "4. 달라진 지점"))
        self.assertIn("N1", errs)

    def test_머리가_두_번이면_막는다(self):
        errs, _ = codes(GOOD + "\n1. **공지 발행 날짜**: 2026-09-04\n")
        self.assertIn("N1", errs)

    def test_날짜_형식이_다르면_막는다(self):
        errs, _ = codes(GOOD.replace("2026-09-03", "2026.09.03"))
        self.assertIn("N1", errs)


class N2Hashes(unittest.TestCase):
    def test_통과(self):
        self.assertNotIn("N2", codes(GOOD)[0])

    def test_전체_해시가_40자가_아니면_막는다(self):
        errs, _ = codes(GOOD.replace("`%s`" % FULL, "`%s`" % FULL[:12]))
        self.assertIn("N2", errs)

    def test_괄호_해시7_이_앞_7자와_다르면_막는다(self):
        errs, _ = codes(GOOD.replace("(`%s`)" % FULL[:7], "(`bbbbbbb`)"))
        self.assertIn("N2", errs)

    def test_이전_버전이_해시7_이_아니면_막는다(self):
        errs, _ = codes(GOOD.replace("(`de4203a`)", "(`de42`)"))
        self.assertIn("N2", errs)


class N3TeamWords(unittest.TestCase):
    def test_통과(self):
        self.assertNotIn("N3", codes(GOOD)[0])

    def test_팀_구분어는_막는다(self):
        for w in ("백엔드", "클라이언트", "프론트", "서버팀"):
            errs, _ = codes(GOOD + "- 공유계약 — %s 몫 A-4\n" % w)
            self.assertIn("N3", errs, w)

    def test_백틱_안은_안_본다(self):
        """경로·파일명에 들어간 낱말은 지점이지 팀 구분이 아니다."""
        errs, _ = codes(GOOD + "- 사양서·요구사항 `클라이언트-구성` — §1\n")
        self.assertNotIn("N3", errs)


class N4Leak(unittest.TestCase):
    def test_통과(self):
        self.assertNotIn("N4", codes(GOOD)[0])

    def test_코드_펜스는_막는다(self):
        errs, _ = codes(GOOD + "\n```json\n{}\n```\n")
        self.assertIn("N4", errs)

    def test_화살표는_막는다(self):
        for a in ("→", "->", "=>"):
            errs, _ = codes(GOOD + "- 코드 사전 — `CD-X` %s 값 추가\n" % a)
            self.assertIn("N4", errs, a)

    def test_행머리_인용은_막는다(self):
        errs, _ = codes(GOOD + "> 짧은 인용\n")
        self.assertIn("N4", errs)

    def test_4항_항목의_백틱_밖_콜론은_막는다(self):
        errs, _ = codes(GOOD + "- 코드 사전 — `CD-X`: 값이 셋으로 늘었다\n")
        self.assertIn("N4", errs)

    def test_백틱_안_콜론은_경로다(self):
        errs, _ = codes(GOOD + "- API 계약서 공통 — `POST /app/approval-routes/{id}:deactivate`\n")
        self.assertNotIn("N4", errs)


class N5Long(unittest.TestCase):
    def test_통과(self):
        self.assertEqual(codes(GOOD)[1], [])

    def test_160자_넘는_항목은_경고만(self):
        long_item = "- 화면설계서 `W-01-01` — " + " · ".join("§%d" % i for i in range(1, 60)) + "\n"
        self.assertGreater(len(long_item), 160)
        errs, warns = codes(GOOD + long_item)
        self.assertIn("N5", warns)
        self.assertNotIn("N5", errs)


class N6Placeholder(unittest.TestCase):
    def test_통과(self):
        self.assertNotIn("N6", codes(GOOD)[0])

    def test_자리표시는_막는다(self):
        for ph in ("<해시>", "YYYY-MM-DD", "W-00-00", "omf-mes#00", "<날짜>", "v0.0"):
            errs, _ = codes(GOOD + "- 공유계약 — %s\n" % ph)
            self.assertIn("N6", errs, ph)


class TTitle(unittest.TestCase):
    def test_통과(self):
        errs, _ = codes(GOOD, TITLE)
        self.assertEqual(errs, [])

    def test_제목_없이도_본문은_검사한다(self):
        self.assertNotIn("T", codes(GOOD, None)[0])

    def test_형식이_다르면_막는다(self):
        for t in ("[설계 변동 공지] 2026-09-03", "설계 변동 공지 2026-09-03 · aaaaaaa",
                  "[설계 변동 공지] 2026-09-03 · AAAAAAA", "[설계 변동 공지] 2026-09-03 · aaaaaaa 추가"):
            errs, _ = codes(GOOD, t)
            self.assertIn("T", errs, t)

    def test_날짜가_1항과_다르면_막는다(self):
        errs, _ = codes(GOOD, "[설계 변동 공지] 2026-09-04 · " + FULL[:7])
        self.assertIn("T", errs)

    def test_해시가_2항과_다르면_막는다(self):
        errs, _ = codes(GOOD, "[설계 변동 공지] 2026-09-03 · bbbbbbb")
        self.assertIn("T", errs)


class MainOutput(unittest.TestCase):
    def test_통과하면_gh_명령_두_줄을_출력만_한다(self):
        rc, out = run_main(GOOD, "--title", TITLE)
        self.assertEqual(rc, 0)
        self.assertIn("✅ 통과", out)
        self.assertEqual(out.count("gh issue create"), 2)
        self.assertIn("--repo CREFLEINC/omf-mes-client", out)
        self.assertIn("--repo CREFLEINC/omf-mes-server", out)
        self.assertIn('--label "설계 변동 공지"', out)
        self.assertIn('--label "uiux→client"', out)

    def test_위반은_규칙코드와_행번호를_낸다(self):
        rc, out = run_main(GOOD + "- 코드 사전 — `CD-X` → 값 추가\n")
        self.assertEqual(rc, 1)
        self.assertIn("⛔ N4 ", out)
        self.assertNotIn("gh issue create", out)

    def test_경고만이면_통과하되_알린다(self):
        rc, out = run_main(GOOD + "- 사양서·요구사항 `01` — REQ-PR-0001\n")
        self.assertEqual(rc, 0)
        self.assertIn("⚠ P ", out)


# ─────────────────────────────────────────── 통합 — build-notice.py

SCREEN_V1 = "# W-01-01 테스트\n\n## §1. 개요\n\n첫 문단\n\n## §3 목록\n\n- 항목 a\n\n## §5. 기타\n\n끝\n"
SCREEN_V2 = SCREEN_V1.replace("- 항목 a\n", "- 항목 a\n- 항목 b VALUE_B_SECRET\n")
CONTRACT_V1 = ('{"openapi":"3.0.3","info":{"title":"t","version":"1"},'
               '"paths":{"/quality/lot-holds":{"get":{"summary":"목록"}}},'
               '"components":{"schemas":{"LotHold":{"type":"object","properties":{"id":{"type":"string"}}}}}}')
CONTRACT_V2 = ('{"openapi":"3.0.3","info":{"title":"t","version":"1"},'
               '"paths":{"/quality/lot-holds":{"get":{"summary":"목록 SUMMARY_SECRET"}}},'
               '"components":{"schemas":{"LotHold":{"type":"object","properties":{"id":{"type":"string"},'
               '"reasonSecretField":{"type":"string"}}},'
               '"LotHoldCreate":{"type":"object","properties":{"reasonSecretField":{"type":"string"}}}}}}')
DICT_V1 = "# 코드 사전\n\n## CD-X 판정\n\n| 값 | 뜻 |\n| --- | --- |\n| A | 합격 |\n"
DICT_V2 = DICT_V1 + "| B | 불합격 DICT_VALUE_SECRET |\n"
SECRETS = ("VALUE_B_SECRET", "SUMMARY_SECRET", "reasonSecretField", "DICT_VALUE_SECRET", "합격", "항목 a")


def _git(root, *args):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          cwd=root, capture_output=True, text=True, check=True).stdout.strip()


def _write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as f:
        f.write(text)


class BuildNotice(unittest.TestCase):
    """임시 저장소 두 커밋 — «지점만 나오고 값은 안 나온다»."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="notice-test-")
        r = cls.tmp
        _git(r, "init", "-q")
        _write(r, "design/wiki/screens/W-01-01-테스트화면.md", SCREEN_V1)
        _write(r, "design/wiki/api-contracts/openapi/quality-03품질.json", CONTRACT_V1)
        _write(r, "design/schema/code-dictionary.md", DICT_V1)
        _write(r, "design/wiki/screens/W-01-01-테스트화면.html", "<p>배포본</p>")
        _git(r, "add", "-A")
        _git(r, "commit", "-q", "-m", "첫 커밋")
        cls.first = _git(r, "rev-parse", "HEAD")
        _write(r, "design/wiki/screens/W-01-01-테스트화면.md", SCREEN_V2)
        _write(r, "design/wiki/api-contracts/openapi/quality-03품질.json", CONTRACT_V2)
        _write(r, "design/schema/code-dictionary.md", DICT_V2)
        _write(r, "design/wiki/screens/W-01-01-테스트화면.html", "<p>배포본 2</p>")
        _git(r, "add", "-A")
        _git(r, "commit", "-q", "-m", "둘째 커밋")
        cls.second = _git(r, "rev-parse", "HEAD")

    def _build(self, *extra):
        out = os.path.join(self.tmp, "out-%d.md" % len(os.listdir(self.tmp)))
        p = subprocess.run([sys.executable, BUILD, "--repo-root", self.tmp, "--out", out,
                            "--date", "2026-09-03", *extra],
                           capture_output=True, text=True)
        return p, out

    def test_지점만_나오고_값은_안_나온다(self):
        p, out = self._build("--since", self.first)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("지점", p.stdout)
        with io.open(out, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("1. **공지 발행 날짜**: 2026-09-03", text)
        self.assertIn("2. **배포 버전**: `%s` (`%s`)" % (self.second, self.second[:7]), text)
        self.assertIn("4. **이전 버전(`%s`)과 달라진 지점**" % self.first[:7], text)
        self.assertIn("- 화면설계서 `W-01-01` — §3", text)
        self.assertIn("API 계약서 03품질 — ", text)
        self.assertIn("`GET /quality/lot-holds`", text)
        self.assertIn("스키마 `LotHold`", text)
        self.assertIn("스키마 `LotHoldCreate`(신설)", text)
        self.assertIn("- 코드 사전 — `CD-X`", text)
        self.assertIn("| 화면설계서 | `design/wiki/screens/` | `%s` |" % self.second[:7], text)
        self.assertIn("| 공유계약 | `design/wiki/decisions-policy/공유계약.md` | — |", text)
        for s in SECRETS:
            self.assertNotIn(s, text, s)
        self.assertNotIn("§1", text)   # 안 바뀐 절은 안 나온다
        self.assertNotIn("§5", text)
        self.assertNotIn(".html", text)

    def test_생성물이_검사기를_통과한다(self):
        p, out = self._build("--since", self.first)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        title = "[설계 변동 공지] 2026-09-03 · " + self.second[:7]
        for flags in (["--no-git"], []):        # 형식만 · 임시 저장소에서 해시 실재까지
            q = subprocess.run([sys.executable, CHECK, out, "--title", title,
                                "--repo-root", self.tmp, *flags],
                               capture_output=True, text=True)
            self.assertEqual(q.returncode, 0, q.stdout + q.stderr)
            self.assertIn("✅ 통과", q.stdout)
            self.assertEqual(q.stdout.count("gh issue create"), 2)

    def test_없는_해시는_git_검사에서_막힌다(self):
        p, out = self._build("--since", self.first)
        with io.open(out, encoding="utf-8") as f:
            text = f.read()
        with io.open(out, "w", encoding="utf-8") as f:
            f.write(text.replace("(`%s`)과" % self.first[:7], "(`0000000`)과"))
        q = subprocess.run([sys.executable, CHECK, out, "--repo-root", self.tmp],
                           capture_output=True, text=True)
        self.assertEqual(q.returncode, 1)
        self.assertIn("⛔ N2 ", q.stdout)

    def test_변경이_없으면_1을_낸다(self):
        p, _ = self._build("--since", self.second)
        self.assertEqual(p.returncode, 1)
        self.assertIn("공지할 것이 없다", p.stdout)

    def test_태그도_since_도_없으면_2를_낸다(self):
        p, _ = self._build()
        self.assertEqual(p.returncode, 2)
        self.assertIn("--since", p.stdout + p.stderr)

    def test_notice_태그가_있으면_기본_기준이_된다(self):
        _git(self.tmp, "tag", "notice/20260901", self.first)
        try:
            p, out = self._build()
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn("%s..%s" % (self.first[:7], self.second[:7]), p.stdout)
        finally:
            _git(self.tmp, "tag", "-d", "notice/20260901")


if __name__ == "__main__":
    unittest.main(verbosity=2)
