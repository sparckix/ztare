#!/usr/bin/env python3
"""World-class SELF-PLAY CONJECTURER — the corpus-growth engine that removes the 96-proof data ceiling (design
step 5). Grounded in STP (Dong & Ma, Self-play Theorem Prover, arXiv 2502.00212) and Minimo (Poesia et al.,
2407.00695): a CONJECTURER proposes statements near the prover's frontier; the PROVER attempts them (best-of-N);
the KERNEL verifies — we OWN the reward — and every verified (statement, proof) pair GROWS the training corpus.
Iterate: a stronger prover proves harder conjectures → the corpus grows → the next round trains on more data.

REUSES the leanmill apparatus end-to-end rather than reinventing it:
  • PROVER            = solver_core.solve_adhoc (the governed best-of-N cascade; API prover, so this runs WITHOUT a GPU)
  • VERIFIER / reward = the Lean kernel (solve_adhoc only returns kernel-checked, sorry-free closures)
  • NOVELTY gate      = export_training_corpus._akey (α-equivalence — a proposal α-equal to a known theorem is not new)
  • SOUNDNESS gates   = statement elaboration + a warm cheap-tactic/non-vacuity probe
  • CORPUS growth      = the governed closure-certificate ledger (the exporter's existing authority)

PROPOSAL STRATEGIES (a verified seed theorem → candidate NEW statements). The conjecturer mutates the seed's
self-contained probe (defs kept, the target theorem's SIGNATURE transformed), so every candidate stays well-formed:
  1. instance_vary  — retype a typeclass along the Mathlib hierarchy (`[Semiring F]`→`[Field F]`, `[Preorder α]`→
     `[LinearOrder α]`). The one-token change that FLIPS the proof strategy — STP's frontier + the highest-signal
     near-miss pairs. WEAKEN ⇒ harder / maybe false (frontier); STRENGTHEN ⇒ easier (curriculum).
  2. drop_hypothesis — remove one hypothesis binder: a STRICTLY STRONGER claim. If still true ⇒ a real generalization;
     if false ⇒ the prover/kernel reject it (no cost, sound by construction).
  3. compose         — chain two verified lemmas whose conclusion/hypothesis text-match (A ⊢ P, P ⊢ Q ⇒ propose A ⊢ Q).
  4. model_propose   — dispatch the solver's agent to propose a related-but-novel conjecture (optional; the STP
     conjecturer role, learnable later — v1 uses the structural strategies + this as an agentic augmenter).

FRONTIER / CURRICULUM (STP): a proposal is KEPT for the corpus iff the prover CLOSES it (kernel-verified) AND it
passed the non-triviality gate — "provable but not trivial." Difficulty (wall/attempts) is recorded so a later
conjecturer-training round can target the frontier (proved-by-some, not-by-all).

`--dry-run` emits the proposals + gate verdicts WITHOUT the prover (offline-testable, no API/GPU); `--prove` runs
the full loop. Best-effort + fail-closed at the kernel — a bad proposal can never enter the corpus unverified.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# CODEX leaf by default — the self-play prover is a heavy best-of-N consumer; run it on the codex subscription, not
# the metered Claude quota (operator token budget). `ZTARE_LEANMILL_LEAF_RUNTIME=claude` overrides if ever wanted.
os.environ.setdefault("ZTARE_LEANMILL_LEAF_RUNTIME", "codex")

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

# Mathlib typeclass hierarchy fragments: (weaker ⟶ stronger). A retype UP the chain adds structure (easier/curriculum);
# DOWN removes it (harder / possibly false — the frontier). Only well-known, widely-instantiated classes.
_HIERARCHIES = [
    ["Semiring", "Ring", "CommRing", "Field"],
    ["CommMonoid", "CommGroup"],
    ["Monoid", "Group"],
    ["Preorder", "PartialOrder", "LinearOrder"],
    ["SemilatticeSup", "Lattice", "CompleteLattice"],
    ["SemilatticeInf", "Lattice", "CompleteLattice"],
    ["Finite", "Fintype"],
    ["MulOneClass", "Monoid", "CommMonoid"],
]
_NEIGHBORS: "dict[str, list[str]]" = {}
for _chain in _HIERARCHIES:
    for _i, _c in enumerate(_chain):
        _NEIGHBORS.setdefault(_c, [])
        if _i > 0:
            _NEIGHBORS[_c].append(_chain[_i - 1])       # weaken
        if _i + 1 < len(_chain):
            _NEIGHBORS[_c].append(_chain[_i + 1])       # strengthen


def _akey(stmt: str) -> str:
    from importlib import import_module
    m = import_module("export_training_corpus") if "export_training_corpus" in sys.modules else None
    if m is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        m = __import__("export_training_corpus")
    return m._akey(stmt)


def _split_probe(probe: str, target: str) -> "tuple[str, str, str] | None":
    """(preamble_defs, signature, proof_tail) for the target theorem in its self-contained probe — canonical
    lean_source parsing, no ad-hoc regex on structure."""
    from ztare.leanmill.lean_source import (
        extract_signature,
        preamble_before_target,
        resolve_theorem_target,
    )

    identity = resolve_theorem_target(probe, target)
    if identity is None:
        return None
    sig = extract_signature(probe, target)
    if not sig.strip():
        return None
    pre = preamble_before_target(probe, target)
    block = probe[identity.decl_start:identity.decl_end]
    return pre, sig, block


def _emit(pre: str, name: str, sig: str) -> str:
    """A self-contained candidate probe: the seed's defs + the (mutated) theorem, sorried for the prover to close."""
    body = pre if pre.lstrip().startswith("import") else "import Mathlib\n\n" + pre
    return f"{body}\n\ntheorem {name} {sig} := by sorry\n"


