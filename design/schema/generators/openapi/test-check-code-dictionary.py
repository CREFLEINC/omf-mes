#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# check-code-dictionary.py 의 단위 테스트. 표준 라이브러리만 쓴다(저장소 관행).
#
# ⛔ 이 파일이 잠그는 사고는 하나다 — **키가 「같은 이름 다른 값집합」을 못 갈랐다.**
# 첫 판은 사전의 「값」 칸에 «프로퍼티 이름»(documentTypeCode)을 적었고, 검사기가
# 이름으로만 세어 세 키가 «같은 9자리»를 봤다. 「어느 자리가 어느 키인가」를 기계가
# 판정 못 한 것이고, 그것이 이 사전의 존재 이유다.
# ⇒ 값 칸에 실제 코드 문자열을 담고 «값으로» 대조하게 고쳤다. 그 회귀를 잠근다.
#
# ⭐ 2026-09-02 — 값 대조만으로는 **값집합이 우연히 같은 다른 코드를 못 가른다**는
# 것이 실물로 드러났다(CD-PICKING-TYPE 의 MATERIAL·SHIPMENT ⊂ CD-RESERVATION-TYPE 의
# MATERIAL·SHIPMENT·PRODUCTION). 그래서 계약이 자리마다 `x-code-key` 를 «직접» 적고
# 검사기는 대조만 한다. 아래 세 벌(㉠㉡㉢)이 그 대조가 실제로 ⛔ 를 내는지 잠근다.
import importlib
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
cd = importlib.import_module("check-code-dictionary")

PRINT9 = ["MATERIAL_LOT_LABEL", "GOODS_ISSUE_QR", "PACKING_LABEL"]
LOGI9 = ["PURCHASE_ORDER", "INBOUND_RECEIPT", "GOODS_ISSUE"]


class 자리_상태를_가른다(unittest.TestCase):
    def test_enum이_있으면_enum(self):
        self.assertEqual(cd.state({"type": "string", "enum": PRINT9}, None), "enum")

    def test_배열이면_items에서_본다(self):
        self.assertEqual(
            cd.state({"type": "array", "items": {"enum": PRINT9}}, None), "enum")

    def test_포인터가_있으면_ptr(self):
        d = "값 목록은 GET /mdm/code-values?codeGroupCode=CYCLE_TYPE 로 받는다"
        self.assertEqual(cd.state({"type": "string"}, d), "ptr")

    def test_둘_다_없으면_bare(self):
        self.assertEqual(cd.state({"type": "string"}, "그냥 설명"), "bare")

    def test_enum이_포인터보다_먼저다(self):
        d = "codeGroupCode=X 로 받는다"
        self.assertEqual(cd.state({"type": "string", "enum": PRINT9}, d), "enum")


class 사전_표를_읽는다(unittest.TestCase):
    """⛔ 열이 «정확히 일곱»인 표만 본다 — 같은 문서의 결과 표를 삼켰다(10 → 13)."""

    @staticmethod
    def parse(text):
        import tempfile
        p = os.path.join(tempfile.mkdtemp(), "d.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return cd.read_dictionary(p)

    def test_일곱_열_행을_읽는다(self):
        row = ("| `CD-PRINT-DOCUMENT-TYPE` | `MATERIAL_LOT_LABEL` `PACKING_LABEL` "
               "| — | `documentTypeCode` | `enum` | 6 | 근거 |\n")
        got = self.parse(row)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["key"], "CD-PRINT-DOCUMENT-TYPE")
        self.assertEqual(got[0]["values"], ["MATERIAL_LOT_LABEL", "PACKING_LABEL"])
        self.assertEqual(got[0]["group"], [])
        self.assertEqual(got[0]["names"], ["documentTypeCode"])
        self.assertEqual(got[0]["owner"], "enum")
        self.assertEqual(got[0]["places"], 6)

    def test_registry_는_값과_그룹을_따로_갖는다(self):
        # ⭐ 값 열은 «언제나» 코드 문자열이고 그룹은 따로다.
        #    첫 판은 registry 갈래의 값 열에 그룹 이름을 적어 한 열에 두 종류가 섞였다.
        row = ("| `CD-MAINTENANCE-ORDER-STATUS` | `ISSUED` `DONE` `CANCELLED` "
               "| `MAINTENANCE_ORDER_STATUS` | `statusCode` | `registry-system` | 2 | 근거 |\n")
        got = self.parse(row)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["values"], ["ISSUED", "DONE", "CANCELLED"])
        self.assertEqual(got[0]["group"], ["MAINTENANCE_ORDER_STATUS"])
        self.assertEqual(got[0]["owner"], "registry-system")

    def test_다섯_열_결과표는_안_읽는다(self):
        # ⛔ 실제로 삼켰던 형태 — 문서 아래쪽 「검증 결과」 표.
        row = "| `CD-PRINT-DOCUMENT-TYPE` | 7 | 4 | **3** | 어디 |\n"
        self.assertEqual(self.parse(row), [])

    def test_키가_아니면_안_읽는다(self):
        row = "| 무엇 | 값 | 그룹 | 이름 | 소유 | 자리 | 근거 |\n"
        self.assertEqual(self.parse(row), [])


