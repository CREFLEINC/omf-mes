#!/usr/bin/env python3
"""보고 문서에 **뜻을 안 밝힌 줄임말·기호**가 있는가.

왜 필요한가
-----------
2026-08-13 사용자 확정 — 「보고 내용 작성 시 **키워드를 사용하지 않는다.**
키워드 대신 명시적 단어로 작성하고, 키워드를 쓸 필요가 있으면 **명시적 단어도
함께** 작성한다.」

실제로 어겼다. 「다형」을 여러 차례 쓰고도 정의한 적이 없어 사용자가
「다형이 무엇인가」를 물었다. 화면 번호·조항 번호도 뜻 없이 나열했다.

    ⛔  W-01-06 에 A-10 을 적용하면 E-4 가 풀린다
    ✅  자재 폐기 화면(W-01-06)에 다형 참조 대응표 조항(A-10)을 적용하면
        폐기 계정 회신 대기(E-4)가 풀린다

무엇을 보나
-----------
줄임말·기호를 찾고, **같은 줄에 뜻이 함께 적혀 있는가**를 본다.

  ① 화면 번호      W-01-06 · P-02-13 · M-04-01
  ② 조항 번호      A-10 · G-2 · B-8 · L-3
  ③ 회신 번호      E-3 · E-4
  ④ 전문 용어      다형 · 멱등 · 낙관적 잠금 · 구간 형 · 파생 · 다국어
  ⑤ 업무 약어      IQC · PQC · OQC · WO · PO · PM · BOM

**뜻이 함께 있다**로 인정하는 것 — 같은 줄에 한글 설명이 있고, 그것이 기호
자체를 반복한 것이 아닐 때. 표의 「설명 열」과 괄호 병기가 여기 해당한다.

⚠ 이 검사기가 못 보는 것
------------------------
**대화로 하는 보고는 못 본다.** 파일만 본다. 대화 쪽은 `uiux/CLAUDE.md`
규칙 4 가 맡는다.

그리고 **뜻이 「맞는가」는 못 본다.** 옆에 한글이 있으면 통과한다.

쓰기
----
    python3 check-report-language.py <파일...>
    python3 check-report-language.py --track uiux/2026-08-13-…/   # 폴더 전체

⛔ 위반이 있으면 종료 코드 1. --warn 을 주면 종료 코드 0(보고만).
"""
from __future__ import annotations

import glob
import io
import os
import re
import sys

# ── 무엇을 줄임말로 보는가 ────────────────────────────────────────────
SCREEN = re.compile(r"\b([WPM]-[A-Z0-9]{2}-\d{2})\b")
# ⚠ E 를 뺀다 — E-3·E-4 는 회신 번호다. 안 빼면 한 기호를 두 번 센다.
CLAUSE = re.compile(r"(?<![A-Za-z0-9])([A-DF-L]-\d{1,2})(?![0-9-])")
REPLY = re.compile(r"(?<![A-Za-z0-9])(E-\d{1,2})(?![0-9-])")
ROUND = re.compile(r"(확대\s*\d+\s*차)")

# 뜻을 밝혀야 하는 전문 용어 — 처음 쓸 때 풀어야 한다
TERMS = {
    "다형": "한 칸이 여러 표를 가리킨다",
    "멱등": "여러 번 불러도 결과가 같다",
    "낙관적 잠금": "저장할 때 버전을 대조해 충돌을 잡는다",
    "구간 형": "「진행 중」을 끝 시각의 부재로 판정한다",
    "파생": "저장하지 않고 계산해 낸다",
    "다형 참조": "한 칸이 여러 표를 가리킨다",
}
ABBR = {
    "IQC": "수입 검사", "PQC": "공정 검사", "OQC": "출하 검사",
    "BOM": "자재 명세", "PGI": "출고 전기",
}

# 이 줄들은 검사하지 않는다 — 설명 대상이 아니다
SKIP_LINE = re.compile(
    r"^\s*(?:\||```|>\s*작성일|#{1,6}\s|[-*]\s*`?[a-z0-9_./-]+\.(?:md|py|json|sql)`?\s*$)"
)
CODE_FENCE = re.compile(r"^\s*```")
# 근거·경로만 적는 줄 — 번호 나열이 정상이다
REF_LINE = re.compile(r"(근거|참조|관련|출처|파일|경로)\s*[:：]|^\s*[-*]\s*`")

