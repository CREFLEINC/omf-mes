#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# UI 요구 추출 — 화면 상세 스펙에서 액션을 전건 뽑는다.
#
# 목적은 커버리지 검산이다. 화면이 요구하는 액션 하나하나가 요구서의
# 화면→API 매핑표에서 다뤄졌는지 대조하기 위한 기준 목록을 만든다.
#
# 물리 모델과 OpenAPI 를 대조하지 않는다 — 그것은 데이터모델 담당 소관이다.
# 표준 라이브러리만 쓴다(저장소 관행).
#
# 도메인이 일곱이다 — `--domain 01`(자재창고 24장) · `--domain 02`(생산실행 20장) ·
#   `--domain 03`(품질 7장 — ⭐ 도메인 배지 5 + 01·02 이월 2) ·
#   `--domain 04`(제품출하 16장 — ⭐ 도메인 배지 18 − 출력물 계약 2) ·
#   `--domain app`(공통 승인 2장) · `--domain print`(공통 출력물 5장) · 기본(mdm 기준정보).
import io, os, re, sys

EXPANSION = "uiux/2026-08-03-화면상세스펙-확대1차"
PILOT = "uiux/2026-07-31-화면상세스펙-파일럿"
E2 = "uiux/2026-08-04-화면상세스펙-확대2차"
E4 = "uiux/2026-08-05-화면상세스펙-확대4차"
E5 = "uiux/2026-08-05-화면상세스펙-확대5차"
E7 = "uiux/2026-08-07-화면상세스펙-확대7차"
E3_ = "uiux/2026-08-04-화면상세스펙-확대3차"
E8 = "uiux/2026-08-07-화면상세스펙-확대8차"
E9 = "uiux/2026-08-07-화면상세스펙-확대9차"
E15 = "uiux/2026-08-11-화면상세스펙-확대15차"
E6 = "uiux/2026-08-06-화면상세스펙-확대6차"
E10 = "uiux/2026-08-07-화면상세스펙-확대10차"

# 대상 화면 — 확대 1차 13장 − W-06-13(통합 폐지) − W-06-08·09·12(API 정의 불가) + 파일럿 W-06-07
SCREENS = [
    (EXPANSION, "W-CO-02"),
    (EXPANSION, "W-06-01"),
    (EXPANSION, "W-06-02"),
    (EXPANSION, "W-06-03"),
    (EXPANSION, "W-06-04"),
    (EXPANSION, "W-06-05"),
    (EXPANSION, "W-06-06"),
    (EXPANSION, "W-06-10"),
    (EXPANSION, "W-06-11"),
    (PILOT, "W-06-07"),
    (E7, "W-06-14"),   # 적치 규칙 마스터 — 계약이 먼저 쓰였다(mdm-기준정보.json)
]

# 01 자재창고 24장. ⛔ M-01-12(재생재 등록)는 #64 로 동결 · W-01-08 은 결번.
SCREENS_01 = [
    (PILOT, "W-01-01"), (PILOT, "M-01-02"),
    (E2, "W-01-02"), (E2, "W-01-03"), (E2, "W-01-09"), (E2, "W-01-10"), (E2, "W-01-11"),
    (E2, "M-01-01"), (E2, "M-01-06"), (E2, "P-01-01"),
    (E4, "W-01-04"), (E4, "M-01-04"), (E4, "M-01-05"), (E4, "M-01-07"), (E4, "M-01-08"),
    (E4, "M-01-09"), (E4, "M-01-10"), (E4, "M-01-11"), (E4, "P-01-02"),
    (E5, "W-01-05"), (E5, "W-01-06"), (E5, "W-01-07"), (E5, "W-01-12"),
    (E7, "W-01-13"),   # 물류 문서 진행현황·취소 — 계약 개정으로 취소 경로가 생겼다
]

# app 공통(승인) 2장. 결재선 정의와 결재함이 승인 실행 계약을 낳는다.
# ⛔ W-01-13(물류 문서 진행현황·취소)은 여기가 아니다 — 01 계약 개정 소관이다.
SCREENS_APP = [
    (E7, "W-06-15"), (E7, "W-CO-09"),
]