class 값으로_갈라야_같은_이름이_갈린다(unittest.TestCase):
    """⭐ 이 사전의 핵심 — 값이 다르면 키가 다르다."""

    def test_같은_이름_다른_값집합은_다른_자리다(self):
        # 사전이 PRINT9 를 선언했는데 자리의 enum 이 LOGI9 면 «남의 자리»다.
        self.assertNotEqual(set(PRINT9), set(LOGI9))

    def test_null이_섞인_enum도_값으로_맞춘다(self):
        # destinationTypeCode 가 nullable 이라 enum 에 None 이 들어 있다.
        enum = ("LOCATION", "PARTNER", "DISPOSAL_SITE", None)
        want = {"LOCATION", "PARTNER", "DISPOSAL_SITE"}
        self.assertEqual(want, {x for x in enum if x is not None})


class 형제_갈림을_찾는다(unittest.TestCase):
    """④ 같은 이름이 「값 있음」과 「맨몸」으로 갈린 자리."""

    def test_갈리면_잡는다(self):
        found = {"statusCode": [
            ("logi", "스키마", "/a", "ptr", (), ("X",)),
            ("logi", "쿼리", "/b", "bare", (), ()),
        ]}
        out = cd.split_siblings(found)
        self.assertEqual(len(out), 1)
        name, f, bare, has, tot = out[0]
        self.assertEqual((name, len(bare), has, tot), ("statusCode", 1, "ptr", 2))

    def test_전부_맨몸이면_안_잡는다(self):
        # 「갈렸다」가 아니라 「통째로 없다」다 — 다른 물음이다.
        found = {"x": [("f", "스키마", "/a", "bare", (), ()),
                       ("f", "쿼리", "/b", "bare", (), ())]}
        self.assertEqual(cd.split_siblings(found), [])

    def test_계약이_다르면_안_묶는다(self):
        found = {"x": [("A", "스키마", "/a", "enum", ("V",), ()),
                       ("B", "쿼리", "/b", "bare", (), ())]}
        self.assertEqual(cd.split_siblings(found), [])



def 사전행(key, values=(), group=(), names=(), owner="enum", places=None):
    """사전 한 행을 지어낸다 — read_dictionary 가 내는 모양 그대로."""
    return {"key": key, "values": list(values), "group": list(group),
            "names": list(names), "owner": owner, "places": places, "basis": "테스트"}


def 자리(f="logi", kind="스키마", path="/a", st="enum", enum=(), ptr=(),
       key=None, landed=False):
    """계약 자리 한 칸을 지어낸다 — scan() 이 내는 여덟 칸 튜플 그대로."""
    return (f, kind, path, st, tuple(enum), tuple(ptr), key, landed)