HANGUL = re.compile(r"[가-힣]{2,}")


def explained(line: str, token: str) -> bool:
    """이 줄에서 기호의 뜻이 함께 밝혀졌는가.

    두 모양을 다 인정한다 — 앞에 붙이는 것과 뒤 괄호에 다는 것.

        자재 폐기 화면(W-01-06)          ← 앞
        `W-06-06`(공통코드·조직 마스터)   ← 뒤 괄호

    ⚠ 뒤만 볼 때는 **바로 뒤 괄호**로 좁힌다. 줄 어딘가에 한글이 있다고
    인정하면 「W-01-06 과 W-04-10 을 고쳤다」 같은 나열이 통과한다.
    """
    head, _, tail = line.partition(token)
    if HANGUL.search(head):
        return True
    m = re.match(r"[`\s]*[(（]([^)）]{2,})[)）]", tail)
    return bool(m and HANGUL.search(m.group(1)))


def scan_text(text: str) -> list[tuple[int, str, str]]:
    """(줄번호, 종류, 기호) 목록을 낸다."""
    out: list[tuple[int, str, str]] = []
    seen_terms: set[str] = set()
    in_fence = False

    for no, line in enumerate(text.split("\n"), 1):
        if CODE_FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or SKIP_LINE.match(line) or REF_LINE.search(line):
            continue

        for kind, pat in (("화면 번호", SCREEN), ("조항 번호", CLAUSE),
                          ("회신 번호", REPLY), ("차수", ROUND)):
            for tok in dict.fromkeys(m.group(1) for m in pat.finditer(line)):
                # 한 줄에 같은 기호가 여러 번 나와도 한 번만 센다 —
                # 세는 도구가 부풀려 세면 그것을 믿고 규모를 잘못 잡는다.
                if not explained(line, tok):
                    out.append((no, kind, tok))

        for term in TERMS:
            if term in line and term not in seen_terms:
                seen_terms.add(term)
                # 처음 나온 자리에 풀이가 붙었는가 — 괄호나 「—」 뒤 설명
                tail = line.split(term, 1)[1][:60]
                if not re.search(r"[(（—\-:：]", tail):
                    out.append((no, "전문 용어(첫 등장)", term))

        for abbr in ABBR:
            if re.search(rf"\b{abbr}\b", line) and not explained(line, abbr):
                out.append((no, "업무 약어", abbr))
    return out


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    warn_only = "--warn" in sys.argv

    targets: list[str] = []
    if "--track" in sys.argv:
        i = sys.argv.index("--track") + 1
        targets = sorted(glob.glob(os.path.join(sys.argv[i], "*.md")))
        args = [a for a in args if a != sys.argv[i]]
    targets += [a for a in args if a.endswith(".md")]

    if not targets:
        print("쓰기: check-report-language.py <파일.md ...> | --track <폴더>",
              file=sys.stderr)
        return 2

    total = 0
    for path in targets:
        with io.open(path, encoding="utf-8") as f:
            hits = scan_text(f.read())
        if not hits:
            continue
        total += len(hits)
        print(f"\n⛔ {path}")
        for no, kind, token in hits[:20]:
            print(f"   {no:>4}줄  [{kind}] {token}")
        if len(hits) > 20:
            print(f"   … 외 {len(hits)-20}건")

    if not total:
        print(f"✅ 뜻 없이 쓴 줄임말이 없습니다 — {len(targets)}개 문서")
        return 0

    print(
        f"\n⛔ 뜻 없이 쓴 줄임말 {total}건\n"
        "→ 기호 앞에 무엇인지 적는다.\n"
        "   예)  W-01-06 …            →  자재 폐기 화면(W-01-06) …\n"
        "        A-10 을 적용         →  다형 참조 대응표 조항(A-10)을 적용\n"
        "   전문 용어는 처음 쓰는 자리에서 푼다 — 「다형(한 칸이 여러 표를 가리킨다)」"
    )
    return 0 if warn_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
