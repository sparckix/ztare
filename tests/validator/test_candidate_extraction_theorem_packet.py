from ztare.validator.candidate_extraction import (
    extract_best_python_candidate,
    preserve_theorem_packet_source,
)


THEOREM_RUBRIC = {
    "theorem_packet_contract": {
        "required_top_level_functions": [
            "vector_ledger_terms",
            "trackb_convexity_theorem",
        ]
    }
}


def test_theorem_packet_python_block_scores_as_candidate():
    raw = """```python
def vector_ledger_terms():
    return {}

def trackb_convexity_theorem():
    return {}
```"""

    extraction = extract_best_python_candidate(raw)

    assert extraction.python_code is not None
    assert "def vector_ledger_terms" in extraction.python_code


def test_theorem_packet_custom_required_functions_drive_block_selection():
    raw = """```python
PARAMETRIC_FORM = "features['x']"
def I_model(features): return features['x']
```

```python
def fixed_lp_bony_topology():
    return {}

def projected_transport_commutator_receipt():
    return {}
```"""
    rubric = {
        "theorem_packet_contract": {
            "required_top_level_functions": [
                "fixed_lp_bony_topology",
                "projected_transport_commutator_receipt",
            ]
        }
    }

    extraction = extract_best_python_candidate(raw, rubric)

    assert extraction.python_code is not None
    assert "def fixed_lp_bony_topology" in extraction.python_code
    assert "PARAMETRIC_FORM" not in extraction.python_code


def test_theorem_packet_source_is_preserved_when_prose_is_empty():
    python_code = """def vector_ledger_terms():
    return {}

def trackb_convexity_theorem():
    return {}
"""

    thesis = preserve_theorem_packet_source("", python_code, THEOREM_RUBRIC)

    assert "Theorem Packet Source" in thesis
    assert "def vector_ledger_terms" in thesis
    assert "def trackb_convexity_theorem" in thesis


def test_non_theorem_packet_still_strips_python_from_thesis():
    python_code = "def I_model(d, params=None):\n    return 0.5"

    thesis = preserve_theorem_packet_source("", python_code, {})

    assert thesis == ""


def test_strategy_receipt_docstring_wrapper_is_normalized_out_of_python():
    raw = '''```python
"""
STRATEGY_CARD_DISCHARGE: {"failure_family_sha":"abc","outcome":"blocked","observed_status":"x","evidence_refs":["r"]}

WORLD_MODEL_SPEC = {"always": []}

def step(grid, action, t):
    """
    carrier docstring
    """
    return tuple(tuple(row) for row in grid)
"""
```'''

    extraction = extract_best_python_candidate(raw, {"fit_expression_grammar": "grid_dsl"})

    assert extraction.python_code is not None
    assert extraction.auto_repaired is True
    assert extraction.clean_thesis.startswith("STRATEGY_CARD_DISCHARGE:")
    assert "STRATEGY_CARD_DISCHARGE" not in extraction.python_code
    assert extraction.python_code.startswith("WORLD_MODEL_SPEC")
    assert '"""' in extraction.python_code
    compile(extraction.python_code, "<candidate>", "exec")


def test_strategy_receipt_alias_line_is_normalized_out_of_python():
    raw = '''```python
STRATEGY_CARD_RECEIPT: {"failure_family_sha":"abc","outcome":"blocked","observed_status":"x","evidence_refs":["r"]}

def step(grid, action, t):
    return grid
```'''

    extraction = extract_best_python_candidate(raw, {"fit_expression_grammar": "grid_dsl"})

    assert extraction.auto_repaired is True
    assert extraction.clean_thesis.startswith("STRATEGY_CARD_RECEIPT:")
    assert "STRATEGY_CARD_RECEIPT" not in extraction.python_code
    compile(extraction.python_code or "", "<candidate>", "exec")
