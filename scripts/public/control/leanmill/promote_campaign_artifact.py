#!/usr/bin/env python3
"""Promote a machine-checked campaign closure to a filed .lean artifact WITH a per-campaign "factory cert" header.

The proof body is the VERBATIM machine closure (copied from `closures/<target>.lean`, never hand-authored). The
header is GENERATED metadata — the campaign's P0 economics so the artifact is self-documenting: outcome+axioms,
time-to-closure, compute-to-closure, the phase decomposition (where the wall went), yield, reuse (cited banked
rungs), the decomposition bill-of-materials, moves, domain+generality. Sources are the SAME durable read-models
factory_intelligence uses (phase_timing.summarize_campaign_cycle_time / summarize_phase_timings + the attempts
DB), plus #print axioms from a compile. Reusable for ANY campaign closure, not this one specifically.

  PYTHONPATH=src python scripts/.../promote_campaign_artifact.py \
      --run-tag <rt> --target <closure_name> \
      --dest ztare_proofs/leanmill-formalizations/strategy/<file>.lean [--log <run.log>]

  CANONICAL dest = ztare_proofs/leanmill-formalizations/{strategy,finance}/ (the curated, GitHub-public
  formalizations home, alongside leanmill-formalizations/blueprints/). NOT ztare_proofs/ZtareProofs/strategy/
  (a stale auto-default). The local repo is master; the VPS is a mirror — file artifacts into the LOCAL repo.
"""
from __future__ import annotations

import argparse
import sqlite3
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

from ztare.leanmill.phase_timing import summarize_campaign_cycle_time, summarize_phase_timings  # noqa: E402

ATTEMPTS = REPO / "analytics" / "public" / "queries" / "solver_lane_attempts.db"
CLOSURES = REPO / "ztare_proofs" / ".solver_scratch" / "closures"
LEAN_ROOT = REPO / "ztare_proofs"


def _run_closures(run_tag: str) -> Path:
    """The closure cert dir for a run — the run-scratch-ISOLATED `.solver_scratch/<run_tag>/closures` (what
    `agentic_leaf.probe_dir` writes under `ZTARE_LEANMILL_RUN_SCRATCH`, every `leanmill campaign`) if it exists,
    else the legacy non-isolated `CLOSURES`. The bare `CLOSURES` constant predates run-scratch isolation
    (2026-07-02), so promote raised `body not found` on every isolated close (corpgov, 2026-07-03) — the reader
    side of the same split-brain the P0-sidecar + auto-promote had. Isolated-first + legacy-fallback covers both."""
    iso = REPO / "ztare_proofs" / ".solver_scratch" / (run_tag or "") / "closures"
    return iso if (run_tag and iso.exists()) else CLOSURES


def _attempt_rows(run_tag: str) -> "list[dict]":
    if not ATTEMPTS.exists():
        return []
    cx = sqlite3.connect(f"file:{ATTEMPTS}?mode=ro", uri=True)
    try:
        cols = ("run_tag", "attempt_at", "outcome", "ratified", "wallclock_s", "move", "provider")
        return [dict(zip(cols, r)) for r in cx.execute(
            f"SELECT {','.join(cols)} FROM attempts WHERE run_tag=?", (run_tag,)).fetchall()]
    finally:
        cx.close()


