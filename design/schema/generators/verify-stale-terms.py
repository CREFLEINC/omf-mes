#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""표기를 바꾼 뒤 «옛 이름»이 아직 남아 있나 — 기준 시점과 대조한다.

왜 필요한가
-----------
2026-08-26 단말 형태가 「부착형 스캐너 세트」에서 「스캐너 일체형 PDA」로 바뀌었다.
문서 11장을 고쳤고 리뷰를 세 번 돌았는데 **옛 이름 3건이 살아남았다**(`omf-mes#244`
→ `omf-mes#250`). 표기 변경은 「같은 뜻의 다른 낱말」이라 문법·링크·경로 검사기가
전부 초록이다 — **이 종류를 보는 검사기가 저장소에 하나도 없었다.**

    옛 이름을 지운 줄이 있다  →  그 이름이 다른 데 «그대로» 남아 있나?

무엇을 보나
-----------
기준 ref 의 트리와 «지금 작업 트리»를 파일마다 대조한다.

    ① 줄 단위 diff — 지워진 줄(base 쪽) · 새로 쓴 줄(head 쪽)
    ② ⛔ 양쪽 «모두»에서 취소선(`~~…~~`)과 정합주(`«(정합주: …)»`) 스팬을 걷어낸다
    ③ 구(句)를 뽑는다 — 토큰 2~5개 · 조사·어미로 끝나는 조각은 버린다
    ④ gone = (지워진 줄의 구) − (새로 쓴 줄의 구)
    ⑤ 작업 트리 전체를 훑어 gone 의 구가 아직 있는 줄을 낸다

⭐ ②의 「추가줄에서도 걷어낸다」가 이 검사기의 핵심이다. 안 하면 옛 이름이 **추가줄의
취소선 안에서 되살아나** 삭제-전용 집합에서 탈락한다 — `03-HW구성안.md` 회귀가 정확히
그 형태였다(프로토타입 실측: 안 걷으면 2/3 · 걷으면 3/3).

⭐ ⑤의 대조는 **비대칭**이다 — 1단계는 구 단위, 2단계는 «공백 제거 부분문자열»이다.
구 단위 완전일치로 하면 잔존 표기 「스캐너 연결 상태」가 후보 「스캐너 연결」과 안 맞아
`M-01-02:157` 을 놓친다.

보고하지 않는 줄
----------------
    a. `«(정합주:` 가 있는 줄        — 그 자리에 대해 현재 상태를 이미 밝혔다
    b. 그 구가 취소선 안에만 있는 줄 — 이력 보존 표기다
    c. 최근접 상위 제목에 「이력」·「변경 이력」·「상세 이력」·「회고」가 있는 절
    d. `«(구표기 보존)»` 가 붙은 줄  — 회고·반박 서술이라 옛 이름을 인용해야 뜻이 통한다
    e. `design/raw/` — 시점 고착 자료다(`.claude/hooks/protect_readonly.py` 가 쓰기를 막는다)

⚠ c 를 「제목 «전체» 일치」로 걸지 않은 이유 — 형제 검사기
`check-dead-path-citations.py:80` 은 `^#{1,6}\\s*변경 이력\\s*$` 로 전체 일치를 건다.
여기서는 그 방식이 못 잡는다: `### 상세 이력 (v3.0~v4.4, 행 분리 대기)` 처럼 제목에
부기가 붙는 실례가 있다. 대신 **낱말을 넷으로 좁혀** 오탐을 막는다.

⚠ 이 검사기가 못 보는 것
------------------------
- **바꾼 것이 «옳은지»는 안 본다.** 「지운 이름이 남아 있다」까지만 말한다.
- **한 번도 지운 적 없는 옛 이름은 못 본다** — 기준 ref 와의 «차이»에서만 후보를 뽑는다.
  기준을 너무 가깝게 잡으면(예: `HEAD`) 아무것도 안 나온다.