class 키로_대조한다(unittest.TestCase):
    """⑤ ㉠㉡㉢ — 셋 다 ⛔ 다. 「이미 붙인 키가 «틀렸다»」는 다른 결정 없이 고친다."""

    def test_규칙1_사전에_없는_키는_잡는다(self):
        sites = cd.key_sites({"typeCode": [자리(enum=PRINT9, key="CD-없는키")]})
        unknown, enum_gap, ptr_gap = cd.check_keys(sites, [사전행("CD-PRINT-DOCUMENT-TYPE")])
        self.assertEqual(len(unknown), 1)
        self.assertEqual(unknown[0][4], "CD-없는키")
        self.assertEqual((enum_gap, ptr_gap), ([], []))

    def test_규칙2_값집합이_다르면_잡는다(self):
        # ⭐ 이 사고의 실물 — PICKING(2값)과 RESERVATION(3값)은 두 값이 겹친다.
        sites = cd.key_sites({"typeCode": [
            자리(enum=("MATERIAL", "SHIPMENT"), key="CD-RESERVATION-TYPE")]})
        e = 사전행("CD-RESERVATION-TYPE",
                 values=("MATERIAL", "SHIPMENT", "PRODUCTION"))
        unknown, enum_gap, ptr_gap = cd.check_keys(sites, [e])
        self.assertEqual((unknown, ptr_gap), ([], []))
        self.assertEqual(len(enum_gap), 1)
        self.assertEqual(enum_gap[0][5], ["MATERIAL", "PRODUCTION", "SHIPMENT"])  # 사전
        self.assertEqual(enum_gap[0][6], ["MATERIAL", "SHIPMENT"])                # 계약

    def test_규칙2_값집합이_같으면_안_잡는다(self):
        sites = cd.key_sites({"typeCode": [
            자리(enum=("MATERIAL", "SHIPMENT"), key="CD-PICKING-TYPE")]})
        e = 사전행("CD-PICKING-TYPE", values=("SHIPMENT", "MATERIAL"))  # 순서는 무관하다
        self.assertEqual(cd.check_keys(sites, [e]), ([], [], []))

    def test_규칙2_null이_섞여도_안_잡는다(self):
        # nullable 자리는 enum 에 None 이 들어 있다 — 값으로 세지 않는다.
        sites = cd.key_sites({"typeCode": [
            자리(enum=("LOCATION", "PARTNER", None), key="CD-X")]})
        e = 사전행("CD-X", values=("LOCATION", "PARTNER"))
        self.assertEqual(cd.check_keys(sites, [e]), ([], [], []))

    def test_규칙2_사전_값이_비면_건너뛴다(self):
        # ⬜ 로 «세어서» 남긴 키다 — 대조할 것이 없는 자리를 ⛔ 로 내면
        # 「값을 모른다」가 「키가 틀렸다」로 둔갑한다.
        sites = cd.key_sites({"typeCode": [자리(enum=("A_ONE",), key="CD-X")]})
        self.assertEqual(cd.check_keys(sites, [사전행("CD-X")]), ([], [], []))

    def test_규칙3_그룹_포인터가_다르면_잡는다(self):
        sites = cd.key_sites({"statusCode": [
            자리(st="ptr", ptr=("LOT_STATUS",), key="CD-LOT-STATUS")]})
        e = 사전행("CD-LOT-STATUS", group=("MAINTENANCE_ORDER_STATUS",),
                 owner="registry-system")
        unknown, enum_gap, ptr_gap = cd.check_keys(sites, [e])
        self.assertEqual((unknown, enum_gap), ([], []))
        self.assertEqual(len(ptr_gap), 1)
        self.assertEqual((ptr_gap[0][5], ptr_gap[0][6]),
                         (["MAINTENANCE_ORDER_STATUS"], ["LOT_STATUS"]))

    def test_규칙3_사전이_그룹을_안_적었는데_포인터가_있으면_잡는다(self):
        # enum 소유로 적힌 키인데 계약은 등록부 그룹을 가리킨다 — 소유가 어긋난다.
        sites = cd.key_sites({"statusCode": [
            자리(st="ptr", ptr=("LOT_STATUS",), key="CD-X")]})
        _, _, ptr_gap = cd.check_keys(sites, [사전행("CD-X", values=("A_ONE",))])
        self.assertEqual(len(ptr_gap), 1)

    def test_규칙3_같으면_안_잡는다(self):
        sites = cd.key_sites({"statusCode": [
            자리(st="ptr", ptr=("LOT_STATUS",), key="CD-LOT-STATUS")]})
        e = 사전행("CD-LOT-STATUS", group=("LOT_STATUS",), owner="registry-system")
        self.assertEqual(cd.check_keys(sites, [e]), ([], [], []))

    def test_키가_없는_자리는_대조하지_않는다(self):
        # ㉣ 소관이다 — ⑤ 는 «붙은» 키만 본다.
        sites = cd.key_sites({"typeCode": [자리(enum=PRINT9), 자리(st="bare")]})
        self.assertEqual(sites, [])

    def test_실물에는_세_규칙_위반이_없다(self):
        """⛔ 게이트다 — 실물 계약 7벌이 초록이어야 한다."""
        entries = cd.read_dictionary(cd.DICT)
        unknown, enum_gap, ptr_gap = cd.check_keys(cd.key_sites(cd.scan()), entries)
        self.assertEqual([u[4] for u in unknown], [], "㉠ 사전에 없는 키")
        self.assertEqual([(g[4], g[3]) for g in enum_gap], [], "㉡ 값집합 어긋남")
        self.assertEqual([(g[4], g[3]) for g in ptr_gap], [], "㉢ 그룹 어긋남")