# app 공통(출력물) — ⚠ **이 편은 화면을 소유하지 않는다.** `app.document_issue_log` 는
# 도메인 셋(01·02·04)이 함께 쓰고 규약은 §K 하나라 **계약만 공유**한다.
#
# 그래서 여기 등록하는 것은 **출력이 주 기능이고 도메인 요구서가 아직 없는 화면**뿐이다.
#   ⛔ `P-01-01`·`P-01-02` — 01 요구서가 이미 덮는다(§3-6·§3-15에 「미착지」로 적혀 있다).
#      그 행들을 이 계약 경로로 **갱신**하는 것이지 여기서 다시 세지 않는다.
#   ⛔ `W-04-03`·`P-04-01`·`M-02-01` — 출력이 액션 하나뿐이다. 04·02 요구서가 설 때 그쪽이 센다.
#   ⛔ `W-06-07` — 라벨 **양식 마스터**라 mdm 소관이다.
#
# ⚠ `P-02-05`·`P-02-07`·`P-02-09` 는 확대 3차 서식이라 액션 표가 없다.
#    생성기가 경고로 표시하고, 요구는 §5 본문에서 사람이 읽어 요구서 §3 에 옮긴다.
SCREENS_PRINT = [
    (E3_, "P-02-05"), (E3_, "P-02-07"), (E3_, "P-02-09"),  # 인식표 · 생산LOT 라벨 · 재출력
    (E8, "P-04-02"),                                        # 납품 포장 라벨 출력
    (E9, "P-04-04"),                                        # 재구성 신규 라벨 발행
]

# 02 생산실행 — 계약 대상 **20장**.
#   전체 24장 중 넷을 뺀다:
#     ⛔ P-02-05·P-02-07·P-02-09  출력·인쇄 — app-공통(출력물) 계약이 이미 덮는다(--domain print)
#     ⛔ P-02-13                  PQC 검사 결과 — quality 는 03 트랙 소관
#   ⚠ W-02-09 는 결번이다(생성기 VACATED).
SCREENS_02 = [
    (PILOT, "P-02-04"),
    (E3_, "P-02-03"), (E3_, "P-02-06"), (E3_, "P-02-08"), (E3_, "P-02-10"),
    (E3_, "P-02-11"), (E3_, "P-02-12"), (E3_, "W-02-04"),
    (E4, "M-02-01"), (E4, "M-02-02"),
    (E5, "W-02-01"), (E5, "W-02-02"), (E5, "W-02-03"), (E5, "W-02-05"),
    (E5, "W-02-06"), (E5, "W-02-07"), (E5, "W-02-08"), (E5, "W-02-10"),
    (E15, "P-02-01"), (E15, "P-02-02"),
]

# 04 제품출하 16장. ⭐ 도메인 배지는 18 이지만 계약 대상은 16 이다 —
#   P-04-02·P-04-04 는 출력이 주 기능이라 공통 출력물 계약이 이미 덮었다(--domain print).
#   ⚠ 출력물 요구서가 「04 소관」이라 적고 비워 둔 칸이 셋인데, 실측하니 둘은 01 계약에
#      이미 있었다. 04 가 내는 것은 P-04-02 의 「합격 건 목록」 하나뿐이다(04 계약 1단계 §2-1).
#   ⛔ W-04-09·M-04-02 는 결번이다.
SCREENS_04 = [
    (E8, "W-04-01"), (E8, "W-04-02"), (E8, "W-04-03"), (E8, "W-04-04"), (E8, "W-04-05"),
    (E8, "W-04-08"), (E8, "W-04-11"), (E8, "W-04-12"),
    (E8, "P-04-01"), (E8, "M-04-01"), (E8, "M-04-04"),
    (E9, "W-04-06"), (E9, "W-04-07"), (E9, "W-04-10"),
    (E9, "P-04-03"), (E9, "M-04-03"),
]

