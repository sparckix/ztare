#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/public/control/manual_console.sh claude
  scripts/public/control/manual_console.sh codex
  scripts/public/control/manual_console.sh docker-claude

Purpose:
  Open a direct interactive agent console in this repo without starting the
  role daemon, work discovery, gates, or the validator loop.

Modes:
  claude         Run local Claude Code CLI interactively in the repo.
  codex          Run local Codex CLI interactively in the repo.
  docker-claude  Run Claude Code inside the manual-console Docker profile.

This is the direct human-agent path. If the work changes durable repo state,
the agent is still expected to follow AGENTS.md closure discipline.
EOF
}

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
mode="${1:-}"

if [[ -z "${mode}" || "${mode}" == "-h" || "${mode}" == "--help" ]]; then
  usage
  exit 0
fi

cd "${repo_root}"

preflight() {
  local cli="$1"
  local missing=0
  for path in AGENTS.md docs/guides/org_runtime_quickstart.md docs/concepts/ztare_research_company_architecture.md; do
    if [[ ! -f "${path}" ]]; then
      echo "missing required context file: ${path}" >&2
      missing=1
    fi
  done
  if ! command -v "${cli}" >/dev/null 2>&1; then
    echo "agent CLI not found on PATH: ${cli}" >&2
    missing=1
  fi
  if [[ "${missing}" != "0" ]]; then
    exit 1
  fi
}

banner() {
  local cli="$1"
  cat <<EOF
ZTARE manual console
repo: ${repo_root}
agent: ${cli}

This starts no daemon and runs no validator loop.
The agent should read AGENTS.md, then use the direct-console lane unless asked
to enter the org runtime or ZTARE validator path.

EOF
}

case "${mode}" in
  claude)
    preflight claude
    banner claude
    exec claude
    ;;
  codex)
    preflight codex
    banner codex
    exec codex
    ;;
  docker-claude)
    banner "docker:manual-claude"
    if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
      exec docker compose --profile console run --rm operator-claude
    fi
    if command -v docker-compose >/dev/null 2>&1; then
      exec docker-compose --profile console run --rm operator-claude
    fi
    echo "Docker Compose is not available. Install Docker Desktop or the Docker Compose plugin." >&2
    exit 1
    ;;
  *)
    usage
    exit 2
    ;;
esac
