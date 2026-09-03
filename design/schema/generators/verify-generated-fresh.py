#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""생성물이 정본과 갈렸는지 본다 — 다시 만들어 보고 «되돌린다». 저장소를 바꾸지 않는다.

무엇을 보나
-----------
`openapi/ui-요구목록*.md` 는 **화면 상세 스펙 §5 액션 표에서 생성한 파생물**이다.
그런데 커밋돼 있어서 **정본처럼 읽힌다.** 스펙이 바뀌었는데 다시 만들지 않으면
파일이 조용히 낡고, 그것을 읽는 `verify-mapping-coverage.py` 가 **거짓 초록**을 낸다.

이 검사는 도메인마다 생성기를 돌려 **바뀌는 것이 있는지**만 보고 **원래대로 되돌린다.**

**HTML 배포본 9건도 같은 성격이다** — `.md` 에서 생성돼 커밋되고, 다시 만들지 않으면
조용히 낡는다. 조달·프론트가 실제로 여는 것이 이 단일 파일 배포본이다(폰트 base64
임베드, 건당 2.1~2.5MB). 짝 표는 생성기의 «선언»에서 가져온다 — `build-doc-html.py` 의
`CONFIG`, 04 두 건의 `SRC`/`DST`. ⛔ 파일명 매칭은 `00-요구사항명세서.md` →
`01-요구사항명세서.html` 한 쌍을 놓친다.

⛔ 왜 만들었나 — 실제로 일어났다
--------------------------------
2026-08-18 실측:

    커버리지 게이트          04 — 액션 147 · ✅ 전건 다뤘습니다
    스냅숏을 다시 만들면      04 — 액션 149          ← 둘이 더 있었다

늘어난 둘은 2026-08-13 확정(DR-013)이 낳은 폐기 거래처 액션이었고, **04 요구서에
그 낱말이 0건**이었다. 게이트는 초록인데 요구서는 그 동작을 몰랐다.

⭐ 뿌리는 「어느 쪽이 정본인지 안 정한 것」이다 — **정본은 화면 스펙이고 이 목록은
파생물이다.** 계약 쪽은 같은 뿌리의 문제를 「JSON 이 정본」으로 정해 끝냈고,
여기는 이 검사가 그 자리를 대신한다.

⚠ 무엇을 «안» 보나
-------------------
- **목록의 내용이 맞는지** — 스펙이 틀렸으면 생성물도 똑같이 틀린다. 같이 틀린다.
- **요구서가 그 액션을 다뤘는지** — 그것은 `verify-mapping-coverage.py` 몫이다.
  이 검사가 초록이어도 게이트는 빨갈 수 있다(그것이 정상이다).
- **생성기 자체가 옳은지** — 생성기가 액션을 빠뜨리면 양쪽이 함께 빠진다.
- **표지 KPI·lede 가 낡았는지** — `build-doc-html.py` 의 `CONFIG` 에 «손으로» 적힌
  값이라, 원본 `.md` 의 숫자가 바뀌어도 재생성 바이트가 안 바뀐다
  (`design/wiki/00-index.md` 의 ⚠ 문단과 같은 이야기). `build-04-ia-html.py` ·
  `build-04-ia-도식본.py` 는 md 에서 직접 세므로 예외다.

쓰기
----
    python3 design/schema/generators/verify-generated-fresh.py              # md 9 + html 9
    python3 design/schema/generators/verify-generated-fresh.py --kind html  # 배포본만
    python3 design/schema/generators/verify-generated-fresh.py --domain 04  # md 한 도메인

전건 실행 0.4초 남짓이다(생성기 3종 순차 real 0.35s 실측) — 상시 검사에 그대로 둔다.

