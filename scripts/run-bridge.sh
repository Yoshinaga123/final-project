#!/usr/bin/env bash
set -euo pipefail

# Simple Linux launcher for the USI WebSocket bridge
# Reads environment variables (from .env if you export them) and starts the bridge.
#
# Required:
#   USI_ENGINE_PATH  Path to the USI engine binary (e.g., YaneuraOu)
# Optional:
#   USI_BRIDGE_HOST  Default 127.0.0.1
#   USI_BRIDGE_PORT  Default 8787
#   USI_BRIDGE_TOKEN Optional token to require on WS URL
#   PYTHON_EXE       Python to use (default: python)
#
# Usage:
#   1) Ensure the engine is built and executable (chmod +x /path/to/engine)
#   2) Export envs or put them in .env and `export $(grep -v '^#' .env | xargs)`
#   3) ./scripts/run-bridge.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Auto-load .env if present (export everything declared there)
if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ROOT_DIR}/.env"
  set +a
fi
ENGINE="${USI_ENGINE_PATH:-}"
HOST="${USI_BRIDGE_HOST:-127.0.0.1}"
PORT="${USI_BRIDGE_PORT:-8787}"
TOKEN="${USI_BRIDGE_TOKEN:-}"
PY="${PYTHON_EXE:-python}"

if [[ -z "${ENGINE}" ]]; then
  echo "ERROR: USI_ENGINE_PATH is not set. Set it in .env or export it." >&2
  exit 1
fi
# If a directory is given, try to auto-detect an engine binary inside
if [[ -d "${ENGINE}" ]]; then
  for cand in AVX2 AVX YaneuraOu-by-gcc YaneuraOu YaneuraOu*; do
    if [[ -x "${ENGINE}/${cand}" ]]; then
      ENGINE="${ENGINE}/${cand}"
      break
    fi
  done
fi

if [[ ! -x "${ENGINE}" ]]; then
  echo "ERROR: Engine binary not executable: ${ENGINE}" >&2
  echo "Hint: set USI_ENGINE_PATH to the engine file or a directory containing it (e.g., .../source/AVX2), then ensure chmod +x." >&2
  exit 1
fi

cd "${ROOT_DIR}"
ARGS=("${ENGINE}" "${PORT}" "--host" "${HOST}")
if [[ -n "${TOKEN}" ]]; then ARGS+=("--token" "${TOKEN}"); fi

exec "${PY}" tools/usi-bridge.py "${ARGS[@]}"
