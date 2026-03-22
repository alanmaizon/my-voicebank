#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
TOOLS_DIR="${TOOLS_DIR:-${REPO_ROOT}/tools}"

DIFFSINGER_REPO="${DIFFSINGER_REPO:-https://github.com/openvpi/DiffSinger.git}"
MAKEDIFFSINGER_REPO="${MAKEDIFFSINGER_REPO:-https://github.com/openvpi/MakeDiffSinger.git}"
SOME_REPO="${SOME_REPO:-https://github.com/openvpi/SOME.git}"
AUDIO_SLICER_REPO="${AUDIO_SLICER_REPO:-https://github.com/openvpi/audio-slicer.git}"

CLONE_AUDIO_SLICER="${CLONE_AUDIO_SLICER:-1}"
GIT_DEPTH="${GIT_DEPTH:-1}"
PULL_IF_EXISTS="${PULL_IF_EXISTS:-0}"

log() {
  printf '[bootstrap] %s\n' "$*"
}

fail() {
  printf '[bootstrap] ERROR: %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

has_non_placeholder_contents() {
  local dir="$1"
  find "$dir" -mindepth 1 ! -name '.gitkeep' -print -quit | grep -q .
}

prepare_clone_target() {
  local dir="$1"

  if [[ -d "${dir}/.git" ]]; then
    return 0
  fi

  if [[ -d "$dir" ]]; then
    if has_non_placeholder_contents "$dir"; then
      fail "Refusing to clone into non-empty directory: $dir"
    fi
    rm -f "${dir}/.gitkeep"
    rmdir "$dir" 2>/dev/null || true
  fi
}

clone_repo() {
  local label="$1"
  local url="$2"
  local dir="$3"
  local clone_cmd

  if [[ -d "${dir}/.git" ]]; then
    if [[ "$PULL_IF_EXISTS" == "1" ]]; then
      log "Updating ${label} in ${dir}"
      git -C "$dir" pull --ff-only
    else
      log "Skipping ${label}; repository already exists at ${dir}"
    fi
    return 0
  fi

  prepare_clone_target "$dir"
  mkdir -p "$(dirname -- "$dir")"

  clone_cmd=(git clone)
  if [[ "$GIT_DEPTH" =~ ^[0-9]+$ ]] && (( GIT_DEPTH > 0 )); then
    clone_cmd+=(--depth "$GIT_DEPTH")
  fi
  clone_cmd+=("$url" "$dir")

  log "Cloning ${label} from ${url}"
  "${clone_cmd[@]}"
}

main() {
  require_cmd git

  clone_repo "DiffSinger" "$DIFFSINGER_REPO" "${TOOLS_DIR}/DiffSinger"
  clone_repo "MakeDiffSinger" "$MAKEDIFFSINGER_REPO" "${TOOLS_DIR}/MakeDiffSinger"
  clone_repo "SOME" "$SOME_REPO" "${TOOLS_DIR}/SOME"

  if [[ "$CLONE_AUDIO_SLICER" == "1" ]]; then
    clone_repo "audio-slicer" "$AUDIO_SLICER_REPO" "${TOOLS_DIR}/audio-slicer"
  else
    log "Skipping audio-slicer because CLONE_AUDIO_SLICER=${CLONE_AUDIO_SLICER}"
  fi

  log "Bootstrap complete."
}

main "$@"
