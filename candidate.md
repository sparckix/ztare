# Pricing Intelligence: Scale Only on Incremental Customer-Economic Discovery

## Decision

Fund the 12-week, six-service pilot as a reversible evidence-acquisition bet. Scale is prohibited unless the pilot both passes the charter and causally demonstrates an incremental, material customer-economic issue that the registered existing-workflow counterfactual missed before approval or launch. Discovery-mode failure records informed this repair; they are not pilot evidence or a clean-transfer result.

## Conditional claim and mechanism

If the shared layer finds, before approval or launch, at least one independently adjudicated material customer-economic issue that a comparable concurrent existing-workflow case does not find by the same deadline, and it also reduces fully burdened preparation labor while preserving decision quality and frozen primitive identity, then it improves pricing decisions under the six-service, approved-source, central-Pricing-operated pilot scope.

The mechanism is: reusable commercial identities and scenarios join rates, terms, and usage assumptions; deterministic comparison and simulation expose a cliff, surprise, or predictability failure; evidence-linked review surfaces it before commitment; decision memory makes the evidence and resolution reusable. Faster preparation, source linkage, issue coverage, or artifact production alone do not establish this mechanism.

## Rival hypothesis

The registered managed-Pricing workflow using existing documents, spreadsheets, and expert review finds the same material issues by the same decision deadline at comparable quality and fully burdened effort. The thesis predicts at least one stable-identity, material issue found in treatment before approval or launch but absent from the matched control record at its locked deadline; the rival predicts no such incremental issue after independent adjudication.

## Named discriminator: deadline-locked incremental issue-discovery test

Before assignment and before outcomes are inspected, the pilot evaluation owner registers comparable treatment/control cases, approval or launch deadlines, and an issue ledger schema. Each issue receives a stable identifier, affected customer scenario, economic consequence, evidence, discovery timestamp, discovering workflow, and disposition. An adjudicator independent of the product and case teams, blinded to workflow where artifacts permit, applies a pre-registered materiality rule: an issue is material only when its correction changes the customer charge, removes an avoidable cliff or surprise, or changes the accountable pricing approval or launch decision. Mere missing citations, broader coverage, or stylistic corrections do not qualify.

For every treatment candidate, the adjudicator searches the control's timestamped issue and review record using the pre-registered identity/equivalence rule. Incremental discovery passes only if: treatment recorded the issue before its locked approval/launch deadline; the matched control did not record an identical or equivalent issue by its same-stage locked deadline; records are complete; and the adjudicator confirms materiality and the claimed economic consequence. No suitable comparable case, incomplete control records, post-deadline discovery, or unresolved equivalence means this gate fails, not that the issue was missed.

## Forward observables

- **Incremental customer-economic discovery.** What: stable issue IDs, equivalence decisions, customer scenario, quantified or decision-changing consequence, timestamps, workflow assignment, deadlines, dispositions, and completeness attestations for matched cases. When: after both cases reach their pre-registered approval/launch deadline and independent adjudication closes. Direction: the thesis requires at least one qualifying treatment-only pre-deadline material issue; the rival is supported if controls find every equivalent issue by deadline or the comparison is indeterminate.

- **Causal efficiency.** What: contributor-level minutes for treatment and matched control across central Pricing, service teams, Finance, ingestion, reconciliation, verification, adapters, maintenance, remediation, and rework; balance/overlap diagnostics, an effect interval, and low/expected/high missing-time sensitivities. When: pilot close after registered completion events. Direction: the charter hurdle requires treatment median labor no more than half control median; causal support additionally requires a favorable informative interval, favorable high-cost sensitivity, adequate balance/overlap, complete accounting, and no worse quality countermetric. Otherwise efficiency is unproven.

- **Frozen identity-preserving reuse.** What: before first execution, the primitive owner freezes the governing job, owner and authority, input/output contracts, equality relation, invariants, prohibited changes, permitted adapters, and semantic hash. For each of three distinct service families, independent adjudication records execution hash, contract and invariant checks, adapter diff, semantic diff, family identity, adapter labor, verification labor, and total central effort. When: independent review closes after the third-family execution. Direction: reuse passes only if all three executions satisfy the frozen equality relation and invariants under the same semantic hash, use only permitted adapters, contain no bespoke redesign, fully account for adapter/verification work, and show complexity-adjusted central effort does not increase. Otherwise reuse fails.

- **Accountable adoption.** What: owner-signed records for at least five pricing decisions and artifact use by at least five participating teams, plus timestamped distinct later decisions showing repeat use by at least three stable teams. When: pilot close. Direction: signed decision use and qualifying repeat use support adoption; artifacts, demonstrations, logins, or multiple decisions by too few teams do not.

## Dependencies, veto, and decision rule

Operations owns the labor and record-completeness ledgers; the evaluation owner freezes matching, deadlines, equivalence, exclusions, and analysis; an independent adjudication owner rules on issue identity, timing, materiality, and primitive preservation; Finance validates economic consequences and burdening; the primitive owner freezes identity; service GMs or pricing owners sign decisions; the Central Pricing sponsor decides disposition.

The independent evidence auditor has the absolute evidentiary veto. The leverage required for a scale state-change is access to timestamped treatment and control records, contributor time capture, frozen protocols and primitive contract, named submitters, and signed completeness and adjudication attestations. The sponsor may fund the pilot but cannot waive a failed or indeterminate gate while claiming the shared layer works.

