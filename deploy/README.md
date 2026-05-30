# VPS Deployment — Persistent Agent Daemon

## What this is

A 24/7 autonomous agent that discovers work, proposes it to you via Telegram, waits for your approval, executes via Claude Code CLI, and records results. You manage it from your phone.

## Quick setup (Ubuntu VPS)

```bash
# 1. Provision a VPS ($5-10/mo: DigitalOcean, Hetzner, Oracle free tier)
# 2. SSH in and clone the repo
git clone https://github.com/sparckix/ztare.git ~/ztare
cd ~/ztare

# 3. Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Install Claude Code CLI
# See: https://docs.anthropic.com/en/docs/claude-code
npm install -g @anthropic-ai/claude-code

# 5. Set API keys
export ANTHROPIC_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."

# 6. Telegram setup (interactive — needs your phone)
python scripts/telegram_setup.py

# 7. Test one tick
python scripts/agent_daemon.py --tick-once --dry-run

# 8. Deploy as systemd service
sudo cp deploy/agent-daemon.service /etc/systemd/system/
# Edit the service file to add your API keys
sudo systemctl daemon-reload
sudo systemctl enable agent-daemon
sudo systemctl start agent-daemon

# 9. Check logs
journalctl -u agent-daemon -f
```

## Lean Backend Prep

For proof-search servers that run the governed Lean harness, prepare
the pinned Hammer/Duper/auto backend stack with one command:

```bash
bash deploy/prepare_lean_backends.sh
```

This builds the pinned Carleson sandbox backend oleans, ensures the
Zipperposition executable exists for LeanHammer/lean-auto, and runs
`lean_env_parity.py --require-backends`. It is idempotent and is also
called by `scripts/public/control/setup_vps.sh` when the pinned Lean
sandbox is present. Python dependencies still live in
`requirements.txt`; Lean/Lake backend artifacts are not pip packages.

## How it works

```
Every 10 minutes:
  1. Check telegram for STOP/PAUSE/STATUS commands
  2. Check damage signals for unresolved issues
  3. Discover work (TODO items in seams + damage signals)
  4. Propose top candidate to you via telegram
  5. Wait up to 30 min for your APPROVE/SKIP/STOP
  6. If approved: spawn Claude Code CLI to execute
  7. Record result in daemon log + notify you
  8. Sleep until next tick
```

## Telegram commands

| Command | What it does |
|---------|-------------|
| `APPROVE` | Execute the proposed task |
| `SKIP` | Defer to next tick |
| `STOP` | Halt the daemon |
| `PAUSE` | Sleep 30 min |
| `RESUME` | Wake from pause |
| `STATUS` | Report current state |
| *(any text)* | Treated as a directive for the next task |

## Cost

- VPS: $5-10/mo
- Claude API: ~$0.50-2.00 per task execution (depends on task complexity)
- Telegram: free
- Your attention: ~30 seconds per approval (from your phone)

## This is generalizable

The governance kernel (`org/`, `src/ztare/signals/`, `src/ztare/sessions/`, `src/ztare/notifications/`) works for any project. Change the mandate, point at a different repo, and the same daemon governs a different workload. The mandate is the contract; the daemon is the enforcement; the telegram is the interface.

## GP-241 commit-membrane (the forcing layer)

The daemon above *discovers and records* work. The **GP-241
commit-membrane** is a separate, stronger layer that makes it
**impossible for an authorized-but-uncooperative agent to make
anything official without it being genuinely earned** — a verificator
daemon is the sole signer of official state; the agent can only
propose; substantive obligations must be discharged by a
separate-family JUDGE whose verdict is cryptographically proven (the
mutator cannot fabricate it). Anyone can stand the whole mechanism up
from scratch:

➡ **`deploy/FIRST_TIME_SETUP.md`** — full reproducible provisioning
(verificator user + store, daemon signing key, judge signing key,
pinned public anchors, the agent-unwritable trusted install, the
fail-closed-until-provisioned guarantee, key rotation). Same pattern
as the cognitive-firm deployment: every trust anchor is
operator-provisioned once; until each is in place the relevant path
**fail-closes** (substantive ticks blocked, never falsely trusted).

One-line summary of the order: `vps_update.sh` → `gen_daemon_key.py`
(commit `gp241_daemon_pubkey.hex`) → `gen_judge_key.py` on the judge
host (commit `gp241_judge_pubkey.hex`) → `install_local_verifier.sh`
→ run the kill-tests in `FIRST_TIME_SETUP.md` step 5. Architecture +
the cold-review hardening history live in
`research_areas/seams/apparatus/cage/GP-241_commit_membrane_mode_independent_forcing_seam.md`.

