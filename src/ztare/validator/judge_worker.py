"""GP-241 #2 — the daemon-invoked JUDGE worker.

Runs as the dedicated `ztare_judge` OS identity (NOT the agent, NOT
the daemon signer). It ONLY services daemon-signed judge_requests:
the agent has no write access to the requests queue and cannot invoke
this worker, so it cannot steer which witness/rubric the judge sees
(`run_request` re-verifies the daemon signature regardless).

Idempotency without mutating the daemon-owned requests dir: the
worker records a `<rid>.done` marker in its OWN state dir (ztare_judge
-owned) once a request has produced a terminal result. A transient
infra failure (e.g. codex unreachable) leaves NO marker ⇒ retried.

Loop only; no agent-facing surface. `--once` for tests.
"""
from __future__ import annotations

import json
import sys
import time

from src.ztare.validator.judge_out_of_loop import _STORE, run_request

REQ = _STORE / "judge_queue" / "requests"
WST = _STORE / "judge_queue" / "worker_state"

# Terminal return codes from run_request (deterministic given the
# signed request): 0 ok, 3 judge-core/key fail-closed, 4 forged/
# non-judge_request. Anything else / an exception is transient.
_TERMINAL = {0, 3, 4}


def scan_once() -> int:
    try:
        WST.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass  # deploy provisions it; a transient mkdir error must
        # not crash the loop (resilience over correctness here).
    if not REQ.is_dir():
        return 0
    n = 0
    try:
        reqs = sorted(REQ.glob("*.json"))
    except Exception as e:
        print(json.dumps({"scan": "glob_failed", "err": repr(e)}),
              flush=True)
        return 0
    for f in reqs:
        # HARD RESILIENCE (mirrors the daemon _ingest fix): the ENTIRE
        # per-request body — including the marker stat/write — is
        # wrapped. A single unreadable/foreign-owned worker_state file
        # or any other path error must SKIP that request, never crash
        # scan_once (a crashing loop ⇒ systemd restart ⇒ crash-loop ⇒
        # the queue never drains ⇒ a liveness DoS that looks "stuck").
        try:
            rid = f.stem
            done = WST / f"{rid}.done"
            try:
                if done.exists():
                    continue
            except Exception as e:
                print(json.dumps({"req": rid,
                                  "marker_stat_skipped": repr(e)}),
                      flush=True)
                continue
            try:
                rc = run_request(str(f))
            except Exception as e:
                print(json.dumps({"req": rid, "transient": repr(e)}),
                      flush=True)
                continue
            if rc in _TERMINAL:
                try:
                    done.write_text(str(rc), encoding="utf-8")
                except Exception as e:
                    print(json.dumps({"req": rid,
                                      "marker_write_failed": repr(e)}),
                          flush=True)
                n += 1
        except Exception as e:
            print(json.dumps({"req": str(f), "loop_guard": repr(e)}),
                  flush=True)
            continue
    return n


def main() -> int:
    once = "--once" in sys.argv
    print(f"ztare_judge worker — requests={REQ} "
          f"mode={'once' if once else 'loop'}", flush=True)
    while True:
        scan_once()
        if once:
            return 0
        time.sleep(3)


if __name__ == "__main__":
    raise SystemExit(main())
