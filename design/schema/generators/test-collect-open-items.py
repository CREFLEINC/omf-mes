#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# collect-open-items.py 의 «해소 판정» 단위 테스트. 표준 라이브러리만 쓴다.
#
# 왜 이 표본인가 — 2026-09-02(#349) 실측 때문이다. 판정이 행의 모든 칸을 이어
# `✅|해소|종결|~~` 를 찾기만 해서 **살아 있는 미결 5행을 해소로 셌다.** 미결 대장은
# 이슈를 닫기 전 4중 잠금 ④(「걸린 미결이 0건인가」)가 읽는 자리라, 이 판정이 틀리면
# **닫으면 안 되는 이슈가 닫힌다.**
#
# 원인은 둘이고 표본도 둘로 나뉜다:
#   ① 부정 접두 — 한국어는 「미-」가 붙어도 원형을 품는다. 「미해소」가 「해소」로 걸렸다
#   ② 남의 해소 인용 — 처리 열이 「…종결…」을 인용하기만 해도 그 행이 통째로 넘어갔다
#
# ⛔ 반대 방향도 함께 잠근다. 「아직」을 부정 목록에 넣자는 안이 있었으나 실측 반례가
#    있다 — `W-05-08` 미결 2 는 진짜 종결인데 «남의 화면» 미결을 「아직 살아 있어」로
#    언급한다. 넣으면 그 행이 거꾸로 열림이 된다. 그 표본을 아래에 박아 둔다.
#
# 문면은 2026-09-02 시점의 화면 스펙 §8 원문에서 땄다. 스펙이 나중에 바뀌어도 이
# 테스트가 잠그는 것은 «규칙»이므로 그대로 둔다.
import importlib
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
coi = importlib.import_module("collect-open-items")


# ── ① 부정 접두 — 해소 표시가 있어도 열림이다 ────────────────────────────────
미해소 = (
    "2 점검 항목 표시 순서 — [추정]으로 남긴 것 수집 대기 "
    "⚠ 여전히 미해소. 화면은 순서대로 그리되, 현행 일상점검표 실물을 봐야 확정된다"
)  # M-05-01 미결 2

부분해소 = (
    "2 외주공정 구분 · L/T · UPH 상류↔하류 불일치 — 부분 해소 "
    "외주 구분: ✅ 완전 해소(2026-08-30) — isOutsourced 계약 반영. "
    "L/T·UPH: 미해소 유지 — 목표관리 화면이 인벤토리에 없다"
)  # W-06-01 미결 2 — 한 행에 소관이 둘. 절반이 열려 있으면 열림이다

# ── ② 남의 해소 «인용» — 「」 안은 이 행의 판정이 아니다 ──────────────────────
인용_착수전해소 = (
    "1 물리 모델의 선언 범위에 설비보전이 없다 "
    "⭐ 2026-08-18 갱신 — 「착수 전 해소」 조건은 DR-001 1-A 가 동결을 풀어 무효가 됐고, "
    "모델 결손 자체는 그대로 남아 있다"
)  # W-06-08 미결 1 — 05 도메인 17화면 파급. 사라지면 아무도 못 찾는다

인용_미결해소 = (
    "2 audit.audit_event 가 화면을 그리기에 부족하다 "
    "ⓐ 매핑표 ⓑ jsonb 키 규약이 필요한데 둘 다 하류에 없다. "
    "W-CO-02 §8-1 이 「B-4 변경 이력 미결 해소」로 닫은 것은 테이블의 존재까지다"
)  # W-06-11 미결 2

인용_종결 = (
    "7 BOM Rev 축의 진행 W/O 전환 규칙 회신/설계 "
    "WF06 S8 「Routing 축은 스냅샷으로 종결 — BOM 축 잔여」. "
    "이 화면이 보여 줄 「참조 중 W/O」의 의미가 BOM에서는 아직 정의되지 않았다"
)  # W-06-11 미결 7

# ── 반례 — 이것들은 해소다. 뒤집으면 대장이 거꾸로 망가진다 ──────────────────
진짜_종결_아직있음 = (
    "2 OEE 세 항의 재료가 전부 실재한다 설계 결정 "
    "⭐ W-CO-05 가 받아 §3-4·§9-1 로 판정했다. "
    "⚠ 다만 그 화면 §8 미결 1·3 이 아직 살아 있어 이월은 판정 완료·조건부 재검토로 종결한다"
)  # W-05-08 미결 2 — 「아직」을 부정 목록에 넣으면 이 행이 깨진다

