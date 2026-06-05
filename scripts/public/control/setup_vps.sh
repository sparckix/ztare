#!/usr/bin/env bash
# setup_vps.sh — seamless ZTARE Research Co (or any tenant) VPS bootstrap.
#
# Run this from your LAPTOP, pointing at a fresh Ubuntu VPS:
#
#     ./scripts/public/control/setup_vps.sh root@<vps-ip>
#
# What it does (idempotent — safe to re-run):
#   1. Probe SSH; if password-only, prompt to upgrade to key-based + harden
#   2. Install OS deps (python 3.12+, git, build tools, jq, inotify-tools)
#   3. Install Node 22 LTS via NodeSource (overrides Ubuntu's old Node 18)
#   4. Install Claude Code CLI + OpenAI Codex CLI globally
#   5. Create `ztare` user with passwordless sudo + same SSH key
#   6. Disable root password auth + harden sshd drop-ins
#   7. Print the manual-step checklist that remains (deploy keys, OAuth tokens, etc.)
#
# What this script does NOT do (requires per-deployment principal action):
#   - Add deploy key to GitHub (needs GitHub auth)
#   - Run `claude setup-token` (interactive OAuth)
#   - Drop API keys into .env (per-principal secrets)
#   - Clone the tenant overlay (per-tenant repo)
#   - Run setup_tenant.sh (lives in tenant overlay repo)
#
# These remaining steps are listed at the end with copy-paste commands.
#
# Designed for Hetzner CCX23 (Ubuntu 24.04+), but should work on any Debian/
# Ubuntu LTS with apt + systemd. Tested 2026-05-07 on ubuntu-16gb-nbg1-1.

set -euo pipefail

