# VPS Deployment — Persistent Agent Daemon

## What this is

A 24/7 autonomous agent that discovers work, proposes it to you via Telegram, waits for your approval, executes via Claude Code CLI, and records results. You manage it from your phone.

## Quick setup (Ubuntu VPS)

```bash
# 1. Provision a VPS ($5-10/mo: DigitalOcean, Hetzner, Oracle free tier)
# 2. SSH in and clone the repo
git clone https://github.com/sparckix/ztare.git ~/figs_activist_loop
cd ~/figs_activist_loop

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
