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


def _load_member(entry: dict):
    ns: dict = {"__name__": "candidate"}
    try:
        exec(compile(entry["source"], f"pool:{entry['sha']}", "exec"), ns)  # noqa: S102
    except Exception:
        return None
    if isinstance(ns.get("WORLD_MODEL_SPEC"), dict):
        from ztare.worldmodel.spec_catalog import lower_spec
        fn, _ = lower_spec(ns["WORLD_MODEL_SPEC"])
        return fn
    for alias in ("step", "f", "model", "I_model"):
        if callable(ns.get(alias)):
            return ns[alias]
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
    # Derive action arity from the log so the counterfactual probe is valid on
    # non-4-arity environments. Hardcoding 4 probed nonexistent actions on
    # smaller arities, producing identity predictions → spurious dedup
    # (committee shrinkage). Falls back to 4 when the log is empty.
    arity = (max(tr.a for tr in log_rows) + 1) if log_rows else 4
    probe = [(tr.s, tr.a, tr.t) for tr in log_rows[:8]]
    for line in path.read_text().splitlines():
        try:
            entry = json.loads(line)
        except Exception:
            continue
        fn = _load_member(entry)
        if fn is None or not replay_consistency_gate(fn, log).ok:
            continue
        p = as_predictor(fn)
        sig = tuple(p(s, (a + 1) % arity, t) for (s, a, t) in probe)  # counterfactual probe
        if sig in signatures:
            continue
        signatures.add(sig)
        survivors.append(fn)
    return survivors
