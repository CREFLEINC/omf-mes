#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""화면 스펙 §8 을 전수로 훑어 «미결 대장»을 생성한다.

왜 필요한가
-----------
미결이 태어나는 자리는 화면 스펙 §8 하나인데, **전체를 담은 대장이 없었다.**
그래서 「확정이 내려왔을 때 어느 화면이 걸리나」를 사람이 118파일을 훑어야
답할 수 있었고, 실제로 두 번 못 찾았다.

    2026-08-16  「MES 는 품의서를 기안하지 않는다」 확정
                → 확정문이 예로 든 W-01-06 만 보고 W-04-10 을 못 봤다
    2026-08-16  재고 상태 값 목록 협착
                → 어느 통지가 걸리는지 안 보고 계약을 좁혔다

⭐ **그래서 사람이 적는 대장을 만들지 않는다.** 손으로 쓴 대장은 이 저장소에서
예외 없이 낡았다(요구서 머리말 6/8 · README 6수치 · ds-gap 진도 …).
**스펙이 정본이고 대장은 뽑는 것**이어야 한다.

무엇을 하나
-----------
1. `design/wiki/screens/*/` 아래 화면 스펙(`W-`·`P-`·`M-` 로 시작)을 전부 찾는다.
2. 각 파일에서 「미결」 절의 표를 찾아 행을 뽑는다. 서식은 두 판이 섞여 있다.

       5열 판  | # | 항목 | 성격 | 등급 | 처리 |
       4열 판  | # | 항목 | 성격 | 처리 |

   열 이름으로 가르므로 열 순서가 바뀌어도 따라간다.
3. 행마다 **추적 표지**를 뽑는다 — 이슈 `#N` · 의사결정 요청 `DR-00N` ·
   공유계약 조항 `X-N` · 고객 회신 `회신 E-N`. 하나도 없으면 그 행은 **답이 왔을 때
   기계로 찾을 수 없다.**
   ⛔ `E-N` 은 세 가지가 쓴다(§E 조항 · 고객 회신 · 화면 스펙 §7 예외). 앞 낱말로
   가르고 **예외 번호는 버린다** — `tag_e_codes()` 주석 참조.
4. **해소 표시**(✅ · 해소 · 종결 · 취소선)가 붙은 행을 갈라 센다.
   ⛔ 단 「좁힘」이 적힌 행은 **살아 있는 것으로 센다** — 부분 해소 표기라 문면에
   「해소」가 같이 나온다. `resolved()` 주석 ③ 참조.
5. `design/wiki/handover/미결-대장.md` 로 쓴다.

⚠ 이 생성기가 못 보는 것
------------------------
- **미결의 «내용»이 맞는지는 안 본다.** 표에 적힌 것을 옮길 뿐이다.
- **추적 표지가 «가리키는 곳»이 살아 있는지 안 본다.** `#54` 처럼 이미 닫힌
  이슈를 가리켜도 표지가 있는 것으로 센다. 닫힌 이슈 되짚기는 별도 절차다.
- **표 밖에 적힌 미결은 못 잡는다.** 확대 1차는 미결 상세를 공유계약 §I 묶음
  표에 두어, 스펙 행만으로는 무엇을 기다리는지 알 수 없다(`--warn` 이 알린다).
- **「차단」 판정이 맞는지 안 본다.** 4열 판에는 등급 열이 아예 없다.
- **해소 판정은 낱말로 한다 — 뜻으로 하지 않는다.** 부정 표현은 목록(`NOT_DONE`)에
  적힌 것만 가른다. 목록 밖의 말로 「안 됐다」를 적으면 여전히 해소로 샌다.
  ⚠ 반대쪽도 있다 — **자기 해소를 「」 «안»에 적으면 열림으로 샌다.** 인용 안은
  남의 판정으로 보기 때문이다. 해소는 인용 밖에 적는다(지금 그런 행은 0건).
  ⭐ **한 행에 소관을 둘 두지 않는 것**이 근본 해법이다 — 가르면 추정할 것이 없어진다
  (선례: `#336` 이 `W-04-07` 미결 1 을 `1`·`1-b` 로 가름).
