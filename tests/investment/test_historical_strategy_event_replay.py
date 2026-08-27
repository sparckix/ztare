from ztare.investment.historical_strategy_event_replay import (
    _semantic_resolution_matches,
    classify_sec_item_201,
)


def test_semantic_resolution_survives_source_epoch_event_rehash():
    classification = {
        "filing_document_sha256": "filing",
        "classification_receipt_sha256": "classification",
        "event_sha256": "new-epoch-event",
    }
    semantic = {
        "filing_document_sha256": "filing",
        "deterministic_classification_receipt_sha256": "classification",
        "event_sha256": "prior-epoch-event",
    }

    assert _semantic_resolution_matches(semantic, classification)
    assert not _semantic_resolution_matches(
        {**semantic, "deterministic_classification_receipt_sha256": "other"},
        classification,
    )


def test_sec_item_201_classifier_uses_only_filed_transaction_language():
    acquisition = classify_sec_item_201(b"""
        <h2>Item 2.01 Completion of Acquisition or Disposition of Assets</h2>
        <p>The Company completed its previously announced acquisition of Target.</p>
        <h2>Item 9.01 Financial Statements and Exhibits</h2>
    """)
    disposition = classify_sec_item_201(b"""
        <h2>Item 2.01 Completion of Acquisition or Disposition of Assets</h2>
        <p>The registrant completed the sale of its legacy division.</p>
    """)

    assert acquisition["classification"] == "acquisition_completion"
    assert disposition["classification"] == "disposition_completion"
    assert acquisition["llm_used"] is disposition["llm_used"] is False

    separation = classify_sec_item_201(b"""
        <h2>Item 2.01 Completion of Acquisition or Disposition of Assets</h2>
        <p>The Company completed the separation of its services business through a
        distribution to its stockholders.</p>
    """)
    financing = classify_sec_item_201(b"""
        <h2>Item 2.01 Completion of Acquisition or Disposition of Assets</h2>
        <p>RPI purchased rights under a Revenue Participation Right Purchase Agreement.</p>
    """)
    bad_index_row = classify_sec_item_201(b"<h2>Item 2.02 Results of Operations</h2>")

    assert separation["classification"] == "separation_completion"
    assert separation["issuer_role"] == "separating_parent"
    assert financing["strategy_event_eligibility"] == "excluded_financial_rights_transfer"
    assert bad_index_row["transaction_form"] == "non_event_document"