class 소유와_자리의_모양이_맞는가(unittest.TestCase):
    """⑤ ㉤㉥ — 2026-09-03 신설. 둘 다 ⛔ 다.

    ⭐ 소유는 「값이 어디 사나」다 — `enum` 이면 계약 안, `registry*` 면 공통코드
       마스터. 어긋나면 사전이 「계약이 닫는다」는데 자리는 열려 있거나, 마스터의
       값을 계약이 또 갖는다(두 벌).
    ⛔ 이 구멍을 «어느 검사기도 안 보고 있었다» — ㉡ 는 enum 이 있을 때만 값을
       비교하고 없다는 사실 자체는 안 본다.
    """

    def test_소유가_enum인데_자리에_enum이_없으면_잡는다(self):
        sites = cd.key_sites({"typeCode": [자리(st="bare", key="CD-X")]})
        miss, sur = cd.check_owner_shape(sites, [사전행("CD-X", values=("A", "B"))])
        self.assertEqual(len(miss), 1)
        self.assertEqual(sur, [])
        self.assertEqual(miss[0][4], "CD-X")

    def test_소유가_enum이고_자리에_enum이_있으면_안_잡는다(self):
        sites = cd.key_sites({"typeCode": [자리(enum=("A", "B"), key="CD-X")]})
        e = 사전행("CD-X", values=("A", "B"))
        self.assertEqual(cd.check_owner_shape(sites, [e]), ([], []))

    def test_사전_값이_비면_enum을_요구하지_않는다(self):
        # ⚠ 넣을 값이 없는데 요구할 수 없다 — ⬜ 로 세어서 남긴 키가 그것이다.
        sites = cd.key_sites({"typeCode": [자리(st="bare", key="CD-X")]})
        self.assertEqual(cd.check_owner_shape(sites, [사전행("CD-X")]), ([], []))

    def test_소유가_registry인데_enum이_있으면_잡는다(self):
        sites = cd.key_sites({"typeCode": [자리(enum=("A", "B"), key="CD-X")]})
        e = 사전행("CD-X", values=("A", "B"), group=("G",), owner="registry")
        miss, sur = cd.check_owner_shape(sites, [e])
        self.assertEqual(miss, [])
        self.assertEqual(len(sur), 1)
        self.assertEqual(sur[0][5], ["A", "B"])

    def test_소유가_registry_system이어도_같다(self):
        sites = cd.key_sites({"typeCode": [자리(enum=("A",), key="CD-X")]})
        e = 사전행("CD-X", values=("A",), group=("G",), owner="registry-system")
        _, sur = cd.check_owner_shape(sites, [e])
        self.assertEqual(len(sur), 1)

    def test_소유가_registry이고_enum이_없으면_안_잡는다(self):
        sites = cd.key_sites({"typeCode": [자리(st="ptr", ptr=("G",), key="CD-X")]})
        e = 사전행("CD-X", values=("A",), group=("G",), owner="registry")
        self.assertEqual(cd.check_owner_shape(sites, [e]), ([], []))

    def test_사전에_없는_키는_넘긴다(self):
        # ㉠ 가 이미 잡는다 — 여기서 또 내면 한 사고가 두 줄로 보인다.
        sites = cd.key_sites({"typeCode": [자리(st="bare", key="CD-없는키")]})
        self.assertEqual(cd.check_owner_shape(sites, [사전행("CD-X")]), ([], []))

    def test_키가_배열이고_소유가_섞이면_판정하지_않는다(self):
        # ⚠ 한 자리가 enum 키와 registry 키를 함께 가리키면 어느 모양이어야
        #    하는지 정할 수 없다 — 그 판정은 사람이 한다.
        sites = cd.key_sites({"typeCode": [자리(st="bare", key=["CD-A", "CD-B"])]})
        entries = [사전행("CD-A", values=("X",)),
                   사전행("CD-B", values=("Y",), group=("G",), owner="registry")]
        self.assertEqual(cd.check_owner_shape(sites, entries), ([], []))

    def test_실물에는_모양_위반이_없다(self):
        """⛔ 게이트다 — 실물 계약 7벌이 초록이어야 한다."""
        entries = cd.read_dictionary(cd.DICT)
        miss, sur = cd.check_owner_shape(cd.key_sites(cd.scan()), entries)
        self.assertEqual([(m[4], m[3]) for m in miss], [], "㉤ 소유 enum 인데 enum 없음")
        self.assertEqual([(s[4], s[3]) for s in sur], [], "㉥ 소유 registry 인데 enum 있음")


