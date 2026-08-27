#!/usr/bin/env python3
"""check-issue.py 단위 테스트 — `--reply` 모드 중심.

⚠ 이 검사기는 **되돌릴 수 없는 행위의 마지막 방어선**이다. 공개 저장소에 한 번 나가면
인덱싱된 사본과 포크는 회수되지 않는다. 그래서 「무엇을 잡느냐」만큼 **「무엇을 안 잡느냐」**를
잠근다 — 형제 스크립트(`uiux-design/scripts/test-check-report-language.py`)가 세운 원칙이다.

여기서 특히 잠그는 것 — **규약을 «지킨» 회신을 오탐으로 막지 않는가.**

실제로 첫 판이 그랬다. 머리 표기를 완전 일치로 잡아
`## 개발팀 전달사항 — <한 줄 결론>`(당시 정본의 골격이고, 그 정본을 지킨 유일한
실측 회신 `omf-mes#206` 이 그 형태다)을 위반으로 판정했다. 오탐이 나면 사람은 규약이
아니라 **검사기를 끈다.** 그러면 없느니만 못하다.

⚠ **2026-08-27 정본이 바뀌었다** — 사용자가 v2 문서 원문("개발팀에 전달사항", 조사 있음)
그대로 재확정했고, `##`는 강제하지 않기로 했다. 이 파일의 테스트는 새 정본 기준이다 —
`## 개발팀 전달사항`(조사 없음)은 이제 **위반**으로 검사한다(아래 `test_이전_정본은_이제_차단`).
"""
from __future__ import annotations

import importlib.util
import io
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "chk", os.path.join(HERE, "check-issue.py")
)
chk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chk)


def run(body: str, *flags: str) -> int:
    """본문을 임시 파일에 쓰고 main() 을 돌려 종료 코드를 돌려준다.

    0 = 통과 · 1 = ⛔ 위반 · 2 = 사용법 오류.
    """
    fd, path = tempfile.mkstemp(suffix=".md")
    os.close(fd)
    try:
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(body)
        argv = chk.sys.argv
        chk.sys.argv = ["check-issue.py", path] + list(flags)
        try:
            out = io.StringIO()
            stdout = chk.sys.stdout
            chk.sys.stdout = out
            try:
                return chk.main() or 0
            finally:
                chk.sys.stdout = stdout
        finally:
            chk.sys.argv = argv
    finally:
        os.unlink(path)


BODY = "\n\n3개 물음에 답합니다. 반영 PR #244 — 병합 `7dbb0d8`.\n"


class ReplyHead(unittest.TestCase):
    """머리 표기 — 접두 일치이지 완전 일치가 아니다. 정본은 2026-08-27 기준."""

    def test_민머리_통과(self):
        """「##」 없이도 통과한다 — 2026-08-27 결정으로 강제하지 않는다."""
        self.assertEqual(run("개발팀에 전달사항" + BODY, "--reply", "--private"), 0)

    def test_샵있는_민머리도_통과(self):
        self.assertEqual(run("## 개발팀에 전달사항" + BODY, "--reply", "--private"), 0)

    def test_한줄결론_붙은_형태_통과(self):
        """대시로 한 줄 결론을 붙이는 것도 여전히 접두 일치로 통과한다."""
        head = "## 개발팀에 전달사항 — 지적이 맞습니다. 스펙을 갱신합니다"
        self.assertEqual(run(head + BODY, "--reply", "--private"), 0)

    def test_한줄결론_민머리로도_통과(self):
        """「##」 없이 한 줄 결론만 붙인 형태도 통과한다."""
        head = "개발팀에 전달사항 — 입력값은 «LOT 크기»가 맞습니다 · 계약을 `lotSize` 필수로 교체했습니다"
        self.assertEqual(run(head + BODY, "--reply", "--private"), 0)

    def test_이전_정본은_이제_차단(self):
        """omf-mes#206 이 지켰던 구 정본(조사 없음) — 2026-08-27 재확정 이후로는 위반이다."""
        self.assertEqual(run("## 개발팀 전달사항" + BODY, "--reply", "--private"), 1)

    def test_조사_빠짐_차단(self):
        """omf-mes#232 계열 — "에"가 빠진 형태."""
        self.assertEqual(run("개발팀 전달사항" + BODY, "--reply", "--private"), 1)

    def test_구표기_공백_차단(self):
        """omf-mes#222 실측 위반 — "전달"과 "사항" 사이에 공백이 낀 변형."""
        self.assertEqual(run("## 개발팀에 전달 사항" + BODY, "--reply", "--private"), 1)

    def test_접두만_같고_이어붙은_변형_차단(self):
        """접두 일치로 바꾸면서 헐거워지지 않았는지 — 공백으로 끊겨야 한다."""
        self.assertEqual(run("개발팀에 전달사항입니다" + BODY, "--reply", "--private"), 1)

    def test_빈_본문_차단되고_터지지_않는다(self):
        self.assertEqual(run("", "--reply", "--private"), 1)
        self.assertEqual(run("   \n\n  \n", "--reply", "--private"), 1)


