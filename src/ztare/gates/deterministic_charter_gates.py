"""GP-030 first slice — deterministic charter-gate evaluator.

Hardens the GP-023 Phase 1 attack surface (judge softening on hard
numeric thresholds) by binding declared charter gates to the project's
``test_model.py`` harness rather than to thesis prose.

Design (decision-critical per GP-030 Turns 1–3):

- The charter is the source of truth for *which* gates exist.
- ``test_model.py`` is the source of truth for *whether* a gate passes.
  The judge reads prose; the deterministic gate reads the executable
  interface. Those jobs do not cross.
- Score interaction is fail-closed: if any declared gate fails, the
  champion's effective score is capped at 50 via the existing
  ``soft_score_caps`` plumbing in
  ``test_thesis.finalize_deterministic_score``.
- The first slice does not auto-parse thesis prose, does not synthesize
  callables, and does not enforce the construction-time invariant
  (test_model.py must expose the callables at sandbox-seal time). The
  seal-time invariant is explicitly deferred to the next slice; for
  this slice, projects that declare gates and ship a harness without
  the contract simply fail-closed at runtime, which preserves the
  fail-closed property without requiring the invariant check yet.

Harness contract (first slice):

The runner invokes ``python test_model.py --emit-deterministic-gates``
in a subprocess. The harness is expected to print a single JSON line
to stdout of the form::

    {"gates": [
        {"name": "global_residual", "passed": false,
         "actual": 1.79, "threshold": 0.05, "operator": "lt",
         "reason": "max abs residual 1.79 exceeds 0.05 on psi=1.8 sweep"},
        ...
    ]}

If the harness does not support the flag (returncode != 0, no JSON on
stdout, or JSON shape mismatch), every declared gate is treated as
failed with reason ``"harness did not expose --emit-deterministic-gates"``.
This is the fail-closed semantics from Turn 3.

If the project's charter has no ``## Deterministic Gates`` section,
this evaluator is a complete no-op. GP-030 is per-project opt-in.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


GATE_FAILURE_SCORE_CAP = 50
"""Score cap applied via ``soft_score_caps`` when any declared gate
fails. 50 keeps the failure visible-in-history while blocking champion
promotion (the canonical promotion threshold sits above 50). Per
Codex Turn 2 and Claude Turn 3: not zero, because zero would conflate
"failed a hard threshold" with "structurally incoherent thesis"."""

GATE_HARNESS_TIMEOUT_SECONDS = 15
"""Subprocess timeout for harness invocation. Mirrors the existing
test_suite invocation timeout in ``test_thesis.py``. A timeout counts
as a fail-closed result."""

VALID_OPERATORS = frozenset({"lt", "le", "gt", "ge", "eq"})


@dataclass(frozen=True)
class DeterministicGateSpec:
    """One declared gate from the charter."""

    name: str
    metric: str
    threshold: float
    operator: str
    evidence_source: str = ""
    scope: str = ""


@dataclass(frozen=True)
class DeterministicGateResult:
    """One gate's evaluation outcome."""

    name: str
    passed: bool
    reason: str
    actual: float | None = None
    threshold: float | None = None
    operator: str = ""


@dataclass(frozen=True)
class DeterministicGateEvaluation:
    """Aggregate result of evaluating all declared gates."""

    declared: tuple[DeterministicGateSpec, ...]
    results: tuple[DeterministicGateResult, ...]
    harness_invoked: bool
    harness_failure_reason: str = ""

    @property
    def any_failed(self) -> bool:
        return any(not result.passed for result in self.results)

    @property
    def failure_count(self) -> int:
        return sum(1 for result in self.results if not result.passed)


# ---------------------------------------------------------------------------
# Charter parsing
# ---------------------------------------------------------------------------


_FENCE_RE = re.compile(r"^```")


def parse_deterministic_gates_from_charter(
    charter_text: str | None,
) -> list[DeterministicGateSpec]:
    """Extract gate specs from a ``## Deterministic Gates`` section.

    The expected charter shape is a single fenced YAML-ish block under
    a ``## Deterministic Gates`` heading, with a ``deterministic_gates:``
    list of dicts. Parsing is intentionally minimal — no PyYAML
    dependency, no support for nested structures, no support for
    multiline values. The charter author writes one gate per dict and
    one ``key: value`` per line. Anything fancier should fail to
    parse, which is fine because GP-030 first slice does not need to
    parse arbitrary YAML; it needs to parse the documented contract.

    A charter with no ``## Deterministic Gates`` section returns ``[]``,
    which makes the evaluator a no-op for that project (per the
    per-project opt-in property in the seam's Scope section).
    """

    if not charter_text:
        return []

    lines = charter_text.splitlines()
    in_section = False
    block_lines: list[str] = []
    in_fence = False
    for raw_line in lines:
        stripped_full = raw_line.rstrip()
        stripped = stripped_full.strip()
        if stripped.startswith("## ") and not in_fence:
            in_section = stripped == "## Deterministic Gates"
            continue
        if not in_section:
            continue
        if _FENCE_RE.match(stripped):
            in_fence = not in_fence
            continue
        if in_fence:
            block_lines.append(stripped_full)

    if not block_lines:
        return []

    return _parse_gate_block(block_lines)


