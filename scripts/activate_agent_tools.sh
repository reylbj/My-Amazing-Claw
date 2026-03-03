#!/usr/bin/env bash
# Activate Python 3.11 agent tools environment and run quick checks.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${WORKSPACE_DIR}/.venv-agent-tools"

usage() {
  cat <<'EOF'
Usage:
  source scripts/activate_agent_tools.sh
  bash scripts/activate_agent_tools.sh --check
  bash scripts/activate_agent_tools.sh --doctor
  bash scripts/activate_agent_tools.sh --run "python --version && agent-reach doctor"

Notes:
  - Use `source ...` if you want to keep the venv activated in your current shell.
  - Use `--run` if you only want to run one command in the venv.
EOF
}

ensure_venv() {
  if [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
    echo "[agent-tools][error] venv not found: ${VENV_DIR}" >&2
    echo "Please rebuild it first." >&2
    exit 1
  fi
}

activate_env() {
  # shellcheck disable=SC1090
  source "${VENV_DIR}/bin/activate"
}

run_check() {
  python --version
  command -v xreach >/dev/null 2>&1 && xreach --version
  command -v x-reader >/dev/null 2>&1 && x-reader | sed -n '1,20p'
  command -v agent-reach >/dev/null 2>&1 && agent-reach version
}

run_doctor() {
  agent-reach doctor
}

main() {
  ensure_venv

  case "${1:-}" in
    --check)
      activate_env
      run_check
      ;;
    --doctor)
      activate_env
      run_doctor
      ;;
    --run)
      shift
      [[ -n "${1:-}" ]] || { usage; exit 1; }
      activate_env
      eval "$1"
      ;;
    -h|--help|help)
      usage
      ;;
    "")
      usage
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

# If sourced: just activate and print python version.
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
  ensure_venv
  activate_env
  python --version
else
  main "$@"
fi