def _laundering_markers(body: str) -> "list[str]":
    """PUBLISH-BOUNDARY GUARD (2026-06-30 RCA). A filed `closed · faithful` artifact must be the SELF-CONTAINED
    real proof: no `sorry`, and no local `axiom` DECLARATIONS. A local `axiom` decl is the tell of the PROBE-WORLD
    standalone — the solver stubs cited banked rungs as `axiom`s so the single theorem recompiles in isolation.
    Publishing THAT with a clean-axioms header is the laundering-looking disconnect Gemini flagged on VCG (the
    first COMPOSITE campaign filed): the real substrate proof is axiom-clean — those stubs are proven theorems
    there — but the standalone stubs them, so `#print axioms` on the filed FILE shows the stubs and contradicts
    the header. Refuse to file when these appear so the disconnect can never ship; file the substrate instead.
    Uses the canonical `lean_source` comment-aware scanners (a `sorry`/`axiom` inside a comment is not a hit)."""
    from ztare.leanmill import lean_source as _ls
    markers: "list[str]" = []
    if _ls.has_sorry(body):
        markers.append("body contains `sorry` (a closed·faithful artifact must be sorry-free)")
    code = _ls.blank_comments(body)             # comment-blanked, offsets preserved → honest line scan
    _re = __import__("re")
    for i, ln in enumerate(code.splitlines(), 1):
        if _re.match(r"\s*axiom\s+\w", ln):
            markers.append(f"L{i}: local `axiom` declaration (probe-world stub) — {body.splitlines()[i-1].strip()[:70]}")
        # PROOF-SEARCH TACTIC (2026-07-03, the bayes-screening auto-promote gap): `exact?`/`apply?` is a SEARCH,
        # not a finished proof — it resolves against the banked lemmas in the WARM campaign env but leaves `sorryAx`
        # when the artifact is compiled standalone (and is Mathlib-version-fragile). It is not a literal `sorry`, so
        # the sorry-scan above misses it; a probe cert closed with `<;> exact?` sailed through. File the
        # self-contained SUBSTRATE (which has the cited lemmas), or replace the search with the named cites first.
        if _re.search(r"\b(exact\?|apply\?)", ln):
            markers.append(f"L{i}: proof-search tactic (`exact?`/`apply?`) — resolves in the warm env, not standalone; "
                           f"file the substrate or name the cites — {body.splitlines()[i-1].strip()[:60]}")
    return markers


def _strip_internal_advisories(body: str) -> "tuple[str, int]":
    """Drop the apparatus's OWN internal advisory comments that the solver prepends to a probe — the
    `-- 📊 LEARNED move track-record` block (per-move kernel close-rates, dead-move hints). These STEER THE SEARCH;
    they are not part of the published proof and leak apparatus internals (close-rates, dead moves) into a public
    artifact (2026-07-03 release-hygiene). Remove the 📊 header line + the contiguous `--   <move>: N/M closed (P%)`
    rate lines under it, then collapse the blank run the removal leaves. Returns (cleaned_body, n_lines_removed)."""
    import re as _re
    lines = body.splitlines()
    out, removed, i = [], 0, 0
    _rate = _re.compile(r"^\s*--\s+\S.*\bclosed\s*\(\d+%\)\s*$")
    while i < len(lines):
        if "📊" in lines[i] and "track-record" in lines[i]:
            removed += 1
            i += 1
            while i < len(lines) and _rate.match(lines[i]):
                removed += 1
                i += 1
            continue
        out.append(lines[i])
        i += 1
    cleaned = _re.sub(r"\n{3,}", "\n\n", "\n".join(out))
    return (cleaned + ("\n" if body.endswith("\n") and not cleaned.endswith("\n") else "")), removed


def _insert_blueprint_pointer(body: str, blueprint: str) -> str:
    """Insert a pointer to the natural-language blueprint (the English SPECIFICATION this theorem was formalized
    from) right after `import Mathlib`, so a reader finds the spec next to the proof and can check the faithfulness
    boundary — the guarantee stops where the English intent is argued, not proved (2026-07-03 release-hygiene).
    `blueprint` is the basename (e.g. `basel_leverage_ratio_blueprint.md`); no-op if empty, already present, or no
    `import Mathlib` anchor."""
    if not blueprint or "Natural-language specification (blueprint)" in body or "import Mathlib\n" not in body:
        return body
    ptr = (f"\n-- Natural-language specification (blueprint): blueprints/{blueprint}\n"
           f"-- Read the blueprint to check the faithfulness boundary — the guarantee stops where the English "
           f"intent is argued, not proved.\n")
    return body.replace("import Mathlib\n", "import Mathlib\n" + ptr, 1)