# 03 품질 7장. ⭐ 도메인 배지는 5장이지만 계약 대상은 7이다 —
#   01 이 「03 소관」으로 미룬 W-01-01 · 02 가 「03 소관」으로 뺀 P-02-13 이 여기서 풀린다.
#   ⛔ W-03-04·06·07·08 은 결번(흡수·Analytics 이관).
SCREENS_03 = [
    (E6, "W-03-01"), (E6, "W-03-02"), (E6, "W-03-03"), (E6, "W-03-05"),
    (E10, "W-03-09"),
    (PILOT, "W-01-01"),   # 01 이월 — 01 요구서 §6-1
    (E5, "P-02-13"),      # 02 이월 — 02 요구서 머리 「03 소관 1 제외」
]

DOMAINS = {
    "mdm": (SCREENS, "ui-요구목록.md", "06-API-요구서.md"),
    "01": (SCREENS_01, "ui-요구목록-01자재창고.md", "06-API-요구서-01자재창고.md"),
    "app": (SCREENS_APP, "ui-요구목록-app공통승인.md", "06-API-요구서-app공통승인.md"),
    "02": (SCREENS_02, "ui-요구목록-02생산실행.md", "06-API-요구서-02생산실행.md"),
    "print": (SCREENS_PRINT, "ui-요구목록-app공통출력물.md", "06-API-요구서-app공통출력물.md"),
    "03": (SCREENS_03, "ui-요구목록-03품질.md", "06-API-요구서-03품질.md"),
    "04": (SCREENS_04, "ui-요구목록-04제품출하.md", "06-API-요구서-04제품출하.md"),
}

_SCREEN_ID = re.compile(r"([WMP]-(?:CO|[0-9]{2})-[0-9]{2})")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_STRIKE = re.compile(r"~~(.+?)~~")


def _strip_md(text):
    # 굵게·취소선·코드 표기를 벗기고 앞뒤 공백을 없앤다.
    text = _BOLD.sub(r"\1", text)
    text = _STRIKE.sub(r"\1", text)
    return text.replace("`", "").strip()


_ACTION_HEADING = re.compile(r"^### §5-\d+\..*액션.*$", re.M)
_NEXT_HEADING = re.compile(r"^#{2,3} ", re.M)


def find_action_block(text):
    # 액션 표가 든 소절을 돌려준다. 없으면 None.
    #
    # 기준정보 10장은 전부 `### §5-1. 액션` 이지만 01 자재창고는 소절 번호가
    # 화면마다 다르다(§5-2 · §5-5 · §5-6 · §5-7 · §5-8). 번호를 고정하면 조용히
    # 0건이 되어 커버리지가 부풀려진다 — 제목으로 찾는다.
    m = _ACTION_HEADING.search(text)
    if m is None:
        return None
    # 소절의 끝은 「다음 ### 」이 아니라 「다음 ## 또는 ### 」이다.
    # 액션 소절이 §5 의 마지막 소절이면 다음 제목이 `## §6` 이라 ### 만 찾으면
    # §6·§7·§8 의 표까지 삼킨다(01 자재창고에서 액션이 414건으로 부풀었다).
    nxt = _NEXT_HEADING.search(text, m.end())
    return text[m.start():nxt.start()] if nxt else text[m.start():]


def extract_actions(md_path):
    # 한 화면 스펙의 액션 표를 [{screen, action, condition, note}] 로.
    m = _SCREEN_ID.search(os.path.basename(md_path))
    screen = m.group(1) if m else os.path.basename(md_path)
    with io.open(md_path, encoding="utf-8") as f:
        text = f.read()

    block = find_action_block(text)
    if block is None:
        return []

    # §5-1 표의 열 구성이 화면마다 다르다 — 대부분 「액션|위치|활성 조건|비고」
    # 4열이지만 W-06-10 은 「액션|활성 조건|비고」 3열(위치 열이 없다). 열 위치를
    # 고정 인덱스로 가정하면 W-06-10 에서 활성 조건과 비고가 뒤섞인다. 그래서
    # 표의 첫 행(헤더)에서 열 이름으로 「활성 조건」·「비고」 위치를 찾는다.
    header = None
    cond_idx = None
    note_idx = None
    rows = []
    for line in block.split("\n"):
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue

        if header is None:
            header = [_strip_md(c) for c in cells]
            if "활성 조건" in header:
                cond_idx = header.index("활성 조건")
            if "비고" in header:
                note_idx = header.index("비고")
            continue

        if cells[0].startswith("---"):
            continue  # 구분선 행

        first = _strip_md(cells[0])
        if not first:
            continue
        rows.append({
            "screen": screen,
            "action": first,
            "condition": (_strip_md(cells[cond_idx])
                          if cond_idx is not None and len(cells) > cond_idx else ""),
            "note": (_strip_md(cells[note_idx])
                     if note_idx is not None and len(cells) > note_idx else ""),
        })
    return rows


