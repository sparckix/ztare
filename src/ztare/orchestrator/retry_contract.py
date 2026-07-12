from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


RetryPriorMode = Literal["verbatim", "summary"]


@dataclass(frozen=True)
class RetryContractSurface:
    """Common R1 retry envelope across substrate submission contracts.

    The substrate adapter owns carrier examples and rules. This renderer owns
    the retry boundary: error, strike history, output contract, free-retry
    status, and prior-submission carry-through.
    """

    rejected_subject: str
    error_text: str
    error_history: str = ""
    body: str = ""
    resubmit_instruction: str = "RESUBMIT THE COMPLETE SUBMISSION."
    prior_heading: str = "Your prior submission was:"
    prior_content: str = ""
    prior_mode: RetryPriorMode = "verbatim"
    scientific_failure_phrase: str = (
        "rejected by the R1 lint check; this is a contract boundary, not a "
        "gate verdict"
    )
    free_retry_sentence: str = (
        "The iteration counter has NOT advanced; this is a free retry."
    )


def render_retry_contract_surface(surface: RetryContractSurface) -> str:
    intro = (
        f"Your prior {surface.rejected_subject} was "
        f"{surface.scientific_failure_phrase}. Specific error:\n\n"
        f"  {surface.error_text}\n\n"
        f"{surface.error_history}"
    )
    body = surface.body.rstrip()
    resubmit = (
        f"{surface.resubmit_instruction.rstrip()} "
        f"{surface.free_retry_sentence}\n\n"
    )
    prior = _render_prior(
        heading=surface.prior_heading,
        content=surface.prior_content,
        mode=surface.prior_mode,
    )
    return intro + (body + "\n\n" if body else "") + resubmit + prior


def _render_prior(*, heading: str, content: str, mode: RetryPriorMode) -> str:
    if not heading:
        return content
    if mode == "summary":
        return f"{heading}\n{content.rstrip()}\n"
    return f"{heading}\n```\n{content}\n```\n"