진짜_해소_평문 = "1 점검 기록 테이블이 없다 설계 결정 ✅ 정의했다(§4·§5-1)"
진짜_해소_취소선 = "5 ~~BOM 구성품의 MES 확장 열~~ 설계 ✅ 해소"
진짜_해소_낱말만 = "1 외주공정 구분 상류↔하류 불일치 해소 — 📨 데이터 모델 통지(저장 컬럼)"


class 해소판정(unittest.TestCase):
    def test_부정접두는_열림이다(self):
        for 문면 in (미해소, 부분해소):
            with self.subTest(문면=문면[:20]):
                self.assertFalse(coi.resolved(문면))

    def test_인용_안의_해소는_이_행의_판정이_아니다(self):
        for 문면 in (인용_착수전해소, 인용_미결해소, 인용_종결):
            with self.subTest(문면=문면[:20]):
                self.assertFalse(coi.resolved(문면))

    def test_진짜_해소는_그대로_해소다(self):
        for 문면 in (진짜_해소_평문, 진짜_해소_취소선, 진짜_해소_낱말만):
            with self.subTest(문면=문면[:20]):
                self.assertTrue(coi.resolved(문면))

    def test_아직은_부정어가_아니다(self):
        """⛔ 반례 — 「아직」으로 뒤집으면 진짜 종결이 열림이 된다."""
        self.assertTrue(coi.resolved(진짜_종결_아직있음))

    def test_해소_표시가_아예_없으면_열림이다(self):
        self.assertFalse(coi.resolved("3 값 목록 미정 공통코드 W-06-06 · #145"))


class 좁힘은_살아있다(unittest.TestCase):
    """⛔ 2026-09-02 실측 — 좁힘 16행 중 3행이 대장에서 «통째로» 사라져 있었다.

    부분 해소 표기의 문면은 거의 언제나 「X 는 해소됐다. 남은 것은 Y」 꼴이라
    DONE 의 「해소」에 걸린다. 그런데 그 행은 «남은 물음»만 담고 있어 사라지면
    대장의 존재 이유(「확정이 오면 어느 화면이 걸리나」)가 그 자리에서 깨진다.
    """

    def test_좁힘이_적히면_해소가_같이_있어도_열림이다(self):
        문면 = ("1 reissue_reason_code 값 목록 미확정 공통코드 조정 "
                "⭐ 2026-09-02 좁힘 — 제목을 갈았다. document_type_code 는 해소됐다")
        self.assertFalse(coi.resolved(문면))

    def test_좁힘이_없으면_해소는_그대로_해소다(self):
        문면 = "1 document_type_code 값 목록 공통코드 ✅ 종결 — 계약이 enum 9종으로 닫았다"
        self.assertTrue(coi.resolved(문면))

    def test_인용_안의_좁힘은_남의_말이라_안_본다(self):
        # 「」 안은 남의 판정이다 — QUOTED 가 먼저 걷으므로 좁힘으로 살아나지 않는다.
        문면 = "2 이 건은 종결됐다 — 「W-01-01 은 2026-09-02 좁힘」 과 다른 자리다"
        self.assertTrue(coi.resolved(문면))