def _parse_gate_block(block_lines: list[str]) -> list[DeterministicGateSpec]:
    """Parse the YAML-ish ``deterministic_gates:`` block.

    Accepted shape::

        deterministic_gates:
          - name: global_residual
            metric: max_abs_residual
            threshold: 0.05
            operator: lt
            evidence_source: evidence.txt
            scope: all_sweeps
          - name: peak_location
            ...
    """

    gates: list[DeterministicGateSpec] = []
    current: dict[str, str] | None = None
    inside_list = False

    for line in block_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "deterministic_gates:":
            inside_list = True
            continue
        if not inside_list:
            continue
        if stripped.startswith("- "):
            if current is not None:
                spec = _gate_spec_from_dict(current)
                if spec is not None:
                    gates.append(spec)
            current = {}
            after_dash = stripped[2:].strip()
            if after_dash:
                key, _, value = after_dash.partition(":")
                if value:
                    current[key.strip()] = value.strip()
            continue
        if current is None:
            continue
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        current[key.strip()] = value.strip()

    if current is not None:
        spec = _gate_spec_from_dict(current)
        if spec is not None:
            gates.append(spec)

    return gates


def _gate_spec_from_dict(raw: dict[str, str]) -> DeterministicGateSpec | None:
    """Build a typed spec from a parsed dict, dropping malformed entries."""

    name = raw.get("name", "").strip()
    metric = raw.get("metric", "").strip()
    threshold_raw = raw.get("threshold", "").strip()
    operator = raw.get("operator", "").strip().lower()
    if not name or not metric or not threshold_raw or operator not in VALID_OPERATORS:
        return None
    try:
        threshold = float(threshold_raw)
    except ValueError:
        return None
    return DeterministicGateSpec(
        name=name,
        metric=metric,
        threshold=threshold,
        operator=operator,
        evidence_source=raw.get("evidence_source", "").strip(),
        scope=raw.get("scope", "").strip(),
    )


# ---------------------------------------------------------------------------
# Harness invocation
# ---------------------------------------------------------------------------


