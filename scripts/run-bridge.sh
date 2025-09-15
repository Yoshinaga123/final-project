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
SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_MOCK="${SCRIPT_DIR}/../tools/mock_engine/mock_usi.py"

# Auto-load .env if present (export everything declared there)
if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ROOT_DIR}/.env"
  set +a
fi
ENGINE="${1:-${USI_ENGINE_PATH:-}}"
HOST="${USI_BRIDGE_HOST:-127.0.0.1}"
PORT="${USI_BRIDGE_PORT:-8787}"
TOKEN="${USI_BRIDGE_TOKEN:-}"
PY="${PYTHON_EXE:-python}"

if [[ -z "${ENGINE}" ]]; then
  # In production, do not allow silent fallback
  if [[ "${APP_ENV:-}" == "production" ]]; then
    echo "ENGINE_REQUIRED_IN_PROD: set -Engine arg or USI_ENGINE_PATH" >&2
    exit 3
  fi
  if [[ -f "${DEFAULT_MOCK}" ]]; then
    echo "[run-bridge.sh] USI_ENGINE_PATH not set; using mock engine: ${DEFAULT_MOCK}" >&2
    ENGINE="${DEFAULT_MOCK}"
  else
    echo "MOCK_ENGINE_MISSING: ${DEFAULT_MOCK}" >&2
    exit 4
  fi
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

if [[ -f "${ENGINE}" ]]; then
  # Allow Python scripts even if not executable; usi-bridge.py will run them via the current interpreter
  if [[ -x "${ENGINE}" || "${ENGINE}" == *.py ]]; then
    : # ok
  else
    echo "ENGINE_NOT_EXECUTABLE: ${ENGINE}" >&2
    echo "Hint: either 'chmod +x' the engine binary, or point USI_ENGINE_PATH to a .py engine script (allowed without +x)." >&2
    exit 2
  fi
else
  echo "ERROR: Engine path not found: ${ENGINE}" >&2
  exit 1
fi

cd "${ROOT_DIR}"
ARGS=("${ENGINE}" "${PORT}" "--host" "${HOST}")
if [[ -n "${TOKEN}" ]]; then ARGS+=("--token" "${TOKEN}"); fi
# Friendly startup log
echo "[run-bridge.sh] Starting USI bridge"
echo "  Engine: ${ENGINE}"
echo "  Listen: ws://${HOST}:${PORT}/ws"
if [[ -n "${TOKEN}" ]]; then echo "  Token : (set)"; else echo "  Token : (none)"; fi

exec "${PY}" tools/usi-bridge.py "${ARGS[@]}"
