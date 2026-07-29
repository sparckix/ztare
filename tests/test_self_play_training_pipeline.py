from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

from ztare.leanmill.ratification_policy import (
    TARGET_GOVERNANCE_AUTHORITIES,
    TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256,
)
from ztare.leanmill.solver.closed_artifact import finalize_solver_validation


REPO = Path(__file__).resolve().parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_self_play_split_resolves_qualified_namespace_target():
    self_play = _load(
        "self_play_conjecturer_test_split",
        "scripts/public/control/leanmill/self_play_conjecturer.py",
    )
    source = """import Mathlib

namespace Deck
def localObject (n : Nat) := n + 1

theorem seed (n : Nat) : localObject n = n + 1 := by
  rfl
end Deck
"""

    split = self_play._split_probe(source, "Deck.seed")

    assert split is not None
    preamble, signature, block = split
    assert "def localObject" in preamble
    assert "theorem seed" not in preamble
    assert signature == "(n : Nat) : localObject n = n + 1"
    assert block.lstrip().startswith("theorem seed")


def test_self_play_gate_rejects_cheap_tactic_closure(tmp_path):
    self_play = _load(
        "self_play_conjecturer_test_gate",
        "scripts/public/control/leanmill/self_play_conjecturer.py",
    )
    probe = "import Mathlib\n\ntheorem candidate (n : Nat) : n + 0 = n := by sorry\n"
    calls = []

    def compile_fn(source, _root, *, timeout, reject_sorry):
        calls.append((source, timeout, reject_sorry))
        return True, "ok"

    ok, reason = self_play.gate(
        probe,
        "candidate",
        "(n : Nat) : n + 0 = n",
        set(),
        tmp_path,
        compile_fn=compile_fn,
        nondegenerate_probe_fn=lambda *_a, **_k: {"vacuity_confirmed": False},
    )

    assert ok is False
    assert "cheap tactic" in reason
    assert [row[2] for row in calls] == [False, True]


def test_self_play_gate_fails_closed_when_vacuity_probe_crashes(tmp_path):
    self_play = _load(
        "self_play_conjecturer_test_fail_closed",
        "scripts/public/control/leanmill/self_play_conjecturer.py",
    )
    probe = "import Mathlib\n\ntheorem candidate (n : Nat) : n + 0 = n := by sorry\n"
    count = 0

    def compile_fn(_source, _root, *, timeout, reject_sorry):
        nonlocal count
        count += 1
        return (True, "ok") if count == 1 else (False, "unsolved goals")

    def unavailable(*_args, **_kwargs):
        raise RuntimeError("instrument unavailable")

    ok, reason = self_play.gate(
        probe,
        "candidate",
        "(n : Nat) : n + 0 = n",
        set(),
        tmp_path,
        compile_fn=compile_fn,
        nondegenerate_probe_fn=unavailable,
    )

    assert ok is False
    assert "non-triviality probe unavailable" in reason


def test_self_play_gate_fails_closed_when_cheap_compile_has_no_verdict(tmp_path):
    self_play = _load(
        "self_play_conjecturer_test_no_cheap_verdict",
        "scripts/public/control/leanmill/self_play_conjecturer.py",
    )
    probe = """import Mathlib

def LocalCarrier (n : Nat) := n
theorem candidate (n : Nat) : LocalCarrier n = n := by sorry
"""
    calls = []

    def compile_fn(source, _root, *, timeout, reject_sorry):
        calls.append((source, timeout, reject_sorry))
        return (True, "ok") if len(calls) == 1 else None

    ok, reason = self_play.gate(
        probe,
        "candidate",
        "(n : Nat) : LocalCarrier n = n",
        set(),
        tmp_path,
        compile_fn=compile_fn,
        nondegenerate_probe_fn=lambda *_a, **_k: {"vacuity_confirmed": False},
    )

    assert ok is False
    assert "cheap compile returned no verdict" in reason
    assert [row[2] for row in calls] == [False, True]


