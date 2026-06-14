#!/usr/bin/env bash
# OPT-IN, HEAVYWEIGHT provisioning of the Isabelle `sledgehammer` server for MOVE_SLEDGEHAMMER.
#
# WHY OPT-IN: sledgehammer is a default-OFF, FAIL-CLOSED leanmill move whose LIFT is UNMEASURED. Isabelle
# + its ATP portfolio is ~1GB and the first HOL build is slow (~15-30 min). So this is NOT part of the
# default deploy (`prepare_lean_backends.sh`) — run it deliberately, only once you intend to USE / measure
# the premise-mining move. Without it, sledgehammer is simply a silent no-op (never a false closure).
#
# WHAT IT DOES: download a pinned Isabelle, build the HOL heap, then start `isabelle_sledgehammer_server.py`
# (the reference HTTP server implementing the run_sledgehammer contract). Prints the ZTARE_ISABELLE_SERVER
# export to point leanmill at it.
#
# Usage:
#   bash deploy/prepare_isabelle_server.sh                 # install + build HOL + start server :8080
#   ISABELLE_VERSION=2024 PORT=8080 bash deploy/prepare_isabelle_server.sh
#   START_SERVER=0 bash deploy/prepare_isabelle_server.sh  # install only, don't start
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
ISABELLE_VERSION="${ISABELLE_VERSION:-2024}"
PREFIX="${ISABELLE_PREFIX:-$HOME/.local/isabelle}"
PORT="${PORT:-8080}"
HOST="${HOST:-127.0.0.1}"
START_SERVER="${START_SERVER:-1}"

say() { echo "== $* =="; }
die() { echo "ERROR: $*" >&2; exit 1; }

if [ -x "$REPO/venv/bin/python" ]; then PY="$REPO/venv/bin/python"; else PY="${PYTHON:-python3}"; fi

say "0. platform detection"
OS="$(uname -s)"
case "$OS" in
  Linux)  ASSET="Isabelle${ISABELLE_VERSION}_linux.tar.gz";  DIRNAME="Isabelle${ISABELLE_VERSION}" ;;
  Darwin) ASSET="Isabelle${ISABELLE_VERSION}_macos.tar.gz";  DIRNAME="Isabelle${ISABELLE_VERSION}.app" ;;
  *) die "unsupported OS '$OS' (Isabelle ships linux/macos/windows only)" ;;
esac
# URL location depends on whether $ISABELLE_VERSION is the CURRENT release (`/dist/`) or ARCHIVED
# (`/website-Isabelle<V>/dist/`). ARCHIVED path first (confirmed-good for 2024). We GET each candidate
# DIRECTLY (no HEAD pre-probe — rapid HEADs trip the server's rate-limit and 000 even on a valid URL);
# `curl -fL` fails on 404 so we just fall through to the next candidate.
CANDIDATE_URLS=(
  "https://isabelle.in.tum.de/website-Isabelle${ISABELLE_VERSION}/dist/${ASSET}"
  "https://isabelle.in.tum.de/dist/${ASSET}"
)
echo "OS=$OS  asset=$ASSET  prefix=$PREFIX"

ISABELLE_HOME="$PREFIX/$DIRNAME"

# Locate the `isabelle` launcher under PREFIX rather than HARDCODING a platform-specific path — the macOS
# tarball nests it inside the `.app` bundle (`Isabelle2024.app/Contents/Resources/Isabelle2024/bin/isabelle`
# OR `Isabelle2024.app/bin/isabelle` depending on the release), and a wrong guess makes the post-extract
# `-x` check die on a perfectly good install. `find` for the real one (a `*/bin/isabelle` regular file).
locate_isabelle_bin() {
  find "$PREFIX" -type f -name isabelle -path '*/bin/isabelle' 2>/dev/null | head -n1
}
ISABELLE_BIN="$(locate_isabelle_bin || true)"

say "1. download + extract Isabelle (skip if already present)"
if [ -n "$ISABELLE_BIN" ] && [ -x "$ISABELLE_BIN" ]; then
  echo "OK: Isabelle already at $ISABELLE_BIN"
