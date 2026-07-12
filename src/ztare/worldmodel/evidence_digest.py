"""Bounded, deterministic evidence digest for LLM worker prompts (FIX A).

The interactive-substrate `evidence.txt` is a full deterministic render of the
episode log; it grows every cycle (~788KB and climbing on arc3_ls20_gov) and
overflows the sealed codex worker's context window — the `_cap_codex_prompt`
head+tail elision in dispatch_model is the blunt backstop for when it does.

This is the proper fix: replace the RAW evidence embedded in the judge/mutator
prompt with a bounded digest that keeps exactly what a text worker needs to
reason about the law, in priority order under a char budget:

  1. summary header  — row/episode count, grid frame, env-frame count, and the
     per-color count invariant (conserved / monotone / varies)
  2. residuals       — exact when small; quotient-compressed into
     diff-signature classes when numerous
  3. exemplars       — a few transitions per distinct diff-signature cluster
     (reusing the operator_proposals clusterer), so each recurring mechanic the
     champion already explains is still WITNESSED, not just counted
  4. newest          — the newest transitions, to fill the remaining budget

Only LLM prompts get the digest; the deterministic gates/harness keep consuming
the full evidence off disk. Pure function of (transitions, residuals, budget) —
same input, same digest.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

DEFAULT_BUDGET_ENV = "ZTARE_EVIDENCE_DIGEST_CHARS"
ENABLED_ENV = "ZTARE_EVIDENCE_DIGEST"
_DEFAULT_BUDGET = 24000
_EXEMPLARS_PER_CLUSTER = 3
_RESIDUAL_VERBATIM_MAX = 64


def default_budget() -> int:
    try:
        return max(2000, int(os.environ.get(DEFAULT_BUDGET_ENV, str(_DEFAULT_BUDGET))))
    except ValueError:
        return _DEFAULT_BUDGET


def digest_enabled() -> bool:
    return os.environ.get(ENABLED_ENV, "1").strip().lower() not in ("0", "off", "false", "")


# ── rendering ────────────────────────────────────────────────────────────────

def _render_transition(tr) -> str:
    changed = [(y, x, tr.s[y][x], tr.s_next[y][x])
               for y in range(len(tr.s)) for x in range(len(tr.s[0]))
               if tr.s[y][x] != tr.s_next[y][x]]
    body = "; ".join(f"({y},{x}):{o}->{n}" for y, x, o, n in changed)
    return f"  (t={tr.t}, a={tr.a}): changed {len(changed)} cells [{body}]"


def _sig_str(signature) -> str:
    action, motion, dims, colors = signature
    h, w = dims
    return f"action={action} motion={motion} bbox={h}x{w} colors={sorted(colors)}"


def _residual_clusters(rows, residual_indices):
    """Quotient counterexamples by the same diff-signature axis used for
    operator cards. Prompts need the basis plus witnesses; replay gates keep
    the full row set on disk."""
    from ztare.worldmodel.operator_proposals import WorldmodelOperatorProposals

    clusters = WorldmodelOperatorProposals().cluster_residual(
        rows, None, sorted(residual_indices)
    )
    clusters.sort(key=lambda c: (repr(c["signature"]), min(c["indices"])))
    return clusters


def _header_facts(rows):
    n = len(rows)
    H, W = len(rows[0].s), len(rows[0].s[0])
    episodes = 1 + sum(1 for i in range(1, n) if rows[i].t <= rows[i - 1].t)
    states = [r.s for r in rows] + [rows[-1].s_next]
    counts = [Counter(v for row in g for v in row) for g in states]
    colors = sorted(set().union(*(set(c) for c in counts))) if counts else []
    facts = {}
    for c in colors:
        seq = [cp.get(c, 0) for cp in counts]
        if len(set(seq)) == 1:
            facts[c] = f"conserved@{seq[0]}"
        elif all(a <= b for a, b in zip(seq, seq[1:])):
            facts[c] = "monotone_up"
        elif all(a >= b for a, b in zip(seq, seq[1:])):
            facts[c] = "monotone_down"
        else:
            facts[c] = "varies"
    return n, H, W, episodes, facts


# ── the digest (pure) ────────────────────────────────────────────────────────

def digest_transitions(transitions, *, residual_indices=None, budget=None,
                       raw_header=None, env_frames=None) -> str:
    """Deterministic digest of an episode log for an LLM worker prompt.

    ``residual_indices`` are the transitions the current champion mispredicts
    (the mutator's targets). Small residual sets are included in full; large
    residual sets are quotiented with representative witnesses. ``raw_header``
    (the provenance top of evidence.txt) and ``env_frames`` (count) are
    optional context."""
    rows = list(transitions)
    budget = budget or default_budget()
    if not rows:
        return raw_header or ""

    n, H, W, episodes, facts = _header_facts(rows)
    resid = sorted(i for i in set(residual_indices or []) if 0 <= i < n)
    resid_set = set(resid)

    out: "list[str]" = []

    def _final_len(extra: str) -> int:
        # exact length of "\n\n".join(out + [extra]) + "\n"
        k = len(out) + 1
        return sum(len(s) for s in out) + len(extra) + 2 * (k - 1) + 1

    def emit(section: str, *, force: bool = False) -> bool:
        if not force and _final_len(section) > budget:
            return False
        out.append(section)
        return True

    # (1) header — always
    head = []
    if raw_header:
        head.append(raw_header.rstrip())
    head.append("=== EVIDENCE DIGEST (deterministic; the gates still see full evidence) ===")
    envs = f"  env_frames={env_frames}" if env_frames is not None else ""
    head.append(f"rows={n}  episodes={episodes}  grid={H}x{W}{envs}")
    head.append("per-color count invariant: "
                + ", ".join(f"{c}:{v}" for c, v in sorted(facts.items())))
    emit("\n".join(head), force=True)

    # (2) residuals — exact when small, quotient-compressed when large. The
    # full evidence remains on disk; this prompt surface is for hypothesis
    # generation, so counterexample classes dominate raw row count.
    if resid:
        if len(resid) <= _RESIDUAL_VERBATIM_MAX:
            block = [f"--- UNEXPLAINED / RESIDUAL TRANSITIONS ({len(resid)}); "
                     "the mutator MUST explain every one ---"]
            block += [_render_transition(rows[i]) for i in resid]
            emit("\n".join(block), force=True)
        else:
            clusters = _residual_clusters(rows, resid)
            emit(
                f"--- QUOTIENTED RESIDUAL TRANSITIONS ({len(resid)} rows -> "
                f"{len(clusters)} diff-signature classes); full log stays on disk ---",
                force=True,
            )
            for cl in clusters:
                idxs = sorted(cl["indices"])
                sample = idxs[:_EXEMPLARS_PER_CLUSTER]
                if not emit(
                    f"residual class [{_sig_str(cl['signature'])}] "
                    f"n={len(idxs)} sample_indices={sample}"
                ):
                    break
                for i in sample:
                    if not emit(_render_transition(rows[i])):
                        break

    included = set(resid_set)

    # (3) per-mechanic exemplars — reuse the operator_proposals diff-signature clusterer
    explained = [i for i in range(n) if i not in resid_set]
    clusters = _residual_clusters(rows, explained)
    if clusters and _final_len("") < budget:
        emit(f"--- PER-MECHANIC EXEMPLARS ({len(clusters)} diff-signature clusters) ---")
        for cl in clusters:
            idxs = sorted(cl["indices"])[:_EXEMPLARS_PER_CLUSTER]
            if not emit(f"cluster [{_sig_str(cl['signature'])}] n={len(cl['indices'])}:"):
                break
            for i in idxs:
                if emit(_render_transition(rows[i])):
                    included.add(i)
                else:
                    break

    # (4) newest transitions — fill the remaining budget, tail first
    newest = [i for i in range(n - 1, -1, -1) if i not in included]
    if newest and _final_len("") < budget:
        emit("--- NEWEST TRANSITIONS (recency fill) ---")
        for i in newest:
            if not emit(_render_transition(rows[i])):
                break

    return "\n\n".join(out) + "\n"


# ── project wiring (judge + mutator prompt assembly) ─────────────────────────

def _raw_header(raw_evidence: "str | None") -> "str | None":
    """The provenance top of evidence.txt (sha, committee status) — cheap to keep."""
    if not raw_evidence:
        return None
    i = raw_evidence.find("Visible data")
    return raw_evidence[:i].rstrip() if i > 0 else None


def _last_partial_spec(project_dir) -> "dict | None":
    """The newest abduced spec receipt — the standing partial champion whose
    mismatches are the residuals (the committee read model's champion is null at
    grammar_ceiling, which is exactly when the mutator runs)."""
    path = Path(project_dir) / "workspace" / "spec_receipts.jsonl"
    if not path.exists():
        return None
    last = None
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            last = json.loads(line)
        except json.JSONDecodeError:
            continue
    return (last or {}).get("spec") if last else None


def _residual_indices(log, spec):
    """Non-env transitions the spec mispredicts. None if no lowerable spec."""
    if not spec:
        return None
    from ztare.worldmodel.spec_catalog import lower_spec
    from ztare.worldmodel.gates import env_frame_indices
    step, _err = lower_spec(spec)
    if step is None:
        return None
    env = env_frame_indices(log)
    out = []
    for i, tr in enumerate(log):
        if i in env:
            continue
        try:
            pred = step(tr.s, tr.a, tr.t)
        except Exception:  # noqa: BLE001 — a broken partial spec must not break the digest
            pred = None
        if pred != tr.s_next:
            out.append(i)
    return out


def build_evidence_digest(project_dir, raw_evidence, *, budget=None) -> str:
    """Digest the interactive-substrate evidence; return raw unchanged for
    non-interactive projects (research papers have no episode log)."""
    from ztare.worldmodel.adapter import episode_log_path
    from ztare.worldmodel.episode_log import EpisodeLog
    from ztare.worldmodel.gates import env_frame_indices

    log_path = episode_log_path(project_dir)
    if not Path(log_path).exists():
        return raw_evidence
    log = EpisodeLog.read_jsonl(log_path)
    if len(log) == 0:
        return raw_evidence
    resid = _residual_indices(log, _last_partial_spec(project_dir))
    return digest_transitions(
        log,
        residual_indices=resid,
        budget=budget or default_budget(),
        raw_header=_raw_header(raw_evidence),
        env_frames=len(env_frame_indices(log)),
    )


def maybe_digest_evidence(project_dir, raw_evidence, *, budget=None) -> str:
    """Prompt-assembly entry point: digest when ``ZTARE_EVIDENCE_DIGEST`` is on
    (default) and the project is an interactive substrate; else the legacy raw
    evidence. Never raises — a digest failure falls back to raw evidence."""
    if not digest_enabled():
        return raw_evidence
    try:
        return build_evidence_digest(project_dir, raw_evidence, budget=budget)
    except Exception:  # noqa: BLE001 — the loop must survive a digest failure
        return raw_evidence
