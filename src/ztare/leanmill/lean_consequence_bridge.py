"""Conditional Lean tasks for lifting bounded theory consequences."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ztare.leanmill import lean_source
from ztare.leanmill.contracts.kernel import SolveResult
from ztare.leanmill.contracts.work_items import WorkItem, WorkReceipt
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    LeanLoweringConfig,
    TheorySignature,
    content_hash,
    lower_conditional_pack_to_lean,
    render_formula_to_lean,
)


CompileFn = Callable[[str], bool | None]
GovernedSolveFn = Callable[..., Mapping[str, Any]]


def _normalized_proof_text(value: str) -> str:
    proof = str(value or "").strip()
    if not proof.startswith("```"):
        return proof
    from ztare.leanmill.solver.agent_output import fenced_block

    return (
        fenced_block(proof, "", lang="lean")
        or fenced_block(proof, "")
        or proof
    ).strip()


@dataclass(frozen=True)
class LeanConsequenceTask:
    task_id: str
    target_name: str
    signature_hash: str
    premise_hashes: tuple[str, ...]
    target_hash: str
    source_with_hole: str
    signature: TheorySignature
    premises: tuple[AxiomFormula, ...]
    target: AxiomFormula
    base_axioms: tuple[AxiomFormula, ...] = ()
    schema: str = "leanmill.lean_consequence_task.v1"

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "task_id": self.task_id,
            "target_name": self.target_name,
            "signature_hash": self.signature_hash,
            "premise_hashes": list(self.premise_hashes),
            "target_hash": self.target_hash,
            "source_with_hole": self.source_with_hole,
            "work_item": self.to_work_item().model_dump(),
        }

    def to_work_item(self) -> WorkItem:
        signature = lean_source.extract_signature(self.source_with_hole, self.target_name)
        return WorkItem(
            kind="theorem_goal",
            statement=signature,
            residual_class="axiompack_frontier_consequence",
            patterns=["conditional_theory_lift"],
            anti_patterns=["global_axiom", "premise_independent_proof"],
            consumer_check="full/empty/leave-one-out replay must attribute the proof",
            campaign=self.task_id,
        )


@dataclass(frozen=True)
class LeanConsequenceAttempt:
    task_id: str
    status: str
    kernel_checked: bool
    source_digest: str
    proof_text: str
    reason: str = ""
    schema: str = "leanmill.lean_consequence_attempt.v1"

    def to_json(self) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "task_id": self.task_id,
            "status": self.status,
            "kernel_checked": self.kernel_checked,
            "source_digest": self.source_digest,
            "proof_text": self.proof_text,
            "reason": self.reason,
        }
        return {**core, "receipt_sha256": content_hash(core)}


@dataclass(frozen=True)
class GovernedLeanConsequenceAttempt:
    task_id: str
    status: str
    proof_text: str
    solver_result_digest: str
    attribution: Mapping[str, Any] | None
    work_receipt: Mapping[str, Any]
    refutation: Mapping[str, Any] | None = None
    reason: str = ""
    schema: str = "leanmill.governed_consequence_attempt.v1"

    def to_json(self) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "task_id": self.task_id,
            "status": self.status,
            "proof_text": self.proof_text,
            "solver_result_digest": self.solver_result_digest,
            "attribution": dict(self.attribution) if self.attribution is not None else None,
            "work_receipt": dict(self.work_receipt),
            "refutation": dict(self.refutation) if self.refutation is not None else None,
            "reason": self.reason,
        }
        return {**core, "receipt_sha256": content_hash(core)}


def render_lean_consequence_task(
    signature: TheorySignature,
    premises: Sequence[AxiomFormula],
    target: AxiomFormula,
    *,
    base_axioms: Sequence[AxiomFormula] = (),
) -> LeanConsequenceTask:
    config = LeanLoweringConfig()
    lowered = lower_conditional_pack_to_lean(
        signature, tuple(premises), base_axioms=tuple(base_axioms), config=config
    )
    # This boundary certifies finite/small models. Keeping the quantified
    # carriers in ``Type`` lets an explicit finite countermodel refute the
    # generated proposition directly; universe polymorphism belongs to a
    # later transport theorem, not to finite-theory adjudication.
    sort_params = " ".join(f"({row.name} : Type)" for row in signature.sorts)
    sort_args = " ".join(row.name for row in signature.sorts)
    nonempty = "".join(f" [Nonempty {row.name}]" for row in signature.sorts)
    signature_class = f"{config.namespace}.{signature.name}Signature"
    pack_class = f"{config.namespace}.{config.pack_class}"
    base_class = f"{config.namespace}.{config.base_class}"
    base_instance = f" [{base_class} {sort_args}]" if base_axioms else ""
    goal = render_formula_to_lean(signature, target.formula, signature_class=signature_class)
    identity = {
        "signature_hash": signature.content_hash,
        "premise_hashes": [row.semantic_hash for row in premises],
        "base_hashes": [row.semantic_hash for row in base_axioms],
        "target_hash": target.semantic_hash,
    }
    target_name = "axiompack_consequence_" + content_hash(identity).split(":")[-1][:16]
    theorem = (
        f"theorem {target_name} {sort_params} [{signature_class} {sort_args}]"
        f"{nonempty}{base_instance} [{pack_class} {sort_args}] : {goal} := by\n"
        "  sorry -- AXIOMPACK_PROOF"
    )
    source = "import Mathlib\n\n" + lowered + "\n" + theorem
    core = {**identity, "target_name": target_name, "source_with_hole": source}
    return LeanConsequenceTask(
        task_id="lean-consequence:" + content_hash(core),
        target_name=target_name,
        signature_hash=signature.content_hash,
        premise_hashes=tuple(row.semantic_hash for row in premises),
        target_hash=target.semantic_hash,
        source_with_hole=source,
        signature=signature,
        premises=tuple(premises),
        target=target,
        base_axioms=tuple(base_axioms),
    )


def check_lean_consequence_proof(
    task: LeanConsequenceTask,
    proof_text: str,
    *,
    compile_fn: CompileFn,
) -> LeanConsequenceAttempt:
    proof = _normalized_proof_text(proof_text)
    if not proof:
        return LeanConsequenceAttempt(task.task_id, "unresolved", False, "", "", "empty proof")
    marker = "  sorry -- AXIOMPACK_PROOF"
    if task.source_with_hole.count(marker) != 1:
        return LeanConsequenceAttempt(
            task.task_id, "invalid", False, "", proof, "proof marker is not unique"
        )
    head, tail = task.source_with_hole.split(marker, 1)
    source = lean_source.attach_proof(head.rstrip(), proof) + tail
    digest = content_hash({"lean_source": source})
    if lean_source.has_sorry(source) or any(
        lean_source.decl_kind(block) == "axiom" for _name, block in lean_source.decl_blocks(source)
    ):
        return LeanConsequenceAttempt(
            task.task_id, "invalid", False, digest, proof, "forbidden axiom or sorry"
        )
    try:
        checked = compile_fn(source)
    except Exception as exc:  # noqa: BLE001
        return LeanConsequenceAttempt(
            task.task_id, "unresolved", False, digest, proof, f"compiler:{type(exc).__name__}"
        )
    return LeanConsequenceAttempt(
        task.task_id,
        "proved" if checked is True else "refuted_by_kernel" if checked is False else "unresolved",
        checked is True,
        digest,
        proof,
        "" if checked is not None else "compiler unavailable",
    )


def matched_proof_attribution(
    signature: TheorySignature,
    premises: Sequence[AxiomFormula],
    target: AxiomFormula,
    proof_text: str,
    *,
    compile_fn: CompileFn,
    base_axioms: Sequence[AxiomFormula] = (),
    prechecked_full: LeanConsequenceAttempt | None = None,
) -> dict[str, Any]:
    """Replay identical proof bytes under full, empty, and leave-one-out packs."""
    arms: dict[str, dict[str, Any]] = {}
    proof_text = _normalized_proof_text(proof_text)
    subsets = [("full", tuple(premises)), ("empty", ())]
    subsets.extend(
        (f"without:{premise.semantic_hash}", tuple(row for row in premises if row != premise))
        for premise in premises
    )
    for label, subset in subsets:
        task = render_lean_consequence_task(signature, subset, target, base_axioms=base_axioms)
        attempt = (
            prechecked_full
            if label == "full" and prechecked_full is not None
            else check_lean_consequence_proof(task, proof_text, compile_fn=compile_fn)
        )
        arms[label] = {
            "premise_hashes": list(task.premise_hashes),
            "status": attempt.status,
            "kernel_checked": attempt.kernel_checked,
            "source_digest": attempt.source_digest,
        }
    core = {
        "schema": "leanmill.matched_consequence_attribution.v1",
        "target_hash": target.semantic_hash,
        "proof_digest": content_hash({"proof_text": proof_text}),
        "arms": arms,
    }
    return {**core, "receipt_sha256": content_hash(core)}


def recheck_governed_lean_consequence(
    task: LeanConsequenceTask,
    proof_text: str,
    *,
    compile_fn: CompileFn,
    generic_solver_outcome: str = "rejected_banned_axiom",
    solver_entry: str = (
        "ztare.leanmill.lean_consequence_bridge.recheck_governed_lean_consequence"
    ),
) -> GovernedLeanConsequenceAttempt:
    """Apply premise-aware governance to saved proof bytes without a model call."""

    proof = _normalized_proof_text(proof_text)
    full_attempt = check_lean_consequence_proof(task, proof, compile_fn=compile_fn)
    attribution: Mapping[str, Any] | None = None
    if full_attempt.status == "proved" and full_attempt.kernel_checked:
        attribution = matched_proof_attribution(
            task.signature,
            task.premises,
            task.target,
            proof,
            compile_fn=compile_fn,
            base_axioms=task.base_axioms,
            prechecked_full=full_attempt,
        )
        full = attribution["arms"]["full"]
        negatives = [
            arm
            for label, arm in attribution["arms"].items()
            if label == "empty" or label.startswith("without:")
        ]
        status = (
            "proved_attributed"
            if full["status"] == "proved"
            and full["kernel_checked"] is True
            and all(arm["status"] != "proved" for arm in negatives)
            else "proved_unattributed"
        )
        verdict = "completed"
        reason = "premise-aware full/empty/leave-one-out kernel replay"
    else:
        status = full_attempt.status
        verdict = "rejected" if full_attempt.status == "invalid" else "gap"
        reason = full_attempt.reason or full_attempt.status
    work_receipt = WorkReceipt(
        item=task.to_work_item(),
        verdict=verdict,
        formal_leg={
            "solver_entry": solver_entry,
            "generic_solver_outcome": generic_solver_outcome,
            "outcome": status,
            "credit_ready": status == "proved_attributed",
            "closure_certificate": None,
            "attribution_ref": (
                attribution.get("receipt_sha256") if attribution is not None else None
            ),
        },
        gap_text="" if verdict == "completed" else reason,
    ).model_dump()
    return GovernedLeanConsequenceAttempt(
        task_id=task.task_id,
        status=status,
        proof_text=proof,
        solver_result_digest=content_hash(
            {
                "generic_solver_outcome": generic_solver_outcome,
                "proof_text": proof,
                "full_source_digest": full_attempt.source_digest,
            }
        ),
        attribution=attribution,
        work_receipt=work_receipt,
        reason=reason,
    )


def execute_governed_lean_consequence(
    task: LeanConsequenceTask,
    *,
    substrate: str | Path,
    timeout_s: int,
    compile_fn: CompileFn,
    solve_fn: GovernedSolveFn | None = None,
    notes: str = "",
) -> GovernedLeanConsequenceAttempt:
    """Solve the full arm through LeanMill, then replay identical proof bytes."""

    if solve_fn is None:
        from ztare.leanmill.solver.conjecture import (
            adjudicate_statement_false_verdict,
            confirmed_refutation_verdict,
            recover_saved_refutation,
        )

        recovered, detail, block = recover_saved_refutation(
            task.target_name,
            task.source_with_hole,
            Path(substrate),
            int(timeout_s),
        )
        if recovered:
            accepted, detail, block = adjudicate_statement_false_verdict(
                task.target_name,
                task.source_with_hole,
                "",
                True,
                detail,
                block,
                provenance="lean_consequence.saved_probe_kernel_recheck",
            )
            if not accepted:
                block = ""
            raw = {
                "results": [{
                    "outcome": "falsified" if accepted else "unresolved",
                    "compile_tail": detail,
                }],
                "statement_false_verified": bool(accepted),
                "statement_false_refutation": block,
                "control_verdict": confirmed_refutation_verdict(
                    task.target_name, task.source_with_hole, ""
                ),
                "refutation_provenance": "saved_probe_kernel_recheck",
            }
        else:
            from ztare.leanmill.solver.solver_core import solve_adhoc

            solve_fn = solve_adhoc
    if solve_fn is not None:
        raw = dict(
            solve_fn(
                task.target_name,
                task.source_with_hole,
                "",
                substrate=Path(substrate),
                timeout_s=int(timeout_s),
                notes=notes or "AxiomPack conditional consequence; preserve every local premise.",
            )
        )
    solve_result = SolveResult.from_dict(raw)
    primary = solve_result.primary()
    outcome = str(primary.get("outcome") or "")
    validation = primary.get("contract_validation") or {}
    proof = _normalized_proof_text(str(primary.get("proof_text") or ""))
    credited = (
        outcome == "closed"
        and bool(proof)
        and validation.get("credit_ready_at_solver_layer") is True
    )
    reason = str(
        primary.get("compile_tail") or primary.get("provider_error_detail") or ""
    )[-400:]
    typed_refutation_declared = False
    typed_refutation_source = ""
    typed_verdict_json: Mapping[str, Any] | None = None
    control_verdict = getattr(solve_result, "control_verdict", None)
    if isinstance(control_verdict, Mapping):
        typed_verdict_json = control_verdict
        try:
            from ztare.leanmill.control_plane import Verdict, VerdictKind, source_fingerprint

            typed_verdict = Verdict.from_json(typed_verdict_json)
            if typed_verdict.kind is VerdictKind.REFUTED:
                typed_refutation_declared = True
                identity = typed_verdict.statement_id
                if (
                    identity.target_name == task.target_name
                    and identity.target_source_hash == source_fingerprint(task.source_with_hole)
                ):
                    typed_refutation_source = typed_verdict.kernel_refutation_source()
                    reason = typed_verdict.detail
        except (TypeError, ValueError):
            typed_refutation_declared = True
    attribution: Mapping[str, Any] | None = None
    refutation: Mapping[str, Any] | None = None
    if credited or (outcome == "rejected_banned_axiom" and proof):
        scoped = recheck_governed_lean_consequence(
            task,
            proof,
            compile_fn=compile_fn,
            generic_solver_outcome=outcome,
            solver_entry="ztare.leanmill.solver.solver_core.solve_adhoc",
        )
        if scoped.status in {"proved_attributed", "proved_unattributed"}:
            return scoped
        status, verdict = scoped.status, scoped.work_receipt["verdict"]
        attribution = scoped.attribution
        reason = scoped.reason
    elif typed_refutation_declared or solve_result.statement_false_verified:
        block = typed_refutation_source
        if not typed_refutation_declared:
            block = str(
                raw.get("statement_false_refutation")
                or primary.get("statement_false_refutation")
                or ""
            )
        if block.strip():
            refutation_core = {
                "schema": "leanmill.lean_refutation_certificate.v1",
                "task_id": task.task_id,
                "target_name": task.target_name,
                "source_sha256": content_hash({"lean_source": block}),
                "lean_source": block,
                "control_verdict": dict(typed_verdict_json or {}),
                "authority": "lean_kernel_axiom_audit",
            }
            refutation = {
                **refutation_core,
                "receipt_sha256": content_hash(refutation_core),
            }
            status, verdict = "refuted_by_kernel", "rejected"
        else:
            status, verdict = "unavailable", "gap"
            reason = "kernel refutation lacked replayable certificate bytes"
    elif outcome.startswith("rejected_"):
        status, verdict = "rejected_by_governance", "rejected"
    elif outcome.startswith("inadmissible") or outcome == "skipped_by_circuit_breaker":
        status, verdict = "unavailable", "gap"
    else:
        status, verdict = "unresolved", "gap"
    work_receipt = WorkReceipt(
        item=task.to_work_item(),
        verdict=verdict,
        formal_leg={
            "solver_entry": "ztare.leanmill.solver.solver_core.solve_adhoc",
            "outcome": outcome,
            "credit_ready": credited,
            "closure_certificate": solve_result.closure_certificate,
            "attribution_ref": (
                attribution.get("receipt_sha256") if attribution is not None else None
            ),
            "refutation_ref": (
                refutation.get("receipt_sha256") if refutation is not None else None
            ),
        },
        gap_text="" if verdict == "completed" else (reason or status),
    ).model_dump()
    return GovernedLeanConsequenceAttempt(
        task_id=task.task_id,
        status=status,
        proof_text=proof,
        solver_result_digest=content_hash(raw),
        attribution=attribution,
        work_receipt=work_receipt,
        refutation=refutation,
        reason=reason,
    )
__all__ = [
    "GovernedLeanConsequenceAttempt", "LeanConsequenceAttempt", "LeanConsequenceTask",
    "check_lean_consequence_proof", "execute_governed_lean_consequence",
    "matched_proof_attribution", "recheck_governed_lean_consequence",
    "render_lean_consequence_task",
]