- **미결 절 안의 «다른 표»를 못 가른다.** 열 수가 같으면 미결 행으로 흡수한다
  (`W-05-03` §8-2 의 규칙 표 8행 — 별건).

쓰기
----
    python3 design/schema/generators/collect-open-items.py              # 대장을 다시 만든다
    python3 design/schema/generators/collect-open-items.py --check      # 무변경인지만 본다(종료 1 = 갈렸다)
    python3 design/schema/generators/collect-open-items.py --warn       # 추적 표지 없는 행을 나열
    python3 design/schema/generators/collect-open-items.py --issue 64   # 그 표지가 걸린 화면만
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "design", "wiki", "handover", "미결-대장.md")

SPEC_GLOB = os.path.join(ROOT, "design", "wiki", "screens", "*", "[WPM]-*.md")
SCREEN_ID = re.compile(r"^([WPM]-(?:CO|\d{2})-\d{2})")

# 「미결」이 제목에 들어간 절. §8 이 표준이나 차수마다 번호가 다를 수 있어
# 번호로 찾지 않는다.
HEAD = re.compile(r"^(#{2,4})\s+.*미결", re.M)
ANY_HEAD = re.compile(r"^#{1,4}\s", re.M)

# 추적 표지 — 이 넷 중 하나라도 있으면 「답이 왔을 때 되짚을 수 있다」.
#
# ⛔ 「회신」을 따로 두지 않는다 — 정규식이 「조항」과 «글자 그대로 겹쳤다»(2026-09-02).
#    `E-\d` 는 `[A-J]-\d` 의 부분집합이라 같은 문자열이 나오고, 아래 dedup 이
#    둘을 하나로 합쳐 «어느 쪽인지가 사라졌다.» 갈라 내는 일은 tag_e_codes() 가 한다.
#
# ⛔ 「이슈」도 따로 두지 않는다 — `#N` 을 «고객 질의응답 번호»가 같은 모양으로 쓴다.
#    「보류 등록이 알림 대상인가(QA #24)」의 `#24` 를 이슈 #24(도식스펙-04 정합)로
#    잡고 있었다. 갈라 내는 일은 tag_issues() 가 한다.
TRACKS = (
    ("DR", re.compile(r"\bDR-(\d{3})\b")),
    ("조항", re.compile(r"\b([A-DF-J]-\d{1,2})\b")),
)

# ⛔ `E-n` 은 «세 가지»가 쓴다 — 문자열만 보면 갈 수 없다(2026-09-02 실측).
#
#    ① 공유계약 §E 조항        E-1 「POP 화면 예산」 · E-2 「긴 식별자 표시 규칙」
#    ② 고객 회신 번호           회신 E-9 「권한 값 목록」
#    ③ 화면 스펙 §7 예외 번호   예외 E-6 ② 「Hold 강제출고」  ← 그 화면의 «자기» 번호
#
# ③ 은 추적 표지가 «아니다» — 답을 줄 상대가 없다. 그런데 대장은 셋을 한 칸에 합쳐
# 「추적 표지 → 걸리는 화면」 표를 「답이 왔을 때 여기를 본다」로 내놓고 있었다.
# 실측 — 추적 표지 칸에 `E-n` 이 실린 25행 중 «18행이 예외»였고, 그중 17행은
# 다른 표지가 없어 「추적 가능」으로 잘못 세어졌다.
#
# 가르는 수단은 «바로 앞 낱말»이다. 실측에서 예외 78회·회신 71회가 전부 앞에 그 말을
# 달고 있었고, 아무 말도 없는 것은 전부 §E 조항 인용이었다.
E_CODE = re.compile(r"\b(E-\d{1,2})\b")
E_NEAR = 10          # 앞 낱말을 찾는 창. 「예외 E-6 ②」·「회신 E-9(권한 …)」 둘 다 덮는다