class 살아있다고_적은_행(unittest.TestCase):
    """⛔ 표지를 갈아 끼울 때 «옛 표지의 결말»을 적으면 그 행 자신이 닫혔다.

    2026-09-04 · `omf-mes#378` 3회차에서 실제로 일곱 행이 대장에서 사라졌다 —
    `W-03-10` 3 · `W-06-06` 9 · `W-04-10` 4 · `W-01-04` 2 · `W-06-14` 6 ·
    `W-06-15` 6 · `W-CO-09` 1. 그중 둘은 계약·등록부가 그 미결 번호를 인용하며
    자리를 비워 둔 곳이라 사라지면 계약 주석이 죽는다.
    """

    def test_표지_교체는_열림이다(self):
        문면 = "3 ⭐ 표지 교체 — 옛 표지 #64 는 2026-08-25 에 회신 없이 종결됐다"
        self.assertFalse(coi.resolved(문면))

    def test_닫지_않는다는_열림이다(self):
        문면 = "9 ⛔ 그래도 이 행은 닫지 않는다 — 등록부가 이 미결을 이름으로 인용한다"
        self.assertFalse(coi.resolved(문면))

    def test_열어_둔다는_열림이다(self):
        문면 = "4 ⚠ 답이 없다 — 열어 둔다. #44 는 종결됐고 그 결말이 이것을 닫지 않는다"
        self.assertFalse(coi.resolved(문면))

    def test_표기가_없으면_옛_표지의_종결이_이_행을_닫는다(self):
        """⛔ 반례 — 이것이 규약을 «필요»하게 만든 자리다.

        같은 뜻인데 표기가 빠지면 닫힌다. 그래서 머리말이 「함께 적는다」로 못박는다.
        """
        문면 = "3 옛 표지 #64 는 2026-08-25 에 회신 없이 종결됐다"
        self.assertTrue(coi.resolved(문면))

    def test_답이_없다도_열림이다(self):
        """판정 3 의 어휘 그대로다 — 판정을 적으면 표기가 저절로 붙는다."""
        문면 = ("4 ⚠ 2026-09-04 — 답이 없다. 표지가 죽었고 갈아 끼울 곳도 없다. "
              "#44 는 2026-07-29 에 코멘트 0건으로 종결됐다")
        self.assertFalse(coi.resolved(문면))

    def test_진짜_해소는_여전히_해소다(self):
        self.assertTrue(coi.resolved("2 ✅ 해소 2026-09-04 — 계약에 자리가 섰다"))