- **문서 밖은 안 본다** — `.md` 만 본다. `.html` 배포본에 남은 옛 표기는
  `verify-generated-fresh.py --kind html` 이 「원본과 갈렸다」로 잡는다.
- **6토큰 이상의 긴 조각은 후보로 안 쓴다** — 잡음이 상위를 덮으면 사람이 검사기를 끈다.

쓰기
----
    python3 design/schema/generators/verify-stale-terms.py <기준 ref>
    python3 design/schema/generators/verify-stale-terms.py $(git merge-base origin/main HEAD)

⭐ 기준 ref 를 «반드시» 준다. 생략하면 `HEAD` 라 커밋 직후에는 언제나 0건이다
(`check-enum-narrowing.py` 와 같은 함정). 발견이 있으면 종료 코드 1.

⚠ **기준을 «표기 폐기 회차» 직전에 둔다** — 실측 2026-08-29, 대규모 정합 브랜치의
`git merge-base origin/main HEAD` 를 기준으로 주면 **572건**이 나온다(대조 파일 161 ·
사라진 구 199). 회차 하나가 아니라 수천 줄을 손본 구간 전체를 기준으로 잡으면 「표기를
바꾼 것」이 아닌 조각까지 후보가 되고, 그 잡음이 진짜 잔재를 덮는다.
"""
from __future__ import annotations

import difflib
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))

# 대상 — 정본 문서 두 층. design/raw/ 는 시점 고착 자료라 제외한다.
TARGET_DIRS = (os.path.join("design", "wiki"), os.path.join("design", "schema"))
RAW_DIR = os.path.join("design", "raw") + os.sep

STRIKE = re.compile(r"~~[^~]*~~")
NOTE_SPAN = re.compile(r"«\(정합주:.*?\)»", re.S)
NOTE_MARK = "«(정합주:"
KEEP_MARK = "«(구표기 보존)»"          # 신설 억제 마커 — design/schema/00-authoring-rules.md

# 구를 자르는 자리 — 구두점·표 구분자·화살표, 그리고 2칸 이상 공백.
SPLIT = re.compile(r"[|·,;()\[\]{}「」『』“”\"'`*→←⇒=—–\-/:>~#!?.]+|\s{2,}")
TOKEN = re.compile(r"[가-힣]+|[A-Za-z][A-Za-z0-9+]*")
# 조사·어미로 끝나는 조각은 낱말이 아니라 문장 부스러기다(「확정 시」·「지금은」·「표시만」).
TAIL = re.compile(r"(은|는|이|가|을|를|의|에|로|으로|와|과|도|만|다|한다|된다|하고"
                  r"|에서|이다|였다|맞다|시)$")
HEADING = re.compile(r"^#{1,6}\s+(.*)$")
HISTORY_WORDS = ("이력", "변경 이력", "상세 이력", "회고")

MIN_TOKENS, MAX_TOKENS = 2, 5


def strip_spans(line: str) -> str:
    """⛔ 취소선·정합주 스팬을 걷어낸다 — 삭제줄·추가줄 «양쪽»에 적용한다."""
    return STRIKE.sub(" ", NOTE_SPAN.sub(" ", line))


def phrases(line: str) -> set[str]:
    """한 줄에서 후보 구를 뽑는다 — 토큰 2~5개 · 조사·어미로 끝나면 버린다."""
    out: set[str] = set()
    for fragment in SPLIT.split(strip_spans(line)):
        tokens = TOKEN.findall(fragment)
        if not MIN_TOKENS <= len(tokens) <= MAX_TOKENS:
            continue
        if TAIL.search(tokens[-1]):
            continue
        out.add(" ".join(tokens))
        if len(tokens) >= 3:
            out.add(" ".join(tokens[-2:]))     # 뒤 2토큰 부분구
    return out


def targets() -> list[str]:
    """검사 대상 .md 의 저장소 상대 경로 — design/raw/ 는 뺀다."""
    found: list[str] = []
    for base in TARGET_DIRS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, base)):
            dirnames[:] = [d for d in dirnames if d != ".git"]
            for filename in sorted(filenames):
                if not filename.endswith(".md"):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, filename), ROOT)
                if rel.startswith(RAW_DIR):
                    continue
                found.append(rel)
    return sorted(found)


def at_ref(ref: str, rel: str) -> str | None:
    """기준 ref 시점의 파일 내용 — 그때 없던 파일이면 None."""
    run = subprocess.run(["git", "show", "%s:%s" % (ref, rel)],
                         capture_output=True, text=True, cwd=ROOT)
    return run.stdout if run.returncode == 0 else None


def gone_phrases(ref: str) -> tuple[set[str], int]:
    """(사라진 구, 대조한 파일 수) — 삭제줄에만 있고 추가줄에는 없는 구."""
    deleted: set[str] = set()
    added: set[str] = set()
    compared = 0
    for rel in targets():
        old = at_ref(ref, rel)
        if old is None:
            continue                       # 기준 시점에 없던 파일 — 지운 것이 없다
        with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            new = fh.read()
        if old == new:
            continue
        compared += 1
        a, b = old.splitlines(), new.splitlines()
        matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag in ("replace", "delete"):
                for line in a[i1:i2]:
                    deleted |= phrases(line)
            if tag in ("replace", "insert"):
                for line in b[j1:j2]:
                    added |= phrases(line)
    return deleted - added, compared


def buckets(gone: set[str]) -> dict[str, list[tuple[str, str]]]:
    """앞 두 글자로 묶는다 — 54,000줄을 구 하나하나로 훑으면 느리다."""
    index: dict[str, list[tuple[str, str]]] = {}
    for phrase in gone:
        flat = phrase.replace(" ", "")
        if len(flat) < 2:
            continue
        index.setdefault(flat[:2], []).append((flat, phrase))
    return index


def in_history_section(heading: str | None) -> bool:
    return bool(heading) and any(word in heading for word in HISTORY_WORDS)


def scan(gone: set[str]) -> list[tuple[str, int, str]]:
    index = buckets(gone)
    findings: list[tuple[str, int, str]] = []
    for rel in targets():
        heading: str | None = None
        with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            for number, line in enumerate(fh, 1):
                match = HEADING.match(line)
                if match:
                    heading = match.group(1)
                    continue
                if NOTE_MARK in line or KEEP_MARK in line:
                    continue               # a · d
                if in_history_section(heading):
                    continue               # c
                flat = "".join(strip_spans(line).split())   # b — 취소선 밖만 남는다
                hit: set[str] = set()
                for position in range(len(flat) - 1):
                    for candidate, phrase in index.get(flat[position:position + 2], ()):
                        if flat.startswith(candidate, position):
                            hit.add(phrase)
                for phrase in sorted(hit):
                    findings.append((rel, number, phrase))
    return findings


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
    gone, compared = gone_phrases(base)
    findings = scan(gone)

    if not findings:
        print("✅ 폐기한 옛 표기가 남아 있는 자리가 없습니다 — 기준 %s"
              " (대조한 파일 %d · 사라진 구 %d)" % (base, compared, len(gone)))
        return 0

    print("⚠ 폐기한 옛 표기가 아직 남아 있는 자리 %d건 — 기준 %s"
          " (대조한 파일 %d · 사라진 구 %d)\n"
          % (len(findings), base, compared, len(gone)))
    for rel, number, phrase in findings:
        print("  %s:%d: %s" % (rel, number, phrase))
    print("\n⛔ 고칠 것이 아니면 표시를 답니다 — 회고·반박 서술이라 옛 이름을 인용해야"
          " 뜻이 통하면 «(구표기 보존)», 현재 상태를 밝히려면 «(정합주: …)».\n"
          "   규약: design/schema/00-authoring-rules.md")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