def test_self_play_kept_closure_requires_governance_and_exact_certificate_record():
    self_play = _load(
        "self_play_conjecturer_test_ratified_receipt",
        "scripts/public/control/leanmill/self_play_conjecturer.py",
    )
    closed = {
        "results": [{"outcome": "closed", "proof_text": "by rfl"}],
        "closure_certificate": "analytics/public/queries/adhoc_closure_certificates.jsonl",
        "closure_certificate_record_sha256": "a" * 64,
        "governance_ratification_eligible": True,
    }

    assert self_play._ratified_closure_receipt(closed) == ("by rfl", "a" * 64)
    assert self_play._ratified_closure_receipt({
        **closed,
        "governance_ratification_eligible": False,
    }) is None
    assert self_play._ratified_closure_receipt({
        **closed,
        "closure_certificate_record_sha256": "",
    }) is None


def test_gold_name_gate_does_not_treat_local_hypothesis_projection_as_library_gold():
    from ztare.gates.v33_paraphrase_gate import detect_gold_name_verbatim

    source = """import Mathlib
theorem transfer_seed_sp {α : Type*} [PartialOrder α] {a b c : α}
    (h₁ : a ≤ b) (h₂ : b ≤ c) : a ≤ c := by
  exact h₁.trans h₂
"""

    receipt = detect_gold_name_verbatim(source)

    assert receipt["distinct_cited_lemmas"] == []
    assert receipt["gold_name_verbatim_suspect"] is False