class 표를_읽어서도_같은가(unittest.TestCase):
    """단위 판정이 맞아도 표를 거쳐 오면 달라질 수 있다 — 끝까지 한 번 태운다."""

    스펙 = """# W-99-01 시험용 화면

## §8. 미결

| # | 항목 | 성격 | 처리 |
| :-: | --- | --- | --- |
| **1** | **첫째** | **설계 결정** | ✅ **정의했다**(§4) |
| **2** | **둘째** | **수집 대기** | ⚠ **여전히 미해소.** 실물을 봐야 확정된다 |
| **3** | **셋째** | 회신/설계 | WF06 S8 「Routing 축은 스냅샷으로 종결」. BOM 축은 정의되지 않았다 |
"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_열림_둘_해소_하나(self):
        경로 = os.path.join(self.tmp, "W-99-01-시험용화면.md")
        with open(경로, "w", encoding="utf-8") as f:
            f.write(self.스펙)
        결과 = coi.parse(경로)
        self.assertEqual([r["done"] for r in 결과["rows"]], [True, False, False])


# ── omf-mes#357 — 미결 절 안의 «다른 표»를 미결 행으로 삼켰다 ────────────────
#
# 파서가 표 경계를 «열 수»로만 판정해서(`len(cs) < len(header)-1`), 같은 절 안에
# 4열 표가 또 나오면 그 행까지 미결로 셌다. 실물 — `W-05-03` §8-2 공유계약 후보
# 표 둘이 §8-1 뒤에 붙어 있어 규칙 표 7행이 통째로 미결이 됐다:
#     「타발수 입력(P-05-01) · 증분 +1,250」 · 「자기참조 체인」 · 「이력 · 체인이 곧 이력」
# 그중 3행은 ✅ 가 붙어 «해소»로까지 세어졌다.
#
# ⛔ 「번호가 숫자인 행만 센다」는 답이 아니다 — 정당한 비숫자 번호가 실재한다.
#    아래 «비숫자 번호» 표본이 그 반증을 박아 둔 자리다.
class 표_경계(unittest.TestCase):
    """미결 표는 «머리»에서 시작해 «표가 끝나는 자리»에서 끝난다."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def parse(self, 본문: str, 이름: str = "W-99-02-시험용화면.md") -> dict:
        경로 = os.path.join(self.tmp, 이름)
        with open(경로, "w", encoding="utf-8") as f:
            f.write(본문)
        return coi.parse(경로)

    # ⓐ 미결 절에 표가 둘 — 둘째 표를 안 센다 (`W-05-03` §8-1 + §8-2 의 축소판)
    표가_둘 = """# W-99-02 시험용 화면

## §8. 미결 · 계약 후보

### §8-1. 미결

| # | 항목 | 성격 | 처리 |
| :-: | --- | --- | --- |
| **1** | **PM 실적 테이블 없음** | **설계 결정** | ✅ **정의했다**(§5-A) |
| **2** | **보전부위 마스터** | **설계 결정** | ⚠ 자유 입력 유지 |

### §8-2. 이 장에서 나온 공유 계약 후보

#### **한 컬럼에 증분과 치환이 함께 붙는다** — B-18 단서

| 행위 | 방식 | 낙관적 잠금 | 왜 |
| --- | --- | :-: | --- |
| 타발수 입력(`P-05-01`) | **증분** `+1,250` | ⛔ **안 건다** | 여러 POP 이 동시에 기여 |
| **PM 리셋**(이 화면) | **치환** `→ 0` | ✅ **건다** | 덮어쓰는 행위라 충돌 감지가 필요 |

#### **자기참조 체인 대신 마스터의 현재 값을 갱신한다**

| | 자기참조 체인 | **마스터 현재 값** |
| --- | --- | --- |
| 중간 한 건 취소 | ⛔ 뒤가 전부 어긋난다 | ✅ 영향 없다 |
| 이력 | 체인이 곧 이력 | 실적이 각자 남는다 |
"""

    def test_둘째_표는_미결이_아니다(self):
        결과 = self.parse(self.표가_둘)
        self.assertEqual([r["no"] for r in 결과["rows"]], ["1", "2"])
        self.assertEqual([r["done"] for r in 결과["rows"]], [True, False])

    def test_둘째_표의_행이_한_줄도_안_섞인다(self):
        결과 = self.parse(self.표가_둘)
        문면 = " ".join(r["item"] + r["handling"] for r in 결과["rows"])
        for 섞이면_안_되는_말 in ("증분", "치환", "자기참조", "체인이 곧 이력", "행위"):
            with self.subTest(말=섞이면_안_되는_말):
                self.assertNotIn(섞이면_안_되는_말, 문면)

    # ⛔ 미결 표가 «첫 표»가 아닌 스펙이 실재한다 — 2026-09-03 전수 실측에서
    #    미결 절에 표가 둘 이상인 4벌 중 `W-05-02`·`W-05-05` 는 앞에 DS 매핑 표가
    #    온다. 「첫 표만 센다」로 고쳤으면 그 둘이 통째로 사라진다.
    미결표가_뒤에 = """# W-99-03 시험용 화면

## §8. 미결

| 요소 | 유형 | 컴포넌트 |
| --- | --- | --- |
| 오더 목록 | 표 | DataGrid |

### §8-1. 미결

| # | 항목 | 성격 | 처리 |
| :-: | --- | --- | --- |
| **1** | **값 목록 미정** | **공통코드** | `W-06-06` |
"""

    def test_미결_표가_첫_표가_아니어도_찾는다(self):
        결과 = self.parse(self.미결표가_뒤에, "W-99-03-시험용화면.md")
        self.assertTrue(결과["table"])
        self.assertEqual([r["no"] for r in 결과["rows"]], ["1"])
        self.assertEqual(결과["rows"][0]["item"], "**값 목록 미정**")

    # ⓑ 정당한 비숫자 번호는 살아남는다 — 실물 3형태.
    #     `7(신설)`  P-01-01     `신설 6`  W-02-06     `~~5~~`  W-06-05
    #    (`~~5~~` 는 «취소선으로 해소를 적은» 형태라 행은 남되 done=True 다)
    비숫자_번호 = """# W-99-04 시험용 화면

## §8. 미결

| # | 항목 | 성격 | 처리 |
| :-: | --- | --- | --- |
| **7(신설)** | 채번 도출·검증 상세 미정 | 데이터 | 서버 몫 |
| **신설 6** | 모바일 반품 경로 | 프로세스 | 확인 |
| ~~5~~ | ~~BOM 확장 열도 작성중에만 편집 가능한가~~ | 설계 결정 | ✅ **종결(2026-08-29)** |
| **4-a** | 재고 상태 값 목록 | 공통코드 | `W-06-06` |
"""

    def test_비숫자_번호는_사라지지_않는다(self):
        결과 = self.parse(self.비숫자_번호, "W-99-04-시험용화면.md")
        self.assertEqual([r["no"] for r in 결과["rows"]],
                         ["7(신설)", "신설 6", "~~5~~", "4-a"])

    def test_취소선_번호는_행은_남고_해소로_센다(self):
        결과 = self.parse(self.비숫자_번호, "W-99-04-시험용화면.md")
        self.assertEqual([r["done"] for r in 결과["rows"]],
                         [False, False, True, False])


