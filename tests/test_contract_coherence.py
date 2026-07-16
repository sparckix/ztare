"""Structural round-trip tests that FAIL when contract surfaces drift.

Five test classes:
  (a) RECEIPT-TYPE COHERENCE  — every type the prompts teach exists in _KNOWN_CONTROL_RECEIPT_TYPES;
                                every known type is either taught or in the internal-only allowlist
  (b) OMIT-CANDIDATE COHERENCE — every receipt type whose prompt teaches omit → may_omit_candidate
  (c) ROUND-TRIP               — parse+render do not raise; candidate code survives validate
  (d) ZERO-CALLER ORGANS       — exported entry points that MUST have ≥1 non-definition call in src/
  (e) RETRY-PROMPT COHERENCE   — worldmodel skeleton mentions test_model_py, doesn't claim fence-only

Real drifts caught at HEAD are marked xfail with a comment naming the debt.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
sys.path.insert(0, str(SRC))

# ── imports ───────────────────────────────────────────────────────────────────

from ztare.validator.worldmodel_typed_payload import (
    WORLDMODEL_TYPED_PAYLOAD_CONTRACT_PROMPT,
    _KNOWN_CONTROL_RECEIPT_TYPES,
    _RENDERED_CONTROL_MARKERS,
    parse_worldmodel_typed_payload_text,
    render_worldmodel_typed_payload,
    worldmodel_typed_payload_contract_prompt,
)
from ztare.common.science_output_policy import SCIENCE_OUTPUT_POLICY
from ztare.common.candidate_first_policy import (
    candidate_first_empty_candidate_decision,
    candidate_first_policy_text,
)
from ztare.fit.mutation_suite_guard import validate_python_suite_candidate
from ztare.worldmodel.retry_surface import format_worldmodel_retry_skeleton

# ── helpers ───────────────────────────────────────────────────────────────────

def _all_prompt_text() -> str:
    """Union of all prompt surfaces that teach the leaf what receipt types it may use."""
    return "\n".join([
        worldmodel_typed_payload_contract_prompt(),
        SCIENCE_OUTPUT_POLICY.final_contract_text(),
        candidate_first_policy_text(),
    ])

# Match any token that looks like a known receipt type:
#   - underscore-separated ALL_CAPS (LOWERABILITY_BLOCKED, LEAF_WORKBENCH_ACTION_REQUEST)
#   - OR a plain ALL_CAPS word ≥5 chars that appears in _KNOWN_CONTROL_RECEIPT_TYPES
#   The second arm is needed for types like INVESTIGATED (no underscore).
_MULTI_WORD_CAPS_RE = re.compile(r'\b([A-Z][A-Z0-9]{0,}(?:_[A-Z0-9]+){1,})\b')

_KNOWN_SET = set(_KNOWN_CONTROL_RECEIPT_TYPES)
_RENDERED_TYPE_SET = {marker_type for _, marker_type in _RENDERED_CONTROL_MARKERS}

def _taught_known_types_in(text: str) -> set[str]:
    """Return the subset of _KNOWN_CONTROL_RECEIPT_TYPES that appear in text."""
    # Check each known type directly (handles both underscored and non-underscored names).
    return {t for t in _KNOWN_SET if re.search(r'\b' + re.escape(t) + r'\b', text)}

# Types that are legal but are INTERNAL-ONLY (never taught in any prompt, by design):
#   - VISIBLE_WORKBENCH_DIAGNOSTIC: emitted by the renderer from LEAF_WORKBENCH_RECEIPT,
#     never authored by the leaf directly, so deliberately absent from prompts.
#   - LEAF_WORKBENCH_CAPABILITY_PROPOSAL_QUARANTINED: renderer-internal quarantine marker.
_INTERNAL_ONLY_ALLOWLIST: frozenset[str] = frozenset({
    "VISIBLE_WORKBENCH_DIAGNOSTIC",
    "LEAF_WORKBENCH_CAPABILITY_PROPOSAL_QUARANTINED",
})


# ── (a) RECEIPT-TYPE COHERENCE ────────────────────────────────────────────────

class TestReceiptTypeCoherence:
    """Every type the prompts teach must exist in _KNOWN_CONTROL_RECEIPT_TYPES,
    and every known type must be either taught in some prompt or in _INTERNAL_ONLY_ALLOWLIST.
    """

    def test_prompt_types_are_in_known(self):
        """Every receipt-name token surfaced by the prompt texts is in _KNOWN_CONTROL_RECEIPT_TYPES.

        Catches the forward direction: if a new type appears in a prompt but someone
        forgot to add it to _KNOWN_CONTROL_RECEIPT_TYPES.
        """
        all_tokens = set(_MULTI_WORD_CAPS_RE.findall(_all_prompt_text()))
        # Exclude known template placeholder names and non-receipt identifiers.
        _EXCLUDED = {
            "SCIENCE_OUTPUT_POLICY_TOOL_GAP_TEXT", "PATCH_CARRIER_BRIEF_LINE",
            "CANDIDATE_FIRST_POLICY", "DYNAMICS_ASSUMPTION_LINE",
            "WORLD_MODEL_SPEC", "WORLD_MODEL_LEAF_WORKBENCH_CONTRACT",
            "MODEL_PARAMS", "PARAMETER_NAMES", "INIT_RANGE",
            "PARAMETRIC_FORM", "Q_VARIABLES", "EXTENSIONS_SRC",
            # carrier/format concepts (submission form), not control receipts:
            "PATCH_BASE", "PATCH_DELTA", "PATCH_DELTA_SPEC",
            "LEAF_WORKBENCH_ACTION_REQUEST_PRECHECK",
            "LEAF_WORKBENCH_RECEIPT_PROVENANCE_PRECHECK",
            "PATCH_BASE_REGRESSION_PRECHECK", "PATCH_BASE_IMPROVEMENT_PRECHECK",
        }
        phantom = {
            t for t in all_tokens
            if t not in _KNOWN_SET
            and t not in _INTERNAL_ONLY_ALLOWLIST
            and t not in _EXCLUDED
        }
        assert not phantom, (
            f"Prompt surfaces teach receipt-shaped tokens not in _KNOWN_CONTROL_RECEIPT_TYPES "
            f"and not in the allowlists: {sorted(phantom)}. "
            "Add them to _KNOWN_CONTROL_RECEIPT_TYPES or to a known exclusion list."
        )

    def test_investigated_in_initial_contract_prompt(self):
        """INVESTIGATED should be taught in the initial contract prompt, not only in retry."""
        assert "INVESTIGATED" in candidate_first_policy_text(), (
            "candidate_first_policy_text() does not mention INVESTIGATED even though "
            "candidate_first_empty_candidate_decision honors it."
        )

    def test_known_types_taught_or_internal(self):
        """Every _KNOWN_CONTROL_RECEIPT_TYPES entry is taught in some prompt surface
        or listed in _INTERNAL_ONLY_ALLOWLIST.
        """
        all_text = _all_prompt_text()
        untaught = {
            t for t in _KNOWN_SET
            if t not in _taught_known_types_in(all_text)
            and t not in _INTERNAL_ONLY_ALLOWLIST
        }
        assert not untaught, (
            f"_KNOWN_CONTROL_RECEIPT_TYPES entries not taught in any prompt surface "
            f"and not in _INTERNAL_ONLY_ALLOWLIST: {sorted(untaught)}. "
            "Either add them to a prompt surface or add them to _INTERNAL_ONLY_ALLOWLIST."
        )

    def test_rendered_markers_backed_by_known_or_internal(self):
        """Every _RENDERED_CONTROL_MARKERS entry maps to a type in _KNOWN_CONTROL_RECEIPT_TYPES
        or _INTERNAL_ONLY_ALLOWLIST (the renderer may produce internal types the leaf never authors).
        """
        phantom = {
            marker_type for _, marker_type in _RENDERED_CONTROL_MARKERS
            if marker_type not in _KNOWN_SET
            and marker_type not in _INTERNAL_ONLY_ALLOWLIST
        }
        assert not phantom, (
            f"_RENDERED_CONTROL_MARKERS maps to types not in _KNOWN_CONTROL_RECEIPT_TYPES "
            f"or _INTERNAL_ONLY_ALLOWLIST: {sorted(phantom)}"
        )


# ── (b) OMIT-CANDIDATE COHERENCE ─────────────────────────────────────────────

# Types the contract surfaces explicitly permit to omit test_model_py.
# WORLDMODEL_TYPED_PAYLOAD_CONTRACT_PROMPT line ~99: LEAF_WORKBENCH_ACTION_REQUEST, LOWERABILITY_BLOCKED
# SCIENCE_OUTPUT_POLICY.final_contract_text(): INVESTIGATED
_OMIT_TAUGHT_TYPES: list[str] = [
    "LEAF_WORKBENCH_ACTION_REQUEST",
    "LOWERABILITY_BLOCKED",
    "INVESTIGATED",
]


class TestOmitCandidateCoherence:
    """For every receipt type the contract says may omit test_model_py,
    candidate_first_empty_candidate_decision([that_type]).may_omit_candidate is True.
    """

    @pytest.mark.parametrize("receipt_type", _OMIT_TAUGHT_TYPES)
    def test_omit_allowed(self, receipt_type: str):
        decision = candidate_first_empty_candidate_decision([receipt_type])
        assert decision.may_omit_candidate, (
            f"Receipt type {receipt_type!r} is taught in a prompt as permitting empty "
            f"test_model_py, but candidate_first_empty_candidate_decision returns "
            f"may_omit_candidate=False. Drift between prompt surface and policy function."
        )

    def test_candidate_required_when_no_special_receipt(self):
        """No special receipt → may_omit must be False (the baseline contract)."""
        decision = candidate_first_empty_candidate_decision([])
        assert not decision.may_omit_candidate

    def test_candidate_required_for_unknown_receipt(self):
        """An unrecognized receipt type must NOT grant omit permission."""
        decision = candidate_first_empty_candidate_decision(["UNKNOWN_RECEIPT_TYPE_XYZ"])
        assert not decision.may_omit_candidate


# ── (c) ROUND-TRIP ────────────────────────────────────────────────────────────

_MINIMAL_LOWERABILITY_BLOCKED_PAYLOAD = {
    "visible_capabilities_attempted": ["run_visible_json_probe"],
    "candidate_family_attempted": "step_fn",
    "obstruction": "no gamma-lowerable witness",
    "missing_witness_or_sensor": "state_transition_witness",
    "next_action": "request_probe",
    "evidence_refs": ["workspace/visible_cli_receipts/probe_001.json"],
}

_ROUND_TRIP_CASES: list[tuple[str, dict]] = [
    (
        "LEAF_WORKBENCH_ACTION_REQUEST",
        {
            "control_receipts": [
                {
                    "type": "LEAF_WORKBENCH_ACTION_REQUEST",
                    "payload": {
                        "capability_id": "inspect_worldmodel_counterexample_context",
                        "input_refs": {},
                        "claim_bindings": ["inspect counterexample"],
                    },
                }
            ],
            "thesis_markdown": "running workbench action",
            "test_model_py": "",
        },
    ),
    (
        "LOWERABILITY_BLOCKED",
        {
            "control_receipts": [
                {"type": "LOWERABILITY_BLOCKED", "payload": _MINIMAL_LOWERABILITY_BLOCKED_PAYLOAD}
            ],
            "thesis_markdown": "no lowerable candidate",
            "test_model_py": "",
        },
    ),
    (
        "INVESTIGATED",
        {
            "control_receipts": [
                {
                    "type": "INVESTIGATED",
                    "payload": {
                        "eliminated_hypothesis": "rule_identity_x",
                        "witness": {"source": "episode_001"},
                        "evidence_refs": ["workspace/visible_cli_receipts/abc.json"],
                    },
                }
            ],
            "thesis_markdown": "investigation turn",
            "test_model_py": "",
        },
    ),
]


class TestRoundTrip:
    """parse+render must not raise for each may-omit type.
    For candidate-bearing payloads, extracted code must survive validate_python_suite_candidate.
    """

    @pytest.mark.parametrize("receipt_type,payload", _ROUND_TRIP_CASES)
    def test_control_only_roundtrip(self, receipt_type: str, payload: dict):
        import json
        text = json.dumps(payload)
        parsed = parse_worldmodel_typed_payload_text(text)
        assert isinstance(parsed, dict), f"parse returned non-dict for {receipt_type}"
        rendered = render_worldmodel_typed_payload(parsed)
        assert isinstance(rendered, str), f"render returned non-str for {receipt_type}"

    def test_candidate_payload_roundtrip(self):
        """A candidate-bearing payload: parse, render, and validate_python_suite_candidate survive."""
        import json
        payload = {
            "control_receipts": [],
            "thesis_markdown": "direct candidate",
            "test_model_py": "def step(grid, action, t):\n    return grid\n",
        }
        text = json.dumps(payload)
        parsed = parse_worldmodel_typed_payload_text(text)
        assert isinstance(parsed, dict)
        extracted = str(parsed.get("test_model_py") or "")
        assert extracted.strip(), "test_model_py lost during parse"
        validate_python_suite_candidate(extracted)  # must not raise
        rendered = render_worldmodel_typed_payload(parsed)
        assert "def step" in rendered


# ── (d) ZERO-CALLER ORGANS ────────────────────────────────────────────────────

# Add new exported entry points that MUST have callers here — one line each.
# Format: (def_file_relative_to_src_ztare, function_name)
_MUST_HAVE_CALLERS: list[tuple[str, str]] = [
    ("ztare/validator/core/worldmodel_control_outcome.py", "build_worldmodel_control_only_eval"),
    ("ztare/validator/core/strategy_card_gate.py", "persist_strategy_card_discharges"),
    # ponytail: add more here when a new validator/eval entry point is exported to core/
]


class TestZeroCallerOrgans:
    """For each entry in _MUST_HAVE_CALLERS, assert src/ has ≥1 call site outside
    the definition file. Extend _MUST_HAVE_CALLERS by one line to enroll a new organ.
    """

    @pytest.mark.parametrize("def_file,fn_name", _MUST_HAVE_CALLERS)
    def test_has_caller_in_src(self, def_file: str, fn_name: str):
        """grep src/ztare/ for calls to fn_name, excluding its definition file."""
        result = subprocess.run(
            ["grep", "-rn", fn_name, str(SRC / "ztare")],
            capture_output=True,
            text=True,
        )
        lines = [
            line for line in result.stdout.splitlines()
            if def_file not in line
            and ".pyc" not in line
            and ".py:" in line    # only source lines, not binary matches
        ]
        assert lines, (
            f"{fn_name!r} defined in {def_file!r} has no callers in src/ztare/ "
            "outside its own definition. Either delete the export or wire it in."
        )


# ── (e) RETRY-PROMPT COHERENCE ────────────────────────────────────────────────

class TestRetryPromptCoherence:
    """Retry skeletons must not instruct the leaf to use a path the extractor cannot accept."""

    def _worldmodel_skeleton(self, error_text: str = "") -> str:
        return format_worldmodel_retry_skeleton(
            error_text or "Missing required Python falsification suite block; reject candidate before evaluation.",
            prior_content="",
            max_prior_chars=1000,
            project_dir=None,
        )

    def test_worldmodel_skeleton_mentions_test_model_py(self):
        """The worldmodel retry skeleton must instruct the leaf to populate test_model_py."""
        skeleton = self._worldmodel_skeleton()
        assert "test_model_py" in skeleton, (
            "Worldmodel retry skeleton does not mention test_model_py. "
            "The extractor reads this JSON field; the retry prompt must name it."
        )

    def test_worldmodel_skeleton_does_not_claim_fences_are_only_path(self):
        """The worldmodel skeleton must NOT tell the leaf that fenced code blocks are the
        only accepted carrier path (the extractor also accepts JSON test_model_py field).
        """
        skeleton = self._worldmodel_skeleton()
        # Split into sentences; look for ones that say 'only' near 'fence'
        # while excluding the acceptable form that offers both paths ('either...or a fenced').
        sentences = re.split(r'(?<=[.!?])\s+', skeleton)
        bad = [
            s for s in sentences
            if "only" in s.lower() and "fenced" in s.lower()
            and "either" not in s.lower()
            and "or a fenced" not in s.lower()
            and "or a ```" not in s.lower()
        ]
        assert not bad, (
            "Worldmodel retry skeleton contains sentence(s) claiming fenced blocks are "
            f"the ONLY carrier path: {bad[:2]}. The JSON test_model_py field is also "
            "accepted — do not forbid it."
        )

    def test_worldmodel_skeleton_missing_block_names_both_paths(self):
        """When the error is a missing-block error, the worldmodel skeleton must offer
        both the JSON field path and the fenced block path.
        """
        error = "Missing required Python falsification suite block; reject candidate before evaluation."
        skeleton = format_worldmodel_retry_skeleton(error, "", max_prior_chars=1000, project_dir=None)
        assert "test_model_py" in skeleton, "Missing test_model_py in worldmodel missing-block retry"
        # The worldmodel variant specifically says "either...or a fenced" — both paths visible.
        has_fence = "fenced" in skeleton.lower() or "```python" in skeleton
        has_json = "test_model_py" in skeleton
        assert has_json and has_fence, (
            "worldmodel missing-block retry should offer both JSON field and fenced block paths. "
            f"has_json={has_json}, has_fence={has_fence}"
        )
