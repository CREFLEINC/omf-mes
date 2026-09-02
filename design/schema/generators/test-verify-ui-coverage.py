#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# verify-ui-coverage.py 의 단위 테스트. 표준 라이브러리만 쓴다.
import io, os, sys, unittest, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
cov = importlib.import_module("verify-ui-coverage")

SCREENS_ROOT = os.path.join(HERE, "..", "..", "wiki", "screens")
W0607 = os.path.join(SCREENS_ROOT, "06", "W-06-07-창고Location마스터.md")


def _read(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


class ExtractActionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = cov.extract_actions(W0607)

    def test_화면ID를_파일명에서_읽는다(self):
        self.assertTrue(all(r["screen"] == "W-06-07" for r in self.rows))

    def test_액션을_일곱_뽑는다(self):
        self.assertEqual(len(self.rows), 7)

    def test_첫_액션이_창고_추가다(self):
        self.assertEqual(self.rows[0]["action"], "창고 추가")

    def test_굵은표기를_벗긴다(self):
        acts = [r["action"] for r in self.rows]
        self.assertIn("사용 중지", acts)
        self.assertIn("라벨 이미지 생성", acts)

    def test_구분선과_헤더행은_제외한다(self):
        acts = [r["action"] for r in self.rows]
        self.assertNotIn("액션", acts)
        self.assertFalse(any(a.startswith("---") for a in acts))

    def test_전체_화면을_모으면_14개다(self):
        rows = cov.extract_all(SCREENS_ROOT)
        screens = sorted({r["screen"] for r in rows})
        self.assertEqual(len(screens), 14, screens)
        self.assertIn("W-CO-02", screens)
        self.assertIn("W-06-07", screens)
        self.assertIn("W-06-14", screens)  # 2026-08-07 편입 — 계약이 먼저 쓰였다
        self.assertNotIn("W-06-13", screens)  # 통합 폐지 — W-06-02 에 흡수
        # ⭐ 2026-08-18 복귀 — 셋을 뺐던 근거가 「테이블이 없다」였고 그것이 뒤집혔다.
        for back in ("W-06-08", "W-06-09", "W-06-12"):
            self.assertIn(back, screens)


# §5-1 표의 열 구성이 화면마다 다르다 — 대상 10개 중 9개는
# 「액션|위치|활성 조건|비고」 4열이지만 W-06-10 만 「액션|활성 조건|비고」
# 3열(위치 열이 없다). 열 위치를 고정 인덱스(cells[2]=활성 조건,
# cells[3]=비고)로 읽으면 W-06-10 에서 활성 조건과 비고가 뒤바뀐다.
# 이 클래스는 그 회귀를 잠근다 — 고정 인덱스 코드로는 실패하고
# 헤더 이름 기반 조회에서는 통과해야 한다.
class ColumnMappingRegressionTest(unittest.TestCase):
    W0610 = os.path.join(SCREENS_ROOT, "06", "W-06-10-연계동기화현황실패재처리.md")

    def test_3열_표에서_활성조건과_비고를_바르게_읽는다(self):
        # W-06-10 원문(3열): "| 조회 | **기간 지정됨** | 로그 규약 |"
        # 고정 인덱스(cells[2]) 로 읽으면 activation 대신 비고 텍스트가
        # condition 에 들어가고 note 는 항상 빈 문자열이 된다.
        rows = cov.extract_actions(self.W0610)
        row = next(r for r in rows if r["action"] == "조회")
        self.assertEqual(row["condition"], "기간 지정됨")
        self.assertEqual(row["note"], "로그 규약")

    def test_4열_표에서_활성조건과_비고를_바르게_읽는다(self):
        # W-06-07 원문(4열): "| 창고 추가 | 헤더 | 항상 | |"
        rows = cov.extract_actions(W0607)
        row = next(r for r in rows if r["action"] == "창고 추가")
        self.assertEqual(row["condition"], "항상")
        self.assertEqual(row["note"], "")


# 01 자재창고는 액션 소절 번호가 화면마다 다르고(§5-2·§5-5~§5-8), 액션 소절이
# §5 의 마지막 소절인 화면이 많다. 두 가정을 잠근다.
class Domain01Test(unittest.TestCase):
    M0104 = os.path.join(SCREENS_ROOT, "01", "M-01-04-자재위치확인.md")
    W0101 = os.path.join(SCREENS_ROOT, "01", "W-01-01-IQC수입검사판정.md")

    def test_소절_번호가_1이_아니어도_찾는다(self):
        # M-01-04 의 액션 표는 §5-7 이다. §5-1 로 고정하면 0건이 된다.
        rows = cov.extract_actions(self.M0104)
        self.assertEqual([r["action"] for r in rows],
                         ["스캔(암묵)", "직접 입력", "다음 스캔"])

    def test_액션_소절이_마지막이면_다음_장에서_끊는다(self):
        # 소절의 끝을 「다음 ###」으로만 찾으면 다음 제목이 `## §6` 이라
        # §6·§7·§8 의 표까지 삼킨다. M-01-04 는 3건이어야 한다.
        block = cov.find_action_block(_read(self.M0104))
        self.assertNotIn("§6", block)
        self.assertNotIn("EmptyState", block)

    def test_액션_표가_없으면_None_이다(self):
        # W-01-01 은 §5 에 판정 분기만 있고 액션 표가 없다.
        self.assertIsNone(cov.find_action_block(_read(self.W0101)))
        self.assertEqual(cov.extract_actions(self.W0101), [])

    def test_액션_표_없는_화면을_숨기지_않는다(self):
        missing = cov.screens_without_action_table(SCREENS_ROOT, cov.SCREENS_01)
        self.assertEqual(sorted(missing),
                         ["M-01-01", "W-01-01", "W-01-02", "W-01-10"])

    def test_취소_화면이_등록돼_있다(self):
        # W-01-13 은 01 계약 개정(2026-08-07)으로 들어왔다. 빠지면 취소 액션이
        # 커버리지 대조에서 통째로 사라진다.
        rows = cov.extract_all(SCREENS_ROOT, cov.SCREENS_01)
        screens = {r["screen"] for r in rows}
        self.assertIn("W-01-13", screens)
        # 119 — W-01-06 에 「자체 폐기 체크」·「폐기 거래처 선택」 2건 추가(DR-013) +
        #       P-01-01 「인쇄(등록 완료분)」 1건. ⚠ 118 은 2026-08-29 실측에서 이미 낡아
        #       있었다 — 이 수치는 verify-counts 등록부와 달리 아무도 감시하지 않는다.
        # ⭐ 126 (2026-09-02 · omf-mes#335) — 121 에서 +5.
        #    ⛔ 그 121 자체가 «이미 빨강»이었다. W-01-07 선택지 행 +1 이 들어온 뒤
        #       아무도 이 수치를 고치지 않아 origin/main 에서 121 != 120 으로 깨져
        #       있었다(실측). 이 파일 자신이 위에 적어 둔 「아무도 감시하지 않는다」가
        #       그대로 실현된 것이다 — 검토 절차의 검사기 표에 test-*.py 가 없다.
        #    +4 는 명단에 M-01-12·M-01-13 을 되살린 몫이고(생성기 주석 참조),
        #       +1 은 M-01-13 §5-2 에 「내가 올린 요청 조회」 행을 더한 몫이다.
        self.assertEqual(len(rows), 126)

    def test_모바일_POP_화면ID도_읽는다(self):
        rows = cov.extract_actions(self.M0104)
        self.assertTrue(all(r["screen"] == "M-01-04" for r in rows))

    def test_기준정보_추출은_그대로다(self):
        # 공용 코드를 고쳤으므로 기존 도메인이 안 흔들리는지 함께 잠근다.
        rows = cov.extract_all(SCREENS_ROOT)
        # 104 — 81(DR-013 거래처 역할 탭까지) ＋ 2026-08-18 복귀 세 화면 18건 ＋ 1 ＋ 4.
        # ⭐ 그 1 은 `535f068`(#290 되살리기 2차)이 W-CO-02 에 「비밀번호 초기화」를
        #    더한 것이다. 7 → 8 로 늘었다.
        # ⭐ 마지막 4 는 2026-09-03 — `W-06-01` 이 **공정 마스터를 흡수**하면서 §5-1 에
        #    더한 액션 4건이다(공정 추가 · 공정 수정 · 사용 중지/재개 · 공정 유형 선택).
        #    사용자 확정으로 「공정 마스터 관리 화면이 어디인가」(§8-5 미결 5)를 닫았다 —
        #    `mdm.process` 는 `REQ-PR-0026` 이 확정한 MES 정본인데 «만드는» 화면이
        #    없었다. 최상위 탭 2개(《Routing》/《공정 마스터》)로 나눈 결과다.
        # ⛔ 이 수를 올릴 때는 «무엇이 늘었는지»를 여기 함께 적는다. 안 적으면 다음 사람이
        #    「그냥 올리면 되겠지」로 지나가고, 진짜 결손이 나도 같은 말로 넘어간다.
        #    실제로 그랬다 — 99 는 `535f068`(2026-08-30) 부터 낡았는데 시험이 사흘을
        #    빨간 채로 서 있었고, 고칠 때도 왜 늘었는지는 안 적혔다(`omf-mes#358`).
        self.assertEqual(len(rows), 104)
        self.assertEqual(len({r["screen"] for r in rows}), 14)


class DomainAppTest(unittest.TestCase):
    # 공통 승인 2장. 도메인이 늘면서 등록부가 갈리는지 잠근다.
    def test_두_화면을_뽑는다(self):
        rows = cov.extract_all(SCREENS_ROOT, cov.SCREENS_APP)
        self.assertEqual(sorted({r["screen"] for r in rows}), ["W-06-15", "W-CO-09"])

    def test_액션이_20건이다(self):
        self.assertEqual(len(cov.extract_all(SCREENS_ROOT, cov.SCREENS_APP)), 20)

    def test_액션_표_없는_화면이_없다(self):
        self.assertEqual(cov.screens_without_action_table(SCREENS_ROOT, cov.SCREENS_APP), [])

    def test_도메인_등록부에_아홉이_있다(self):
        self.assertEqual(sorted(cov.DOMAINS),
                         ["01", "02", "03", "04", "05", "app", "co", "mdm", "print"])

    def test_공통은_10장이고_액션_표가_다_있다(self):
        # ⛔ 2026-08-19 까지 공통 10장이 게이트 «밖» 이었다 — 요구서 여덟 편은 매핑
        #    절이 §3 인데 공통 한 편만 §2 라 소절 인식에 안 걸렸다. 화면 진도표를
        #    만들자 「요구서가 다루지 않은 화면」으로 떠서 드러났다.
        self.assertEqual(len(cov.SCREENS_CO), 10)
        self.assertEqual(cov.screens_without_action_table(SCREENS_ROOT, cov.SCREENS_CO), [])
        rows = cov.extract_all(SCREENS_ROOT, cov.SCREENS_CO)
        self.assertEqual(len({r["screen"] for r in rows}), 10)
        # 48 — W-CO-04 에 「게시」 1건 추가(2026-08-29 · 공지 상태 모델을 계약과 맞추며
        #      기간이 정하는 3값 대신 명시적 게시 액션을 세웠다)
        self.assertEqual(len(rows), 48)

    def test_05_설비툴은_17장이고_액션_표가_다_있다(self):
        self.assertEqual(len(cov.SCREENS_05), 17)
        self.assertEqual(cov.screens_without_action_table(SCREENS_ROOT, cov.SCREENS_05), [])
        rows = cov.extract_all(SCREENS_ROOT, cov.SCREENS_05)
        self.assertEqual(len({r["screen"] for r in rows}), 17)


class DomainPrintTest(unittest.TestCase):
    # 공통 출력물 5장. ⚠ 이 편은 화면을 소유하지 않는다 — 출력이 주 기능이고
    # 도메인 요구서가 아직 없는 것만 등록한다. 범위가 다시 넓어지면 여기서 걸린다.
    def test_다섯_화면이_등록돼_있다(self):
        self.assertEqual(
            sorted(cov.SCREENS_PRINT),
            ["P-02-05", "P-02-07", "P-02-09", "P-04-02", "P-04-04"],
        )

    def test_이미_다른_도메인이_세는_화면은_없다(self):
        # P-01-01·P-01-02 는 01 이 센다. 여기 들어오면 이중 계상이다.
        overlap = set(cov.SCREENS_PRINT) & set(cov.SCREENS_01)
        self.assertEqual(overlap, set())

    def test_액션이_17건이다(self):
        # 액션 표가 있는 두 장(P-04-02 8 · P-04-04 9)만 센다.
        self.assertEqual(len(cov.extract_all(SCREENS_ROOT, cov.SCREENS_PRINT)), 17)

    def test_액션_표_없는_화면_셋을_알린다(self):
        # 확대 3차 서식이라 표가 없다. 조용히 0건으로 넘어가면 안 된다.
        self.assertEqual(
            cov.screens_without_action_table(SCREENS_ROOT, cov.SCREENS_PRINT),
            ["P-02-05", "P-02-07", "P-02-09"],
        )

class Domain03Test(unittest.TestCase):
    # 03 품질 7장. ⭐ 도메인 배지(dom=03)는 5장인데 계약 대상은 7이다 —
    # 01·02 가 「03 소관」으로 미룬 두 장이 여기서 풀린다. 그 둘이 조용히
    # 빠지면 커버리지가 「전건 다뤘다」로 부풀려진다.
    def test_여덟_화면이_등록돼_있다(self):
        self.assertEqual(len(cov.SCREENS_03), 8)   # W-03-10 신설(DR-008 3-A)

    def test_이월_두_장이_들어_있다(self):
        ids = list(cov.SCREENS_03)
        self.assertIn("W-01-01", ids)   # 01 요구서 §6-1
        self.assertIn("P-02-13", ids)   # 02 요구서 머리 「03 소관 1 제외」

    def test_결번은_등록하지_않는다(self):
        ids = set(cov.SCREENS_03)
        for vacated in ("W-03-04", "W-03-06", "W-03-07", "W-03-08"):
            self.assertNotIn(vacated, ids)

    def test_액션_표_없는_화면은_W_01_01_뿐이다(self):
        # 파일럿 서식이라 액션 표가 없다. 요구는 §5 본문에서 사람이 읽는다.
        self.assertEqual(
            cov.screens_without_action_table(SCREENS_ROOT, cov.SCREENS_03), ["W-01-01"])

class Domain04Test(unittest.TestCase):
    # 04 제품출하 16장. ⭐ 도메인 배지는 18 인데 계약 대상은 16 이다 —
    # P-04-02·P-04-04 는 출력물 계약이 이미 센다. 여기 들어오면 이중 계상이다.
    def test_열여섯_화면이_등록돼_있다(self):
        self.assertEqual(len(cov.SCREENS_04), 16)

    def test_출력물_계약이_세는_둘은_없다(self):
        ids = set(cov.SCREENS_04)
        self.assertNotIn("P-04-02", ids)
        self.assertNotIn("P-04-04", ids)

    def test_이미_다른_도메인이_세는_화면은_없다(self):
        mine = set(cov.SCREENS_04)
        for other in (cov.SCREENS_PRINT, cov.SCREENS_02, cov.SCREENS_03, cov.SCREENS_01):
            self.assertEqual(mine & set(other), set())

    def test_결번은_등록하지_않는다(self):
        ids = set(cov.SCREENS_04)
        for vacated in ("W-04-09", "M-04-02"):
            self.assertNotIn(vacated, ids)

    def test_액션_표가_전부_있다(self):
        self.assertEqual(cov.screens_without_action_table(SCREENS_ROOT, cov.SCREENS_04), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