def tag_e_codes(text: str) -> list[str]:
    """`E-n` 을 앞 낱말로 갈라 표지를 만든다. 예외 번호는 표지가 아니라 «버린다»."""
    out = []
    for m in E_CODE.finditer(text):
        pre = text[max(0, m.start() - E_NEAR):m.start()]
        if "예외" in pre:
            continue                      # ③ 화면 자기 번호 — 답이 와도 못 찾는다
        tag = f"회신 {m.group(1)}" if "회신" in pre else m.group(1)
        if tag not in out:
            out.append(tag)
    return out


# ⛔ `#N` 도 «두 가지»가 쓴다 — `E-n` 과 같은 형태의 오독이다(2026-09-02 실측).
#
#    ① 이슈 번호        #145 「공통코드 값 목록」 — 답이 오면 그 이슈가 움직인다
#    ② 고객 질의응답     QA #24 「보류 등록이 알림 대상인가」 — 답이 «이미» 온 근거다
#
# ⚠ ② 를 이슈로 세면 «엉뚱한 이슈»에 걸린다. `W-03-03` 미결 6 의 「QA #24」가
#    이슈 #24(도식스펙-04 정합 4건)로 잡혀 있었다 — 그 이슈가 닫혀도 이 행은 안 움직인다.
#    실측 — 미결 표의 `#N` 227 개 중 10 개가 QA 번호였다.
ISSUE_NO = re.compile(r"#(\d{1,3})\b")
QA_MARK = re.compile(r"(QA|질의응답)\s*$")


def tag_issues(text: str) -> list[str]:
    """`#N` 을 앞 낱말로 갈라 이슈 표지만 남긴다. QA 번호는 «버린다»."""
    out = []
    for m in ISSUE_NO.finditer(text):
        if QA_MARK.search(text[max(0, m.start() - 12):m.start()]):
            continue                      # ② 고객 질의응답 번호 — 이슈가 아니다
        tag = f"#{m.group(1)}"
        if tag not in out:
            out.append(tag)
    return out


DONE = re.compile(r"✅|해소|종결|~~")

# ⛔ 해소 판정을 «두 번» 거른다 — 그냥 찾으면 반대말과 남의 말을 삼킨다(2026-09-02 · #349).
#
# ① 부정 접두 — 한국어는 「미-」가 붙어도 원형을 그대로 품어 낱말 경계로 못 가른다.
#    「여전히 미해소」가 「해소」로 걸려 그 행이 대장에서 사라졌다.
#    ⚠ 「아직」·「잔여」·「부분 해소」는 **넣지 않는다** — 실측 반례가 있다.
#    `W-05-08` 미결 2 는 진짜 종결인데 «남의 화면» 미결을 「아직 살아 있어」로 언급한다.
#    넣으면 그 행이 거꾸로 열림이 된다.
NOT_DONE = re.compile(r"미해소|해소되지|해소 안|미종결|종결되지|종결 안")

# ③ 「좁힘」 — 우리가 «부분 해소»에 쓰는 표기다(1·2회차). 그 문면은 거의 언제나
#    「X 는 해소됐다. 남은 것은 Y」 꼴이라 위 DONE 의 「해소」에 걸린다. 그런데
#    좁힘은 «행이 살아 있다»는 뜻이므로 사라지면 안 된다.
#    실측 2026-09-02 — 좁힘 16행 중 3행이 통째로 사라져 있었다(P-01-01 1 ·
#    P-02-05 1 · W-04-01 3). 하필 «남은 물음»만 담긴 행이라 가장 나쁘다.
#    ⚠ 「아직」·「잔여」와 달리 이것은 «표기 규약»이라 남의 말을 옮길 위험이 없다 —
#    남의 판정을 옮길 때는 「」 안에 넣고, 그것은 QUOTED 가 이미 걷는다.
NARROWED = re.compile(r"좁힘")

