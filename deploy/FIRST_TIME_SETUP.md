# GP-241 commit-membrane — first-time setup (production)

Stand up the full forcing mechanism from scratch on a fresh
verificator host + judge host. Mirrors the cognitive-firm deployment
pattern: every trust anchor is operator-provisioned once; the agent
can never produce official state or a judge verdict by itself.

## Trust model (why each step exists)

- **Verificator daemon** (`ztare_verify` user, VPS): the SOLE writer
  of the official store; signs every row with the **daemon key**.
- **Daemon key**: ed25519, `ztare_verify`-only, agent-unreadable.
  Public key pinned in-repo (`deploy/gp241_daemon_pubkey.hex`) so
  readers verify a row is genuinely daemon-signed (endpoint identity
  out of the TCB).
- **Judge key**: a SEPARATE ed25519 key on the judge host, owned by a
  provisioned judge identity, agent-unreadable. `judge_out_of_loop`
  signs the execution proof with it; the daemon verifies it before
  signing an official `judge_verdict`. The mutator lacks this key ⇒
  cannot fabricate a verdict (cold review baxgapbe9).
- **Trusted laptop install** (`/usr/local/ztare_gate`, root-owned):
  the agent-unwritable copy the verifier/anchor run from, so an agent
  can't swap the pinned pubkey or the resolver code.
- **Frozen legacy manifest + structural-anchor registry**: pinned
  anchors so pre-cutover history and residual-target naming can't be
  forged.

Until a key/anchor is provisioned the relevant path **fail-closes**
(substantive ticks are *blocked*, never falsely trusted).

## Steps (order matters)

1. **VPS users + store + daemon** — idempotent:
   ```
   ZTARE_VPS_SSH=user@host bash deploy/vps_update.sh
   ```
   This rsyncs the file set, runs `ztare_membrane_deploy.sh --apply`
   (creates `ztare_verify`, the official store outside the synced
   repo, perms, the systemd unit), force-restarts the daemon, and
   runs the hard-gated post-checks.

2. **Daemon signing key** (once, on the VPS, as `ztare_verify`):
   ```
   sudo install -d -o ztare_verify -g ztare_verify -m 0700 /srv/ztare_verify_keys
   sudo -u ztare_verify python3 deploy/gen_daemon_key.py
   ```
   Commit the printed `PUBKEY_HEX` to `deploy/gp241_daemon_pubkey.hex`
   (the pinned anchor). Re-run `vps_update.sh`; the deploy
   hard-verifies the VPS key matches the committed anchor.