if [[ $# -lt 1 ]]; then
    cat <<EOF
Usage: $0 root@<vps-ip>

Optional env:
  KEY_FILE=path/to/your/id_ed25519.pub   (default: ~/.ssh/id_ed25519.pub)
  ZTARE_USER=ztare                        (default: ztare)
  GITHUB_REPO=sparckix/ztare              (default: sparckix/ztare; the public kernel)
  TENANT_REPO=sparckix/ztare-research-co  (default: ; private tenant overlay)
EOF
    exit 1
fi

VPS_TARGET="$1"
KEY_FILE="${KEY_FILE:-$HOME/.ssh/id_ed25519.pub}"
ZTARE_USER="${ZTARE_USER:-ztare}"
GITHUB_REPO="${GITHUB_REPO:-sparckix/ztare}"
TENANT_REPO="${TENANT_REPO:-}"

if [[ ! -f "$KEY_FILE" ]]; then
    echo "ERROR: SSH public key not found at $KEY_FILE" >&2
    echo "Generate one with: ssh-keygen -t ed25519" >&2
    exit 2
fi

PUBKEY="$(cat "$KEY_FILE")"
VPS_HOST="${VPS_TARGET#*@}"

echo "═══════════════════════════════════════"
echo "  ZTARE VPS Bootstrap"
echo "═══════════════════════════════════════"
echo "  Target:    $VPS_TARGET"
echo "  Key file:  $KEY_FILE"
echo "  User:      $ZTARE_USER"
echo "  Kernel:    https://github.com/$GITHUB_REPO"
[[ -n "$TENANT_REPO" ]] && echo "  Overlay:   https://github.com/$TENANT_REPO"
echo ""

# ── Step 1: SSH key install + sshd hardening ──────────────────────────────
echo "── Step 1/5: SSH key + sshd hardening ──"
ssh -o StrictHostKeyChecking=accept-new "$VPS_TARGET" "
set -e
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo '$PUBKEY' >> ~/.ssh/authorized_keys
sort -u ~/.ssh/authorized_keys -o ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
# Disable password auth at all override layers (cloud-init included)
mkdir -p /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/01-disable-password.conf <<'SSHEOF'
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PermitRootLogin prohibit-password
SSHEOF
# Cloud-init's drop-in alphabetically wins by default — neutralize it
if [[ -f /etc/ssh/sshd_config.d/50-cloud-init.conf ]]; then
    sed -i 's/^PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config.d/50-cloud-init.conf
fi
systemctl reload ssh
echo '  ✓ key installed; password auth disabled'
" || { echo "✗ SSH hardening failed"; exit 3; }

# ── Step 2: OS dependencies ───────────────────────────────────────────────
echo ""
echo "── Step 2/5: OS dependencies (python, git, build tools, jq) ──"
ssh "$VPS_TARGET" "
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq 2>&1 | tail -2
apt-get install -y -qq \
    python3-venv python3-pip python3-dev \
    git curl rsync make build-essential \
    pkg-config libffi-dev libssl-dev \
    ca-certificates jq inotify-tools unzip 2>&1 | tail -3
echo '  ✓ python:' \$(python3 --version)
echo '  ✓ git:' \$(git --version)
"

# ── Step 3: Node 22 LTS ───────────────────────────────────────────────────
echo ""
echo "── Step 3/5: Node 22 LTS (Ubuntu's default Node 18 is too old for orbit) ──"
ssh "$VPS_TARGET" "
set -e
NODE_MAJOR=\$(node --version 2>/dev/null | sed 's/v//' | cut -d. -f1 || echo 0)
if [[ \"\$NODE_MAJOR\" -ge 20 ]]; then
    echo '  ✓ node already' \$(node --version)
else
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - 2>&1 | tail -2
    apt-get install -y -qq nodejs 2>&1 | tail -2
    echo '  ✓ node:' \$(node --version)
fi
"

# ── Step 4: CLI tools (claude + codex) ────────────────────────────────────
echo ""
echo "── Step 4/5: Claude Code CLI + Codex CLI (npm globals) ──"
ssh "$VPS_TARGET" "
set -e
if ! command -v claude >/dev/null 2>&1; then
    npm install -g @anthropic-ai/claude-code 2>&1 | tail -2
fi
echo '  ✓ claude:' \$(claude --version 2>&1 | head -1)
if ! command -v codex >/dev/null 2>&1; then
    npm install -g @openai/codex 2>&1 | tail -2
fi
echo '  ✓ codex:' \$(codex --version 2>&1 | head -1)
"

# ── Step 5: Create ztare user with passwordless sudo + clone repo ────────
echo ""
echo "── Step 5/5: Create $ZTARE_USER user + clone public kernel ──"
ssh "$VPS_TARGET" "
set -e
if ! id $ZTARE_USER &>/dev/null; then
    useradd -m -s /bin/bash -G sudo $ZTARE_USER
    mkdir -p /home/$ZTARE_USER/.ssh
    cp /root/.ssh/authorized_keys /home/$ZTARE_USER/.ssh/
    chown -R $ZTARE_USER:$ZTARE_USER /home/$ZTARE_USER/.ssh
    chmod 700 /home/$ZTARE_USER/.ssh
    chmod 600 /home/$ZTARE_USER/.ssh/authorized_keys
    echo '$ZTARE_USER ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/$ZTARE_USER
    chmod 440 /etc/sudoers.d/$ZTARE_USER
    echo '  ✓ created $ZTARE_USER user with passwordless sudo'
else
    echo '  (user $ZTARE_USER already exists)'
fi
"

ssh "$ZTARE_USER@$VPS_HOST" "
set -e
if [[ ! -d ~/figs_activist_loop ]]; then
    git clone https://github.com/$GITHUB_REPO ~/figs_activist_loop 2>&1 | tail -2
fi
cd ~/figs_activist_loop
if [[ ! -d venv ]]; then
    python3 -m venv venv
fi
./venv/bin/pip install --quiet --upgrade pip 2>&1 | tail -1
./venv/bin/pip install --quiet -r requirements.txt 2>&1 | tail -2
./venv/bin/pip install --quiet python-dotenv 2>&1 | tail -1
echo '  ✓ public kernel cloned + python venv ready'

if [[ \"\${PREP_LEAN_BACKENDS:-1}\" = \"1\" ]] && [[ -d analytics/public/leanmill/external_benchmarks/sandboxes/v28A_carleson_baseline/carleson ]]; then
    bash deploy/prepare_lean_backends.sh
    echo '  ✓ Lean backend artifacts ready (Hammer/Duper/auto + Zipperposition)'
else
    echo '  (Lean backend prep skipped: PREP_LEAN_BACKENDS=0 or sandbox absent)'
fi

# Generate deploy key for tenant overlay clone (if not yet present)
if [[ ! -f ~/.ssh/github_deploy ]]; then
    ssh-keygen -t ed25519 -f ~/.ssh/github_deploy -N '' -C 'ztare-vps-deploy' 2>&1 | tail -2
    cat > ~/.ssh/config <<'GHEOF'
Host github-private
  HostName github.com
  User git
  IdentityFile ~/.ssh/github_deploy
  IdentitiesOnly yes
GHEOF
    chmod 600 ~/.ssh/config
    echo '  ✓ deploy key generated for tenant overlay'
fi

# Install systemd units (NOT enabled yet — let principal review first)
sudo cp deploy/agent-daemon.service /etc/systemd/system/ 2>&1 || true
if [[ -f deploy/orbit-sync.service ]]; then
    sudo cp deploy/orbit-sync.service /etc/systemd/system/
fi
sudo systemctl daemon-reload
echo '  ✓ systemd units staged (not enabled)'

# Pre-stage .env from .env.example
if [[ ! -f .env ]] && [[ -f .env.example ]]; then
    cp .env.example .env
    chmod 600 .env
fi
echo '  ✓ .env skeleton in place at ~/figs_activist_loop/.env'

# Install orbit deps
if [[ -d orbit ]] && [[ ! -d orbit/node_modules ]]; then
    cd orbit && npm install --silent 2>&1 | tail -2
    echo '  ✓ orbit npm install complete'
fi
"

# ── Replicate local .env (incl. API keys) to the node — MECHANIZED ──────────
# Was a manual checklist step. The LOCAL .env is the source of truth (GEMINI/OPENAI/DEEPSEEK/etc.).
# Merge key-by-key on the node: every non-empty KEY=val locally is upserted (node-only keys kept,
# existing node values never blanked). Skip with SYNC_ENV=0 (e.g. an untrusted node that must not
# hold secrets). chmod 600 on the node. Run from the laptop that has the populated .env.
echo ""
echo "── Replicating local .env → node (API keys included; SYNC_ENV=0 to skip) ──"
if [[ "${SYNC_ENV:-1}" == "1" ]] && [[ -f .env ]]; then
    scp -q .env "$ZTARE_USER@$VPS_HOST:/tmp/.env.incoming"
    ssh "$ZTARE_USER@$VPS_HOST" 'cd ~/figs_activist_loop && python3 - <<PY
import pathlib
node=pathlib.Path(".env"); inc=pathlib.Path("/tmp/.env.incoming")
def parse(p):
    d={}
    if p.exists():
        for l in p.read_text().splitlines():
            s=l.strip()
            if s and not s.startswith("#") and "=" in s:
                k,v=l.split("=",1); d[k.strip()]=v
    return d
n=parse(node); i=parse(inc)
for k,v in i.items():
    if v.strip(): n[k]=v
node.write_text("".join(k+"="+v+"\n" for k,v in n.items()))
node.chmod(0o600); inc.unlink(missing_ok=True)
print("  done: .env now has", sum(1 for v in n.values() if v.strip()), "non-empty vars")
PY'
else
    echo "  (skipped: SYNC_ENV=0 or no local .env present)"
fi

# ── Print remaining manual steps ──────────────────────────────────────────
DEPLOY_PUBKEY=$(ssh "$ZTARE_USER@$VPS_HOST" "cat ~/.ssh/github_deploy.pub" 2>/dev/null || echo "<run setup again to generate>")
cat <<EOF

═══════════════════════════════════════════════════════════════════
  ✓ VPS bootstrap complete
═══════════════════════════════════════════════════════════════════

What's done:
  ✓ SSH key-only access; password auth disabled
  ✓ ztare user with passwordless sudo
  ✓ OS deps + Node 22 + claude + codex CLIs
  ✓ Public kernel cloned to ~/figs_activist_loop/
  ✓ Python venv + requirements installed (incl. python-dotenv)
  ✓ Deploy key generated for tenant overlay
  ✓ systemd units staged (not enabled)
  ✓ orbit npm install complete

Remaining steps (interactive — principal must perform):

  1. Add deploy key to GitHub for tenant overlay clone:

         echo '$DEPLOY_PUBKEY' | gh repo deploy-key add - \\
             --repo ${TENANT_REPO:-<your-org>/ztare-research-co} \\
             --title 'ztare-vps-${VPS_HOST}'

  2. API keys / .env — DONE automatically above (local .env replicated key-by-key to the node;
     re-run with SYNC_ENV=0 to skip on an untrusted node). Verify:

         ssh $ZTARE_USER@$VPS_HOST 'grep -c "=." ~/figs_activist_loop/.env'

  3. Set up Telegram bot creds:

         scp ~/figs_activist_loop/org/mandates/.telegram_creds \\
             $ZTARE_USER@$VPS_HOST:~/figs_activist_loop/org/mandates/.telegram_creds

     (Or run scripts/public/control/telegram_setup.py interactively on VPS.)

  4. Run claude setup-token on VPS (interactive OAuth — needs your laptop browser):

         ssh $ZTARE_USER@$VPS_HOST
         unset ANTHROPIC_API_KEY  # so claude prefers OAuth
         claude setup-token
         # Visit URL on laptop browser; paste code back; exit

  5. (Optional) Sync Codex CLI auth from local laptop:

         rsync -az ~/.codex/auth.json \\
             $ZTARE_USER@$VPS_HOST:~/.codex/auth.json

  6. Clone tenant overlay + activate:

         ssh $ZTARE_USER@$VPS_HOST
         git clone git@github-private:${TENANT_REPO:-<your-org>/ztare-research-co} \\
             ~/ztare-research-co
         ~/ztare-research-co/scripts/public/setup_tenant.sh ~/figs_activist_loop

  7. Verify everything works:

         ssh $ZTARE_USER@$VPS_HOST 'cd ~/figs_activist_loop && \\
             ./venv/bin/python scripts/public/control/org_role_preflight.py --role research_director'

  8. Enable + start daemons (when satisfied with preflight):

         ssh $ZTARE_USER@$VPS_HOST 'sudo systemctl enable --now agent-daemon orbit-sync'

  9. Install mutagen on VPS for bidirectional sync (laptop ↔ VPS):

         ssh $ZTARE_USER@$VPS_HOST 'cd /tmp && \\
             curl -sL https://github.com/mutagen-io/mutagen/releases/download/v0.18.1/mutagen_linux_amd64_v0.18.1.tar.gz | tar xz && \\
             sudo mv mutagen /usr/local/bin/ && sudo chmod +x /usr/local/bin/mutagen'

         # On laptop (after installing mutagen locally):
         mutagen sync create --name=ztare-vps-sync --sync-mode=two-way-resolved \\
             --ignore=venv --ignore=node_modules --ignore=__pycache__ \\
             --ignore="*.pyc" --ignore=".git" --ignore=".pytest_cache" \\
             /path/to/local/figs_activist_loop \\
             $ZTARE_USER@$VPS_HOST:/home/$ZTARE_USER/figs_activist_loop

  10. Set up daily git push of org_overlay (GP-192 Axis 7 — recovery snapshot):

         ssh $ZTARE_USER@$VPS_HOST 'crontab -e'
         # Add:
         #   0 2 * * * cd ~/figs_activist_loop && git add -A && \\
         #     git commit -m "snap \$(date -u +%F)" --allow-empty && git push 2>&1 \\
         #     | logger -t ztare-snap

═══════════════════════════════════════════════════════════════════
EOF