# ── PROPOSERS: seed (pre, sig) → list[(mode, new_sig)] ────────────────────────────────────────────────
def propose_instance_vary(sig: str) -> "list[tuple[str, str]]":
    out = []
    for cls, alts in _NEIGHBORS.items():
        # match `[Cls x]` / `[Cls x y]` instance binders (word-boundary so `Semiring` ≠ `CommSemiring` mid-token)
        for m in re.finditer(r"\[\s*" + re.escape(cls) + r"\b", sig):
            for alt in alts:
                new = sig[:m.start()] + "[" + alt + sig[m.end():]
                direction = "strengthen" if alt in _NEIGHBORS.get(cls, []) and _stronger(cls, alt) else "weaken"
                out.append((f"instance_vary:{cls}->{alt}:{direction}", new))
    return out


def _stronger(a: str, b: str) -> bool:
    for ch in _HIERARCHIES:
        if a in ch and b in ch:
            return ch.index(b) > ch.index(a)
    return False


def propose_drop_hypothesis(sig: str) -> "list[tuple[str, str]]":
    """Remove one explicit hypothesis binder `(h : Prop)` → a strictly stronger claim (a candidate generalization).
    Only drops PROP hypotheses (name : <capitalized/∀/≤/…>), never a data binder whose removal ill-types the rest."""
    from ztare.leanmill.lean_source import top_level_colon
    ci = top_level_colon(sig)
    if ci < 0:
        return []
    binders, concl = sig[:ci], sig[ci:]
    out = []
    for m in re.finditer(r"\(([A-Za-z_]\w*)\s*:\s*([^()]*?)\)", binders):
        hyp_type = m.group(2).strip()
        # heuristic: a Prop hypothesis (not a data type like `F`/`V → A`) — starts with ∀/∃/¬ or a known Prop head,
        # or contains a relation. Dropping a DATA binder would ill-type the conclusion, so restrict to Prop-ish.
        if re.match(r"^(∀|∃|¬|Odd|Even|.*[≤<>=∈∧∨→].*)", hyp_type) and m.group(1) not in concl:
            out.append(("drop_hypothesis:" + m.group(1), (binders[:m.start()] + binders[m.end():]).strip() + " " + concl))
    return out