def _clean_public_names(body: str) -> "tuple[str, dict, list]":
    """Strip content-stable banking hashes (`Foo__c64ef761` → `Foo`) from the filed artifact's decl names.

    WHY: promote files the persisted banked substrate verbatim, and a COMPOSITE/conjunctive campaign banks its
    generic planner nodes under content-stable `__<hash>` names (§4.5). Those internal names then leak into the
    public `.lean` (and mismatch the paper's clean citations, e.g. BFT `..._witness__c64ef761`). This is purely
    cosmetic — the proofs are axiom-clean — but a public library should read like Mathlib, not like machine spew.

    NON-IATROGENIC by construction: a *consistent* alpha-rename of a decl and every reference to it (decl head,
    proof cites, `#print axioms` line) is definitionally identical — the kernel accepts the renamed file iff it
    accepted the original. We only rename when the clean base name does NOT collide with an existing decl (so
    Shamir's `_conjN__hash` banked proofs, which sit alongside clean `_conjN` wrappers, are left untouched — a
    collision is reported, never force-merged). The hashed name is a globally-unique token, so the whole-body
    replace can't clip a substring. Re-verify (compile + `#print axioms`) still gates the filed artifact."""
    import re
    # decl names via the CANONICAL parser (§4.3c single door — lean_source.DECL_START handles the
    # private/protected/noncomputable/@[attr] prefixes a hand-rolled keyword regex silently misses; a
    # missed decl here would skip its rename AND, worse, miss a collision → an unsound force-merge).
    from ztare.leanmill.lean_source import decl_blocks
    declared = {n for n, _ in decl_blocks(body) if n}
    hashed = sorted(n for n in declared if re.search(r"__[0-9a-f]{6,}$", n))
    renames: "dict[str, str]" = {}
    taken = set(declared)
    for n in hashed:
        base = re.sub(r"__[0-9a-f]{6,}$", "", n)
        if base in taken or base in renames.values():
            continue                                    # collision → leave hashed, report it
        renames[n] = base
        taken.add(base)
    cleaned = body
    for n, base in renames.items():                     # token-bounded consistent rename (decl + refs + #print)
        cleaned = re.sub(r"(?<![A-Za-z0-9_'.])" + re.escape(n) + r"(?![A-Za-z0-9_'.])", base, cleaned)
    residual = [n for n in hashed if n not in renames]
    return cleaned, renames, residual


def _strip_dead_banked_scaffolding(body: str, target: str) -> "tuple[str, int]":
    """Remove the `[family-lemma-library] banked` compounding sections from the PUBLIC artifact. WHY (2026-07-02,
    the Basel manual-trim the operator flagged — "we shouldn't touch files ex-post"): the banking door appends the
    warm-env library at EOF as `section  -- [family-lemma-library] banked rungs … end` blocks — GENERIC/hashed
    DUPLICATES of the consolidated clean decls (`iso_lemma1`, `iso_lemma1__<hash>`). `_clean_public_names` can't
    clean them when the clean base collides with a sibling (so both were left in), and they are internal
    compounding scaffolding for the NEXT run's citations, never publishable content. SAFE BY CONSTRUCTION: banking
    appends AFTER every real decl, so nothing the artifact publishes cites them. FAIL-CLOSED: if stripping would
    drop the TARGET decl (it lived only in a banked section — the closure-path artifact), keep the original body.
    Returns (body, n_stripped). Balanced `section … end` removal leaves no dangling `open`/`variable`/`end`."""
    import re
    from ztare.leanmill.lean_source import decl_blocks
    lines = body.splitlines(keepends=True)
    # 1) index every family section: [start, end_excl, {decl names in it}]
    sections: "list[list]" = []
    i = 0
    while i < len(lines):
        if "[family-lemma-library] banked rungs" in lines[i] and lines[i].lstrip().startswith("section"):
            j = i + 1
            while j < len(lines) and lines[j].strip() != "end":
                j += 1
            names = {nm for nm, _ in decl_blocks("".join(lines[i:j + 1])) if nm}
            sections.append([i, j + 1, names])
            i = j + 1
            continue
        i += 1
    if not sections:
        return body, 0
    # 2) the PUBLISHED (non-family) body — what the artifact actually ships
    in_sec = [False] * len(lines)
    for s, e, _ in sections:
        for k in range(s, e):
            in_sec[k] = True
    published = "".join(l for k, l in enumerate(lines) if not in_sec[k])
    # 3) KEEP a banked section iff one of its decls is REFERENCED by the published body (or a KEPT section) — a
    # UNIQUE family-banked helper the target's proof CITES (the CLOB `bidPrice_le_bestBid` / `bestAsk_le_of_mem_…`
    # regression: they lived in a banked section but the authored `restOrder_preserves_uncrossed_of_safe` cites
    # them → whole-section strip → `unknown identifier`, the artifact does NOT build). Only genuinely-UNREFERENCED
    # duplicates (`iso_lemma1__<hash>`, cited by nobody published) are dropped. Transitive via fixpoint (helper A
    # cited only by helper B which the target cites). Self-declaration never counts — a section's OWN text is not
    # in the reference corpus unless it is already kept.
    def _refd(names: "set[str]", text: str) -> bool:
        return any(re.search(r"(?<![\w.])" + re.escape(nm) + r"(?![\w'.])", text) for nm in names)
    keep = [False] * len(sections)
    changed = True
    while changed:
        changed = False
        ref_corpus = published + "".join("".join(lines[s:e]) for (s, e, _), k in zip(sections, keep) if k)
        for idx, (s, e, names) in enumerate(sections):
            if not keep[idx] and names and _refd(names, ref_corpus):
                keep[idx] = True
                changed = True
    # 4) rebuild: published lines + KEPT sections, original order
    out = []
    for k, l in enumerate(lines):
        sidx = next((idx for idx, (s, e, _) in enumerate(sections) if s <= k < e), None)
        if sidx is None or keep[sidx]:
            out.append(l)
    n = sum(1 for kp in keep if not kp)
    if not n:
        return body, 0
    stripped = "".join(out)
    if target and target not in {nm for nm, _ in decl_blocks(stripped) if nm}:
        return body, 0                                  # fail-closed: never drop the published target
    return stripped, n


