"""GP-046 first-slice asymptotic-claim discipline helpers.

Minimal A ships here:
- operator-declared charter contract is the canonical project-typing surface
- strong candidate-side asymptotic self-claims still cap score even when the
  charter omitted the flag (the silent-omission path GP-045 exposed)
- weaker undeclared signals emit warnings only

The farther-tail holdout itself remains a sandbox / harness concern. This
module only decides whether a missing farther-tail contract should cap score
or emit a warning.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from src.ztare.validator.core.charter_parsing import AsymptoticClaimContract
from src.ztare.fit.fit_primitive import parse_fit_declaration


LOCAL_TAIL_SURROGATE_CAP = 83
"""Cap used when a thesis asks for asymptotic / global-law credit without a
declared farther-tail contract. 83 matches the existing "real current signal,
but decisive mechanism credit is deferred" cap family in ``test_thesis.py``."""

_OFFSET_LIKE_PARAM_RE = re.compile(r"(floor|offset|baseline)", re.IGNORECASE)
_ASYMPTOTIC_LANGUAGE_RE = re.compile(
    r"\basymptot(?:e|ic)\b|"
    r"phi\s*->\s*infinity|"
    r"phi\s+approach(?:es)?\s+infinity|"
    r"\bglobal(?:-|\s)?law\b|"
    r"\bglobal(?:-|\s)?tail\b|"
    r"\basymptotic\s+floor\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AsymptoticClaimAssessment:
    contract_declared: bool
    asymptotic_claim_declared: bool
    farther_tail_contract_declared: bool
    fit_declaration_present: bool
    offset_like_parameter_names: tuple[str, ...]
    thesis_asymptotic_language_detected: bool
    candidate_any_signal: bool
    candidate_strong_signal: bool
    warning_only: bool
    local_tail_downgrade_applied: bool
    silent_omission_path_detected: bool
    cap: int | None
    reason: str

    def to_dict(self) -> dict:
        return {
            "contract_declared": self.contract_declared,
            "asymptotic_claim_declared": self.asymptotic_claim_declared,
            "farther_tail_contract_declared": self.farther_tail_contract_declared,
            "fit_declaration_present": self.fit_declaration_present,
            "offset_like_parameter_names": list(self.offset_like_parameter_names),
            "thesis_asymptotic_language_detected": self.thesis_asymptotic_language_detected,
            "candidate_any_signal": self.candidate_any_signal,
            "candidate_strong_signal": self.candidate_strong_signal,
            "warning_only": self.warning_only,
            "local_tail_downgrade_applied": self.local_tail_downgrade_applied,
            "silent_omission_path_detected": self.silent_omission_path_detected,
            "cap": self.cap,
            "reason": self.reason,
        }


def assess_asymptotic_claim_discipline(
    thesis_text: str,
    contract: AsymptoticClaimContract,
) -> AsymptoticClaimAssessment:
    """Classify whether GP-046 first-slice downgrade / warning should fire."""

    fit_declaration_present = False
    offset_like_parameter_names: tuple[str, ...] = ()
    try:
        declaration = parse_fit_declaration(thesis_text)
    except Exception:
        declaration = None
    if declaration is not None:
        fit_declaration_present = True
        offset_like_parameter_names = tuple(
            name
            for name in declaration.parameter_names
            if _OFFSET_LIKE_PARAM_RE.search(name)
        )

    thesis_asymptotic_language_detected = bool(_ASYMPTOTIC_LANGUAGE_RE.search(thesis_text or ""))
    candidate_any_signal = bool(offset_like_parameter_names) or thesis_asymptotic_language_detected
    candidate_strong_signal = bool(offset_like_parameter_names) and thesis_asymptotic_language_detected
    missing_farther_tail_contract = not contract.farther_tail_contract

    operator_trigger = (
        contract.asymptotic_claim
        and candidate_any_signal
        and missing_farther_tail_contract
    )
    silent_omission_trigger = candidate_strong_signal and missing_farther_tail_contract
    local_tail_downgrade_applied = operator_trigger or silent_omission_trigger
    warning_only = candidate_any_signal and missing_farther_tail_contract and not local_tail_downgrade_applied

    reason = ""
    cap = None
    if local_tail_downgrade_applied:
        cap = LOCAL_TAIL_SURROGATE_CAP
        reason = (
            "GP-046 asymptotic-claim discipline: candidate asks for asymptotic / global-law "
            "credit without a declared farther-tail contract, so claim scope is downgraded "
            "to a local late-tail surrogate."
        )
    elif warning_only:
        reason = (
            "GP-046 asymptotic-claim discipline warning: candidate contains a floor/offset-like "
            "term or asymptotic language, but no declared farther-tail contract is present."
        )

    return AsymptoticClaimAssessment(
        contract_declared=contract.declared,
        asymptotic_claim_declared=contract.asymptotic_claim,
        farther_tail_contract_declared=contract.farther_tail_contract,
        fit_declaration_present=fit_declaration_present,
        offset_like_parameter_names=offset_like_parameter_names,
        thesis_asymptotic_language_detected=thesis_asymptotic_language_detected,
        candidate_any_signal=candidate_any_signal,
        candidate_strong_signal=candidate_strong_signal,
        warning_only=warning_only,
        local_tail_downgrade_applied=local_tail_downgrade_applied,
        silent_omission_path_detected=silent_omission_trigger and not contract.asymptotic_claim,
        cap=cap,
        reason=reason,
    )