def propose_compose(seeds: "list[dict]", a: dict) -> "list[tuple[str, str, dict]]":
    """Chain lemma A (concl P) with a lemma B whose FIRST hypothesis text-matches P → propose A's hyps ⊢ B's concl.
    Approximate (text match on the normalized conclusion); the kernel gates the real thing. Returns (mode,new_sig,B)."""
    from ztare.leanmill.lean_source import extract_signature, top_level_colon
    def concl(s):
        i = top_level_colon(s)
        return " ".join(s[i + 1:].split()) if i >= 0 else ""
    ca = concl(a.get("statement") or "")
    if not ca:
        return []
    out = []
    for b in seeds:
        if b is a:
            continue
        sb = b.get("statement") or ""
        # B uses A's conclusion as a hypothesis? (text containment of the normalized conclusion)
        if ca and ca in " ".join(sb.split()) and concl(sb) and concl(sb) != ca:
            # propose A-hyps ⊢ B-conclusion (drop the bridging hyp; the prover reconstructs it via A)
            ia = top_level_colon(a.get("statement") or "")
            hyps_a = (a.get("statement") or "")[:ia]
            out.append(("compose:" + (b.get("target") or "?"), f"{hyps_a} : {concl(sb)}", b))
    return out[:2]


# ── GATES ─────────────────────────────────────────────────────────────────────────────────────────────
def gate(
    probe: str,
    name: str,
    sig: str,
    corpus_keys: set,
    lean_root: Path,
    timeout: int = 90,
    *,
    compile_fn=None,
    nondegenerate_probe_fn=None,
) -> "tuple[bool, str]":
    """Cheap pre-prover gates: NOVEL (α-key not in corpus) · WELL-FORMED (compiles as `:= by sorry`) · NON-TRIVIAL."""
    stmt = f"theorem {name} {sig} := by sorry"
    if _akey(stmt) in corpus_keys:
        return False, "not novel (α-equal to a corpus theorem)"
    try:
        if compile_fn is None:
            from ztare.formal.repl_compile import compile_probe_via_repl
            compile_fn = compile_probe_via_repl
        r = compile_fn(probe, lean_root, timeout=timeout, reject_sorry=False)  # sorry OK: gating the STATEMENT
        if not (isinstance(r, tuple) and r[0]):
            return False, "statement not well-formed (probe does not elaborate)"
    except Exception as e:  # noqa: BLE001
        return False, f"well-formedness probe unavailable: {e!r}"[:80]
    try:
        from ztare.gates.v33_preflight_risk_detector import detect_risks, nondegenerate_instance_probe
        from ztare.leanmill.lean_source import swap_sorry

        if detect_risks(sig).get("vacuity_suspected") is True:
            return False, "vacuous statement (lexical risk gate)"
        cheap = swap_sorry(
            probe,
            "by first | trivial | rfl | simp_all | omega | decide | tauto | norm_num",
        )
        if not cheap.strip():
            return False, "non-triviality probe could not be constructed"
        r = compile_fn(cheap, lean_root, timeout=timeout, reject_sorry=True)
        if not (isinstance(r, tuple) and r):
            return False, "non-triviality probe unavailable (cheap compile returned no verdict)"
        if r[0]:
            return False, "trivial (closes by the cheap tactic cascade)"
        nondegenerate_probe_fn = nondegenerate_probe_fn or nondegenerate_instance_probe
        vacuity = nondegenerate_probe_fn(sig, lean_root, timeout=timeout)
        if isinstance(vacuity, dict) and vacuity.get("vacuity_confirmed") is True:
            return False, "vacuous statement (no non-degenerate instance)"
    except Exception as e:  # noqa: BLE001 — a dead quality instrument cannot admit training data
        return False, f"non-triviality probe unavailable: {e!r}"[:120]
    return True, "novel · well-formed · non-trivial"


