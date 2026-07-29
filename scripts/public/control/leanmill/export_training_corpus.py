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
import hashlib
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
STRICT_CERTIFICATE_SCHEMA = "leanmill.governed_closure.v2"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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
    try:
        from ztare.leanmill.result_cards import certificate_statement

        return certificate_statement(cert)
    except Exception:  # noqa: BLE001
        return ""


def _certificate_rank(cert: dict) -> tuple:
    """Prefer carried, positively governed, content-bound certificates before deduplication."""
    from ztare.leanmill.result_cards import certificate_strength_rank

    return certificate_strength_rank(cert)


def strict_certificate_rejection(cert: dict) -> str:
    """Return the first reason a closure cannot enter the release corpus.

    Historical rows remain useful for diagnostics, but missing identity cannot
    be reconstructed by the exporter.  Strict rows must carry the exact
    artifact, the solver decision that admitted it, and mutually consistent
    content bindings.
    """
    from ztare.leanmill.result_cards import certificate_is_governed

    if cert.get("certificate_schema") != STRICT_CERTIFICATE_SCHEMA:
        return "legacy_certificate_schema"
    for field in ("ts", "job_id", "run_tag", "target", "checker"):
        if not str(cert.get(field) or "").strip():
            return f"missing_{field}"
    if cert.get("recompilable_probe_reconstructed") is True:
        return "reconstructed_probe"
    if not certificate_is_governed(cert):
        return "governance_not_admitted"
    validation = cert.get("solver_validation")
    if not isinstance(validation, dict) or validation.get(
        "credit_ready_at_solver_layer"
    ) is not True:
        return "solver_credit_missing"
    receipts = validation.get("receipts")
    if not isinstance(receipts, dict):
        return "solver_receipts_missing"
    required = (
        "kernel_compile_receipt",
        "matched_negative_control_receipt",
        "governance_kernel_receipt",
        "axiom_allowlist_receipt",
    )
    for name in required:
        receipt = receipts.get(name)
        if (
            not isinstance(receipt, dict)
            or receipt.get("available") is not True
            or receipt.get("passed") is not True
        ):
            return f"{name}_not_positive"
    mnc = receipts["matched_negative_control_receipt"]
    if mnc.get("admitted_under_policy") is not True:
        return "matched_negative_control_not_admitted"
    for field in (
        "goal_sha256",
        "source_sha256",
        "recompilable_probe_sha256",
        "proof_sha256",
    ):
        if not _SHA256_RE.fullmatch(str(cert.get(field) or "")):
            return f"invalid_{field}"
    proof = str(cert.get("proof_text") or "")
    probe = str(cert.get("recompilable_probe") or "")
    if hashlib.sha256(proof.encode()).hexdigest() != cert["proof_sha256"]:
        return "proof_hash_mismatch"
    if hashlib.sha256(probe.encode()).hexdigest() != cert[
        "recompilable_probe_sha256"
    ]:
        return "probe_hash_mismatch"
    toolchain = cert.get("toolchain_identity")
    if not isinstance(toolchain, dict):
        return "missing_toolchain_identity"
    if toolchain.get("schema") != "leanmill.closure_toolchain_identity.v1":
        return "legacy_toolchain_identity"
    if toolchain.get("complete") is not True:
        return "incomplete_toolchain_identity"
    supplied_toolchain_sha = str(toolchain.get("identity_sha256") or "")
    toolchain_core = {
        key: value for key, value in toolchain.items() if key != "identity_sha256"
    }
    expected_toolchain_sha = hashlib.sha256(
        json.dumps(
            toolchain_core,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()
    if supplied_toolchain_sha != expected_toolchain_sha:
        return "toolchain_identity_hash_mismatch"
    if cert.get("kernel_parity_record_persisted") is not True:
        return "kernel_parity_not_persisted"
    if not _SHA256_RE.fullmatch(
        str(cert.get("kernel_parity_record_sha256") or "")
    ):
        return "invalid_kernel_parity_record_sha256"
    bindings = {
        "target_signature_sha256": "goal_sha256",
        "posed_source_sha256": "source_sha256",
        "closure_source_sha256": "recompilable_probe_sha256",
    }
    for receipt_field, cert_field in bindings.items():
        if mnc.get(receipt_field) != cert.get(cert_field):
            return f"mnc_{receipt_field}_mismatch"
    return ""


def strict_faithfulness_rejection(row: dict) -> str:
    if row.get("record_schema") != "leanmill.faithfulness_record.v2":
        return "legacy_faithfulness_schema"
    if row.get("evidence_tier") not in {"reviewed", "certified"}:
        return "missing_evidence_tier"
    if not isinstance(row.get("verdict_provenance"), dict) or not row[
        "verdict_provenance"
    ]:
        return "missing_verdict_provenance"
    if not isinstance(row.get("statement_id"), dict) or not row["statement_id"]:
        return "missing_statement_id"
    if not str(row.get("source") or "").strip():
        return "missing_source"
    return ""


def strict_no_good_rejection(row: dict) -> str:
    if row.get("record_schema") != "leanmill.confirmed_no_good.v2":
        return "legacy_no_good_schema"
    if row.get("confirmed") is not True:
        return "missing_confirmed_authority"
    if not isinstance(row.get("statement_id"), dict) or not row["statement_id"]:
        return "missing_statement_id"
    if not str(row.get("source") or "").strip():
        return "missing_source"
    if not str(row.get("witness") or "").strip():
        return "missing_witness"
    if row.get("failure_class") in _ALTERATION_CLASSES:
        from ztare.leanmill.solver.no_good_store import (
            validate_integrity_artifact_binding,
            validate_integrity_rejection_provenance,
        )

        if reason := validate_integrity_artifact_binding(
            row.get("artifact_binding")
        ):
            return reason
        binding = row["artifact_binding"]
        if reason := validate_integrity_rejection_provenance(
            row.get("integrity_provenance"),
            binding=binding,
            source=str(row.get("source") or ""),
            witness=str(row.get("witness") or ""),
        ):
            return reason
        try:
            from ztare.leanmill.solver import statement_integrity

            replay = statement_integrity.check(
                binding["posed_probe"],
                binding["altered_probe"],
                binding["target_selector"],
            )
        except Exception:  # noqa: BLE001 - strict export is fail-closed
            return "integrity_verdict_replay_error"
        if replay.ok is not False:
            return "altered_artifact_not_rejected"
        if str(row.get("witness") or "") not in replay.violations:
            return "integrity_witness_not_replayed"
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


def prover_rows(certs: "list[dict]", void_only: bool = False, all_time: bool = False,
                strict_provenance: bool = True) -> "list[dict]":
    """Kernel-verified (statement, proof) pairs — closed, sorry-free, deduped by α-key, noise-targets + (by default)
    pre-clean-regime rows excluded. The expert-iteration corpus."""
    seen: set = set()
    rows: "list[dict]" = []
    cutoff = _clean_since()
    # Selection happens before logical dedup: if several certificates carry the
    # same theorem, the strongest governed artifact owns the exported row.
    for c in sorted(certs, key=_certificate_rank, reverse=True):
        if c.get("outcome") != "closed":
            continue
        if strict_provenance and strict_certificate_rejection(c):
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
        statement = _target_statement(c)
        if not statement:
            continue
        void = _uses_bespoke_def(c)
        if void_only and not void:
            continue
        k = _akey(statement)
        if k in seen:
            continue
        seen.add(k)
        rows.append({"target": c.get("target"), "statement": statement,
                     "proof": proof, "recompilable_probe": probe, "substrate": c.get("substrate"),
                     "void_novel": void, "checker": c.get("checker"), "ts": c.get("ts"),
                     "job_id": c.get("job_id"),
                     "run_tag": c.get("run_tag"),
                     "goal_sha256": c.get("goal_sha256"),
                     "source_sha256": c.get("source_sha256"),
                     "proof_sha256": c.get("proof_sha256"),
                     "recompilable_probe_sha256": c.get("recompilable_probe_sha256"),
                     "authority": ("strict_forward" if strict_provenance else "legacy_diagnostic")})
    return rows


def autoformalization_rows(faith: "list[dict]", strict_provenance: bool = True) -> "list[dict]":
    """CONFIRMED-faithful (nl, lean_statement) pairs — the firewall-admitted NL↔formal correspondences."""
    seen: set = set()
    rows: "list[dict]" = []
    for r in faith:
        if r.get("kind") != "faithful":
            continue
        if strict_provenance and strict_faithfulness_rejection(r):
            continue
        nl, stmt = (r.get("nl") or "").strip(), (r.get("statement") or "").strip()
        if not nl or not stmt:
            continue
        k = (_akey(stmt), " ".join(nl.lower().split()))
        if k in seen:
            continue
        seen.add(k)
        rows.append({"nl": nl, "lean_statement": stmt, "source": r.get("source"),
                     "evidence_tier": r.get("evidence_tier"),
                     "verdict_provenance": r.get("verdict_provenance"),
                     "statement_id": r.get("statement_id"),
                     "authority": ("strict_forward" if strict_provenance else "legacy_diagnostic")})
    return rows


def falsification_rows(nogood: "list[dict]", strict_provenance: bool = True) -> "list[dict]":
    """CONFIRMED kernel-refuted (statement, refutation) pairs — teach FALSIFY (data almost no corpus has)."""
    seen: set = set()
    rows: "list[dict]" = []
    for r in nogood:
        if r.get("failure_class") != "statement_false":
            continue
        if strict_provenance and strict_no_good_rejection(r):
            continue
        stmt = (r.get("statement") or "").strip()
        if not stmt:
            continue
        k = _akey(stmt)
        if k in seen:
            continue
        seen.add(k)
        rows.append({"statement": stmt, "refutation": (r.get("witness") or r.get("distinguishing") or "").strip(),
                     "source": r.get("source"), "statement_id": r.get("statement_id"),
                     "authority": ("strict_forward" if strict_provenance else "legacy_diagnostic")})
    return rows


_ALTERATION_CLASSES = ("target_signature_altered", "definition_altered")


def faithfulness_discriminator_rows(nogood: "list[dict]", strict_provenance: bool = True) -> "list[dict]":
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
        if strict_provenance and strict_no_good_rejection(r):
            continue
        binding = r.get("artifact_binding") if strict_provenance else None
        # The rejected object is the altered Lean source.  `r.statement` stays
        # keyed to the posed goal for CEGIS and must never be exported as the
        # negative label (the historic corpus-laundering bug).
        stmt = (
            (binding or {}).get("altered_probe")
            if isinstance(binding, dict)
            else r.get("statement")
        ) or ""
        stmt = stmt.strip()
        if not stmt:
            continue
        k = (
            _akey(stmt),
            (binding or {}).get("receipt_sha256")
            if isinstance(binding, dict) else "legacy",
        )
        if k in seen:
            continue
        seen.add(k)
        rows.append({"statement": stmt, "label": "unfaithful", "failure_class": r.get("failure_class"),
                     "witness": (r.get("witness") or "").strip(), "source": r.get("source"),
                     "statement_id": (
                         (binding or {}).get("altered_statement_id")
                         if isinstance(binding, dict) else r.get("statement_id")
                     ),
                     "target_statement": (
                         (binding or {}).get("altered_target_signature")
                         if isinstance(binding, dict) else ""
                     ),
                     "target_name": (
                         (binding or {}).get("altered_target_identity")
                         if isinstance(binding, dict) else ""
                     ),
                     "posed_probe_sha256": (
                         (binding or {}).get("posed_probe_sha256")
                         if isinstance(binding, dict) else ""
                     ),
                     "altered_probe_sha256": (
                         (binding or {}).get("altered_probe_sha256")
                         if isinstance(binding, dict) else ""
                     ),
                     "artifact_binding_receipt_sha256": (
                         (binding or {}).get("receipt_sha256")
                         if isinstance(binding, dict) else ""
                     ),
                     "artifact_binding": binding,
                     "integrity_provenance": r.get("integrity_provenance"),
                     "authority": ("strict_forward" if strict_provenance else "legacy_diagnostic")})
    return rows


def export(repo: Path, out: "Path | None" = None, void_only: bool = False, all_time: bool = False,
           dedup_near: bool = False, strict_provenance: bool = True) -> dict:   # REVERTED 2026-07-02 (Gemini review B): the token-Jaccard second pass
    # DROPS logically-DISTINCT-but-textually-close pairs — `[Semiring F]`→`[Field F]`, a one-token change that FLIPS
    # the proof strategy — which are the HIGHEST-signal examples in formal math (~30% of near-misses discarded). The
    # α-equivalence `_akey` already removes genuine logical duplicates; Jaccard on top is a net LOSS. Default-OFF.
    out = out or (repo / OUT_REL)
    out.mkdir(parents=True, exist_ok=True)
    certs = _read_jsonl(repo / CERTS_REL)
    faith = _read_jsonl(repo / FAITH_REL)
    nogood = _read_jsonl(repo / NOGOOD_REL)
    pv = prover_rows(certs, void_only=void_only, all_time=all_time,
                     strict_provenance=strict_provenance)
    _attach_reasoning(pv, _read_jsonl(repo / PLAN_REL))          # CoT distillation (precise, unambiguous join)
    af_raw = autoformalization_rows(faith, strict_provenance=strict_provenance)
    fa = falsification_rows(nogood, strict_provenance=strict_provenance)
    fd = faithfulness_discriminator_rows(nogood, strict_provenance=strict_provenance)
    # near-dup curation applies ONLY to autoformalization NL (reworded NL is genuinely redundant). It does NOT
    # touch prover/discriminator: for THEOREMS the α-key already drops logical duplicates, and layering
    # token-Jaccard on top would wrongly drop logically-DISTINCT but textually-close variants ([Semiring F] →
    # [Field F]) — the one-token shifts that flip the proof strategy, the highest-signal examples (Gemini review B).
    af = _drop_near_dups(af_raw, lambda r: r.get("nl") or "") if dedup_near else af_raw
    autoformalization_near_dups_dropped = len(af_raw) - len(af)
    # A statement cannot be emitted simultaneously as proved/refuted or
    # faithful/unfaithful.  Remove both sides and expose the conflict count;
    # choosing one would make the exporter a new adjudicator.
    proved = {_akey(r["statement"]) for r in pv}
    refuted = {_akey(r["statement"]) for r in fa}
    faithful = {_akey(r["lean_statement"]) for r in af}
    unfaithful = {_akey(r["statement"]) for r in fd}
    proof_conflicts = proved & refuted
    faithfulness_conflicts = faithful & unfaithful
    if proof_conflicts:
        pv = [r for r in pv if _akey(r["statement"]) not in proof_conflicts]
        fa = [r for r in fa if _akey(r["statement"]) not in proof_conflicts]
    if faithfulness_conflicts:
        af = [r for r in af if _akey(r["lean_statement"]) not in faithfulness_conflicts]
        fd = [r for r in fd if _akey(r["statement"]) not in faithfulness_conflicts]
    output_rows = (("prover_corpus", pv), ("autoformalization_corpus", af),
                   ("falsification_corpus", fa),
                   ("faithfulness_discriminator_corpus", fd))
    corpus_sha256s = {}
    for name, rows in output_rows:
        path = out / f"{name}.jsonl"
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        corpus_sha256s[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {"prover_pairs": len(pv), "prover_void_novel": sum(1 for r in pv if r["void_novel"]),
                "prover_with_cot": sum(1 for r in pv if r.get("reasoning")),
                "autoformalization_pairs": len(af), "falsification_pairs": len(fa),
                "faithfulness_discriminator_pairs": len(fd),
                "autoformalization_near_dups_dropped": autoformalization_near_dups_dropped,
                "dedup_near": dedup_near, "total_distinct_pairs": len(pv) + len(af) + len(fa) + len(fd),
                "authority": ("strict_forward" if strict_provenance else "legacy_diagnostic"),
                "corpus_sha256s": corpus_sha256s,
                "proof_refutation_conflicts_excluded": len(proof_conflicts),
                "faithfulness_conflicts_excluded": len(faithfulness_conflicts),
                "prover_provenance_excluded": sum(
                    bool(strict_certificate_rejection(c)) for c in certs
                    if c.get("outcome") == "closed"
                ) if strict_provenance else 0,
                "faithfulness_provenance_excluded": sum(
                    bool(strict_faithfulness_rejection(r)) for r in faith
                    if r.get("kind") == "faithful"
                ) if strict_provenance else 0,
                "no_good_provenance_excluded": sum(
                    bool(strict_no_good_rejection(r)) for r in nogood
                    if r.get("failure_class") == "statement_false"
                    or r.get("failure_class") in _ALTERATION_CLASSES
                ) if strict_provenance else 0,
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
    ap.add_argument("--legacy-diagnostic", action="store_true",
                    help="include legacy rows lacking forward identity; output is labelled diagnostic and is not training-admissible")
    args = ap.parse_args(argv)
    m = export(REPO, args.out, void_only=args.void_only, all_time=args.all_time,
               dedup_near=args.dedup_near, strict_provenance=not args.legacy_diagnostic)
    print(json.dumps(m, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