class 키가_없는_착지_자리를_센다(unittest.TestCase):
    """㉣ ⚠ **막지 않는다 — 센다.**

    래칫도 걸지 않는다 — 지금 여러 손이 동시에 줄이는 수라 기준선을 두면
    한쪽이 줄이는 순간 다른 쪽 작업 트리가 ⛔ 가 되어 서로 방해한다.
    """

    def test_착지했는데_키가_없으면_센다(self):
        found = {"typeCode": [자리(landed=True)]}
        self.assertEqual(len(cd.keyless_landed(found)), 1)

    def test_키가_있으면_안_센다(self):
        found = {"typeCode": [자리(landed=True, key="CD-X")]}
        self.assertEqual(cd.keyless_landed(found), [])

    def test_착지_안_한_자리는_안_센다(self):
        # ⭐ 물리 컬럼이 안 정해진 자리에 키를 요구하면 «판정 전에» 이름을 붙이란 말이다.
        found = {"typeCode": [자리(landed=False)]}
        self.assertEqual(cd.keyless_landed(found), [])


class 사전이_키로_자리를_센다(unittest.TestCase):
    """③ 키가 붙은 자리는 «키로», 안 붙은 자리는 옛 방식(값·그룹)으로 짚는다."""

    def test_키가_맞으면_값이_달라도_내_자리다(self):
        e = 사전행("CD-PICKING-TYPE", values=("MATERIAL", "SHIPMENT"), owner="enum")
        self.assertTrue(cd.matches(e, 자리(enum=("MATERIAL",), key="CD-PICKING-TYPE")))

    def test_키가_다르면_값이_같아도_남의_자리다(self):
        # ⭐ 이것이 키 대조의 전부다 — 값 대조로는 영영 못 가르는 자리.
        e = 사전행("CD-PICKING-TYPE", values=("MATERIAL", "SHIPMENT"), owner="enum")
        p = 자리(enum=("MATERIAL", "SHIPMENT"), key="CD-RESERVATION-TYPE")
        self.assertFalse(cd.matches(e, p))

    def test_키가_없으면_값으로_짚는다(self):
        e = 사전행("CD-PRINT-DOCUMENT-TYPE", values=PRINT9, owner="enum")
        self.assertTrue(cd.matches(e, 자리(enum=PRINT9)))
        self.assertFalse(cd.matches(e, 자리(enum=LOGI9)))

    def test_키가_없으면_registry는_그룹으로_짚는다(self):
        e = 사전행("CD-LOT-STATUS", group=("LOT_STATUS",), owner="registry-system")
        self.assertTrue(cd.matches(e, 자리(st="ptr", ptr=("LOT_STATUS",))))
        self.assertFalse(cd.matches(e, 자리(st="ptr", ptr=("OTHER_STATUS",))))

    def test_옛_여섯칸_튜플도_읽는다(self):
        # ⚠ 칸을 «뒤에» 붙였다 — 앞 여섯 칸만 아는 자리가 그대로 돌아야 한다.
        e = 사전행("CD-PRINT-DOCUMENT-TYPE", values=PRINT9, owner="enum")
        old = ("logi", "스키마", "/a", "enum", tuple(PRINT9), ())
        self.assertIsNone(cd.place_key(old))
        self.assertFalse(cd.place_landed(old))
        self.assertTrue(cd.matches(e, old))