def _invoke_harness(test_path: Path) -> tuple[bool, str, list[dict]]:
    """Run ``python test_model.py --emit-deterministic-gates``.

    Returns ``(harness_ok, failure_reason, harness_gate_payloads)``.
    ``harness_ok=False`` means the deterministic gate cannot be
    evaluated against this harness and the caller must apply the
    fail-closed policy to all declared gates.
    """

    if not test_path.exists():
        return False, f"test_model.py missing at {test_path}", []
    # Prefer a sibling `gate_harness.py` when present. The frozen harness
    # sits outside the mutator's write-scope, so the deterministic-gate
    # emission contract cannot drift when the mutator rewrites test_model.py.
    # The frozen harness imports I_model / MODEL_PARAMS from test_model.py;
    # if the mutator renames or removes them, the harness raises and this
    # function returns harness_ok=False → fail-closed cap-at-50.
    gate_harness_path = test_path.parent / "gate_harness.py"
    invocation_path = gate_harness_path if gate_harness_path.exists() else test_path
    try:
        completed = subprocess.run(
            ["python", str(invocation_path), "--emit-deterministic-gates"],
            capture_output=True,
            text=True,
            timeout=GATE_HARNESS_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return False, "harness timed out during deterministic gate emission", []
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"harness invocation raised {type(exc).__name__}: {exc}", []

    if completed.returncode != 0:
        return (
            False,
            f"harness exited {completed.returncode} on --emit-deterministic-gates "
            f"(stderr={completed.stderr.strip()[:200]})",
            [],
        )

    stdout = completed.stdout.strip()
    payload = _extract_json_payload(stdout)
    if payload is None:
        return False, "harness did not emit a parseable JSON payload on stdout", []
    if not isinstance(payload, dict) or "gates" not in payload:
        return False, "harness JSON payload missing 'gates' key", []
    gates = payload.get("gates")
    if not isinstance(gates, list):
        return False, "harness 'gates' field is not a list", []
    return True, "", gates


def _extract_json_payload(text: str) -> object | None:
    """Find the first parseable JSON object in stdout.

    The harness may legitimately print other lines (logging, etc.)
    around the JSON payload. The first ``{...}`` block that parses as
    JSON wins. This is more forgiving than ``json.loads(text)`` would
    be and matches the way other ZTARE harness contracts work.
    """

    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for match in re.finditer(r"\{.*\}", text, re.DOTALL):
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


# ---------------------------------------------------------------------------
# Result construction
# ---------------------------------------------------------------------------


def _result_from_payload(
    spec: DeterministicGateSpec, payload: dict
) -> DeterministicGateResult:
    """Build a result for ``spec`` from one harness payload entry."""

    passed = bool(payload.get("passed", False))
    reason = str(payload.get("reason", "") or "").strip()
    if not reason:
        reason = (
            f"gate {spec.name}: passed={passed}, "
            f"actual={payload.get('actual')}, threshold={payload.get('threshold')}, "
            f"operator={payload.get('operator')}"
        )
    actual = payload.get("actual")
    threshold = payload.get("threshold", spec.threshold)
    return DeterministicGateResult(
        name=spec.name,
        passed=passed,
        reason=reason,
        actual=float(actual) if isinstance(actual, (int, float)) else None,
        threshold=float(threshold) if isinstance(threshold, (int, float)) else None,
        operator=str(payload.get("operator", spec.operator) or spec.operator),
    )


def _failure_result_for_missing_harness(
    spec: DeterministicGateSpec, harness_failure_reason: str
) -> DeterministicGateResult:
    return DeterministicGateResult(
        name=spec.name,
        passed=False,
        reason=(
            f"gate {spec.name} fail-closed: {harness_failure_reason}. "
            f"declared threshold {spec.operator} {spec.threshold} on metric "
            f"'{spec.metric}'."
        ),
        actual=None,
        threshold=spec.threshold,
        operator=spec.operator,
    )


def _failure_result_for_missing_payload(
    spec: DeterministicGateSpec,
) -> DeterministicGateResult:
    return DeterministicGateResult(
        name=spec.name,
        passed=False,
        reason=(
            f"gate {spec.name} fail-closed: harness did not emit a payload "
            f"for declared gate (declared {spec.operator} {spec.threshold} "
            f"on metric '{spec.metric}')"
        ),
        actual=None,
        threshold=spec.threshold,
        operator=spec.operator,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def evaluate_deterministic_charter_gates(
    *,
    charter_text: str | None,
    test_model_path: Path,
) -> DeterministicGateEvaluation:
    """Evaluate all declared gates against the project harness.

    No-op (empty evaluation) when the charter declares no gates. Per
    the Scope section of GP-030, GP-030 is per-project opt-in: only
    projects with a ``## Deterministic Gates`` section participate.
    """

    declared = parse_deterministic_gates_from_charter(charter_text)
    if not declared:
        return DeterministicGateEvaluation(
            declared=(),
            results=(),
            harness_invoked=False,
            harness_failure_reason="",
        )

    harness_ok, harness_failure_reason, payload_entries = _invoke_harness(test_model_path)
    if not harness_ok:
        results = tuple(
            _failure_result_for_missing_harness(spec, harness_failure_reason)
            for spec in declared
        )
        return DeterministicGateEvaluation(
            declared=tuple(declared),
            results=results,
            harness_invoked=True,
            harness_failure_reason=harness_failure_reason,
        )

    payloads_by_name: dict[str, dict] = {}
    for entry in payload_entries:
        if isinstance(entry, dict) and isinstance(entry.get("name"), str):
            payloads_by_name[entry["name"]] = entry

    results: list[DeterministicGateResult] = []
    for spec in declared:
        payload = payloads_by_name.get(spec.name)
        if payload is None:
            results.append(_failure_result_for_missing_payload(spec))
            continue
        results.append(_result_from_payload(spec, payload))

    return DeterministicGateEvaluation(
        declared=tuple(declared),
        results=tuple(results),
        harness_invoked=True,
        harness_failure_reason="",
    )


def soft_cap_entries_for_evaluation(
    evaluation: DeterministicGateEvaluation,
) -> list[dict]:
    """Translate gate failures into ``soft_score_caps`` dicts.

    Returns one entry per failed gate so each appears in the score
    contract record. The cap value is fixed at
    ``GATE_FAILURE_SCORE_CAP``; the existing
    ``finalize_deterministic_score`` machinery already takes the min
    across all caps so adding multiple cap entries with the same value
    is safe and produces good debug output.
    """

    entries: list[dict] = []
    for result in evaluation.results:
        if result.passed:
            continue
        entries.append(
            {
                "reason": (
                    f"GP-030 deterministic charter gate '{result.name}' failed: "
                    f"{result.reason}"
                ),
                "cap": GATE_FAILURE_SCORE_CAP,
            }
        )
    return entries


def gate_results_to_dicts(
    evaluation: DeterministicGateEvaluation,
) -> list[dict]:
    """JSON-friendly representation for embedding in score_contract."""

    return [
        {
            "name": result.name,
            "passed": result.passed,
            "actual": result.actual,
            "threshold": result.threshold,
            "operator": result.operator,
            "reason": result.reason,
        }
        for result in evaluation.results
    ]


def declared_gate_names(evaluation: DeterministicGateEvaluation) -> list[str]:
    return [spec.name for spec in evaluation.declared]
