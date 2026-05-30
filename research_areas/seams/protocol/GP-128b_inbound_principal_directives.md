# GP-128b — Inbound Principal Directives (Telegram channel)

> **Seam metadata** · `seam_id:` GP-128 · `track:` protocol · `status:` active (build authorized 2026-04-24) · `last_updated:` 2026-05-09


**Parent seam:** GP-128 persistent-manager-agent
**Status:** active (build authorized 2026-04-24)
**Owner:** Claude (manager)
**Visibility:** private (channel auth lives in repo conventions)

## Problem statement

GP-128 manager_mandate.md covers OUTBOUND escalation (ntfy push for
urgent, inbox file for non-urgent). It does NOT cover mid-session
INBOUND directives — the principal cannot pause, redirect, or
override the manager while the manager is in auto mode away from the
local terminal.

Concretely, during a long-running auto loop (e.g. a cron-driven
experiment monitor), the principal has three failure modes today:

1. Wants to STOP a misbehaving agent → has to walk to the laptop.
2. Wants to redirect ("focus on X instead of Y") → no channel.
3. Wants to ask a quick status question → has to wait for next cron
   tick to land in his terminal.

## Decision: Telegram bot polled at the manager's tick

After comparing four options (vercel webapp, telegram bot, ntfy 2-way,
docker socket), Telegram bot wins on every axis except "no third party
sees the messages". Specifically:

| Channel | Setup | Phone-native | Auth | Cost |
|---------|-------|--------------|------|------|
| Vercel webapp | ~4hrs | Yes | Solid | $0 free tier |
| **Telegram bot** | **~30 min** | **Yes** | **chat_id allowlist + token** | **$0 forever** |
| ntfy 2-way | ~10 min | Yes | Topic-as-secret only | $0 |
| Docker socket | ~15 min | No (LAN only) | N/A | $0 |

Telegram is the right answer for `1 principal × 1 manager`. The
"messages live on Telegram servers" privacy concern is acceptable for
operational directives ("STOP", "PAUSE", "look at X") which are not
research IP. Research output continues to live in repo / inbox.

## Architectural insight

The manager already has a "tick" — the cron fire (every 3 min while a
loop is active). Inbound is **not a websocket**; it's an extension of
the existing polling loop:

```
each tick:
  1. poll Telegram getUpdates(offset=last_seen_id)
  2. for each new message:
       a. authenticate (chat_id allowlist + HMAC token)
       b. dispatch by command type
       c. log to org/sessions/<sid>/inbound.jsonl
  3. resume normal cron work
```

This is the central design choice that keeps the system simple. Any
mid-session inbound delivery is bounded by the poll interval (≤3 min
in steady state), which is acceptable for the use case. If the
principal needs sub-minute response, they can switch to a manual
terminal session — the channel exists for "I'm out, let the agent run"
not for tight feedback loops.

## Message types (canonical)

The poller recognises four command types, parsed from message text:

| Command          | Effect |
|------------------|--------|
| `STOP`           | Kill any running experiment-loop process; cancel session crons; ack via outbound ntfy |
| `PAUSE`          | Set a pause flag the manager checks at next tick; do not schedule new tool calls; resume on `RESUME` |
| `RESUME`         | Clear pause flag |
| `STATUS`         | One-line outbound ntfy reply summarising current state |
| `DIRECTIVE: <t>` | Queue `<t>` as the next user-turn prompt; manager processes at next tick |
| anything else    | Treat as `DIRECTIVE: <text>` (default) |

Free-form text is the most likely usage; the explicit verbs exist for
machine-readable ops (STOP / PAUSE / RESUME / STATUS).

## Auth model

Two-layer auth:

1. **Chat ID allowlist** — only messages from `PRINCIPAL_CHAT_ID` are
   processed. Telegram surfaces a numeric chat_id per user; the
   principal's id is hardcoded in gitignored config.
2. **Optional HMAC token** — for high-stakes commands (STOP, RESUME),
   message must include `[token=<sha256-prefix>]`. Defends against
   the case where the principal's phone is briefly accessible to
   a third party.

Both auth secrets live in `org/mandates/.telegram_creds` (gitignored,
mode 0600). Loss of the bot token → revoke via @BotFather, regenerate.
Loss of chat_id → cannot escalate severity (it's a lookup key, not a
secret).

## Cost analysis

- **Telegram Bot API**: $0/month, no quotas relevant at human-typing
  rate.
- **Polling**: 1 HTTP GET per tick. At 3-min cadence: ~480 calls/day,
  trivial.
- **Storage**: messages logged to `org/sessions/<sid>/inbound.jsonl`,
  bounded by retention rule (purge at 30 days).

Total marginal cost: $0.

## Files to ship (build phase)

```
src/ztare/notifications/
  inbound_telegram.py             — poller, auth, message dispatch
scripts/public/
  poll_telegram.py                — one-shot CLI poller (cron-friendly)
  telegram_setup.py               — interactive setup wizard
                                    (BotFather token + chat_id capture)
org/mandates/
  .telegram_creds.example         — template config
  .telegram_creds                 — real creds (gitignored)
.gitignore (append)
  org/mandates/.telegram_creds
```

## Integration points

- **Cron tick**: each cron-fire prompt for an active loop is updated to
  prepend `python scripts/public/control/poll_telegram.py --consume` before its main
  work. `--consume` returns inbound messages and marks them seen.
- **Auto mode tick**: the agent calls poll_telegram at the start of each
  end-of-turn assessment (before deciding next action). Messages
  surface as part of the agent's context.
- **Session start**: any session starting an active goal loop reads
  pending inbound messages from `inbound.jsonl` once.

## Out of scope (deferred)

- Webapp UI (Vercel) — defer until multi-agent / multi-principal need
  is real.
- Slack / Discord channels — wait for a use case beyond 1 principal.
- Voice → text inbound — not needed for current use case.

## Promotion criteria (private → public)

This seam stays **private** because:
- The Telegram bot token is operational infrastructure (not first-mover
  IP, but credential-adjacent).
- The principal allowlist + HMAC pattern is generic but the *deployed*
  channel is principal-specific.

Promote to public when (and only when) we want others to install the
manager-agent stack with their own bots; at that point the seam is
generic infrastructure documentation, not a private operations doc.

## Decision log

- **2026-04-24** — seam authored after gp154 v3 substrate ship and run
  re-launch. Principal explicitly approved Telegram over Vercel during
  the org-design discussion. Build authorized in same turn.
