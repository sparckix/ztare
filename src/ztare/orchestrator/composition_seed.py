"""Component-D composition-seed queue helper (Phase 4g, 2026-05-06 PM).

Single helper extracted from autoresearch_loop. Pops the front of the
Component D seed queue (`workspace/composition_seed.json`) after a
failed iteration so the loop doesn't infinite-retry a crashing
candidate.

Pure function — no apparatus state, no module globals. Behaviour
preserved verbatim from the prior inline implementation
(autoresearch_loop.py 2026-05-05 git history).
"""
from __future__ import annotations

import json
from pathlib import Path


def pop_seed_queue(workspace_dir: Path, injected: bool) -> None:
    """Pop the front of the Component D seed queue after a failed iteration.

    Called from every early-exit path (R1 exception, R1 mismatch, R3
    rejection, subprocess crash) to prevent infinite retry of a
    crashing candidate. On success the queue is cleared entirely
    (handled separately by the orchestrator).

    No-op when ``injected`` is False (the iter didn't pull from the
    seed queue this round) or when ``composition_seed.json`` is
    absent.
    """
    if not injected:
        return
    seed_file = workspace_dir / "composition_seed.json"
    if not seed_file.exists():
        return
    try:
        q = json.loads(seed_file.read_text())
        if isinstance(q, list) and len(q) > 1:
            q.pop(0)
            seed_file.write_text(json.dumps(q, indent=2) + "\n")
            print(f"    🧬 Seed queue: popped failed candidate, {len(q)} remaining")
        else:
            seed_file.unlink()
            print("    🧬 Seed queue exhausted (all candidates tested)")
    except Exception:
        seed_file.unlink()
