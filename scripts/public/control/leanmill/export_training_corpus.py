#!/usr/bin/env python3
"""Export LeanMill's kernel-verified output as a TRAINING corpus — the expert-iteration flywheel's data tap.

The strange loop (and the field's most-validated compounding mechanism — DeepSeek-Prover / AlphaProof: generate
kernel-verified proofs, then TRAIN the next model on them): our inference-time harness already *generates*
kernel-checked artifacts. We don't fine-tune here, but curating those artifacts into a training-ready corpus lets
a FUTURE pretrain/SFT consume them — and the rarest, most defensible part (the data) is exactly what we own.
"Specialize in the void": much of this is in domains NO public corpus has (theory-built defs Mathlib lacks +
their proofs, NL↔formal pairs in econ/finance/strategy, kernel-refutations of false claims), so it fills gaps the
base model cannot get elsewhere.

THREE corpora, each from a store we already write (no new instrumentation; read-only; dedup + quality-filter):
  1. prover_corpus      — (statement, kernel-verified proof) from adhoc_closure_certificates.jsonl
                          (outcome==closed, sorry-free; deduped by the canonical α-equivalence key).
  2. autoformalization  — (nl, lean_statement) CONFIRMED-faithful pairs from the faithfulness store
                          (the firewall-admitted correspondences — uniquely ours; most autoformalizers have none).
  3. falsification      — (statement, refutation/counterexample) from the no_good store (failure_class
                          statement_false) — teach a model to FALSIFY, the data almost no corpus contains.
  4. faithfulness_discriminator — (laundered statement, why-unfaithful witness) from the no_good store
                          (target_signature_altered / definition_altered): mis-formalizations the firewall
                          CAUGHT. The labelled NEGATIVE complement to stream 2's faithful positives — a
                          faithfulness-checker corpus that exists only where a firewall rejects.

QUALITY DISCIPLINE (mirrors the bank's "verify before bank" + the literature's "filter failures or memory
self-poisons"): prover rows are kernel-closed + sorry-free; autoformalization rows are CONFIRMED-faithful only;
falsification rows are CONFIRMED ¬G only. `--void-only` keeps just rows whose statement uses a bespoke def (not
pure Mathlib) — the rarest, highest-value slice. NOT a soundness surface: a downstream trainer is responsible for
its own use; this only curates + dedups what the kernel already certified.

  python scripts/public/control/leanmill/export_training_corpus.py [--out DIR] [--void-only]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

CERTS_REL = "analytics/public/queries/adhoc_closure_certificates.jsonl"
FAITH_REL = "analytics/public/queries/solver_lane_faithfulness_store.jsonl"
NOGOOD_REL = "analytics/public/queries/solver_lane_no_good_store.jsonl"
PLAN_REL = "analytics/public/queries/solver_lane_plan_choices.jsonl"
OUT_REL = "analytics/public/leanmill/training_corpus"


def _read_jsonl(p: Path) -> "list[dict]":
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def _akey(stmt: str) -> str:
    """Canonical α-equivalence key for dedup — the SAME normalizer the proof cache + re-derivation metric use."""
    try:
        from ztare.leanmill.solver.proof_cache import normalize_statement_equiv
        return normalize_statement_equiv(stmt or "")
    except Exception:  # noqa: BLE001 — fall back to whitespace-normalized text (still dedups exact repeats)
        return " ".join((stmt or "").split())


def _target_statement(cert: dict) -> str:
    """The target theorem's signature from the cert's self-contained probe (canonical lean_source parse)."""
    probe = cert.get("recompilable_probe") or ""
    tgt = cert.get("target") or ""
    if not probe.strip():
        return ""
    try:
        from ztare.leanmill.solver.statement_integrity import decl_blocks
        from ztare.leanmill.lean_source import extract_signature
        blocks = dict(decl_blocks(probe))
        if tgt in blocks:
            return (extract_signature(probe, tgt) or "").strip()
        return (extract_signature(probe, tgt) or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def _uses_bespoke_def(cert: dict) -> bool:
    """True ⇒ the proof's statement references a def DEFINED in its own probe (a theory-built, not-in-Mathlib
    object) — the 'void' slice that is the rarest training data. Reuses the canonical decl parser; no regex over types."""
    probe = cert.get("recompilable_probe") or ""
    if not probe.strip():
        return False
    try:
        import re
        from ztare.leanmill.solver.statement_integrity import decl_blocks
        from ztare.leanmill.lean_source import extract_signature
        blocks = dict(decl_blocks(probe))
        defnames = {n for n, b in blocks.items()
                    if re.match(r"\s*(?:noncomputable\s+|private\s+|protected\s+)*(?:def|abbrev|structure|inductive|class)\b", b)}
        sig = extract_signature(probe, cert.get("target") or "") or ""
        return any(d and re.search(r"(?<![\w.])" + re.escape(d) + r"(?![\w])", sig) for d in defnames)
    except Exception:  # noqa: BLE001
        return False


def _clean_since() -> str:
    """CLEAN-REGIME cutoff — see compounding_curve._clean_since. The historical ledger carries this session's
    fixed-bug noise (mislabeled closes, double-by splices, dead-instrument rows); default the training corpus to
    post-fix closures so we don't train on contaminated rows. `--all-time` includes everything (a kernel-closed
    sorry-free proof is valid whenever proved, but forward-looking is the safer default given the noise)."""
    import os
    return os.environ.get("ZTARE_LEANMILL_COMPOUNDING_CLEAN_SINCE", "2026-06-24T00:00:00+00:00")


def _is_noise_target(name: str) -> bool:
    n = (name or "").strip()
    return n in {"bank_wiring_probe", "cite_probe_lemma"} or n.endswith("_probe") or n.startswith("probe_")


def _attach_reasoning(rows: "list[dict]", plan_choices: "list[dict]") -> "list[dict]":
    """CoT distillation (Gemini review A): attach the agent's DECOMPOSITION reasoning to each proof, so a prover
    can be trained to think-then-prove (DeepSeek-Prover-V1.5 / Lean-STaR). The reasoning lives in
    solver_lane_plan_choices.reason (the agent's own plan for the goal); the join must be PRECISE — a LONG
    (≥80-char) goal that appears VERBATIM in exactly ONE proof's probe — because a fuzzy substring join mis-attributes
    one reason to many proofs (verified: it mapped 'partial fractions' onto unrelated putnam targets). Rows with no
    unambiguous reason keep reasoning='' (bare whole-proof, still the valid DeepSeek-Prover-V1 baseline format)."""
    reasons: "dict[str, str]" = {}
    for r in plan_choices:
        g = " ".join((r.get("target") or "").split())
        rsn = (r.get("reason") or "").strip()
        if rsn and len(g) >= 40:                                # 40 (not 80): the goal CONCLUSION is often shorter
            reasons.setdefault(g, rsn)
    for row in rows:
        # match the planner goal against BOTH the statement and the probe (the conclusion appears in either)
        hay = " ".join(((row.get("statement") or "") + " " + (row.get("recompilable_probe") or "")).split())
        hits = [rsn for g, rsn in reasons.items() if g in hay]
        row["reasoning"] = hits[0] if len(hits) == 1 else ""   # per-row unambiguous only; else no CoT (never mis-attribute)
    return rows


def _shingle(s: str) -> set:
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", (s or "").lower()))


def _drop_near_dups(rows: "list[dict]", textfn, thr: float = 0.85) -> "list[dict]":
    """Second-pass dedup beyond the α-key: drop a row whose token-set Jaccard against an already-kept row is
    ≥ thr (the same statement reformulated or renamed — distinct α-keys, near-identical content). Redundant
    training pairs teach nothing (the 'Library Learning Doesn't' failure mode), so the training corpus is
    curated for DIVERSITY, not just exact-distinctness. Order-stable; O(n²) but n is small."""
    import re as _re  # noqa: F401 — _shingle uses module-level re; kept explicit for clarity
    kept: "list[set]" = []
    out: "list[dict]" = []
    for r in rows:
        sh = _shingle(textfn(r))
        if not sh:
            out.append(r)
            continue
        if any(len(sh & k) / max(1, len(sh | k)) >= thr for k in kept):
            continue
        kept.append(sh)
        out.append(r)
    return out


def prover_rows(certs: "list[dict]", void_only: bool = False, all_time: bool = False) -> "list[dict]":
    """Kernel-verified (statement, proof) pairs — closed, sorry-free, deduped by α-key, noise-targets + (by default)
    pre-clean-regime rows excluded. The expert-iteration corpus."""
    seen: set = set()
    rows: "list[dict]" = []
    cutoff = _clean_since()
    for c in certs:
        if c.get("outcome") != "closed":
            continue
        if _is_noise_target(c.get("target") or ""):
            continue
        if not all_time and (c.get("ts") or "") < cutoff:
            continue
        proof = (c.get("proof_text") or "").strip()
        probe = c.get("recompilable_probe") or ""
        if not proof or "sorry" in proof or "admit" in proof or "sorry" in probe:
            continue
        # `exact?`/`apply?` are interactive SEARCH tactics captured as a "proof" — they carry no proof content
        # and don't port to a cold context, so they are worthless (harmful) training targets. Drop them.
        if "exact?" in proof or "apply?" in proof:
            continue
        void = _uses_bespoke_def(c)
        if void_only and not void:
            continue
        k = _akey(_target_statement(c) or probe)
        if k in seen:
            continue
        seen.add(k)
        rows.append({"target": c.get("target"), "statement": _target_statement(c),
                     "proof": proof, "recompilable_probe": probe, "substrate": c.get("substrate"),
                     "void_novel": void, "checker": c.get("checker"), "ts": c.get("ts")})
    return rows


def autoformalization_rows(faith: "list[dict]") -> "list[dict]":
    """CONFIRMED-faithful (nl, lean_statement) pairs — the firewall-admitted NL↔formal correspondences."""
    seen: set = set()
    rows: "list[dict]" = []
    for r in faith:
        if r.get("kind") != "faithful":
            continue
        nl, stmt = (r.get("nl") or "").strip(), (r.get("statement") or "").strip()
        if not nl or not stmt:
            continue
        k = (_akey(stmt), " ".join(nl.lower().split()))
        if k in seen:
            continue
        seen.add(k)
        rows.append({"nl": nl, "lean_statement": stmt, "source": r.get("source")})
    return rows


def falsification_rows(nogood: "list[dict]") -> "list[dict]":
    """CONFIRMED kernel-refuted (statement, refutation) pairs — teach FALSIFY (data almost no corpus has)."""
    seen: set = set()
    rows: "list[dict]" = []
    for r in nogood:
        if r.get("failure_class") != "statement_false" or not r.get("confirmed", True):
            continue
        stmt = (r.get("statement") or "").strip()
        if not stmt:
            continue
        k = _akey(stmt)
        if k in seen:
            continue
        seen.add(k)
        rows.append({"statement": stmt, "refutation": (r.get("witness") or r.get("distinguishing") or "").strip(),
                     "source": r.get("source")})
    return rows


_ALTERATION_CLASSES = ("target_signature_altered", "definition_altered")


def faithfulness_discriminator_rows(nogood: "list[dict]") -> "list[dict]":
    """FAITHFULNESS-DISCRIMINATOR negatives: mis-formalizations the firewall CAUGHT — a Lean statement the agent
    produced that altered the target signature or a referenced definition, with the witness naming the alteration.
    The complement to `autoformalization_rows` (the confirmed-faithful positives): together they form a labelled
    (faithful / unfaithful, with the reason) corpus for training a faithfulness checker — data no public
    autoformalizer has, because it exists only where a firewall rejects. Deduped by the canonical α-key."""
    seen: set = set()
    rows: "list[dict]" = []
    for r in nogood:
        if str(r.get("failure_class")) not in _ALTERATION_CLASSES:
            continue
        stmt = (r.get("statement") or "").strip()
        if not stmt:
            continue
        k = _akey(stmt)
        if k in seen:
            continue
        seen.add(k)
        rows.append({"statement": stmt, "label": "unfaithful", "failure_class": r.get("failure_class"),
                     "witness": (r.get("witness") or "").strip(), "source": r.get("source")})
    return rows


def export(repo: Path, out: "Path | None" = None, void_only: bool = False, all_time: bool = False,
           dedup_near: bool = False) -> dict:   # REVERTED 2026-07-02 (Gemini review B): the token-Jaccard second pass
    # DROPS logically-DISTINCT-but-textually-close pairs — `[Semiring F]`→`[Field F]`, a one-token change that FLIPS
    # the proof strategy — which are the HIGHEST-signal examples in formal math (~30% of near-misses discarded). The
    # α-equivalence `_akey` already removes genuine logical duplicates; Jaccard on top is a net LOSS. Default-OFF.
    out = out or (repo / OUT_REL)
    out.mkdir(parents=True, exist_ok=True)
    certs = _read_jsonl(repo / CERTS_REL)
    faith = _read_jsonl(repo / FAITH_REL)
    nogood = _read_jsonl(repo / NOGOOD_REL)
    pv = prover_rows(certs, void_only=void_only, all_time=all_time)
    _attach_reasoning(pv, _read_jsonl(repo / PLAN_REL))          # CoT distillation (precise, unambiguous join)
    af_raw = autoformalization_rows(faith)
    fa = falsification_rows(nogood)
    fd = faithfulness_discriminator_rows(nogood)
    # near-dup curation applies ONLY to autoformalization NL (reworded NL is genuinely redundant). It does NOT
    # touch prover/discriminator: for THEOREMS the α-key already drops logical duplicates, and layering
    # token-Jaccard on top would wrongly drop logically-DISTINCT but textually-close variants ([Semiring F] →
    # [Field F]) — the one-token shifts that flip the proof strategy, the highest-signal examples (Gemini review B).
    af = _drop_near_dups(af_raw, lambda r: r.get("nl") or "") if dedup_near else af_raw
    for name, rows in (("prover_corpus", pv), ("autoformalization_corpus", af), ("falsification_corpus", fa),
                       ("faithfulness_discriminator_corpus", fd)):
        (out / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    manifest = {"prover_pairs": len(pv), "prover_void_novel": sum(1 for r in pv if r["void_novel"]),
                "prover_with_cot": sum(1 for r in pv if r.get("reasoning")),
                "autoformalization_pairs": len(af), "falsification_pairs": len(fa),
                "faithfulness_discriminator_pairs": len(fd),
                "autoformalization_near_dups_dropped": len(af_raw) - len(af),
                "dedup_near": dedup_near, "total_distinct_pairs": len(pv) + len(af) + len(fa) + len(fd),
                "raw_closed_certs": sum(1 for c in certs if c.get("outcome") == "closed"),
                "clean_since": (None if all_time else _clean_since()), "void_only": void_only, "out_dir": str(out)}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--void-only", action="store_true", help="keep only theory-built (not-in-Mathlib) statements")
    ap.add_argument("--all-time", action="store_true", help="include pre-clean-regime closures (default: forward-looking only)")
    ap.add_argument("--dedup-near", action="store_true",
                    help="OPT-IN to the token-Jaccard second-pass dedup (default OFF — it drops high-signal "
                         "logically-distinct-but-textually-close pairs; α-key dedup is the correct default)")
    args = ap.parse_args(argv)
    m = export(REPO, args.out, void_only=args.void_only, all_time=args.all_time, dedup_near=args.dedup_near)
    print(json.dumps(m, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
