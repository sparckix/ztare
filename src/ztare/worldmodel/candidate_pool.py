"""Loop-level candidate pool: multiple hypotheses as executable objects.

The deterministic layer already maintains a committee (synthesis survivors +
probe signatures); the LLM loop did not — rivals lived in thesis PROSE, and
discriminating states were reached by accident. This pool makes every
gate-passing candidate (spec / step / AST, any carrier) a PERSISTENT member,
re-gated against the growing evidence: survivors form the loop-level
committee, `planner.plan_disagreement` targets their frontier, and the live
environment settles the argument. (Lineage: Hypothesis Search / theory-based
RL populations; completes the seam's own disagreement-frontier contract.)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.gates import as_predictor, replay_consistency_gate


def pool_path(project_dir) -> Path:
    return Path(project_dir) / "workspace" / "candidate_pool.jsonl"


def add_candidate(project_dir, source_text: str, *, carrier: str, origin: str) -> str:
    """Persist a gate-passing candidate's SOURCE (dedup by content hash)."""
    path = pool_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source_text.encode()).hexdigest()[:16]
    if path.exists() and digest in path.read_text():
        return digest
    with path.open("a") as f:
        f.write(json.dumps({"schema": "ztare-candidate-v1", "sha": digest,
                            "carrier": carrier, "origin": origin,
                            "source": source_text}) + "\n")
    return digest


def _load_member(entry: dict, *, project_dir: str | Path):
    ns: dict = {"__name__": "candidate"}
    try:
        exec(compile(entry["source"], f"pool:{entry['sha']}", "exec"), ns)  # noqa: S102
        from ztare.worldmodel.carrier_loader import lower_carrier_namespace

        return lower_carrier_namespace(ns, project_dir=project_dir)
    except Exception:
        return None


def surviving_committee(project_dir, log: EpisodeLog) -> "list":
    """Members that still replay the CURRENT log exactly — the loop-level
    committee. Growing evidence prunes the pool automatically; behavioral
    duplicates are collapsed by prediction signature on the log's states."""
    path = pool_path(project_dir)
    if not path.exists():
        return []
    survivors, signatures = [], set()
    log_rows = list(log)
    entries = []
    for line in path.read_text().splitlines():
        try:
            entries.append(json.loads(line))
        except Exception:
            continue
    # Candidate memory is the gate's evidence-indexed survivor ledger.  Use it
    # as the committee index, then replay only the current exact members as a
    # defense.  Replaying every historical source made this advisory step cost
    # O(pool history × evidence bank) after the project gate had already done
    # the same work.
    current_exact: set[str] | None = None
    try:
        from ztare.common.observation_chart import capture_project_evidence_epoch

        memory = json.loads(
            (Path(project_dir) / "workspace" / "candidate_memory.json").read_text()
        )
        epoch_sha = capture_project_evidence_epoch(project_dir).epoch_sha256
        current_exact = {
            str(row.get("sha") or "")[:16]
            for row in (memory.get("records") or [])
            if row.get("evidence_epoch_sha256") == epoch_sha
            and row.get("visible_checked_rows") == row.get("visible_exact_rows")
        }
    except (OSError, TypeError, ValueError):
        pass
    if current_exact is not None:
        entries = [row for row in entries if str(row.get("sha") or "") in current_exact]
        if len(entries) < 2:
            return []
    # Derive action arity from the log so the counterfactual probe is valid on
    # non-4-arity environments. Hardcoding 4 probed nonexistent actions on
    # smaller arities, producing identity predictions → spurious dedup
    # (committee shrinkage). Falls back to 4 when the log is empty.
    arity = (max(tr.a for tr in log_rows) + 1) if log_rows else 4
    probe = [(tr.s, tr.a, tr.t) for tr in log_rows[:8]]
    for entry in entries:
        fn = _load_member(entry, project_dir=project_dir)
        if fn is None or not replay_consistency_gate(fn, log).ok:
            continue
        p = as_predictor(fn)
        sig = tuple(p(s, (a + 1) % arity, t) for (s, a, t) in probe)  # counterfactual probe
        if sig in signatures:
            continue
        signatures.add(sig)
        survivors.append(fn)
    return survivors