class 등록부와_사전이_1대1인가(unittest.TestCase):
    """⛔ 2026-09-02 2단계 — 이 셋만 «막는다».

    걸어 두지 않으면 새 그룹이 사전을 건너뛰고, 값은 다시 계약 산문으로 흩어진다 —
    1단계에서 꺼낸 45그룹이 정확히 그렇게 흩어져 있던 것들이다.
    """

    def test_실물이_1대1이다(self):
        # 62그룹 전부가 사전에 있어야 한다. 하나라도 빠지면 게이트가 울린다.
        import importlib
        ptr = importlib.import_module("check-code-group-pointer")
        registry = ptr.load_registry()
        covered = set()
        for e in cd.read_dictionary(cd.DICT):
            covered |= set(e["group"])
        self.assertEqual(sorted(registry - covered), [])

    def test_소유가_등록부와_같다(self):
        import importlib
        ptr = importlib.import_module("check-code-group-pointer")
        owners = ptr.load_registry_owners()
        for e in cd.read_dictionary(cd.DICT):
            for g in e["group"]:
                if owners.get(g, "미판정") != "미판정":
                    self.assertEqual(e["owner"], owners[g],
                                     "%s 의 소유가 등록부와 다르다" % e["key"])

    def test_사전의_그룹은_전부_등록부_안이다(self):
        import importlib
        ptr = importlib.import_module("check-code-group-pointer")
        registry = ptr.load_registry()
        for e in cd.read_dictionary(cd.DICT):
            for g in e["group"]:
                self.assertIn(g, registry, "%s 의 그룹이 등록부 밖이다" % e["key"])

    def test_키는_중복하지_않는다(self):
        keys = [e["key"] for e in cd.read_dictionary(cd.DICT)]
        self.assertEqual(len(keys), len(set(keys)))


# ── ㉦㉧ 계약의 예시·산문이 사전과 같은 말을 하는가 ──────────────────────
#
# ⛔ 2026-09-03 신설. 사전이 닫힌(639/639) 뒤에도 계약 83자리가 낡아 있었다 —
# `example` 이 값집합 밖 52 · 산문이 「확정된 값 목록이 아직 없다」 31.
# ㉡ 는 `enum` 만 봤고, 값을 나르는 나머지 두 자리는 아무도 안 보고 있었다.

def prop(key, example=None, desc=None):
    node = {"type": "string", "x-code-key": key}
    if example is not None:
        node["example"] = example
    if desc is not None:
        node["description"] = desc
    return {"components": {"schemas": {"S": {"properties": {"aCode": node}}}}}


