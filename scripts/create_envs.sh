#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

DIFFSINGER_DIR="${DIFFSINGER_DIR:-${REPO_ROOT}/tools/DiffSinger}"
SOME_DIR="${SOME_DIR:-${REPO_ROOT}/tools/SOME}"

DIFFSINGER_ENV_NAME="${DIFFSINGER_ENV_NAME:-myvb-diffsinger}"
SOME_ENV_NAME="${SOME_ENV_NAME:-myvb-some}"
MFA_ENV_NAME="${MFA_ENV_NAME:-myvb-mfa}"
PYTHON_VERSION="${PYTHON_VERSION:-3.10}"

TORCH_PACKAGE_SPEC="${TORCH_PACKAGE_SPEC:-torch>=2.1}"
TORCHAUDIO_PACKAGE_SPEC="${TORCHAUDIO_PACKAGE_SPEC:-torchaudio>=2.1}"
TORCH_INDEX_URL="${TORCH_INDEX_URL:-}"
DIFFSINGER_TORCH_INDEX_URL="${DIFFSINGER_TORCH_INDEX_URL:-${TORCH_INDEX_URL}}"
SOME_TORCH_INDEX_URL="${SOME_TORCH_INDEX_URL:-${TORCH_INDEX_URL}}"
INSTALL_TOOL_REQUIREMENTS="${INSTALL_TOOL_REQUIREMENTS:-1}"
DEFAULT_PIP_SPEC="${DEFAULT_PIP_SPEC:-pip}"
DEFAULT_SETUPTOOLS_SPEC="${DEFAULT_SETUPTOOLS_SPEC:-setuptools<81}"
DEFAULT_WHEEL_SPEC="${DEFAULT_WHEEL_SPEC:-wheel}"
SOME_PIP_SPEC="${SOME_PIP_SPEC:-pip<24.1}"
SOME_SETUPTOOLS_SPEC="${SOME_SETUPTOOLS_SPEC:-setuptools<81}"
SOME_WHEEL_SPEC="${SOME_WHEEL_SPEC:-wheel}"

log() {
  printf '[envs] %s\n' "$*"
}

fail() {
  printf '[envs] ERROR: %s\n' "$*" >&2
  exit 1
}

pick_conda_cmd() {
  local candidate
  for candidate in micromamba mamba conda; do
    if command -v "$candidate" >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

CONDA_CMD="$(pick_conda_cmd)" || fail "Install micromamba, mamba, or conda before running this script."

require_file() {
  [[ -f "$1" ]] || fail "Missing expected file: $1"
}

env_exists() {
  "$CONDA_CMD" run -n "$1" python -c "import sys" >/dev/null 2>&1
}

create_python_env() {
  local name="$1"

  if env_exists "$name"; then
    log "Skipping ${name}; environment already exists."
    return 0
  fi

  log "Creating Python ${PYTHON_VERSION} environment: ${name}"
  "$CONDA_CMD" create -y -n "$name" "python=${PYTHON_VERSION}" pip
}

upgrade_pip_stack() {
  local env_name="$1"
  shift
  local pip_specs=("$@")
  log "Upgrading pip/setuptools/wheel in ${env_name}"
  "$CONDA_CMD" run -n "$env_name" python -m pip install --upgrade "${pip_specs[@]}"
}

install_torch_stack() {
  local env_name="$1"
  local index_url="$2"
  local install_cmd=(python -m pip install)

  if [[ -n "$index_url" ]]; then
    install_cmd+=(--index-url "$index_url")
  fi

  install_cmd+=("$TORCH_PACKAGE_SPEC" "$TORCHAUDIO_PACKAGE_SPEC")

  log "Installing PyTorch stack in ${env_name}"
  "$CONDA_CMD" run -n "$env_name" "${install_cmd[@]}"
}

install_requirements() {
  local env_name="$1"
  local requirements_file="$2"

  log "Installing requirements from ${requirements_file} into ${env_name}"
  "$CONDA_CMD" run -n "$env_name" python -m pip install -r "$requirements_file"
}

create_mfa_env() {
  if env_exists "$MFA_ENV_NAME"; then
    log "Skipping ${MFA_ENV_NAME}; environment already exists."
    return 0
  fi

  log "Creating MFA environment: ${MFA_ENV_NAME}"
  "$CONDA_CMD" create -y -n "$MFA_ENV_NAME" -c conda-forge montreal-forced-aligner
}

main() {
  if [[ "$INSTALL_TOOL_REQUIREMENTS" == "1" ]]; then
    require_file "${DIFFSINGER_DIR}/requirements.txt"
    require_file "${SOME_DIR}/requirements.txt"
  fi

  create_python_env "$DIFFSINGER_ENV_NAME"
  upgrade_pip_stack \
    "$DIFFSINGER_ENV_NAME" \
    "$DEFAULT_PIP_SPEC" \
    "$DEFAULT_SETUPTOOLS_SPEC" \
    "$DEFAULT_WHEEL_SPEC"
  install_torch_stack "$DIFFSINGER_ENV_NAME" "$DIFFSINGER_TORCH_INDEX_URL"
  if [[ "$INSTALL_TOOL_REQUIREMENTS" == "1" ]]; then
    install_requirements "$DIFFSINGER_ENV_NAME" "${DIFFSINGER_DIR}/requirements.txt"
  fi

  create_python_env "$SOME_ENV_NAME"
  # fairseq 0.12.x depends on older omegaconf metadata rejected by newer pip.
  upgrade_pip_stack \
    "$SOME_ENV_NAME" \
    "$SOME_PIP_SPEC" \
    "$SOME_SETUPTOOLS_SPEC" \
    "$SOME_WHEEL_SPEC"
  install_torch_stack "$SOME_ENV_NAME" "$SOME_TORCH_INDEX_URL"
  if [[ "$INSTALL_TOOL_REQUIREMENTS" == "1" ]]; then
    install_requirements "$SOME_ENV_NAME" "${SOME_DIR}/requirements.txt"
  fi

  create_mfa_env

  log "Environment setup complete."
  log "DiffSinger env: ${DIFFSINGER_ENV_NAME}"
  log "SOME env: ${SOME_ENV_NAME}"
  log "MFA env: ${MFA_ENV_NAME}"
}

main "$@"
