#!/usr/bin/env bash
set -euo pipefail

IMAGE="${IMAGE:-ztare-public-smoke}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed or not on PATH." >&2
  exit 127
fi

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: docker daemon is not reachable." >&2
  exit 1
fi

docker build -t "$IMAGE" .

docker run --rm "$IMAGE" python scripts/public/control/agent_daemon.py --help >/dev/null
docker run --rm "$IMAGE" python scripts/public/control/org_role_preflight.py --help >/dev/null
docker run --rm "$IMAGE" sh -lc \
  "python scripts/public/control/org_first_run_setup.py --init-private --skip-smoke >/dev/null && python scripts/public/control/org_runtime_smoke.py --role research_director --member-id docker-smoke --agent-cli claude --agent-adapter auto >/dev/null"
docker run --rm "$IMAGE" sh -lc \
  "python scripts/public/control/org_first_run_setup.py --init-private --skip-smoke >/dev/null && make smoke-public PYTHON=python"

echo "OK: ZTARE Docker image built and public smoke passed."
