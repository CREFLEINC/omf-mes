#!/usr/bin/env bash
# 설계팀 3역할(Consultant/Architect/Caster) 워크트리를 준비한다.
#
# 이 스크립트는 "설계팀 프로젝트를 새로 클론받은 로컬 환경에서 처음 개발환경을 설정할 때"
# 실행되는 절차다(multi-agent-team-workflow-v3-design-team-structure.md 「설계팀 시작하기」
# §2) — 저장소 하나를 손으로 한 번만 세팅해두는 게 아니라, 클론할 때마다 다시 실행되는 게
# 정상이다. 멱등하게 짰다: 이미 있는 워크트리는 재생성하지 않고 최신 상태로만 갱신한다.
#
# 사용법:
#   .claude/scripts/setup-team-worktrees.sh [consultant|architect|caster|all]
#   인자를 생략하면 all과 동일 — "명시하지 않으면 3가지 역할을 위한 모든 준비를 한다"(원문).
#
# 세 역할이 보는 자료 상태가 다르다(각자의 워크트리 안에서만 유효):
#   consultant : 가장 최근 설계 변동 공지(notice/* 태그)로 디태치드 체크아웃.
#   architect  : main에서 분기한 작업 브랜치 — 자유롭게 커밋·PR.
#   caster     : origin/main 최신(배포 브랜치)으로 디태치드 체크아웃.

set -euo pipefail

ROLE="${1:-all}"

MAIN_ROOT="$(git worktree list --porcelain | awk '/^worktree /{print $2; exit}')"
if [ -z "$MAIN_ROOT" ]; then
  echo "git 저장소 안에서 실행하세요 (git worktree list 가 비었습니다)." >&2
  exit 1
fi

WORKTREES_DIR="$MAIN_ROOT/.claude/worktrees"
mkdir -p "$WORKTREES_DIR"

worktree_exists() {
  git -C "$MAIN_ROOT" worktree list --porcelain | grep -qx "worktree $1"
}

copy_local_settings() {
  local dest="$1"
  if [ -f "$MAIN_ROOT/.claude/settings.local.json" ]; then
    mkdir -p "$dest/.claude"
    cp "$MAIN_ROOT/.claude/settings.local.json" "$dest/.claude/settings.local.json"
    echo "  settings.local.json 복제 (git이 자동으로 동반하지 않는 유일한 관련 파일)"
  fi
}

setup_consultant() {
  local path="$WORKTREES_DIR/consultant"
  local latest_tag
  latest_tag="$(git -C "$MAIN_ROOT" tag -l 'notice/*' --sort=-creatordate | head -1)"
  if [ -z "$latest_tag" ]; then
    echo "[consultant] 발행된 notice/* 태그가 아직 없습니다 — origin/main으로 대신 체크아웃합니다." >&2
    git -C "$MAIN_ROOT" fetch origin main --quiet
    latest_tag="origin/main"
  fi
  if worktree_exists "$path"; then
    echo "[consultant] 기존 워크트리를 최신 공지 태그($latest_tag)로 갱신"
    git -C "$path" checkout --detach "$latest_tag" --quiet
  else
    echo "[consultant] 워크트리 생성 — 최신 공지 태그($latest_tag), 디태치드 HEAD"
    git -C "$MAIN_ROOT" worktree add --detach "$path" "$latest_tag"
  fi
  copy_local_settings "$path"
  echo "  과거 버전 열람은 체크아웃을 바꾸지 말고 'git show <tag>:<path>'를 쓴다."
}

setup_architect() {
  local path="$WORKTREES_DIR/architect"
  if worktree_exists "$path"; then
    echo "[architect] 기존 워크트리를 건드리지 않음 (진행 중인 작업을 덮어쓰지 않는다)"
  else
    echo "[architect] 워크트리 생성 — main에서 분기한 작업 브랜치 'architect-work'"
    git -C "$MAIN_ROOT" fetch origin main --quiet
    git -C "$MAIN_ROOT" worktree add "$path" -b architect-work origin/main
  fi
  copy_local_settings "$path"
}

setup_caster() {
  local path="$WORKTREES_DIR/caster"
  git -C "$MAIN_ROOT" fetch origin main --quiet
  if worktree_exists "$path"; then
    echo "[caster] 기존 워크트리를 origin/main 최신으로 갱신"
    git -C "$path" checkout --detach origin/main --quiet
  else
    echo "[caster] 워크트리 생성 — origin/main(배포 브랜치), 디태치드 HEAD"
    git -C "$MAIN_ROOT" worktree add --detach "$path" origin/main
  fi
  copy_local_settings "$path"
}

case "$ROLE" in
  consultant) setup_consultant ;;
  architect)  setup_architect ;;
  caster)     setup_caster ;;
  all)
    setup_consultant
    setup_architect
    setup_caster
    ;;
  *)
    echo "알 수 없는 역할: $ROLE (consultant|architect|caster|all 중 하나)" >&2
    exit 1
    ;;
esac

echo
echo "완료. 현재 워크트리:"
git -C "$MAIN_ROOT" worktree list
