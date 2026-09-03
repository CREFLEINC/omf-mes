#!/usr/bin/env python3
"""PreToolUse 훅: 읽기 전용 영역 보호.

- design/raw/  : 설계 과정 부산물·고객 원자료·확정기록 원문. 생성·수정·삭제·이동을 전부
  차단한다(읽기는 허용). 정본: design/README.md·design/schema/00-authoring-rules.md.
- 생성물(GENERATED_FILES) : design/wiki/handover/*.md 4종 + design/schema/generators/openapi/
  ui-요구목록*.md — 손으로 고치면 다음 재생성 때 덮여 사라지고, 그 사이엔 "손으로 고친 값"이
  정본처럼 읽힌다(2026-08-18 커버리지 게이트 거짓 초록 사고). Write/Edit/NotebookEdit·Bash로
  직접 건드리는 것을 막는다 — 항상 해당 생성 스크립트를 다시 돌려서 만든다.

  ⚠ 생성 스크립트 자신(예: build-screen-progress.py)은 이 훅에 걸리지 않는다 — 스크립트가
  Python 내부에서 open()으로 파일을 쓰는 것은 Claude의 Write/Edit 도구도, 아래 Bash 명령
  휴리스틱(리다이렉션·sed -i 등 셸 레벨 쓰기 패턴 탐지)도 거치지 않기 때문이다. 의도된 예외다.

이 파일은 docs/.claude/hooks/protect_readonly.py(구 문서 하네스, docs/raw·docs/planning/versions
보호용)를 원본으로 복사해 이 저장소(design/ 3층 구조) 대상으로 재배선한 것이다. 원본은 그대로
두고 손대지 않는다 — 이번 재구성 범위 밖.

Bash 검사는 휴리스틱 안전망이며 완전한 샌드박스가 아니다.
종료 코드: 0 통과, 2 차단(stderr가 Claude에게 전달됨).
"""
import json
import os
import re
import shlex
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT / "design" / "raw"

# 생성물 — design/wiki/handover/*.md 4종
# ⚠ settings.json 의 deny 는 Write/Edit 만 막는다 — Bash 리다이렉션은 이 목록이 막는다.
#   변경-요약.md 가 빠져 있던 동안(2026-09-03) 그 경로로 실제 오염이 났다.
GENERATED_RELS = {
    Path("design/wiki/handover/화면-진도표.md"),
    Path("design/wiki/handover/미결-대장.md"),
    Path("design/wiki/handover/99-인계대장.md"),
    Path("design/wiki/handover/변경-요약.md"),
}
# 생성물 — design/schema/generators/openapi/ui-요구목록*.md (도메인별 파생 파일 + 총괄본)
GENERATED_GLOB_DIR = Path("design/schema/generators/openapi")
GENERATED_GLOB_PREFIX = "ui-요구목록"

RAW_MSG = (
    "차단됨: design/raw/ 는 읽기 전용 원자료입니다. 생성·수정·삭제·이동할 수 없습니다. "
    "원자료를 정리한 결과는 design/wiki/에 새 문서로 작성하세요. "
    "design/raw/에 파일을 추가하는 것은 사용자가 직접 합니다."
)
GEN_MSG = (
    "차단됨: 이 파일은 스크립트가 만드는 생성물입니다. 손으로 고치면 다음 재생성 때 사라지고, "
    "그 사이엔 손으로 고친 값이 정본처럼 읽힙니다. design/schema/generators/의 해당 스크립트를 "
    "다시 돌려서 갱신하세요."
)

DELETE_VERBS = {"rm", "rmdir", "unlink", "shred", "trash"}
CREATE_VERBS = {"touch", "mkdir", "truncate", "chmod", "chown", "install"}
COPY_VERBS = {"cp", "rsync", "ditto", "ln"}
WRAPPERS = {"sudo", "command", "nohup", "nice", "env", "time", "xargs", "caffeinate"}
DANGEROUS_EXEC = DELETE_VERBS | CREATE_VERBS | {"mv", "sed", "tee", "sh", "bash", "zsh"}
# 대상 경로를 플래그로 받는 명령들 (tar -C, unzip -d, curl -o, wget -O/-P, sort -o, dd)
DEST_FLAG_VERBS = {"tar", "bsdtar", "unzip", "7z", "7za", "wget", "curl", "aria2c", "sort", "dd"}
DEST_FLAGS = {"-o", "-O", "-P", "-C", "-d", "--output", "--output-document", "--directory-prefix"}


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def resolve(token, cwd):
    """토큰을 절대 경로로 해석한다. 경로로 볼 수 없으면 None."""
    token = token.strip("'\"")
    if not token or token.startswith("-"):
        return None
    try:
        p = Path(os.path.expanduser(token))
        if not p.is_absolute():
            p = Path(cwd) / p
        return Path(os.path.realpath(str(p)))
    except (OSError, ValueError):
        return None