## Operator-identity boundary (C2/C4) — the third key

`gen_daemon_key.py` (signer) and `gen_judge_key.py` (judge) have a
**third peer**: the **operator key**. It gates transitions the agent
must never self-authorize — `target_register` (which Lean target a
proof is checked against, C2) and `tick_retire` (the liveness hatch
for a jammed tick, C4). The old forgeable `ZTARE_OPERATOR_RETIRE=1`
env flag is **deleted**; a retire now requires an ed25519 signature
from a key the agent cannot read, daemon-mediated and chain-valid.

Provision once, on the VPS, as a dedicated identity:

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin ztare_operator
sudo install -d -m 0700 -o ztare_operator -g ztare_operator /srv/ztare_operator_keys
sudo -u ztare_operator python3 deploy/gen_operator_key.py
#   → PUBKEY_HEX=<64 hex>   — pin it into deploy/gp241_operator_pubkey.hex
# Triad check (must hold, else C2/C4 are decorative — the OS topology
# IS the boundary, not the crypto):
sudo -u ztare        test -r /srv/ztare_operator_keys/operator_ed25519.key && echo FAIL || echo "OK agent ✗"
sudo -u ztare_verify test -r /srv/ztare_operator_keys/operator_ed25519.key && echo FAIL || echo "OK signer ✗"
sudo -u ztare_operator test -r /srv/ztare_operator_keys/operator_ed25519.key && echo "OK operator ✓"
```

Until the pubkey is pinned, C2/C4 **fail-closed** (no target
registers, no tick retires) — intended: a wedged loop is safe, a
forgeable hatch is not.

### Retiring a jammed tick — one command

When `rd_tick_brief` refuses because a prior tick never closed and is
genuinely un-closeable, retire it (operator-only) with the
self-contained script — **all three args required**, no hardcoded
target:

```bash
bash deploy/operator_retire.sh <owner> <EXACT_full_F-row_id> <reason>
#   reason ∈ legacy_raw_propose_no_forecast_contract |
#            legacy_audit_finding_no_forecast_contract |
#            pre_lifecycle_bypass_debt
```

It forces the authoritative store (no observe/dry-run footgun),
derives the canonical payload, signs it via
`sudo -u ztare_operator deploy/operator_sign.py` (fails loudly if the
caller is not the operator — that failure *is* the boundary),
submits the daemon-mediated signed `tick_retire`, **hard-aborts on
any dry-run / refusal**, and prints the `rd_tick_brief` line to
confirm NS unblocked. It marks the tick as bypass-debt (NOT a
creditable RD close). The cleaner alternative to retiring a
discipline-following-but-aged tick is a reviewed close-window policy
change — retire is the liveness exit, not the preferred fix.

Acceptance of the C2/C4 mechanism is **not** builder self-review: it
is the not-the-builder kill-test in `tests/gates/` plus the triad
check above, run in the environment where the agent actually
executes. Spec + contracts:
`research_areas/seams/apparatus/cage/GP-241_forward_spec_promotion_contracts.md`.

### NS pre-tick — use `ns_brief.sh`, NOT bare `rd_tick_brief.py`

`python3 scripts/public/control/rd_tick_brief.py` (bare) has a known,
spec'd-not-yet-fixed dual-module-identity defect (full RCA in
`research_areas/seams/apparatus/cage/GP-241_forward_spec_promotion_contracts.md`):
it mixes repo-root and repo/src on `sys.path`, so the gate fail-closes
("stamped_state unavailable") even when the prior tick is validly
retired/closed. The gate LOGIC is correct (verified ≥5 ways incl.
instrumented runpy of the real script) — the defect is the launcher's
import ordering. Sanctioned NS entrypoint (one command, canonical
sys.path; the gate runs its real logic, NO bypass):

```bash
RD_OWNER=<id> bash projects/ns_millennium_hunt/ns_brief.sh
```

Bare `rd_tick_brief.py` must not be used for tick decisions until the
C5 launcher fix lands (single canonical sys.path discipline; reviewed,
NOT a mid-session patch, per P15). Guard
`tests/gates/test_no_src_prefixed_imports.py` blocks NEW runtime
modules from re-introducing the `src.ztare.…` spelling that creates
the dual identity.