class PublicSafetySplit(unittest.TestCase):
    """공개 안전 스캔(②)과 회신 규약(③)은 갈려 있다."""

    RISKY = ("개발팀에 전달사항 — 비공개 회신\n\n"
             "조달 단가는 629,000원 이고 서버는 10.0.1.24 입니다.\n")

    def test_비공개면_공개안전_스캔을_끈다(self):
        """비공개 omf-mes 회신에서 단가·내부 주소는 막을 이유가 없다."""
        self.assertEqual(run(self.RISKY, "--reply", "--private"), 0)

    def test_공개면_같은_본문을_막는다(self):
        self.assertEqual(run(self.RISKY, "--reply"), 1)

    def test_비공개여도_머리표기는_본다(self):
        """#232·#222 가 둘 다 «비공개» 회신이었다 — 여기서 놓치면 도입 이유가 사라진다."""
        self.assertEqual(run("개발팀 전달사항" + BODY, "--reply", "--private"), 1)

    def test_기본은_공개안전_켜짐(self):
        """--private 를 «잊었을 때» 과하게 막힐 뿐 흘러나가지 않는다."""
        self.assertEqual(run(self.RISKY, "--reply"), 1)

    def test_private_는_reply_없이_못_쓴다(self):
        """착수·변경 통지는 언제나 공개 저장소로 나간다 — 끌 수 있는 자리가 아니다."""
        self.assertEqual(run(self.RISKY, "--private"), 2)


class ReplySkipsFormChecks(unittest.TestCase):
    """--reply 는 폼 6항목 구조와 중복 발행을 보지 않는다."""

    def test_폼_없는_회신이_통과한다(self):
        """회신에는 「4. 미결 항목」 같은 절이 없다 — 그것이 정상이다."""
        self.assertEqual(run("개발팀에 전달사항" + BODY, "--reply", "--private"), 0)

    def test_화면ID가_있어도_중복발행으로_막지_않는다(self):
        """답하는 대상이 바로 그 화면의 이슈다. 원격 조회도 하지 않는다."""
        body = ("개발팀에 전달사항 — M-CO-01 회신\n\n"
                "모바일 기기 등록·사번 인증 화면(M-CO-01) 관련입니다.\n")
        self.assertEqual(run(body, "--reply", "--private"), 0)

    def test_자리표시자는_회신에서도_막는다(self):
        """PR 번호·sha 를 안 채우고 게시하는 사고를 막는 자리."""
        body = "개발팀에 전달사항\n\n반영 PR #<번호> — 병합 <해시>.\n"
        self.assertEqual(run(body, "--reply", "--private"), 1)


class NoRegression(unittest.TestCase):
    """기존 모드가 --reply 도입으로 바뀌지 않았다."""

    FORM_LESS = "## 무언가\n\n폼 6항목이 없는 본문.\n"

    def test_기본모드는_구조를_계속_본다(self):
        self.assertEqual(run(self.FORM_LESS, "--no-remote"), 1)

    def test_변경통지모드는_구조를_건너뛴다(self):
        """--change-notice 의 기존 동작 — 구조 검사 없음."""
        self.assertEqual(run(self.FORM_LESS, "--change-notice", "--no-remote"), 0)

    def test_두_모드를_함께_주면_reply_가_이기되_경고한다(self):
        """조용히 다른 검사가 도는 것을 막는다."""
        rc = run("개발팀에 전달사항" + BODY,
                 "--reply", "--private", "--change-notice")
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