갈린 것이 있으면 종료 코드 1. 되돌리기는 **어떤 경우에도** 수행한다.
"""
from __future__ import annotations

import filecmp
import argparse
import importlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_COV = importlib.import_module("verify-ui-coverage")

DOMAINS = list(_COV.DOMAINS)
GENERATOR = os.path.join(HERE, "verify-ui-coverage.py")

# ── HTML 배포본 축 (omf-mes#248) ────────────────────────────────────
# 짝 표는 «생성기 자신의 선언»에서 가져온다 — ⛔ 파일명 매칭 금지:
# '00-요구사항명세서.md' → '01-요구사항명세서.html' 처럼 이름이 다른 짝이 있다.
_DOC = importlib.import_module("build-doc-html")     # CONFIG · DOC_DIR · ROOT

# ⛔ 04 두 건은 import 하면 안 된다:
#    · build-04-ia-도식본.py 는 __main__ 가드가 없어 import 즉시 배포본을 덮어쓴다
#    · 두 건 모두 모듈 수준에서 sys.argv[1] 을 번들 경로(KIT)로 읽어 검사기 인자를 오인한다
#    → 소스에서 SRC/DST 리터럴만 «정적으로» 뽑는다.
_IA_SCRIPTS = ("build-04-ia-html.py", "build-04-ia-도식본.py")
_IA_LIT = re.compile(
    r"^(SRC|DST)\s*=\s*os\.path\.join\(PROJECT_SPEC_DIR,\s*'([^']+)'\)", re.M)


def _ia_pair(script: str) -> tuple[str, str]:
    body = open(os.path.join(HERE, script), encoding="utf-8").read()
    got = dict(_IA_LIT.findall(body))
    if set(got) != {"SRC", "DST"}:
        raise SystemExit("⛔ %s 의 SRC/DST 선언을 못 읽었다 — 생성기가 바뀌었다" % script)
    return got["SRC"], got["DST"]


def html_targets() -> list[tuple[str, str, list[str]]]:
    """[(원본 md, 배포본 html, 재생성 명령)] — 9건."""
    out = []
    for key, cfg in _DOC.CONFIG.items():
        d = _DOC.DOC_DIR[key]
        out.append((os.path.join(d, cfg["src"]), os.path.join(d, cfg["dst"]),
                    [sys.executable, "build-doc-html.py", key]))
    spec = os.path.join(_DOC.ROOT, "design", "wiki", "project-spec")
    for script in _IA_SCRIPTS:
        src, dst = _ia_pair(script)
        out.append((os.path.join(spec, src), os.path.join(spec, dst),
                    [sys.executable, script]))
    return out


def check_html() -> int:
    """배포본을 다시 만들어 바이트 비교하고 «되돌린다». 낡은 건수를 돌려준다."""
    targets = html_targets()
    stale: list[str] = []
    # ⛔ 9건 합계 19.6MB — 메모리 대신 임시 디렉터리에 사본을 둔다.
    with tempfile.TemporaryDirectory() as keep:
        saved: dict[str, str] = {}
        try:
            for i, (src, dst, cmd) in enumerate(targets):
                if not os.path.exists(dst):
                    print("⛔ 배포본이 없다 — %s" % os.path.relpath(dst, _DOC.ROOT))
                    stale.append(dst)
                    continue
                bak = os.path.join(keep, "%02d.bak" % i)
                shutil.copy2(dst, bak)
                saved[dst] = bak
                try:
                    subprocess.run(cmd, cwd=HERE, check=True,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                except subprocess.CalledProcessError as e:
                    # ⛔ 기본 메시지는 stderr 를 담지 않는다 — 「returned non-zero exit
                    #    status 1」만 남으면 생성기가 왜 깨졌는지 알 수 없다.
                    sys.stderr.write((e.stderr or b"").decode("utf-8", "replace"))
                    raise SystemExit("⛔ 생성기가 실패했습니다: %s" % " ".join(cmd))
                if not filecmp.cmp(dst, bak, shallow=False):
                    stale.append(dst)
                    print("⛔ 배포본이 낡았다 — %s  (원본 %s)"
                          % (os.path.relpath(dst, _DOC.ROOT), os.path.basename(src)))
        finally:
            # ⛔ 어떤 경우에도 되돌린다 — 이 검사는 저장소를 바꾸지 않는다.
            for dst, bak in saved.items():
                shutil.copy2(bak, dst)
    if not stale:
        print("✅ 배포본 %d건이 원본 .md 와 같습니다 — 다시 만들어도 안 바뀝니다."
              % len(targets))
    return len(stale)


def target_of(domain: str) -> str:
    return os.path.join(HERE, "openapi", _COV.DOMAINS[domain][1])


def regenerate(domain: str) -> None:
    # ⛔ --write 는 반드시 준다 — 2026-09-03 부터 verify-ui-coverage.py 의 기본은
    #    «검사»이고 인자 없이는 아무것도 쓰지 않는다. 빼면 이 검사가 «원본을 그대로
    #    두고 비교»해 언제나 초록이 된다(거짓 초록).
    cmd = [sys.executable, GENERATOR, "--write"]
    if domain != "mdm":  # mdm 은 생성기의 기본값이라 --domain 을 주지 않는다
        cmd += ["--domain", domain]
    try:
        subprocess.run(cmd, cwd=HERE, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        sys.stderr.write((e.stderr or b"").decode("utf-8", "replace"))
        raise SystemExit("⛔ 배포본 생성기가 실패했습니다: %s" % " ".join(cmd))


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--domain", choices=DOMAINS)
    ap.add_argument("--kind", choices=("md", "html"),
                    help="생략하면 둘 다 — md=ui-요구목록 9건 · html=배포본 9건")
    args = ap.parse_args()
    # ⛔ --kind html 은 도메인 개념이 없다. 둘을 함께 주면 md 축도 html 축도 돌지 않아
    #    «아무것도 검사하지 않고 EXIT=0» 이 난다 — 이 저장소가 O-1 에서 겪은 거짓 초록과
    #    같은 형태다(PR #288 리뷰 지적).
    if args.domain and args.kind == "html":
        ap.error("--domain 은 md 축(ui-요구목록) 개념입니다 — html 배포본에는 도메인이 없습니다.")

    run_md = args.kind in (None, "md")
    run_html = args.kind in (None, "html") and not args.domain   # --domain 은 md 축 개념
    domains = ([args.domain] if args.domain else DOMAINS) if run_md else []
    before: dict[str, bytes] = {}
    stale: list[str] = []

    try:
        for d in domains:
            path = target_of(d)
            if not os.path.exists(path):
                print(f"⛔ 생성물이 없다 — {os.path.relpath(path, HERE)}")
                stale.append(d)
                continue
            before[path] = open(path, "rb").read()
            regenerate(d)
            after = open(path, "rb").read()
            if after != before[path]:
                stale.append(d)
                print(f"⛔ {d} — 다시 만들면 달라진다 · "
                      f"{os.path.relpath(path, HERE)}")
    finally:
        # ⛔ 어떤 경우에도 되돌린다 — 이 검사는 저장소를 바꾸지 않는다.
        for path, body in before.items():
            open(path, "wb").write(body)

    print()
    rc = 0
    if stale:
        print(f"⛔ 낡은 생성물 {len(stale)}건 — {' · '.join(stale)}")
        print("→ 다시 만들고, 늘어난 액션을 요구서 §3 매핑표에 넣는다.")
        print("   (이 검사는 되돌려 두었으므로 저장소는 그대로다)")
        rc = 1
    elif run_md:
        print(f"✅ 생성물 {len(domains)}건이 스펙과 같습니다 — 다시 만들어도 안 바뀝니다.")
    if run_html:
        n = check_html()
        if n:
            print(f"⛔ 낡은 배포본 {n}건 — 원본 .md 를 고치고 다시 만들지 않았다.")
            print("→ python3 build-doc-html.py all · build-04-ia-html.py · build-04-ia-도식본.py")
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
