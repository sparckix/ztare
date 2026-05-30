from src.ztare.gates.claim_polarity import (
    ast_rejection_string_lines,
    hard_positive_phrase_group_labels,
    positive_phrase_group_labels,
)


BANNED = {
    "degree-only scaling": ("degree-only", "q>p", "degree domination"),
    "uncharged arbitrary observable": (
        "arbitrary observable",
        "free-choice certificate",
        "uncharged matrix",
    ),
}


def test_ast_rejection_key_marks_child_strings_not_positive_claims():
    source = """
def admissible_observable_class():
    return {
        "forbidden": [
            "arbitrary uncharged matrix observables",
            "degree-only q>p argument",
        ],
        "not_claimed": [
            "uncharged matrix-observable theorem",
        ],
    }
"""

    lines = ast_rejection_string_lines(source)

    assert lines
    assert positive_phrase_group_labels(source, BANNED, ast_rejection_lines=lines) == []


def test_positive_claims_still_fail_even_with_nearby_safety_prose():
    source = """
def trackb_convexity_theorem():
    return {
        "scope": "not a Clay proof",
        "claim": "tax degree q>p proves the theorem",
    }
"""

    assert positive_phrase_group_labels(source, BANNED) == ["degree-only scaling"]


def test_free_substring_does_not_hit_divergence_free_certificate():
    source = """
def theorem():
    return {
        "claim": "global smooth divergence-free certificate with charged matrix blocks",
    }
"""

    assert positive_phrase_group_labels(source, BANNED) == []


def test_positive_uncharged_certificate_claim_fails():
    source = """
def theorem():
    return {
        "claim": "uncharged matrix observable is allowed as a free-choice certificate",
    }
"""

    assert positive_phrase_group_labels(source, BANNED) == [
        "uncharged arbitrary observable"
    ]


def test_split_python_string_rejection_is_not_positive_claim():
    source = '''
def vector_ledger_terms():
    return {
        "sharp_constant_burden": (
            "The exact root is required; degree-only "
            "q>p scaling is insufficient."
        ),
    }
'''

    assert positive_phrase_group_labels(source, BANNED) == []


def test_assertion_probe_string_is_not_positive_claim():
    source = '''
def vector_ledger_terms():
    return {
        "sharp_constant_burden": (
            "The exact root is required; degree-only "
            "q>p scaling is insufficient."
        ),
    }

assert "degree-only" in vector_ledger_terms()["sharp_constant_burden"]
'''

    assert positive_phrase_group_labels(source, BANNED) == []


def test_fails_if_key_marks_child_strings_not_positive_claims():
    source = '''
def named_discriminator():
    return {
        "fails_if": (
            "A claimed proof relies only on finite audits, scalar control, "
            "or degree-only q>p scaling."
        ),
    }
'''

    assert positive_phrase_group_labels(source, BANNED) == []


def test_not_accepted_as_key_marks_child_strings_not_positive_claims():
    source = '''
def accepted_bridge_outcome():
    return {
        "not_accepted_as": [
            "Clay proof",
            "global regularity proof",
            "degree-only q>p theorem",
        ],
    }
'''

    assert ast_rejection_string_lines(source)
    assert positive_phrase_group_labels(source, BANNED) == []


def test_hard_positive_claim_blocks_affirmative_degree_only_claim():
    source = '''
def trackb_convexity_theorem():
    return {
        "claim": "tax degree q>p proves the theorem globally",
    }
'''

    assert hard_positive_phrase_group_labels(source, BANNED) == [
        "degree-only scaling"
    ]


def test_hard_positive_claim_ignores_ambiguous_protocol_mentions():
    source = '''
def known_technique_resolution_rule():
    return {
        "rejected_promotion_conditions": [
            "finite cutoff only",
            "degree-only q>p scaling",
        ],
        "note": "degree-only q>p scaling is a known failure mode.",
    }
'''

    assert hard_positive_phrase_group_labels(source, BANNED) == []
