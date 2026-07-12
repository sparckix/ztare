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
  • SOUNDNESS gates   = autoformalize.default_triviality (reject `simp`/`rfl`-trivial) + a well-formed `:= by sorry` compile
  • CORPUS growth      = a self_play_corpus.jsonl the exporter folds in (same schema as a campaign closure)

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
    from ztare.leanmill.lean_source import extract_signature, decl_blocks, split_at_proof
    blk = dict(decl_blocks(probe)).get(target)
    if not blk:
        return None
    sig = extract_signature(probe, target)
    if not sig.strip():
        return None
    pre = re.split(r"(?m)^\s*(?:theorem|lemma)\s+" + re.escape(target) + r"\b", probe, maxsplit=1)[0].rstrip()
    return pre, sig, blk


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
def gate(probe: str, name: str, sig: str, corpus_keys: set, lean_root: Path, timeout: int = 90) -> "tuple[bool, str]":
    """Cheap pre-prover gates: NOVEL (α-key not in corpus) · WELL-FORMED (compiles as `:= by sorry`) · NON-TRIVIAL."""
    stmt = f"theorem {name} {sig} := by sorry"
    if _akey(stmt) in corpus_keys:
        return False, "not novel (α-equal to a corpus theorem)"
    try:
        from ztare.formal.repl_compile import compile_probe_via_repl
        r = compile_probe_via_repl(probe, lean_root, timeout=timeout, reject_sorry=False)  # sorry OK: gating the STATEMENT
        if not (isinstance(r, tuple) and r[0]):
            return False, "statement not well-formed (probe does not elaborate)"
    except Exception as e:  # noqa: BLE001
        return False, f"well-formedness probe unavailable: {e!r}"[:80]
    try:
        from ztare.leanmill.solver.autoformalize import default_triviality
        if default_triviality(probe, lean_root):
            return False, "trivial (closes by simp/rfl/decide alone — no training signal)"
    except Exception:  # noqa: BLE001 — triviality is advisory; a probe error ⇒ keep (the prover will decide)
        pass
    return True, "novel · well-formed · non-trivial"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=Path, default=REPO / "ztare_proofs/leanmill-formalizations")
    ap.add_argument("--prover-corpus", type=Path, default=None,
                    help="prover_corpus.jsonl of verified seeds (default: <corpus>/../.solver_scratch export)")
    ap.add_argument("--seeds", type=int, default=8, help="verified theorems to extend this pass")
    ap.add_argument("--per-seed", type=int, default=6, help="cap on gated proposals routed to the prover per seed")
    ap.add_argument("--modes", default="instance_vary,drop_hypothesis,compose")
    ap.add_argument("--out", type=Path, default=REPO / "ztare_proofs/.solver_scratch/self_play_corpus.jsonl")
    ap.add_argument("--lean-root", type=Path, default=REPO / "ztare_proofs")
    ap.add_argument("--dry-run", action="store_true", help="propose + gate only; do NOT invoke the prover (no API/GPU)")
    ap.add_argument("--codex-fallback", action="store_true",
                    help="after proof-transfer, ADAPT non-transferable variants with codex (default OFF — transfer-"
                         "only is fast + free; codex measured 0-yield on false weakenings, use only when worth it)")
    ap.add_argument("--timeout", type=int, default=400, help="per-conjecture prover budget (s)")
    a = ap.parse_args()

    # LAKE ON PATH (the canonical mechanized fix solver_core.main applies): a DIRECT solve_adhoc caller — like this
    # self-play — bypasses main(), so without this native_hammer's cold `lake` probe fails its positive control,
    # the cheap tactic move goes DEAD, and every conjecture falls to codex (slow). Bootstrap elan/lake here.
    try:
        from ztare.gates.lean_compile_primitives import ensure_elan_on_path
        ensure_elan_on_path()
    except Exception:  # noqa: BLE001
        pass

    pc = a.prover_corpus or (a.corpus / ".." / ".." / "analytics_placeholder")
    rows = []
    for cand in [a.prover_corpus, REPO / "scripts/public/models/void_sft" / "corpus_fresh/prover_corpus.jsonl",
                 Path.home() / "void_sft_artifacts/corpus_fresh/prover_corpus.jsonl"]:
        if cand and Path(cand).exists():
            rows = [json.loads(l) for l in Path(cand).read_text().splitlines() if l.strip()]
            break
    if not rows:
        print("no prover_corpus.jsonl found — pass --prover-corpus", file=sys.stderr)
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
            # PROOF-TRANSFER FIRST (cheap, no codex — the big yield lever): a STRUCTURAL variant's proof is usually
            # the seed's proof VERBATIM (a strengthening compiles as-is; a weaken/drop often does too). Splice the
            # seed's kernel-checked proof and compile it via the warm REPL (~seconds). If it closes ⇒ an instant
            # verified new theorem at ZERO codex cost. Only when the original proof does NOT transfer do we spend
            # codex to ADAPT it (the genuinely-harder variants). This is what turns low-yield/slow into high-yield/fast.
            _op = (s.get("proof") or "").strip()
            if _op:
                _tp = (pre if pre.lstrip().startswith("import") else "import Mathlib\n\n" + pre) + \
                    f"\n\ntheorem {cname} {new_sig} := {_op}\n"
                try:
                    from ztare.formal.repl_compile import compile_probe_via_repl
                    _r = compile_probe_via_repl(_tp, a.lean_root, timeout=90, reject_sorry=True)
                    if isinstance(_r, tuple) and _r[0]:
                        rec = {"target": cname, "statement": new_sig, "proof": _op, "recompilable_probe": _tp,
                               "source": "self_play", "seed": s["target"], "mode": mode + ":proof_transfer",
                               "checker": "lean_lake"}
                        kept.append(rec)
                        Path(a.out).parent.mkdir(parents=True, exist_ok=True)   # CHECKPOINT immediately: transfer
                        with Path(a.out).open("a", encoding="utf-8") as _f:     # closures skip solve_adhoc's cert
                            _f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        print(f"[self-play] ✓ TRANSFER {mode} from {s['target']} (seed proof, no codex)", flush=True)
                        continue
                except Exception:  # noqa: BLE001 — transfer is best-effort; fall to codex
                    pass
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
            _sub = a.lean_root / f"_sp_{cname}.lean"
            # SEED-PROOF HINT (the STP lever): a `mode` variant's proof is usually the ORIGINAL proof adapted, not a
            # from-scratch rederivation. Hand codex the seed's kernel-checked proof as `notes` so it ADAPTS it to the
            # changed hypothesis/instance — turns "prove a hard theorem cold" into "tweak a known proof" (yield ↑↑).
            _hint = (f"This target is a `{mode}` variant of the ALREADY-PROVEN theorem `{s['target']}`. Its "
                     f"kernel-checked proof is below — ADAPT it to close this variant (the argument is usually the "
                     f"same up to the changed hypothesis / typeclass instance):\n\n{(s.get('proof') or '').strip()}")
            res = solve_adhoc(cname, probe, "", substrate=_sub, timeout_s=a.timeout, notes=_hint) or {}
            r0 = (res.get("results") or [{}])[0]
            proof = r0.get("proof_text") or ""
            if r0.get("outcome") == "closed" and proof.strip() and "sorry" not in proof:
                rec = {"target": cname, "statement": new_sig, "proof": proof, "recompilable_probe": probe,
                       "source": "self_play", "seed": s["target"], "mode": mode, "checker": "lean_lake"}
                kept.append(rec)
                Path(a.out).parent.mkdir(parents=True, exist_ok=True)
                with Path(a.out).open("a", encoding="utf-8") as _f:   # incremental (same as transfer) — no end-of-run
                    _f.write(json.dumps(rec, ensure_ascii=False) + "\n")   # re-write ⇒ no double-write bug
                print(f"[self-play] ✓ CLOSED {mode} from {s['target']}", flush=True)
            else:
                print(f"[self-play] ✗ {mode} from {s['target']} → {r0.get('outcome') or 'no-result'}", flush=True)

    n_gated = sum(1 for p in proposals if "novel" in p["gate"])
    print(json.dumps({"seeds_extended": len(seeds), "proposals": len(proposals), "passed_gates": n_gated,
                      "proven_new_theorems": len(kept), "appended_to": str(a.out) if kept else None}, indent=2))
    if a.dry_run:
        print("\n[self-play] DRY-RUN proposals that PASSED the gates (the prover would attack these):")
        for p in proposals:
            if "novel" in p["gate"]:
                print(f"  [{p['mode']}] {p['seed']}: {p['sig']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
