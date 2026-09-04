#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""설계 진도 대장 — 우리 설계에서 아직 안 정해진 것을 한자리에 모은다.

왜 필요한가 — ⚠ 2026-09-03 개정으로 «누구를 위한 것인가»가 바뀌었다
--------------------------------------------------------------------
옛 이유는 **개발팀을 향해** 있었다 — 「인도물에 미결의 자리가 없으면 개발이
「다 정해졌다」로 읽고 만들다 멈춘다」.

⛔ **그 이유는 더 이상 성립하지 않는다.** 업무 방식 개정(2026-09-03)으로 설계팀은
개발팀의 업무에 관여하지 않고, 개발팀은 **설계 자료를 직접 열람한다.** 무엇이
미결인지는 화면 스펙 §8 이 그 자리에서 이미 말한다.

⭐ **지금 이 대장은 «설계팀 자신»을 위한 것이다** — 우리 설계에서 아직 안 정해진
것이 화면 스펙 백 몇 장에 흩어져 있어, 모아 두지 않으면 **우리가 우리 진행을 놓친다.**
⛔ 여기 수를 «박지» 않는다 — 본문 수치는 미결 대장 요약을 그때그때 읽어 쓴다.
⭐ 동시에 반대쪽도 말한다 — 살아 있는 미결이 수백 행이어도 **차단 등급이 0** 이면
「설계 골격은 서 있다」가 사실이다. 그 둘을 함께 보이지 않으면 숫자만 보고
겁먹거나, 숫자를 감추고 다 됐다고 말하게 된다.

⚠ **「인계」라는 낱말이 더는 안 맞는다** — 개발팀에 넘겨주는 문서가 아니라 우리
   진도표다. 폴더 이름(`design/wiki/progress/`)과 파일 이름 변경은 이번 범위 밖이라
   **적어만 둔다.**

⛔ 복사하지 않는다 — «합류» 시킨다
----------------------------------
정본이 이미 각자 답을 낸다. 이 대장은 **그것들을 돌려 결과를 잇는다.**

    collect-open-items.py        화면 스펙 §8 미결
    code-dictionary.md           코드 값 판정(⭐ 정본 — 아래 §2 참조)
    count-undecided-codes.py     `enum` 이 없는 `*Code` 이름(기계적 목록)
    build-screen-progress.py     화면 축의 구멍(스펙·요구서)

⭐ §2 는 «코드 사전»이 정본이다(2026-09-03)
-------------------------------------------
전에는 `count-undecided-codes.py` 의 「`enum` 이 없으면 미확정」이라는 **기계적
기준**을 그대로 「확정되지 않은 업무 코드」로 실었다. 코드 사전·포인터
(`codeGroupCode=`)가 정본이 된 뒤로 그 기준은 **크게 과장됐다** — 2026-09-03 실측:
후보 47종 중 **46종이 이미 판정돼 있었고**(값 있음 39 · 「코드 아님」 7)
값이 비어 있는 그룹은 **1종**이었다.

⇒ 이제 그 후보를 **코드 사전(`design/schema/code-dictionary.md`)으로 다시 가른다.**
   판정 함수는 `openapi/check-code-dictionary.py` 의 것을 «그대로 빌려 쓴다» —
   같은 판정을 두 곳에 두면 갈린다. ⛔ 위 수치도 «인용»이라 낡을 수 있다 —
   지금 값은 이 스크립트가 돌 때마다 다시 센다.

⚠ **한 칸이 여러 표를 가리키는 자리의 대응표 결손(구 `verify-polymorphic-mapping.py`)은
더 이상 여기 합류하지 않는다** — 물리 모델 소관이 백엔드팀으로 넘어가면서 이
저장소 안에는 그 검사기가 참조할 물리 모델 원본이 없다(2026-08-25, 데이터
모델링 폴더 삭제). 물리 모델 대응은 백엔드팀 소관 저장소에서 확인한다.

