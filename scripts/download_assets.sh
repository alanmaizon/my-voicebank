#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

GITHUB_API_URL="${GITHUB_API_URL:-https://api.github.com}"

VOCODER_REPO="${VOCODER_REPO:-openvpi/vocoders}"
VOCODER_TAG="${VOCODER_TAG:-pc-nsf-hifigan-44.1k-hop512-128bin-2025.02}"
VOCODER_ASSET_NAME="${VOCODER_ASSET_NAME:-}"
VOCODER_ASSET_PATTERN="${VOCODER_ASSET_PATTERN:-pc|nsf|hifigan|vocoder|diffsinger}"
VOCODER_EXCLUDE_PATTERN="${VOCODER_EXCLUDE_PATTERN:-oudep|onnx|openutau}"
VOCODER_DIR="${VOCODER_DIR:-${REPO_ROOT}/models/vocoder/openvpi}"

DOWNLOAD_SOME_MODEL="${DOWNLOAD_SOME_MODEL:-0}"
SOME_MODEL_REPO="${SOME_MODEL_REPO:-openvpi/SOME}"
SOME_MODEL_TAG="${SOME_MODEL_TAG:-v0.0.1}"
SOME_MODEL_ASSET_NAME="${SOME_MODEL_ASSET_NAME:-}"
SOME_MODEL_ASSET_PATTERN="${SOME_MODEL_ASSET_PATTERN:-ckpt|checkpoint|model|pretrain|pretrained|zip|tar}"
SOME_MODEL_EXCLUDE_PATTERN="${SOME_MODEL_EXCLUDE_PATTERN:-windows|darwin|macos|linux-x64|source|\.7z$}"
SOME_MODEL_DIR="${SOME_MODEL_DIR:-${REPO_ROOT}/models/some}"

DOWNLOAD_RMVPE="${DOWNLOAD_RMVPE:-0}"
RMVPE_REPO="${RMVPE_REPO:-yxlllc/RMVPE}"
RMVPE_TAG="${RMVPE_TAG:-latest}"
RMVPE_ASSET_NAME="${RMVPE_ASSET_NAME:-}"
RMVPE_ASSET_PATTERN="${RMVPE_ASSET_PATTERN:-rmvpe(\.pt|\.zip)$}"
RMVPE_EXCLUDE_PATTERN="${RMVPE_EXCLUDE_PATTERN:-}"
RMVPE_DIR="${RMVPE_DIR:-${REPO_ROOT}/tools/SOME/pretrained}"

EXTRACT_ARCHIVES="${EXTRACT_ARCHIVES:-1}"
OVERWRITE="${OVERWRITE:-0}"

log() {
  printf '[assets] %s\n' "$*"
}

fail() {
  printf '[assets] ERROR: %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

api_url_for_release() {
  local repo="$1"
  local tag="$2"

  if [[ "$tag" == "latest" ]]; then
    printf '%s/repos/%s/releases/latest\n' "$GITHUB_API_URL" "$repo"
  else
    printf '%s/repos/%s/releases/tags/%s\n' "$GITHUB_API_URL" "$repo" "$tag"
  fi
}

fetch_release_json() {
  local repo="$1"
  local tag="$2"
  local url

  url="$(api_url_for_release "$repo" "$tag")"
  curl -fsSL \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$url"
}

select_asset() {
  local release_json="$1"
  local exact_name="$2"
  local include_pattern="$3"
  local exclude_pattern="$4"

  RELEASE_JSON="$release_json" python3 - "$exact_name" "$include_pattern" "$exclude_pattern" <<'PY'
import json
import os
import re
import sys

exact_name, include_pattern, exclude_pattern = sys.argv[1:4]
release = json.loads(os.environ["RELEASE_JSON"])
assets = release.get("assets") or []

if not assets:
    raise SystemExit("Release has no downloadable assets.")

def matches(pattern: str, text: str) -> bool:
    if not pattern:
        return True
    return re.search(pattern, text, re.IGNORECASE) is not None

available_names = [asset.get("name", "") for asset in assets]

if exact_name:
    candidates = [asset for asset in assets if asset.get("name") == exact_name]
    if not candidates:
        raise SystemExit(
            "Requested asset was not found. Available assets: "
            + ", ".join(sorted(filter(None, available_names)))
        )
else:
    candidates = [
        asset for asset in assets
        if matches(include_pattern, asset.get("name", ""))
    ]
    if exclude_pattern:
        candidates = [
            asset for asset in candidates
            if not matches(exclude_pattern, asset.get("name", ""))
        ]
    if not candidates:
        candidates = assets
        if exclude_pattern:
            candidates = [
                asset for asset in candidates
                if not matches(exclude_pattern, asset.get("name", ""))
            ]
    if not candidates:
        raise SystemExit(
            "No assets matched the current filters. Available assets: "
            + ", ".join(sorted(filter(None, available_names)))
        )

priority_tokens = (
    "diffsinger",
    "inference",
    "pretrained",
    "pretrain",
    "model",
    "checkpoint",
    "ckpt",
    "pth",
    "pt",
    "zip",
    "tar",
)

def sort_key(asset):
    name = asset.get("name", "").lower()
    rank = 100
    for index, token in enumerate(priority_tokens):
        if token in name:
            rank = index
            break
    return (rank, len(name), name)

chosen = sorted(candidates, key=sort_key)[0]
print(chosen["name"])
print(chosen["browser_download_url"])
print(release.get("tag_name", ""))
print(release.get("html_url", ""))
PY
}

extract_archive() {
  local archive_path="$1"
  local destination_dir="$2"

  mkdir -p "$destination_dir"

  case "$archive_path" in
    *.zip)
      if command -v unzip >/dev/null 2>&1; then
        unzip -o "$archive_path" -d "$destination_dir" >/dev/null
      else
        python3 -m zipfile -e "$archive_path" "$destination_dir"
      fi
      ;;
    *.tar.gz|*.tgz)
      tar -xzf "$archive_path" -C "$destination_dir"
      ;;
    *.tar.xz)
      tar -xJf "$archive_path" -C "$destination_dir"
      ;;
    *.7z)
      if command -v 7z >/dev/null 2>&1; then
        7z x -y "-o${destination_dir}" "$archive_path" >/dev/null
      else
        log "Skipping extraction for ${archive_path}; install 7z to unpack it."
      fi
      ;;
  esac
}