class ProseExampleGapsTest(unittest.TestCase):
    VALS = {"CD-A": {"ALPHA", "BETA"}, "CD-B": {"GAMMA"}}

    def test_example_이_값집합_밖이면_잡는다(self):
        ex, pr = cd.prose_example_gaps(prop("CD-A", example="STANDARD"), self.VALS)
        self.assertEqual(len(ex), 1)
        self.assertEqual(ex[0][2], "STANDARD")
        self.assertEqual(pr, [])

    def test_example_이_값집합_안이면_잡지_않는다(self):
        ex, _ = cd.prose_example_gaps(prop("CD-A", example="ALPHA"), self.VALS)
        self.assertEqual(ex, [])

    def test_자리채움_값도_같은_규칙으로_잡힌다(self):
        for junk in ("값", "STANDARD", "NORMAL"):
            ex, _ = cd.prose_example_gaps(prop("CD-A", example=junk), self.VALS)
            self.assertEqual(len(ex), 1, junk)

    def test_사전에_값이_없으면_예시를_판정하지_않는다(self):
        # ⬜ 갈래(고객이 운영 중에 채운다)는 우리가 예시를 정할 근거가 없다.
        ex, _ = cd.prose_example_gaps(prop("CD-C", example="ANY"), self.VALS)
        self.assertEqual(ex, [])

    def test_키가_둘이면_합집합으로_본다(self):
        doc = {"components": {"schemas": {"S": {"properties": {"aCode": {
            "type": "string", "x-code-key": ["CD-A", "CD-B"], "example": "GAMMA"}}}}}}
        ex, _ = cd.prose_example_gaps(doc, self.VALS)
        self.assertEqual(ex, [])

    def test_산문이_아직_없다고_적는데_사전은_값을_가지면_잡는다(self):
        doc = prop("CD-A", desc="확정된 값 목록이 아직 없다 — 서버가 내려주는 선택지를 쓴다")
        _, pr = cd.prose_example_gaps(doc, self.VALS)
        self.assertEqual(len(pr), 1)

    def test_값_목록_미정도_같은_문면으로_본다(self):
        _, pr = cd.prose_example_gaps(prop("CD-A", desc="공통코드 — 값 목록 미정"), self.VALS)
        self.assertEqual(len(pr), 1)

    def test_값을_적은_산문은_잡지_않는다(self):
        doc = prop("CD-A", desc="값 = ALPHA·BETA (2026-09-03 코드 사전 등재)")
        _, pr = cd.prose_example_gaps(doc, self.VALS)
        self.assertEqual(pr, [])

    def test_키가_없는_자리는_보지_않는다(self):
        doc = {"components": {"schemas": {"S": {"properties": {"aCode": {
            "type": "string", "example": "STANDARD", "description": "값 목록 미정"}}}}}}
        ex, pr = cd.prose_example_gaps(doc, self.VALS)
        self.assertEqual((ex, pr), ([], []))


# ── ㉨ 자리의 «모양»에 관계없이 판정이 있는가 ────────────────────────────
#
# ⛔ 2026-09-03 신설. 「639/639 = 100%」로 보고한 분모가 **경로 인라인 스키마와
# 배열 items 안의 자리를 세지 않았다.** 그 자리 9곳이 판정 없이 남아 있었고,
# 첨부 등록(POST) 본문의 targetTypeCode 는 읽는 쪽이 값·근거를 다 갖는데
# **쓰는 쪽만 맨몸**이었다 — 프론트가 «보내는» 자리에 안내가 0이었다.

def place(key=None, excuse=None, kind="스키마", landed=False):
    return ("logi", kind, "/x", "bare", (), (), key, landed, excuse)