def screen_path(root, folder, sid):
    # 화면 ID 로 시작하는 스펙 파일 경로. 없으면 None.
    d = os.path.join(root, folder)
    if not os.path.isdir(d):
        return None
    for fn in sorted(os.listdir(d)):
        if fn.startswith(sid) and fn.endswith(".md"):
            return os.path.join(d, fn)
    return None


def extract_all(base_dir, screens=None):
    # 대상 화면의 액션을 모은다. base_dir 은 deliverables/ 경로.
    root = os.path.normpath(os.path.join(base_dir, ".."))
    out = []
    for folder, sid in (screens or SCREENS):
        path = screen_path(root, folder, sid)
        if path:
            out.extend(extract_actions(path))
    return out


def screens_without_action_table(base_dir, screens=None):
    # 스펙은 있는데 액션 표가 없는 화면. 조용히 빠지면 커버리지가 부풀려진다.
    root = os.path.normpath(os.path.join(base_dir, ".."))
    out = []
    for folder, sid in (screens or SCREENS):
        path = screen_path(root, folder, sid)
        if not path:
            continue
        with io.open(path, encoding="utf-8") as f:
            if find_action_block(f.read()) is None:
                out.append(sid)
    return out


def render(rows, domain="mdm", no_table=()):
    # 요구 목록을 markdown 으로.
    _, _, doc = DOMAINS[domain]
    arg = "" if domain == "mdm" else " --domain %s" % domain
    lines = [
        "# UI 요구 목록 — 화면이 API 에 요구하는 것",
        "",
        "> 생성물이다. `python3 verify-ui-coverage.py%s` 로 다시 만든다." % arg,
        "> 이 목록의 모든 행이 `%s` §3 매핑표에서 다뤄져야 한다." % doc,
        "> 엔드포인트가 없는 액션은 「없음 + 이유」로 명시한다 — 빈칸은 누락이다.",
        "",
    ]
    if no_table:
        lines += [
            "⚠ **액션 표가 없는 화면 %d장** — %s."
            % (len(no_table), " · ".join("`%s`" % s for s in no_table)),
            "이 화면들의 요구는 §5 본문에서 사람이 읽어 §3 에 옮긴다. **목록에 없다고 없는 것이 아니다.**",
            "",
        ]
    cur = None
    for r in rows:
        if r["screen"] != cur:
            cur = r["screen"]
            lines += ["", "## " + cur, "", "| 액션 | 활성 조건 |", "| --- | --- |"]
        lines.append("| %s | %s |" % (r["action"], r["condition"]))
    lines += ["", "---", "",
              "**합계: 화면 %d · 액션 %d**"
              % (len({r["screen"] for r in rows}), len(rows)), ""]
    return "\n".join(lines)


def main():
    domain = "mdm"
    if "--domain" in sys.argv:
        domain = sys.argv[sys.argv.index("--domain") + 1]
    if domain not in DOMAINS:
        print("모르는 도메인: %s (%s 중 하나)" % (domain, " · ".join(DOMAINS)))
        return 1

    here = os.path.dirname(os.path.abspath(__file__))
    screens, filename, _ = DOMAINS[domain]
    rows = extract_all(here, screens)
    no_table = screens_without_action_table(here, screens)

    dst = os.path.join(here, "openapi", filename)
    d = os.path.dirname(dst)
    if not os.path.isdir(d):
        os.makedirs(d)
    with io.open(dst, "w", encoding="utf-8") as f:
        f.write(render(rows, domain, no_table))
    print("생성: %s" % dst)
    print("화면 %d · 액션 %d" % (len({r["screen"] for r in rows}), len(rows)))
    if no_table:
        print("⚠ 액션 표 없는 화면 %d: %s" % (len(no_table), " ".join(no_table)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