# ② 인용 — 「」 안은 **남의 판정**이지 이 행의 판정이 아니다.
#    「Routing 축은 스냅샷으로 종결 — BOM 축 잔여」를 처리 열에 적었더니
#    그 행(BOM 축이 미결인 행)이 통째로 해소로 넘어갔다.
QUOTED = re.compile(r"「[^」]*」")


def resolved(whole: str) -> bool:
    """이 행이 해소됐나. 인용 «밖»에서 해소 표시를 찾고, 부정 표현이 있으면 뒤집는다.

    ⚠ 두 거름의 범위가 다르다 — 해소는 인용을 걷고 찾지만 부정은 전문에서 찾는다.
    둘 다 «열림 쪽»으로 기울이려는 것이다. 대장이 놓치면 미결이 사라지고,
    남기면 사람이 한 번 더 볼 뿐이다.
    """
    body = QUOTED.sub(" ", whole)
    if NARROWED.search(body):
        return False                    # ③ 좁힘은 «살아 있다» — 「해소」가 같이 적혀도
    return bool(DONE.search(body)) and not NOT_DONE.search(whole)


def cells(line: str) -> list[str]:
    """마크다운 표 한 줄을 칸으로 가른다 — 양끝 파이프는 버린다."""
    if not line.startswith("|"):
        return []
    return [c.strip() for c in line.strip().strip("|").split("|")]


def plain(text: str) -> str:
    """표기를 걷어 낸다 — 대장에서 다시 표로 쓰므로 파이프는 이스케이프한다."""
    t = re.sub(r"\*\*|~~|`", "", text)
    return t.replace("|", "\\|").strip()


def section(body: str) -> str | None:
    """미결 절 본문. 다음 «같거나 더 높은 수준» 헤딩까지.

    ⚠ 제목에 「미결」이 든 헤딩이 여럿일 수 있다 — 「`W-04-08` 미결 해소」처럼
    §5 소절이 남의 미결을 «언급»하기도 한다. 그래서 첫 헤딩을 집지 않고,
    **미결 표(`| # | 항목 …`)를 실제로 가진 절**을 고른다.
    """
    fallback = None
    for m in HEAD.finditer(body):
        level = len(m.group(1))
        rest = body[m.end():]
        sec = rest
        for nxt in ANY_HEAD.finditer(rest):
            if len(nxt.group(0).split()[0]) <= level:
                sec = rest[: nxt.start()]
                break
        if any(cells(l)[:1] in (["#"], ["번호"]) and any("항목" in c for c in cells(l))
               for l in sec.splitlines() if l.startswith("|")):
            return sec
        if fallback is None:
            fallback = sec
    return fallback


def parse(path: str) -> dict | None:
    sid = SCREEN_ID.match(os.path.basename(path))
    if not sid:
        return None
    body = open(path, encoding="utf-8").read()
    sec = section(body)
    if sec is None:
        return {"screen": sid.group(1), "path": path, "rows": [], "table": False,
                "declared": None}

    rows, header = [], None
    for line in sec.splitlines():
        cs = cells(line)
        if not cs:
            continue
        if header is None:
            if cs[0] in ("#", "번호") and any("항목" in c for c in cs):
                header = cs
            continue
        if set("".join(cs)) <= set("-: "):        # 구분선
            continue
        if len(cs) < len(header) - 1:             # 표가 끝났다
            break
        col = dict(zip(header, cs))
        item = next((v for k, v in col.items() if "항목" in k), cs[1] if len(cs) > 1 else "")
        handling = next((v for k, v in col.items() if "처리" in k), "")
        nature = next((v for k, v in col.items() if "성격" in k), "")
        grade = next((v for k, v in col.items() if "등급" in k), "")
        whole = " ".join(cs)
        marks = []
        for tag in tag_issues(whole):       # `#N` 은 QA 번호와 갈라야 한다
            marks.append(tag)
        for kind, pat in TRACKS:
            for hit in pat.findall(whole):
                tag = f"DR-{hit}" if kind == "DR" else hit
                if tag not in marks:
                    marks.append(tag)
        for tag in tag_e_codes(whole):      # `E-n` 은 앞 낱말로 갈라야 한다
            if tag not in marks:
                marks.append(tag)
        rows.append({
            "no": cs[0].strip("*# "), "item": item, "nature": nature,
            "grade": grade, "handling": handling, "marks": marks,
            "done": resolved(whole),
        })

    declared = None
    m = re.search(r"차단\s*(\d+)\s*건", sec)
    if m:
        declared = int(m.group(1))
    return {"screen": sid.group(1), "path": path, "rows": rows,
            "table": header is not None, "declared": declared}