def test_export_prefers_carried_governed_certificate():
    exporter = _load(
        "export_training_corpus_test",
        "scripts/public/control/leanmill/export_training_corpus.py",
    )
    probe = """import Mathlib
namespace Deck
theorem seed (n : Nat) : n = n := by rfl
end Deck
"""
    weak = {
        "ts": "2026-07-17T00:00:00+00:00",
        "target": "Deck.seed",
        "outcome": "closed",
        "proof_text": "by exact Eq.refl _",
        "recompilable_probe": probe,
        "recompilable_probe_reconstructed": True,
    }
    proof = "by rfl"
    goal_sha = hashlib.sha256(b"(n : Nat) : n = n").hexdigest()
    source_sha = hashlib.sha256(b"posed source").hexdigest()
    probe_sha = hashlib.sha256(probe.encode()).hexdigest()
    signature_sha = hashlib.sha256(b"(n : Nat) : n = n").hexdigest()
    toolchain_core = {
        "schema": "leanmill.closure_toolchain_identity.v1",
        "project": "proofs",
        "lean_toolchain": "leanprover/lean4:v4.30.0-rc2",
        "lean_toolchain_sha256": hashlib.sha256(
            b"leanprover/lean4:v4.30.0-rc2"
        ).hexdigest(),
        "lean_version": "Lean (version 4.30.0-rc2)",
        "lean_version_sha256": hashlib.sha256(
            b"Lean (version 4.30.0-rc2)"
        ).hexdigest(),
        "project_file_sha256s": {"lean-toolchain": "a" * 64},
        "package_revisions": {},
        "complete": True,
    }
    toolchain = {
        **toolchain_core,
        "identity_sha256": hashlib.sha256(
            json.dumps(
                toolchain_core,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode()
        ).hexdigest(),
    }
    governance = {
        "probe_match": "carried_exact_artifact",
        "governance_kernel": {
            "available": True,
            "passed": True,
            "policy_profile": "target_ratification",
            "required_authorities": sorted(TARGET_GOVERNANCE_AUTHORITIES),
            "authority_disposition": {
                authority: "passed"
                for authority in TARGET_GOVERNANCE_AUTHORITIES
            },
            "authority_roster_sha256": (
                TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256
            ),
        },
        "statement_integrity": {"ok": True},
    }
    validation = finalize_solver_validation({
        "credit_ready_at_solver_layer": True,
        "positive_axiom_receipt_required": True,
        "discriminating_mnc_required": True,
        "receipts": {
            "kernel_compile_receipt": {"available": True, "passed": True},
            "matched_negative_control_receipt": {
                "available": True,
                "passed": True,
                "admitted_under_policy": True,
                "target_signature_sha256": goal_sha,
                "posed_source_sha256": source_sha,
                "closure_source_sha256": probe_sha,
            },
            "governance_kernel_receipt": {
                "available": True,
                "passed": True,
            },
            "axiom_allowlist_receipt": {"available": True, "passed": True},
        },
    }, governance)
    strong = {
        **weak,
        "certificate_schema": "leanmill.governed_closure.v2",
        "ts": "2026-07-17T00:01:00+00:00",
        "job_id": "attempt-row-1",
        "run_tag": "run-1",
        "checker": "lean_lake",
        "proof_text": proof,
        "recompilable_probe_reconstructed": False,
        "goal_sha256": goal_sha,
        "source_sha256": source_sha,
        "recompilable_probe_sha256": probe_sha,
        "proof_sha256": hashlib.sha256(proof.encode()).hexdigest(),
        "posed_target_signature_sha256": signature_sha,
        "closed_target_signature_sha256": signature_sha,
        "toolchain_identity": toolchain,
        "kernel_parity_record_sha256": "b" * 64,
        "kernel_parity_record_persisted": True,
        "solver_validation": validation,
        "governance": governance,
        "matched_negative_control": {"available": True, "passed": True},
    }

    rows = exporter.prover_rows([weak, strong], all_time=True)

    assert len(rows) == 1
    assert rows[0]["statement"] == "(n : Nat) : n = n"
    assert rows[0]["proof"] == "by rfl"
    assert rows[0]["recompilable_probe_sha256"] == probe_sha
    assert rows[0]["authority"] == "strict_forward"


def test_export_legacy_rows_are_diagnostic_only():
    exporter = _load(
        "export_training_corpus_test_legacy",
        "scripts/public/control/leanmill/export_training_corpus.py",
    )
    legacy = {
        "ts": "2026-07-17T00:00:00+00:00",
        "target": "seed",
        "outcome": "closed",
        "proof_text": "by rfl",
        "recompilable_probe": "import Mathlib\ntheorem seed : True := by trivial\n",
    }

    assert exporter.prover_rows([legacy], all_time=True) == []
    rows = exporter.prover_rows(
        [legacy], all_time=True, strict_provenance=False
    )
    assert len(rows) == 1
    assert rows[0]["authority"] == "legacy_diagnostic"


def test_export_forward_faithfulness_and_no_good_authority():
    exporter = _load(
        "export_training_corpus_test_authority",
        "scripts/public/control/leanmill/export_training_corpus.py",
    )
    faithful = {
        "record_schema": "leanmill.faithfulness_record.v2",
        "kind": "faithful",
        "nl": "Every number equals itself.",
        "statement": "theorem seed (n : Nat) : n = n := by sorry",
        "source": "firewall_admit",
        "evidence_tier": "reviewed",
        "verdict_provenance": {"method": "firewall_roundtrip_review"},
        "statement_id": {"digest": "faithful"},
    }
    from ztare.leanmill.solver.no_good_store import (
        build_integrity_artifact_binding,
        build_integrity_rejection_provenance,
    )

    posed_probe = "import Mathlib\n\ntheorem bad : True := by sorry\n"
    altered_probe = "import Mathlib\n\ntheorem bad : False := by sorry\n"
    binding = build_integrity_artifact_binding(
        posed_probe, altered_probe, "bad"
    )
    assert binding is not None
    from ztare.leanmill.solver import statement_integrity
    integrity_witness = statement_integrity.check(
        posed_probe, altered_probe, "bad"
    ).violations[0]
    provenance = build_integrity_rejection_provenance(
        binding,
        source="statement_integrity",
        witness=integrity_witness,
    )
    assert provenance is not None
    no_good = {
        "record_schema": "leanmill.confirmed_no_good.v2",
        "failure_class": "target_signature_altered",
        "statement": posed_probe,
        "witness": integrity_witness,
        "source": "statement_integrity",
        "confirmed": True,
        "statement_id": {"digest": "bad"},
        "artifact_binding": binding,
        "integrity_provenance": provenance,
    }

    assert len(exporter.autoformalization_rows([faithful])) == 1
    discriminator = exporter.faithfulness_discriminator_rows([no_good])
    assert len(discriminator) == 1
    assert discriminator[0]["statement"] == altered_probe.strip()
    assert discriminator[0]["target_statement"] == ": False"
    assert discriminator[0]["altered_probe_sha256"] == hashlib.sha256(
        altered_probe.encode()
    ).hexdigest()
    assert discriminator[0]["artifact_binding_receipt_sha256"] == binding[
        "receipt_sha256"
    ]
    assert discriminator[0]["integrity_provenance"] == provenance
    assert exporter.autoformalization_rows([
        {key: value for key, value in faithful.items() if key != "verdict_provenance"}
    ]) == []
    assert exporter.faithfulness_discriminator_rows([
        {key: value for key, value in no_good.items() if key != "confirmed"}
    ]) == []
    tampered = json.loads(json.dumps(no_good))
    tampered["artifact_binding"]["altered_probe"] = altered_probe.replace(
        "False", "True"
    )
    assert exporter.faithfulness_discriminator_rows([tampered]) == []


def test_integrity_no_good_binds_exact_altered_artifact(tmp_path):
    from ztare.leanmill.solver import statement_integrity
    from ztare.leanmill.solver.no_good_store import (
        NoGoodStore,
        validate_integrity_artifact_binding,
    )

    posed = """import Mathlib

def localValue : Nat := 0
theorem target : localValue = 0 := by sorry
"""
    altered = """import Mathlib

def localValue : Nat := 1
theorem target : localValue = 1 := by rfl
"""
    verdict = statement_integrity.check(posed, altered, "target")
    assert verdict.ok is False
    store_path = tmp_path / "no_good.jsonl"
    store = NoGoodStore(store_path)

    assert store.record_integrity_verdict(
        "theorem target : localValue = 0",
        verdict,
        source="forward_integrity_gate",
        posed_probe=posed,
        altered_probe=altered,
        target_name="target",
    ) >= 1

    rows = [json.loads(line) for line in store_path.read_text().splitlines()]
    bound = [row for row in rows if row.get("artifact_binding")]
    assert bound
    binding = bound[0]["artifact_binding"]
    assert validate_integrity_artifact_binding(binding) == ""
    assert binding["posed_probe"] == posed
    assert binding["altered_probe"] == altered
    assert binding["posed_target_signature"] == ": localValue = 0"
    assert binding["altered_target_signature"] == ": localValue = 1"


def test_forward_store_records_can_supersede_legacy_identity(tmp_path):
    from ztare.leanmill.solver.faithfulness_store import FaithfulnessStore, nl_key
    from ztare.leanmill.solver.no_good_store import NoGoodStore
    from ztare.leanmill.solver.proof_cache import _key_for

    nl = "Every number equals itself."
    statement = "theorem seed (n : Nat) : n = n := by sorry"
    faith_path = tmp_path / "faith.jsonl"
    faith_path.write_text(json.dumps({
        "key": nl_key(nl), "kind": "faithful", "nl": nl,
        "statement": statement, "evidence_tier": "reviewed",
    }) + "\n", encoding="utf-8")
    faith = FaithfulnessStore(faith_path)
    assert faith.record(
        nl, statement, confirmed=True, source="firewall_admit",
        evidence_tier="reviewed",
        verdict_provenance={"method": "firewall_roundtrip_review"},
    )

    witness = "target_signature_altered: changed conclusion"
    no_good_path = tmp_path / "no_good.jsonl"
    no_good_path.write_text(json.dumps({
        "key": _key_for(statement), "statement": statement,
        "failure_class": "target_signature_altered", "witness": witness,
        "source": "legacy",
    }) + "\n", encoding="utf-8")
    no_good = NoGoodStore(no_good_path)
    assert no_good.record(
        statement, "target_signature_altered", witness,
        confirmed=True, source="statement_integrity",
    )

    faith_rows = [json.loads(line) for line in faith_path.read_text().splitlines()]
    no_good_rows = [json.loads(line) for line in no_good_path.read_text().splitlines()]
    assert faith_rows[-1]["record_schema"] == "leanmill.faithfulness_record.v2"
    assert no_good_rows[-1]["record_schema"] == "leanmill.confirmed_no_good.v2"


def test_training_consumer_refuses_unlabelled_legacy_corpus(tmp_path):
    from ztare.leanmill.training_corpus_contract import (
        validate_training_corpus_directory,
    )

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "prover_corpus.jsonl").write_text("{}\n", encoding="utf-8")
    with __import__("pytest").raises(ValueError, match="no authority manifest"):
        validate_training_corpus_directory(
            corpus, required_files=("prover_corpus.jsonl",)
        )
    diagnostic = validate_training_corpus_directory(
        corpus,
        required_files=("prover_corpus.jsonl",),
        allow_legacy_diagnostic=True,
    )
    assert diagnostic["authority"] == "legacy_diagnostic"