else
  mkdir -p "$PREFIX"
  TARBALL="$PREFIX/$ASSET"
  # STAGED TARBALL (preferred for the VPS): `scp` the matching platform tarball once and point ISABELLE_TARBALL
  # at it (or just drop it at $PREFIX/$ASSET) — much faster + dodges the upstream host's rate-limit/HTTP2 flaps.
  #   local$  curl -fL -o /tmp/Isabelle2024_linux.tar.gz https://isabelle.in.tum.de/website-Isabelle2024/dist/Isabelle2024_linux.tar.gz
  #   local$  scp /tmp/Isabelle2024_linux.tar.gz  vps:~/.local/isabelle/Isabelle2024_linux.tar.gz
  #   vps$    ISABELLE_TARBALL=~/.local/isabelle/Isabelle2024_linux.tar.gz bash deploy/prepare_isabelle_server.sh
  # NOTE: the tarball is platform-specific (linux vs macos) and the built HEAPS are not portable, so the heap
  # build (step 2) still runs natively on the VPS — staging only saves the ~1-1.5GB download.
  if [ -n "${ISABELLE_TARBALL:-}" ] && [ -f "$ISABELLE_TARBALL" ] && [ "$ISABELLE_TARBALL" != "$TARBALL" ]; then
    echo "  using staged tarball $ISABELLE_TARBALL (no download)"
    cp "$ISABELLE_TARBALL" "$TARBALL"
  fi
  if [ ! -f "$TARBALL" ]; then
    command -v curl >/dev/null 2>&1 || die "curl required to download Isabelle (or stage it via ISABELLE_TARBALL / scp)"
    ok=0
    for cand in "${CANDIDATE_URLS[@]}"; do
      echo "  GET (~1-1.5GB) $cand ..."
      # --http1.1: the Isabelle host's HTTP/2 intermittently throws `curl (16) framing layer` errors.
      if curl -fL --http1.1 --retry 5 --retry-delay 5 --retry-connrefused -o "$TARBALL" "$cand"; then
        ok=1; break
      fi
      echo "  -> failed, trying next candidate"
      rm -f "$TARBALL"
    done
    [ "$ok" = "1" ] || die "download failed for all candidates: ${CANDIDATE_URLS[*]} (stage via ISABELLE_TARBALL/scp, or set ISABELLE_VERSION)"
  fi
  echo "extracting ..."
  tar -xzf "$TARBALL" -C "$PREFIX" || die "extract failed"
  ISABELLE_BIN="$(locate_isabelle_bin || true)"
  [ -n "$ISABELLE_BIN" ] && [ -x "$ISABELLE_BIN" ] || die "isabelle binary not found under $PREFIX after extract (locate_isabelle_bin found nothing — inspect: find $PREFIX -name isabelle)"
fi
echo "isabelle: $("$ISABELLE_BIN" version 2>/dev/null || echo '<version check failed>')"

say "2. build the HOL heap (slow on first run, ~15-30 min) + verify an ATP backend is available"
"$ISABELLE_BIN" build -b HOL || die "isabelle build HOL failed"
# Pre-build the PARENT-SESSION heap the server uses (`ISABELLE_PARENT_SESSION`, default
# HOL-Computational_Algebra) so the FIRST live /sledgehammer request doesn't pay the ~5-15 min parent build.
# The server's per-request session-build then loads this heap (fast) and only compiles the tiny goal theory.
PARENT_SESSION="${ISABELLE_PARENT_SESSION:-HOL-Computational_Algebra}"
say "2b. pre-build the server parent-session heap '$PARENT_SESSION' (one-time, ~5-15 min)"
"$ISABELLE_BIN" build -b "$PARENT_SESSION" || die "isabelle build $PARENT_SESSION failed (set ISABELLE_PARENT_SESSION)"
# sledgehammer needs >=1 ATP; Isabelle bundles E + others. Surface what's configured (advisory).
"$ISABELLE_BIN" env bash -c 'echo "ATP components: ${E_HOME:-<no E>} ${VAMPIRE_HOME:-<no vampire>} ${Z3_SOLVER:-<no z3>}"' || true

say "3. server self-test (parse/shape; subprocess validated on the first live request)"
ISABELLE_BIN="$ISABELLE_BIN" "$PY" "$REPO/deploy/isabelle_sledgehammer_server.py" --selftest

if [ "$START_SERVER" = "1" ]; then
  say "4. start the sledgehammer server on http://$HOST:$PORT"
  echo "   FIRST LIVE REQUEST validates the isabelle invocation (see _run_isabelle NEEDS-LIVE-VALIDATION)."
  echo "   point leanmill at it:"
  echo "     export ZTARE_ISABELLE_SERVER=http://$HOST:$PORT"
  echo "     export ZTARE_LEANMILL_SLEDGEHAMMER=1   # enable the move"
  exec env ISABELLE_BIN="$ISABELLE_BIN" "$PY" "$REPO/deploy/isabelle_sledgehammer_server.py" \
       --host "$HOST" --port "$PORT"
else
  say "install complete (START_SERVER=0). To run:"
  echo "  ISABELLE_BIN=$ISABELLE_BIN $PY $REPO/deploy/isabelle_sledgehammer_server.py --port $PORT"
fi