**수치를 이 파일에 손으로 적지 않는다.** 원본이 바뀌면 복사본에는 갱신 의무가
아무에게도 없다 — 이 저장소에서 손으로 쓴 수치는 예외 없이 낡았다.

⚠ 이 대장이 «안» 보는 것
------------------------
- **미결의 내용이 맞는지** — 스펙이 틀렸으면 대장도 똑같이 틀린다
- **추적 표지가 가리키는 곳이 살아 있는지** — 닫힌 이슈를 가리켜도 모른다
- **고객·팀 리더 회신 대기** — 그것은 화면 스펙 §8 밖에 있다
- **개발팀의 진행** — 2026-09-03 개정으로 우리가 갖는 정보가 아니다

쓰기
----
    python3 design/schema/generators/build-progress-ledger.py
"""
from __future__ import annotations

import argparse
import importlib
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OPENAPI = os.path.join(HERE, "openapi")
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
PROGRESS = os.path.join(ROOT, "design", "wiki", "progress")
OUT = os.path.join(PROGRESS, "99-설계진도대장.md")

# 갈래 이름 — 표와 코드가 같은 말을 쓰도록 한자리에 둔다.
HAS_VALUE = "사전이 값을 갖는다"
NOT_A_CODE = "계약이 「코드 그룹이 아니다」로 판정"
EMPTY_GROUP = "사전에 키는 있고 값이 ⬜"
NO_VERDICT = "어느 쪽에도 없다"


def run(script: str, *args: str) -> str:
    r = subprocess.run([sys.executable, os.path.join(HERE, script), *args],
                       capture_output=True, text=True, cwd=ROOT)
    return r.stdout


def read(path: str) -> str:
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def _plain(text: str) -> str:
    """굵게·코드 표기와 트리 기호를 벗긴다 — 이름을 «정확히» 맞추기 위해서다."""
    return text.replace("*", "").replace("`", "").lstrip("└├─ ").strip()


def summary_rows(text: str, keys: tuple[str, ...]) -> dict[str, str]:
    """생성물 요약 표에서 「| 이름 | 값 |」을 집어 온다.

    ⛔ 이름을 «시작 일치» 로 맞추지 않는다 — 「살아 있는 행」이 「살아 있는 행 중
    추적 표지가 없는 것」에도 걸려 뒤 값이 앞 값을 덮었다. 정확히 맞춘다.
    """
    want = set(keys)
    out: dict[str, str] = {}
    for line in text.split("\n"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        label = _plain(cells[0])
        if label in want:
            out[label] = _plain(cells[1])
    return out


def mechanical_codes() -> tuple[str, list[str]]:
    """`enum` 이 없는 `*Code` 업무 코드 — 개수와 이름.

    ⚠ **이것은 판정이 아니라 «후보 목록»이다.** 「`enum` 이 없다」는 기계적 기준이라,
    코드 사전·포인터(`codeGroupCode=`)로 확정된 자리까지 전부 담는다.
    가르는 일은 `code_verdicts()` 가 한다.
    """
    text = run("openapi/count-undecided-codes.py")
    m = re.search(r"⭐ 업무 코드\s+(\d+)", text)
    count = m.group(1) if m else "?"
    names: list[str] = []
    started = False
    for line in text.split("\n"):
        if line.startswith("⭐ 업무 코드"):
            started = True
            continue
        if started:
            if not line.startswith("   "):
                if names:
                    break
                continue
            names += line.split()
    return count, names


def code_verdicts(names: list[str]) -> dict[str, list[tuple[str, str]]]:
    """후보 이름들을 «코드 사전»으로 다시 가른다 — (갈래 → [(이름, 덧말)]).

    ⛔ 판정을 여기에 «다시 적지» 않는다 — `openapi/check-code-dictionary.py` 의
       `read_dictionary()`·`scan()` 을 그대로 빌려 쓴다. 사전을 읽는 파서가 둘이
       되면 그 순간 갈린다(코드 사전이 고치려는 병이 정확히 그것이다).

    가르는 길은 둘이다.
      ① **이름** — 사전 「프로퍼티」 열이 그 이름을 적었나
      ② **키**   — 계약의 그 자리가 `x-code-key: CD-…` 를 달았나
         ⭐ ② 가 있어야 하는 이유 — 사전 행의 프로퍼티 이름과 계약의 자리 이름이
            «다를 수 있다». `overrideReasonCode` 는 `CD-CONTROL-OVERRIDE-REASON`
            (프로퍼티 열은 `reasonCode`)을 가리켜 이름으로만 보면 안 걸린다.
    """
    if OPENAPI not in sys.path:
        sys.path.insert(0, OPENAPI)
    ccd = importlib.import_module("check-code-dictionary")

    entries = ccd.read_dictionary(ccd.DICT)
    places = ccd.scan()
    by_prop: dict[str, list[dict]] = {}
    by_key: dict[str, dict] = {}
    for e in entries:
        by_key[e["key"]] = e
        for prop in e["names"]:
            by_prop.setdefault(prop, []).append(e)

    out: dict[str, list[tuple[str, str]]] = {
        HAS_VALUE: [], NOT_A_CODE: [], EMPTY_GROUP: [], NO_VERDICT: []}
    for name in names:
        rows = list(by_prop.get(name, []))
        for place in places.get(name, []):
            for key in ccd.key_list(ccd.place_key(place)):
                e = by_key.get(key)
                if e is not None and e not in rows:
                    rows.append(e)
        excuses = [ccd.place_excused(p) for p in places.get(name, [])
                   if ccd.place_excused(p)]
        valued = [e for e in rows if e["values"]]
        if valued:
            # ⛔ 덧말에 키를 옮겨 적지 않는다 — 한 이름이 사전 키 스물 몇 개에
            #    걸리는 자리가 있고(`statusCode`), 그것을 여기 실으면 사전의 사본이 된다.
            out[HAS_VALUE].append((name, ""))
        elif rows:
            out[EMPTY_GROUP].append((name, " · ".join(
                "`%s`(%s · `%s`)" % (e["key"], " ".join("`%s`" % g for g in e["group"])
                                     or "그룹 없음", e["owner"]) for e in rows)))
        elif excuses:
            # 이유의 «첫 문장»만 싣는다 — 전문은 계약이 정본이다.
            # ⛔ 파이프는 이스케이프한다 — 이 덧말이 표 칸에 들어간다.
            why = " ".join(excuses[0].split(".")[0].split()).replace("|", "\\|")
            out[NOT_A_CODE].append((name, why))
        else:
            out[NO_VERDICT].append((name, ""))
    return out


def screen_gaps() -> dict[str, str]:
    """화면 축의 구멍. ⛔ 「착수 통지가 아직 안 나간 화면」 행은 없앴다(2026-09-03) —
    착수 통지가 폐지돼 셀 대상이 아니다."""
    run("build-screen-progress.py")
    text = read(os.path.join(PROGRESS, "화면-진도표.md"))
    out: dict[str, str] = {}
    for head in ("상세 스펙이 없는 화면", "요구서 §3 이 다루지 않은 화면"):
        m = re.search(r"^### [⛔⚠] %s — (\d+)건\n\n(.*)$" % re.escape(head),
                      text, re.M)
        out[head] = "%s건 — %s" % (m.group(1), m.group(2)) if m else "조회 못 함"
    return out


def main() -> int:
    # ⛔ `--no-remote` 는 없앴다(2026-09-03) — 착수 통지 폐지로 상대 저장소를
    #    조회하는 자리가 이 계보 전체에서 사라졌다.
    argparse.ArgumentParser(add_help=True).parse_args()

    run("collect-open-items.py")
    ledger = read(os.path.join(PROGRESS, "미결-대장.md"))
    TRACKLESS = "살아 있는 행 중 추적 표지가 없는 것"
    # ⭐ 「폐지 확정으로 제외한 스펙」도 함께 집는다 — 조용히 빼면 다음 사람이 스펙
    #    «파일»을 세고 「대장이 또 갈렸다」로 읽는다. 실제로 그 어긋남이 있었다
    #    (진도표 117 ↔ 이 대장 118). 판정은 `collect-open-items.retired()` 하나다.
    RETIRED = "폐지 확정으로 제외한 스펙"
    s = summary_rows(ledger, ("화면 스펙", RETIRED, "미결 행", "살아 있는 행",
                              TRACKLESS, "등급 열을 가진 행", "그중 차단"))
    code_count, code_names = mechanical_codes()
    verdicts = code_verdicts(code_names)
    open_codes = verdicts[EMPTY_GROUP] + verdicts[NO_VERDICT]
    gaps = screen_gaps()

    blocking = s.get("그중 차단", "?")
    verdict = ("✅ **차단 0 — 설계 골격은 서 있다.**"
               if blocking == "0" else
               "⛔ **차단 %s건 — 그 화면은 골격이 바뀔 수 있다.**" % blocking)

    lines = [
        "# 99 설계 진도 대장 — 우리 설계에서 아직 안 정해진 것",
        "",
        "> ⛔ **생성물이다. 손으로 고치지 마라.** `python3 design/schema/generators/build-progress-ledger.py` 가 다시 만든다.",
        ">",
        "> ⭐ **이 대장은 «설계팀 자신»을 위한 것이다** — 우리 설계의 미결이 화면 스펙 %s장에 흩어져 있어,"
        % s.get("화면 스펙", "여러"),
        "> 모아 두지 않으면 **우리가 우리 진행을 놓친다.**",
        ">",
        "> ⚠ **2026-09-03 개정** — 옛 이유는 개발팀을 향해 있었다(「인도물에 미결의 자리가 없으면 개발이 다 정해졌다로 읽는다」).",
        "> 지금은 개발팀이 **설계 자료를 직접 열람하고**, 설계팀은 **개발팀의 업무 진행에 직접 정보를 보유하지 않는다.**",
        "> 그래서 이 대장이 말하는 것은 **「우리 설계가 어디까지 됐나」** 하나다.",
        ">",
        "> ⚠ **「인계」라는 낱말이 더는 안 맞는다** — 넘겨주는 문서가 아니라 우리 진도표다.",
        "> 폴더·파일 이름 변경은 이번 범위 밖이라 **적어만 둔다**(`design/wiki/progress/`).",
        "",
        "## ⭐ 한 줄 판정",
        "",
        verdict,
        "",
        "살아 있는 미결이 **%s행**이지만 그중 **화면 골격을 바꾸는 것은 %s건**이다."
        % (s.get("살아 있는 행", "?"), blocking),
        "나머지는 **동작·문구가 바뀌거나 표시만 바뀌는 것**이라 골격을 다시 세우지 않는다.",
        "",
        "---",
        "",
        "## 1. 화면 스펙 미결",
        "",
        "| 무엇 | 값 |",
        "| --- | :-: |",
    ]
    for k in ("화면 스펙", "미결 행", "살아 있는 행", "등급 열을 가진 행", "그중 차단"):
        if k in s:
            lines.append("| %s | **%s** |" % (k, s[k]))
        if k == "화면 스펙" and RETIRED in s:
            # `_plain` 이 백틱을 벗겨 오므로 화면 ID 에 다시 씌운다.
            lines.append("| └ %s | %s |" % (RETIRED, re.sub(
                r"([WPM]-(?:CO|\d{2})-\d{2})", r"`\1`", s[RETIRED])))
    if TRACKLESS in s:
        lines.append("| 살아 있는 행 중 **추적 표지가 없는 것** | **%s** |" % s[TRACKLESS])
    lines += [
        "",
        "**전건과 화면별 내역은 `미결-대장.md` 가 정본이다.** 여기 옮기지 않는다.",
    ]
    if RETIRED in s:
        lines += [
            "",
            "⛔ **폐지 확정 스펙은 세지 않는다** — 파일은 남아 있어도 서 있는 화면이 아니다.",
            "그래서 이 대장·미결 대장·화면 진도표가 **같은 수**를 말한다"
            "(판정은 `collect-open-items.retired()` 하나를 셋이 함께 쓴다).",
            "전에는 진도표가 정본 인벤토리로 세고 두 대장이 스펙 «파일»로 세어 **한 벌만큼 갈려 있었다.**",
        ]
    lines += [
        "",
        "⭐ **추적 표지가 없는 행은 «결손»이 아니라 「안 붙인 것」이다**(2026-09-03) — 표지를 게이트로 읽던",
        "「표지 → 걸리는 화면」 역인덱스 표를 미결 대장에서 걷었다. 계수는 그대로 두되 뜻이 바뀐다:",
        "표지가 있으면 **역방향 조회가 되고**, 없으면 그 행은 **미결 대장의 화면별 절에서 화면으로 찾는다.**",
        "",
        "```",
        "python3 design/schema/generators/collect-open-items.py --issue <표지>   # 그 표지가 걸린 화면",
        "python3 design/schema/generators/collect-open-items.py --warn           # 표지 없는 행",
        "```",
        "",
        "## 2. 값이 아직 비어 있는 코드 그룹 — **%d종**" % len(open_codes),
        "",
        "⭐ **여기 남는 것은 「고객사가 자기 분류 체계를 정해야 하는 값」이 아니다** — 소유는 이미 갈렸다.",
        "남는 것은 **사전의 「값」 칸이 아직 ⬜ 인 그룹**이다.",
        "⭐ **확정을 기다리지 않는다** — 소유가 `registry` 면 **고객이 `W-06-06` 에서 운영 중에 채우는 값**이라",
        "«비어 있는 것이 정상»이고, 구현은 초기 시드로 진행한다.",
        "",
        "> ✅ **2026-09-03 해소 — 이 절이 크게 과장돼 있었다.** 전에는 「`enum` 이 없으면 미확정」이라는",
        "> **기계적 기준**으로 뽑은 **%s종**을 그대로 「확정되지 않은 업무 코드」로 실었는데,"
        " 그중 **%d종은 이미 판정이 끝나 있었다.**"
        % (code_count, len(verdicts[HAS_VALUE]) + len(verdicts[NOT_A_CODE])),
        "> 바로 그 아래에 「이 목록은 기계적 기준으로 뽑았다 … `G-31` 기준으로 **한 번 가른다**」는 경고가 달려 있었는데,",
        "> 그 가름을 **코드 사전(`design/schema/code-dictionary.md`)이 전건 끝냈다.** 이제 이 절이 사전을 읽는다.",
        "",
        "| 기계적 후보 **%s종**을 사전으로 다시 가르면 | 종수 |" % code_count,
        "| --- | :-: |",
    ]
    for bucket in (HAS_VALUE, NOT_A_CODE, EMPTY_GROUP, NO_VERDICT):
        mark = "**" if bucket in (EMPTY_GROUP, NO_VERDICT) else ""
        lines.append("| %s | %s%d%s |" % (bucket, mark, len(verdicts[bucket]), mark))
    lines += [
        "",
        "- **사전이 값을 갖는다** = 코드 사전의 「값」 열에 실제 코드 문자열이 있다. 계약이 `enum` 으로 닫았든 `codeGroupCode=` 포인터로 두었든 **값은 정해져 있다.**",
        "- **코드 그룹이 아니다** = 계약이 그 자리에 `x-no-code-key: \"<이유>\"` 를 적었다 — 개체 «식별자»이거나(공유계약 `A-16`) 그 축을 아예 세우지 않는다.",
        "",
    ]
    if verdicts[HAS_VALUE]:
        lines += ["<details><summary>사전이 값을 갖는 %d종 — 이름</summary>"
                  % len(verdicts[HAS_VALUE]), "",
                  " · ".join("`%s`" % n for n, _ in verdicts[HAS_VALUE]), "",
                  "값·그룹·소유는 **코드 사전이 정본이다** — 여기 옮기지 않는다"
                  "(한 이름이 사전 키 여럿에 걸린다).", "", "</details>", ""]
    if verdicts[NOT_A_CODE]:
        lines += ["<details><summary>「코드 그룹이 아니다」로 판정된 %d종 — 이유</summary>"
                  % len(verdicts[NOT_A_CODE]), "",
                  "| 이름 | 계약이 적은 이유 |", "| --- | --- |"]
        lines += ["| `%s` | %s |" % (n, why) for n, why in verdicts[NOT_A_CODE]]
        lines += ["", "</details>", ""]
    if verdicts[EMPTY_GROUP]:
        lines += ["### ⬜ 값이 비어 있는 그룹", "",
                  "| 이름 | 사전 키(그룹 · 소유) |", "| --- | --- |"]
        lines += ["| `%s` | %s |" % (n, why) for n, why in verdicts[EMPTY_GROUP]]
        lines += [""]
    if verdicts[NO_VERDICT]:
        lines += ["### ⛔ 판정이 아예 없는 이름", "",
                  "사전에도 없고 계약도 「코드 아님」을 안 적었다. **사전에 행을 세워야 한다.**", "",
                  " · ".join("`%s`" % n for n, _ in verdicts[NO_VERDICT]), ""]
    lines += [
        "> ⚠ **같은 이름이 도메인마다 다른 값 집합을 갖는 자리가 있다** — `inspectionTypeCode`(품질 `IQC`·`PQC`·`OQC` ↔ 설비 `DAILY`·`MONTHLY`·`MAINTENANCE`) · `eventTypeCode` · `statusCode`. **이름 하나로 뭉뚱그릴 수 없다.** 그래서 사전은 이름이 아니라 **`CD-` 키**로 값집합을 가른다(공유계약 `B-28`·`G-32`).",
        "",
        "> 다시 가르려면 `python3 design/schema/generators/openapi/check-code-dictionary.py`",
        "> 후보 목록만 다시 세려면 `python3 design/schema/generators/openapi/count-undecided-codes.py`",
        "",
        "## 3. 화면 축의 구멍",
        "",
        "| 무엇 | 값 |",
        "| --- | --- |",
    ]
    for k, v in gaps.items():
        lines.append("| %s | %s |" % (k, v))
    lines += [
        "",
        "> ⚠ **「착수 통지가 아직 안 나간 화면」 행은 없앴다**(2026-09-03) — 착수 통지가 폐지돼 셀 대상이 아니다.",
        "> 남은 두 행은 **설계팀 자신의 진행**이다.",
        "",
        "> 다시 만들려면 `python3 design/schema/generators/build-screen-progress.py`",
        "",
        "---",
        "",
        "## ⚠ 이 대장이 **안** 보는 것",
        "",
        "| 무엇 | 왜 |",
        "| --- | --- |",
        "| **미결의 내용이 맞는지** | 스펙이 틀렸으면 대장도 똑같이 틀린다 |",
        "| **추적 표지가 가리키는 곳이 살아 있는지** | 닫힌 이슈를 가리켜도 모른다 |",
        "| **고객·팀 리더 회신 대기** | 화면 스펙 §8 밖에 있다 |",
        "| **데이터 모델 결손** | 스펙·계약에 업무 사실로 적혀 있고 우리를 막지 않는다 — 별도 통지는 없다(V3 규칙 2) |",
        "| **개발팀의 진행** | 2026-09-03 개정 — 설계팀이 갖는 정보가 아니다 |",
        "",
    ]
    io.open(OUT, "w", encoding="utf-8").write("\n".join(lines))
    print("생성: %s" % os.path.relpath(OUT, ROOT))
    print("차단 %s · 살아 있는 미결 %s · 값이 비어 있는 코드 그룹 %d (기계적 후보 %s종 중)"
          % (blocking, s.get("살아 있는 행", "?"), len(open_codes), code_count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