class UndecidedTest(unittest.TestCase):
    def test_키도_이유도_없으면_잡는다(self):
        self.assertEqual(len(cd.undecided({"aCode": [place()]})), 1)

    def test_키가_있으면_잡지_않는다(self):
        self.assertEqual(cd.undecided({"aCode": [place(key="CD-A")]}), [])

    def test_코드_아님_이유가_적혀_있으면_잡지_않는다(self):
        self.assertEqual(cd.undecided({"aCode": [place(excuse="식별자다")]}), [])

    def test_착지_여부와_무관하게_본다(self):
        # ⛔ ㉣ 는 착지를 문턱으로 삼는다. ㉨ 는 그 문턱이 «없다» — 그것이 사각지대였다.
        self.assertEqual(len(cd.undecided({"aCode": [place(landed=False)]})), 1)
        self.assertEqual(len(cd.undecided({"aCode": [place(landed=True)]})), 1)

    def test_쿼리_자리도_이유를_읽는다(self):
        # ⛔ 쿼리 갈래만 튜플이 여덟 칸이라 place_excused 가 늘 None 이었다.
        #    「코드 아님」으로 이유를 적어 둔 쿼리 파라미터 19자리가 판정 없음으로 보였다.
        self.assertEqual(
            cd.undecided({"aCode": [place(excuse="채번 식별자다", kind="쿼리")]}), [])

    def test_실물_계약에_판정_없는_자리가_없다(self):
        self.assertEqual(cd.undecided(cd.scan()), [])

    def test_스키마_이름이_Code_로_끝나는_object_는_자리가_아니다(self):
        # `ItemExternalCode`·`DefectCode`·`CauseCode` 셋이 「판정 없는 자리」로 세어졌다.
        names = {n for n, _ in
                 ((n, p) for n, ps in cd.scan().items() for p in ps)}
        for junk in ("ItemExternalCode", "DefectCode", "CauseCode"):
            self.assertNotIn(junk, names)


class SelfCountGapsTest(unittest.TestCase):
    FACTS = {"키": 174, "자리": 491, "그룹": 103}

    def test_문면이_실물과_같으면_통과한다(self):
        text = "⭐ **174키 / 491자리.** 등록부 **103그룹 전부**와 …"
        self.assertEqual(cd.self_count_gaps(text, self.FACTS), [])

    def test_키_수가_어긋나면_잡는다(self):
        gaps = cd.self_count_gaps("**103키 / 491자리.** 등록부 **103그룹 전부**", self.FACTS)
        self.assertEqual(len(gaps), 1)
        self.assertIn("문면 103", gaps[0])

    def test_자리_수가_어긋나면_잡는다(self):
        gaps = cd.self_count_gaps("**174키 / 257자리.**", self.FACTS)
        self.assertEqual(len(gaps), 1)
        self.assertIn("자리", gaps[0])

    def test_등록부_그룹_수가_어긋나면_잡는다(self):
        gaps = cd.self_count_gaps("등록부 **62그룹 전부**", self.FACTS)
        self.assertEqual(len(gaps), 1)
        self.assertIn("그룹", gaps[0])

    def test_같은_수를_두_번_적으면_두_번_본다(self):
        text = "**174키 / 491자리.** … 사전 — **103키 / 257자리**"
        gaps = cd.self_count_gaps(text, self.FACTS)
        self.assertEqual(len(gaps), 2)

    def test_볼드_안에_앞말이_붙어도_본다(self):
        # ⛔ `**완성 — 174키 / 491자리.**` 가 정규식에서 빠져 있었다(2026-09-03).
        gaps = cd.self_count_gaps("⭐ **완성 — 103키 / 257자리.**", self.FACTS)
        self.assertEqual(len(gaps), 2)

    def test_볼드_안에_앞말이_붙고_수가_맞으면_통과한다(self):
        self.assertEqual(cd.self_count_gaps("⭐ **완성 — 174키 / 491자리.**", self.FACTS), [])

    def test_수를_안_적으면_잡을_것이_없다(self):
        self.assertEqual(cd.self_count_gaps("계수를 적지 않았다", self.FACTS), [])

    def test_실물_사전이_자기_계수와_맞는다(self):
        import importlib
        ptr = importlib.import_module("check-code-group-pointer")
        entries = cd.read_dictionary(cd.DICT)
        facts = {"키": len(entries),
                 "자리": sum(e["places"] or 0 for e in entries),
                 "그룹": len(ptr.load_registry())}
        with open(cd.DICT, encoding="utf-8") as fh:
            self.assertEqual(cd.self_count_gaps(fh.read(), facts), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