def _p0_sidecar(closure: Path) -> "dict | None":
    """Honest P0 STAMPED at campaign close (autoformalize_notes) in the warm/persisted world: persisted-world
    `#print axioms` + this-run banked/reused counts. promote READS this instead of re-deriving P0 from the cold
    probe closure — which times out (→ `axioms ?`), reports probe-world stub axioms, and whose log-regex misses
    intra-run banking (→ `reuse 0`). Absent for pre-2026-06-30 runs ⇒ callers fall back to the probe compile /
    log parse. This is the single source of truth that ends the recurring P0-at-promote bug class."""
    sc = closure.parent / (closure.stem + ".p0.json")
    if not sc.exists():
        return None
    try:
        import json
        return json.loads(sc.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _axioms(closure: Path) -> str:
    """#print axioms from a compile (the closure carries the `#print axioms` command). Best-effort; '?' if the
    toolchain/compile is unavailable — never block filing on it."""
    try:
        out = subprocess.run(["lake", "env", "lean", str(closure)], cwd=str(LEAN_ROOT),
                             capture_output=True, text=True, timeout=400).stdout
        ax = []
        cap = False
        for ln in out.splitlines():
            if "depends on axioms:" in ln:
                cap = True
                ax.append(ln.split("depends on axioms:", 1)[1].strip())
                continue
            if cap:
                ax.append(ln.strip())
                if "]" in ln:
                    break
        joined = " ".join(ax).strip()
        return joined or "(none printed)"
    except Exception:  # noqa: BLE001
        return "?"


def _cited_rungs(log: "Path | None") -> "list[str]":
    """Banked rungs reused this run — the COMPOUNDING signal. DB `cache_reuse` rows undercount, so read the run
    log (NOT Lean ⇒ log-text parse, not lean_source): both the proof-level `CITED banked rung ... for '<name>'`
    cites AND the campaign-level `REUSED from bank ... theorem <name>` skips (the (b) banked-lemma reuse, which
    skips re-formalizing an already-proven decl). Counting only the former under-reported a fully-reused run as
    'cited 0' even though it stood entirely on banked work."""
    names: "list[str]" = []
    if log and log.exists():
        import re
        txt = log.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"CITED banked rung.*?for '([^']+)'", txt):
            if m.group(1) not in names:
                names.append(m.group(1))
        for m in re.finditer(r"REUSED from bank[^\n]*?:\s*theorem\s+(\w+)", txt):
            if m.group(1) not in names:
                names.append(m.group(1))
    return names


def _fmt(n) -> str:
    return "—" if n is None else f"{n:g}"


def _family_rows(run_tag: str, only: "set[str] | None" = None) -> "list[dict]":
    """Attempt rows for run_tag's campaign family (v4/v5/v6…) — the honest multi-run milestone view (a milestone
    whose lemmas were proven in one run and whose target closed in a later reuse run must NOT report only the
    cheap reuse run's time-to-closure: that UNDER-represents the real proving cost — a confound). Uses the
    canonical `campaign_family` strip. `only` (optional) restricts to specific member run_tags — used to EXCLUDE
    pre-fix / debugging runs whose wall was bug-thrash, not proving (the OTHER confound direction)."""
    from ztare.leanmill.phase_timing import campaign_family
    fam = campaign_family(run_tag)
    if not ATTEMPTS.exists():
        return []
    cx = sqlite3.connect(f"file:{ATTEMPTS}?mode=ro", uri=True)
    try:
        cols = ("run_tag", "attempt_at", "outcome", "ratified", "wallclock_s", "move", "provider")
        all_rows = [dict(zip(cols, r)) for r in cx.execute(f"SELECT {','.join(cols)} FROM attempts").fetchall()]
    finally:
        cx.close()
    return [r for r in all_rows if campaign_family(r.get("run_tag") or "") == fam
            and (only is None or (r.get("run_tag") or "") in only)]


