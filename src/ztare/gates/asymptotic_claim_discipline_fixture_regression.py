"""Fixture regression for GP-046 first-slice asymptotic-claim discipline."""

from __future__ import annotations

import sys

from src.ztare.gates.asymptotic_claim_discipline import (
    LOCAL_TAIL_SURROGATE_CAP,
    assess_asymptotic_claim_discipline,
)
from src.ztare.validator.charter_parsing import (
    AsymptoticClaimContract,
    extract_asymptotic_claim_contract_from_charter,
)


_THESIS_WITH_STRONG_SIGNAL = """\
Claim: the model has a psi-dependent asymptotic floor as phi -> infinity.

```fit_declaration
{
  "expression": "Floor_offset + Amp * phi / (1 + K * phi)",
  "independent_vars": ["phi", "psi"],
  "parameter_names": ["Floor_offset", "Amp", "K"]
}
```
"""

_THESIS_WITH_OFFSET_ONLY = """\
Local tail description only.

```fit_declaration
{
  "expression": "offset + Amp * phi",
  "independent_vars": ["phi"],
  "parameter_names": ["offset", "Amp"]
}
```
"""


def test_parse_absent_contract_returns_defaults() -> None:
    contract = extract_asymptotic_claim_contract_from_charter("# Charter\n")
    assert contract == AsymptoticClaimContract()


def test_parse_contract_section_reads_bools() -> None:
    charter = """\
## Asymptotic Claim Contract

```yaml
asymptotic_claim: true
farther_tail_contract: false
```
"""
    contract = extract_asymptotic_claim_contract_from_charter(charter)
    assert contract.declared is True
    assert contract.asymptotic_claim is True
    assert contract.farther_tail_contract is False


def test_strong_signal_without_charter_flag_caps_score() -> None:
    assessment = assess_asymptotic_claim_discipline(
        _THESIS_WITH_STRONG_SIGNAL,
        AsymptoticClaimContract(),
    )
    assert assessment.local_tail_downgrade_applied is True
    assert assessment.silent_omission_path_detected is True
    assert assessment.cap == LOCAL_TAIL_SURROGATE_CAP


def test_operator_declared_path_caps_without_farther_tail_contract() -> None:
    assessment = assess_asymptotic_claim_discipline(
        _THESIS_WITH_OFFSET_ONLY,
        AsymptoticClaimContract(
            declared=True,
            asymptotic_claim=True,
            farther_tail_contract=False,
        ),
    )
    assert assessment.local_tail_downgrade_applied is True
    assert assessment.cap == LOCAL_TAIL_SURROGATE_CAP
    assert assessment.silent_omission_path_detected is False


def test_warning_only_for_weak_undeclared_signal() -> None:
    assessment = assess_asymptotic_claim_discipline(
        _THESIS_WITH_OFFSET_ONLY,
        AsymptoticClaimContract(),
    )
    assert assessment.warning_only is True
    assert assessment.local_tail_downgrade_applied is False
    assert assessment.cap is None


def test_farther_tail_contract_clears_cap() -> None:
    assessment = assess_asymptotic_claim_discipline(
        _THESIS_WITH_STRONG_SIGNAL,
        AsymptoticClaimContract(
            declared=True,
            asymptotic_claim=True,
            farther_tail_contract=True,
        ),
    )
    assert assessment.local_tail_downgrade_applied is False
    assert assessment.warning_only is False
    assert assessment.cap is None


_TESTS = (
    test_parse_absent_contract_returns_defaults,
    test_parse_contract_section_reads_bools,
    test_strong_signal_without_charter_flag_caps_score,
    test_operator_declared_path_caps_without_farther_tail_contract,
    test_warning_only_for_weak_undeclared_signal,
    test_farther_tail_contract_clears_cap,
)


def main() -> int:
    failed = 0
    for test in _TESTS:
        try:
            test()
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc}")
        except Exception as exc:
            failed += 1
            print(f"ERROR {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {test.__name__}")
    print(f"\n{len(_TESTS) - failed}/{len(_TESTS)} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