def is_under(p, d):
    return p == d or d in p.parents


def hits_raw(p):
    return p is not None and is_under(p, RAW_DIR)


def contains_raw(p):
    """p가 raw/의 상위인 경우 (예: 프로젝트 루트 전체 삭제)."""
    return p is not None and is_under(RAW_DIR, p)


def is_generated(p):
    if p is None:
        return False
    try:
        rel = p.relative_to(PROJECT)
    except ValueError:
        return False
    if rel in GENERATED_RELS:
        return True
    if rel.parent == GENERATED_GLOB_DIR and rel.name.startswith(GENERATED_GLOB_PREFIX) and rel.suffix == ".md":
        return True
    return False


def exists(p):
    return p is not None and p.exists()


def check_file_tool(tool, tool_input, cwd):
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not path:
        return
    p = resolve(path, cwd)
    if hits_raw(p):
        fail(RAW_MSG)
    if is_generated(p):
        fail(GEN_MSG)


def split_segments(cmd):
    return [s for s in re.split(r"\|\||&&|[;|&\n]", cmd) if s.strip()]


def tokenize(seg):
    try:
        return shlex.split(seg, posix=True)
    except ValueError:
        return seg.split()


def check_bash(cmd, cwd):
    # 1) 리다이렉션 대상 (> design/raw/x, >> design/wiki/handover/화면-진도표.md ...)
    for m in re.finditer(r"\d?>{1,2}\s*([^\s;|&<>]+)", cmd):
        t = resolve(m.group(1), cwd)
        if hits_raw(t):
            fail(RAW_MSG)
        if is_generated(t):
            fail(GEN_MSG)

    # 2) 세그먼트별 명령 검사
    for seg in split_segments(cmd):
        toks = tokenize(seg)
        i = 0
        while i < len(toks) and (
            re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", toks[i]) or toks[i] in WRAPPERS
        ):
            i += 1
        if i >= len(toks):
            continue
        verb = Path(toks[i]).name
        args = toks[i + 1:]
        resolved = [resolve(a, cwd) for a in args]
        raw_args = [p for p in resolved if hits_raw(p)]
        gen_args = [p for p in resolved if is_generated(p)]
        raw_hit = bool(raw_args) or any(contains_raw(p) for p in resolved)
        gen_hit = bool(gen_args)

        if verb in DEST_FLAG_VERBS:
            for j, a in enumerate(args[:-1]):
                if a in DEST_FLAGS:
                    t = resolve(args[j + 1], cwd)
                    if hits_raw(t):
                        fail(RAW_MSG)
                    if is_generated(t):
                        fail(GEN_MSG)
            for a in args:
                if a.startswith("of="):
                    t = resolve(a[3:], cwd)
                    if hits_raw(t):
                        fail(RAW_MSG)
                    if is_generated(t):
                        fail(GEN_MSG)

        if verb in DELETE_VERBS:
            if raw_hit:
                fail(RAW_MSG)
            if gen_hit:
                fail(GEN_MSG)
        elif verb == "find":
            danger = "-delete" in args
            for flag in ("-exec", "-execdir", "-ok", "-okdir"):
                if flag in args:
                    k = args.index(flag)
                    sub = Path(args[k + 1]).name if k + 1 < len(args) else ""
                    if sub in DANGEROUS_EXEC:
                        danger = True
            if danger:
                if raw_hit:
                    fail(RAW_MSG)
                if gen_hit:
                    fail(GEN_MSG)
        elif verb == "mv":
            if raw_hit:
                fail(RAW_MSG)
            if gen_hit:
                fail(GEN_MSG)
        elif verb in COPY_VERBS:
            positional = [p for a, p in zip(args, resolved) if not a.startswith("-") and p is not None]
            last = positional[-1] if positional else None
            if hits_raw(last):
                fail(RAW_MSG)
            if is_generated(last):
                fail(GEN_MSG)
        elif verb in CREATE_VERBS or verb == "tee" or (
            verb in {"sed", "perl"} and any(a == "-i" or a.startswith("-i") for a in args)
        ):
            if raw_args:
                fail(RAW_MSG)
            if gen_args:
                fail(GEN_MSG)


def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name") or ""
    tool_input = data.get("tool_input") or {}
    cwd = data.get("cwd") or os.getcwd()
    if tool == "Bash":
        check_bash(tool_input.get("command") or "", cwd)
    elif tool in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
        check_file_tool(tool, tool_input, cwd)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # 훅 버그가 세션 전체를 막지 않도록 비차단 오류로 처리
        print("protect_readonly 훅 오류: {}".format(exc), file=sys.stderr)
        sys.exit(1)