def _family_block(run_tag: str, only: "set[str] | None" = None) -> "list[str]":
    """Render the campaign-FAMILY P0 rollup (combined wall + per-member role) so a multi-run milestone is honest:
    which run PROVED the lemmas vs which CLOSED the target vs a discarded attempt — never a single-run blob.
    `only` restricts to the genuine post-fix runs (excludes pre-fix bug-thrash)."""
    from ztare.leanmill.phase_timing import campaign_family
    fam = campaign_family(run_tag)
    camps = summarize_campaign_cycle_time(_family_rows(run_tag, only=only)).get("campaigns", {})
    members = {rt: c for rt, c in camps.items() if campaign_family(rt) == fam}
    if not members:
        return []
    # REAL ELAPSED = span, now measured launch(campaign-marker)→last-attempt (2026-07-01: the marker fix — span
    # previously started at the first solve ATTEMPT and so excluded theory-consolidation + statement-formalize,
    # under-reporting a theory-building run by minutes; the earlier wallclock→span fix was partial). `span` now
    # INCLUDES formalize; the active-solve sum is the (smaller) compute figure. Formalize/prove split is per-run.
    span = round(sum((c.get("span_s") or 0) for c in members.values()), 1)
    formalize = round(sum((c.get("time_to_formalize_s") or 0) for c in members.values()), 1)
    active = round(sum(((c.get("cost_to_closure_s") or {}).get("total_wall_s") or 0) for c in members.values()), 1)
    closed = sum(((c.get("yield") or {}).get("closed") or 0) for c in members.values())
    out = [f"  milestone   : campaign family '{fam}' — {len(members)} run(s) · REAL elapsed (launch→last) "
           f"{span:g}s (~{span/60:.0f} min) = formalize {formalize:g}s + prove/other · active-solve {active:g}s · "
           f"{closed} closures [launch→last is the honest wall]"]
    for rt, c in sorted(members.items()):
        sp = c.get("span_s") or 0
        out.append(f"     - {rt}: {((c.get('yield') or {}).get('closed') or 0)}/{c.get('attempts', 0)} closed · "
                   f"elapsed {sp:g}s (~{sp/60:.1f} min)")
    return out


