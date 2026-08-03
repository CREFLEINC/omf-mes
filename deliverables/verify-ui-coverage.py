#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# UI 요구 추출 — 화면 상세 스펙에서 액션을 전건 뽑는다.
#
# 목적은 커버리지 검산이다. 화면이 요구하는 액션 하나하나가 요구서의
# 화면→API 매핑표에서 다뤄졌는지 대조하기 위한 기준 목록을 만든다.
#
# 물리 모델과 OpenAPI 를 대조하지 않는다 — 그것은 데이터모델 담당 소관이다.
# 표준 라이브러리만 쓴다(저장소 관행).
import io, os, re, sys

EXPANSION = "uiux/2026-08-03-화면상세스펙-확대1차"
PILOT = "uiux/2026-07-31-화면상세스펙-파일럿"

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
]

_SCREEN_ID = re.compile(r"(W-(?:CO|[0-9]{2})-[0-9]{2})")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_STRIKE = re.compile(r"~~(.+?)~~")


def _strip_md(text):
    # 굵게·취소선·코드 표기를 벗기고 앞뒤 공백을 없앤다.
    text = _BOLD.sub(r"\1", text)
    text = _STRIKE.sub(r"\1", text)
    return text.replace("`", "").strip()


def extract_actions(md_path):
    # 한 화면 스펙의 §5-1 액션 표를 [{screen, action, condition, note}] 로.
    m = _SCREEN_ID.search(os.path.basename(md_path))
    screen = m.group(1) if m else os.path.basename(md_path)
    text = io.open(md_path, encoding="utf-8").read()

    start = text.find("### §5-1")
    if start == -1:
        return []
    end = text.find("###", start + 4)
    block = text[start:end] if end != -1 else text[start:]

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


def extract_all(base_dir):
    # 대상 화면 10개의 액션을 모은다. base_dir 은 deliverables/ 경로.
    root = os.path.normpath(os.path.join(base_dir, ".."))
    out = []
    for folder, sid in SCREENS:
        d = os.path.join(root, folder)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.startswith(sid) and fn.endswith(".md"):
                out.extend(extract_actions(os.path.join(d, fn)))
                break
    return out


def render(rows):
    # 요구 목록을 markdown 으로.
    lines = [
        "# UI 요구 목록 — 화면이 API 에 요구하는 것",
        "",
        "> 생성물이다. `python3 verify-ui-coverage.py` 로 다시 만든다.",
        "> 이 목록의 모든 행이 `06-API-요구서.md` §3 매핑표에서 다뤄져야 한다.",
        "> 엔드포인트가 없는 액션은 「없음 + 이유」로 명시한다 — 빈칸은 누락이다.",
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
    here = os.path.dirname(os.path.abspath(__file__))
    rows = extract_all(here)
    dst = os.path.join(here, "openapi", "ui-요구목록.md")
    d = os.path.dirname(dst)
    if not os.path.isdir(d):
        os.makedirs(d)
    with io.open(dst, "w", encoding="utf-8") as f:
        f.write(render(rows))
    print("생성: %s" % dst)
    print("화면 %d · 액션 %d" % (len({r["screen"] for r in rows}), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