write_manifest() {
  local manifest_path="$1"
  local repo="$2"
  local tag="$3"
  local release_url="$4"
  local asset_name="$5"
  local asset_url="$6"

  cat >"$manifest_path" <<EOF
repo=${repo}
tag=${tag}
release_url=${release_url}
asset_name=${asset_name}
asset_url=${asset_url}
downloaded_at_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF
}

download_release_asset() {
  local label="$1"
  local repo="$2"
  local tag="$3"
  local exact_name="$4"
  local include_pattern="$5"
  local exclude_pattern="$6"
  local destination_dir="$7"
  local release_json selection asset_name asset_url resolved_tag release_url destination_path manifest_path

  mkdir -p "$destination_dir"

  log "Resolving ${label} asset from ${repo} (${tag})"
  release_json="$(fetch_release_json "$repo" "$tag")"
  selection="$(select_asset "$release_json" "$exact_name" "$include_pattern" "$exclude_pattern")"

  asset_name="$(printf '%s\n' "$selection" | sed -n '1p')"
  asset_url="$(printf '%s\n' "$selection" | sed -n '2p')"
  resolved_tag="$(printf '%s\n' "$selection" | sed -n '3p')"
  release_url="$(printf '%s\n' "$selection" | sed -n '4p')"

  destination_path="${destination_dir}/${asset_name}"
  manifest_path="${destination_path}.source.txt"

  if [[ -f "$destination_path" && "$OVERWRITE" != "1" ]]; then
    log "Skipping download for ${label}; asset already exists at ${destination_path}"
  else
    log "Downloading ${label} asset ${asset_name}"
    curl -fL --retry 3 --output "$destination_path" "$asset_url"
  fi

  write_manifest "$manifest_path" "$repo" "$resolved_tag" "$release_url" "$asset_name" "$asset_url"

  if [[ "$EXTRACT_ARCHIVES" == "1" ]]; then
    extract_archive "$destination_path" "$destination_dir"
  fi
}

main() {
  require_cmd curl
  require_cmd python3
  require_cmd sed

  download_release_asset \
    "OpenVPI vocoder" \
    "$VOCODER_REPO" \
    "$VOCODER_TAG" \
    "$VOCODER_ASSET_NAME" \
    "$VOCODER_ASSET_PATTERN" \
    "$VOCODER_EXCLUDE_PATTERN" \
    "$VOCODER_DIR"

  if [[ "$DOWNLOAD_SOME_MODEL" == "1" ]]; then
    download_release_asset \
      "SOME checkpoint" \
      "$SOME_MODEL_REPO" \
      "$SOME_MODEL_TAG" \
      "$SOME_MODEL_ASSET_NAME" \
      "$SOME_MODEL_ASSET_PATTERN" \
      "$SOME_MODEL_EXCLUDE_PATTERN" \
      "$SOME_MODEL_DIR"
  else
    log "Skipping SOME checkpoint because DOWNLOAD_SOME_MODEL=${DOWNLOAD_SOME_MODEL}"
  fi

  if [[ "$DOWNLOAD_RMVPE" == "1" ]]; then
    download_release_asset \
      "RMVPE model" \
      "$RMVPE_REPO" \
      "$RMVPE_TAG" \
      "$RMVPE_ASSET_NAME" \
      "$RMVPE_ASSET_PATTERN" \
      "$RMVPE_EXCLUDE_PATTERN" \
      "$RMVPE_DIR"
  else
    log "Skipping RMVPE because DOWNLOAD_RMVPE=${DOWNLOAD_RMVPE}"
  fi

  log "Asset download step complete."
}

main "$@"