@contextmanager
def _direct_fallback_solver():
    """Keep the optional blind-corpus fallback bounded to direct proof adaptation."""
    names = ("ZTARE_LEANMILL_ISO_ROUTE", "ZTARE_LEANMILL_DECOMPOSE_FIRST")
    previous = {name: os.environ.get(name) for name in names}
    try:
        for name in names:
            os.environ[name] = "0"
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _checkpoint(path: Path, row: dict) -> None:
    """Append a resumable run view. The governed certificate ledger remains the proof authority."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def _ratified_closure_receipt(result: object) -> "tuple[str, str] | None":
    """Return the proof and exact certificate record only for a governed, durable closure.

    ``outcome == closed`` is the kernel verdict, not permission for self-play to
    claim trainable output.  The solver owns governance eligibility and the
    canonical ledger append; this consumer requires both receipts.
    """
    if not isinstance(result, dict):
        return None
    rows = result.get("results")
    primary = rows[0] if isinstance(rows, list) and rows else None
    if not isinstance(primary, dict) or primary.get("outcome") != "closed":
        return None
    proof = str(primary.get("proof_text") or "").strip()
    if not proof or "sorry" in proof or "admit" in proof:
        return None
    if result.get("governance_ratification_eligible") is not True:
        return None
    ledger = str(result.get("closure_certificate") or "").strip()
    record_sha = str(result.get("closure_certificate_record_sha256") or "").strip()
    if not ledger or re.fullmatch(r"[0-9a-f]{64}", record_sha) is None:
        return None
    return proof, record_sha


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, default=REPO / "ztare_proofs/leanmill-formalizations")
    ap.add_argument("--prover-corpus", type=Path, default=None,
                    help="prover_corpus.jsonl of verified seeds (default: <corpus>/../.solver_scratch export)")
    ap.add_argument("--seeds", type=int, default=8, help="verified theorems to extend this pass")
    ap.add_argument("--per-seed", type=int, default=6, help="cap on gated proposals routed to the prover per seed")
    ap.add_argument("--modes", default="instance_vary,drop_hypothesis,compose")
    ap.add_argument("--out", type=Path, default=REPO / "ztare_proofs/.solver_scratch/self_play_trajectory.jsonl",
                    help="append-only run checkpoint; governed closures enter the canonical certificate ledger")
    ap.add_argument("--run-tag", default="", help="explicit campaign identity (default: inherited or timestamped)")
    ap.add_argument("--lean-root", type=Path, default=REPO / "ztare_proofs")
    ap.add_argument("--dry-run", action="store_true", help="propose + gate only; do NOT invoke the prover (no API/GPU)")
    ap.add_argument("--codex-fallback", action="store_true",
                    help="after proof-transfer, ADAPT non-transferable variants with codex (default OFF — transfer-"
                         "only is fast + free; codex measured 0-yield on false weakenings, use only when worth it)")
    ap.add_argument("--timeout", type=int, default=400, help="per-conjecture prover budget (s)")
    ap.add_argument("--allow-legacy-diagnostic", action="store_true",
                    help="explicitly permit a legacy corpus for diagnostics; rows cannot be treated as release training data")
    a = ap.parse_args()

    # LAKE ON PATH (the canonical mechanized fix solver_core.main applies): a DIRECT solve_adhoc caller — like this
    # self-play — bypasses main(), so without this native_hammer's cold `lake` probe fails its positive control,
    # the cheap tactic move goes DEAD, and every conjecture falls to codex (slow). Bootstrap elan/lake here.
    try:
        from ztare.gates.lean_compile_primitives import ensure_elan_on_path
        ensure_elan_on_path()
    except Exception:  # noqa: BLE001
        pass

    run_tag = (a.run_tag or os.environ.get("ZTARE_SOLVER_RUN_TAG") or
               f"selfplay_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    os.environ["ZTARE_SOLVER_RUN_TAG"] = run_tag
    try:
        from ztare.leanmill.phase_timing import record_campaign
        record_campaign("self-play", run_tag=run_tag, target="blind-corpus-topup")
    except Exception:  # noqa: BLE001 — telemetry cannot block the governed loop
        pass

    from ztare.leanmill.training_corpus_contract import validate_training_corpus_directory

    rows = []
    corpus_errors = []
    for cand in [a.prover_corpus, REPO / "analytics/public/leanmill/training_corpus/prover_corpus.jsonl",
                 REPO / "scripts/public/models/void_sft" / "corpus_fresh/prover_corpus.jsonl",
                 Path.home() / "void_sft_artifacts/corpus_fresh/prover_corpus.jsonl"]:
        if cand and Path(cand).exists():
            try:
                validate_training_corpus_directory(
                    Path(cand).parent,
                    required_files=(Path(cand).name,),
                    allow_legacy_diagnostic=a.allow_legacy_diagnostic,
                )
            except ValueError as exc:
                corpus_errors.append(f"{cand}: {exc}")
                if a.prover_corpus is not None and Path(cand) == a.prover_corpus:
                    break
                continue
            rows = [json.loads(l) for l in Path(cand).read_text().splitlines() if l.strip()]
            break
    if not rows:
        detail = "; ".join(corpus_errors) or "no prover_corpus.jsonl found"
        print(detail, file=sys.stderr)
        return 2
    corpus_keys = {_akey(r.get("statement") or "") for r in rows if r.get("statement")}
    modes = set(a.modes.split(","))
    # SIMPLEST-FIRST (yield/codex-minute): a short-proof seed's variants are far likelier provable AND close fast;
    # grinding our hardest filed theorems (Topkis, ~1100s) first burns big budgets on low-odds variants. Sort by
    # proof length ascending so the cheap, high-yield candidates run first.
    _elig = [r for r in rows if r.get("recompilable_probe") and r.get("target") and r.get("statement")]
    seeds = sorted(_elig, key=lambda r: len(r.get("proof") or ""))[:a.seeds]
    print(f"[self-play] {len(rows)} verified seeds in corpus · extending {len(seeds)} · modes={sorted(modes)} · "
          f"{'DRY-RUN' if a.dry_run else 'PROVE'}", flush=True)

    proposals, kept = [], []
    checkpointed = 0
    for s in seeds:
        sp = _split_probe(s["recompilable_probe"], s["target"])
        if not sp:
            continue
        pre, sig, _ = sp
        cand: "list[tuple[str, str]]" = []
        if "instance_vary" in modes:
            cand += propose_instance_vary(sig)
        if "drop_hypothesis" in modes:
            cand += propose_drop_hypothesis(sig)
        if "compose" in modes:
            cand += [(mode, ns) for mode, ns, _b in propose_compose(seeds, s)]
        # gate + (optionally) prove
        n_from_seed = 0
        for mode, new_sig in cand:
            if n_from_seed >= a.per_seed:
                break
            cname = f"{s['target']}_sp"
            probe = _emit(pre, cname, new_sig)
            ok, why = gate(probe, cname, new_sig, corpus_keys, a.lean_root)
            proposals.append({"seed": s["target"], "mode": mode, "sig": new_sig.strip()[:120], "gate": why})
            if not ok:
                continue
            n_from_seed += 1
            corpus_keys.add(_akey(f"theorem {cname} {new_sig} := by sorry"))   # don't re-propose within the pass
            if a.dry_run:
                continue
            # PROOF-TRANSFER FIRST: route the carried proof through solve_adhoc's provider-free ratification-only
            # door. It performs the same kernel, axiom, statement-integrity, governance, and certificate steps as
            # every other closure; direct REPL compilation is not an authority or a second persistence path.
            _op = (s.get("proof") or "").strip()
            if _op:
                try:
                    from ztare.leanmill.solver.solver_core import solve_adhoc
                    _sub = a.lean_root
                    res = solve_adhoc(
                        cname,
                        probe,
                        "",
                        substrate=_sub,
                        timeout_s=min(a.timeout, 180),
                        preverified_proof=_op,
                        preverified_provider="self_play_proof_transfer",
                        preverified_only=True,
                        require_positive_axiom_receipt=True,
                    ) or {}
                    r0 = (res.get("results") or [{}])[0]
                    receipt = _ratified_closure_receipt(res)
                    if receipt is not None:
                        proof, certificate_record_sha256 = receipt
                        rec = {
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "run_tag": run_tag,
                            "target": cname,
                            "seed": s["target"],
                            "mode": mode + ":proof_transfer",
                            "outcome": "closed",
                            "statement_sha256": hashlib.sha256(new_sig.encode()).hexdigest(),
                            "probe_sha256": hashlib.sha256(probe.encode()).hexdigest(),
                            "proof_sha256": hashlib.sha256(proof.encode()).hexdigest(),
                            "closure_certificate": res.get("closure_certificate"),
                            "closure_certificate_record_sha256": certificate_record_sha256,
                        }
                        kept.append(rec)
                        _checkpoint(a.out, rec)
                        checkpointed += 1
                        print(f"[self-play] ✓ TRANSFER {mode} from {s['target']} (seed proof, no codex)", flush=True)
                        continue
                    transfer_failure = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "run_tag": run_tag,
                        "target": cname,
                        "seed": s["target"],
                        "mode": mode + ":proof_transfer",
                        "outcome": str(r0.get("outcome") or "no_result"),
                        "reason": str(
                            r0.get("failure_reason")
                            or r0.get("reason")
                            or res.get("reason")
                            or "carried proof did not ratify for the candidate statement"
                        )[:500],
                        "statement_sha256": hashlib.sha256(new_sig.encode()).hexdigest(),
                        "probe_sha256": hashlib.sha256(probe.encode()).hexdigest(),
                        "seed_proof_sha256": hashlib.sha256(_op.encode()).hexdigest(),
                        "closure_certificate": res.get("closure_certificate"),
                        "closure_certificate_record_sha256": res.get(
                            "closure_certificate_record_sha256"
                        ),
                    }
                    _checkpoint(a.out, transfer_failure)
                    checkpointed += 1
                except Exception as e:  # noqa: BLE001 — transfer failure can fall to the optional adapter
                    _checkpoint(
                        a.out,
                        {
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "run_tag": run_tag,
                            "target": cname,
                            "seed": s["target"],
                            "mode": mode + ":proof_transfer",
                            "outcome": "infrastructure_failure",
                            "reason": repr(e)[:500],
                            "statement_sha256": hashlib.sha256(new_sig.encode()).hexdigest(),
                            "probe_sha256": hashlib.sha256(probe.encode()).hexdigest(),
                            "seed_proof_sha256": hashlib.sha256(_op.encode()).hexdigest(),
                            "closure_certificate": None,
                            "closure_certificate_record_sha256": None,
                        },
                    )
                    checkpointed += 1
                    print(f"[self-play] transfer unavailable for {s['target']}: {e!r}", flush=True)
            if not a.codex_fallback:
                # TRANSFER-ONLY (default): the codex ADAPT fallback measured 0-yield + ~2-3 min/candidate on false
                # weakenings — pure throttle. DEFER non-transferable variants to a later round (skip-if-hard, the STP
                # curriculum: the frontier advances as the model improves). `--codex-fallback` re-enables the adapt try.
                continue
            # PROVE via the governed cascade (kernel-gated best-of-N; API prover=codex, no GPU). solve_adhoc writes
            # the self-contained probe to `substrate`, runs it through contract→moves→governance→receipt, and
            # returns {"results":[{"outcome","proof_text",...}]}; a kernel-clean close ⇒ outcome=="closed".
            from ztare.leanmill.solver.solver_core import solve_adhoc
            # substrate at the LAKE-ROOT (next to lakefile), NOT .solver_scratch — a subdir has no lakefile, so
            # native_hammer's `lake` can't find the project ⇒ its positive control fails ⇒ the cheap tactic move
            # goes DEAD and everything falls to codex (the slow path). Root-level = native_hammer live. 2026-07-02.
            _sub = a.lean_root
            # SEED-PROOF HINT (the STP lever): a `mode` variant's proof is usually the ORIGINAL proof adapted, not a
            # from-scratch rederivation. Hand codex the seed's kernel-checked proof as `notes` so it ADAPTS it to the
            # changed hypothesis/instance — turns "prove a hard theorem cold" into "tweak a known proof" (yield ↑↑).
            _hint = (f"This target is a `{mode}` variant of the ALREADY-PROVEN theorem `{s['target']}`. Its "
                     f"kernel-checked proof is below — ADAPT it to close this variant (the argument is usually the "
                     f"same up to the changed hypothesis / typeclass instance):\n\n{(s.get('proof') or '').strip()}")
            with _direct_fallback_solver():
                res = solve_adhoc(
                    cname,
                    probe,
                    "",
                    substrate=_sub,
                    timeout_s=a.timeout,
                    notes=_hint,
                    require_positive_axiom_receipt=True,
                ) or {}
            r0 = (res.get("results") or [{}])[0]
            receipt = _ratified_closure_receipt(res)
            if receipt is not None:
                proof, certificate_record_sha256 = receipt
                rec = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "run_tag": run_tag,
                    "target": cname,
                    "seed": s["target"],
                    "mode": mode,
                    "outcome": "closed",
                    "statement_sha256": hashlib.sha256(new_sig.encode()).hexdigest(),
                    "probe_sha256": hashlib.sha256(probe.encode()).hexdigest(),
                    "proof_sha256": hashlib.sha256(proof.encode()).hexdigest(),
                    "closure_certificate": res.get("closure_certificate"),
                    "closure_certificate_record_sha256": certificate_record_sha256,
                }
                kept.append(rec)
                _checkpoint(a.out, rec)
                checkpointed += 1
                print(f"[self-play] ✓ CLOSED {mode} from {s['target']}", flush=True)
            else:
                _checkpoint(
                    a.out,
                    {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "run_tag": run_tag,
                        "target": cname,
                        "seed": s["target"],
                        "mode": mode,
                        "outcome": str(r0.get("outcome") or "no_result"),
                        "reason": str(
                            r0.get("failure_reason")
                            or r0.get("reason")
                            or res.get("reason")
                            or "governed prover did not close the candidate"
                        )[:500],
                        "statement_sha256": hashlib.sha256(new_sig.encode()).hexdigest(),
                        "probe_sha256": hashlib.sha256(probe.encode()).hexdigest(),
                        "closure_certificate": res.get("closure_certificate"),
                        "closure_certificate_record_sha256": res.get(
                            "closure_certificate_record_sha256"
                        ),
                    },
                )
                checkpointed += 1
                print(f"[self-play] ✗ {mode} from {s['target']} → {r0.get('outcome') or 'no-result'}", flush=True)

    n_gated = sum(1 for p in proposals if "novel" in p["gate"])
    print(json.dumps({"seeds_extended": len(seeds), "proposals": len(proposals), "passed_gates": n_gated,
                      "proven_new_theorems": len(kept),
                      "governed_certificate_ledger": "analytics/public/queries/adhoc_closure_certificates.jsonl",
                      "checkpoint_rows": checkpointed,
                      "checkpoint": str(a.out) if checkpointed else None,
                      "run_tag": run_tag}, indent=2))
    if a.dry_run:
        print("\n[self-play] DRY-RUN proposals that PASSED the gates (the prover would attack these):")
        for p in proposals:
            if "novel" in p["gate"]:
                print(f"  [{p['mode']}] {p['seed']}: {p['sig']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