def test_strict_export_manifest_binds_consumer_bytes(tmp_path):
    exporter = _load(
        "export_training_corpus_test_contract",
        "scripts/public/control/leanmill/export_training_corpus.py",
    )
    from ztare.leanmill.training_corpus_contract import (
        validate_training_corpus_directory,
    )

    for relative in (
        exporter.CERTS_REL,
        exporter.FAITH_REL,
        exporter.NOGOOD_REL,
        exporter.PLAN_REL,
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    corpus = tmp_path / "strict"
    exporter.export(tmp_path, out=corpus, all_time=True)
    receipt = validate_training_corpus_directory(
        corpus, required_files=("prover_corpus.jsonl",)
    )
    assert receipt["authority"] == "strict_forward"

    (corpus / "prover_corpus.jsonl").write_text("{}\n", encoding="utf-8")
    with __import__("pytest").raises(ValueError, match="bytes changed identity"):
        validate_training_corpus_directory(
            corpus, required_files=("prover_corpus.jsonl",)
        )


def test_export_rejects_reconstructed_declaration_without_proof_delimiter():
    exporter = _load(
        "export_training_corpus_test_malformed",
        "scripts/public/control/leanmill/export_training_corpus.py",
    )
    malformed = {
        "ts": "2026-07-17T00:00:00+00:00",
        "target": "Deck.seed",
        "outcome": "closed",
        "proof_text": "by rfl",
        "recompilable_probe": """import Mathlib
namespace Deck
theorem seed (n : Nat) : n = n
by
  rfl
end Deck
""",
    }

    assert exporter._target_statement(malformed) == ""
    assert exporter.prover_rows([malformed], all_time=True) == []


def _prove_row(target: str, probe: str, statement: str) -> dict:
    return {
        "task": "prove",
        "target": target,
        "prompt": f"Prove the following Lean theorem.\n\n{statement}",
        "probe": probe,
        "completion": " by rfl",
    }


def test_holdout_family_is_transitive_and_statement_keyed():
    formatter = _load(
        "format_corpus_test_family",
        "scripts/public/models/void_sft/format_corpus.py",
    )
    rows = [
        _prove_row(
            "same",
            "import Mathlib\ndef SharedA (n : Nat) := n\ntheorem same : SharedA 0 = 0 := by rfl",
            ": SharedA 0 = 0",
        ),
        _prove_row(
            "bridge",
            "import Mathlib\ndef SharedA (n : Nat) := n\ndef SharedB (n : Nat) := n\n"
            "theorem bridge : SharedA 0 = SharedB 0 := by rfl",
            ": SharedA 0 = SharedB 0",
        ),
        _prove_row(
            "same",
            "import Mathlib\ndef SharedB (n : Nat) := n\ntheorem same : SharedB 1 = 1 := by rfl",
            ": SharedB 1 = 1",
        ),
    ]

    families = formatter.content_family_map(rows)
    ids = [formatter._row_identity(row) for row in rows]

    assert len(set(ids)) == 3
    assert len({families[row_id] for row_id in ids}) == 1


def test_holdout_groups_pure_mathlib_name_siblings_and_near_duplicates():
    formatter = _load(
        "format_corpus_test_siblings",
        "scripts/public/models/void_sft/format_corpus.py",
    )
    sibling_a = _prove_row(
        "route_conj1",
        "import Mathlib\ntheorem route_conj1 (n : Nat) : n = n := by rfl",
        "(n : Nat) : n = n",
    )
    sibling_b = _prove_row(
        "route_conj2",
        "import Mathlib\ntheorem route_conj2 (n : Nat) : n = n := by rfl",
        "(n : Nat) : n = n",
    )
    families = formatter.content_family_map([sibling_a, sibling_b])

    assert families[formatter._row_identity(sibling_a)] == families[formatter._row_identity(sibling_b)]


def test_family_holdout_has_no_definition_or_near_duplicate_leak():
    formatter = _load(
        "format_corpus_test_split",
        "scripts/public/models/void_sft/format_corpus.py",
    )
    rows = [
        _prove_row(
            "alpha1",
            "import Mathlib\ndef Alpha (n : Nat) := n\ntheorem alpha1 : Alpha 0 = 0 := by rfl",
            ": Alpha 0 = 0",
        ),
        _prove_row(
            "alpha2",
            "import Mathlib\ndef Alpha (n : Nat) := n\ntheorem alpha2 : Alpha 1 = 1 := by rfl",
            ": Alpha 1 = 1",
        ),
        _prove_row(
            "beta1",
            "import Mathlib\ndef Beta (n : Nat) := n + 2\ntheorem beta1 : Beta 0 = 2 := by rfl",
            ": Beta 0 = 2",
        ),
        _prove_row(
            "gamma1",
            "import Mathlib\ndef Gamma (n : Nat) := n + 3\ntheorem gamma1 : Gamma 0 = 3 := by rfl",
            ": Gamma 0 = 3",
        ),
    ]

    train, evaluation = formatter.split_family_holdout(rows, min_eval=1)

    assert train and evaluation
    alpha_sides = {
        "eval" if row in evaluation else "train"
        for row in rows
        if row["target"].startswith("alpha")
    }
    assert len(alpha_sides) == 1


def test_family_holdout_manifest_binds_policy_leakage_and_output_bytes(tmp_path):
    formatter = _load(
        "format_corpus_test_receipt",
        "scripts/public/models/void_sft/format_corpus.py",
    )
    train = [_prove_row(
        "alpha",
        "import Mathlib\ndef Alpha (n : Nat) := n\ntheorem alpha : Alpha 0 = 0 := by rfl",
        ": Alpha 0 = 0",
    )]
    evaluation = [_prove_row(
        "beta",
        "import Mathlib\ndef Beta (n : Nat) := n + 1\ntheorem beta : Beta 0 = 1 := by rfl",
        ": Beta 0 = 1",
    )]
    for name, rows in (
        ("sft_train.jsonl", train),
        ("sft_eval.jsonl", evaluation),
    ):
        (tmp_path / name).write_text(
            "".join(formatter.json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )
    (tmp_path / "holdout_eval.json").write_text(
        formatter.json.dumps(evaluation), encoding="utf-8"
    )
    leakage = formatter._with_receipt({
        "schema": "leanmill.content_family_holdout_receipt.v1",
        **formatter.holdout_leakage_metrics(train, evaluation),
        "authority": "deterministic_dataset_splitter",
    })
    core = {
        "schema": "leanmill.void_sft_format_manifest.v2",
        "corpus_sha256": "a" * 64,
        "split_policy": {
            "id": "content_family_holdout",
            "version": 2,
            "minimum_proof_eval_rows": 1,
        },
        "leakage_receipt": leakage,
        "output_sha256s": {
            name: formatter._sha256_path(tmp_path / name)
            for name in ("sft_train.jsonl", "sft_eval.jsonl", "holdout_eval.json")
        },
        "total": 2,
        "train": 1,
        "eval": 1,
        "by_task": {"prove": 2},
        "train_by_task": {"prove": 1},
        "eval_by_task": {"prove": 1},
    }
    manifest = formatter._with_receipt(core)
    (tmp_path / "format_manifest.json").write_text(
        formatter.json.dumps(manifest), encoding="utf-8"
    )

    assert formatter.verify_format_manifest(tmp_path) == manifest
    (tmp_path / "sft_train.jsonl").write_text("{}\n", encoding="utf-8")
    try:
        formatter.verify_format_manifest(tmp_path)
    except ValueError as exc:
        assert "changed identity" in str(exc)
    else:
        raise AssertionError("mutated training bytes were accepted")