3. **Judge signing key** (once, on the JUDGE host — where `codex`/the
   judge model is reachable — as a DEDICATED judge identity that is
   neither the agent user nor the daemon signer). On the VPS (codex is
   installed there ⇒ run the judge there for real OS-separation; the
   single-user laptop cannot separate a sudo-capable agent):
   **This is now fully automated** by `deploy/ztare_membrane_deploy.sh`
   step 4b (invoked by `vps_update.sh`): it creates the `ztare_judge`
   nologin user, the `0700` key store, runs `gen_judge_key.py`
   (generate-if-absent), and **hard-verifies** the VPS-derived pubkey
   equals the committed anchor `deploy/gp241_judge_pubkey.hex` —
   mismatch ⇒ deploy aborts (fail-closed). It also provisions the
   `judge_queue` (requests = daemon-write/judge-read; verdicts =
   judge-write/daemon-read; worker_state = judge-only; **the agent has
   no access to any of them**), grants `ztare_judge` read-only ACL on
   the gate code tree, and installs+restarts the worker unit.

   Verify the triad separation any time:
   ```
   sudo -u <agent_user> test -r /srv/ztare_judge_keys/judge_ed25519.key && echo FAIL || echo "OK agent ✗"
   sudo -u ztare_verify test -r /srv/ztare_judge_keys/judge_ed25519.key && echo FAIL || echo "OK signer ✗"
   sudo -u ztare_judge  test -r /srv/ztare_judge_keys/judge_ed25519.key && echo "OK judge ✓"
   ```
   To rotate: re-run `gen_judge_key.py` deliberately and re-commit the
   new `deploy/gp241_judge_pubkey.hex` in a reviewed commit (the
   deploy hard-verify enforces this — a silent rotation aborts).

   **Reference deployment:** `ztare_judge` uid 995; key
   `/srv/ztare_judge_keys/judge_ed25519.key` (0400 ztare_judge); triad
   verified; pinned pubkey
   `da35951baf36c69e9156c4ff11d2c7cc5d8382f0b81a3a131394e754ec72b309`.

   **Judge codex credentials (ChatGPT SUBSCRIPTION, not an API key).**
   codex on this box authenticates via a ChatGPT subscription (OAuth
   `auth.json`), NOT `OPENAI_API_KEY`. Hard facts learned the hard way
   (now automated by deploy step 4b — do not rediscover):
   - `ztare_judge` needs a **persistent** agent-unreadable HOME +
     CODEX_HOME (`/var/lib/ztare_judge` + `/.codex`). codex **refuses
     to create helper binaries under `/tmp`** and walks CWD upward for
     a project `config.toml` (the unit's `WorkingDirectory=/srv/ztare_gate`
     keeps it off the agent's `~/.codex`). The unit sets `HOME`,
     `CODEX_HOME`.
   - A ChatGPT account does **not** support `gpt-4.1`
     (`400 … not supported when using Codex with a ChatGPT account`).
     The unit pins `ZTARE_JUDGE_MODEL=gpt-5.5` (subscription-supported,
     proven) at `medium` reasoning. Subscription cost is flat, so this
     is a latency choice, not a $-per-call one.
   - The deploy **seeds** `/var/lib/ztare_judge/.codex/auth.json` from
     the box's working subscription login (`/root/.codex` — the
     finance-os session — else the agent user's), and is **idempotent:
     it never clobbers an existing judge `auth.json`** because OAuth
     refresh tokens are single-use, so re-copying a since-rotated
     source would break it.
   - If no source auth exists, deploy prints a LOUD fail-closed
     warning; provision once interactively:
     ```
     sudo -u ztare_judge env HOME=/var/lib/ztare_judge \
       CODEX_HOME=/var/lib/ztare_judge/.codex codex login
     ```
   Absent/stale judge auth ⇒ codex `401` ⇒ no verdict ⇒ substantive
   ticks **fail-closed**, never falsely trusted. Token rotation note:
   if the seeded session is also actively used elsewhere it may
   rotate the judge copy stale — give the judge its **own** one-time
   `codex login` for a fully independent session.

   **Judge charter (prose, deliberately NOT a cognitive-firm role —
   minimal TCB).** The judge worker exists to do exactly one thing:
   adjudicate whether a single submitted witness genuinely discharges
   one frozen obligation, out of the producing agent's control. It
   MUST: run only daemon-signed requests; judge the rubric recomputed
   from the frozen start_tick (never an agent-supplied one); sign its
   execution proof with the judge key; downgrade an inflated PASS via
   the independent critique pass. It MUST NOT: accept agent-chosen
   inputs, write the ledger or inbox, hold discretion over *which*
   work runs, or carry any state beyond its `worker_state` markers.
   Its authority is mechanical and leaf-level; all governance
   discretion stays with the daemon/agent, all trust with the keys +
   OS separation. Wrapping it in a role/mandate would enlarge the
   trusted path for no security gain — intentionally avoided.

   **Protocol (the legitimate path, now built & e2e-tested):** agent
   submits a close with witness `provenance: judge:auto` → daemon
   emits a daemon-signed `judge_request` → `ztare-judge-worker`
   services it (verifies the daemon sig, judges, judge-key-signs the
   proof, writes a verdict) → daemon ingests the verdict, the hardened
   handler stamps it → the agent re-submits the identical close and
   the id-free `judge:auto` resolver discharges it. The agent never
   sees the judge key, never triggers the worker, never picks the
   rubric or witness the judge sees.

4. **Trusted laptop verifier install** (once, and after any
   resolver/`_daemon_sig`/`propose` change), as root:
   ```
   sudo bash deploy/install_local_verifier.sh
   ```
   Installs the agent-unwritable `/usr/local/ztare_gate`. Invoke
   remote-enforce `propose` from there:
   `( cd /usr/local/ztare_gate && ZTARE_VERIFICATOR_SSH=user@host \
      python3 -m src.ztare.gates.propose ... )`

5. **Verify the whole loop** (kill-tests, all must hold):
   - agent cannot write the official store / `.md` rows are not
     authority;
   - a `tick_close` without a signed frozen `start_tick` → quarantine;
   - a substantive obligation discharged with self-asserted prose /
     blanket `why_not` / a fabricated `judge_verdict` (no valid
     judge-key signature) → **quarantine**;
   - a real `judge_out_of_loop` run (separate family, judge-key
     signed, prompt_hash == prompt recomputed from the FROZEN
     start_tick) → the discharge resolves and the tick closes.

## Rotation

Keys persist across deploys. To rotate: generate a new key, commit the
new `*_pubkey.hex` in a reviewed commit, redeploy. Rotation is a
deliberate, version-controlled, two-party act — never a silent
regeneration (the deploy fail-closes on pubkey/anchor mismatch).
