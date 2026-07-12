#!/usr/bin/env python3
"""Autoformalize + attack a proof FROM RESEARCH NOTES — a blueprint-decomposition loop over the canonical
`autoformalize_and_solve` (NL → faithfulness firewall → solve_adhoc_governed + governance kernel). This is
the LEAP / DeepSeek-Prover-V2 blueprint-decomposition pattern with the blueprint supplied as NOTES.

WHY this is solver SOURCE (not an experiment): formalizing a NL blueprint, proving each lemma through the
firewall+kernel, accumulating a citable proven-lemma SHELF, and attacking the target is GENERAL apparatus.
Specific problem corpora are the experiment-specific INPUTS that feed this loop; the loop is reusable and
belongs next to the `autoformalize_and_solve` it orchestrates.

The decomposition lives INSIDE leanmill at TWO levels — this is the LITE design (no autoresearch
evidence-mutation machinery, no `orchestrator.mutator_briefing`; that does open-ended DISCOVERY, this
PROVES a known blueprint):
  • TOP level (this module): the notes ARE the coarse decomposition (lemmas in dependency order). The agent
    does not have to invent the breakdown — a human / research-director blueprint supplies it.
  • RECURSIVE retry (INHERITED, no new engine): each line is attacked through `autoformalize_and_solve` →
    `default_solve` → `solve_adhoc`, and `solve_adhoc` already routes an HONEST non-closure (exact_gap /
    open / failed) to the recursive planner `isomorphism_decompose.route_and_solve` under
    `ZTARE_LEANMILL_ISO_ROUTE` (default-on): the warm leaf GENERATES a sub-decomposition, the KERNEL audits
    it, each sub-lemma re-enters the route (depth-guarded), then composite-ratifies. So the notes loop gets
    the agent's recursive re-decomposition for free — it does NOT fork a recursion engine or an assembler.

Notes format (markdown, dependency order — most foundational lemma first):
    ## Target
    <one NL sentence: the theorem to ultimately prove>
    ## Lemmas
    - <NL lemma 1>
    - <NL lemma 2>

Each line runs through `autoformalize_and_solve`: the firewall GATES it (unfaithful / vacuous / trivial →
rejected before any solve), an admitted statement is attacked by the kernel. Lemmas that CLOSE accumulate as
a citable SHELF (only `outcome == "closed"` counts — `exact_gap` / `open` do NOT, see `_default_attack`).

SERIAL Lean (every `_compile_probe` is a fresh Mathlib reload; no parallel compiles on one box).
CLI:  PYTHONPATH=src python -m ztare.leanmill.solver.autoformalize_notes <notes.md>
      PYTHONPATH=src python -m ztare.leanmill.solver.autoformalize_notes --selftest
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Callable, Optional

REPO = Path(__file__).resolve().parents[4]
LEAN_ROOT_DEFAULT = (REPO / "ztare_proofs").resolve()


_RUN_MANIFEST_CODE_FINGERPRINTS = (
    "src/ztare/leanmill/control_plane.py",
    "src/ztare/leanmill/verdict_store.py",
    "src/ztare/leanmill/run_diagnostics.py",
    "src/ztare/leanmill/run_observability.py",
    "src/ztare/leanmill/definition_contract.py",
    "src/ztare/leanmill/lean_source.py",
    "src/ztare/leanmill/solver/autoformalize.py",
    "src/ztare/leanmill/solver/autoformalize_notes.py",
    "src/ztare/leanmill/solver/conjecture.py",
    "src/ztare/leanmill/solver/family_lemma_library.py",
    "src/ztare/leanmill/solver/no_good_store.py",
    "src/ztare/leanmill/solver/proof_cache.py",
    "src/ztare/leanmill/solver/solver_core.py",
    "src/ztare/formal/repl_compile.py",
)


def _sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _code_fingerprints() -> dict:
    files = {}
    for rel in _RUN_MANIFEST_CODE_FINGERPRINTS:
        path = REPO / rel
        files[rel] = _sha256_file(path) if path.exists() else ""
    return {
        "schema": "leanmill.code_fingerprints.v1",
        "files": files,
    }


def _provider_manifest() -> dict:
    import os
    raw = os.environ.get("ZTARE_LEANMILL_SOLVE_PROVIDERS", "")
    providers = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    return {
        "schema": "leanmill.provider_manifest.v1",
        "solve_providers_raw": raw,
        "solve_providers": providers,
        "subscription_runtime": os.environ.get("ZTARE_DEFAULT_SUBSCRIPTION_RUNTIME", ""),
        "claude_agent_model": os.environ.get("ZTARE_CLAUDE_AGENT_MODEL", ""),
        "roundtrip_model": os.environ.get("ZTARE_LEANMILL_ROUNDTRIP_MODEL", ""),
    }


def _launch_config_manifest() -> dict:
    import os

    def _env(name: str, default: str = "") -> str:
        return os.environ.get(name, default)

    def _int_env(name: str, default: int) -> int:
        try:
            return int(_env(name, str(default)) or default)
        except (TypeError, ValueError):
            return default

    return {
        "schema": "leanmill.launch_config.v1",
        "identity": {
            "run_tag": _env("ZTARE_SOLVER_RUN_TAG"),
            "run_scratch": _env("ZTARE_LEANMILL_RUN_SCRATCH"),
            "domain": _env("ZTARE_SOLVER_DOMAIN"),
        },
        "reuse": {
            "proof_cache": _env("ZTARE_PROOF_CACHE", "1"),
            "exact_reference_reuse": _env("ZTARE_LEANMILL_REFERENCE_REUSE_STATEMENT", "1"),
            "decomposition_cache": _env("ZTARE_LEANMILL_DECOMP_CACHE", "1"),
            "staged_reuse": _env("ZTARE_LEANMILL_STAGED_REUSE", "1"),
            "reuse_banked_lemmas": _env("ZTARE_LEANMILL_REUSE_BANKED_LEMMAS", "1"),
        },
        "execution": {
            "proposer_pool": _env("ZTARE_LEANMILL_PROPOSER_POOL", "1"),
            "warm_verify": _env("ZTARE_LEANMILL_WARM_VERIFY", "1"),
            "warm_compile": _env("ZTARE_LEANMILL_WARM_COMPILE", "1"),
            "lean_warm": _env("ZTARE_LEANMILL_LEAN_WARM", "1"),
            "bank_env_ratify": _env("ZTARE_LEANMILL_BANK_ENV_RATIFY", "1"),
            "bank_rungs_to_theory": _env("ZTARE_LEANMILL_BANK_RUNGS_TO_THEORY", "1"),
        },
        "budgets": {
            "campaign_wall_s": _int_env("ZTARE_LEANMILL_CAMPAIGN_WALL_S", 14400),
            "notes_lemma_s": _int_env("ZTARE_LEANMILL_NOTES_LEMMA_S", 0),
            "notes_target_s": _int_env("ZTARE_LEANMILL_NOTES_TARGET_S", 0),
            "direct_continue_turns": _int_env("ZTARE_LEANMILL_DIRECT_CONTINUE_TURNS", 6),
            "proposer_pool_max_depth": _int_env("ZTARE_LEANMILL_PROPOSER_POOL_MAX_DEPTH", 0),
        },
        "gates": {
            "run_standards": _env("ZTARE_LEANMILL_RUN_STANDARDS", "1"),
            "instrument_liveness": _env("ZTARE_LEANMILL_INSTRUMENT_LIVENESS", "1"),
            "blueprint_lint": _env("ZTARE_LEANMILL_BLUEPRINT_LINT", "1"),
            "substrate_liveness": _env("ZTARE_LEANMILL_SUBSTRATE_LIVENESS", "1"),
            "denotation_check": _env("ZTARE_LEANMILL_DENOTATION_CHECK", "1"),
        },
    }


def _emit_notes_writeback_trace(row: dict) -> None:
    """Best-effort JSONL breadcrumbs for notes/refined-note mutation. Never affects the campaign result."""
    try:
        import os
        import time
        p = Path(os.environ.get(
            "ZTARE_LEANMILL_NOTES_TRACE",
            str(REPO / "analytics" / "public" / "queries" / "leanmill_notes_writeback_trace.jsonl"),
        ))
        p.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": time.time(), "run_tag": os.environ.get("ZTARE_SOLVER_RUN_TAG", ""), **row}
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
    except Exception:  # noqa: BLE001
        return


def _write_run_manifest(notes_path: Path, *, theory_rel: str = "") -> Path | None:
    """Best-effort run manifest for diagnostics: one receipt for launch flags, inputs, and authority modes."""
    try:
        import os
        import time
        import subprocess
        from ztare.leanmill.control_plane import cache_authority
        run_tag = os.environ.get("ZTARE_SOLVER_RUN_TAG", "")
        scratch = os.environ.get("ZTARE_LEANMILL_RUN_SCRATCH", run_tag or "default")
        out = LEAN_ROOT_DEFAULT / ".solver_scratch" / scratch / "run_manifest.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        substrate = (LEAN_ROOT_DEFAULT / theory_rel).resolve() if theory_rel else None
        blueprint_snapshot = out.parent / "launch_blueprint.md"
        blueprint_snapshot_sha = ""
        blueprint_snapshot_bytes = 0
        if notes_path.exists():
            blueprint_bytes = notes_path.read_bytes()
            blueprint_snapshot.write_bytes(blueprint_bytes)
            blueprint_snapshot_sha = _sha256_file(blueprint_snapshot)
            blueprint_snapshot_bytes = len(blueprint_bytes)
        env_keys = [
            "ZTARE_LEANMILL_SOLVE_PROVIDERS",
            "ZTARE_DEFAULT_SUBSCRIPTION_RUNTIME",
            "ZTARE_CLAUDE_AGENT_MODEL",
            "ZTARE_LEANMILL_ROUNDTRIP_MODEL",
            "ZTARE_LEANMILL_PROPOSER_POOL",
            "ZTARE_LEANMILL_PROPOSER_POOL_MAX_DEPTH",
            "ZTARE_LEANMILL_STAGED_REUSE",
            "ZTARE_PROOF_CACHE",
            "ZTARE_LEANMILL_REFERENCE_REUSE_STATEMENT",
            "ZTARE_LEANMILL_DECOMP_CACHE",
            "ZTARE_LEANMILL_BANK_ENV_RATIFY",
            "ZTARE_LEANMILL_BANK_RUNGS_TO_THEORY",
            "ZTARE_LEANMILL_WARM_VERIFY",
            "ZTARE_LEANMILL_WARM_COMPILE",
            "ZTARE_LEANMILL_SUBSTRATE_GUARD",
            "ZTARE_LEANMILL_DIRECT_CONTINUE_TURNS",
            "ZTARE_LEANMILL_NOTES_LEMMA_S",
            "ZTARE_LEANMILL_NOTES_TARGET_S",
            "ZTARE_LEANMILL_CAMPAIGN_WALL_S",
        ]
        try:
            git_head = subprocess.check_output(
                ["git", "rev-parse", "--short=12", "HEAD"], cwd=REPO, text=True,
                stderr=subprocess.DEVNULL, timeout=3).strip()
        except Exception:
            git_head = ""
        manifest = {
            "schema": "leanmill.run_manifest.v1",
            "created_at_s": time.time(),
            "run_tag": run_tag,
            "run_scratch": scratch,
            "git_head": git_head,
            "blueprint": {
                "path": str(notes_path),
                "sha256": _sha256_file(notes_path) if notes_path.exists() else "",
                "launch_snapshot_path": str(blueprint_snapshot) if blueprint_snapshot_sha else "",
                "launch_snapshot_sha256": blueprint_snapshot_sha,
                "launch_snapshot_bytes": blueprint_snapshot_bytes,
            },
            "substrate": {
                "path": str(substrate) if substrate else "",
                "sha256": _sha256_file(substrate) if substrate and substrate.exists() else "",
            },
            "providers": _provider_manifest(),
            "launch_config": _launch_config_manifest(),
            "code_fingerprints": _code_fingerprints(),
            "authority_modes": {
                "proof_cache": os.environ.get("ZTARE_PROOF_CACHE", "1"),
                "exact_reference_reuse": os.environ.get("ZTARE_LEANMILL_REFERENCE_REUSE_STATEMENT", "1"),
                "decomposition_cache": os.environ.get("ZTARE_LEANMILL_DECOMP_CACHE", "1"),
                "staged_reuse": os.environ.get("ZTARE_LEANMILL_STAGED_REUSE", "1"),
                "proposer_pool": os.environ.get("ZTARE_LEANMILL_PROPOSER_POOL", "1"),
                "bank_env_ratify": os.environ.get("ZTARE_LEANMILL_BANK_ENV_RATIFY", "1"),
                "bank_rungs_to_theory": os.environ.get("ZTARE_LEANMILL_BANK_RUNGS_TO_THEORY", "1"),
            },
            "cache_authority_classes": {
                name: cache_authority(name).value
                for name in (
                    "proof_cache",
                    "exact_reference_reuse",
                    "decomposition_cache",
                    "staged_reuse",
                    "semantic_shelf",
                    "wip_probe",
                    "banked_rung",
                )
            },
            "env": {k: os.environ.get(k, "") for k in env_keys},
        }
        if substrate and substrate.exists():
            _substrate_text = substrate.read_text(encoding="utf-8", errors="replace")
            try:
                from ztare.leanmill.definition_contract import emit_definition_api_receipt
                manifest["definition_api_receipt"] = emit_definition_api_receipt(
                    _substrate_text,
                ).to_json()
            except Exception as exc:  # noqa: BLE001
                manifest["definition_api_receipt_error"] = str(exc)[:240]
            try:
                from ztare.leanmill.library_delta import emit_library_delta_receipt
                manifest["library_delta_receipt"] = emit_library_delta_receipt(_substrate_text).to_json()
            except Exception as exc:  # noqa: BLE001
                manifest["library_delta_receipt_error"] = str(exc)[:240]
        out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return out
    except Exception:
        return None


def _log_formalize_attempt(campaign_id: str, lemma_idx: int, rec: dict, phase: str) -> None:
    """FIX #2 (2026-07-06, operator "don't we have cot or debug on that"): campaign-scoped per-attempt formalize
    log so "was it the SAME render N times or did it vary, and why was each rejected" is a one-line query — not a
    40-line grep of the GLOBAL, all-campaigns-mixed `cot_traces.jsonl` (the observability gap that made a def-body
    divergence read as a generic reject). One line per attack (first pass + each retry): render_hash (⇒ dedup),
    render_head, outcome, reason. Best-effort; never breaks the loop."""
    try:
        import hashlib
        import time
        stmt = re.sub(r"\s+", " ", (rec.get("lean_statement") or "").strip())
        p = LEAN_ROOT_DEFAULT.parent / "analytics" / "public" / "queries" / "formalize_attempts.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": time.time(), "run_tag": campaign_id, "lemma_idx": lemma_idx, "phase": phase,
                "render_hash": hashlib.sha1(stmt.encode("utf-8")).hexdigest()[:10] if stmt else "",
                "render_head": stmt[:220], "outcome": rec.get("outcome"),
                "faithful": rec.get("faithful"), "solved": bool(rec.get("solved")),
                "reason": str(rec.get("faithfulness_reason") or "")[:240],
            }) + "\n")
    except Exception:  # noqa: BLE001 — telemetry is advisory; never break the campaign
        pass


def _falsify_bridge_marker(open_recs: "list[tuple]", lean_root: Path, timeout_s: int,
                           log=print) -> "tuple[str, str, Optional[int]]":
    """FIX #1 (2026-07-06, operator "wire to falsify indeed"): bridge a FORMALIZE-stage divergence deadlock into
    the EXISTING falsify recovery. A goal the firewall rejects for a substrate def-body DIVERGENCE means the
    formalizer kept STRENGTHENING a too-weak substrate def to render a TRUE goal (the gale flagship
    `quiescent_reachable_stable` was FALSE-AS-STATED — missing list-completeness `∀ w, w ∈ fullList m`). The
    falsify/reformulate recovery lives DOWNSTREAM at solve, so a goal blocked at FORMALIZE never reaches it and
    the self-correction round (which needs a `-- STATEMENT-FALSE:` marker the solve leaf drops) never fires —
    the goal churns silently. Bridge it: canonicalize the divergent render back to the substrate's canonical defs
    (`enforce_canonical_defs` — a function BUILT for exactly this but previously wired NOWHERE) and dispatch the
    EXISTING kernel-gated skeptic (`verify_statement_false_claim`). A genuine sorry-free ¬G ⇒ the registered goal
    really IS false → return (counterexample_block, false_lemma_nl, lemma_idx) so it SURFACES + the existing
    `governed_def_revision` self-correction can fire. Returns ("", "", None) when no open lemma is a divergence
    reject, or the canonicalized (substrate-faithful) goal is NOT falsifiable — i.e. the divergence was a
    WEAKENING / carrier-ghost, correctly left as a hard reject (never a false "it's false"). NEVER accepts
    anything (only reclassifies a reject + surfaces). Fail-safe; gated by ZTARE_LEANMILL_FALSIFY_ESCALATION=0."""
    try:
        from ztare.formal.repl_compile import get_campaign_substrate
        from ztare.leanmill.lean_source import enforce_canonical_defs
        from ztare.leanmill.solver.conjecture import verify_statement_false_claim
        sub = get_campaign_substrate()
        if not sub or not Path(sub).exists():
            return "", "", None
        sub_src = Path(sub).read_text(encoding="utf-8", errors="replace")
        for nl, rec, idx in open_recs:
            stmt = (rec.get("lean_statement") or "").strip()
            reason = str(rec.get("faithfulness_reason") or "")
            if "UNFAITHFUL to the registered substrate" not in reason or not stmt:
                continue
            canonical, swapped = enforce_canonical_defs(stmt, sub_src)
            if not swapped:                       # nothing canonicalized ⇒ not a bridgeable def-body divergence
                continue
            m = re.search(r"(?m)^\s*(?:noncomputable\s+|private\s+|@\[[^\]]*\]\s*)*"
                          r"(?:theorem|lemma)\s+(\w+)", canonical)
            if not m:
                continue
            confirmed, detail, refute = verify_statement_false_claim(
                m.group(1), canonical, "", Path(lean_root), min(int(timeout_s), 600))
            if confirmed and refute:
                log(f"  *** FALSIFY FIRED (formalize-divergence bridge): goal FALSE-AS-STATED — the registered "
                    f"`{', '.join(swapped)}` is too WEAK (kernel-checked ¬G confirms it). The formalizer's "
                    f"STRENGTHENING is the fix → routing to governed def-revision. [{detail[:100]}]")
                return refute, nl, idx
    except Exception as e:  # noqa: BLE001 — best-effort bridge; never break the campaign
        log(f"  (falsify bridge errored, no marker: {repr(e)[:110]})")
    return "", "", None


def parse_theory_file(text: str) -> "Optional[str]":
    """Parse the optional `## Theory file` section → the campaign-owned .lean path (#123, theory-first
    campaigns): the file the agent CREATES AND EXTENDS with definitions + API lemmas that Mathlib lacks —
    definitions as first-class work items (the NS-track manifest pattern transported to leanmill)."""
    m = re.search(r"(?ms)^##\s*Theory file\s*\n\s*(\S+\.lean)\s*$", text)
    return m.group(1) if m else None


def parse_domain(text: str) -> "Optional[str]":
    """Parse the optional `## Domain` line → the campaign-class label (e.g. `math`, `formalization-nonmath`) used
    by the factory time-to-closure read model to segment avg-time-to-closure by domain. First non-blank line of
    the section; None if absent (the caller falls back to ZTARE_SOLVER_DOMAIN, then 'unspecified')."""
    m = re.search(r"(?ms)^##\s*Domain\s*\n(.+?)(?=^##|\Z)", text)
    if not m:
        return None
    for ln in m.group(1).splitlines():
        if ln.strip():
            return ln.strip()
    return None


def parse_notes(text: str) -> "tuple[str, list[str]]":
    """Parse the `## Target` paragraph + the `- ` bullets under `## Lemmas`. Deterministic markdown-STRUCTURE
    parsing (not agent-output parsing — those use `agent_output`); the value is the formalize+attack loop, not
    a notes DSL. Tolerates `*` bullets and blank lines."""
    target = ""
    m = re.search(r"(?ms)^##\s*Target\s*\n(.+?)(?=^##|\Z)", text)
    if m:
        target = " ".join(l.strip() for l in m.group(1).strip().splitlines() if l.strip())
    lemmas: "list[str]" = []
    lm = re.search(r"(?ms)^##\s*Lemmas\s*\n(.+?)(?=^##|\Z)", text)
    if lm:
        lemmas = [re.sub(r"^[-*]\s*", "", l).strip() for l in lm.group(1).splitlines()
                  if l.strip().startswith(("-", "*"))]
    return target, lemmas


def _insert_lemmas_section(notes_text: str, bullets: "list[str]") -> str:
    """Splice `- <bullet>` items at the TOP of the `## Lemmas` section (foundational-first), creating the
    section if it is ABSENT. The ONE canonical notes-`## Lemmas` editor — callers must NOT re-roll
    `re.sub`/`re.search` on the heading (RCA 2026-06-18: a theory-first blueprint with no `## Lemmas` anchor
    silently DROPPED the agent's sorried API work-items, so the built theory was never proven). Line-based,
    no scattered regex; the heading test mirrors `parse_notes` (`##` then `Lemmas`, flexible spacing)."""
    if not bullets:
        return notes_text
    new = [f"- {b}" for b in bullets]
    lines = notes_text.splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("##") and s[2:].strip() == "Lemmas":      # the `## Lemmas` heading line
            return "\n".join(lines[:i + 1] + new + lines[i + 1:]) + "\n"
    return notes_text.rstrip() + "\n\n## Lemmas\n" + "\n".join(new) + "\n"   # absent → append the section


def _default_attack(nl: str, *, lean_root: Path, timeout_s: int, notes: "str | None" = None,
                    shelf_prelude: str = "") -> dict:
    """Real apparatus: one NL line → faithfulness firewall → governed solve → compact per-piece record.
    `notes` (the blueprint) threads into the recursive planner when the line does NOT close directly.
    `solved` is True ONLY when the governed outcome is `closed`. (`autoformalize_and_solve` puts the per-
    result outcome string in `solved`, so `exact_gap` / `open` are TRUTHY strings — taking `bool(outcome)`
    would mark an unproven gap as solved. That false-positive is fixed here at the source.)"""
    from ztare.leanmill.solver.autoformalize import autoformalize_and_solve
    from ztare.leanmill.contracts.kernel import AttackRecord   # #49: typed record — `solved` is a BOOL, decided
    r = autoformalize_and_solve(nl, sandbox=lean_root, timeout_s=timeout_s, notes=notes,
                                shelf_prelude=shelf_prelude)   # ONCE (outcome=="closed")
    # `.model_dump()` re-emits the exact legacy keys (nl/lean_statement/faithful/outcome/solved + the firewall
    # verdict reason/checks + the planner sub-DAG), so the notes loop + write-back are unchanged — but the
    # gap-as-solved false positive (`bool("exact_gap")` ⇒ True) is now impossible by construction.
    return AttackRecord.from_firewall_result(r, nl=nl).model_dump()


def _is_execution_stop(record: object) -> bool:
    """Identify a host/provider stop, which is neither a math negative nor an empty answer."""
    if not isinstance(record, dict):
        return False
    outcome = str(record.get("outcome") or "").strip().lower()
    reason = str(record.get("faithfulness_reason") or "").upper()
    return outcome in {
        "budget_exhausted",
        "provider_budget_exhausted",
        "inadmissible_provider_dead",
    } or "BUDGET_EXCEEDED" in reason or "BUDGET_EXHAUSTED" in reason


def _bullet_decl_name_candidates(bullet: str) -> "set[str]":
    """Declaration names explicitly carried by a Markdown lemma bullet.

    This is Markdown/input parsing, not Lean parsing. Lean names still come
    from `decl_blocks` below. The point is to recognize the common authoring
    forms:
      - `**(foo)** ...`        campaign convention
      - `` `foo`: ... ``       README/blueprint convention
      - `foo: ...`             compact queue convention
    """
    b = bullet or ""
    names: "set[str]" = set()
    name_pat = r"[A-Za-z_][\w.']*"
    for m in re.finditer(r"`(" + name_pat + r")`", b):
        names.add(m.group(1))
    for m in re.finditer(r"\((" + name_pat + r")\)", b):
        names.add(m.group(1))
    s = b.strip()
    m = re.match(r"^(?:\*\*)?`?(" + name_pat + r")`?(?:\*\*)?\s*:", s)
    if m:
        names.add(m.group(1))
    m = re.match(r"^(?:theorem|lemma)\s+(" + name_pat + r")\b", s)
    if m:
        names.add(m.group(1))
    return names


def _banked_lemma_reuse(bullet: str, lean_root) -> "Optional[str]":
    """BANKED-DECL REUSE (2026-06-25, operator "don't re-formalize, reuse"): if a lemma BULLET's intended decl
    name (`**(name)**`, the campaign naming convention) is ALREADY a PROVEN (sorry-free) decl in the registered
    campaign substrate, return its signature — the lemma is DONE, so re-formalizing+re-attacking it is pure waste
    AND the vocabulary-drift vector that orphans the shelf (the AMM RCA: a fresh formalization in a divergent form
    — `NoHistoryRoundTripArbitrage` predicate vs the unfolded conjunction — mismatches the banked one and the
    target then false-rejects). Returns the banked signature (citable shelf entry) or None.

    SOUND: this only SKIPS work + shelves an ALREADY-kernel-proven decl; it mints no closure. The target's own
    closure is still kernel-gated downstream, so a stale/mismatched blueprint can at worst leave the target as an
    honest gap — never a false closure.

    NO BRITTLE REGEX (operator): the decl names come from the canonical Lean parser (`decl_blocks` +
    `first_theorem_name`/`has_sorry` over the substrate), NOT a regex guess at the bullet. The bullet→decl link is
    the campaign `**(name)**` convention, matched with a plain substring test `f"({name})" in bullet` against the
    REAL banked names — deterministic, and it can only match a name that actually exists banked + sorry-free."""
    try:
        from ztare.formal.repl_compile import get_campaign_substrate
        cs = get_campaign_substrate()
        if not cs:
            return None
        src = Path(cs).read_text(encoding="utf-8", errors="replace")
        from ztare.leanmill.solver.statement_integrity import decl_blocks
        from ztare.leanmill.lean_source import DECL_START, signature_before_proof, first_theorem_name, has_sorry
        b = bullet or ""
        named = _bullet_decl_name_candidates(b)
        # SEMANTIC identity, not the brittle NAME (2026-07-05, operator "world-class semantic reuse — is it
        # semantic or what … siblings of how we cache"): route the "is this the same lemma?" check through the ONE
        # name-agnostic normalizer (`proof_cache.normalize_statement`) — the DOCUMENTED general rule (faithfulness
        # `confirms()`, the structural + def-faithfulness legs already route through it; THIS reuse door was the
        # missed sibling). A generic bullet `iso_lemma1` then recognizes the substrate's content-stable-mangled
        # `iso_lemma1__89847c75` (proven, sorry-free) as THE SAME statement and SHELVES it — the ROOT cure for
        # "the campaign re-litigates proven lemmas through the cited-rung governance seam (where get_campaign_
        # substrate is None) and never CLOSES". The `(name)` substring stays a fast path. SOUND: reuse only
        # SHELVES an ALREADY-kernel-proven decl; a wrong match fails when the target CITES it and won't compile
        # (caught downstream — never a false closure), the same argument as the confirms() short-circuit.
        from ztare.leanmill.solver.proof_cache import normalize_statement as _ns
        _bnorm = _ns(b)
        for n, blk in decl_blocks(src):
            if has_sorry(blk):
                continue
            m_kind = DECL_START.match((blk or "").lstrip())
            if not m_kind or m_kind.group(1) not in ("theorem", "lemma"):
                continue
            short = first_theorem_name(blk) or str(n).split(".")[-1]
            decl_names = {str(n), str(n).split(".")[-1], short, str(short).split(".")[-1]}
            _sig = signature_before_proof(blk) or ""
            if ((named and any(x in named for x in decl_names if x))
                    or (short and (f"({short})" in b))
                    or (not named and _bnorm and _sig and _ns(_sig) == _bnorm)):
                return " ".join(_sig.split())
        return None
    except Exception:  # noqa: BLE001 — reuse is an optimization; any failure ⇒ fall through to the normal attack
        return None


def _campaign_door_warning(*, attack_injected: bool, target: str) -> "str | None":
    """MISLAUNCH REPORTER (2026-07-02, the §4.3.0 trap's sibling caught live on the ftap_hard run): calling
    `autoformalize_from_notes()` bare skips everything the module `main()` arms — instrument standards
    (fail-closed), embedder/round-trip liveness, run_tag/domain attribution, theory consolidation, and the warm
    substrate — so the run proves DEGRADED (no shelf/vocab surfacing, no warm-verify, unattributable P0) while
    looking healthy. Returns the one warning line, or None for every LEGITIMATE direct use:
      · an injected attack_fn (hermetic tests / selftests drive the loop with a stub);
      · ZTARE_SOLVER_RUN_TAG already set (main() or an A/B harness armed the run);
      · no campaign shape (no `## Target` parsed — not a campaign at all).
    ADVISORY ONLY (Gate/Reporter/Move): the caller logs it and proceeds; soundness never depended on the arming
    (the kernel gates regardless) — this guards against silent DEGRADATION, not unsoundness.
    `ZTARE_LEANMILL_DOOR_GUARD=0` reverts. solve_adhoc's single-target entry is deliberately untouched."""
    import os as _o
    if _o.environ.get("ZTARE_LEANMILL_DOOR_GUARD", "1") == "0":
        return None
    if attack_injected or _o.environ.get("ZTARE_SOLVER_RUN_TAG") or not (target or "").strip():
        return None
    return ("⚠ campaign-door: autoformalize_from_notes() called WITHOUT the campaign door (no run_tag) — "
            "instrument standards / liveness probes / theory consolidation / substrate arming were NOT run, so "
            "reuse and attribution are silently degraded. Launch campaigns via "
            "`leanmill campaign <blueprint.md>` (the sanctioned CLI). Proceeding (advisory).")


def _run_closures_dir() -> Path:
    """The run-scratch-ISOLATED closures dir where the solver writes closure certs — `.solver_scratch/<run_tag>/
    closures` when `ZTARE_LEANMILL_RUN_SCRATCH` is set, else `.solver_scratch/closures`. THE single resolver the
    solver-writer + `promote --run-tag` reader already share (`agentic_leaf.probe_dir`). The P0-sidecar + auto-
    promote had hardcoded the NON-isolated `.solver_scratch/closures` — a path that predates run-scratch isolation
    (2026-07-02) — so under an isolated run (every `leanmill campaign`) the P0 landed in the wrong dir and the
    auto-promote's `_cert.exists()` guard silently FAILED before any log line → the verified close never staged its
    filed artifact (corpgov, 2026-07-03). Route all three through here so the write/read paths can never drift."""
    from ztare.leanmill.solver.agentic_leaf import probe_dir as _pd
    return _pd(LEAN_ROOT_DEFAULT) / "closures"


def _modeling_faithfulness_audit(res: dict, theory_rel: "Optional[str]", lean_root: Path, *,
                                 log=print) -> None:
    """Attach theory-first modeling-faithfulness receipts to `res`.

    The statement firewall handles NL↔target faithfulness. Theory-first runs
    also introduce local definitions, so publication staging needs the
    denotation/non-vacuity receipts before it decides whether to file a
    review artifact. This helper is receipt-only: it never flips
    `target.solved`.
    """
    import os as _os
    if not theory_rel or _os.environ.get("ZTARE_LEANMILL_DENOTATION_CHECK", "1") == "0":
        return
    try:
        from ztare.leanmill.solver.def_denotation import (
            certify_def_denotation, kernel_denotation_verifier, mentions_token)
        tp = lean_root / theory_rel
        theory_final = tp.read_text(encoding="utf-8") if tp.exists() else ""
        if not theory_final.strip():
            return
        from ztare.leanmill import lean_source as _lsd
        built = _lsd.def_names(theory_final)
        proof_blob = "\n".join((d.get("closure_lean") or "") + "\n" + (d.get("statement") or "")
                               for d in res.get("deep_closures", []))
        for rec in res.get("lemmas", []):
            if isinstance(rec, dict) and rec.get("solved"):
                proof_blob += "\n" + "\n".join(str(rec.get(k) or "") for k in
                                                ("closure_lean", "proof_text", "lean_statement", "statement"))
        tgt = res.get("target") or {}
        proof_blob += "\n" + "\n".join(str(tgt.get(k) or "") for k in
                                        ("closure_lean", "proof_text", "lean_statement", "statement"))
        composed = {d for d in built if mentions_token(proof_blob, d)}
        verify = kernel_denotation_verifier(theory_final, lean_root)
        den = certify_def_denotation(theory_final, verify_anchor_fn=verify, composed_defs=composed)
        res["denotation"] = den
        log(f"[notes] denotation-faithfulness: {den['verdict']} — {den['reason']}")
        if _os.environ.get("ZTARE_LEANMILL_VACUITY_CHECK", "1") != "0":
            from ztare.leanmill.solver.def_denotation import certify_nonvacuity
            vac = certify_nonvacuity(theory_final, verify_fn=verify)
            res["nonvacuity"] = vac
            log(f"[notes] vacuity-faithfulness: {vac['verdict']} — {vac['reason']}")
    except Exception as e:  # noqa: BLE001
        res["denotation_error"] = repr(e)[:240]
        log(f"[notes] denotation/vacuity check skipped: {repr(e)[:120]}")


def _auto_promote_blockers(res: dict, theory_rel: "Optional[str]") -> "list[str]":
    """Reasons a closed campaign should not auto-stage a publish-review file."""
    import os as _os
    if _os.environ.get("ZTARE_LEANMILL_ALLOW_UNPINNED_AUTO_PROMOTE", "0") == "1":
        return []
    if not theory_rel or _os.environ.get("ZTARE_LEANMILL_DENOTATION_CHECK", "1") == "0":
        return []
    try:
        from ztare.leanmill.policy import faithfulness_promotion_policy
        pol = faithfulness_promotion_policy()
    except Exception:  # noqa: BLE001
        pol = {
            "require_def_denotation_receipt_for_auto_promote": True,
            "require_pinned_def_denotation_for_auto_promote": True,
            "block_refuted_def_denotation_auto_promote": True,
            "block_vacuity_exposed_auto_promote": False,
        }
    blockers: "list[str]" = []
    den = res.get("denotation") if isinstance(res.get("denotation"), dict) else None
    verdict = str((den or {}).get("verdict") or "")
    if pol.get("require_def_denotation_receipt_for_auto_promote", True) and not verdict:
        blockers.append("missing denotation-faithfulness receipt")
    if verdict == "REFUTED" and pol.get("block_refuted_def_denotation_auto_promote", True):
        blockers.append(str((den or {}).get("reason") or "def denotation refuted"))
    if verdict == "UNDERDETERMINED" and pol.get("require_pinned_def_denotation_for_auto_promote", True):
        blockers.append(str((den or {}).get("reason") or "def denotation underdetermined"))
    vac = res.get("nonvacuity") if isinstance(res.get("nonvacuity"), dict) else None
    if (str((vac or {}).get("verdict") or "") == "VACUITY_EXPOSED"
            and pol.get("block_vacuity_exposed_auto_promote", False)):
        blockers.append(str((vac or {}).get("reason") or "vacuity exposed"))
    return blockers


def autoformalize_from_notes(notes_text: str, *, lean_root: Optional[Path] = None,
                             lemma_timeout_s: "Optional[int]" = None, target_timeout_s: "Optional[int]" = None,
                             attack_fn: Optional[Callable[..., dict]] = None,
                             notes_path: Optional[Path] = None,
                             on_progress: Optional[Callable[[str], None]] = None) -> dict:
    """Blueprint-decomposition loop: parse notes → prove each lemma through the firewall+kernel → accumulate
    a citable proven-lemma SHELF → attack the target. Every leg is injectable so the selftest is hermetic:
    `attack_fn(nl, *, lean_root, timeout_s, notes) -> record` defaults to `_default_attack` (the real apparatus);
    `on_progress(msg)` defaults to print. Returns
        {target_nl, lemmas:[record], target:record|None, shelf:[lean_statement of CLOSED lemmas], summary}.
    Wiring the shelf into the target solve as cited premises is the planner / composite-ratification path."""
    lean_root = Path(lean_root) if lean_root is not None else LEAN_ROOT_DEFAULT
    _attack_injected = attack_fn is not None      # captured BEFORE the default: an injected attack_fn marks a
    attack_fn = attack_fn or _default_attack      # hermetic/self-test caller, which the door guard must not nag
    log = on_progress or (lambda m: print(m, flush=True))
    # GENEROUS whole-attack wallclocks from the central factory (NOT hardcoded 400/600 — those guillotined a
    # codex run that had an audit-passing DAG ready). The planner draws from these (no arbitrary sub-cap);
    # env-tunable + self-learnable. Caller can still override explicitly.
    if lemma_timeout_s is None or target_timeout_s is None:
        from ztare.common.timeouts import timeout_s as _tbudget
        lemma_timeout_s = _tbudget("notes_lemma") if lemma_timeout_s is None else lemma_timeout_s
        target_timeout_s = _tbudget("notes_target") if target_timeout_s is None else target_timeout_s

    target, lemmas = parse_notes(notes_text)
    # GLOBAL CAMPAIGN WALL (2026-06-13 — the "v6 ran 6 hours" RCA): the per-lemma/per-target budgets are
    # GENEROUS by design, but with deep recursion (ZTARE_ISO_MAX_DEPTH) their SUM across the tree is
    # effectively unbounded — v6 closed the easy rungs in 3h then ground the open-math crux for 3 more
    # (7 codex timeouts, 0 closures). This caps TOTAL wall: once the deadline passes, remaining lemmas/
    # target are SKIPPED as deferred (recorded honestly, never a fake closure). The earned rungs are
    # already kill-safe (incremental write-back below). 0 = disabled (parity). Default = generous so a
    # healthy run is never guillotined, but a grind-on-the-wall run STOPS instead of burning the night.
    import os as _os_w
    import time as _time_w
    _wall_s = int(_os_w.environ.get("ZTARE_LEANMILL_CAMPAIGN_WALL_S", "14400") or 0)   # 4h default
    _deadline = (_time_w.monotonic() + _wall_s) if _wall_s > 0 else None

    def _wall_exceeded() -> bool:
        return _deadline is not None and _time_w.monotonic() >= _deadline
    try:                                          # record the in-force time budgets up front (observability:
        from ztare.common.timeouts import budgets_report   # a stalled run's banner shows which budget governed)
        log(f"[budgets] {budgets_report()}")
        if _deadline is not None:
            log(f"[notes] global campaign wall: {_wall_s}s (deferred-skip past it; 0 disables)")
    except Exception:  # noqa: BLE001
        pass
    log(f"[notes] target: {target!r}")
    log(f"[notes] {len(lemmas)} lemma(s) (foundational first)")
    # BLUEPRINT LINT (§4.2a REPORTER, 2026-07-01): surface authoring smells (definition-bullets, typed-in
    # formalization restrictions, missing sections) at campaign START, when the maintainer can still fix the
    # blueprint — NEVER blocks (Gate/Reporter/Move law: a blueprint fault at worst wastes wall; the kernel
    # still gates every closure). Default-on; "0" disables. try/except so a lint crash can't touch a campaign.
    if _os_w.environ.get("ZTARE_LEANMILL_BLUEPRINT_LINT", "1") != "0":
        try:
            from ztare.leanmill.blueprint_lint import lint_blueprint
            for _w in lint_blueprint(notes_text):
                log(f"[notes] blueprint-lint ⚠ [{_w['rule']}] {_w['msg']}")
        except Exception:  # noqa: BLE001 — advisory only; a lint failure must never affect the campaign
            pass
    _dw = _campaign_door_warning(attack_injected=_attack_injected, target=target)
    if _dw:
        log(f"[notes] {_dw}")

    from datetime import datetime as _dt2, timezone as _tz2
    out: dict = {"target_nl": target, "lemmas": [], "shelf": [],
                 # cert-ledger watermark for the KILL-SAFE incremental deep-rung surfacing (same ISO-UTC
                 # format solve_adhoc stamps cert `ts` with — lexicographic compare is valid)
                 "run_started": _dt2.now(_tz2.utc).isoformat()}
    # PHASE B (opt-in): multi-node lemma partitioning over the shared work bus (work_queue). Default-off
    # ⇒ this block is inert and the loop is byte-identical to single-node. When on, each node leases a
    # lemma before attacking it and skips lemmas a peer owns — peers' proofs converge via the fact-log
    # merge (state_convergence), so a skip is never lossy. Safety is already guaranteed by that merge;
    # this only removes the redundant re-proving. See solver/campaign_coordination.py.
    from ztare.leanmill.solver import campaign_coordination as _coord
    _dist = _coord.distributed_enabled()
    _campaign_id = _os_w.environ.get("ZTARE_SOLVER_RUN_TAG") or "campaign"
    if _dist:
        log(f"[notes] DISTRIBUTED lemma mode ON (node={_coord.node()}, campaign={_campaign_id!r}) — "
            f"lemmas leased via the work bus; peers' results converge via the fact-log merge")
    out["distributed"] = _dist
    out["wall_deferred"] = []
    out["execution_stop"] = None
    # CAMPAIGN-START P0 FORECAST (2026-06-25): before spending the wall, PREDICT expected yield + time-to-closure
    # from the DOMAIN's historical P0 (phase_timing read-models) via the Brier-calibrated forecast router — an
    # admissibility/budget signal AND a prediction PRE-REGISTERED to a ledger, scored ex-post against the actual
    # (the self-learning loop; forecast_router.reweight recalibrates). v1 uses the domain close-rate as a flat
    # per-lemma prior (full per-candidate price() is a refinement). Best-effort; never blocks the campaign.
    try:
        from ztare.leanmill.solver.forecast_router import forecast_campaign_p0, domain_p0_history
        _dom = (parse_domain(notes_text) or _os_w.environ.get("ZTARE_SOLVER_DOMAIN", "") or "unspecified").strip()
        _hist = domain_p0_history(_dom)
        _cr = _hist.get("close_rate")
        _p = [(_cr if _cr is not None else 0.5)] * max(1, len(lemmas))
        _fc = forecast_campaign_p0(_p, domain=_dom, domain_mean_ttc_s=_hist.get("mean_ttc_s"),
                                   domain_mean_cost_s=_hist.get("mean_cost_s"))
        out["p0_forecast"] = _fc
        log(f"[notes] P0 FORECAST (domain={_dom!r}, {_hist.get('n_campaigns', 0)} prior campaigns): "
            f"expected yield {_fc['expected_yield']}/{_fc['n_candidates']}"
            + (f" · ~{_fc['expected_time_to_closure_s']}s to close" if _fc.get('expected_time_to_closure_s')
               else " · no time-history yet (cold start)")
            + (f" · hardest lemma #{(_fc['hardest_lemma_index'] or 0) + 1}"
               if _fc.get('hardest_lemma_index') is not None else ""))
        try:                                  # PRE-REGISTER the prediction (scored ex-post — the learning loop)
            import json as _j0
            _led = LEAN_ROOT_DEFAULT.parent / "analytics" / "public" / "queries" / "campaign_p0_forecasts.jsonl"
            _led.parent.mkdir(parents=True, exist_ok=True)
            with _led.open("a", encoding="utf-8") as _f0:
                _f0.write(_j0.dumps({"run_tag": _campaign_id, "ts": out["run_started"], **_fc}) + "\n")
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001 — the forecast is advisory; never block the campaign
        pass
    for i, lem in enumerate(lemmas):
        if _wall_exceeded():
            log(f"[notes] *** CAMPAIGN WALL reached — deferring lemma {i + 1}/{len(lemmas)} and the rest "
                f"(earned rungs already written back; not a failure) ***")
            out["wall_deferred"] = [str(x) for x in lemmas[i:]]
            break
        if _dist:
            try:
                _owned = _coord.claim_lemma(_campaign_id, str(lem), lease_s=2 * lemma_timeout_s)
            except Exception:  # noqa: BLE001 — queue unavailable ⇒ prove it (the merge dedups redundant work)
                _owned = True
            if not _owned:
                log(f"[notes] lemma {i + 1}/{len(lemmas)} owned by another node — skipping (converges via merge)")
                continue
        log(f"[notes] lemma {i + 1}/{len(lemmas)}: {lem!r}")
        # (b) BANKED-DECL REUSE (2026-06-25): if this lemma's intended name is ALREADY a sorry-free decl in the
        # registered substrate, it is DONE — skip the re-formalize+attack (the waste + vocab-drift vector the
        # operator flagged) and shelf the banked signature so the target can cite it. Default-on; =0 reverts.
        _reuse = None
        if _os_w.environ.get("ZTARE_LEANMILL_REUSE_BANKED_LEMMAS", "1") != "0":
            _reuse = _banked_lemma_reuse(lem, lean_root)
        if _reuse:
            log(f"  -> REUSED from bank (already proven in substrate; skipped re-formalize+attack): {_reuse[:90]}")
            out["lemmas"].append({"solved": "reused_from_bank", "lean_statement": _reuse,
                                  "outcome": "reused_from_bank", "faithful": True})
            out["shelf"].append(_reuse)
            if _dist:
                try:
                    _coord.complete_lemma(_campaign_id, str(lem), solved=True)
                except Exception:  # noqa: BLE001
                    pass
            continue
        # SUBSTRATE HEALTH GATE (2026-07-03 fix-forever for the silent substrate-death class): a mid-run write (a
        # fragile `by aesop` target stub, a bad bank) can leave the substrate NON-COMPILING → the campaign verify
        # env goes DEAD → CORRECT proofs false-reject → the run SPINS degraded (the EF1 lemma-4 saga). Before each
        # attack, verify the substrate compiles; AUTO-REVERT to the last-good snapshot on a break (LOUD, never a
        # silent degrade). Cheap: the warm env is cached on unchanged mtime, so a healthy substrate is ~free.
        try:
            from ztare.formal.repl_compile import get_campaign_substrate, guard_substrate_compiles
            _sub_h = get_campaign_substrate()
            if _sub_h and not guard_substrate_compiles(_sub_h, lean_root, log=log):
                log(f"[notes] ⚠️ substrate DEAD before lemma {i + 1}/{len(lemmas)} and no snapshot to revert — "
                    f"attacking anyway but citing/warm-verify will degrade; FIX THE SUBSTRATE.")
        except Exception:  # noqa: BLE001 — the health gate is best-effort; never break the campaign
            pass
        # the WHOLE blueprint is the planner context for each lemma (the surrounding lemmas are scaffold)
        rec = attack_fn(lem, lean_root=lean_root, timeout_s=lemma_timeout_s, notes=notes_text)
        out["lemmas"].append(rec)
        _log_formalize_attempt(_campaign_id, i, rec, "first_pass")   # FIX #2 (per-attempt observability)
        if rec.get("solved"):
            out["shelf"].append(rec.get("lean_statement") or "")
        if _dist:
            try:                                  # done → terminal; unsolved → released for a peer to retry
                _coord.complete_lemma(_campaign_id, str(lem), solved=bool(rec.get("solved")))
            except Exception:  # noqa: BLE001 — coordination is best-effort, never breaks the solve
                pass
        log(f"  -> faithful={rec.get('faithful')} outcome={rec.get('outcome')} solved={rec.get('solved')}"
            # OBSERVABILITY (2026-06-24): show the reason on ANY non-closure, not only when faithful≠True — a
            # firewall reject with faithful=True (e.g. a def-shell / triviality verdict) was previously SILENT, so
            # a gate false-positive hid across a whole campaign instead of surfacing on the first lemma.
            + (f" | reason={str(rec.get('faithfulness_reason'))[:240]}"
               if (not rec.get('solved') and rec.get('faithfulness_reason')) else ""))
        if _is_execution_stop(rec):
            # A host reservation stop is not a mathematical result.  Leave
            # untouched work queued and avoid retry/falsify/target dispatches.
            out["execution_stop"] = str(
                rec.get("outcome") or rec.get("faithfulness_reason") or "execution_stop"
            )
            out["wall_deferred"] = [str(x) for x in lemmas[i + 1:]]
            log(
                f"[notes] execution stop after lemma {i + 1}/{len(lemmas)} — "
                f"deferred {len(out['wall_deferred'])} untouched item(s)"
            )
            break
        if notes_path is not None:               # INCREMENTAL write-back — survive a timeout/kill. The end-of-run
            try:                                 # write was LOST when the 100-min budget killed the run mid-solve;
                # KILL-SAFE deep rungs (v3/v4 lesson: killed runs are the NORM, not the exception): surface
                # all-depth kernel closures so far + compound the rungs-only section into the ORIGINAL notes
                # NOW (idempotent, sha-deduped, never clobbers ## Lemmas) — a kill after this point loses
                # nothing. The in-flight run is unaffected (it parsed notes_text at entry).
                out["deep_closures"] = deep_closures_since(out["run_started"])
                write_refined_notes(out, notes_path)   # re-emits the deterministic ✅-closed shelf after every
                if out["deep_closures"]:               # lemma (cheap; no warm-agent synthesis — main() adds that).
                    compound_into_original_notes({"target": None, "lemmas": [],
                                                  "deep_closures": out["deep_closures"]}, notes_path)
            except Exception:  # noqa: BLE001
                pass

    # AGENCY (#132 skip-and-return): a lemma that failed EARLY may close now that LATER lemmas proved —
    # their closures grew the citable shelf, which can unblock the earlier wall (a mathematician returns
    # to a stuck lemma after proving its neighbours). The fixed-order single pass couldn't do this. ONE
    # retry pass over the still-open lemmas, with the GROWN shelf in context, wall-respecting. Default-on
    # (sound knob — every retry still goes through the full firewall+kernel); ZTARE_LEANMILL_NOTES_RETRY=0
    # reverts to the single pass. Bounded (one pass) so it can't loop; the campaign wall caps total time.
    if (not out.get("execution_stop")
            and _os_w.environ.get("ZTARE_LEANMILL_NOTES_RETRY", "1") != "0"
            and out["shelf"] and not _wall_exceeded()):
        _open_idx = [i for i, l in enumerate(out["lemmas"]) if not l.get("solved")]
        if _open_idx:
            _shelf_notes = (notes_text.rstrip() + "\n\n## Proven lemmas (citable):\n"
                            + "\n".join(f"- {s}" for s in out["shelf"] if s))
            log(f"[notes] skip-and-return: retrying {len(_open_idx)} still-open lemma(s) with the grown "
                f"shelf ({len(out['shelf'])} proven) — a neighbour's closure may unblock them")
            for i in _open_idx:
                if _wall_exceeded():
                    log("[notes] skip-and-return: wall reached — stopping retries (earned rungs written back)")
                    break
                rec2 = attack_fn(lemmas[i], lean_root=lean_root, timeout_s=lemma_timeout_s, notes=_shelf_notes)
                _log_formalize_attempt(_campaign_id, i, rec2, "retry")   # FIX #2 (per-attempt observability)
                if _is_execution_stop(rec2):
                    out["execution_stop"] = str(
                        rec2.get("outcome") or rec2.get("faithfulness_reason") or "execution_stop"
                    )
                    out["wall_deferred"] = [str(x) for x in lemmas[i:]]
                    break
                if rec2.get("solved"):
                    out["lemmas"][i] = rec2
                    out["shelf"].append(rec2.get("lean_statement") or "")
                    log(f"[notes] *** skip-and-return CLOSED lemma {i + 1}/{len(lemmas)} on retry "
                        f"(unblocked by the grown shelf) ***")
                    if notes_path is not None:                 # kill-safe incremental write-back (as main loop)
                        try:
                            out["deep_closures"] = deep_closures_since(out["run_started"])
                            write_refined_notes(out, notes_path)
                            if out["deep_closures"]:
                                compound_into_original_notes({"target": None, "lemmas": [],
                                                              "deep_closures": out["deep_closures"]}, notes_path)
                        except Exception:  # noqa: BLE001
                            pass

    # FIX #1 (2026-07-06, operator "wire to falsify indeed"): FORMALIZE-divergence → FALSIFY bridge. A goal the
    # firewall rejected for a substrate def-body divergence (the formalizer STRENGTHENING a too-weak substrate def
    # to render it TRUE) never reaches the solve-stage falsify recovery, so a FALSE-AS-STATED goal churns silently
    # (the gale flagship spun here). Dispatch the kernel-gated skeptic on the canonicalized render: a genuine ¬G ⇒
    # SURFACE it loudly (the actionable "your target is FALSE, `{def}` too weak" a silent rejected_by_firewall hid)
    # + hand the marker to the self-correction below. Gated (=0 reverts), fail-safe, NEVER accepts anything.
    _falsify_marker = ""
    _falsify_nl = ""
    if (not out.get("execution_stop")
            and _os_w.environ.get("ZTARE_LEANMILL_FALSIFY_ESCALATION", "1") != "0"
            and not _wall_exceeded()):
        _open_fb = [(str(lemmas[i]), out["lemmas"][i], i)
                    for i, l in enumerate(out["lemmas"]) if not l.get("solved")]
        if _open_fb:
            _falsify_marker, _falsify_nl, _fb_idx = _falsify_bridge_marker(
                _open_fb, lean_root, lemma_timeout_s, log=log)
            if _falsify_marker and _fb_idx is not None:
                out["lemmas"][_fb_idx]["outcome"] = "target_false_as_stated"
                out["lemmas"][_fb_idx]["faithfulness_reason"] = (
                    "FALSE-AS-STATED (falsify fired at the formalize-divergence bridge): "
                    + str(out["lemmas"][_fb_idx].get("faithfulness_reason", ""))[:180])
                out["target_false_as_stated"] = {"lemma_nl": _falsify_nl,
                                                 "counterexample": _falsify_marker[:2000]}

    # SELF-CORRECTION (supersession-acting, 2026-06-23): if lemmas remain OPEN and a lemma was kernel-CONFIRMED
    # FALSE (a `-- STATEMENT-FALSE:` marker survives in this run's scratch), a DEFINITION it cites is too WEAK.
    # Run ONE governed def-revision round — the agent STRENGTHENS the implicated def, GATED so only a kernel-
    # proven strengthening passes (never a laundering) — then re-attack the open lemmas with the strengthened
    # theory. Bounded (one round → can't loop), default-on (sound: the gate + kernel are the boundary), wall-
    # respecting, fail-safe (never breaks the campaign). ZTARE_LEANMILL_SELF_CORRECT_DEFS=0 reverts.
    _theory_rel_sc = parse_theory_file(notes_text)
    if (not out.get("execution_stop")
            and _os_w.environ.get("ZTARE_LEANMILL_SELF_CORRECT_DEFS", "1") != "0" and _theory_rel_sc
            and not _wall_exceeded()):
        _open_sc = [i for i, l in enumerate(out["lemmas"]) if not l.get("solved")]
        _marker = ""
        if _open_sc:
            try:
                from ztare.leanmill.solver.agentic_leaf import (scan_probes_for_statement_false,
                                                                probe_dir as _pdir_sc, default_dispatch as _dd_sc)
                _marker = scan_probes_for_statement_false(_pdir_sc(lean_root))
            except Exception:  # noqa: BLE001
                _marker = ""
        # NOTE (2026-07-06, operator "no more iatrogenic changes in kernel"): the formalize-divergence FALSIFY
        # bridge above is SURFACE-ONLY — it flags a false-as-stated target loudly (out["target_false_as_stated"])
        # but does NOT feed governed_def_revision, so it never auto-edits the substrate. A human fixes the
        # blueprint (uplevel NL). This self-correction still fires on a genuine SOLVE-stage `-- STATEMENT-FALSE:`
        # marker (existing behaviour), which is the vetted path.
        if _open_sc and _marker:
            log(f"[notes] SELF-CORRECT: a lemma was kernel-confirmed FALSE (marker: {_marker[:80]!r}) → governed "
                f"def-revision (strengthen the too-weak def; gated — only a proven strengthening passes)")
            try:
                _rev = governed_def_revision(_theory_rel_sc, lean_root=lean_root, dispatch=_dd_sc,
                                             false_lemma=str(lemmas[_open_sc[0]]), counterexample=_marker)
            except Exception as _e:  # noqa: BLE001 — self-correction is best-effort; never break the campaign
                _rev = {"ok": False, "reason": f"revision error: {repr(_e)[:120]}"}
            out["def_revision"] = _rev
            log(f"[notes] def-revision: ok={_rev.get('ok')} revised={_rev.get('revised_def')} — "
                f"{str(_rev.get('reason',''))[:170]}")
            if _rev.get("ok") and not _wall_exceeded():
                try:   # the theory file changed → re-register the warm-env substrate before re-attacking
                    from ztare.formal.repl_compile import set_campaign_substrate
                    _tp_sc = lean_root / _theory_rel_sc
                    if _tp_sc.exists():
                        set_campaign_substrate(str(_tp_sc.resolve()))
                except Exception:  # noqa: BLE001
                    pass
                for i in _open_sc:
                    if _wall_exceeded():
                        break
                    rec_sc = attack_fn(lemmas[i], lean_root=lean_root, timeout_s=lemma_timeout_s, notes=notes_text)
                    if _is_execution_stop(rec_sc):
                        out["execution_stop"] = str(
                            rec_sc.get("outcome") or rec_sc.get("faithfulness_reason") or "execution_stop"
                        )
                        out["wall_deferred"] = [str(x) for x in lemmas[i:]]
                        break
                    if rec_sc.get("solved"):
                        out["lemmas"][i] = rec_sc
                        out["shelf"].append(rec_sc.get("lean_statement") or "")
                        log(f"[notes] *** SELF-CORRECT CLOSED lemma {i + 1}/{len(lemmas)} after strengthening "
                            f"`{_rev.get('revised_def')}` ***")

    # the TARGET gets the blueprint PLUS the proven shelf — the planner sees which lemmas are already citable
    target_notes = notes_text
    if out["shelf"]:
        target_notes = (notes_text.rstrip() + "\n\n## Proven lemmas (citable):\n"
                        + "\n".join(f"- {s}" for s in out["shelf"] if s))
    # COMPOSITION FIX (2026-06-23): put the proven shelf lemmas IN COMPILE SCOPE for the target solve, so the
    # agent can CITE them by name (a true dependency graph) instead of re-deriving them inline — the dead-code
    # gap on FTAP. Before this, "Proven lemmas (citable)" was text-only; the standalone target probe never had
    # the names in scope, so inlining was the agent's ONLY compiling option. Name-filtered to THIS run (a
    # concurrent campaign shares the cert ledger).
    target_shelf_prelude = ""
    if out["shelf"]:
        try:
            target_shelf_prelude = _run_shelf_prelude(out, out.get("run_started", ""))
        except Exception:  # noqa: BLE001 — composition is additive; never break the target attack
            target_shelf_prelude = ""
    if out.get("execution_stop"):
        log("[notes] execution stop — deferring the TARGET attack (no additional provider dispatch)")
        if target:
            out["wall_deferred"].append(str(target))
        out["target"] = {
            "deferred": "execution_stop",
            "solved": False,
            "outcome": str(out["execution_stop"]),
        }
    elif target and _wall_exceeded():
        log("[notes] *** CAMPAIGN WALL reached — deferring the TARGET attack (proven rungs are written "
            "back; the target stays HONESTLY OPEN, never a fake closure) ***")
        out["wall_deferred"].append(str(target))
        out["target"] = {"deferred": "campaign_wall", "solved": False}
    else:
        log(f"[notes] TARGET: {target!r}"
            + (f" (shelf in scope: {target_shelf_prelude.count('theorem ') + target_shelf_prelude.count('lemma ')} proven lemmas citable)"
               if target_shelf_prelude.strip() else ""))
        out["target"] = (attack_fn(target, lean_root=lean_root, timeout_s=target_timeout_s, notes=target_notes,
                                   shelf_prelude=target_shelf_prelude)
                         if target else None)
    # RESOLVE target_theorem_name (2026-07-02 RCA — the P0-sidecar + auto-promote at RATIFICATION silently SKIPPED).
    # Both ratification-time automations key on `out["target"]["target_theorem_name"]` to locate `closures/<name>.lean`
    # / the banked decl — but `attack_fn` returns no such field, and an iso-route target is formalized under the
    # planner's GENERIC `iso_lemmaN` (its closure lands at `closures/iso_lemma1.lean`). With the name empty, the
    # `if _tname …` / `if _tn_ap …` guards no-op'd, so a ratified target neither stamped its P0 sidecar nor auto-staged.
    # Resolve the name from the formalized `lean_statement` via the comment-safe `first_theorem_name` so both fire.
    # Only fills when absent (respects an explicit name); best-effort (never blocks the campaign).
    if isinstance(out.get("target"), dict) and not str(out["target"].get("target_theorem_name") or "").strip():
        try:
            from ztare.leanmill.lean_source import first_theorem_name as _ftn_tgt
            _resolved_tn = _ftn_tgt(out["target"].get("lean_statement") or "")
            if _resolved_tn:
                out["target"]["target_theorem_name"] = _resolved_tn
                log(f"[notes] resolved target_theorem_name='{_resolved_tn}' from lean_statement "
                    f"(enables the P0-sidecar + auto-promote at ratification)")
        except Exception:  # noqa: BLE001 — name resolution is best-effort; never block the campaign
            pass
    if out["target"]:
        t = out["target"]
        log(f"  -> faithful={t.get('faithful')} outcome={t.get('outcome')} solved={t.get('solved')}"
            # OBSERVABILITY (2026-06-24): reason on ANY non-closure (see the per-lemma log above).
            + (f" | reason={str(t.get('faithfulness_reason'))[:240]}"
               if (not t.get('solved') and t.get('faithfulness_reason')) else ""))

    # FINAL-TARGET PERSISTENCE AUDIT (RCA 2026-06-25, fix #3): the per-rung bank guard already audits the target
    # in the persisted env, but make the campaign DOUBLY honest — re-`#print axioms` the target's banked decl
    # against the FULL theory file. A `sorryAx` here (the assembled proof bound to a still-sorried sibling in the
    # persistence world, which the probe-world audit can miss — the two-verify-worlds class) DOWNGRADES
    # "closed" → an honest gap, loudly. Never a false-clean. Backstops #1 (supersession) + #2 (bank guard).
    _theory_rel_final = parse_theory_file(notes_text)
    if (out.get("target") or {}).get("solved") and _theory_rel_final:
        try:
            from ztare.leanmill.solver.family_lemma_library import _default_axiom_audit, decl_names as _dn
            _tname = str((out["target"].get("target_theorem_name") or "")).strip()
            _tp = (lean_root / _theory_rel_final)
            if _tname and _tp.exists():
                _names = _dn(_tp.read_text(encoding="utf-8"))
                _banked = _tname if _tname in _names else next((n for n in _names if n.startswith(_tname + "__")), "")
                # AXIOM SOURCE (2026-07-02 recurring-skip fix): a COMPOSITE is banked INTO the substrate (_banked);
                # a DIRECT close lives ONLY in the self-contained closure cert (closures/<t>.lean) and is NOT in the
                # substrate ⇒ _banked='' ⇒ the whole audit/sidecar block was skipped SILENTLY (median-voter + every
                # non-composite target) ⇒ promote fell back to a cold recompute reporting 'axioms none printed'. Read
                # the cert when the target isn't banked, so the P0 sidecar stamps for direct closes too.
                _cert = _run_closures_dir() / f"{_tname}.lean"
                _ax_src, _ax_decl = (_tp, _banked) if _banked else ((_cert, _tname) if _cert.exists() else (None, ""))
                if _ax_decl and _ax_src is not None:
                    _clean, _areason = _default_axiom_audit(str(_ax_src), str(LEAN_ROOT_DEFAULT), _ax_decl)
                    if not _clean:
                        log(f"[notes] *** TARGET AXIOM-TAINT in the persisted theory ({_areason}) — DOWNGRADING "
                            f"'closed' → HONEST GAP (the assembled proof bound to a sorried sibling, not the "
                            f"proof) — never a false-clean ***")
                        out["target"]["solved"] = False
                        out["target"]["outcome"] = "axiom_taint_gap"
                        out["target"]["faithfulness_reason"] = f"persisted-theory {_areason}"
                    else:
                        # P0 SINGLE-DOOR (2026-06-30): stamp the honest persisted-world axioms (+ this-run
                        # banked/reused counts) in a sidecar beside the closure so promote READS them — never
                        # re-derives P0 from the cold probe-world closure (→ `axioms ?` / stub axioms / `reuse 0`).
                        # HARDENED (2026-07-01): the warm CAMPAIGN-env audit is "unavailable" when the REPL dropped
                        # after a long run (the BFT sidecar never stamped) → fall back to `axioms_raw_via_repl` on
                        # the self-contained substrate (BASE env, no campaign-env dependency) so the stamp fires
                        # reliably. Best-effort; never blocks a verified closure.
                        try:
                            import json as _json_p0, re as _re_p0
                            _ax_str = _areason if ("unavailable" not in _areason) else ""
                            if not _ax_str:
                                from ztare.formal.repl_compile import axioms_raw_via_repl as _araw
                                _raw = _araw(_ax_src.read_text(encoding="utf-8"), _ax_decl, str(LEAN_ROOT_DEFAULT))
                                if _raw and "depends on axioms" in _raw:
                                    _ax_str = ", ".join(_re_p0.findall(r"[A-Za-z_][\w.]*",
                                                        _raw.split("depends on axioms", 1)[-1]))
                            if _ax_str:
                                _banked_n = sum(1 for _l in out["lemmas"]
                                                if _l.get("solved") and _l.get("outcome") != "reused_from_bank")
                                _reused_n = sum(1 for _l in out["lemmas"] if _l.get("outcome") == "reused_from_bank")
                                _cdir_p0 = _run_closures_dir()
                                _cdir_p0.mkdir(parents=True, exist_ok=True)
                                (_cdir_p0 / f"{_tname}.p0.json").write_text(_json_p0.dumps({
                                    "axioms": _ax_str,               # persisted-world #print axioms (warm campaign-env, else base-env fallback)
                                    "composite_decl": _ax_decl,
                                    "theory_file": _theory_rel_final,
                                    "banked_this_run": _banked_n,
                                    "reused_from_bank": _reused_n,
                                }, indent=2), encoding="utf-8")
                                log(f"[notes] P0 stamped: closures/{_tname}.p0.json "
                                    f"(axioms={_ax_str} · {_banked_n} banked/{_reused_n} reused this run)")
                            else:
                                log("[notes] P0 sidecar SKIPPED — axioms unavailable (warm campaign-env dropped + "
                                    "base-env #print-axioms fallback inconclusive); promote will re-derive from the closure")
                        except Exception:  # noqa: BLE001 — telemetry; never blocks a verified closure
                            pass
        except Exception:  # noqa: BLE001 — defense-in-depth backstop; never break the run
            pass

    _modeling_faithfulness_audit(out, _theory_rel_final, lean_root, log=log)
    _promote_blockers = _auto_promote_blockers(out, _theory_rel_final)

    # AUTO-PROMOTE (2026-07-02): on a verified close, GENERATE the filed artifact (provenance header w/ the honest
    # family P0 + persisted axioms from the sidecar above + clean public names + the laundering-boundary guard) into
    # a STAGING dir, so filing to the public library is a review-and-move, not a hand-run of promote (the manual step
    # that silently under-counted P0 when --family/--axioms were forgotten). Best-effort — the close is already
    # complete; a promote failure only skips the convenience artifact. STAGING ONLY (`.solver_scratch/filed/`) —
    # publishing to the public repo stays a deliberate manual push. ZTARE_LEANMILL_AUTO_PROMOTE=0 reverts.
    if (out.get("target") or {}).get("solved") and _os_w.environ.get("ZTARE_LEANMILL_AUTO_PROMOTE", "1") != "0":
        if _promote_blockers:
            log("[notes] auto-promote blocked by modeling-faithfulness policy: "
                + " ; ".join(_promote_blockers)[:500])
        else:
            try:
                _rt_ap = _os_w.environ.get("ZTARE_SOLVER_RUN_TAG", "")
                _tn_ap = str((out.get("target") or {}).get("target_theorem_name") or "").strip()
                _repo_ap = Path(__file__).resolve().parents[4]
                _cert_ap = _run_closures_dir() / f"{_tn_ap}.lean"
                if _rt_ap and _tn_ap and _cert_ap.exists():
                    import subprocess as _sp_ap, sys as _sys_ap
                    _filed_ap = LEAN_ROOT_DEFAULT / ".solver_scratch" / "filed"
                    _filed_ap.mkdir(parents=True, exist_ok=True)
                    _prom_ap = _repo_ap / "scripts/public/control/leanmill/promote_campaign_artifact.py"
                    _prom_args = [_sys_ap.executable, str(_prom_ap), "--run-tag", _rt_ap, "--target", _tn_ap,
                                  "--dest", str(_filed_ap / f"{_tn_ap}.lean")]
                    if notes_path is not None:   # link the English spec next to the proof (translation boundary)
                        _prom_args += ["--blueprint", notes_path.name]
                    _res_ap = _sp_ap.run(
                        _prom_args, capture_output=True, text=True, timeout=600,
                        env={**_os_w.environ, "PYTHONPATH": str(_repo_ap / "src")})
                    if _res_ap.returncode == 0:
                        log(f"[notes] AUTO-PROMOTED → .solver_scratch/filed/{_tn_ap}.lean (family P0 + axioms; review + move to publish)")
                    else:
                        log(f"[notes] auto-promote skipped (rc={_res_ap.returncode}): "
                            f"{((_res_ap.stderr or _res_ap.stdout) or '').strip()[-160:]}")
            except Exception as _e_ap:  # noqa: BLE001 — best-effort convenience; never blocks a verified close
                log(f"[notes] auto-promote skipped: {repr(_e_ap)[:120]}")

    # SUBSTRATE HYGIENE (2026-07-01): sweep DEAD sorried orphans — sorried decls nothing else references, the
    # scaffolding a campaign leaves when a proven sibling supersedes an abstract stub (VCG's general witness vs
    # its concrete `_closed`). Keeps the warm env + any filed artifact sorry-free (a dead `sorry` reads as
    # unfinished + trips the promote publish guard). Recompile-verify + REVERT: a removal that breaks the env is
    # rolled back (the reference scan is textual, so this is the safety net). Best-effort; ZTARE_LEANMILL_SWEEP_ORPHANS=0 off.
    if _theory_rel_final and _os_w.environ.get("ZTARE_LEANMILL_SWEEP_ORPHANS", "1") != "0":
        try:
            from ztare.leanmill.solver.family_lemma_library import strip_dead_sorried_orphans
            from ztare.formal.repl_compile import campaign_file_env
            _tp_sw = lean_root / _theory_rel_final
            if _tp_sw.exists():
                _orig = _tp_sw.read_text(encoding="utf-8")
                _swept, _removed = strip_dead_sorried_orphans(_orig)
                if _removed:
                    _tp_sw.write_text(_swept, encoding="utf-8")
                    if campaign_file_env(str(_tp_sw), str(LEAN_ROOT_DEFAULT)) is None:
                        _tp_sw.write_text(_orig, encoding="utf-8")   # revert — removal broke the env
                        log(f"[notes] orphan-sweep REVERTED (removal broke the env); kept {_removed}")
                    else:
                        log(f"[notes] orphan-sweep: removed {len(_removed)} dead sorried orphan(s) {_removed} "
                            f"(nothing cited them; env still compiles)")
        except Exception:  # noqa: BLE001 — hygiene is best-effort; never blocks the run
            pass

    n_ok = sum(1 for l in out["lemmas"] if l.get("solved"))
    target_closed = bool((out["target"] or {}).get("solved"))
    out["summary"] = (f"{n_ok}/{len(lemmas)} lemmas formalized+closed; shelf={len(out['shelf'])}; "
                      f"target {'closed' if target_closed else 'open'}")
    if out.get("execution_stop"):
        out["summary"] += f"; execution_stop={out['execution_stop']}"
    # FINAL deterministic write-back — the COMPLETE gap ledger. The incremental writes above are kill-safety
    # snapshots taken BEFORE the target attack + wall-deferral were known, so they can't carry the TARGET gap
    # or the `wall_deferred` rungs (the 5 never-attempted lemmas a campaign-wall run leaves). This last write
    # guarantees EVERY caller (not just main(), which later UPGRADES it with agent synthesis) persists the full
    # honest gap record. No agent dispatch ⇒ free; main()'s later write with `dispatch` only enriches the
    # open-frontier decomposition. Best-effort: a write error never changes the run result.
    if notes_path is not None:
        try:
            out["deep_closures"] = deep_closures_since(out["run_started"])
            write_refined_notes(out, notes_path)
        except Exception:  # noqa: BLE001
            pass
    return out


# Prompt lives in the canonical registry (prompts.py); local name preserved for the call site.
from ztare.leanmill.solver.prompts import THEORY_PROMPT as _THEORY_PROMPT


def _anti_unify_block(lean_root: Path) -> str:
    """Advisory anti-unification leads (#124) for the theory-consolidation prompt: the top mined schema
    over OUR proven-rung corpus, rendered as a 'consider the common generalization' suggestion. Empty
    string on the kill-switch, no corpus, or no sibling pair found — never blocks the round."""
    import os as _os
    if _os.environ.get("ZTARE_LEANMILL_ANTIUNIFY", "1") == "0":
        return ""
    try:
        from ztare.leanmill.solver.anti_unify import mine_cert_pairs
        leads = mine_cert_pairs(max_pairs=2)
    except Exception:  # noqa: BLE001 — advisory; never fail the consolidation round
        return ""
    if not leads:
        return ""
    out = ["\n\n## Anti-unification leads (advisory — proven sibling rungs that may share one general lemma):"]
    for m in leads:
        out.append(f"- `{m['name_a']}` and `{m['name_b']}` instantiate a common schema "
                   f"({m['n_vars']} hole(s)): consider STATING + proving the general lemma, then deriving "
                   f"both as instances. Schema: {m['schema'][:160]}")
    out.append("(Only if it genuinely generalizes — if the holes force incompatible types, ignore this lead.)")
    return "\n".join(out)


def theory_consolidation(notes_text: str, theory_rel: str, *, lean_root: Path,
                         dispatch: "Optional[Callable]" = None,
                         compile_fn: "Optional[Callable]" = None,
                         triviality_fn: "Optional[Callable]" = None) -> dict:
    """Phase 0 of a theory-first campaign (#123): the agent CREATES/EXTENDS the campaign-owned theory file;
    deterministic gates decide whether the round counts (Goldilocks: authorship is the agent's, the gates
    are mechanical):
      • APPEND-ONLY integrity — the prior content must appear VERBATIM in the new content (definition
        EDITING is the laundering surface statement_integrity exists for; here the baseline is the file
        itself, checked byte-level). Violation ⇒ file reverted, round rejected.
      • KERNEL COMPILE (sorry-tolerant) — the extended file must elaborate; a non-compiling theory round
        is reverted (never poison the campaign substrate).
    Returns {ok, reverted?, reason?, new_decls, sorried_statements} — `sorried_statements` (full theorem
    text) feed the run's lemma queue: API lemmas become ordinary governed work items."""
    theory_path = (lean_root / theory_rel) if not Path(theory_rel).is_absolute() else Path(theory_rel)
    theory_path.parent.mkdir(parents=True, exist_ok=True)
    before = theory_path.read_text(encoding="utf-8") if theory_path.exists() else ""
    # THEORY-IDENTITY GUARD (2026-06-25 AMM RCA): the vocab-swap that orphaned a proven theory
    # (`ConstantProductPool`→`PoolState`) required the substrate to be RESET first — then a fresh genAI
    # consolidation re-formalized the prose in a NEW vocabulary, and the old proofs (keyed on the old vocab)
    # no longer matched (the α-cache is binder-axis only, not def-vocab; see proof_cache). The append-only
    # gate below can only block EDITS, never a rebuild-from-empty. So: if this substrate has prior BANKED
    # (proven) facts but the file is now empty/trivial, it was reset — REFUSE to silently re-formalize
    # (which would orphan the proven theory in a new vocab). Fail LOUD so the operator recovers (rederive /
    # restore) instead of compounding the loss. Default-on; ZTARE_LEANMILL_THEORY_IDENTITY_GUARD=0 reverts.
    import os as _os_ti
    if _os_ti.environ.get("ZTARE_LEANMILL_THEORY_IDENTITY_GUARD", "1") != "0":
        try:
            from ztare.leanmill.solver.family_lemma_library import read_bank_events as _rbe
            _prior = [e for e in _rbe() if e.get("substrate") == theory_path.name
                      and (e.get("decl_text") or "").strip()]
        except Exception:  # noqa: BLE001 — guard is best-effort; a lookup failure never blocks the run
            _prior = []
        _n_thm = before.count("theorem ") + before.count("lemma ")
        # a RESET substrate has NO theorems/lemmas (empty or import-only); an established one always has them.
        # Keying on "zero results" (not a char-length heuristic) is the robust reset signal.
        _trivial = (_n_thm == 0)
        if _prior and _trivial:
            return {"ok": False, "reverted": False, "theory_reset_detected": True,
                    "new_decls": [], "sorried_statements": [],
                    "reason": (f"THEORY-IDENTITY GUARD: substrate {theory_path.name!r} has {len(_prior)} banked "
                               f"(proven) facts but the file is empty/trivial ({_n_thm} theorems) — it was RESET. "
                               f"Refusing to re-formalize from prose (would orphan the proven theory in a NEW "
                               f"vocabulary — the AMM ConstantProductPool→PoolState RCA). Recover the proven theory "
                               f"(rederive_library_from_events / restore a backup) BEFORE re-running.")}
    if dispatch is not None:
        target, _ = parse_notes(notes_text)
        # ANTI-UNIFICATION LEADS (#124 consumer wiring): the library editor is exactly where mined schema
        # seeds belong — proven sibling rungs that instantiate one unstated general lemma become a
        # "consider stating the common generalization" advisory. Comment-style/advisory, fail-open,
        # ZTARE_LEANMILL_ANTIUNIFY=0 reverts; the kernel still gates anything the agent writes.
        _notes = notes_text[:8000] + _anti_unify_block(lean_root)
        # REAL timeout (bug 2026-06-13: passed timeout=None → default_dispatch does int(None) → crash; the
        # mock-only selftest never hit it). Theory-building is substantial — use the per-lemma budget.
        from ztare.common.timeouts import timeout_s as _ts_theory
        _theory_to = _ts_theory("notes_lemma")
        _prompt = _THEORY_PROMPT.format(path=str(theory_path), root=str(lean_root), target=target, notes=_notes)
        try:
            dispatch(_prompt, repo=lean_root, timeout=_theory_to)
        except TypeError:   # dispatch signatures vary (timeout kw optional on injected fakes)
            dispatch(_prompt, repo=lean_root)
        except Exception as e:  # noqa: BLE001 — a failed dispatch leaves the file as-is; gates decide below
            return {"ok": False, "reason": f"dispatch error: {repr(e)[:120]}"}
    after = theory_path.read_text(encoding="utf-8") if theory_path.exists() else ""
    if after == before:
        return {"ok": True, "unchanged": True, "new_decls": [], "sorried_statements": []}
    # GATE 1: append-only (baseline integrity — additions may interleave imports at top, so the check is:
    # every prior NON-IMPORT line present verbatim AS A WHOLE LINE and in order; imports may be added).
    # 2026-06-13 audit (BUG 1): this was a SUBSTRING match (`_a_text.find(l)`), so an IN-PLACE edit whose
    # old text is a prefix of the new line (`def A := True` → `def A := True ∧ True`) passed the
    # anti-laundering wall — a definition edit is exactly what this gate exists to reject. Whole-line,
    # in-order matching closes it (GATE 2's sorry-tolerant compile can't catch an edited def — it still
    # compiles). Soundness boundary: a silently-edited def could invalidate a previously-proven rung.
    _b_lines = [l for l in before.splitlines() if l.strip() and not l.strip().startswith("import ")]
    _a_lines = [l for l in after.splitlines() if l.strip() and not l.strip().startswith("import ")]
    _pos = 0
    for l in _b_lines:
        try:
            _pos = _a_lines.index(l, _pos) + 1   # whole-line, in order; not a substring
        except ValueError:
            theory_path.write_text(before, encoding="utf-8")   # REVERT — definition editing rejected
            return {"ok": False, "reverted": True,
                    "reason": f"append-only violated: prior line altered/removed: {l[:80]!r}"}
    # GATE 2: kernel compile, sorry-tolerant (the canonical v33 probe — same oracle the solver trusts)
    _real_sandbox = compile_fn is None   # a real run uses the live probe; an injected mock ⇒ GATE 3 has no Lean env
    if compile_fn is None:
        from ztare.gates.v33_preflight_risk_detector import _compile_probe as compile_fn  # type: ignore
    from ztare.common.timeouts import timeout_s as _ts
    ok = compile_fn(after, lean_root, "TheoryConsolidation", _ts("cold_compile"))
    if ok is not True:
        theory_path.write_text(before, encoding="utf-8")
        return {"ok": False, "reverted": True, "reason": "extended theory file does not compile"}
    # REPRESENTATION-DEPENDENCE audit (2026-07-05, CLOB `bestBid=head` RCA — general-purpose foresight). A def that
    # extracts the "best"/"top" of a SET-like collection through a POSITION primitive (`.head?`/`.getLast`/`.get`…)
    # is representation-dependent: faithful to a suggestive NL adjective yet FALSE downstream when the collection is
    # order-agnostic (the firewall gates target-faithfulness, not def-faithfulness, so it slips to prove-time). This
    # is the FIRST failure surface for data-structure campaigns (all prior closures had representation-INDEPENDENT
    # defs). ADVISORY reporter (never gates — order may be genuinely meant, e.g. a `foldl` over a sequence); surfaced
    # LOUD at consolidation so the maintainer switches to an order-independent def (max/min/Finset) + an anchor
    # lemma BEFORE the campaign spends. ZTARE_LEANMILL_REPRESENTATION_AUDIT=0 reverts.
    # DEF-QUALITY audit — the SINGLE DOOR for every meaning-bearing def-shape check (representation-dependence,
    # non-reduction, partial/WF-recursion, classical branch). ONE registry (`lean_source._DEF_AUDITS`): a new audit
    # is added there and inherited here with no sibling to drift. The firewall gates NL↔target faithfulness, not def
    # MEANING/TRACTABILITY — each new domain opens a new "faithful-but-X" surface — so these run at consolidation,
    # surfaced LOUD so the author fixes a faithful-but-false/intractable def BEFORE the campaign spends; never gates.
    # Supersedes the split REPRESENTATION_AUDIT/TRACTABILITY_AUDIT flags. ZTARE_LEANMILL_DEF_QUALITY_AUDIT=0 reverts.
    if _os_ti.environ.get("ZTARE_LEANMILL_DEF_QUALITY_AUDIT", "1") != "0":
        try:
            from ztare.leanmill.lean_source import def_quality_audit as _dqa
            for _cat, _flag in _dqa(after):
                print(f"[consolidation] ⚠️ {_cat}: {_flag}", flush=True)
        except Exception:  # noqa: BLE001 — advisory only; never block consolidation
            pass
    # SUPERSESSION HEAL (sorried-sibling class, 2026-07-01): the APPEND-ONLY gate above forbids the AGENT editing
    # `X := sorry` → `X := proof`, so when it proves a shelf lemma it appends a proven TWIN (`X_banked`) and the
    # canonical `X` stays sorried — sorried-canonical / proven-twin pairs ACCUMULATE across rounds (inflating the
    # shelf; blocking a clean filing). The HARNESS may fold each proven twin into its sorried canonical (NOT agent
    # laundering — it only replaces a `sorry` with `by exact <twin>`, a kernel-checkable cite of an EXISTING
    # identical-statement proof). Guarded: REVERIFY the healed file compiles (sorry-tolerant) and REVERT on any
    # break (never poison the substrate — same discipline as the gates above). Default-on; =0 reverts.
    import os as _os_sup
    if _os_sup.environ.get("ZTARE_LEANMILL_SUPERSEDE_TWINS", "1") != "0":
        try:
            from ztare.leanmill.lean_source import supersede_sorried_twins as _sst
            _healed, _rep = _sst(after)
            if _rep and _healed != after:
                theory_path.write_text(_healed, encoding="utf-8")
                if compile_fn(_healed, lean_root, "SupersedeHeal", _ts("cold_compile")) is True:
                    after = _healed
                    print(f"[consolidation] SUPERSEDED {len(_rep)} sorried-canonical(s) via proven twin: "
                          f"{[c for c, _ in _rep][:6]}", flush=True)
                else:
                    theory_path.write_text(after, encoding="utf-8")   # REVERT — never poison the substrate
        except Exception:  # noqa: BLE001 — heal is best-effort; the un-healed file already passed GATE 2
            pass
    # SIMP-FRIENDLY SUBSTRATE (durable fix, RCA 2026-07-04 RBAC iso_lemma3): theory-consolidation emits reduction
    # anchors (`anchor_grants_assignRole … := rfl`) but never `@[simp]` — so a leaf's CORRECT constructor-reduction
    # simp-proof (`simp [grants,…]`) reduces in the self-contained probe but NOT against the substrate → unsolved
    # goal → reverted_noncompile → env-parity RETRACT of a correct proof (we were hurting the leaf iatrogenically).
    # Tag the COMPUTATION anchors (single door `lean_source.simp_tag_computational_anchors`: rfl + application-LHS,
    # no logical connective ⇒ never over-unfolds) so every leaf's standard simp-proof PORTS. Compile-GATED: a tag
    # that breaks the substrate (e.g. a simp loop in the theory's own proofs) reverts. First bit on RBAC because it
    # is the first CONSTRUCTOR-REDUCTION-heavy substrate (an `Operation` inductive + pattern-matching reducers);
    # prior substrates used plain def-unfold that ports without @[simp]. ZTARE_LEANMILL_SIMP_TAG_ANCHORS=0 reverts.
    import os as _os_st
    if _real_sandbox and _os_st.environ.get("ZTARE_LEANMILL_SIMP_TAG_ANCHORS", "1") != "0":
        try:
            from ztare.leanmill.lean_source import simp_tag_computational_anchors as _simptag
            _tagged = _simptag(after)
            if _tagged != after:
                theory_path.write_text(_tagged, encoding="utf-8")
                if compile_fn(_tagged, lean_root, "SimpTagAnchors", _ts("cold_compile")) is True:
                    after = _tagged
                    print("[consolidation] tagged reduction anchors @[simp] (substrate now simp-friendly ⇒ leaf "
                          "constructor-reduction proofs PORT, not reverted_noncompile)", flush=True)
                else:
                    theory_path.write_text(after, encoding="utf-8")   # REVERT — tagging broke the substrate
        except Exception:  # noqa: BLE001 — hygiene is best-effort; never poison a good consolidation
            theory_path.write_text(after, encoding="utf-8")
    # extract the NEW sorried API statements → solver work items. "Is this decl OPEN?" is a KERNEL fact,
    # NOT a lexical grep (the operator's "fix once and for all"): the file just compiled, so ask the
    # elaborator which NEW decls carry `sorryAx` (`kernel_structure.sorried_names`). This CANNOT be fooled
    # by a `sorry` in a section comment — the 2026-06-13 bug that queued an already-proven `by simp` lemma
    # and burned ~25min. Lexical `has_sorry` (now nested-comment-aware) is only the FALLBACK when no live
    # REPL exists here. (Canonical decl parser throughout — no module re-rolls a Lean-source regex.)
    from ztare.leanmill.solver.statement_integrity import decl_blocks
    from ztare.leanmill.lean_source import strip_comments as _sc, has_sorry as _has_sorry, split_at_proof as _sap
    before_names = {n for n, _ in decl_blocks(before)}
    # WORK-ITEM COMPLETENESS (Goldilocks: surface the KERNEL FACT of what's OPEN — do not curate a partial list;
    # 2026-07-05 restOrder_preserves ORPHAN bug + operator "why targeting logic at all, are we goldilocks"). The
    # old filter `n not in before_names` queued ONLY decls THIS round added — so a leaf left sorried by a PRIOR
    # run (already in `before`) was never re-queued: the flagship's last lemma never got a 2nd shot, and the engine
    # ground the TOP (which cites the sorried leaf → admitted_and_exact_gap) forever. Now ALSO re-surface any
    # PERSISTENT decl whose OWN proof body still carries a literal `sorry` (the true open leaf). Comment-`sorry`
    # can't fool it (strip_comments + split_at_proof isolate the proof body). Transitive-sorryAx PARENTS
    # (textually sorry-free, merely citing the open leaf) are NOT re-queued — only the literal-sorry leaves — so
    # once the leaf closes the parents become genuinely clean. The agent still CHOOSES how to prove each; this
    # only reports the complete open-set (a fact), never a strategy.
    def _own_body_sorried(_blk):
        return _has_sorry(_sap(_sc(_blk))[1])
    after_blocks = [(n, b) for n, b in decl_blocks(after)
                    if (n not in before_names) or _own_body_sorried(b)]
    new_decls = [n for n, _ in after_blocks if n not in before_names]
    from ztare.leanmill.solver.kernel_structure import sorried_names as _ksorried
    _kernel_open = _ksorried(after, lean_root, names=[n for n, _ in after_blocks])   # set[name] | None (None ⇒ fall back)
    new_sorried = []
    for name, block in after_blocks:
        _clean = _sc(block)
        _open = (name in _kernel_open) if _kernel_open is not None else _has_sorry(_sap(_clean)[1])  # proof-body, binder-safe
        if _open:
            new_sorried.append(" ".join(_clean.split()))   # clean signature, no comment/proof cruft
    # GATE 3: NON-TRIVIALITY of the new sorried shelf lemmas (the vacuous-bridge class, EF1 RCA 2026-07-03).
    # A frontier model scaffolding a hard proof can weaken a hard bridge lemma to a trivially-true shell
    # (`∃ dropped, True`), which compiles (GATE 2 passes) and enters the decomposition DAG as a "core" lemma; it
    # is only caught at PROVE time by the firewall's triviality leg, AFTER the target's proof already routes
    # through it → the run wastes cycles / can stick. Move the SAME leg (`default_triviality`, the single door)
    # upstream to consolidation: a new sorried lemma the cheap-tactic cascade closes is a fake stepping stone —
    # REVERT with a naming reason so the agent re-states it faithfully. Defense-in-depth (the prove-time firewall
    # still gates every rung); default-on, ZTARE_LEANMILL_CONSOLIDATION_NONTRIVIAL=0 reverts.
    import os as _os_nt
    if (new_sorried and (triviality_fn is not None or _real_sandbox)
            and _os_nt.environ.get("ZTARE_LEANMILL_CONSOLIDATION_NONTRIVIAL", "1") != "0"):
        _triv = triviality_fn
        if _triv is None:
            from ztare.leanmill.solver.autoformalize import default_triviality as _triv
        _degenerate = []
        for _stmt in new_sorried:
            try:
                if _triv(_stmt, lean_root):
                    _degenerate.append(_stmt[:90])
            except Exception as _e:  # noqa: BLE001 — a triviality PROBE infra failure is advisory here: GATE 2
                # already elaborated the file and the prove-time firewall re-checks every rung, so probe
                # flakiness must not block a good consolidation round (fail-open ONLY for the probe, not the check).
                print(f"[consolidation] GATE3 triviality probe inconclusive ({repr(_e)[:70]}) — advisory skip "
                      "(prove-time firewall still gates)", flush=True)
        if _degenerate:
            theory_path.write_text(before, encoding="utf-8")   # REVERT — a vacuous shelf lemma cannot discharge the target
            return {"ok": False, "reverted": True, "vacuous_shelf_lemmas": _degenerate,
                    "reason": (f"GATE 3 non-triviality: {len(_degenerate)} new shelf lemma(s) are trivially true "
                               f"(a cheap tactic closes them) — a fake stepping stone that cannot discharge the "
                               f"target. State each lemma's REAL conclusion; if the vocabulary lacks the "
                               f"intermediate predicate it needs, define it. Offenders: {_degenerate}")}
    # SUPERSESSION REQUESTS (captured, not auto-applied): the agent may flag a wrong-shaped EXISTING
    # definition with `-- SUPERSEDE: <name>: <why>`. Editing is still forbidden this round (append-only
    # stands); the request is surfaced in the result/receipt and queued for a governed revision — the
    # rewrite-and-revalidate machinery is a trust-surface change shipped separately, but the agent's
    # revision signal is never silently dropped.
    supersede = [{"name": m.group(1).strip(), "why": m.group(2).strip()[:200]}
                 for m in re.finditer(r"--\s*SUPERSEDE:\s*([^:]+):\s*(.+)", after)]
    out = {"ok": True, "new_decls": new_decls, "sorried_statements": new_sorried}
    if supersede:
        out["supersession_requests"] = supersede
    return out


def governed_def_revision_gate(before_src: str, after_src: str, def_name: str, *,
                               verify_fn: "Callable[[str], bool]") -> "tuple[bool, str]":
    """ANTI-GAMING gate for SUPERSESSION-ACTING (the governed def-revision the `-- SUPERSEDE` request was queued
    for). When a kernel-CONFIRMED-false theorem traces to a too-weak `def <D>`, the agent may STRENGTHEN it —
    but only soundly. `after_src` is accepted iff:
      (1) the OLD def is preserved VERBATIM, renamed `<D>__pre` (so the witness can name it);
      (2) a NEW `def <D>` exists (same name → existing usages rebind to it);
      (3) a `witness_strengthen_<D>` theorem is present AND `verify_fn` KERNEL-confirms it — it proves
          `∀ …, <D> … → <D>__pre …`, i.e. the new def IMPLIES the old = a STRENGTHENING. A weakening /
          trivialization / sideways-change cannot prove this, so it is rejected;
      (4) every OTHER prior decl is UNCHANGED (append-only — only <D>, <D>__pre, the witness are new/changed).
    Goldilocks: the AGENT authors the stronger def + proves the implication (upstream agency); the KERNEL gates
    that it is genuinely a strengthening (the boundary). Reuses the canonical `decl_blocks`/`lean_source` parser
    and the SAME witness verifier the denotation leg uses — no new oracle, no parallel machinery. The goal and
    every other def are untouched, so a revision can only RESTRICT <D> (it cannot launder a false theorem)."""
    from ztare.leanmill.solver.statement_integrity import decl_blocks
    from ztare.leanmill import lean_source as _ls
    pre, witness = f"{def_name}__pre", f"witness_strengthen_{def_name}"

    def _norm(s: str) -> str:
        return " ".join((s or "").split())

    def _value(src: str, name: str) -> str:   # the def's value (after `:=`), whitespace-normalized
        body = _ls.def_body(src, name) or ""
        v = _ls.split_at_proof(body)[1]
        return _norm(v[2:] if v.startswith(":=") else v)

    if def_name not in _ls.def_names(before_src):
        return False, f"{def_name} is not a prior definition"
    if pre not in _ls.def_names(after_src):
        return False, f"old def not preserved as `{pre}` (the strengthening witness must reference it)"
    if _value(after_src, pre) != _value(before_src, def_name):
        return False, f"`{pre}` body is not the verbatim original `{def_name}` body"
    if def_name not in _ls.def_names(after_src):
        return False, f"revised `{def_name}` missing"
    if witness not in _ls.theorem_names(after_src):
        return False, f"missing strengthening witness `{witness}` (∀ …, {def_name} … → {pre} …)"
    # (4) NO laundering of any OTHER decl. A non-superseded CONCEPT def (Prop-valued — the meaning surface) must
    # stay BYTE-IDENTICAL; a THEOREM/instance/term may keep its STATEMENT/type but ADAPT its proof/body to the
    # strengthened def (a structure-field def like single-crossing forces its instances, e.g. `const`, to
    # re-prove — forbidding that would make the whole mechanism unusable). Statements (signatures) are the
    # laundering boundary; the kernel re-verifies the adapted proofs, and every downstream closure is re-governed.
    bb, ab = dict(decl_blocks(before_src)), dict(decl_blocks(after_src))
    before_defs = set(_ls.def_names(before_src))
    for n, blk in bb.items():
        short = n.split(".")[-1]
        if short == def_name:
            continue   # the superseded def may change its meaning (gated by the strengthening witness above)
        if n not in ab:
            return False, f"prior decl removed: `{n}` (not allowed)"
        if short in before_defs and _ls.def_is_prop_valued(before_src, short):
            if " ".join(ab[n].split()) != " ".join(blk.split()):   # a CONCEPT def must be byte-identical
                return False, f"a non-superseded CONCEPT def changed: `{n}` (only `{def_name}` may change its meaning)"
        elif _norm(_ls.signature_before_proof(ab[n])) != _norm(_ls.signature_before_proof(blk)):
            return False, f"prior decl SIGNATURE/type changed: `{n}` (statements are append-only; only proofs/instance-bodies may adapt)"
    # (5) the strengthening must be KERNEL-confirmed — new `<D>` IMPLIES old `<D>__pre` (a decoy/weakening can't)
    try:
        if not verify_fn(witness):
            return False, f"`{witness}` not kernel-verified — the revision is not a proven strengthening (rejected)"
    except Exception as _e:  # noqa: BLE001
        return False, f"witness verify error: {_e!r}"
    return True, f"`{def_name}` soundly strengthened — `{witness}` kernel-verified; goal + other defs untouched"


def _detect_revised_def(after_src: str) -> "str | None":
    """The def the agent revised: a `def <D>` for which BOTH `<D>__pre` (preserved old) and
    `witness_strengthen_<D>` (the strengthening proof) were written. None if no revision pattern present."""
    from ztare.leanmill import lean_source as _ls
    defs, thms = set(_ls.def_names(after_src)), set(_ls.theorem_names(after_src))
    for d in defs:
        if f"{d}__pre" in defs and f"witness_strengthen_{d}" in thms:
            return d
    return None


def governed_def_revision(theory_rel: str, *, lean_root: Path, dispatch: "Callable",
                          false_lemma: str, counterexample: str = "",
                          compile_fn: "Optional[Callable]" = None,
                          verify_fn_factory: "Optional[Callable]" = None,
                          timeout_s: "int | None" = None) -> dict:
    """SUPERSESSION-ACTING orchestrator — the self-correction the `-- SUPERSEDE` request was queued for. A
    campaign lemma was KERNEL-confirmed false because a def it cites is too WEAK; dispatch the agent to
    STRENGTHEN that def (preserve old as `<D>__pre`, prove `witness_strengthen_<D>`), then gate via
    `governed_def_revision_gate` (only a kernel-proven strengthening passes — no laundering). The theory file is
    REVERTED on any failure (never poison the substrate). Returns {ok, revised_def?, reverted?, reason}. Reuses
    the v33 compile probe + the SAME witness verifier the denotation leg uses — no parallel machinery."""
    from ztare.gates.v33_preflight_risk_detector import _compile_probe
    from ztare.leanmill.solver import prompts as _p
    from ztare.common.timeouts import timeout_s as _ts
    theory_path = (lean_root / theory_rel) if not Path(theory_rel).is_absolute() else Path(theory_rel)
    before = theory_path.read_text(encoding="utf-8") if theory_path.exists() else ""
    if not before.strip():
        return {"ok": False, "reason": "no theory file to revise"}
    prompt = _p.REVISE_DEF_PROMPT.format(path=str(theory_path), false_lemma=(false_lemma or "")[:700],
                                         counterexample=(counterexample or "(no explicit counterexample text)")[:700])
    try:
        dispatch(prompt, repo=lean_root, timeout=timeout_s or _ts("notes_lemma"))
    except TypeError:                              # injected fakes may omit the timeout kw
        dispatch(prompt, repo=lean_root)
    except Exception as e:                         # noqa: BLE001 — failed dispatch leaves the file; gates below decide
        return {"ok": False, "reason": f"dispatch error: {repr(e)[:120]}"}
    after = theory_path.read_text(encoding="utf-8") if theory_path.exists() else ""
    if after == before:
        return {"ok": False, "reason": "no revision written"}
    cf = compile_fn or _compile_probe
    if cf(after, lean_root, "DefRevision", _ts("cold_compile")) is not True:
        theory_path.write_text(before, encoding="utf-8")
        return {"ok": False, "reverted": True, "reason": "revised theory does not compile"}
    dname = _detect_revised_def(after)
    if not dname:
        theory_path.write_text(before, encoding="utf-8")
        return {"ok": False, "reverted": True,
                "reason": "no `<D>__pre` + `witness_strengthen_<D>` revision pattern (agent did not follow the governed-revision protocol)"}
    if verify_fn_factory is not None:
        _verify = verify_fn_factory(after, lean_root)
    else:
        from ztare.leanmill.solver.def_denotation import kernel_denotation_verifier
        _verify = kernel_denotation_verifier(after, lean_root)
    okg, why = governed_def_revision_gate(before, after, dname, verify_fn=_verify)
    if not okg:
        theory_path.write_text(before, encoding="utf-8")
        return {"ok": False, "reverted": True, "revised_def": dname, "reason": why}
    return {"ok": True, "revised_def": dname, "reason": why}


def _gap_class(rec: dict) -> str:
    """The honest, typed FAILURE CLASS of a non-closing record — the reason it is a GAP, not a closure
    (Goldilocks: a gap is NEVER a closure). A firewall rejection (unfaithful / vacuous / trivial) is a
    DIFFERENT gap than an admitted-but-unclosed lemma; recording the class (not a bare "open") is what makes
    the gap ledger actionable for the next planner pass and keeps the notes taxonomy aligned with the
    per-statement `no_good_store` (tactical conflict clauses) + `conjecture_book` (evidence ledger) the
    solver already maintains."""
    reason = " ".join(str(rec.get("faithfulness_reason") or "").split()).strip()
    if rec.get("faithful") is not True:
        return "firewall_rejected" + (f": {reason[:160]}" if reason else "")
    # faithful=True but still a non-closure: surface the outcome AND any gate reason (e.g. a def-shell / triviality
    # verdict on an admitted statement) — previously dropped, which hid the cause across a whole campaign (the AMM
    # def-shell stall: 16 `gap[rejected_by_firewall]` lines with no reason). Observability, 2026-06-24.
    return str(rec.get("outcome") or "open") + (f": {reason[:160]}" if reason else "")


def write_refined_notes(result: dict, notes_path: "Path", *, dispatch: "Optional[Callable]" = None) -> "Path":
    """The APPARATUS updates its own research notes — the operator should NOT re-draft. GOLDILOCKS split:
      • DETERMINISTIC (this code) owns the GOVERNED FACTS — which lemmas KERNEL-CLOSED + the proven shelf. The
        agent must never author these or it could write down a closure that never happened (fake closure).
      • The WARM AGENT authors the SYNTHESIS — for each still-OPEN lemma it proposes a DEEPER decomposition
        (the next sub-lemmas to attempt). Research-notes authoring is creative, not a mechanical dump.
    Gated by `ZTARE_LEANMILL_AGENT_REFINE_NOTES` (default-on; `=0` ⇒ deterministic factual fallback, parity). The
    next run reads `<name>.refined.md` and compounds (cites the shelf, attacks the agent's finer breakdown);
    the operator's seed is preserved. This closes the loop — the planner drafts+refines, no human in it."""
    import os as _os
    closed = [l for l in result.get("lemmas", []) if l.get("solved")]
    open_ = [l for l in result.get("lemmas", []) if not l.get("solved")]
    shelf = [s for s in (result.get("shelf") or []) if s]
    # ── DETERMINISTIC governed-facts section (the agent CANNOT fabricate a closure) ──
    det = [f"# {(result.get('target_nl') or '')[:90]} — apparatus-refined",
           f"<!-- {result.get('summary', '')} -->", "", "## Target", (result.get("target_nl") or ""), "",
           "## Proven this run (✅ kernel-closed — citable):"]
    det += ([f"- ✅ {l.get('nl', '')}" for l in closed] or ["- (none kernel-closed this run)"])
    if shelf:
        det += ["", "## Proven shelf (cite these):"] + [f"- {s}" for s in shelf]
    # ── DETERMINISTIC GAP LEDGER (honest non-closures — recorded, NEVER laundered into a closure). Writes
    #    WHICH blueprint lemmas/target stayed OPEN this run + their typed FAILURE CLASS (firewall_rejected /
    #    admitted_and_exact_gap / open / deferred:campaign_wall). This is the CAMPAIGN-level status map the
    #    NEXT planner pass reads from the blueprint — DISTINCT in granularity from the two machine ledgers the
    #    leaf already consumes: `no_good_store.jsonl` is per-STATEMENT tactical ("don't retry THIS rejected
    #    approach", rendered into the leaf prompt at the lemma level) and `conjecture_book.jsonl` is the
    #    machine evidence ledger. A gap is a GOVERNED FACT (the kernel/governance decided it did not close), so
    #    it lives here in the deterministic section the agent cannot author — it can never become a fake ✅. ──
    _seen_gap: set = set()
    gap_lines: "list[str]" = []
    def _add_gap(nl: str, cls: str) -> None:
        key = (nl or "").strip()
        if not key or key in _seen_gap:
            return
        _seen_gap.add(key)
        gap_lines.append(f"- ⬜ {nl} — gap[{cls}]")
    for l in open_:
        _add_gap(l.get("nl", ""), _gap_class(l))
    _tgt_gap = result.get("target") or {}
    if _tgt_gap and not _tgt_gap.get("solved"):
        _tcls = (f"deferred:{_tgt_gap.get('deferred')}" if _tgt_gap.get("deferred") else _gap_class(_tgt_gap))
        _add_gap("(TARGET) " + (result.get("target_nl") or ""), _tcls)
    for d in (result.get("wall_deferred") or []):
        if str(d).strip() == (result.get("target_nl") or "").strip():
            continue   # the TARGET, if wall-deferred, is already recorded above (don't double-count)
        _add_gap(str(d)[:200], "deferred:campaign_wall")
    if gap_lines:
        det += ["", "## Gaps this run (non-closures — NOT proven, NOT citable):"] + gap_lines
    # ── Open-lemma synthesis. PREFER the PLANNER's ACTUAL sub-DAG (route_and_solve's decomposition — the same
    #    agent's mid-proof breakdown, already in the result); deterministically RENDER it (rendering the agent's
    #    own output is not authoring). Only lemmas the planner did NOT decompose get a fresh re-proposal dispatch. ──
    agent_md = ""
    if open_:
        open_md = ["## Open frontier — refined decomposition (attempt next)"]
        no_dag = []
        for l in open_:
            dec = l.get("decomposition") or {}
            sub = dec.get("lemmas") or []
            if sub:                                  # the planner already decomposed this lemma — persist its sub-DAG
                tag = " [kernel-audited]" if dec.get("audited") else ""
                open_md.append(f"\n### ⬜ {l.get('nl', '')}{tag} — gap[{_gap_class(l)}], planner sub-decomposition:")
                open_md += [f"- {str(s)[:220]}" for s in sub]
            else:
                no_dag.append(l)
        if no_dag and dispatch is not None and _os.environ.get("ZTARE_LEANMILL_AGENT_REFINE_NOTES", "1") != "0":   # DEFAULT-ON 2026-06-12 (advisory notes, kernel gates downstream; =0 reverts)
            facts = "\n".join(f"- OPEN: {l.get('nl', '')} | outcome: {l.get('outcome')}" for l in no_dag)
            prompt = ("You are a research mathematician REFINING your proof blueprint. These lemmas did NOT close "
                      "and the planner produced no sub-decomposition:\n" + facts + "\n\nFor EACH, propose a DEEPER "
                      "decomposition — 2–4 smaller, foundational-first sub-lemmas whose conjunction proves it, for "
                      "the prover to attempt next. Output ONLY markdown bullets. Do NOT claim anything is proven.")
            from ztare.common.timeouts import timeout_s   # central budget factory (byte-parity: notes_refine defaults to the prior 240)
            try:
                extra = (dispatch(prompt, repo=LEAN_ROOT_DEFAULT, timeout=timeout_s("notes_refine")) or "").strip()
                if extra:
                    open_md += ["", extra]
            except Exception:  # noqa: BLE001 — best-effort
                pass
        elif no_dag:
            open_md += [f"\n- ⬜ {l.get('nl', '')} (outcome: {l.get('outcome')}; no planner decomposition)" for l in no_dag]
        agent_md = "\n".join(open_md)
    # ALSO persist the TARGET's OWN route_and_solve decomposition: a notes file may carry NO `## Lemmas` (just a
    # `## Target`, e.g. P1 n=1), so the agent's breakdown lives ONLY on result['target'] — which the per-lemma loop
    # above never sees. Without this the `.refined.md` drops the target's whole sub-DAG (the other half of the
    # self-evolving-loop amnesia). Mirrors the open-lemma rendering; deterministic (rendering the agent's output).
    _tgt = result.get("target") or {}
    if _tgt and not _tgt.get("solved"):
        _tdec = _tgt.get("decomposition") or {}
        _tsub = _tdec.get("lemmas") or []
        if _tsub:
            if not agent_md:
                agent_md = "## Open frontier — refined decomposition (attempt next)"
            _tag = " [kernel-audited]" if _tdec.get("audited") else ""
            agent_md += (f"\n\n### ⬜ {str(_tgt.get('nl', ''))[:120]}{_tag} — planner sub-decomposition (the TARGET):\n"
                         + "\n".join(f"- {str(s)[:220]}" for s in _tsub))
    # ── DEEP RUNGS (v3 RCA 2026-06-12): kernel-closed sub-lemmas from the WHOLE recursion tree. The
    #    per-lemma records above only see TOP-level outcomes (`solve_decomposition` keeps {name, outcome}
    #    of its DIRECT children), so a depth≥2 closure was INVISIBLE here — v3 closed 2 deep rungs while
    #    this file said "(none kernel-closed this run)" and the next run had to re-derive them. Governed
    #    facts (cert-ledger render), so it lives in the deterministic section. ──
    deep = result.get("deep_closures") or []
    if deep:
        det += ["", "## Kernel-closed sub-lemmas this run (deep rungs — citable):"]
        for d in deep:
            flag = " ⚠️ integrity-unverified (NOT auto-citable)" if d.get("integrity_unverified") else ""
            if d.get("fragile") and not flag:
                flag = " ⚠️ fragile (margin battery: kernel-true, weakened signals)"
            loc = f" ({d.get('closure_lean')})" if d.get("closure_lean") else ""
            det.append(f"- ✅ {d.get('target')} [sha:{d.get('goal_sha')}] {d.get('statement', '')}{flag}{loc}")
    refined = notes_path.with_suffix(".refined.md")
    refined.write_text("\n".join(det) + "\n\n" + agent_md + "\n", encoding="utf-8")
    try:
        _emit_notes_writeback_trace({
            "kind": "write_refined_notes",
            "notes_path": str(notes_path),
            "refined_path": str(refined),
            "closed_count": len(closed),
            "open_count": len(open_),
            "shelf_count": len(shelf),
            "gap_count": len(gap_lines),
            "deep_closure_count": len(deep),
            "agent_frontier_chars": len(agent_md or ""),
            "agent_refine_enabled": __import__("os").environ.get("ZTARE_LEANMILL_AGENT_REFINE_NOTES", "1") != "0",
        })
    except Exception:  # noqa: BLE001
        pass
    return refined


def deep_closures_since(since_iso: str, *, ledger: "Optional[Path]" = None) -> "list[dict]":
    """Kernel-closed targets ratified at ANY recursion depth since `since_iso`, read from the durable
    closure-cert ledger — the single source of truth EVERY depth's `solve_adhoc` already appends to.
    WHY (v3 RCA 2026-06-12): `solve_decomposition` returns only {name, outcome} for its DIRECT children,
    so depth≥2 closures never reached the notes write-back — proven rungs were lost to the compounding
    loop (re-derived next run = the amnesia disease, paid in tokens). Returns
    [{target, goal_sha, statement, closure_lean, integrity_unverified}], deduped by goal identity;
    `statement` is extracted from the recompilable probe via the canonical decl parser."""
    if ledger is None:
        from ztare.leanmill.solver.solver_core import ADHOC_CLOSURE_CERTIFICATES as _L
        ledger = _L
    out: "list[dict]" = []
    seen: set = set()
    try:
        lines = Path(ledger).read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for ln in lines:
        try:
            c = json.loads(ln)
        except ValueError:
            continue
        if c.get("outcome") != "closed" or str(c.get("ts") or "") < since_iso:
            continue
        stmt = ""
        probe = c.get("recompilable_probe") or ""
        if probe:
            try:   # canonical decl parser (statement_integrity) — never a re-rolled regex
                from ztare.leanmill.solver.statement_integrity import decl_blocks
                blocks = dict(decl_blocks(probe))
                stmt = blocks.get(c.get("target")) or next(iter(blocks.values()), "")
            except Exception:  # noqa: BLE001 — best-effort render; the cert itself stays authoritative
                stmt = probe
            from ztare.leanmill.lean_source import signature_before_proof   # canonical binder-safe head extractor
            stmt = " ".join(signature_before_proof(stmt).split())[:300]
        key = c.get("goal_sha") or (c.get("target"), stmt)
        if key in seen:
            continue
        seen.add(key)
        out.append({"target": c.get("target"), "goal_sha": c.get("goal_sha"), "statement": stmt,
                    "closure_lean": c.get("closure_lean"),
                    "integrity_unverified": bool((c.get("governance") or {}).get("integrity_unverified")),
                    # margin-of-safety tier (differential re-verification battery): fragile = kernel-TRUE
                    # but weakened signals (decorative hypotheses etc.) — still citable, flagged honestly
                    "fragile": ((c.get("governance") or {}).get("margin_of_safety") or {})
                    .get("overall") == "fragile_advisory"})
    return out


def _run_shelf_prelude(out: dict, since_iso: str, *, ledger: "Optional[Path]" = None) -> str:
    """Assemble THIS run's proven sibling lemmas into a compile prelude so the TARGET solve has them IN SCOPE
    and can CITE them (a true dependency graph) rather than re-deriving inline — the composition fix
    (2026-06-23, after Gemini flagged the FTAP target re-proving its lemmas as dead code).

    Source = the closure-cert ledger's `recompilable_probe` (the full proven `theorem … := <proof>`), the same
    ledger `deep_closures_since` reads. FILTERED to this run's own closed-lemma decl names (a concurrent
    campaign shares the ledger, so a since-`ts` window alone would import a neighbour's lemmas). Imports are
    stripped (the assembled target body supplies exactly one). Canonical decl parser (`statement_integrity.
    decl_blocks`) — never a re-rolled regex. Returns "" when nothing applies (⇒ byte-identical to the old body)."""
    from ztare.leanmill.solver.statement_integrity import decl_blocks
    names: set = set()
    for lem in out.get("lemmas", []):
        if not lem.get("solved"):
            continue
        try:
            for nm, _blk in decl_blocks(lem.get("lean_statement") or ""):
                if nm:
                    names.add(nm)
        except Exception:  # noqa: BLE001
            continue
    if not names:
        return ""
    if ledger is None:
        from ztare.leanmill.solver.solver_core import ADHOC_CLOSURE_CERTIFICATES as _L
        ledger = _L
    pieces: "list[str]" = []
    seen: set = set()
    try:
        lines = Path(ledger).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for ln in lines:
        try:
            c = json.loads(ln)
        except ValueError:
            continue
        if c.get("outcome") != "closed" or str(c.get("ts") or "") < (since_iso or ""):
            continue
        tgt = c.get("target") or ""
        if tgt not in names or tgt in seen:
            continue
        probe = c.get("recompilable_probe") or ""
        if not probe.strip():
            continue
        seen.add(tgt)
        body = "\n".join(l for l in probe.splitlines() if not l.lstrip().startswith("import")).strip()
        if body:
            pieces.append(body)
    return "\n\n".join(pieces)


def _self_test() -> int:
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # --- parse ---
    NOTES = "## Target\nFor all n, P n.\n## Lemmas\n- Lemma A.\n* Lemma B.\n"
    tgt, lems = parse_notes(NOTES)
    ok("parse_target", tgt == "For all n, P n.")
    ok("parse_lemmas_dash_and_star", lems == ["Lemma A.", "Lemma B."])
    ok("parse_no_lemmas_section", parse_notes("## Target\nX.\n")[1] == [])
    ok("parse_multiline_target",
       parse_notes("## Target\nline one\nline two\n## Lemmas\n- L.\n")[0] == "line one line two")
    # canonical ## Lemmas editor (no scattered regex; the sorried-work-item queueing fix)
    _il = _insert_lemmas_section("## Target\nT.\n## Lemmas\n- human rung\n", ["theorem c1 : P", "theorem c2 : Q"])
    ok("insert_lemmas: bullets spliced foundational-FIRST under existing ## Lemmas",
       _il.index("- theorem c1 : P") < _il.index("- human rung") and "- theorem c2 : Q" in _il
       and parse_notes(_il)[1][:2] == ["theorem c1 : P", "theorem c2 : Q"])   # parse round-trips
    _il2 = _insert_lemmas_section("## Target\nT.\n## Theory file\nt.lean\n", ["theorem only : R"])
    ok("insert_lemmas: NO ## Lemmas anchor ⇒ section CREATED (work-items never dropped)",
       "## Lemmas" in _il2 and parse_notes(_il2)[1] == ["theorem only : R"]
       and "## Theory file" in _il2)   # preserves the rest
    ok("insert_lemmas: empty bullets ⇒ unchanged",
       _insert_lemmas_section("## Target\nT.\n", []) == "## Target\nT.\n")

    # --- hermetic loop: Lemma A closes, Lemma B exact_gaps, target opens ---
    seen_notes: dict = {}
    seen_prelude: dict = {}

    def mock_attack(nl, *, lean_root, timeout_s, notes=None, shelf_prelude=""):
        seen_notes[nl] = notes
        seen_prelude[nl] = shelf_prelude
        closed = nl == "Lemma A."
        return {"nl": nl, "lean_statement": f"theorem t : {nl} := by sorry", "faithful": True,
                "outcome": "admitted_and_closed" if closed else "admitted_and_exact_gap",
                "solved": closed}

    res = autoformalize_from_notes(NOTES, attack_fn=mock_attack, on_progress=lambda m: None)
    ok("loop_runs_all_lemmas", len(res["lemmas"]) == 2)
    ok("shelf_only_closed_lemmas", res["shelf"] == ["theorem t : Lemma A. := by sorry"])
    ok("summary_counts", res["summary"].startswith("1/2 lemmas formalized+closed; shelf=1;"))
    ok("target_attacked", res["target"] is not None and res["target"]["nl"] == "For all n, P n.")
    # the blueprint is threaded as planner context for every line (the #81 uplevel)
    ok("notes_threaded_to_lemmas", "## Lemmas" in (seen_notes.get("Lemma A.") or ""))
    ok("target_notes_carry_shelf",
       "Proven lemmas (citable)" in (seen_notes.get("For all n, P n.") or "")
       and "theorem t : Lemma A." in (seen_notes.get("For all n, P n.") or ""))
    # composition fix: the target attack is invoked WITH the shelf_prelude kwarg (in scope, not just notes text)
    ok("target_gets_shelf_prelude_kwarg", "For all n, P n." in seen_prelude)

    # --- the false-positive guard: a non-'closed' truthy outcome must NOT count as solved ---
    def gap_attack(nl, *, lean_root, timeout_s, notes=None, shelf_prelude=""):
        return {"nl": nl, "lean_statement": "", "faithful": True,
                "outcome": "admitted_and_exact_gap", "solved": False}

    r2 = autoformalize_from_notes("## Target\nG.\n## Lemmas\n- A.\n",
                                  attack_fn=gap_attack, on_progress=lambda m: None)
    ok("exact_gap_not_in_shelf", r2["shelf"] == [])
    ok("exact_gap_zero_closed", r2["summary"].startswith("0/1 lemmas"))

    # --- empty target → no target attack, loop still runs lemmas ---
    r3 = autoformalize_from_notes("## Lemmas\n- A.\n", attack_fn=mock_attack, on_progress=lambda m: None)
    ok("empty_target_no_attack", r3["target"] is None and r3["summary"].endswith("target open"))

    # --- compound_into_original_notes (#97): regenerate ## Lemmas from the planner's decomposition, PRESERVE the rest ---
    import os as _os, tempfile as _tf, shutil as _sh
    _td = _tf.mkdtemp(prefix="leanmill_compound_")
    np = Path(_td) / "seed.md"
    # ## Idea is BEFORE ## Lemmas; ## References is AFTER it — the order-robust case the prior split-on-Lemmas dropped.
    SEED = ("## Target\nFor all n, P n.\n## Idea\nUse induction.\n## Lemmas\n- human seed lemma\n"
            "## References\n- Foo 2020\n")
    decomp = {"target": {"decomposition": {"lemmas": ["base case P 0", "step P k -> P (k+1)"]}}, "lemmas": []}
    _prev = _os.environ.get("ZTARE_LEANMILL_COMPOUND_ORIGINAL")
    try:
        np.write_text(SEED, encoding="utf-8")
        _os.environ["ZTARE_LEANMILL_COMPOUND_ORIGINAL"] = "0"   # explicit =0 still reverts (the A/B baseline)
        ok("compound_explicit_off_noop",
           compound_into_original_notes(decomp, np) is None and np.read_text(encoding="utf-8") == SEED)
        _os.environ.pop("ZTARE_LEANMILL_COMPOUND_ORIGINAL", None)   # DEFAULT (unset) now COMPOUNDS (default-on)
        out = compound_into_original_notes(decomp, np)
        txt = np.read_text(encoding="utf-8")
        ok("compound_writes_and_returns_path", out == np)
        ok("compound_has_planner_lemmas", "- base case P 0" in txt and "- step P k -> P (k+1)" in txt)
        ok("compound_regenerates_old_lemma_body", "- human seed lemma" not in txt)  # ## Lemmas body is regenerated by design
        ok("compound_preserves_pre_lemmas_sections", "## Target" in txt and "Use induction." in txt)
        ok("compound_preserves_post_lemmas_section", "## References" in txt and "Foo 2020" in txt)  # the order-robust fix
        # idempotent: a SECOND compound on the already-compounded file must not STACK markers
        compound_into_original_notes(decomp, np)
        txt2 = np.read_text(encoding="utf-8")
        ok("compound_idempotent_single_marker", txt2.count("auto-compounded from the planner") == 1)
        ok("compound_idempotent_still_preserves", "## References" in txt2 and "Use induction." in txt2)
        np.write_text(SEED, encoding="utf-8")
        ok("compound_no_decomp_never_clobbers",
           compound_into_original_notes({"target": None, "lemmas": []}, np) is None
           and np.read_text(encoding="utf-8") == SEED)
        nf = Path(_td) / "notseed.md"; nf.write_text("just prose\n", encoding="utf-8")
        ok("compound_refuses_non_seed_file",
           compound_into_original_notes(decomp, nf) is None and nf.read_text(encoding="utf-8") == "just prose\n")

        # --- deep rungs (v3 RCA): cert-ledger → refined notes + accumulated auto-section in the ORIGINAL ---
        ledger = Path(_td) / "certs.jsonl"
        _c = {"ts": "2026-06-12T16:29:02+00:00", "target": "iso_lemma1", "outcome": "closed",
              "goal_sha": "abcd1234abcd1234", "recompilable_probe":
              "import Mathlib\n\ntheorem iso_lemma1 : 1 + 1 = 2 := by norm_num\n",
              "closure_lean": "ztare_proofs/closures/iso_lemma1.lean", "governance": {}}
        _unv = dict(_c, target="iso_lemma2", goal_sha="ffff0000ffff0000",
                    governance={"integrity_unverified": True}, recompilable_probe="")
        _old = dict(_c, ts="2026-06-11T00:00:00+00:00", goal_sha="0ld0000000000000")
        ledger.write_text("\n".join(json.dumps(x) for x in (_c, _unv, _old,
                          dict(_c, outcome="rejected_governance", goal_sha="rej0000000000000"))) + "\n",
                          encoding="utf-8")
        dc = deep_closures_since("2026-06-12T00:00:00+00:00", ledger=ledger)
        ok("deep_closures: closed-in-window only (old + rejected excluded)",
           {d["goal_sha"] for d in dc} == {"abcd1234abcd1234", "ffff0000ffff0000"})
        ok("deep_closures: statement via canonical decl parser (no proof tail)",
           any(d["statement"].startswith("theorem iso_lemma1 : 1 + 1 = 2") and ":= by" not in d["statement"]
               for d in dc))
        ok("deep_closures: integrity_unverified FLAGGED",
           any(d["integrity_unverified"] for d in dc if d["target"] == "iso_lemma2"))
        # refined render: verified rung cited, unverified marked not-citable
        r_deep = {"target_nl": "T", "summary": "s", "lemmas": [], "shelf": [], "deep_closures": dc}
        rp = write_refined_notes(r_deep, Path(_td) / "deep.md")
        rt = rp.read_text(encoding="utf-8")
        ok("refined: deep-rungs section rendered",
           "deep rungs" in rt and "iso_lemma1 [sha:abcd1234abcd1234]" in rt)
        ok("refined: unverified rung marked NOT auto-citable", "NOT auto-citable" in rt)

        # --- GAP LEDGER (honest non-closures recorded for the next planner pass; gap≠closure) ---
        ok("gap_class: outcome for a faithful-but-open record",
           _gap_class({"faithful": True, "outcome": "admitted_and_exact_gap"}) == "admitted_and_exact_gap")
        ok("gap_class: firewall_rejected for an unfaithful record",
           _gap_class({"faithful": False, "faithfulness_reason": "vacuous: hypothesis is False"})
           .startswith("firewall_rejected:"))
        r_gap = {"target_nl": "Prove the big thing", "summary": "s",
                 "lemmas": [{"nl": "L1 closes", "solved": True, "outcome": "closed", "faithful": True},
                            {"nl": "L2 gaps", "solved": False, "outcome": "admitted_and_exact_gap",
                             "faithful": True},
                            {"nl": "L3 unfaithful", "solved": False, "faithful": False,
                             "faithfulness_reason": "trivial: provable by simp"}],
                 "shelf": ["theorem l1 : True := trivial"],
                 "target": {"nl": "Prove the big thing", "solved": False, "outcome": "admitted_and_open",
                            "faithful": True},
                 "wall_deferred": ["L4 never attempted"]}
        gt = write_refined_notes(r_gap, Path(_td) / "gap.md").read_text(encoding="utf-8")
        ok("gap: non-closure ledger header present",
           "Gaps this run (non-closures" in gt and "NOT proven, NOT citable" in gt)
        ok("gap: open lemma recorded with its typed failure class",
           "L2 gaps — gap[admitted_and_exact_gap]" in gt)
        ok("gap: firewall-rejected lemma recorded as such",
           "L3 unfaithful — gap[firewall_rejected" in gt)
        ok("gap: TARGET gap recorded with its class",
           "(TARGET) Prove the big thing — gap[admitted_and_open]" in gt)
        ok("gap: wall-deferred lemma recorded as deferred:campaign_wall",
           "L4 never attempted — gap[deferred:campaign_wall]" in gt)
        ok("gap: a CLOSED lemma is NOT in the gap ledger (only in ✅ proven)",
           "L1 closes — gap[" not in gt and "- ✅ L1 closes" in gt)
        # a wall-deferred TARGET is recorded ONCE (not double-counted via wall_deferred + target)
        r_wallt = {"target_nl": "Big T", "summary": "s", "lemmas": [],
                   "target": {"deferred": "campaign_wall", "solved": False}, "wall_deferred": ["Big T"]}
        rwt = write_refined_notes(r_wallt, Path(_td) / "wallt.md").read_text(encoding="utf-8")
        ok("gap: wall-deferred TARGET recorded once (no double-count)",
           rwt.count("— gap[deferred:campaign_wall]") == 1 and "(TARGET) Big T" in rwt)
        # a fully-closed run renders NO gap ledger (clean output)
        r_clean = {"target_nl": "T", "summary": "s",
                   "lemmas": [{"nl": "all good", "solved": True, "outcome": "closed", "faithful": True}],
                   "shelf": ["theorem g : True := trivial"],
                   "target": {"nl": "T", "solved": True, "outcome": "closed", "faithful": True}}
        ok("gap: fully-closed run has NO gap ledger",
           "Gaps this run" not in write_refined_notes(r_clean, Path(_td) / "clean.md").read_text(encoding="utf-8"))

        # compound: only VERIFIED rungs reach the original; accumulates + dedupes by sha across runs
        np.write_text(SEED, encoding="utf-8")
        compound_into_original_notes(dict(decomp, deep_closures=dc), np)
        t1 = np.read_text(encoding="utf-8")
        ok("compound: verified rung in ORIGINAL notes; unverified excluded",
           "iso_lemma1 [sha:abcd1234abcd1234]" in t1 and "ffff0000ffff0000" not in t1)
        compound_into_original_notes(dict(decomp, deep_closures=dc), np)   # idempotent re-run
        t2 = np.read_text(encoding="utf-8")
        ok("compound: rungs accumulate WITHOUT duplication (sha-dedup)",
           t2.count("abcd1234abcd1234") == 1 and t2.count("proven-rungs:auto") >= 1
           and "## References" in t2)
        # rungs-only update (planner produced NO decomposition) must not clobber ## Lemmas
        compound_into_original_notes({"target": None, "lemmas": [], "deep_closures": dc}, np)
        t3 = np.read_text(encoding="utf-8")
        ok("compound: rungs-only update preserves ## Lemmas body",
           "- base case P 0" in t3 and t3.count("abcd1234abcd1234") == 1)

        # --- THEORY CONSOLIDATION (#123): append-only + compile gates, sorried-API extraction ---
        troot = Path(_td) / "lroot"; troot.mkdir()
        tfile = troot / "T.lean"
        tfile.write_text("import Mathlib\n\ndef GoodDef (n : Nat) : Prop := n = n\n", encoding="utf-8")
        ok("theory: parse_theory_file finds the section",
           parse_theory_file("## Target\nX.\n## Theory file\nZtareProofs/T.lean\n") == "ZtareProofs/T.lean")

        def disp_extend(prompt, *, repo=None, timeout=None):
            tfile.write_text(tfile.read_text(encoding="utf-8")
                             + "\ndef NewDef (n : Nat) : Prop := 0 < n\n"
                             + "theorem newdef_api (n : Nat) (h : NewDef n) : 0 < n := by sorry\n",
                             encoding="utf-8")
        r_ok = theory_consolidation("## Target\nX.\n", "T.lean", lean_root=troot,
                                    dispatch=disp_extend, compile_fn=lambda *a: True)
        ok("theory: extension accepted; new decls + sorried API extracted",
           r_ok["ok"] and "NewDef" in r_ok["new_decls"]
           and any("newdef_api" in s for s in r_ok["sorried_statements"]))

        # GATE 3 (vacuous-bridge class, EF1 RCA): a trivially-true new sorried shelf lemma is rejected + reverted.
        def disp_vacuous(prompt, *, repo=None, timeout=None):
            tfile.write_text(tfile.read_text(encoding="utf-8")
                             + "\ntheorem vacuous_bridge (n : Nat) : ∃ d : Option Nat, True := by sorry\n",
                             encoding="utf-8")
        _before_vac = tfile.read_text(encoding="utf-8")
        r_vac = theory_consolidation("## Target\nX.\n", "T.lean", lean_root=troot, dispatch=disp_vacuous,
                                     compile_fn=lambda *a: True,
                                     triviality_fn=lambda stmt, sb: ", True :=" in stmt or stmt.rstrip().endswith(": True"))
        ok("theory: GATE3 rejects a vacuous (trivially-true) sorried shelf lemma + reverts",
           r_vac["ok"] is False and r_vac.get("vacuous_shelf_lemmas")
           and tfile.read_text(encoding="utf-8") == _before_vac)

        def disp_real(prompt, *, repo=None, timeout=None):   # a genuine (non-trivial) bridge passes GATE 3
            tfile.write_text(tfile.read_text(encoding="utf-8")
                             + "\ntheorem real_bridge (n : Nat) (h : 0 < n) : n ≠ 0 := by sorry\n", encoding="utf-8")
        r_real = theory_consolidation("## Target\nX.\n", "T.lean", lean_root=troot, dispatch=disp_real,
                                      compile_fn=lambda *a: True, triviality_fn=lambda stmt, sb: False)
        ok("theory: GATE3 accepts a non-trivial sorried shelf lemma",
           r_real["ok"] and any("real_bridge" in s for s in r_real["sorried_statements"]))

        def disp_edit(prompt, *, repo=None, timeout=None):   # REWRITES an existing line — the launder
            tfile.write_text(tfile.read_text(encoding="utf-8")
                             .replace("def GoodDef (n : Nat) : Prop := n = n",
                                      "def GoodDef (n : Nat) : Prop := True"), encoding="utf-8")
        before_edit = tfile.read_text(encoding="utf-8")
        r_edit = theory_consolidation("## Target\nX.\n", "T.lean", lean_root=troot,
                                      dispatch=disp_edit, compile_fn=lambda *a: True)
        ok("theory: definition EDIT rejected + file reverted (append-only integrity)",
           r_edit["ok"] is False and r_edit.get("reverted")
           and tfile.read_text(encoding="utf-8") == before_edit)

        def disp_broken(prompt, *, repo=None, timeout=None):
            tfile.write_text(tfile.read_text(encoding="utf-8") + "\ndef Broken : := :=\n", encoding="utf-8")
        r_bad = theory_consolidation("## Target\nX.\n", "T.lean", lean_root=troot,
                                     dispatch=disp_broken, compile_fn=lambda *a: False)
        ok("theory: non-compiling extension reverted",
           r_bad["ok"] is False and "Broken" not in tfile.read_text(encoding="utf-8"))
        r_same = theory_consolidation("## Target\nX.\n", "T.lean", lean_root=troot,
                                      dispatch=lambda p, **k: None, compile_fn=lambda *a: True)
        ok("theory: unchanged file ⇒ ok/unchanged (no spurious receipt work)",
           r_same["ok"] and r_same.get("unchanged"))

        def disp_supersede(prompt, *, repo=None, timeout=None):
            tfile.write_text(tfile.read_text(encoding="utf-8")
                             + "\n-- SUPERSEDE: GoodDef: wrong-shaped, API lemma unprovable\n"
                             + "def BetterDef (n : Nat) : Prop := 0 < n + 1\n", encoding="utf-8")
        r_sup = theory_consolidation("## Target\nX.\n", "T.lean", lean_root=troot,
                                     dispatch=disp_supersede, compile_fn=lambda *a: True)
        ok("theory: SUPERSEDE request captured (queued, file NOT rewritten, additions accepted)",
           r_sup["ok"] and r_sup.get("supersession_requests", [{}])[0].get("name") == "GoodDef"
           and "def GoodDef (n : Nat) : Prop := n = n" in tfile.read_text(encoding="utf-8"))
    finally:
        if _prev is None:
            _os.environ.pop("ZTARE_LEANMILL_COMPOUND_ORIGINAL", None)
        else:
            _os.environ["ZTARE_LEANMILL_COMPOUND_ORIGINAL"] = _prev
        _sh.rmtree(_td, ignore_errors=True)

    # ── governed_def_revision_gate (supersession-ACTING anti-gaming, 2026-06-23) ──
    _before = "import Mathlib\ndef D (n : Nat) : Prop := n ≥ 0\ntheorem other : True := trivial\n"
    _after_ok = ("import Mathlib\n"
                 "def D__pre (n : Nat) : Prop := n ≥ 0\n"                          # old preserved verbatim
                 "def D (n : Nat) : Prop := n ≥ 0 ∧ n ≤ 100\n"                     # STRENGTHENED
                 "theorem witness_strengthen_D : ∀ n, D n → D__pre n := fun _ h => h.1\n"  # new → old
                 "theorem other : True := trivial\n")                              # untouched
    _ok, _ = governed_def_revision_gate(_before, _after_ok, "D", verify_fn=lambda w: w == "witness_strengthen_D")
    ok("revision gate: strengthening + KERNEL-verified witness ⇒ ACCEPTED", _ok)
    _ok2, _ = governed_def_revision_gate(_before, _after_ok, "D", verify_fn=lambda w: False)
    ok("revision gate: witness NOT kernel-verified ⇒ REJECTED (anti-gaming core)", not _ok2)
    _after_other = _after_ok.replace("theorem other : True := trivial", "theorem other : False := sorry")
    _ok3, _ = governed_def_revision_gate(_before, _after_other, "D", verify_fn=lambda w: True)
    ok("revision gate: changing a NON-superseded decl ⇒ REJECTED (append-only stands)", not _ok3)
    _after_nopre = _after_ok.replace("def D__pre (n : Nat) : Prop := n ≥ 0\n", "")
    _ok4, _ = governed_def_revision_gate(_before, _after_nopre, "D", verify_fn=lambda w: True)
    ok("revision gate: old def not preserved as __pre ⇒ REJECTED", not _ok4)
    _after_nowit = _after_ok.replace("theorem witness_strengthen_D : ∀ n, D n → D__pre n := fun _ h => h.1\n", "")
    _ok5, _ = governed_def_revision_gate(_before, _after_nowit, "D", verify_fn=lambda w: True)
    ok("revision gate: missing strengthening witness ⇒ REJECTED", not _ok5)
    # a non-superseded CONCEPT def (Prop-valued) changed ⇒ REJECTED (the meaning/laundering surface stays fixed)
    _before_e = "import Mathlib\ndef E (n : Nat) : Prop := True\ndef D (n : Nat) : Prop := n ≥ 0\ntheorem other : True := trivial\n"
    _after_e = ("import Mathlib\ndef E (n : Nat) : Prop := False\n"   # CONCEPT def E changed
                "def D__pre (n : Nat) : Prop := n ≥ 0\ndef D (n : Nat) : Prop := n ≥ 0 ∧ n ≤ 100\n"
                "theorem witness_strengthen_D : ∀ n, D n → D__pre n := fun _ h => h.1\ntheorem other : True := trivial\n")
    _ok6, _ = governed_def_revision_gate(_before_e, _after_e, "D", verify_fn=lambda w: True)
    ok("revision gate: a non-superseded CONCEPT def changed ⇒ REJECTED", not _ok6)
    # a THEOREM proof ADAPTS (signature unchanged) ⇒ ACCEPTED (a structure instance/dependent may re-prove)
    _after_padapt = _after_ok.replace("theorem other : True := trivial", "theorem other : True := by trivial")
    _ok7, _ = governed_def_revision_gate(_before, _after_padapt, "D", verify_fn=lambda w: w == "witness_strengthen_D")
    ok("revision gate: a theorem PROOF adapts (signature same) ⇒ ACCEPTED", _ok7)

    # governed_def_revision orchestrator (mock dispatch + injected compile/verify — no live Lean)
    import tempfile as _tfr, shutil as _shr
    _lr3 = Path(_tfr.mkdtemp())
    _orig3 = "import Mathlib\ndef D (n : Nat) : Prop := True\ntheorem t : True := trivial\n"
    (_lr3 / "T.lean").write_text(_orig3, encoding="utf-8")
    def _disp_strong(prompt, *, repo=None, timeout=None):
        (_lr3 / "T.lean").write_text(
            "import Mathlib\ndef D__pre (n : Nat) : Prop := True\n"
            "def D (n : Nat) : Prop := n ≥ 0\n"
            "theorem witness_strengthen_D : ∀ n, D n → D__pre n := fun _ _ => trivial\n"
            "theorem t : True := trivial\n", encoding="utf-8")
    _rv = governed_def_revision("T.lean", lean_root=_lr3, dispatch=_disp_strong, false_lemma="thm", counterexample="cex",
                                compile_fn=lambda *a: True,
                                verify_fn_factory=lambda src, root: (lambda w: w == "witness_strengthen_D"))
    ok("governed_def_revision: agent strengthening + gate ⇒ revised", _rv.get("ok") and _rv.get("revised_def") == "D")
    (_lr3 / "T.lean").write_text(_orig3, encoding="utf-8")
    def _disp_garbage(prompt, *, repo=None, timeout=None):
        (_lr3 / "T.lean").write_text("import Mathlib\ndef D (n : Nat) : Prop := n = n\ntheorem t : True := trivial\n", encoding="utf-8")
    _rv2 = governed_def_revision("T.lean", lean_root=_lr3, dispatch=_disp_garbage, false_lemma="t", counterexample="c",
                                 compile_fn=lambda *a: True, verify_fn_factory=lambda src, root: (lambda w: True))
    ok("governed_def_revision: no __pre/witness pattern ⇒ reverted + file restored",
       (not _rv2.get("ok")) and _rv2.get("reverted") and (_lr3 / "T.lean").read_text(encoding="utf-8") == _orig3)
    _shr.rmtree(str(_lr3), ignore_errors=True)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


def compound_into_original_notes(result: dict, notes_path: "Optional[Path]") -> "Optional[Path]":
    """COMPOUND the PLANNER's own generated decomposition back into the ORIGINAL notes (#97, operator vision:
    the agent adds the breakdown itself — "in the original file", not just .refined.md). Source = the
    `decomposition` sub-DAG `route_and_solve` already stashes in each attack record (the TARGET's, for a minimal
    seed, plus any per-lemma sub-DAGs) — NOT human-authored. Rewrites ONLY the `## Lemmas` BODY, PRESERVING every
    other section in place — the human `## Target` / `## Idea` above AND any section that follows `## Lemmas`
    (e.g. `## References`); only the auto-generated bullet list is regenerated. The next run's parser then attacks the
    agent's OWN breakdown → the compounding loop closes with no human in it. Deterministic render of the agent's
    output (not authoring), so no fake-closure risk. SOUND ⇒ **DEFAULT-ON** (`ZTARE_LEANMILL_COMPOUND_ORIGINAL`, `=0`
    reverts): a deterministic render of the agent's own decomposition has NO soundness surface, so leaving it off only
    threw away the agent's work between runs (the loop never compounded). No-op when the planner produced no decomposition (never clobbers the seed) or
    the file is not a parseable `## Target` seed."""
    import os as _os
    if _os.environ.get("ZTARE_LEANMILL_COMPOUND_ORIGINAL", "1") == "0" or notes_path is None:
        return None
    gen: "list[str]" = []
    def _collect(rec: "Optional[dict]") -> None:
        dec = (rec or {}).get("decomposition") or {}
        for s in (dec.get("lemmas") or []):
            t = " ".join(str(s).split()).strip()
            if t and t not in gen:
                gen.append(t)
    _collect(result.get("target"))
    for l in (result.get("lemmas") or []):
        _collect(l)
    # Deep rungs (v3 RCA 2026-06-12): integrity-VERIFIED kernel closures from the whole recursion tree —
    # these must reach the ORIGINAL notes (the file the next run parses + threads as planner context), or
    # the next run re-derives them (the amnesia disease). Unverified ones are EXCLUDED — never teach the
    # agent to cite a rung whose statement integrity the organs could not check.
    rungs = [d for d in (result.get("deep_closures") or []) if not d.get("integrity_unverified")]
    if not gen and not rungs:
        return None   # nothing to compound; leave the seed untouched
    try:
        text = notes_path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not re.search(r"(?m)^##\s*Target\s*$", text):
        return None   # not a parseable seed ⇒ refuse (never clobber an unexpected file)
    # ACCUMULATE the auto proven-rungs section across runs: lift the prior marker-delimited block out of the
    # text (so the ## Lemmas split below never mistakes it for human tail content), union its bullets with
    # this run's rungs by [sha:…] identity, and re-append fresh at the end. Idempotent by construction.
    _rung_lines: "list[str]" = []
    _rung_block = re.search(r"(?s)<!-- proven-rungs:auto -->\n?(.*?)<!-- /proven-rungs:auto -->\n?", text)
    if _rung_block:
        _rung_lines = [l for l in _rung_block.group(1).splitlines() if l.lstrip().startswith("- ")]
        text = text[:_rung_block.start()] + text[_rung_block.end():]
    _have_shas = {m.group(1) for l in _rung_lines for m in [re.search(r"\[sha:([0-9a-f]+)\]", l)] if m}
    for d in rungs:
        if d.get("goal_sha") and d["goal_sha"] in _have_shas:
            continue
        loc = f" ({d.get('closure_lean')})" if d.get("closure_lean") else ""
        _rung_lines.append(f"- ✅ {d.get('target')} [sha:{d.get('goal_sha')}] {d.get('statement', '')}{loc}")
    parts = re.split(r"(?m)^##\s*Lemmas\s*$", text, maxsplit=1)
    # strip any PRIOR auto-compound marker so re-runs don't STACK markers (it lives just above ## Lemmas ⇒ lands in head)
    head = re.sub(r"(?m)^<!-- ## Lemmas below: auto-compounded.*?-->[ \t]*\n?", "", parts[0]).rstrip()
    tail = ""   # PRESERVE any human section AFTER ## Lemmas (e.g. ## References, or a post-Lemmas ## Idea): only the
    if len(parts) > 1:   # old auto-generated bullet body is regenerated; the next `## ` heading onward is human content.
        nxt = re.search(r"(?m)^##\s+\S", parts[1])
        if nxt:
            tail = parts[1][nxt.start():].rstrip()
    marker = ("<!-- ## Lemmas below: auto-compounded from the planner's OWN decomposition (route_and_solve, #97). "
              "Reseed by editing ## Target / ## Idea above; this section is regenerated each run. -->")
    if gen:
        body = (head + "\n\n" + marker + "\n## Lemmas\n"
                + "\n".join(f"- {g}" for g in gen) + "\n")
        if tail:
            body += "\n" + tail + "\n"
    else:
        body = text.rstrip() + "\n"   # rungs-only update: NEVER regenerate ## Lemmas to empty (would clobber)
    if _rung_lines:
        body += ("\n<!-- proven-rungs:auto -->\n## Proven rungs (kernel-closed, auto — citable)\n"
                 + "\n".join(_rung_lines) + "\n<!-- /proven-rungs:auto -->\n")
    notes_path.write_text(body, encoding="utf-8")
    _emit_notes_writeback_trace({
        "kind": "compound_original_notes",
        "notes_path": str(notes_path),
        "generated_lemma_count": len(gen),
        "proven_rung_count": len(_rung_lines),
        "new_rung_input_count": len(rungs),
        "wrote_lemmas_section": bool(gen),
    })
    return notes_path


def regenerate_dashboard(repo_root, runner=None) -> "str | None":
    """#119 post-run hook: regenerate the ONE leanmill dashboard (scripts/public/control/leanmill/
    leanmill_dashboard.py) so every run ends with fresh artifacts — no more stale post-run reviews.
    Best-effort observability: bounded by the `dashboard_regen` factory budget (=0 disables), runs as a
    SUBPROCESS (src/ must not import scripts/ — the standing boundary), fail-quiet-loud (one line,
    never affects the run result). Returns the dashboard path on success, None otherwise."""
    from pathlib import Path as _P
    from ztare.common.timeouts import timeout_s as _ts_dash
    budget = _ts_dash("dashboard_regen")
    if not budget:
        return None
    script = _P(repo_root) / "scripts" / "public" / "control" / "leanmill" / "leanmill_dashboard.py"
    if not script.exists():
        print(f"[notes] dashboard regen skipped: {script} absent", flush=True)
        return None
    import subprocess as _sp
    import sys as _sys
    run = runner or _sp.run
    try:
        proc = run([_sys.executable, str(script)], cwd=str(repo_root), timeout=budget,
                   capture_output=True, text=True)
        if getattr(proc, "returncode", 1) == 0:
            tail = (getattr(proc, "stdout", "") or "").strip().splitlines()
            print(f"[notes] dashboard regenerated{(': ' + tail[-1]) if tail else ''}", flush=True)
            return str(script)
        print(f"[notes] dashboard regen FAILED rc={getattr(proc, 'returncode', '?')}: "
              f"{(getattr(proc, 'stderr', '') or '')[-200:]}", flush=True)
    except Exception as _e:  # noqa: BLE001 — observability must never mask the run result
        print(f"[notes] dashboard regen error: {_e!r}"[:200], flush=True)
    return None


def _free_mem_gb() -> "Optional[float]":
    """Available RAM in GB from /proc/meminfo MemAvailable (Linux). None where unavailable (non-Linux / no proc)."""
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / (1024 * 1024)   # kB → GB
    except Exception:  # noqa: BLE001
        return None
    return None


def _reap_orphan_repls() -> "list[int]":
    """Kill lean_repl processes whose PARENT IS DEAD (PPID==1, reparented to init) — true orphans holding
    Mathlib-sized RAM from a prior run. A LIVE run's REPL has a live parent (PPID != 1), so it is never touched.
    Conservative by construction; returns the PIDs reaped. Best-effort (`ps` + SIGTERM); any error → reap nothing."""
    import signal
    import subprocess
    reaped: "list[int]" = []
    try:
        out = subprocess.run(["ps", "-eo", "pid,ppid,args"], capture_output=True, text=True, timeout=15).stdout
    except Exception:  # noqa: BLE001 — no ps / timeout ⇒ reap nothing
        return reaped
    for line in out.splitlines()[1:]:
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        pid_s, ppid_s, args = parts
        if "lean_repl" in args and "/repl" in args and ppid_s == "1":   # orphaned REPL (dead parent)
            try:
                import os as _o
                _o.kill(int(pid_s), signal.SIGTERM)
                reaped.append(int(pid_s))
            except (ValueError, ProcessLookupError, PermissionError):
                pass
    return reaped


def main(argv: "Optional[list[str]]" = None) -> int:
    import os as _os   # FUNCTION-SCOPE binding: the embedder-liveness preflight (below) reads _os BEFORE the old
    #   later `import os as _os` bound it — Python made _os local throughout main(), so the early read raised
    #   UnboundLocalError and aborted the run at start. One import, at the top, is the fix (no shadowing sibling).
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--selftest":
        return _self_test()
    if not argv:
        print("usage: python -m ztare.leanmill.solver.autoformalize_notes <notes.md> | --selftest")
        return 2
    from ztare.leanmill.preflight_carriers import assert_carriers_live
    assert_carriers_live()
    # RUN-START RESOURCE GUARD (2026-07-02): a prior run's ORPHANED lean_repl (parent dead → reparented to init)
    # holds Mathlib-sized RAM and can starve THIS run's warm env (a live warm env died to memory pressure today; 6
    # stale REPLs were hand-reaped). Reap ONLY demonstrably-dead-parent orphans (PPID==1) — never a live run's
    # REPL — and warn (not block) on low memory. Conservative + reversible (ZTARE_LEANMILL_REAP_ORPHAN_REPLS=0).
    if _os.environ.get("ZTARE_LEANMILL_REAP_ORPHAN_REPLS", "1") != "0":
        try:
            _reaped = _reap_orphan_repls()
            if _reaped:
                print(f"[notes] resource-guard: reaped {len(_reaped)} orphaned lean_repl(s) (dead parent): {_reaped}",
                      flush=True)
            _memg = _free_mem_gb()
            if _memg is not None and _memg < 3.0:
                print(f"[notes] resource-guard ⚠ only {_memg:.1f} GB free — the warm env may not fit; "
                      f"a heavy substrate can degrade to cold verify", flush=True)
        except Exception as _e:  # noqa: BLE001 — a guard failure must never block the run
            print(f"[notes] resource-guard skipped: {repr(_e)[:100]}", flush=True)
    # #116 INTERNAL STANDARDS (isotope-dilution discipline): a known-positive must CLOSE + a canned cheat must
    # be REJECTED through the same pipeline BEFORE the run spends its wallclock — fail-closed on a dead
    # instrument; the certificate is stamped into the run artifact so every closure is traceable to a
    # demonstrably-live, demonstrably-refusing instrument. ZTARE_LEANMILL_RUN_STANDARDS=0 reverts.
    from ztare.leanmill.run_standards import run_instrument_standards
    _std = run_instrument_standards(LEAN_ROOT_DEFAULT)
    print(f"[notes] instrument standards: {_std.get('detail', 'skipped (=0)')}", flush=True)
    if not _std.get("ok"):
        print("[notes] ABORT — instrument standards FAILED (fail-closed: fix the instrument, do not burn the run)")
        return 3
    # UNIFIED INSTRUMENT LIVENESS (2026-07-01): ONE run-start battery for the ADVISORY external instruments whose
    # SILENT death false-degrades / false-rejects — (1) the semantic-shelf EMBEDDER (dead ⇒ "no prior work" ⇒
    # re-derivation treadmill) and (2) the firewall ROUND-TRIP judge (dead ⇒ empty back-translation ⇒ the firewall
    # fail-closes every target). The round-trip judge was previously UNPROBED at run-start — the BFT campaign
    # burned theory-consolidation, THEN round-trip-false-rejected, because a dead gemini judge (same-family
    # fallback) was only discovered mid-run. Now both are probed up front + reported LOUD. Advisory (never blocks —
    # a transient quota may clear and the cross-family fallback is the resilience) but VISIBLE. Supersedes the
    # embedder-only probe. ZTARE_LEANMILL_INSTRUMENT_LIVENESS=0 skips.
    try:
        from ztare.leanmill.run_standards import run_instrument_liveness_battery
        _il = run_instrument_liveness_battery()
        _emb, _rt = (_il.get("embedder") or {}), (_il.get("roundtrip") or {})
        print(f"[notes] instrument liveness — embedder: "
              f"{'LIVE — ' + str(_emb.get('why', '')) if _emb.get('live') else 'DEAD'} · "
              f"firewall round-trip judge: {'LIVE' if _rt.get('live') else 'DEAD'}", flush=True)
        for _b in (_il.get("banners") or []):
            print(_b, flush=True)
    except Exception as _e:  # noqa: BLE001 — advisory battery; never block the run
        print(f"[notes] instrument-liveness battery skipped: {repr(_e)[:120]}", flush=True)
    notes_path = Path(argv[0])
    # RUN ATTRIBUTION: tag this run's attempts-DB rows + forecast ledger so the compounder/forecast-router can
    # SLICE by run — the DB showed run_tag=NULL for notes runs (#92 said it should feed the substrate, but the
    # notes entry never set the env), making a run unattributable. setdefault RESPECTS an explicit A/B arm
    # (ZTARE_SOLVER_RUN_TAG=<arm>); otherwise defaults to the notes stem + a per-run stamp.
    from datetime import datetime as _dt, timezone as _tz
    _os.environ.setdefault("ZTARE_SOLVER_RUN_TAG", f"notes_{notes_path.stem}_{_dt.now().strftime('%m%dT%H%M')}")
    print(f"[notes] run_tag = {_os.environ['ZTARE_SOLVER_RUN_TAG']}", flush=True)
    # RUN-SCRATCH ISOLATION (2026-07-02 RCA — the Basel `target_signature_altered` false-reject): the planner's
    # generic decomposition name `iso_lemmaN` is REUSED across EVERY campaign, and this notes entry never set
    # ZTARE_LEANMILL_RUN_SCRATCH (only a higher-level launcher did), so every notes run shared the base
    # `.solver_scratch/` — where the winner-probe readback grabbed a STALE `iso_lemma1` probe from a PRIOR
    # campaign (wholly different signature) and governance false-flagged `target_signature_altered`. Isolate each
    # run's scratch by its run_tag (the per-campaign isolation built in task #16, `probe_dir` already honors the
    # env var) so a cross-campaign generic-name collision is IMPOSSIBLE. setdefault respects an explicit override.
    _os.environ.setdefault("ZTARE_LEANMILL_RUN_SCRATCH", _os.environ["ZTARE_SOLVER_RUN_TAG"])
    print(f"[notes] run-scratch isolated → .solver_scratch/{_os.environ['ZTARE_LEANMILL_RUN_SCRATCH']}/", flush=True)
    _since = _dt.now(_tz.utc).isoformat()   # cert-ledger watermark (same format solve_adhoc stamps `ts` with)
    _notes_text = notes_path.read_text(encoding="utf-8")
    # CAMPAIGN DOMAIN STAMP (factory time-to-closure segmentation): label this run math vs non-math formalization
    # so the cycle-time read model can report avg-time-to-closure per domain. Source: `## Domain` in the blueprint,
    # else ZTARE_SOLVER_DOMAIN, else 'unspecified'. ONE canonical emitter (phase_timing.record_campaign); the stamp
    # is best-effort telemetry and NEVER blocks the campaign.
    try:
        from ztare.leanmill.phase_timing import record_campaign as _record_campaign
        _domain = (parse_domain(_notes_text) or _os.environ.get("ZTARE_SOLVER_DOMAIN", "") or "unspecified").strip()
        _record_campaign(_domain, run_tag=_os.environ.get("ZTARE_SOLVER_RUN_TAG", ""),
                         target=(parse_notes(_notes_text)[0] or "")[:80])
        print(f"[notes] campaign domain = {_domain!r} (time-to-closure segmentation)", flush=True)
    except Exception:  # noqa: BLE001 — telemetry stamp never blocks the campaign
        pass
    # PHASE 0 — THEORY CONSOLIDATION (#123, theory-first campaigns): when the notes declare a campaign
    # theory file, the agent EXTENDS it (defs + sorried API statements — the substrate Mathlib lacks;
    # serves the BUILDS-not-lookup invariant) behind the append-only + compile gates; each new sorried
    # API statement becomes a first-class lemma work item; the file's content rides the notes so every
    # downstream formalize/solve sees the campaign substrate. Receipt → the work-items ledger.
    _theory_rel = parse_theory_file(_notes_text)
    _manifest_path = _write_run_manifest(notes_path, theory_rel=_theory_rel or "")
    if _manifest_path is not None:
        print(f"[notes] run manifest → {_manifest_path.relative_to(LEAN_ROOT_DEFAULT)}", flush=True)
    if _theory_rel:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch as _dd0
        import time as _tmc
        # AUTO-SKIP consolidation on a RERUN (2026-07-01): rebuilding a theory that ALREADY exists (>= 3 decls) is
        # the ~225s wall the operator flagged as waste — the theory is banked and ridden into the target attack
        # regardless. A FRESH blueprint has no substrate, so it still builds. The old behaviour needed the opt-in
        # ZTARE_LEANMILL_SKIP_CONSOLIDATION=1 (kept, still forces the skip); this makes the reuse-if-built the
        # DEFAULT. Re-extend a MODIFIED blueprint with ZTARE_LEANMILL_FORCE_CONSOLIDATION=1.
        _tp_pre = (LEAN_ROOT_DEFAULT / _theory_rel)
        _theory_built = False
        try:
            if _tp_pre.exists():
                from ztare.leanmill.lean_source import decl_blocks as _db_pre
                _theory_built = sum(1 for _n, _ in _db_pre(_tp_pre.read_text(encoding="utf-8", errors="replace")) if _n) >= 3
        except Exception:  # noqa: BLE001
            _theory_built = False
        _auto_skip = _theory_built and _os.environ.get("ZTARE_LEANMILL_FORCE_CONSOLIDATION") != "1"
        _skip = (_os.environ.get("ZTARE_LEANMILL_SKIP_CONSOLIDATION") == "1") or _auto_skip
        _consol_t0 = _tmc.time()
        if _skip:
            _why = "auto: built theory reused" if _auto_skip else "fast-debug flag"
            _tc = {"ok": True, "new_decls": [], "sorried_statements": [], "reason": f"skipped ({_why})"}
            print(f"[notes] theory consolidation SKIPPED ({_why}) — reusing existing substrate "
                  f"(re-extend a modified blueprint via ZTARE_LEANMILL_FORCE_CONSOLIDATION=1)", flush=True)
        else:
            _tc = theory_consolidation(_notes_text, _theory_rel, lean_root=LEAN_ROOT_DEFAULT, dispatch=_dd0)
        try:   # PHASE VISIBILITY (2026-07-01): record the consolidation wall so P0 can split time_to_formalize
               # into consolidate + statement-formalize — consolidation is the dominant, now-skippable rerun cost.
            from ztare.leanmill.phase_timing import record_phase as _rp_c
            _rp_c("consolidate", round(_tmc.time() - _consol_t0, 2),
                  run_tag=_os.environ.get("ZTARE_SOLVER_RUN_TAG", ""), target=_theory_rel,
                  extra={"skipped": bool(_skip)})
        except Exception:  # noqa: BLE001 — timing telemetry never blocks the run
            pass
        print(f"[notes] theory consolidation: ok={_tc.get('ok')} new_decls={_tc.get('new_decls', [])} "
              f"sorried={len(_tc.get('sorried_statements', []))} {_tc.get('reason', '')}", flush=True)
        for _sr in _tc.get("supersession_requests", []):
            print(f"[notes] SUPERSESSION REQUESTED (queued for governed revision): "
                  f"{_sr['name']} — {_sr['why']}", flush=True)
        try:   # typed receipt — machine-consumed first (ledger), dashboard-rendered second
            from ztare.leanmill.contracts.work_items import WorkItem, WorkReceipt
            WorkReceipt(
                item=WorkItem(kind="theory_extension", statement=_theory_rel,
                              residual_class="library_gap",
                              consumer_check="campaign lemmas must cite these decls (stamped on use)",
                              campaign=_os.environ.get("ZTARE_SOLVER_RUN_TAG", "")),
                verdict=("completed" if _tc.get("ok") and not _tc.get("unchanged") else
                         "gap" if _tc.get("ok") else "rejected"),
                formal_leg={k: _tc.get(k) for k in ("ok", "reverted", "reason", "new_decls",
                                                     "supersession_requests") if k in _tc},
                ts=_since).append_to_ledger(REPO)
        except Exception as _e:  # noqa: BLE001 — receipt write never blocks the run
            print(f"[notes] work-receipt write failed: {repr(_e)[:100]}", flush=True)
        # UNCONDITIONAL pre-SOLVE supersession heal + substrate register (v5 RCA 2026-07-01): the theory file +
        # banked legs exist whether or not THIS round's consolidation EXTENDED it — a revert (e.g. the accumulated
        # banked-section append-only violation) or an unchanged round still carries prior banked work. The
        # in-consolidation heal only fired on a SUCCESSFUL extension, so a reverted consolidation left the
        # sorried-sibling twins in place and the composite re-blocked. Fold the twins + register the warm substrate
        # here REGARDLESS of `_tc.ok`. Guarded: reverify-compile + revert on break (never poison). Idempotent.
        _tp_u = (LEAN_ROOT_DEFAULT / _theory_rel)
        if _tp_u.exists():
            if _os.environ.get("ZTARE_LEANMILL_SUPERSEDE_TWINS", "1") != "0":
                try:
                    from ztare.leanmill.lean_source import supersede_sorried_twins as _sst2
                    from ztare.gates.v33_preflight_risk_detector import _compile_probe as _cp2
                    from ztare.common.timeouts import timeout_s as _ts2
                    _cur = _tp_u.read_text(encoding="utf-8")
                    _healed2, _rep2 = _sst2(_cur)
                    if _rep2 and _healed2 != _cur:
                        _tp_u.write_text(_healed2, encoding="utf-8")
                        if _cp2(_healed2, LEAN_ROOT_DEFAULT, "SupersedeHealUncond", _ts2("cold_compile")) is True:
                            print(f"[notes] SUPERSEDED {len(_rep2)} sorried-canonical(s) pre-SOLVE: "
                                  f"{[c for c, _ in _rep2][:6]}", flush=True)
                        else:
                            _tp_u.write_text(_cur, encoding="utf-8")   # REVERT — never poison the substrate
                except Exception as _e:  # noqa: BLE001 — heal is best-effort
                    print(f"[notes] pre-SOLVE supersession heal skipped: {repr(_e)[:100]}", flush=True)
            try:
                from ztare.formal.repl_compile import set_campaign_substrate as _scs
                _scs(str(_tp_u.resolve()))
            except Exception:  # noqa: BLE001 — registration best-effort; verify falls back to inline
                pass
        if _tc.get("ok"):
            _tp = (LEAN_ROOT_DEFAULT / _theory_rel)
            # WARM-ENV REGISTER (2026-06-14): the verify seam amortizes this heavy theory's decls into a warm
            # REPL env (elaborated ONCE, re-opened on mtime change) instead of re-inlining + re-elaborating them
            # PER probe — the v7 verify-starvation fix (592-1016s timeouts → ~0.04s/probe). Soundness unchanged:
            # the warm verify still runs the #print-axioms audit against that env.
            if _tp.exists():
                try:
                    from ztare.formal.repl_compile import set_campaign_substrate
                    set_campaign_substrate(str(_tp.resolve()))
                    print(f"[notes] campaign warm-env substrate registered: {_tp}", flush=True)
                except Exception as _e:  # noqa: BLE001 — registration is best-effort; verify falls back to inline
                    print(f"[notes] warm-env register skipped: {repr(_e)[:100]}", flush=True)
                # SUBSTRATE POSITIVE CONTROL (2026-06-25 RCA — the AMM `not_riskFreeProfit_zero` `<;>` bug): a
                # single non-compiling decl ANYWHERE in the registered substrate makes `campaign_file_env` return
                # None, which SILENTLY kills the whole campaign-aware layer (citing / warm-verify / the
                # faithfulness oracle → faithful ∀-fronted proofs FALSE-REJECT as `target_signature_altered`).
                # The substrate can be written by an ungated path (recovery / manual edit) that skips
                # theory_consolidation's GATE-2 whole-file compile, so the ONLY robust catch is a run-start
                # positive control on the ACTUAL file the campaign will use — the same fail-closed-LOUD discipline
                # as the embedder-liveness banner. ZTARE_LEANMILL_SUBSTRATE_LIVENESS=0 skips (A/B).
                if _os.environ.get("ZTARE_LEANMILL_SUBSTRATE_LIVENESS", "1") != "0" and _tp.exists():
                    try:
                        from ztare.formal.repl_compile import campaign_file_env as _cfe
                        _env_id = _cfe(str(_tp.resolve()), LEAN_ROOT_DEFAULT)   # logs the compile errors LOUDLY if it fails
                        if _env_id is not None:
                            print(f"[notes] campaign substrate positive control: LIVE — env elaborates "
                                  f"(env={_env_id}); citing/warm-verify/faithfulness-oracle armed", flush=True)
                        else:
                            print("⚠️  [notes] campaign substrate positive control: DEAD — the registered substrate "
                                  "does NOT compile (errors above). The campaign-aware layer will degrade and "
                                  "faithful proofs may FALSE-REJECT. FIX THE SUBSTRATE before trusting gaps as 'hard "
                                  "math'. (A non-compiling substrate is INADMISSIBLE — never silently re-derive.)",
                                  flush=True)
                    except Exception as _e:  # noqa: BLE001 — the control is advisory; never break the run
                        print(f"[notes] substrate positive control skipped: {repr(_e)[:100]}", flush=True)
                # WARM-LEAN POSITIVE CONTROL (2026-07-03 RCA — the cold-compile STARVATION): start + ADVERTISE the
                # warm Lean checker ONCE at run start so EVERY leaf/planner dispatch inherits a LIVE socket (~0.1s
                # checks) instead of each lazily starting it (or silently getting None → cold `lake env lean`
                # 30-90s/iter → a frontier leaf burns its whole budget on ONE compile and sorries — recovered from
                # the CoT). Same LOUD fail-closed discipline as the substrate control above; the door logs LIVE/DOWN
                # + sets the socket, and each dispatch re-calls it (self-heals a reaped mid-run server).
                if _os.environ.get("ZTARE_LEANMILL_LEAN_WARM", "1") != "0":
                    try:
                        from ztare.formal.lean_check_server import ensure_server_advertised as _esa
                        _esa(str(LEAN_ROOT_DEFAULT), context="run start")
                    except Exception as _e:  # noqa: BLE001 — warm-lean is an optimization; never break the run
                        print(f"[notes] warm-lean positive control skipped: {repr(_e)[:100]}", flush=True)
            _theory_src = _tp.read_text(encoding="utf-8") if _tp.exists() else ""
            if _theory_src.strip():   # the substrate rides the notes (formal scaffolding channel, #88)
                _notes_text += ("\n\n## Theory (campaign substrate — cite, do not re-derive)\n```lean\n"
                                + _theory_src + "\n```\n")
            # (2026-06-23: the advisory `_supersession_steer` formalize-time nudge was REMOVED here — empirically
            # it didn't bind the formalizer against the literal NL, and it is SUBSUMED by the self-correction LOOP:
            # solve_adhoc now kernel-falsifies a stalled target → `autoformalize_and_solve`'s reformulation re-entry
            # has the agent STRENGTHEN + re-attack. One surface (the loop), not two — no parallel steer to drift.)
            # ROBUST work-item queueing (RCA 2026-06-18): the agent's own sorried API lemmas become solver
            # work items, foundational-first, via the canonical `_insert_lemmas_section` (creates `## Lemmas`
            # if absent). A theory-first blueprint with no `## Lemmas` anchor previously DROPPED them — the
            # theory got built but its crux lemmas were never attacked. These are ALREADY formal Lean (no NL
            # round-trip), so attacking them sidesteps the target's formalization firewall entirely.
            _sorried = list(_tc.get("sorried_statements", []))
            # COMPLETE THE OPEN-SET FROM THE SUBSTRATE (Goldilocks: report the kernel FACT of what's open; do not
            # rely on a consolidation-round diff). 2026-07-05 restOrder_preserves ORPHAN fix + operator "why
            # targeting logic at all / are we goldilocks": consolidation extracts work-items only from decls IT
            # changed and EARLY-RETURNS 'unchanged' on a stable rerun — so a leaf a PRIOR run left sorried was
            # never re-queued (the engine ground the TOP, which cites it, forever). Here — regardless of
            # consolidation outcome — re-queue EVERY substrate decl whose OWN proof body still carries a literal
            # `sorry` (the true open leaf; comment-`sorry` can't fool split_at_proof+strip_comments). Deduped by
            # clean statement. The agent still chooses HOW to prove each; this only surfaces the complete open set.
            try:
                from ztare.leanmill.solver.statement_integrity import decl_blocks as _dbk
                from ztare.leanmill.lean_source import (strip_comments as _sc2, has_sorry as _hs2,
                                                        split_at_proof as _sap2)
                _seen = {" ".join(s.split()) for s in _sorried}
                for _n, _blk in _dbk(_theory_src):
                    if _n and _hs2(_sap2(_sc2(_blk))[1]):       # OWN proof body still carries a literal sorry ⇒ OPEN
                        _stmt = " ".join(_sc2(_blk).split())
                        if _stmt not in _seen:
                            _sorried.append(_stmt); _seen.add(_stmt)
                            print(f"[notes] re-queued ORPHANED open substrate leaf: {_n}", flush=True)
            except Exception as _e:  # noqa: BLE001 — completeness is best-effort; never break the run
                print(f"[notes] open-leaf re-queue skipped: {repr(_e)[:100]}", flush=True)
            if _sorried:
                _notes_text = _insert_lemmas_section(_notes_text, _sorried)
    res = autoformalize_from_notes(_notes_text, notes_path=notes_path)  # notes_path ⇒ incremental write-back (timeout-safe)
    res["instrument_standards"] = _std   # traceability: this run's closures carry their instrument certificate
    # v3 RCA: surface kernel closures from the WHOLE recursion tree (the cert ledger), not just the
    # top-level lemma outcomes — depth≥2 rungs were silently lost to the compounding loop.
    res["deep_closures"] = deep_closures_since(_since)
    if res["deep_closures"]:
        print(f"[notes] deep rungs kernel-closed this run: "
              + ", ".join(str(d.get('target')) for d in res['deep_closures']), flush=True)
    # COMPOUNDING-HEALTH EPILOGUE — surface the AMNESIA metric every run via the CANONICAL telemetry
    # (`scripts/public/control/leanmill/compounding_curve.py`, the task-#110 producer; reporting lives in
    # scripts/ per the scripts-vs-src rule). A closure of an already-certified rung is a re-derivation; with the
    # incremental library banking at the cert-write chokepoint (`family_lemma_library` → campaign env) this should
    # trend → 0. Advisory; never gates. ZTARE_LEANMILL_COMPOUNDING_HEALTH=0 reverts. (Banking itself is NOT here
    # anymore — it is per-closure at the kernel-ratify site so a run that dies before this epilogue still compounds.)
    if _os.environ.get("ZTARE_LEANMILL_COMPOUNDING_HEALTH", "1") != "0":
        try:
            import importlib.util as _ilu
            _cc_path = REPO / "scripts/public/control/leanmill/compounding_curve.py"
            _spec = _ilu.spec_from_file_location("compounding_curve", _cc_path)
            _cc = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_cc)
            _rep = _cc.report(REPO)
            res["rederivation"] = _rep.get("rederivation")
            res["reuse"] = _rep.get("reuse")
            res["recent"] = _rep.get("recent")
            _rr = _rep.get("rederivation") or {}
            _rc = _rep.get("recent") or {}
            _ru = _rep.get("reuse") or {}
            # HEADLINE = the CLEAN-REGIME window (forward-looking, since `clean_since`; the all-time rate is a
            # cumulative ghost — this session's fixed-bug noise + test probes dominate it, so it tracks history,
            # not the engine running now). Accrues as clean runs land.
            _cn = _rc.get("clean_closures")
            print(f"[compounding-health] CLEAN (since {_rc.get('clean_since')}, {_cn} closures): "
                  f"re-derivation={_rc.get('rederivation_rate')} ({_rc.get('rederived')}/{_cn}), "
                  f"proof-reuse={_rc.get('proof_reuse_rate')} ({_rc.get('proofs_citing_a_banked_lemma')}/{_cn}); "
                  "→ re-derivation 0 / reuse 1 is healthy", flush=True)
            print(f"[compounding-health] all-time (context, NOT the live engine): "
                  f"re-derivation={_rr.get('rederivation_rate')} ({_rr.get('rederived')}/{_rr.get('closures')}), "
                  f"lemma-reuse={_ru.get('lemma_reuse_rate')} ({_ru.get('lemmas_reused')}/{_ru.get('banked_lemmas')}); "
                  "name-match lower bound", flush=True)
            _co = _rep.get("cost") or {}
            # INFER-VIA-USE (no paid A/B): bank-served closures (direct attribution) + does closing get CHEAPER as
            # the corpus grows (median wall_s early→recent). Observational/confounded — a trend to watch, not a causal claim.
            print(f"[compounding-health] infer-via-use: bank-served={_co.get('bank_served_rate')} "
                  f"({_co.get('bank_served_closures')}/{_co.get('closed')} closures cited a banked rung instead of re-deriving); "
                  f"median wall_s early→recent = {_co.get('median_wall_s_early')}→{_co.get('median_wall_s_recent')} "
                  "(↓ = closing cheaper as the bank grows; confounded by difficulty mix)", flush=True)
        except Exception as _e:  # noqa: BLE001 — telemetry only; never blocks the run
            print(f"[notes] compounding-health skipped: {repr(_e)[:120]}", flush=True)
    # TRAINING-CORPUS EXPORT (the expert-iteration flywheel tap, 2026-06-24): refresh the kernel-verified training
    # corpus (prover (stmt,proof) + autoformalization NL↔Lean + falsification) from the run's closures so the
    # inference→pretrain bridge stays current — our defensible "void" data that no public corpus has. Forward-
    # looking (clean-regime) by default; best-effort, never blocks. ZTARE_LEANMILL_EXPORT_TRAINING_CORPUS=0 skips.
    if _os.environ.get("ZTARE_LEANMILL_EXPORT_TRAINING_CORPUS", "1") != "0":
        try:
            import importlib.util as _ilu2
            _ec = REPO / "scripts/public/control/leanmill/export_training_corpus.py"
            _sp = _ilu2.spec_from_file_location("export_training_corpus", _ec)
            _m = _ilu2.module_from_spec(_sp); _sp.loader.exec_module(_m)
            _man = _m.export(REPO)
            res["training_corpus"] = _man
            print(f"[training-corpus] refreshed: {_man.get('prover_pairs')} prover "
                  f"({_man.get('prover_void_novel')} void-novel) + {_man.get('autoformalization_pairs')} NL↔Lean "
                  f"+ {_man.get('falsification_pairs')} falsification (clean since {_man.get('clean_since')})", flush=True)
        except Exception as _e:  # noqa: BLE001 — flywheel tap is best-effort; never blocks the run
            print(f"[notes] training-corpus export skipped: {repr(_e)[:120]}", flush=True)
    _modeling_faithfulness_audit(
        res, _theory_rel, LEAN_ROOT_DEFAULT, log=lambda m: print(m, flush=True))
    # TRUST-CONSERVATION EPILOGUE (v3 RCA): the layers must AGREE — every ratified DB win has a verified,
    # recompilable cert. Read-only, seconds, fail-LOUD (the v3 disease was exactly a silent disagreement
    # between these layers that no layer-local selftest could see).
    try:
        from ztare.leanmill.run_standards import trust_conservation_audit
        _tc = trust_conservation_audit(_since, run_tag=_os.environ.get("ZTARE_SOLVER_RUN_TAG", ""))
        res["trust_conservation"] = _tc
        if _tc.get("ok"):
            print(f"[notes] trust-conservation: OK {_tc.get('counts')}", flush=True)
        else:
            print("[notes] *** TRUST-CONSERVATION VIOLATION ***", flush=True)
            for _v in _tc.get("violations", []):
                print(f"[notes]   {_v}", flush=True)
    except Exception as _e:  # noqa: BLE001 — the audit must never mask the run result itself
        res["trust_conservation"] = {"ok": None, "error": repr(_e)[:120]}
    artifact = notes_path.with_suffix(".autoformalize_result.json")
    artifact.write_text(json.dumps(res, indent=2, default=str))
    from ztare.leanmill.solver.agentic_leaf import default_dispatch  # the WARM AGENT authors the synthesis
    refined = write_refined_notes(res, notes_path, dispatch=default_dispatch)  # apparatus updates its OWN notes
    compounded = compound_into_original_notes(res, notes_path)  # #97: planner's decomposition → ORIGINAL notes (gated)
    print(f"\n[notes] {res['summary']}")
    print(f"[notes] artifact: {artifact}")
    print(f"[notes] refined blueprint (apparatus-updated, compounds next run): {refined}")
    if compounded:
        print(f"[notes] ORIGINAL notes compounded with the planner's decomposition: {compounded}")
    regenerate_dashboard(REPO)   # #119: every run ends with fresh dashboard artifacts (best-effort)
    return 0


if __name__ == "__main__":
    sys.exit(main())