# ── C2 — 진도표 117 ↔ 미결·인계 대장 118 이 갈렸다 ──────────────────────────
#
# 폐지가 확정돼도 문서는 지우지 않는다(폐지 «판단의 근거»가 그 안에 있다).
# 그래서 스펙 «파일»을 세면 118, 정본 인벤토리는 117 이 되어 인도물 두 장이
# 다른 수를 말했다. 판정을 한 곳(`retired()`)에 두고 셋이 함께 쓴다.
class 폐지_확정_스펙(unittest.TestCase):

    폐지 = "# ~~W-06-13 · 검사정책 설정~~ → **`W-06-02`로 통합·폐지**\n\n## §8. 미결\n"

    def test_취소선과_폐지가_함께_있으면_폐지다(self):
        self.assertTrue(coi.retired(self.폐지))

    def test_낱말_하나로는_안_가른다(self):
        """⛔ 살아 있는 화면의 «이름»에 취소·통합·중단이 들어간다 — 실물 3벌."""
        for h1 in ("# W-01-13 · 물류 문서 진행현황·취소",
                   "# W-04-12 · 출하 확정·취소",
                   "# P-02-10 · 작업 중단(홀드) 등록",
                   "# W-06-02 · 검사기준 등록 — `W-06-13` 을 통합했다"):
            with self.subTest(h1=h1):
                self.assertFalse(coi.retired(h1 + "\n\n## §8. 미결\n"))

    def test_취소선만_있고_폐지가_없으면_아니다(self):
        # 제목의 «옛 이름»을 지우고 새 이름을 붙인 표기 — 폐지가 아니다.
        self.assertFalse(coi.retired("# ~~W-06-03 · 불량코드~~ 불량·원인코드 2계층 마스터\n"))

    def test_폐지_스펙도_행은_읽는다_세지_않을_뿐이다(self):
        """⭐ 안 읽으면 그 문서에 살아 있던 미결이 «소리 없이» 사라진다.

        `W-06-13` 에 실제로 2행이 있었다. 읽어 두어야 대장이 「몇 행이 딸려
        나갔나」를 적을 수 있고, 다음 사람이 통합처를 볼 수 있다.
        """
        tmp = tempfile.mkdtemp()
        try:
            경로 = os.path.join(tmp, "W-99-05-폐지화면.md")
            with open(경로, "w", encoding="utf-8") as f:
                f.write(self.폐지 + """
| # | 항목 | 성격 | 처리 |
| :-: | --- | --- | --- |
| **1** | 통합안이 부결되면 쓸 미결 | 설계 결정 | 보류 |
""")
            결과 = coi.parse(경로)
            self.assertTrue(결과["retired"])
            self.assertEqual([r["no"] for r in 결과["rows"]], ["1"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class 정본_실측(unittest.TestCase):
    """표본이 아니라 «지금 저장소»를 한 번 태운다 — 회귀가 여기서 먼저 보인다."""

    def test_폐지_스펙은_정확히_한_벌이고_그것이_W_06_13_이다(self):
        specs, gone = coi.collect()
        self.assertEqual([s["screen"] for s in gone], ["W-06-13"])
        self.assertNotIn("W-06-13", [s["screen"] for s in specs])

    def test_폐지_스펙에_딸린_미결은_계수에서만_빠진다(self):
        """세지 않는 것과 «없는 것»은 다르다 — 행은 읽혀 있어야 대장이 그 사실을 적는다."""
        _, gone = coi.collect()
        살아있는 = [r for s in gone for r in s["rows"] if not r["done"]]
        self.assertTrue(살아있는, "폐지 스펙의 미결 행을 아예 안 읽으면 대장이 그 사실을 못 적는다")

    def test_대장_문면이_폐지_제외를_말한다(self):
        """⛔ 조용히 빼면 다음 사람이 스펙 «파일»을 세고 「또 갈렸다」로 읽는다."""
        specs, gone = coi.collect()
        본문 = coi.render(specs, gone)
        self.assertIn("폐지 확정으로 제외한 스펙", 본문)
        self.assertIn("W-06-13", 본문)
        self.assertIn("| 화면 스펙 | **%d** |" % len(specs), 본문)

    def test_W_05_03_은_8_1_다섯_행만_낸다(self):
        specs, _ = coi.collect()
        w = next(s for s in specs if s["screen"] == "W-05-03")
        self.assertEqual(len(w["rows"]), 5)          # §8-1 미결 5행
        self.assertEqual([r["no"] for r in w["rows"]], ["1", "2", "3", "4", "5"])

    def test_정당한_비숫자_번호를_읽는다(self):
        """숫자가 아닌 미결 번호(`7(신설)`·`신설 6`·`4-a`)도 «행»으로 읽혀야 한다.

        ⛔ **표본을 「살아 있는 행」으로 잡지 않는다.** 그렇게 두었더니 2026-09-04
           하루에 두 번 빨개졌다 — 3회차가 `W-02-06` 신설 6 을, 이어서
           `P-01-01` 7(신설)을 **정당하게** 닫았기 때문이다. 미결이 닫히는 것은
           이 저장소가 «일을 한» 결과인데 그때마다 시험이 깨지면, 다음 사람은
           시험을 고치는 대신 «닫지 않는» 쪽으로 기울게 된다.
        ⇒ 읽히는가는 **해소 여부와 무관한 성질**이라 닫힌 행까지 전건에서 본다.
        """
        specs, _ = coi.collect()
        번호 = {(s["screen"], r["no"]) for s in specs for r in s["rows"]}
        for 표본 in (("P-01-01", "7(신설)"), ("W-02-06", "신설 6"),
                     ("M-01-12", "4-a"), ("W-CO-08", "1-a")):
            with self.subTest(표본=표본):
                self.assertIn(표본, 번호)
        꼴 = {n for _, n in 번호 if not n.isdigit()}
        self.assertTrue(any("(신설)" in n for n in 꼴), "`N(신설)` 꼴이 사라졌다")
        self.assertTrue(any(n.startswith("신설") for n in 꼴), "`신설 N` 꼴이 사라졌다")
        self.assertTrue(any(n.endswith("-a") for n in 꼴), "`N-a` 꼴이 사라졌다")


# ── `#N` 을 네 가지가 쓴다 — 우리 이슈만 표지다 (2026-09-04 · omf-mes#378) ──────
# ⭐ 문면은 전부 «실물»에서 따왔다 — 지어내면 시험이 실물을 안 지킨다.
우리이슈_맨몸 = "3 값 목록 미정 공통코드 W-06-06 · #145"
우리이슈_접두 = "1 문서 유형 값 집합 — **`omf-mes#347` 으로 판정된다** 확인 필요"
QA_띄움 = "6 알림 발송 대상 — 보류 등록이 알림 대상인가(QA #24)"
QA_붙임 = "2 재입하 이벤트(REQ-PR-0024·QA#23) — 자리표시"
타저장소_server = ("3 `mes_category_code` 값 목록 — ⛔ `enum` 을 만들지 않는다 · "
                "시드 삽입 확인은 `omf-mes-server#45`·`#46`")
타저장소_client = "1 「갭 없음」으로 읽고 client#85 로 넘긴 자리"
MLOT항목 = ("2 채번 상세 설계 부재 — 34자리 자릿수만 확정이고 도출·검증·유일성 "
           "규칙은 별도 후속 과제(MLOT #16)")
확정날짜 = "4 사출 조건은 설비가 갖는다 (✓확정 2026-07-14 #4)"
PR번호 = "1 2차 리뷰 반영(`PR #211`) — 문면만"
자기미결 = "5 「그렇게 처리한다」로 정정. **§8 미결 #3** 과 같은 자리"


class 표지_네갈래(unittest.TestCase):
    """⛔ 우리 이슈가 아닌 `#N` 을 표지로 세면 «엉뚱한 이슈»에 걸린다."""

    def test_맨몸_번호는_우리_이슈다(self):
        self.assertEqual(coi.tag_issues(우리이슈_맨몸), ["#145"])

    def test_우리_저장소_접두는_벗겨서_남긴다(self):
        """`omf-mes#347` 은 우리 것이다 — 접두가 붙었다고 버리면 안 된다."""
        self.assertEqual(coi.tag_issues(우리이슈_접두), ["#347"])

    def test_QA_는_띄우든_붙이든_버린다(self):
        self.assertEqual(coi.tag_issues(QA_띄움), [])
        self.assertEqual(coi.tag_issues(QA_붙임), [])

    def test_다른_저장소_이슈는_표지가_아니다(self):
        """⛔ V3 아래서 개발팀 저장소 이슈는 우리가 추적할 수 없다.

        `omf-mes-server#45` 를 `#45` 로 읽어 「닫힌 표지」 45행 안에 넣고 있었다.
        ⚠ 뒤따르는 `·#46` 은 «맨몸»이라 남는다 — 원문이 같은 저장소를 이어 쓴
           줄임꼴이지만, 그것까지 가르려면 문맥을 봐야 한다. 지금은 안 가른다.
        """
        self.assertNotIn("#45", coi.tag_issues(타저장소_server))
        self.assertEqual(coi.tag_issues(타저장소_client), [])

    def test_다른_번호_체계는_버린다(self):
        """MLOT(확정기록 항목) · 확정 날짜 · PR · 자기 미결 번호."""
        self.assertEqual(coi.tag_issues(MLOT항목), [])
        self.assertEqual(coi.tag_issues(확정날짜), [])
        self.assertEqual(coi.tag_issues(PR번호), [])
        self.assertEqual(coi.tag_issues(자기미결), [])

    def test_네자리_번호도_읽는다(self):
        """⛔ 옛 정규식은 `\d{1,3}` 이라 `#1024` 를 `#102` 로 읽었다."""
        self.assertEqual(coi.tag_issues("1 후속 — #1024 참조"), ["#1024"])

    def test_같은_번호는_한_번만_센다(self):
        self.assertEqual(coi.tag_issues("#61 과 omf-mes#61 은 같다"), ["#61"])

    def test_버린_번호에_이어진_목록도_버린다(self):
        """⛔ `QA #7·#10` 의 `#10` 은 앞 낱말이 구분점이라 낱말만 보면 샌다.

        2026-09-04 실측 8건 — `QA #12·#13`(`P-02-04`) · `QA #4·#6·#35`(`W-02-05`) ·
        `QA #33·#34`(`W-06-06`) · `QA #7·#10`(`W-06-08`) · `QA #1·#4·#6·#35`(`W-06-12`).
        """
        for 문면 in ("판정 근거(QA #7·#10)", "✓확정 QA #12 · #13",
                   "QA #1·#4·#6·#35 로 종결"):
            with self.subTest(문면=문면):
                self.assertEqual(coi.tag_issues(문면), [])

    def test_이어짐은_구분점뿐일_때만이다(self):
        """⚠ 반대로 막으면 안 된다 — 사이에 «말»이 있으면 이어진 목록이 아니다."""
        self.assertEqual(coi.tag_issues("QA #7 이 정했고 #145 가 남았다"), ["#145"])


class 조항과_절번호(unittest.TestCase):
    """⛔ `§4-B-1` 의 꼬리가 공유계약 조항 `B-1` 로 읽히면

    그 화면 «자신의 절»이 「답을 줄 상대」로 둔갑한다 — `E-n` 예외 번호와 같은 병이다.
    2026-09-04 실측 — 화면 스펙 전건 22회 · 이름 4종(`C-1` 13 · `C-2` 4 · `B-1` 4 · `B-2` 1).
    """

    @staticmethod
    def _조항(text):
        for kind, pat in coi.TRACKS:
            if kind == "조항":
                return pat.findall(text)
        raise AssertionError("조항 규칙이 TRACKS 에 없다")

    def test_절_번호의_꼬리는_조항이_아니다(self):
        for 문면 in ("이름 정합화만 데이터 모델 통지(§4-B-1)", "§4-B-1-a 참조",
                   "§4-C-1 표"):
            with self.subTest(문면=문면):
                self.assertEqual(self._조항(문면), [])

    def test_진짜_조항은_그대로_남는다(self):
        self.assertEqual(self._조항("공유계약 B-1 을 본다"), ["B-1"])
        self.assertEqual(self._조항("(A-11) 을 적용"), ["A-11"])
        self.assertEqual(self._조항("A-10·B-3 둘 다"), ["A-10", "B-3"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
