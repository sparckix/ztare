from __future__ import annotations

import hashlib
import json

import pytest

from ztare.leanmill.contracts.axiom_pack_transport import (
    AxiomPackTransportContract,
    band_word_output_schema,
)


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _transport() -> AxiomPackTransportContract:
    view = {"schema": "safe"}
    return AxiomPackTransportContract(
        proposer_view_digest=_digest(view),
        source_catalog={"source": {"schema": "source", "ref": "source"}},
    )


def _row() -> dict[str, str]:
    return {
        "source_ref": "source",
        "axiom_name": "delete_repeat",
        "lhs_word": "xyx",
        "rhs_word": "xy",
        "nl_intent": "delete one repeated occurrence",
        "kill_condition": "a countermodel rejects it",
    }


def test_band_transport_requires_exactly_one_proposal() -> None:
    assert band_word_output_schema()["properties"]["typed_axiom_proposals"]["maxItems"] == 1
    transport = _transport()
    decoded = transport.decode(json.dumps({"typed_axiom_proposals": [_row()]}))
    assert decoded["typed_axiom_proposals"][0]["typed_axiom_proposal"]["axiom"]["name"] == "delete_repeat"

    with pytest.raises(ValueError, match="exactly_one_typed_axiom_proposal_required"):
        transport.decode(json.dumps({"typed_axiom_proposals": [_row(), _row()]}))


def test_band_transport_owns_its_prompt_codec() -> None:
    transport = _transport()
    prompt = transport.render_prompt({"schema": "safe"})
    assert "lhs_word" in prompt
    assert "typed_axiom_proposal`" not in prompt

    with pytest.raises(ValueError, match="frozen transport"):
        transport.render_prompt({"schema": "changed"})
