"""Formalize-only admission for matched AxiomPack shadow campaigns.

This module adds no formalizer, verifier, or prover.  It calls the existing
``autoformalize_and_solve`` entry with a capture callback at its established
``solve_fn`` boundary.  Reaching that callback means the current context,
refinement, faithfulness, def-shell, and optional per-definition gates have all
run.  The captured target can then be supplied unchanged to both shadow arms;
proof authority remains with ``solver_core.solve_adhoc``.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Callable, Mapping


FORMALIZATION_ADMISSION_SCHEMA = "leanmill.formalization_admission.v1"
ADMITTED = "ADMITTED"
REJECTED = "REJECTED"
INADMISSIBLE_PROVIDER_DEAD = "INADMISSIBLE_PROVIDER_DEAD"
INVALID_ADMISSION = "INVALID_ADMISSION"

_STATUSES = {
    ADMITTED,
    REJECTED,
    INADMISSIBLE_PROVIDER_DEAD,
    INVALID_ADMISSION,
}
_SHA256_REF = re.compile(r"^sha256:[0-9a-f]{64}$")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _digest(value: Any) -> str:
    encoded = value if isinstance(value, str) else _canonical_json(value)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _json_object(text: str, *, field_name: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{field_name} must contain canonical JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must contain a JSON object")
    return value


def _json_list(text: str, *, field_name: str) -> list[Any]:
    try:
        value = json.loads(text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{field_name} must contain canonical JSON") from exc
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must contain a JSON list")
    return value


def _normalized_signature(source: str, target_name: str) -> str:
    if not source or not target_name:
        return ""
    from ztare.leanmill.lean_source import extract_signature, strip_comments

    return " ".join(strip_comments(extract_signature(source, target_name) or "").split())


def _target_is_open(source: str, target_name: str) -> bool:
    from ztare.leanmill.lean_source import decl_blocks, has_sorry

    matching = [block for name, block in decl_blocks(source) if name == target_name]
    return len(matching) == 1 and has_sorry(matching[0])


def _compose_arm_prelude(prelude: str, admitted_source: str) -> str:
    """Place imports first, then preserve both declaration bodies verbatim."""

    if not prelude.strip():
        return admitted_source
    imports: list[str] = []

    def split_imports(text: str) -> tuple[list[str], str]:
        kept: list[str] = []
        body: list[str] = []
        for line in text.splitlines():
            if line.startswith("import "):
                if line not in kept:
                    kept.append(line)
            else:
                body.append(line)
        return kept, "\n".join(body).strip()

    prelude_imports, prelude_body = split_imports(prelude)
    source_imports, source_body = split_imports(admitted_source)
    for line in prelude_imports + source_imports:
        if line not in imports:
            imports.append(line)
    parts = [*imports]
    if imports:
        parts.append("")
    if prelude_body:
        parts.extend([prelude_body, ""])
    parts.append(source_body)
    return "\n".join(parts).strip() + "\n"


@dataclass(frozen=True)
class AdmittedSolveInput:
    """Immutable positional payload for ``solver_core.solve_adhoc``."""

    target_name: str
    source_text: str
    goal: str
    admission_digest: str
    target_signature_digest: str

    def positional_args(self) -> tuple[str, str, str]:
        return self.target_name, self.source_text, self.goal


@dataclass(frozen=True)
class FormalizationAdmission:
    """Frozen statement-side result produced before either shadow arm runs."""

    task_digest: str
    intent_text: str
    context_digest: str
    status: str
    target_name: str
    source_text: str
    target_signature: str
    faithfulness_reason: str
    faithfulness_checks_json: str
    refine_trace_json: str
    advisory_audits_json: str
    schema: str = FORMALIZATION_ADMISSION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != FORMALIZATION_ADMISSION_SCHEMA:
            raise ValueError(f"unsupported admission schema: {self.schema!r}")
        if self.status not in _STATUSES:
            raise ValueError(f"unsupported admission status: {self.status!r}")
        if not self.intent_text.strip():
            raise ValueError("intent_text is required")
        if not _SHA256_REF.fullmatch(self.task_digest):
            raise ValueError("task_digest must be a canonical sha256 reference")
        if not _SHA256_REF.fullmatch(self.context_digest):
            raise ValueError("context_digest must be a canonical sha256 reference")
        _json_object(
            self.faithfulness_checks_json,
            field_name="faithfulness_checks_json",
        )
        _json_list(self.refine_trace_json, field_name="refine_trace_json")
        _json_object(self.advisory_audits_json, field_name="advisory_audits_json")
        if self.status == ADMITTED:
            if not self.target_name or not self.source_text or not self.target_signature:
                raise ValueError("an admitted target requires name, source, and signature")
            from ztare.leanmill.lean_source import theorem_names

            names = theorem_names(self.source_text)
            if names.count(self.target_name) != 1 or names[-1] != self.target_name:
                raise ValueError("admitted target must be the final theorem or lemma")
            if _normalized_signature(self.source_text, self.target_name) != self.target_signature:
                raise ValueError("admitted target signature does not match its source")
            if not _target_is_open(self.source_text, self.target_name):
                raise ValueError("admitted target must contain exactly one open declaration")

    @property
    def admitted(self) -> bool:
        return self.status == ADMITTED

    @property
    def intent_digest(self) -> str:
        return _digest(self.intent_text)

    @property
    def source_digest(self) -> str:
        return _digest(self.source_text)

    @property
    def target_signature_digest(self) -> str:
        return _digest(self.target_signature)

    @property
    def faithfulness_checks(self) -> dict[str, Any]:
        return _json_object(
            self.faithfulness_checks_json,
            field_name="faithfulness_checks_json",
        )

    @property
    def refine_trace(self) -> list[Any]:
        return _json_list(self.refine_trace_json, field_name="refine_trace_json")

    @property
    def advisory_audits(self) -> dict[str, Any]:
        return _json_object(
            self.advisory_audits_json,
            field_name="advisory_audits_json",
        )

    def _content(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "task_digest": self.task_digest,
            "intent_text": self.intent_text,
            "intent_digest": self.intent_digest,
            "context_digest": self.context_digest,
            "status": self.status,
            "target_name": self.target_name,
            "source_text": self.source_text,
            "source_digest": self.source_digest,
            "target_signature": self.target_signature,
            "target_signature_digest": self.target_signature_digest,
            "faithfulness_reason": self.faithfulness_reason,
            "faithfulness_checks": self.faithfulness_checks,
            "refine_trace": self.refine_trace,
            "advisory_audits": self.advisory_audits,
        }

    @property
    def admission_digest(self) -> str:
        return _digest(self._content())

    def to_json(self) -> dict[str, Any]:
        return {**self._content(), "admission_digest": self.admission_digest}

    @classmethod
    def from_json(cls, row: Mapping[str, Any]) -> "FormalizationAdmission":
        required = {
            "schema",
            "task_digest",
            "intent_text",
            "intent_digest",
            "context_digest",
            "status",
            "target_name",
            "source_text",
            "source_digest",
            "target_signature",
            "target_signature_digest",
            "faithfulness_reason",
            "faithfulness_checks",
            "refine_trace",
            "advisory_audits",
            "admission_digest",
        }
        if set(row) != required:
            raise ValueError(
                "admission payload fields do not match the frozen schema"
            )
        string_fields = (
            "schema",
            "task_digest",
            "intent_text",
            "intent_digest",
            "context_digest",
            "status",
            "target_name",
            "source_text",
            "source_digest",
            "target_signature",
            "target_signature_digest",
            "faithfulness_reason",
            "admission_digest",
        )
        if not all(isinstance(row.get(name), str) for name in string_fields):
            raise ValueError("admission scalar fields must be strings")
        if not isinstance(row.get("faithfulness_checks"), Mapping):
            raise ValueError("faithfulness_checks must be an object")
        if not isinstance(row.get("refine_trace"), list):
            raise ValueError("refine_trace must be a list")
        if not isinstance(row.get("advisory_audits"), Mapping):
            raise ValueError("advisory_audits must be an object")
        result = cls(
            task_digest=row["task_digest"],
            intent_text=row["intent_text"],
            context_digest=row["context_digest"],
            status=row["status"],
            target_name=row["target_name"],
            source_text=row["source_text"],
            target_signature=row["target_signature"],
            faithfulness_reason=row["faithfulness_reason"],
            faithfulness_checks_json=_canonical_json(row["faithfulness_checks"]),
            refine_trace_json=_canonical_json(row["refine_trace"]),
            advisory_audits_json=_canonical_json(row["advisory_audits"]),
            schema=row["schema"],
        )
        expected = {
            "intent_digest": result.intent_digest,
            "source_digest": result.source_digest,
            "target_signature_digest": result.target_signature_digest,
            "admission_digest": result.admission_digest,
        }
        mismatches = [name for name, value in expected.items() if row.get(name) != value]
        if mismatches:
            raise ValueError(f"admission digest mismatch: {mismatches}")
        return result

    def solve_input(self, *, arm_prelude: str = "") -> AdmittedSolveInput:
        """Return a target-bound input for the canonical ``solve_adhoc`` entry.

        ``arm_prelude`` supplies the base or treatment theory.  The admitted
        source is appended unchanged after imports, preventing an arm from
        editing or pre-closing the heldout target.  Kernel governance still
        decides the elaborated proof.
        """

        if not self.admitted:
            raise ValueError(f"cannot solve admission with status {self.status}")
        if not isinstance(arm_prelude, str):
            raise ValueError("arm_prelude must be a string")
        source = _compose_arm_prelude(arm_prelude, self.source_text)
        from ztare.leanmill.lean_source import theorem_names

        names = theorem_names(source)
        if names.count(self.target_name) != 1 or names[-1] != self.target_name:
            raise ValueError("arm source must retain the admitted target as its final theorem")
        if _normalized_signature(source, self.target_name) != self.target_signature:
            raise ValueError("arm source changed the admitted target signature")
        if not _target_is_open(source, self.target_name):
            raise ValueError("arm source must retain one open admitted target")
        return AdmittedSolveInput(
            target_name=self.target_name,
            source_text=source,
            goal="",
            admission_digest=self.admission_digest,
            target_signature_digest=self.target_signature_digest,
        )


def formalize_only(
    intent_text: str,
    *,
    task_digest: str,
    sandbox: Any,
    substrate: Any = None,
    formalize_fn: Callable[[str], str] | None = None,
    compile_fn: Callable[[str], bool] | None = None,
    triviality_fn: Callable[[str], bool] | None = None,
    backtranslate_fn: Callable[[str], str] | None = None,
    judge_fn: Callable[[str, str], bool] | None = None,
    structural_fn: Callable[[str, str], bool] | None = None,
    timeout_s: int = 600,
    max_refines: int = 2,
    def_faithfulness: bool = False,
    notes: str | None = None,
    shared_context: str = "",
) -> FormalizationAdmission:
    """Run the current admission pipeline and stop at its canonical solve seam.

    The function must be called once per task, before assigning baseline or
    treatment context.  ``task_digest`` binds this frozen output to the heldout
    task selected by the shadow evaluator.
    """

    if not isinstance(intent_text, str) or not intent_text.strip():
        raise ValueError("intent_text is required")
    if not isinstance(task_digest, str) or not _SHA256_REF.fullmatch(task_digest):
        raise ValueError("task_digest must be a canonical sha256 reference")

    captured: list[tuple[str, str]] = []

    def _capture(target_name: str, source_text: str) -> dict[str, Any]:
        if captured:
            raise RuntimeError("formalize-only boundary was crossed more than once")
        captured.append((target_name, source_text))
        return {"results": [{"outcome": "formalize_only_admitted"}]}

    from ztare.leanmill.solver.autoformalize import (
        AutoformalizeSolveConfig,
        autoformalize_and_solve,
    )

    config = AutoformalizeSolveConfig.from_boundary(
        timeout_s=timeout_s,
        max_refines=max_refines,
        def_faithfulness=def_faithfulness,
        reformulate_budget=0,
    )

    raw = autoformalize_and_solve(
        intent_text,
        sandbox=sandbox,
        substrate=substrate,
        formalize_fn=formalize_fn,
        compile_fn=compile_fn,
        triviality_fn=triviality_fn,
        backtranslate_fn=backtranslate_fn,
        judge_fn=judge_fn,
        structural_fn=structural_fn,
        solve_fn=_capture,
        timeout_s=config.timeout_s,
        max_refines=config.max_refines,
        def_faithfulness=config.def_faithfulness,
        notes=notes,
        extra_context=shared_context,
        reformulate_budget=0,
    )

    source_text = str(raw.get("lean_statement") or "")
    target_name = ""
    status = REJECTED
    reason = str(raw.get("faithfulness_reason") or raw.get("outcome") or "")
    if raw.get("outcome") == "inadmissible_provider_dead":
        status = INADMISSIBLE_PROVIDER_DEAD
    elif raw.get("outcome") == "rejected_by_firewall" and not captured:
        # Definition gates run after the statement-level verdict, so the raw
        # `faithful` bit can remain true while the final admission is refused.
        status = REJECTED
    elif raw.get("faithful") is True and len(captured) == 1:
        target_name, captured_source = captured[0]
        if captured_source != source_text:
            status = INVALID_ADMISSION
            reason = "captured source differs from the admitted formalization"
            target_name = ""
        elif not _target_is_open(source_text, target_name):
            status = INVALID_ADMISSION
            reason = "formalized target is not a unique open declaration"
            target_name = ""
        else:
            status = ADMITTED
    elif captured or raw.get("faithful") is True:
        status = INVALID_ADMISSION
        reason = "formalization pipeline did not cross the solve boundary exactly once"

    target_signature = (
        _normalized_signature(source_text, target_name) if status == ADMITTED else ""
    )
    audits = {
        key: raw[key]
        for key in (
            "generality_audit",
            "ambition_audit",
            "def_shells",
            "def_unfaithful",
        )
        if key in raw
    }
    context_subject = {
        "notes": notes or "",
        "shared_context": shared_context,
        "timeout_s": config.timeout_s,
        "max_refines": config.max_refines,
        "def_faithfulness": config.def_faithfulness,
    }
    return FormalizationAdmission(
        task_digest=task_digest,
        intent_text=intent_text,
        context_digest=_digest(context_subject),
        status=status,
        target_name=target_name,
        source_text=source_text,
        target_signature=target_signature,
        faithfulness_reason=reason,
        faithfulness_checks_json=_canonical_json(
            raw.get("faithfulness_checks")
            if isinstance(raw.get("faithfulness_checks"), Mapping)
            else {}
        ),
        refine_trace_json=_canonical_json(
            raw.get("refine_trace")
            if isinstance(raw.get("refine_trace"), list)
            else []
        ),
        advisory_audits_json=_canonical_json(audits),
    )


__all__ = [
    "ADMITTED",
    "FORMALIZATION_ADMISSION_SCHEMA",
    "INADMISSIBLE_PROVIDER_DEAD",
    "INVALID_ADMISSION",
    "REJECTED",
    "AdmittedSolveInput",
    "FormalizationAdmission",
    "formalize_only",
]
