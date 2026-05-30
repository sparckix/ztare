FROM python:3.13-slim

WORKDIR /app

# ── System dependencies ──────────────────────────────────────────────
#
# `git make` are required by the apparatus.
#
# `nodejs npm` are required because the daemons (manager, research_director,
# closure) shell out to an agent CLI — by default `claude` from the
# `@anthropic-ai/claude-code` npm package — for typed work execution. Without
# the agent CLI, scripts/public/control/agent_daemon.py logs `claude CLI not found` and the
# daemon ticks become no-ops. nodejs+npm carry ~150MB; a future split into a
# `ztare-base` (no node) and `ztare-agent` (with node) image would shrink the
# base. For now, one image keeps the docker-compose path simple.
#
# `bash ca-certificates curl` keep parity with deploy/Dockerfile.operator so
# the same agent CLI semantics work in either image.

RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
  && apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    git \
    make \
    nodejs \
    npm \
  && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ───────────────────────────────────────────────

ARG REQUIREMENTS_FILE=requirements-public-smoke.txt
COPY requirements.txt requirements-public-smoke.txt ./
RUN pip install --no-cache-dir -r "$REQUIREMENTS_FILE"

# ── Agent CLI (optional, default skipped for public smoke) ─────────────
#
# Live daemon images can install the default agent CLI globally so the daemon
# services can `claude --print` and scripts/operator_console.sh can drop into
# an interactive `claude` session. The public clean-container smoke skips this
# network-heavy step because it only exercises dry-run/preflight paths.
# Override at build time with `--build-arg INSTALL_AGENT_CLI=1`, or at run time
# with ZTARE_AGENT_CLI=codex if that runtime is available in a sidecar image.

ARG INSTALL_AGENT_CLI=0
RUN if [ "$INSTALL_AGENT_CLI" = "1" ]; then npm install -g @anthropic-ai/claude-code tsx; fi
# `tsx` is the TypeScript runner used by `orbit/src/server/telegram-bot.ts`
# (no compilation step; tsx evaluates .ts directly under Node). Installed
# globally in live agent images so the telegram-bot daemon service can
# `tsx orbit/src/server/...` without first doing `cd orbit && npm install`.
# The bot itself imports only Node builtins (fs, path, fetch) so no other deps
# are needed at runtime.

# ── Source ────────────────────────────────────────────────────────────

COPY . .

# Default: show help so an unconfigured `docker compose run ztare` lands
# the user on a useful surface rather than hanging waiting for input.
CMD ["make", "help"]