def collect() -> list[dict]:
    out = [parse(p) for p in sorted(glob.glob(SPEC_GLOB))]
    return sorted([s for s in out if s], key=lambda s: s["screen"])


def render(specs: list[dict]) -> str:
    rows = [(s, r) for s in specs for r in s["rows"]]
    open_rows = [(s, r) for s, r in rows if not r["done"]]
    untracked = [(s, r) for s, r in open_rows if not r["marks"]]
    graded = [(s, r) for s, r in rows if r["grade"]]
    blocking = [(s, r) for s, r in open_rows if "차단" in r["grade"]]

    L = [
        "# 미결 대장 — 화면 스펙 §8 전수",
        "",
        "> ⛔ **생성물이다. 손으로 고치지 마라.** 정본은 각 화면 스펙의 「미결」 절이고,",
        "> 이 파일은 `python3 design/schema/generators/collect-open-items.py` 가 다시 만든다.",
        ">",
        "> 이 대장이 답하는 질문 = **「확정이 내려왔을 때 어느 화면이 걸리나」**.",
        "> 그 답을 못 찾아 두 번 사고가 났다(2026-08-16 품의 개칭 · 재고 상태 협착).",
        "",
        "## 요약",
        "",
        "| 무엇 | 값 |",
        "| --- | :-: |",
        f"| 화면 스펙 | **{len(specs)}** |",
        f"| 미결 절을 못 찾은 스펙 | **{sum(1 for s in specs if not s['table'])}** |",
        f"| 미결 행 | **{len(rows)}** |",
        f"| ├ 해소 표시가 붙은 행 | {len(rows) - len(open_rows)} |",
        f"| └ 살아 있는 행 | **{len(open_rows)}** |",
        f"| 살아 있는 행 중 **추적 표지가 없는 것** | **{len(untracked)}** "
        f"({round(len(untracked) * 100 / max(len(open_rows), 1))}%) |",
        f"| 등급 열을 가진 행 | {len(graded)} |",
        f"| 그중 **차단** | **{len(blocking)}** |",
        "",
        "⚠ **추적 표지가 없다** = 이슈 `#N` · `DR-00N` · 공유계약 조항 `X-N` ·",
        "고객 회신 `회신 E-N` 어느 것도 안 적혀 있다. 그 행은 **답이 와도 기계로 못 찾는다.**",
        "",
        "⛔ **화면 스펙 §7 의 「예외 `E-N`」은 표지로 세지 않는다**(2026-09-02) — 그 화면의",
        "«자기» 번호라 답을 줄 상대가 없다. 앞 낱말이 「예외」이면 버리고, 「회신」이면",
        "`회신 E-N` 으로, 아무 말도 없으면 공유계약 §E 조항으로 잡는다. **셋은 문자열이 같다.**",
        "",
    ]

    if blocking:
        L += ["## ⛔ 차단 — 착수 통지를 낼 수 없는 화면", ""]
        L += ["| 화면 | 항목 | 처리 |", "| --- | --- | --- |"]
        L += [f"| `{s['screen']}` | {plain(r['item'])} | {plain(r['handling'])} |"
              for s, r in blocking]
        L += [""]

    # 표지별 역인덱스 — 이 대장의 존재 이유다
    index: dict[str, list[str]] = {}
    for s, r in open_rows:
        for mk in r["marks"]:
            index.setdefault(mk, []).append(s["screen"])
    L += ["## 추적 표지 → 걸리는 화면", "",
          "⭐ **답이 왔을 때 여기를 본다.** 표지 하나가 여러 화면에 걸린다.", "",
          "| 표지 | 화면 수 | 화면 |", "| --- | :-: | --- |"]
    for mk in sorted(index, key=lambda k: (-len(index[k]), k)):
        seen = sorted(set(index[mk]))
        L.append(f"| `{mk}` | {len(seen)} | {' · '.join(f'`{x}`' for x in seen)} |")
    L += [""]

    L += ["## 화면별 미결", ""]
    for s in specs:
        live = [r for r in s["rows"] if not r["done"]]
        if not s["table"]:
            L += [f"### `{s['screen']}`", "", "⚠ **미결 절을 못 찾았다** — "
                  f"`{os.path.relpath(s['path'], ROOT)}`", ""]
            continue
        if not live:
            L += [f"### `{s['screen']}` — 살아 있는 미결 0건", ""]
            continue
        L += [f"### `{s['screen']}` — {len(live)}건", "",
              "| # | 항목 | 성격 | 등급 | 처리 | 표지 |",
              "| :-: | --- | --- | :-: | --- | --- |"]
        for r in live:
            marks = " ".join(f"`{m}`" for m in r["marks"]) or "**없음**"
            L.append(f"| {r['no']} | {plain(r['item'])} | {plain(r['nature'])} | "
                     f"{plain(r['grade']) or '—'} | {plain(r['handling'])} | {marks} |")
        L += [""]
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="다시 만든 것과 같은지만 본다")
    ap.add_argument("--warn", action="store_true", help="추적 표지 없는 행을 나열")
    ap.add_argument("--issue", help="그 표지가 걸린 화면만 (예: 64 · DR-007 · C-12)")
    a = ap.parse_args()

    specs = collect()
    if not specs:
        print("⛔ 화면 스펙을 못 찾았다", file=sys.stderr)
        return 1

    if a.issue:
        want = a.issue if not a.issue.isdigit() else f"#{a.issue}"
        hits = [(s["screen"], r) for s in specs for r in s["rows"]
                if want in r["marks"] and not r["done"]]
        screens = sorted({sid for sid, _ in hits})
        print(f"`{want}` 가 걸린 살아 있는 미결 — **{len(hits)}건 / {len(screens)}화면**")
        for sid, r in hits:
            print(f"  {sid:10} {plain(r['item'])[:90]}")
        return 0

    if a.warn:
        bad = [(s["screen"], r) for s in specs for r in s["rows"]
               if not r["done"] and not r["marks"]]
        print(f"추적 표지 없는 살아 있는 미결 — {len(bad)}건")
        for sid, r in bad:
            print(f"  {sid:10} {plain(r['item'])[:90]}")
        return 1 if bad else 0

    text = render(specs)
    if a.check:
        old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if old == text:
            print(f"✅ 미결 대장이 스펙과 같습니다 — 화면 {len(specs)}")
            return 0
        print("⛔ 미결 대장이 스펙과 갈렸습니다 — 다시 만드십시오", file=sys.stderr)
        return 1

    open(OUT, "w", encoding="utf-8").write(text)
    rows = sum(len(s["rows"]) for s in specs)
    live = sum(1 for s in specs for r in s["rows"] if not r["done"])
    untracked = sum(1 for s in specs for r in s["rows"]
                    if not r["done"] and not r["marks"])
    print(f"  ✅ {os.path.relpath(OUT, ROOT)} — 화면 {len(specs)} · 미결 행 {rows} "
          f"· 살아 있음 {live} · 추적 표지 없음 {untracked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