def build_header(run_tag: str, target: str, closure: Path, log: "Path | None", axioms: str = "", domain: str = "",
                 family: bool = False, family_runs: "set[str] | None" = None) -> str:
    rows = _attempt_rows(run_tag)
    cct = summarize_campaign_cycle_time(rows).get("campaigns", {}).get(run_tag, {})
    ph = summarize_phase_timings(run_tag=run_tag)
    phases = {k: round(v.get("total_s", 0.0), 1) for k, v in ph.get("phases", {}).items() if k != "campaign"}
    lead = (ph.get("runs", {}).get(run_tag, {}) or {}).get("lead_time_s")
    moves = Counter(r["move"] for r in rows if r.get("move"))
    tclose = cct.get("time_to_close_s", cct.get("time_to_closure_s", {})) or {}   # PROVING window (first attempt → closure)
    wall = cct.get("wall_s", {}) or {}                                            # launch → closure (marker-based, when a marker exists)
    tform = cct.get("time_to_formalize_s")                                        # launch → first attempt (marker-based)
    # HEADLINE wall = the phase-ledger `lead` (last−first phase event) — available for EVERY run (marker or not),
    # so formalize = wall − prove is honest even for pre-marker campaigns; fall back to the marker-based wall.
    _prove_m = tclose.get("mean")
    _wall_m = lead if lead is not None else wall.get("mean")
    _form_m = (round(_wall_m - _prove_m, 2) if (_wall_m is not None and _prove_m is not None) else tform)
    ctc = cct.get("cost_to_closure_s", {}) or {}
    yld = cct.get("yield", {}) or {}
    # sidecar: next to the closure (fresh promote) OR keyed on TARGET in CLOSURES (so --from-file backfills read it)
    p0 = _p0_sidecar(closure) or _p0_sidecar(_run_closures(run_tag) / f"{target}.lean")
    # axioms + reuse: prefer the close-time stamp (honest persisted world); fall back to probe compile / log.
    ax_str = axioms.strip() or (p0 or {}).get("axioms") or _axioms(closure)
    if p0:
        reuse_str = (f"{p0.get('banked_this_run', 0)} rung(s) banked this run · "
                     f"{p0.get('reused_from_bank', 0)} reused from prior bank")
    else:
        cited = _cited_rungs(log)
        reuse_str = f"cited {len(cited)} banked rung(s)" + (f" — {', '.join(cited)}" if cited else "")
    ph_str = " · ".join(f"{v:g}s {k}" for k, v in sorted(phases.items(), key=lambda kv: -kv[1])) or "—"
    mv_str = " · ".join(f"{m}×{c}" for m, c in moves.most_common()) or "—"
    L = [
        "/-",
        f"LeanMill campaign provenance — {target}",
        "The theorem(s) below are the VERBATIM machine-checked closure. This header is GENERATED from run",
        f"telemetry (run_tag={run_tag}) by promote_campaign_artifact.py — not hand-authored.",
        "",
        f"  outcome     : closed · faithful · axioms {ax_str}",
        f"  domain      : {domain.strip() or cct.get('domain', 'unspecified')}",
        f"  time        : wall {_fmt(_wall_m)}s launch→close = formalize {_fmt(_form_m)}s "
        f"(theory+statement+firewall) + prove {_fmt(tclose.get('mean'))}s (proof search) · "
        f"prove p50 {_fmt(tclose.get('p50'))}s p95 {_fmt(tclose.get('p95'))}s",
        f"  compute     : cost-to-closure {_fmt(ctc.get('mean'))}s mean · {_fmt(ctc.get('total_wall_s'))}s total",
        f"  yield       : {yld.get('closed', 0)}/{cct.get('attempts', 0)} attempts closed "
        f"({yld.get('failed', 0)} failed)",
        f"  phases      : {ph_str}",
        f"  reuse       : {reuse_str}",
        f"  moves       : {mv_str}",
    ]
    if family:
        L.extend(_family_block(run_tag, only=family_runs))
    L.extend(["-/", ""])
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-tag", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--dest", default="", help="output path; defaults to --from-file (in-place backfill)")
    ap.add_argument("--log", default="")
    ap.add_argument("--axioms", default="", help="pre-verified #print axioms (skips a recompile; e.g. on a memory-tight box)")
    ap.add_argument("--domain", default="", help="override the domain label (old runs predate the ## Domain stamp)")
    ap.add_argument("--from-file", default="", help="backfill an EXISTING filed .lean (prepend the header in place) instead of reading closures/")
    ap.add_argument("--blueprint", default="", help="basename of the natural-language blueprint (blueprints/<name>.md) this was formalized from; emitted as a pointer after import Mathlib so the English spec sits next to the proof")
    # DEFAULT-ON (2026-07-02): the family rollup is the HONEST wall for a target proven across runs (a milestone
    # built in one run, target-closed in a later reuse run) — median-voter's single-run header read 465s while the
    # family (substrate-build + close) was ~86 min. Making it opt-IN silently UNDER-counts every auto/hand promote;
    # a single-run campaign just renders one member (harmless). `--no-family` restores the single-run view.
    ap.add_argument("--family", dest="family", action="store_true", default=True,
                    help="render the campaign-FAMILY rollup (combined wall + per-run roles) — DEFAULT-ON (the honest "
                         "P0 for a milestone proven in one run and target-closed in a later reuse run)")
    ap.add_argument("--no-family", dest="family", action="store_false",
                    help="opt OUT of the family rollup — render only this run_tag's single-run view")
    ap.add_argument("--family-runs", default="",
                    help="comma-separated member run_tags to RESTRICT the family rollup to (exclude pre-fix / "
                         "debugging runs whose wall was bug-thrash, not proving — keeps the P0 un-confounded)")
    ap.add_argument("--allow-nonstandard-body", action="store_true",
                    help="override the publish-boundary guard (file a body with a `sorry`/local `axiom` even so). "
                         "For a DELIBERATELY axiomatic development whose header honestly lists the axioms — NOT for "
                         "a composite whose probe standalone stubbed its cited rungs (file the substrate instead).")
    a = ap.parse_args()
    # BODY = an existing filed artifact (backfill) OR the verbatim closure (fresh promote). Either way the proof is
    # copied verbatim; only the generated header is prepended.
    body_path = Path(a.from_file) if a.from_file else (_run_closures(a.run_tag) / f"{a.target}.lean")
    if not body_path.exists():
        print(f"ERROR: body not found: {body_path}")
        return 1
    body = body_path.read_text(encoding="utf-8")
    if "LeanMill campaign provenance" in body[:1200]:
        print(f"SKIP {body_path}: already carries a provenance header (idempotent — not double-prepending)")
        return 0
    # PUBLISH-BOUNDARY NAME HYGIENE: strip content-stable banking hashes (`Foo__c64ef761` → `Foo`) so the public
    # artifact reads like a curated library, not machine output, and matches the paper's clean citations. Internal
    # banked names stay hashed by design; only the filed artifact is cleaned. Semantics-preserving consistent
    # rename (re-verify still gates). Residual = a hashed name whose clean base collides with a sibling (left as-is,
    # reported) — a quality REPORTER, never a soundness gate, so it does not block filing.
    body, _n_scaffold = _strip_dead_banked_scaffolding(body, a.target)
    if _n_scaffold:
        print(f"[publish-hygiene] stripped {_n_scaffold} `[family-lemma-library] banked` scaffolding section(s) — "
              f"internal compounding duplicates (generic/hashed names), not published content (the Basel manual-trim, now mechanical)")
    body, _n_adv = _strip_internal_advisories(body)
    if _n_adv:
        print(f"[publish-hygiene] stripped {_n_adv} internal move-track-record advisory line(s) — apparatus "
              f"search-steering comments (close-rates, dead-move hints), not published content")
    if a.blueprint:
        _b0 = "Natural-language specification (blueprint)" in body
        body = _insert_blueprint_pointer(body, Path(a.blueprint).name)
        if not _b0 and "Natural-language specification (blueprint)" in body:
            print(f"[translation-boundary] linked the English spec → blueprints/{Path(a.blueprint).name}")
    body, _renames, _residual = _clean_public_names(body)
    if _renames:
        print(f"[name-hygiene] cleaned {len(_renames)} banked-internal name(s) → clean public name(s)")
    if _residual:
        print(f"[name-hygiene] ⚠ {len(_residual)} name(s) left hashed (clean base collides with a sibling decl): "
              + ", ".join(_residual))
    # PUBLISH-BOUNDARY GUARD (2026-06-30 RCA): refuse to file a probe-world standalone (cited rungs stubbed as
    # `axiom`) or a body with a `sorry` under a clean-axioms header — that is the laundering-looking disconnect.
    # The real self-contained proof is the SUBSTRATE (the sidecar's `theory_file`); file THAT.
    _markers = _laundering_markers(body)
    if _markers and not a.allow_nonstandard_body:
        _sc = _p0_sidecar(_run_closures(a.run_tag) / f"{a.target}.lean") or {}
        _tf = _sc.get("theory_file")
        print("REFUSED to file — the body is not a self-contained kernel-clean proof (would look laundered):")
        for m in _markers[:12]:
            print(f"  · {m}")
        print("This is the PROBE-WORLD standalone (cited banked rungs axiomatised for portability), not the real")
        print("proof. File the persisted SUBSTRATE instead" + (f": {_tf}" if _tf else " (the campaign theory .lean)")
              + " — verify it is `#print axioms`-clean + sorry-free, then `--from-file <substrate>`.")
        print("(If this is a deliberately-axiomatic development whose header lists the axioms, pass --allow-nonstandard-body.)")
        return 2
    _fam_runs = {s.strip() for s in a.family_runs.split(",") if s.strip()} or None
    header = build_header(a.run_tag, a.target, body_path, Path(a.log) if a.log else None,
                          axioms=a.axioms, domain=a.domain, family=a.family, family_runs=_fam_runs)
    dest = Path(a.dest or a.from_file)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(header + body, encoding="utf-8")
    print(f"FILED {dest} (verbatim proof + generated provenance header)")
    print("--- header ---")
    print(header)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