- **Scale:** only if every charter threshold, no-critical-unsupported-claim audit, incremental issue-discovery gate, causal-efficiency gate, quality countermetrics, adoption gate, and frozen-reuse gate passes.
- **Reshape as a managed Pricing service:** if accountable decisions and incremental material discovery pass but causal efficiency or frozen reuse fails.
- **Stop the platform bet:** if no qualifying incremental issue is found, existing tools find equivalents by deadline, records are insufficient, matched labor is not materially lower, sensitivity reverses direction, quality worsens, or reuse requires semantic redesign.
- **Revisit:** only with a new pre-registered cohort or corrected protocol that addresses the named failed condition; do not relabel or reinterpret the original cohort post hoc.

The pilot is reversible because it uses bounded adapters and does not replace a system of record. Broad integration, contractual dependency, mandatory migration, or irreversible customer pricing changes are prohibited before scale approval.

## WHAT THIS THESIS DOES NOT CURRENTLY PROVE

UNRESOLVED: realized downstream retention, revenue, or long-run customer welfare caused by correcting a discovered issue — no measurement protocol available. Excluded from scoring.

UNRESOLVED: parser and symlink robustness — no measurement protocol available. Excluded from scoring.

No staged pilot outcomes or counterexamples were materialized in this DISCOVERY workbench; every empirical claim above remains prospective.

```python
"""Prospective discriminator for the Pricing Intelligence pilot."""

PARAMETRIC_FORM = (
    "int(issue_incremental and efficiency_pass and quality_pass and "
    "reuse_pass and adoption_pass and charter_pass and audit_pass)"
)
MODEL_PARAMS = {}
PARAMETER_NAMES = []
INIT_RANGE = []

ISSUE_FIELDS = (
    "stable_id", "customer_scenario", "economic_consequence", "evidence",
    "discovery_timestamp", "workflow", "locked_deadline", "disposition",
    "materiality_ruling", "equivalence_ruling", "records_complete",
)
PRIMITIVE_FIELDS = (
    "governing_job", "owner", "authority", "input_contract",
    "output_contract", "equality_relation", "invariants", "semantic_hash",
    "permitted_adapters", "prohibited_changes", "execution_hash",
    "adapter_diff", "semantic_diff", "adapter_labor", "verification_labor",
)

def issue_incremental(features):
    treatment_predeadline = (
        features["treatment_found"]
        and features["treatment_discovery_time"] <= features["locked_deadline"]
    )
    return (
        treatment_predeadline
        and not features["control_equivalent_found_by_deadline"]
        and features["independent_materiality_confirmed"]
        and features["economic_consequence_confirmed"]
        and features["issue_equivalence_adjudicated"]
        and features["records_complete"]
    )

def I_model(features, params=None):
    gates = (
        issue_incremental(features),
        features["efficiency_pass"],
        features["quality_pass"],
        features["reuse_pass"],
        features["adoption_pass"],
        features["charter_pass"],
        features["audit_pass"],
    )
    return int(all(gates))

def thesis_and_rival(features):
    thesis = issue_incremental(features)
    rival = features["control_equivalent_found_by_deadline"]
    return thesis, rival

def reuse_preserved(features):
    return (
        features["distinct_families"] >= 3
        and features["same_semantic_hash"]
        and features["equality_and_invariants_pass"]
        and features["only_permitted_adapters"]
        and not features["bespoke_redesign"]
        and features["adapter_and_verification_labor_complete"]
        and features["complexity_adjusted_central_effort_nonincreasing"]
        and features["independent_adjudication_complete"]
    )

# UNRESOLVED: downstream retention, revenue, or long-run customer welfare.
# UNRESOLVED: parser and symlink robustness.

if __name__ == "__main__":
    base = {
        "treatment_found": True,
        "treatment_discovery_time": 5,
        "locked_deadline": 6,
        "control_equivalent_found_by_deadline": False,
        "independent_materiality_confirmed": True,
        "economic_consequence_confirmed": True,
        "issue_equivalence_adjudicated": True,
        "records_complete": True,
        "efficiency_pass": True,
        "quality_pass": True,
        "reuse_pass": True,
        "adoption_pass": True,
        "charter_pass": True,
        "audit_pass": True,
    }
    thesis, rival = thesis_and_rival(base)
    assert thesis and not rival
    assert I_model(base) == 1
    control_found = dict(base, control_equivalent_found_by_deadline=True)
    thesis, rival = thesis_and_rival(control_found)
    assert rival and not thesis
    assert I_model(control_found) == 0
    late = dict(base, treatment_discovery_time=7)
    assert not issue_incremental(late)
    incomplete = dict(base, records_complete=False)
    assert not issue_incremental(incomplete)
    reuse = {
        "distinct_families": 3,
        "same_semantic_hash": True,
        "equality_and_invariants_pass": True,
        "only_permitted_adapters": True,
        "bespoke_redesign": False,
        "adapter_and_verification_labor_complete": True,
        "complexity_adjusted_central_effort_nonincreasing": True,
        "independent_adjudication_complete": True,
    }
    assert reuse_preserved(reuse)
    assert not reuse_preserved(dict(reuse, same_semantic_hash=False))
```

## Logic DAG

[Operator-authored charter supplies prospective gates, not outcomes] -> [Pre-registered matched cases, locked deadlines, complete ledgers, and independent rulings] -> [A stable material customer-economic issue is found by treatment before approval/launch and no equivalent is found by control by the same-stage deadline] -> [The existing-workflow rival is ruled out for that issue] -> [Only with causal efficiency, quality, accountable adoption, frozen three-family reuse, all charter thresholds, and clean audit may the sponsor conclude that scale is justified]
