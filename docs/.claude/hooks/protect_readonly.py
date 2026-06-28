#!/usr/bin/env python3
"""PreToolUse 훅: 읽기 전용 영역 보호.

- raw/                  : 외부 원본 자료. 생성·수정·삭제·이동을 전부 차단한다 (읽기는 허용).
- planning/**/versions/ : 확정 버전 스냅샷. 기존 파일의 수정·삭제를 차단한다 (새 스냅샷 생성은 허용).

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
RAW_DIR = PROJECT / "raw"
PLANNING_DIR = PROJECT / "planning"

RAW_MSG = (
    "차단됨: raw/ 는 읽기 전용 외부 참조 자료입니다. 생성·수정·삭제·이동할 수 없습니다. "
    "raw/ 자료를 정리한 결과는 research/에, 기획 내용은 planning/에 작성하세요. "
    "raw/에 파일을 추가하는 것은 사용자가 직접 합니다."
)
VER_MSG = (
    "차단됨: planning/versions/ 의 확정 스냅샷은 수정·삭제할 수 없습니다. "
    "변경은 작업본 문서에 하고, /snapshot 으로 새 버전 스냅샷을 만드세요."
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


def in_versions(p):
    if p is None:
        return False
    try:
        parts = p.relative_to(PROJECT).parts
    except ValueError:
        return False
    return len(parts) >= 2 and parts[0] == "planning" and "versions" in parts[1:]


def contains_versions(p):
    if p is None or not PLANNING_DIR.is_dir():
        return False
    try:
        if not p.is_dir():
            return False
    except OSError:
        return False
    vdirs = [d for d in PLANNING_DIR.rglob("versions") if d.is_dir()]
    return any(is_under(v, p) for v in vdirs)


def exists(p):
    return p is not None and p.exists()


def check_file_tool(tool, tool_input, cwd):
    path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not path:
        return
    p = resolve(path, cwd)
    if hits_raw(p):
        fail(RAW_MSG)
    if in_versions(p):
        if tool == "Write" and not exists(p):
            return  # 새 스냅샷 생성은 허용
        fail(VER_MSG)


def split_segments(cmd):
    return [s for s in re.split(r"\|\||&&|[;|&\n]", cmd) if s.strip()]


def tokenize(seg):
    try:
        return shlex.split(seg, posix=True)
    except ValueError:
        return seg.split()


def check_bash(cmd, cwd):
    # 1) 리다이렉션 대상 (> raw/x, >> planning/versions/x ...)
    for m in re.finditer(r"\d?>{1,2}\s*([^\s;|&<>]+)", cmd):
        t = resolve(m.group(1), cwd)
        if hits_raw(t):
            fail(RAW_MSG)
        if in_versions(t) and exists(t):
            fail(VER_MSG)

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
        ver_args = [p for p in resolved if in_versions(p)]
        raw_hit = bool(raw_args) or any(contains_raw(p) for p in resolved)
        ver_hit = bool(ver_args) or any(contains_versions(p) for p in resolved)

        if verb in DEST_FLAG_VERBS:
            for j, a in enumerate(args[:-1]):
                if a in DEST_FLAGS:
                    t = resolve(args[j + 1], cwd)
                    if hits_raw(t):
                        fail(RAW_MSG)
                    if in_versions(t) and exists(t):
                        fail(VER_MSG)
            for a in args:
                if a.startswith("of="):
                    t = resolve(a[3:], cwd)
                    if hits_raw(t):
                        fail(RAW_MSG)
                    if in_versions(t) and exists(t):
                        fail(VER_MSG)

        if verb in DELETE_VERBS:
            if raw_hit:
                fail(RAW_MSG)
            if ver_hit:
                fail(VER_MSG)
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
                if ver_hit:
                    fail(VER_MSG)
        elif verb == "mv":
            if raw_hit:
                fail(RAW_MSG)
            if ver_args:
                last = resolved[-1] if resolved else None
                src_in_versions = any(p in ver_args for p in resolved[:-1])
                if src_in_versions or (last is not None and last in ver_args and exists(last)):
                    fail(VER_MSG)
        elif verb in COPY_VERBS:
            positional = [p for a, p in zip(args, resolved) if not a.startswith("-") and p is not None]
            last = positional[-1] if positional else None
            if hits_raw(last):
                fail(RAW_MSG)
            if in_versions(last) and exists(last):
                fail(VER_MSG)
        elif verb in CREATE_VERBS or verb == "tee" or (
            verb in {"sed", "perl"} and any(a == "-i" or a.startswith("-i") for a in args)
        ):
            if raw_args:
                fail(RAW_MSG)
            if any(exists(p) for p in ver_args):
                fail(VER_MSG)


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
