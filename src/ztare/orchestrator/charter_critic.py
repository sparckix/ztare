"""GP-226 Charter-Critic V1 — post-run closed-loop charter tuning.

Implements the V1 architecture from
``research_areas/private/seams/reflexive/GP-226_charter_critic_role_seam.md``.

**V1 scope.** Post-run dispatch only. Fires at run-end after
``_finalize_run_telemetry_once()`` from inside ``run_post_loop_analyses``.
In-iter / mid-run firing is V3.

**What it does.** Reads (charter, rubric, evidence, debate logs,
operator_value_spec.yaml) and emits a structured ``CharterPatch`` that
either auto-commits (mode=auto) or writes a candidate file for operator
review (mode=advisory).

**Trigger.** Rubric flag ``enable_charter_critic: true`` AND a
``projects/<slug>/operator_value_spec.yaml`` exists.

**Substrate scoping.** The reframe-type taxonomy is keyed by
``operator_value_spec.yaml::substrate_class``. V1 ships starter taxonomies
for qualitative-thesis and proof-target substrates; other substrate classes
start with empty taxonomies (per seam §4k cross-project contamination
mitigation).

**No-LLM design.** V1 is fully deterministic — fingerprint matching uses
regex + bigram-Jaccard against curated phrasings; patch templates are
hard-coded prose. Heavy LLM-assisted patches (cold-shot) are V2.
"""
from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib as _hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Literal


# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

PATCH_SIZE_BYTES_MAX = 4096
DEFAULT_MAX_PATCHES_PER_RUN = 3
DEFAULT_PATCH_EXPIRY_RUNS = 5
DEFAULT_K_DEBATES_TO_READ = 5
ADVISORY_PATCH_FILENAME = "charter_patch_candidate_{run_id}.md"
AUTO_PATCH_LEDGER = "charter_patches.jsonl"

# Charter-contamination keyword denylist — patch body MUST NOT contain these.
# Mirrors the spirit of _preflight_leak_audit + the canonical
# charter_contamination feedback memory.
GT_LEAK_PATTERNS = [
    r"\bground[_\s-]*truth\b",
    r"\b_ground_truth\b",
    r"\bGT\s*=",
    r"\bC[0-9]+\s*=",
    r"\bMODEL_PARAMS\b\s*=\s*\{[^}]*[0-9]\.[0-9]{3}",
]


# ----------------------------------------------------------------------------
# Dataclasses
# ----------------------------------------------------------------------------

@dataclasses.dataclass
class CharterPatch:
    """A typed, sized, sanitation-checked charter patch."""
    target: Literal["evidence", "charter", "rubric_dimension"]
    section_id: str
    operation: Literal["append", "replace", "amend"]
    body: str
    reframe_type: str
    expiry_runs: int
    fingerprint_match: dict[str, Any]   # which fingerprint, similarity, source-debate-iter
    sanitation_checks_passed: list[str]
    created_run_id: str
    created_utc: str

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @property
    def body_sha(self) -> str:
        return _hashlib.sha256(self.body.encode("utf-8")).hexdigest()[:12]


# ----------------------------------------------------------------------------
# Reframe-type taxonomy registry (substrate-class indexed)
# ----------------------------------------------------------------------------

# Each reframe type: (regex patterns matching the panel's stuck-on phrasings,
# bigram-Jaccard similarity threshold, patch template fn).
# Patch templates take (project_slug, recent_weakest_points, value_spec)
# and return a (target, section_id, operation, body) tuple.

ReframeTaxonomy = dict[str, dict[str, Any]]

# ----------------------------------------------------------------------------
# PRIMITIVE LAYER (compression added 2026-05-06 PM after operator observed
# the taxonomy keeps growing per run; fingerprints fall through bucket-level
# regex but cluster around 3 underlying epistemic moves the panel demands.
# Per feedback_invert_compress_primitives + principle_vs_instantiation:
# strip the proper nouns, what's left is the principle.)
# ----------------------------------------------------------------------------

# Three primitives the panel can demand on a qualitative-thesis substrate:
#   DERIVE   — claim must be derived from neutral structure, not asserted
#   BOUND    — claim must specify scope/conditions under which it holds
#   OBSERVE  — variables/parameters in the claim must be empirically tractable
#
# Every bucket is an instantiation of one of these. Unmatched fingerprints
# can fall through bucket-level regex but still classify into a primitive
# via the primitive-level patterns below.

PRIMITIVE_DERIVE = "DERIVE"
PRIMITIVE_BOUND = "BOUND"
PRIMITIVE_OBSERVE = "OBSERVE"

PRIMITIVE_REGEX: dict[str, list[str]] = {
    PRIMITIVE_DERIVE: [
        r"\basserted\s+(rather\s+than|not)\s+derived",
        r"derivation\s+(missing|absent|incomplete)",
        r"smuggled\s+(primitive|vocabulary|assumption)",
        r"presupposes?\s+the\s+(answer|conclusion|claim)",
        r"vocabulary\s+importation",
        r"regression\s+to\s+(tool|labor[\s-]*economics)",
        r"reduces?\s+to\s+(known|prior|existing)",
        r"not\s+structurally\s+novel",
    ],
    PRIMITIVE_BOUND: [
        r"\b(level|scope)[\s-]*bound\b",
        r"under[\s-]*specified\s+(boundary|scope|range)",
        r"durabil(e|ity)\s+(claim|argument|assumption)",
        r"contingent\s+(on|upon)",
        r"may\s+(dissolve|erode|invalidate)",
        r"(rate|rate of|rapidity of)\s+(policy|regulatory|capability|adoption)\s+(convergence|change|shift)",
        r"hard\s+upper\s+bound",
        r"transient\s+regime[\s-]*shift",
        r"single[\s-]*mode\s+(dogma|claim)",
        r"task[\s-]*class\s+(typology|decomposition)",
        r"vague\s+affordance",
        r"abstract\s+category\s+only",
        r"empirically\s+fragile",
        r"no\s+(historical|empirical)\s+precedent",
    ],
    PRIMITIVE_OBSERVE: [
        r"\bestimab(le|ility)\b",
        r"systematically\s+undercount",
        r"non[\s-]*observ(able|ability)",
        r"hard\s+to\s+(validate|measure|bound|estimate)",
        r"silent(ly)?\s+(errors?|fail|undetect)",
        r"\bendogen(ous|eity)\b",
        r"\bexogenous(ly)?\s+(and\s+)?fixed\b",
        r"positive\s+feedback",
        r"reflex(ive|ivity)",
        r"observer[\s-]*effect",
        r"adversarial\s+drift",
        r"taxonomy\s+blindness",
        r"the\s+intervention\s+(itself\s+)?changes",
    ],
}


def classify_into_primitive(text: str) -> tuple[str | None, str]:
    """Primitive-level classification fallback for fingerprints that
    don't match any specific bucket. Returns (primitive_name, reason)
    or (None, '') if no primitive matches."""
    text_lower = text.lower()
    for primitive, patterns in PRIMITIVE_REGEX.items():
        for pat in patterns:
            if re.search(pat, text_lower, re.IGNORECASE):
                return primitive, f"primitive:{primitive}:regex:{pat}"
    return None, ""


def primitive_for_bucket(reframe_type: str, taxonomy: ReframeTaxonomy) -> str | None:
    """Return the primitive that a bucket instantiates. Annotated on each
    bucket entry as `primitive: DERIVE|BOUND|OBSERVE`."""
    spec = taxonomy.get(reframe_type) or {}
    return spec.get("primitive")


QUALITATIVE_THESIS_TAXONOMY: ReframeTaxonomy = {
    "literature_transfer_engagement": {
        "regex_patterns": [
            r"regression\s+to\s+(tool|labor[\s-]*economics|economic)\s+discourse",
            r"vanilla\s+labor\s+economics",
            r"not\s+structurally\s+unique\s+to\s+AI",
            r"reduces?\s+to\s+principal[\s-]*agent",
        ],
        "phrasing_corpus": [
            "regression to tool discourse",
            "regression to labor-economics discourse",
            "this is just labor allocation",
            "the asymmetry is not structurally unique to AI",
            "reduces to principal-agent theory",
        ],
        "jaccard_threshold": 0.42,
        "patch_target": "evidence",
        "patch_template_fn": "_template_literature_transfer_engagement",
        "primitive": PRIMITIVE_DERIVE,
    },
    "named_historical_retrodiction": {
        "regex_patterns": [
            r"empirically\s+fragile",
            r"historically\s+rare",
            r"no\s+(historical|empirical)\s+precedent",
            r"under[\s-]*argued\s+(durability|empirical)",
            r"insufficient\s+(empirical|grounding)",
        ],
        "phrasing_corpus": [
            "empirically fragile",
            "no historical precedent",
            "historically rare and reversible",
            "under-argued durability claim",
            "insufficient empirical grounding",
        ],
        "jaccard_threshold": 0.40,
        "patch_target": "evidence",
        "patch_template_fn": "_template_named_historical_retrodiction",
        "primitive": PRIMITIVE_BOUND,
    },
    "velocity_vs_level_disclosure": {
        "regex_patterns": [
            r"level[\s-]*bound",
            r"capability\s+(advance|shift)\s+could\s+erode",
            r"transient\s+regime[\s-]*shift",
            r"does\s+not\s+engage\s+(velocity|capability)",
        ],
        "phrasing_corpus": [
            "level-bound to current capability",
            "transient regime-shift not structural",
            "does not engage capability shift",
            "rapid capability advance could erode",
        ],
        "jaccard_threshold": 0.42,
        "patch_target": "charter",
        "patch_template_fn": "_template_velocity_vs_level_disclosure",
        "primitive": PRIMITIVE_BOUND,
    },
    "ui_affordance_specification": {
        "regex_patterns": [
            r"vague\s+affordance",
            r"no\s+concrete\s+(UI|interface|affordance)",
            r"abstract\s+category\s+only",
            r"does\s+not\s+specify\s+(UI|interface)",
        ],
        "phrasing_corpus": [
            "vague affordance",
            "no concrete UI specified",
            "abstract category without interface specification",
            "does not specify what the user sees",
        ],
        "jaccard_threshold": 0.42,
        "patch_target": "rubric_dimension",
        "patch_template_fn": "_template_ui_affordance_specification",
        "primitive": PRIMITIVE_BOUND,
    },
    "vocabulary_neutral_restate": {
        "regex_patterns": [
            r"vocabulary\s+importation",
            r"smuggled\s+(primitive|vocabulary)",
            r"phenomenal\s+vocabulary",
            r"presupposes?\s+the\s+(answer|conclusion)",
        ],
        "phrasing_corpus": [
            "vocabulary importation",
            "smuggled primitive in disguise",
            "presupposes the answer",
            "phenomenal vocabulary leaked into structural claim",
        ],
        "jaccard_threshold": 0.42,
        "patch_target": "charter",
        "patch_template_fn": "_template_vocabulary_neutral_restate",
        "primitive": PRIMITIVE_DERIVE,
    },
    "task_class_decomposition_forcing": {
        "regex_patterns": [
            r"single[\s-]*mode\s+(dogma|claim)",
            r"no\s+task[\s-]*class\s+(typology|decomposition)",
            r"over[\s-]*fit(s|ted|ting)?\s+to\s+(developer|one)",
            r"M3\s+everywhere",
        ],
        "phrasing_corpus": [
            "single-mode dogma without typology",
            "no task-class decomposition",
            "overfits to developer workflows",
            "M3-everywhere claim",
        ],
        "jaccard_threshold": 0.42,
        "patch_target": "evidence",
        "patch_template_fn": "_template_task_class_decomposition_forcing",
        "primitive": PRIMITIVE_BOUND,
    },
    # Bucket #7 — added 2026-05-06 PM after run 1778093346 surfaced
    # measurement-fragility critiques that didn't fit any prior bucket.
    # The pattern: panel attacks the estimability/observability/auditability
    # of the decision-critical parameters in the thesis (e.g., ε exception-rate,
    # δ invisibility-rate, audit-coverage fraction) — not the structural
    # claim itself, but whether the variables on which the claim depends
    # are reliably measurable in deployment.
    "parameter_estimability_fragility": {
        "regex_patterns": [
            r"\bestimab(le|ility)\b",
            r"systematically\s+undercount",
            r"adversarial\s+drift",
            r"taxonomy\s+blindness",
            r"silent(ly)?\s+(errors?|fail|undetect)",
            r"hard\s+to\s+(validate|measure|bound|estimate)",
            r"context[\s-]*dependent.*validat",
            r"non[\s-]*observ(able|ability)",
            r"empirical(ly)?\s+(fragile|hard)",
            r"distributed,?\s+emergent",
        ],
        "phrasing_corpus": [
            "parameters are structurally hard to estimate",
            "exception rate is hard to estimate at scale",
            "measurement fragility under adversarial drift",
            "taxonomy blindness undercounts errors",
            "silent errors are not surfaced",
            "context-dependent validation is fragile",
            "decision-critical variables are not reliably observable",
            "audit coverage cannot be empirically bounded",
        ],
        "jaccard_threshold": 0.40,
        "patch_target": "evidence",
        "patch_template_fn": "_template_parameter_estimability_fragility",
        "primitive": PRIMITIVE_OBSERVE,
    },
    # Bucket #8 — added 2026-05-06 PM after run 1778095831 surfaced
    # endogeneity / reflexivity critique: thesis treats a control variable
    # (e.g., regulatory reversion hazard rate H) as exogenous when it is
    # actually endogenous to the interventions the thesis recommends. The
    # interventions themselves change the variable on which their success
    # depends. Classic dynamical-systems / observer-effect critique.
    "endogeneity_reflexivity": {
        "regex_patterns": [
            r"\bendogen(ous|eity|ous)\b",
            r"\bexogenous(ly)?\s+(and\s+)?fixed\b",
            r"positive\s+feedback",
            r"reflex(ive|ivity)",
            r"observer[\s-]*effect",
            r"\binverts?\s+the\s+(claim|verdict|argument)",
            r"the\s+intervention\s+(itself\s+)?changes",
            r"destabili[sz]es\s+the\s+transition",
            r"self[\s-]*defeat(s|ing|ed)?",
            r"endogen.*to\s+(the\s+)?(intervention|UI|policy)",
        ],
        "phrasing_corpus": [
            "treats the variable as exogenous when it is endogenous",
            "the intervention itself changes the variable",
            "positive feedback destabilizes the transition",
            "reflexivity inverts the claim",
            "observer-effect contamination",
            "intervention raises the hazard it is designed to mitigate",
            "self-defeating control structure",
        ],
        "jaccard_threshold": 0.40,
        "patch_target": "evidence",
        "patch_template_fn": "_template_endogeneity_reflexivity",
        "primitive": PRIMITIVE_OBSERVE,
    },
}

PROOF_TARGET_TAXONOMY: ReframeTaxonomy = {
    "proof_anchor_resolution": {
        "regex_patterns": [
            r"\bunresolved\s+(identifier|declaration|anchor|name)",
            r"\b(anchor|declaration|source)\s+(does\s+not|doesn't|did\s+not)\s+(resolve|exist)",
            r"\bhallucinat(ed|ed[-\s]*anchor|ory)\b",
            r"\bno\s+(lean|source|repo)\s+anchor\b",
            r"\bexact\s+(lean|source)\s+(anchor|declaration)\s+missing\b",
            r"\bmissing\s+(witness|proof\s+object|source\s+object|constructor)\b",
            r"\bno\s+constructive\s+(lean\s+)?proof\s+(currently\s+)?establishes\b",
            r"\bassumes?\s+\(?(but\s+)?does\s+not\s+construct\b",
            r"\bonly\s+type[-\s]*level\s+(connectivity|wrappers?|adapters?)\b",
            r"\bno\s+such\s+(object|declaration|witness)\s+exists\b",
        ],
        "phrasing_corpus": [
            "the proposed proof move cites a declaration that does not resolve",
            "candidate has no exact Lean source anchor",
            "the theorem name appears hallucinated or stale",
            "source evidence does not support the constructor",
            "only type-level adapters are present, not the field-level proof object",
            "missing witness blocks the closure move",
        ],
        "jaccard_threshold": 0.38,
        "patch_target": "evidence",
        "patch_template_fn": "_template_proof_anchor_resolution",
        "primitive": PRIMITIVE_DERIVE,
    },
    "proof_non_circularity": {
        "regex_patterns": [
            r"\bcircular(ity)?\b",
            r"\btautolog(y|ical)\b",
            r"\bproof[\s-]*by[\s-]*(assumption|definition)\b",
            r"\b(final|endpoint)\s+(premise|backflow|as\s+a\s+premise)",
            r"\buses?\s+the\s+(target|conclusion)\s+as\s+(premise|input)",
            r"\bself[\s-]*(reference|referential)\b",
        ],
        "phrasing_corpus": [
            "candidate uses the final endpoint as a premise",
            "proof route is circular or self-referential",
            "the construction proves the target by assuming it",
            "definition-level closure masks an unresolved source theorem",
        ],
        "jaccard_threshold": 0.36,
        "patch_target": "charter",
        "patch_template_fn": "_template_proof_non_circularity",
        "primitive": PRIMITIVE_DERIVE,
    },
    "proof_falsifier_first": {
        "regex_patterns": [
            r"\b(no|missing)\s+(falsifier|counterexample|escape\s+sequence|adversarial\s+case)",
            r"\bfalsifier\s+(missing|weak|absent|not\s+operational)",
            r"\bdoes\s+not\s+name\s+the\s+(escape|failure)\s+(mode|class)",
            r"\bno\s+negative\s+case\b",
        ],
        "phrasing_corpus": [
            "candidate does not name the escape sequence that would refute it",
            "falsifier is missing or not operational",
            "proof move lacks a negative case",
            "failure mode is not concrete enough to test",
        ],
        "jaccard_threshold": 0.38,
        "patch_target": "evidence",
        "patch_template_fn": "_template_proof_falsifier_first",
        "primitive": PRIMITIVE_OBSERVE,
    },
    "proof_executable_probe": {
        "regex_patterns": [
            r"\b(no|missing)\s+(command|probe|lake\s+build|compile|script)",
            r"\bnot\s+executable\b",
            r"\b(action|next\s+step)\s+(is\s+)?(vague|not\s+operational)",
            r"\bdoes\s+not\s+(run|refresh|compile|type[-\s]*check)\b",
        ],
        "phrasing_corpus": [
            "candidate gives no executable next command",
            "no lake build or type-check probe is specified",
            "next step is vague and cannot be run by an agent",
            "the graph or workmap refresh observable is missing",
        ],
        "jaccard_threshold": 0.38,
        "patch_target": "evidence",
        "patch_template_fn": "_template_proof_executable_probe",
        "primitive": PRIMITIVE_OBSERVE,
    },
    "proof_decomposition_gap": {
        "regex_patterns": [
            r"\bsemantic\s+gap\b",
            r"\btoo\s+(large|wide|broad)\b",
            r"\bmissing\s+(intermediate|stepping[-\s]*stone|source\s+constructor)",
            r"\bdecompose\s+the\s+(endpoint|obligation|target)",
            r"\btarget\s+surface\s+is\s+too\s+large\b",
        ],
        "phrasing_corpus": [
            "the target obligation is too large for a direct proof move",
            "missing intermediate source constructor",
            "decompose the endpoint into a smaller lemma",
            "semantic gap should be cut before another patch attempt",
        ],
        "jaccard_threshold": 0.38,
        "patch_target": "evidence",
        "patch_template_fn": "_template_proof_decomposition_gap",
        "primitive": PRIMITIVE_BOUND,
    },
    "proof_secondary_observable": {
        "regex_patterns": [
            r"\b(no|missing)\s+(secondary|downstream)\s+observable",
            r"\bworkmap\s+(delta|change|unchanged|not\s+refreshed)",
            r"\bgraph\s+(delta|refresh|unchanged|not\s+refreshed)",
            r"\bcompile\s+pass\s+only\b",
            r"\bno\s+closure\s+(delta|progress|metric)\b",
        ],
        "phrasing_corpus": [
            "candidate has no secondary observable beyond compiling",
            "workmap delta or graph refresh is missing",
            "proof move gives no closure metric change",
            "success criterion needs a downstream observable",
        ],
        "jaccard_threshold": 0.38,
        "patch_target": "evidence",
        "patch_template_fn": "_template_proof_secondary_observable",
        "primitive": PRIMITIVE_OBSERVE,
    },
}

# META_APPARATUS_AUDIT_TAXONOMY (v0_experimental, 2026-05-06 PM)
# Authored from observed failure modes across runs 1-4 of
# `ztare_on_ztare_v2_expanded_scope`. Per seam §4k anti-contamination
# rule, taxonomies should be authored after reframes fire productively
# across ≥2 substrates of the same class. We have ONE meta-apparatus-
# audit substrate, so this taxonomy is provisional. Patterns are
# phrased GENERICALLY (no ACRR/IAP/loop-revival-specific phrasing) so
# they should generalize to future meta-apparatus substrates.
#
# Activation: enabled when operator_value_spec.yaml's substrate_class
# is "meta_apparatus_audit". The LLM fingerprint classifier
# (enable_llm_fingerprint_classifier) provides tier-3 fallback when
# regex/Jaccard miss on substrate-specific vocabulary.

META_APPARATUS_AUDIT_TAXONOMY: ReframeTaxonomy = {
    "anchored_primitive_class": {
        "regex_patterns": [
            r"(?i)same\s+(primitive|mechanism|class)\s+for\s+\d+\s*iter",
            r"(?i)refining\s+(the\s+)?(same|prior|previous)\s+(primitive|class|mechanism)",
            r"(?i)anchored\s+on\s+\w+\s+(primitive|class)",
            r"(?i)(no|never)\s+(switched|rotated|alternative)\s+(primitive|class)",
        ],
        "phrasing_corpus": [
            "anchored on a single primitive class",
            "refining the same mechanism across iters",
            "no class rotation",
            "mutator stayed on prior primitive class",
            "did not propose alternative primitive class",
        ],
        "jaccard_threshold": 0.42,
        "patch_target": "charter",
        "patch_template_fn": "_template_anchored_primitive_class",
        "primitive": PRIMITIVE_BOUND,
    },
    "common_mode_unmitigated": {
        "regex_patterns": [
            r"(?i)common[\s-]*mode\s+(vulnerab|exploit|failure|risk)",
            r"(?i)(supply\s+chain|shared\s+infrastructure|software\s+library)\s+(overlap|dependency)",
            r"(?i)independence\s+(assumption|claim)\s+(critically|fundamentally)\s+depend",
            r"(?i)(single\s+point\s+of\s+failure|spof)\s+reintroduced",
        ],
        "phrasing_corpus": [
            "common-mode vulnerability not addressed",
            "independence assumption critically depends on shared infrastructure",
            "single point of failure reintroduced via supply chain",
            "common-mode exploit can break all redundant components simultaneously",
        ],
        "jaccard_threshold": 0.40,
        "patch_target": "evidence",
        "patch_template_fn": "_template_common_mode_unmitigated",
        "primitive": PRIMITIVE_BOUND,
    },
    "single_substrate_fix": {
        "regex_patterns": [
            r"(?i)single\s+substrate\s+fix",
            r"(?i)does\s+not\s+(generalize|transfer)\s+across\s+substrate",
            r"(?i)narrow\s+scope\s+to\s+\w+\s+substrate",
            r"(?i)substrate[\s-]*specific\s+(refinement|primitive|fix)",
        ],
        "phrasing_corpus": [
            "single-substrate fix; does not generalize",
            "narrow scope to one substrate class",
            "substrate-specific refinement; cross-substrate applicability not demonstrated",
            "applies only to one substrate kind",
        ],
        "jaccard_threshold": 0.42,
        "patch_target": "rubric_dimension",
        "patch_template_fn": "_template_single_substrate_fix",
        "primitive": PRIMITIVE_BOUND,
    },
    "kill_criterion_unmeasurable": {
        "regex_patterns": [
            r"(?i)kill[\s-]*criterion\s+(is\s+)?(unmeasurable|vague|open[\s-]*ended)",
            r"(?i)(threshold|deadline)\s+(not|absent|missing|unspecified)",
            r"(?i)(no|missing)\s+(named\s+)?(metric|measurement|deadline)",
            r"(?i)falsifier\s+(insufficient|too\s+vague|underspecified)",
        ],
        "phrasing_corpus": [
            "kill-criterion is unmeasurable as stated",
            "no specific metric or deadline named",
            "threshold not justified by any data",
            "falsifier underspecified, cannot be checked next cycle",
        ],
        "jaccard_threshold": 0.42,
        "patch_target": "rubric_dimension",
        "patch_template_fn": "_template_kill_criterion_unmeasurable",
        "primitive": PRIMITIVE_BOUND,
    },
    "ceremonial_form_overengineering": {
        "regex_patterns": [
            r"(?i)PARAMETRIC[_\s-]*FORM\s+(uses|calls|references)\s+(disallowed|unwhitelisted|forbidden)",
            r"(?i)R1\s+(compiler[\s-]*bounce|whitelist\s+fail)",
            r"(?i)over[\s-]*engineered\s+(form|stub)",
            r"(?i)(isinstance|sum|is_significant)\s+(in|inside)\s+PARAMETRIC",
        ],
        "phrasing_corpus": [
            "PARAMETRIC_FORM uses disallowed function",
            "R1 compiler-bounce on AST whitelist",
            "over-engineered ceremonial form",
            "complexity belongs in thesis prose, not PARAMETRIC_FORM",
        ],
        "jaccard_threshold": 0.40,
        "patch_target": "charter",
        "patch_template_fn": "_template_ceremonial_form_overengineering",
        "primitive": PRIMITIVE_OBSERVE,
    },
    "evidence_anchor_unverifiable": {
        "regex_patterns": [
            r"(?i)JSONPath\s+(does\s+not\s+resolve|fails|missing)",
            r"(?i)evidence\s+anchor\s+(unverifiable|wrong|stale)",
            r"(?i)cited\s+(file|path|key)\s+not\s+(found|present)",
            r"(?i)excerpt\s+does\s+not\s+match\s+(snapshot|file)",
        ],
        "phrasing_corpus": [
            "evidence anchor JSONPath does not resolve",
            "cited mining-output entry not found",
            "excerpt mismatch with snapshot file",
            "evidence anchor is hand-waved, not verifiable",
        ],
        "jaccard_threshold": 0.42,
        "patch_target": "rubric_dimension",
        "patch_template_fn": "_template_evidence_anchor_unverifiable",
        "primitive": PRIMITIVE_BOUND,
    },
    "compounding_unanchored": {
        "regex_patterns": [
            r"(?i)compounding\s+(claim|effect)\s+(not\s+measured|hand[\s-]*waved|speculative)",
            r"(?i)next[\s-]*week\s+(effect|impact)\s+(unanchored|speculative)",
            r"(?i)does\s+not\s+(name|cite)\s+(mining\s+output|next[\s-]*cycle\s+metric)",
            r"(?i)compounding\s+(without|missing)\s+(metric|measurement)",
        ],
        "phrasing_corpus": [
            "compounding claim not measured by any mining output",
            "next-week effect speculative, no anchored metric",
            "compounding hand-waved without naming the measurement",
            "claims gain in next mining cycle but does not name the cycle metric",
        ],
        "jaccard_threshold": 0.42,
        "patch_target": "rubric_dimension",
        "patch_template_fn": "_template_compounding_unanchored",
        "primitive": PRIMITIVE_OBSERVE,
    },
}


SUBSTRATE_TAXONOMIES: dict[str, ReframeTaxonomy] = {
    "qualitative_thesis": QUALITATIVE_THESIS_TAXONOMY,
    "proof_target": PROOF_TARGET_TAXONOMY,
    # Meta-apparatus-audit: provisional v0 taxonomy authored 2026-05-06
    # from runs 1-4 of ztare_on_ztare_v2_expanded_scope. Genericized
    # phrasing for cross-substrate generalization. LLM fingerprint
    # classifier handles substrate-specific vocabulary.
    "meta_apparatus_audit": META_APPARATUS_AUDIT_TAXONOMY,
    # Other substrate classes start with empty taxonomies. Real reframes
    # are registered as they fire productively across ≥2 substrates of
    # the same class (per seam §4k).
    "nd_features": {},
    "closed_form_constant": {},
    # `audit` historically empty; alias to meta_apparatus_audit when the
    # operator_value_spec uses the broader name.
    "audit": META_APPARATUS_AUDIT_TAXONOMY,
}


# ----------------------------------------------------------------------------
# Value-spec loader
# ----------------------------------------------------------------------------

def load_value_spec(
    project_dir: Path,
    rubric_data: dict[str, Any] | None = None,
    auto_generate: bool = True,
) -> dict[str, Any] | None:
    """Load operator_value_spec.yaml.

    If absent and ``auto_generate=True`` (default), generates a sensible
    default from the rubric's ``cage_meta.type`` and writes it to disk
    so the operator can edit. This eliminates the silent-skip UX gap
    when ``enable_charter_critic`` is set but the YAML doesn't exist.

    YAML parse via stdlib (no PyYAML hard-dep): supports the flat schema
    in the seam (top-level scalar/dict only; no anchors). PyYAML if
    importable.
    """
    spec_path = project_dir / "operator_value_spec.yaml"
    if not spec_path.exists():
        if not auto_generate:
            return None
        default_yaml = _generate_default_value_spec(rubric_data or {})
        spec_path.write_text(default_yaml, encoding="utf-8")
        # caller logs the generation; we just continue with the defaults
    text = spec_path.read_text(encoding="utf-8")

    try:
        import yaml as _pyyaml  # type: ignore[import-untyped]
        return dict(_pyyaml.safe_load(text) or {})
    except ImportError:
        pass

    return _parse_minimal_yaml(text)


_CAGE_META_TYPE_TO_SUBSTRATE_CLASS = {
    "qualitative_thesis": "qualitative_thesis",
    "qualitative_theory": "qualitative_thesis",
    "qualitative_audit": "audit",
    "audit": "audit",
    "proof_target": "proof_target",
    "proof_closure_strategy": "proof_target",
    "proof_closure": "proof_target",
    "lean_proof": "proof_target",
    "nd_features": "nd_features",
    "closed_form_constant": "closed_form_constant",
}


def _infer_substrate_class(rubric_data: dict[str, Any]) -> str:
    cage_meta = rubric_data.get("cage_meta") or {}
    cage_type = (cage_meta.get("type") or "").strip().lower() if isinstance(cage_meta, dict) else ""
    cage_class = (cage_meta.get("class") or "").strip().lower() if isinstance(cage_meta, dict) else ""
    if cage_type in _CAGE_META_TYPE_TO_SUBSTRATE_CLASS:
        return _CAGE_META_TYPE_TO_SUBSTRATE_CLASS[cage_type]
    if cage_class in _CAGE_META_TYPE_TO_SUBSTRATE_CLASS:
        return _CAGE_META_TYPE_TO_SUBSTRATE_CLASS[cage_class]
    falsification_mode = (rubric_data.get("falsification_mode") or "").strip().lower()
    if falsification_mode == "qualitative_thesis":
        return "qualitative_thesis"
    return "qualitative_thesis"  # safest default — at least has a populated taxonomy


def _generate_default_value_spec(rubric_data: dict[str, Any]) -> str:
    """Generate a default operator_value_spec.yaml as a YAML string.

    Substrate-class is inferred from rubric.cage_meta.type when possible.
    Weights are even-ish across the four canonical axes; constraints are
    the seam's anti-Goodhart defaults; mode is advisory.
    """
    substrate_class = _infer_substrate_class(rubric_data)
    return f"""# GP-226 charter-critic V1 — operator value-spec.
# Auto-generated default. Edit weights / constraints / mode to customize.
# Substrate-class inferred from rubric.cage_meta; check it matches your intent.

substrate_class: {substrate_class}

weights:
  novelty: 0.35              # apparatus-output structural surprise
  falsifiability: 0.30       # observable-design discipline
  operationalizability: 0.20 # concrete-control-taxonomy completeness
  cross_domain_transfer: 0.15

constraints:
  novelty_must_not_dominate_falsifiability: true
  min_substitution_survival_engagement: 0.6
  max_charter_patches_per_run: 3
  patch_expiry_runs: 5

mode: advisory   # advisory | auto. Set OPERATOR_OVERRIDE_ADVISORY=1 to force advisory at runtime.
"""


def _parse_minimal_yaml(text: str) -> dict[str, Any]:
    """Minimal YAML parser for the flat operator_value_spec schema.

    Handles: top-level scalars, two-level nested dicts (weights:/
    constraints:), inline booleans/floats/ints/strings. No lists,
    anchors, multi-line strings — schema doesn't need them.
    """
    out: dict[str, Any] = {}
    current_section: str | None = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("  ") and current_section is not None:
            kv = line.strip()
            if ":" not in kv:
                continue
            k, _, v = kv.partition(":")
            out.setdefault(current_section, {})[k.strip()] = _coerce_yaml_scalar(v.strip())
        elif ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            v = v.strip()
            if v == "":
                current_section = k.strip()
                out[current_section] = {}
            else:
                current_section = None
                out[k.strip()] = _coerce_yaml_scalar(v)
    return out


def _coerce_yaml_scalar(s: str) -> Any:
    s = s.strip()
    if s.lower() in ("true", "yes", "on"):
        return True
    if s.lower() in ("false", "no", "off"):
        return False
    if s.lower() in ("null", "none", "~", ""):
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s.strip("\"'")


# ----------------------------------------------------------------------------
# Debate-log fingerprint extraction
# ----------------------------------------------------------------------------

_WEAKEST_POINT_PATTERN = re.compile(
    r"\*\*Weakest Point:\*\*\s*(.+?)(?=\n\*\*|\n##|\Z)",
    re.DOTALL,
)


def extract_recent_weakest_points(
    project_dir: Path,
    k: int = DEFAULT_K_DEBATES_TO_READ,
) -> list[dict[str, Any]]:
    """Read the K most recent debate logs and extract each one's
    ``Weakest Point`` block plus iter timestamp. Returns oldest-first."""
    debates = sorted(project_dir.glob("debate_log_iter_*.md"))
    if not debates:
        return []
    debates = debates[-k:]
    out: list[dict[str, Any]] = []
    for path in debates:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        match = _WEAKEST_POINT_PATTERN.search(text)
        if not match:
            continue
        out.append({
            "iter_ts": path.stem.replace("debate_log_iter_", ""),
            "weakest_point": match.group(1).strip(),
            "debate_path": str(path.relative_to(project_dir)),
        })
    return out


# ----------------------------------------------------------------------------
# Fingerprint classification
# ----------------------------------------------------------------------------

def _bigram_jaccard(a: str, b: str) -> float:
    def _bigrams(s: str) -> set[str]:
        s = re.sub(r"\s+", " ", s.lower().strip())
        if len(s) < 2:
            return set()
        return {s[i:i + 2] for i in range(len(s) - 1)}
    sa, sb = _bigrams(a), _bigrams(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def classify_fingerprint(
    weakest_point: str,
    taxonomy: ReframeTaxonomy,
) -> tuple[str | None, float, str]:
    """Classify a weakest-point string into a reframe-type bucket.

    Returns (reframe_type or None, similarity_score, match_reason).
    Tries regex first (similarity=1.0 if hit); falls back to
    bigram-Jaccard against the phrasing corpus."""
    text = weakest_point.lower()

    for rtype, spec in taxonomy.items():
        for pat in spec.get("regex_patterns", []):
            if re.search(pat, text, re.IGNORECASE):
                return rtype, 1.0, f"regex:{pat}"

    best_type: str | None = None
    best_sim = 0.0
    best_reason = ""
    for rtype, spec in taxonomy.items():
        threshold = float(spec.get("jaccard_threshold", 0.5))
        for phrase in spec.get("phrasing_corpus", []):
            sim = _bigram_jaccard(text, phrase)
            if sim >= threshold and sim > best_sim:
                best_type = rtype
                best_sim = sim
                best_reason = f"jaccard:{sim:.2f}:{phrase[:40]}"
    return best_type, best_sim, best_reason


def _llm_classify_fingerprint(
    text: str,
    taxonomy: ReframeTaxonomy,
    rubric_data: dict[str, Any],
    mutator_model_id: str | None,
) -> tuple[str | None, str | None, float, str] | None:
    """Tier-3 classifier: cheap-tier LLM fallback when regex (tier-1) and
    bigram-Jaccard (tier-2) both miss. Returns
    (reframe_type, primitive, similarity, reason) or None on failure.

    The LLM gets the weakest-point text + bucket descriptions + primitive
    descriptions and returns a structured JSON classification. Cross-family
    by default (claude-haiku when mutator is OpenAI, gpt-4.1-mini when
    mutator is Anthropic) so the classifier doesn't share the mutator's
    bias.

    Activation: rubric flag ``enable_llm_fingerprint_classifier: true``.
    Default off — regex+Jaccard cover most cases at zero cost; LLM falls
    through only when both miss.
    """
    if not bool(rubric_data.get("enable_llm_fingerprint_classifier", False)):
        return None
    try:
        from src.ztare.common.llm_runtime import (
            LLMRuntime, get_model_family, resolve_model_id, pick_default_model_id_for_scripts,
        )
    except ImportError:
        return None

    raw_model = str(rubric_data.get("fingerprint_classifier_model_id") or "@cross_family").strip()
    if raw_model in ("@cross_family", "cross_family"):
        try:
            gen_family = get_model_family(mutator_model_id or "")
        except Exception:
            gen_family = "openai"
        # Cross-family default: prefer the OPPOSITE provider family
        cross_defaults = {"openai": "claude-haiku-4-5", "anthropic": "gpt-4.1-mini", "google": "claude-haiku-4-5"}
        model_id = cross_defaults.get(gen_family, "claude-haiku-4-5")
    elif raw_model in ("@cheap", "cheap"):
        try:
            model_id = pick_default_model_id_for_scripts() or "claude-haiku-4-5"
        except Exception:
            model_id = "claude-haiku-4-5"
    elif raw_model in ("@mutator", "mutator"):
        model_id = (mutator_model_id or "").strip() or "claude-haiku-4-5"
    else:
        try:
            model_id = resolve_model_id(raw_model)
        except Exception:
            model_id = raw_model

    # Build bucket + primitive description block (excluding the synthetic
    # primitive_* entries — those are output targets only, not classification
    # candidates at the bucket-name level).
    bucket_lines = []
    for rtype, spec in taxonomy.items():
        if rtype.startswith("primitive_"):
            continue
        prim = spec.get("primitive") or "?"
        # Use first phrasing-corpus entry as a one-line description hint
        corpus = spec.get("phrasing_corpus") or []
        hint = corpus[0] if corpus else rtype
        bucket_lines.append(f"  - `{rtype}` (primitive={prim}): {hint}")
    buckets_block = "\n".join(bucket_lines)

    prompt = (
        "You are the GP-226 charter-critic tier-3 fingerprint classifier. "
        "A research-apparatus panel issued the weakest-point critique below. "
        "Tier-1 (regex) and tier-2 (bigram-Jaccard) both failed to match it "
        "to any registered reframe-type bucket. Your job: classify it.\n\n"
        f"WEAKEST-POINT CRITIQUE:\n```\n{text[:2000]}\n```\n\n"
        "REGISTERED BUCKETS (reframe_type → primitive):\n"
        f"{buckets_block}\n\n"
        "PRIMITIVES (epistemic-move classes):\n"
        "  - DERIVE: claim must be derived from neutral structure, not asserted/imported\n"
        "  - BOUND: claim must specify scope/conditions under which it holds\n"
        "  - OBSERVE: variables/parameters in the claim must be empirically tractable\n\n"
        "CLASSIFICATION RULES:\n"
        "1. If the critique CLEARLY matches one of the registered buckets despite vocabulary "
        "differences (e.g. substrate-specific paraphrase of a canonical critique), return that "
        "bucket's reframe_type and its primitive.\n"
        "2. If the critique matches a PRIMITIVE (DERIVE/BOUND/OBSERVE) but no specific bucket, "
        "return reframe_type=null and the matched primitive.\n"
        "3. If the critique is genuinely novel — not matching any bucket OR primitive — return "
        "both as null and describe the pattern in `novel_pattern_hint`.\n"
        "4. Confidence in [0.0, 1.0]. Below 0.5 means uncertain; the apparatus should treat "
        "as unmatched.\n\n"
        "OUTPUT — strict JSON, no preamble:\n"
        "{\n"
        '  "reframe_type": "<bucket name from registered list, or null>",\n'
        '  "primitive": "DERIVE" | "BOUND" | "OBSERVE" | null,\n'
        '  "confidence": <float 0.0-1.0>,\n'
        '  "reason": "<one sentence>",\n'
        '  "novel_pattern_hint": "<short label if reframe_type AND primitive are null, else null>"\n'
        "}\n"
    )
    try:
        runtime = LLMRuntime()
        from src.ztare.common.dispatch_model import dispatch_call_text

        response = dispatch_call_text(
            "charter_critic_fingerprint",
            prompt,
            llm_response_call=lambda p: runtime.call_text(
                p,
                model_id=model_id,
                timeout_seconds=float(rubric_data.get("fingerprint_classifier_timeout_seconds", 20.0)),
                request_label="charter_critic_fingerprint_classifier",
                retries=1,
            ),
            timeout_seconds=int(float(rubric_data.get("fingerprint_classifier_timeout_seconds", 20.0))),
        )
        raw = (response.text or "").strip()
    except Exception:
        return None
    obj = _extract_json_object(raw)
    if obj is None:
        return None
    confidence = float(obj.get("confidence") or 0.0)
    if confidence < 0.5:
        return None
    rtype = obj.get("reframe_type")
    if isinstance(rtype, str) and rtype.strip() and rtype != "null":
        rtype = rtype.strip()
        if rtype not in taxonomy:
            rtype = None
    else:
        rtype = None
    primitive = obj.get("primitive")
    if isinstance(primitive, str) and primitive.strip().upper() in ("DERIVE", "BOUND", "OBSERVE"):
        primitive = primitive.strip().upper()
    else:
        primitive = None
    if rtype is None and primitive is None:
        return None
    reason = f"llm_tier3:{model_id}:conf={confidence:.2f}:" + str(obj.get("reason", ""))[:120]
    return rtype, primitive, confidence, reason


def aggregate_fingerprints(
    weakest_points: list[dict[str, Any]],
    taxonomy: ReframeTaxonomy,
    rubric_data: dict[str, Any] | None = None,
    mutator_model_id: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Classify each weakest-point and aggregate by reframe-type with
    recurrence count. Returns (aggregated, unmatched).

    Per seam §8b 4g taxonomy-fixed-point critique: unmatched
    weakest-points are returned separately so the dispatcher can write
    them to a `reframe_proposals_<run_id>.md` artifact for operator
    review. This is the V1 affordance for taxonomy extension proposals.
    """
    classifications: list[dict[str, Any]] = []
    primitive_only: list[dict[str, Any]] = []  # matched primitive but no specific bucket
    unmatched: list[dict[str, Any]] = []
    rubric_data = rubric_data or {}
    for wp in weakest_points:
        rtype, sim, reason = classify_fingerprint(wp["weakest_point"], taxonomy)
        if rtype is None:
            # Tier-2: primitive-level regex fallback
            primitive, prim_reason = classify_into_primitive(wp["weakest_point"])
            # Tier-3: cheap-tier cross-family LLM fallback when both regex tiers miss
            if primitive is None:
                llm_result = _llm_classify_fingerprint(
                    wp["weakest_point"], taxonomy, rubric_data, mutator_model_id,
                )
                if llm_result is not None:
                    rtype_llm, primitive_llm, conf, llm_reason = llm_result
                    if rtype_llm is not None:
                        # LLM matched a specific bucket — promote to bucket-level
                        rtype, sim, reason = rtype_llm, conf, llm_reason
                    elif primitive_llm is not None:
                        primitive, prim_reason = primitive_llm, llm_reason
            if rtype is None and primitive is not None:
                primitive_only.append({
                    "iter_ts": wp["iter_ts"],
                    "primitive": primitive,
                    "reason": prim_reason,
                    "weakest_point_excerpt": wp["weakest_point"][:200],
                    "debate_path": wp.get("debate_path", ""),
                })
                continue
            elif rtype is None:
                unmatched.append({
                    "iter_ts": wp["iter_ts"],
                    "weakest_point_excerpt": wp["weakest_point"][:300],
                    "debate_path": wp.get("debate_path", ""),
                })
                continue
            # else: rtype was set by LLM tier-3, fall through to classification append
        classifications.append({
            "iter_ts": wp["iter_ts"],
            "reframe_type": rtype,
            "primitive": primitive_for_bucket(rtype, taxonomy),
            "similarity": sim,
            "reason": reason,
            "weakest_point_excerpt": wp["weakest_point"][:200],
        })

    by_type: dict[str, list[dict[str, Any]]] = {}
    for c in classifications:
        by_type.setdefault(c["reframe_type"], []).append(c)

    aggregated = []
    for rtype, hits in by_type.items():
        aggregated.append({
            "reframe_type": rtype,
            "recurrence": len(hits),
            "max_similarity": max(h["similarity"] for h in hits),
            "iters": [h["iter_ts"] for h in hits],
            "reasons": [h["reason"] for h in hits],
            "excerpts": [h["weakest_point_excerpt"] for h in hits],
            "primitive": primitive_for_bucket(rtype, taxonomy),
        })
    aggregated.sort(key=lambda d: (d["recurrence"], d["max_similarity"]), reverse=True)

    # Aggregate primitive-only matches into a synthetic "primitive_*" entry
    # per primitive class. These get treated like buckets for emission but
    # use the generic primitive-level templates.
    by_primitive: dict[str, list[dict[str, Any]]] = {}
    for p in primitive_only:
        by_primitive.setdefault(p["primitive"], []).append(p)
    for primitive, hits in by_primitive.items():
        aggregated.append({
            "reframe_type": f"primitive_{primitive}",
            "recurrence": len(hits),
            "max_similarity": 0.7,  # primitive-level matches are weaker than bucket-level
            "iters": [h["iter_ts"] for h in hits],
            "reasons": [h["reason"] for h in hits],
            "excerpts": [h["weakest_point_excerpt"] for h in hits],
            "primitive": primitive,
            "is_primitive_only": True,
        })

    aggregated.sort(key=lambda d: (d["recurrence"], d["max_similarity"]), reverse=True)
    return aggregated, unmatched


def write_unmatched_fingerprint_artifact(
    project_dir: Path,
    unmatched: list[dict[str, Any]],
    run_id: str,
) -> Path | None:
    """Write unmatched weakest-point fingerprints to a proposal file
    for operator review (seam §8b 4g taxonomy_extension_proposer V1
    affordance — emit-only, no auto-extension)."""
    if not unmatched:
        return None
    workspace = project_dir / "workspace"
    workspace.mkdir(exist_ok=True)
    out_path = workspace / f"reframe_proposals_{run_id}.md"
    lines = [
        f"# Unmatched weakest-point fingerprints — run {run_id}",
        "",
        "_GP-226 V1 taxonomy-extension affordance. These weakest-points did not_",
        "_match any registered reframe-type bucket. Operator review: do any of_",
        "_these represent a genuine new reframe pattern that should be added to_",
        "_the taxonomy in `src/ztare/orchestrator/charter_critic.py`?_",
        "",
        f"_Total unmatched: {len(unmatched)}_",
        "",
    ]
    for i, u in enumerate(unmatched, 1):
        lines.append(f"---\n\n## Unmatched #{i} (iter {u['iter_ts']})\n")
        lines.append(f"**Source:** `{u.get('debate_path', '?')}`\n")
        lines.append(f"**Weakest-point:**\n\n> {u['weakest_point_excerpt']}\n")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# ----------------------------------------------------------------------------
# Patch expiry (seam §4h charter-rot mitigation)
# ----------------------------------------------------------------------------

def _read_ledger_entries(project_dir: Path) -> list[dict[str, Any]]:
    ledger = project_dir / "workspace" / AUTO_PATCH_LEDGER
    if not ledger.exists():
        return []
    out = []
    for raw in ledger.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return out


def check_patch_expiry(project_dir: Path, current_run_id: str) -> list[dict[str, Any]]:
    """Scan the ledger for committed patches whose creation run is more
    than ``expiry_runs`` runs ago. Returns list of expired patch summaries.

    "More than K runs ago" is computed by counting distinct run_ids in
    the ledger that are different from the patch's creation run AND
    different from the current run; the patch is expired when this count
    >= expiry_runs.
    """
    entries = _read_ledger_entries(project_dir)
    if not entries:
        return []
    distinct_runs = sorted({e.get("created_run_id", "") for e in entries if e.get("created_run_id")})
    expired: list[dict[str, Any]] = []
    for entry in entries:
        if not entry.get("committed"):
            continue
        creation_run = entry.get("created_run_id", "")
        if not creation_run:
            continue
        runs_since = sum(
            1 for r in distinct_runs
            if r > creation_run and r != current_run_id
        )
        expiry = int(entry.get("expiry_runs", DEFAULT_PATCH_EXPIRY_RUNS))
        if runs_since >= expiry:
            expired.append({
                "reframe_type": entry.get("reframe_type"),
                "target": entry.get("target"),
                "section_id": entry.get("section_id"),
                "created_run_id": creation_run,
                "runs_since": runs_since,
                "expiry_runs": expiry,
            })
    return expired


# ----------------------------------------------------------------------------
# Patch templates (light patches — deterministic prose)
# ----------------------------------------------------------------------------

def _template_literature_transfer_engagement(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — literature-transfer engagement (charter-critic GP-226)\n\n"
        "The panel has flagged regression to tool/labor-economics discourse "
        "across recent iters. The thesis must explicitly engage the literature-transfer alternative:\n\n"
        "  Q: Is the decision-critical structural claim a genuine novel primitive of\n"
        "  human-AI interaction, OR is it the standard governance-of-automation\n"
        "  / principal-agent finding wearing AI-specific vocabulary?\n\n"
        "If the claim is literature-transfer rather than a novel primitive, name (a) the existing literature whose\n"
        "results transfer wholesale, (b) the AI-specific quantitative regime-shift\n"
        "that distinguishes the case, (c) the structural property AI has that the\n"
        "transferred-from substrate did not. Literature-transfer with these three components\n"
        "is a positive finding and earns full credit on the Substitution-Survival\n"
        "Gate per the rubric. Literature-transfer without them is regression."
    )
    return ("evidence", "REFRAME PRESSURE — literature-transfer engagement", "append", body)


def _template_named_historical_retrodiction(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — named historical retrodiction (charter-critic GP-226)\n\n"
        "Panel critique recurred: thesis is empirically fragile / no historical\n"
        "precedent / under-argued durability. The thesis must engage at least\n"
        "FIVE named real-world cases adjacent to the substrate's structural claim\n"
        "and retrodict the relevant durability/snapback question for each.\n\n"
        "Required output structure per case:\n"
        "  CASE: <named historical instance, public-record>\n"
        "  STRUCTURAL ANALOG: <how the substrate's decision-critical variable maps>\n"
        "  RETRODICTION: <did the analog snap back / stabilize / drift / collapse>\n"
        "  IMPLICATION: <what this predicts for the substrate's durability claim>\n\n"
        "A thesis that lists fewer than five named cases or that treats the\n"
        "retrodiction as 'plausibly true' without engagement scores zero on this\n"
        "pressure. The cases must be public-record so a third-party reviewer can\n"
        "audit the retrodiction independently."
    )
    return ("evidence", "REFRAME PRESSURE — historical retrodiction", "append", body)


def _template_velocity_vs_level_disclosure(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — velocity-vs-level disclosure (charter-critic GP-226)\n\n"
        "The thesis is level-bound to current capability and does not engage\n"
        "near-future capability shifts that could dissolve the decision-critical\n"
        "structural claim. The thesis MUST do EXACTLY ONE of:\n\n"
        "(a) DERIVE LEVEL-INVARIANCE — show the structural claim survives at\n"
        "    near-future capability levels with explicit derivation of which\n"
        "    asymmetry, regime, or constraint is preserved across the shift.\n\n"
        "(b) ADMIT LEVEL-BOUND SCOPE — explicitly state the capability range\n"
        "    over which the thesis holds and name the post-range collapse\n"
        "    condition. Honest scope-bound is a positive finding.\n\n"
        "(c) ARGUE ILL-POSEDNESS — frontier-velocity dominates capability-level\n"
        "    such that any structural claim at time t is dominated at t+Δ.\n"
        "    Major reframe; admissible only with constructive proof.\n\n"
        "Theses that ignore the velocity-vs-level question or hand-wave the\n"
        "shift score zero on this pressure."
    )
    return ("charter", "VELOCITY-VS-LEVEL CLAUSE", "append", body)


def _template_ui_affordance_specification(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "Concrete output specification (charter-critic GP-226 patch). The "
        "decision-critical claim must specify the concrete affordance / interface / "
        "operational shape at the grammar level — what an external party would "
        "actually build, see, or measure. Abstract category labels alone earn "
        "partial credit only. For task-class decomposition, specify per "
        "sub-class. The 'concrete' threshold: a competent third party reading "
        "the spec could implement or measure it without further clarification."
    )
    return ("rubric_dimension", "ui_affordance_specification_clause", "append", body)


def _template_vocabulary_neutral_restate(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — vocabulary-neutral restate (charter-critic GP-226)\n\n"
        "Panel critique recurred: the thesis smuggles a primitive in disguise.\n"
        "The decision-critical structural property must be re-stated in vocabulary\n"
        "that does NOT presuppose the conclusion.\n\n"
        "Admissible vocabulary classes (by substrate):\n"
        "  - information theory (channel capacity, mutual information, error correction)\n"
        "  - control theory (observer, plant, closed-loop, plant inversion)\n"
        "  - economics (cost asymmetry, transaction cost, principal-agent)\n"
        "  - cognitive science (working memory, attention bottleneck)\n"
        "  - graph / dynamical systems / measure theory (substrate-specific)\n\n"
        "The thesis must restate the structural claim using ONLY vocabulary\n"
        "from one of these classes. Substitution test: replace the named\n"
        "primitive with its vocabulary-neutral form throughout — if the claim\n"
        "becomes incoherent, the original was a smuggled primitive."
    )
    return ("charter", "VOCABULARY-NEUTRAL CLAUSE", "append", body)


def _template_task_class_decomposition_forcing(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — task-class decomposition forcing (charter-critic GP-226)\n\n"
        "Panel critique recurred: single-mode dogma without task-class\n"
        "typology. The thesis must EITHER:\n\n"
        "(a) PROVE single-mode invariance — show the structural primitive is\n"
        "    task-class-invariant by stating the property that holds across\n"
        "    all admissible task classes.\n\n"
        "(b) ADMIT MULTI-MODE EQUILIBRIUM — provide a structural typology that\n"
        "    selects which mode dominates in which task-class. The typology\n"
        "    must specify (i) the discriminating property of each task-class,\n"
        "    (ii) the mode each task-class selects, (iii) the boundary condition\n"
        "    where the discriminating property flips.\n\n"
        "Honest multi-mode-with-typology is a positive finding and earns full\n"
        "credit on the Multi-Mode Pareto Concession Gate. Single-mode dogma\n"
        "without defense earns zero."
    )
    return ("evidence", "REFRAME PRESSURE — task-class decomposition", "append", body)


def _template_parameter_estimability_fragility(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — parameter-estimability fragility (charter-critic GP-226)\n\n"
        "The panel is no longer attacking the structural claim. The panel is\n"
        "attacking the OBSERVABILITY of the variables the structural claim\n"
        "depends on. The thesis must engage this distinct critique:\n\n"
        "For each decision-critical parameter in the thesis (exception rate, error\n"
        "rate, invisibility rate, coverage fraction, calibration confidence,\n"
        "drift coefficient — whichever the substrate uses), the thesis MUST do\n"
        "ALL of the following:\n\n"
        "(1) NAME the parameter and its role in the decision-critical argument.\n"
        "(2) STATE the proposed measurement protocol — what is sampled, by\n"
        "    whom, with what coverage assumption.\n"
        "(3) ENUMERATE failure modes of the protocol: silent errors, adversarial\n"
        "    drift, taxonomy blindness, distributed/emergent errors that escape\n"
        "    classification, sampling bias from the system being measured.\n"
        "(4) DERIVE either (a) a structural argument that the parameter is\n"
        "    estimable within bounded uncertainty in the deployed regime, or\n"
        "    (b) admit that the parameter is operationally bounded — name the\n"
        "    deployment regime where estimation is reliable and the regime\n"
        "    where it is not.\n\n"
        "A thesis that asserts a parameter exists and is bounded without\n"
        "engaging the measurement protocol earns zero on this pressure. A\n"
        "thesis that admits parameter-fragility AND specifies the deployment\n"
        "regime where its claim holds earns full credit — measurement-bound\n"
        "scope is a positive structural finding."
    )
    return ("evidence", "REFRAME PRESSURE — parameter estimability", "append", body)


def _template_primitive_DERIVE(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — DERIVE primitive (charter-critic GP-226)\n\n"
        "The panel has issued a critique that does not match a specific bucket\n"
        "but clusters around the DERIVE primitive: the decision-critical structural\n"
        "claim is ASSERTED rather than DERIVED from neutral structure.\n\n"
        "The thesis must, for the decision-critical claim:\n\n"
        "(1) STRIP all proper nouns, vendor names, domain-specific vocabulary,\n"
        "    and presupposed primitives from the claim.\n"
        "(2) STATE the residual structural property in vocabulary from one of:\n"
        "    information theory / control theory / economics / cognitive\n"
        "    science / dynamical systems / measure theory / graph theory.\n"
        "(3) DERIVE the original claim as a corollary of the residual property.\n"
        "(4) Apply the substitution test: if substituting the residual property\n"
        "    into a different domain (e.g., human-AI → human-employee, or\n"
        "    cosmic-civilization → extinct-Earth-civilization) preserves the\n"
        "    derivation, the property is genuinely structural. If it breaks,\n"
        "    name what specifically about the original domain is decision-critical.\n\n"
        "A claim that survives strip+restate+derive earns the DERIVE primitive.\n"
        "A claim that requires the original vocabulary to be coherent has\n"
        "smuggled a primitive and earns zero on this pressure."
    )
    return ("evidence", "REFRAME PRESSURE — DERIVE primitive", "append", body)


def _template_primitive_BOUND(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — BOUND primitive (charter-critic GP-226)\n\n"
        "The panel's critique clusters around the BOUND primitive: the\n"
        "decision-critical claim is stated WITHOUT specifying the conditions,\n"
        "scope, or range under which it holds. The panel reads this as\n"
        "implicit-universalism — the claim asserted as if it holds always,\n"
        "when it holds only under unstated conditions.\n\n"
        "The thesis must produce explicit conditional structure for every\n"
        "decision-critical claim:\n\n"
        "  if condition X then verdict V; if condition X' then verdict V'.\n\n"
        "Specifically, for the decision-critical claim, name and bound:\n"
        "(1) the CAPABILITY range over which it holds (e.g., 2026–2028, fails\n"
        "    above ~95% per-task-class reliability),\n"
        "(2) the TASK-CLASS where it holds (task-class decomposition: which task\n"
        "    classes select the dominant mode? which fall outside scope?),\n"
        "(3) the POLICY/INSTITUTIONAL regime (e.g., regulatory-acceptance\n"
        "    floor, attestation-coverage threshold, liability framework),\n"
        "(4) the HISTORICAL precedent class (named real-world cases\n"
        "    structurally analogous; what each retrodicts for the claim).\n\n"
        "A thesis that admits BOUNDED scope on each axis earns the BOUND\n"
        "primitive. A thesis that asserts the claim and waves at its scope\n"
        "earns zero — implicit-universalism is the failure mode."
    )
    return ("evidence", "REFRAME PRESSURE — BOUND primitive", "append", body)


def _template_primitive_OBSERVE(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — OBSERVE primitive (charter-critic GP-226)\n\n"
        "The panel's critique clusters around the OBSERVE primitive: the\n"
        "decision-critical claim depends on variables/parameters that may not be\n"
        "empirically tractable in the deployed regime.\n\n"
        "For each decision-critical variable in the thesis:\n\n"
        "(1) NAME the variable and its role.\n"
        "(2) STATE whether the thesis treats it as observable/measurable,\n"
        "    bounded/estimable, or controllable/exogenous.\n"
        "(3) ENUMERATE failure modes of the assumption: silent errors,\n"
        "    adversarial drift, taxonomy blindness, distributed/emergent\n"
        "    effects escaping classification, observer-effect/reflexivity\n"
        "    where the intervention changes the observed variable, sampling\n"
        "    bias from the system being measured.\n"
        "(4) DERIVE either (a) a structural argument that the variable is\n"
        "    estimable / observable / non-reflexive within bounded\n"
        "    uncertainty, or (b) admit measurement-bound/reflexivity-bound\n"
        "    scope and name the regime where the claim holds.\n\n"
        "A thesis that handles observability/estimability/feedback explicitly\n"
        "earns the OBSERVE primitive. A thesis that asserts variables exist\n"
        "and behave as expected without engaging measurement protocol earns\n"
        "zero on this pressure."
    )
    return ("evidence", "REFRAME PRESSURE — OBSERVE primitive", "append", body)


def _template_endogeneity_reflexivity(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — endogeneity / reflexivity (charter-critic GP-226)\n\n"
        "The panel has identified a class of critique distinct from\n"
        "capability-shift or parameter-estimability: the thesis treats a\n"
        "decision-critical CONTROL VARIABLE as exogenous when it is in fact\n"
        "ENDOGENOUS to the very interventions the thesis recommends.\n\n"
        "For each decision-critical control variable in the thesis (regulatory\n"
        "reversion hazard, adoption rate, trust calibration, audit acceptance,\n"
        "exception classification — substrate-specific), the thesis MUST:\n\n"
        "(1) NAME the control variable and its role in the structural argument.\n"
        "(2) STATE whether the thesis treats it as exogenous (fixed by the\n"
        "    environment) or endogenous (function of the interventions).\n"
        "(3) DERIVE the FEEDBACK STRUCTURE: does the recommended intervention\n"
        "    raise, lower, or leave unchanged the variable on which the\n"
        "    intervention's success depends? Show the sign of dV/dI.\n"
        "(4) HANDLE the positive-feedback case explicitly: if the intervention\n"
        "    raises the variable that destabilizes it (e.g., aggressive\n"
        "    UI cutover raises regulatory reversion hazard), the thesis must\n"
        "    either show the feedback is bounded, propose a damped\n"
        "    intervention path, or admit that the intervention class is\n"
        "    self-defeating in its current form.\n\n"
        "A thesis that treats endogenous variables as exogenous earns zero\n"
        "on this pressure. A thesis that names the feedback, derives the\n"
        "sign, and either bounds or admits the self-defeating case earns\n"
        "full credit — observer-effect-aware structural argument is a\n"
        "positive finding, not a concession."
    )
    return ("evidence", "REFRAME PRESSURE — endogeneity reflexivity", "append", body)


def _template_proof_anchor_resolution(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — proof anchor resolution (charter-critic GP-226)\n\n"
        "The panel has flagged unresolved or weak proof anchors. The next "
        "candidate must name only declarations that resolve in the current "
        "workspace and must cite the file path for each decision-critical source.\n\n"
        "Required output for each proposed proof move:\n"
        "(1) TARGET: exact theorem/structure name being closed or simplified.\n"
        "(2) SOURCES: exact existing declarations used as premises, with paths.\n"
        "(3) TYPE CHECK: a command or probe that confirms those names resolve.\n"
        "(4) REFUSAL: if any source cannot be resolved, emit a smaller search "
        "task instead of inventing a theorem name.\n\n"
        "Do not reward plausible-sounding source names. A proof target packet "
        "earns this pressure only when a coding agent can run the stated "
        "resolution check before attempting a proof edit."
    )
    return ("evidence", "REFRAME PRESSURE — proof anchor resolution", "append", body)


def _template_proof_non_circularity(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — proof non-circularity (charter-critic GP-226)\n\n"
        "The panel has flagged circularity / tautology risk. The next proof "
        "candidate must separate sources from endpoints before proposing a "
        "constructor.\n\n"
        "Required discipline:\n"
        "(1) State the final endpoint and mark it FORBIDDEN AS PREMISE.\n"
        "(2) State the source corridor and verify every premise is strictly "
        "upstream of the target in the dependency graph or workmap.\n"
        "(3) Reject definition-level closure where the target is made true by "
        "assuming an equivalent field, class, or receipt.\n"
        "(4) Name the circularity falsifier: the smallest dependency edge that, "
        "if reversed or reused, would make the proof invalid.\n\n"
        "A candidate that passes Lean by importing the target through a renamed "
        "field is a failure, not progress."
    )
    return ("charter", "REFRAME PRESSURE — proof non-circularity", "append", body)


def _template_proof_falsifier_first(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — proof falsifier-first (charter-critic GP-226)\n\n"
        "The panel has flagged that proposed proof moves do not name the "
        "escape sequence or failure class. Each proof candidate must now "
        "carry a falsifier before the positive route.\n\n"
        "Required output:\n"
        "(1) ESCAPE CLASS: what mathematical object, dependency pattern, or "
        "counterexample shape would refute the route.\n"
        "(2) DETECTOR: exact Lean search, graph query, SymPy/dimensional check, "
        "or source audit that would detect that escape.\n"
        "(3) PIVOT RULE: what the next move becomes if the detector fires.\n\n"
        "Candidates that only say why the proof should work, without a "
        "kill-condition, earn zero on this pressure."
    )
    return ("evidence", "REFRAME PRESSURE — proof falsifier-first", "append", body)


def _template_proof_executable_probe(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — proof executable probe (charter-critic GP-226)\n\n"
        "The panel has flagged non-executable proof advice. The next candidate "
        "must include a concrete probe that can be run by an agent without "
        "additional interpretation.\n\n"
        "Required output:\n"
        "(1) COMMAND: exact command or Lean check to run first.\n"
        "(2) EXPECTED PASS: what output means the proof edit is warranted.\n"
        "(3) EXPECTED FAIL: what output means the target is the wrong layer.\n"
        "(4) POST-EDIT OBSERVABLE: the graph/workmap/status refresh or other "
        "artifact that must change if the proof edit genuinely advanced closure.\n\n"
        "A candidate whose only executable step is a full build after an "
        "untyped edit is too late; the probe must move failure cost forward."
    )
    return ("evidence", "REFRAME PRESSURE — proof executable probe", "append", body)


def _template_proof_decomposition_gap(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — proof decomposition gap (charter-critic GP-226)\n\n"
        "The panel has flagged a target whose semantic gap is too large for a "
        "direct patch. The next candidate must cut the endpoint into a smaller "
        "typed constructor before attempting the main theorem.\n\n"
        "Required output:\n"
        "(1) MAIN TARGET: exact endpoint currently too large.\n"
        "(2) STEPPING STONE: smallest intermediate theorem/structure that would "
        "strictly reduce the target's field count, premise count, or downstream "
        "dependency width.\n"
        "(3) SOURCE LIMIT: existing declarations allowed to feed the stepping "
        "stone; no new analytic estimate may be assumed unless explicitly named "
        "as a missing primitive.\n"
        "(4) COMPLETION RULE: how the main target becomes routing-only after the "
        "stepping stone compiles.\n\n"
        "This pressure rewards endpoint compression and source constructors, not "
        "larger one-shot theorem statements."
    )
    return ("evidence", "REFRAME PRESSURE — proof decomposition gap", "append", body)


def _template_proof_secondary_observable(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — proof secondary observable (charter-critic GP-226)\n\n"
        "The panel has flagged proof progress that only claims local compile "
        "success. The next candidate must name a secondary observable that "
        "would change if the proof move genuinely advances closure.\n\n"
        "Admissible observables include: open-structure count decrease, workmap "
        "rank movement, dependency-graph edge removal/addition, failure-cluster "
        "shrinkage, or a new source constructor appearing in the declaration "
        "index with downstream users. The observable must be refreshed after "
        "the proof edit and interpreted explicitly.\n\n"
        "A compile pass with no closure-surface delta is a routing improvement "
        "at most; it must not be reported as endpoint closure."
    )
    return ("evidence", "REFRAME PRESSURE — proof secondary observable", "append", body)


PATCH_TEMPLATE_REGISTRY = {
    "_template_literature_transfer_engagement": _template_literature_transfer_engagement,
    "_template_named_historical_retrodiction": _template_named_historical_retrodiction,
    "_template_velocity_vs_level_disclosure": _template_velocity_vs_level_disclosure,
    "_template_ui_affordance_specification": _template_ui_affordance_specification,
    "_template_vocabulary_neutral_restate": _template_vocabulary_neutral_restate,
    "_template_task_class_decomposition_forcing": _template_task_class_decomposition_forcing,
    "_template_parameter_estimability_fragility": _template_parameter_estimability_fragility,
    "_template_endogeneity_reflexivity": _template_endogeneity_reflexivity,
    "_template_proof_anchor_resolution": _template_proof_anchor_resolution,
    "_template_proof_non_circularity": _template_proof_non_circularity,
    "_template_proof_falsifier_first": _template_proof_falsifier_first,
    "_template_proof_executable_probe": _template_proof_executable_probe,
    "_template_proof_decomposition_gap": _template_proof_decomposition_gap,
    "_template_proof_secondary_observable": _template_proof_secondary_observable,
    "_template_primitive_DERIVE": _template_primitive_DERIVE,
    "_template_primitive_BOUND": _template_primitive_BOUND,
    "_template_primitive_OBSERVE": _template_primitive_OBSERVE,
}


# Synthetic "primitive_*" reframe-types registered in the taxonomy so
# emit_patches can dispatch them like buckets. These are added at module
# load time, AFTER the bucket definitions, with empty regex (they're
# only triggered by primitive-level fallback in aggregate_fingerprints).
for _prim in (PRIMITIVE_DERIVE, PRIMITIVE_BOUND, PRIMITIVE_OBSERVE):
    QUALITATIVE_THESIS_TAXONOMY[f"primitive_{_prim}"] = {
        "regex_patterns": [],
        "phrasing_corpus": [],
        "jaccard_threshold": 1.0,  # never matches via classify_fingerprint
        "patch_target": "evidence",
        "patch_template_fn": f"_template_primitive_{_prim}",
        "primitive": _prim,
    }
    PROOF_TARGET_TAXONOMY[f"primitive_{_prim}"] = {
        "regex_patterns": [],
        "phrasing_corpus": [],
        "jaccard_threshold": 1.0,
        "patch_target": "evidence",
        "patch_template_fn": f"_template_primitive_{_prim}",
        "primitive": _prim,
    }


# ----------------------------------------------------------------------------
# V2 — heavy LLM-assisted patches (gated by enable_heavy_charter_patches)
# ----------------------------------------------------------------------------

# Per-reframe-type goal description that the LLM uses to generate a
# substrate-specific patch instead of the V1 generic template. The LLM
# is given the goal + the recent weakest-points + an evidence excerpt;
# it returns ONLY a patch-body block (no preamble, no explanation).

_HEAVY_PATCH_GOALS: dict[str, str] = {
    "literature_transfer_engagement": (
        "Force explicit literature-transfer engagement: name the specific existing literature "
        "whose results transfer to this substrate (e.g. principal-agent theory, "
        "governance-of-automation, domain-specific economics), state the "
        "substrate's quantitative regime-shift, and identify the specific "
        "AI-side structural property that makes the substrate distinct."
    ),
    "named_historical_retrodiction": (
        "Force named historical retrodiction: list 5-6 SPECIFIC public-record "
        "cases adjacent to the substrate's decision-critical claim (regulated sectors, "
        "scientific-discovery analogs, technology-adoption analogs — substrate-"
        "appropriate). For each: structural analog, what actually happened "
        "(durability/snapback/drift/collapse), implication for the thesis. "
        "Cases must be public-record so a third-party reviewer can audit."
    ),
    "velocity_vs_level_disclosure": (
        "Force velocity-vs-level engagement: identify 2-3 SPECIFIC near-future "
        "(2027-2030) capability shifts plausibly relevant to the substrate, and "
        "for each: state how the decision-critical structural claim either survives "
        "or is dominated by the shift. Force a derivation, scope-bound, or "
        "ill-posed verdict."
    ),
    "ui_affordance_specification": (
        "Force concrete output specification at the operational/implementation "
        "level: for each task-class or decomposed verdict, specify the exact "
        "interface/affordance/operational shape such that an external party "
        "could implement or measure it without further clarification."
    ),
    "vocabulary_neutral_restate": (
        "Force vocabulary-neutral restatement: identify the specific smuggled "
        "primitive in the recent thesis, propose 2-3 substitute primitives in "
        "vocabulary-neutral classes (information theory / control theory / "
        "economics / cognitive science / dynamical systems / measure theory), "
        "and require substitution-test verification."
    ),
    "task_class_decomposition_forcing": (
        "Force task-class decomposition: identify 4-6 task-classes adjacent to "
        "the substrate's domain that exhibit different selection pressures, and "
        "require the thesis to either (a) prove its claim is task-class-invariant "
        "by naming the invariant property, or (b) admit multi-mode equilibrium "
        "with a typology that selects which mode dominates per task-class."
    ),
    "parameter_estimability_fragility": (
        "Force parameter-estimability engagement: name the decision-critical "
        "parameters in the thesis (e.g., exception rate ε, invisibility rate δ, "
        "coverage fraction, calibration confidence — substrate-specific). For "
        "each: state the measurement protocol assumed, enumerate the failure "
        "modes of that protocol (silent errors, adversarial drift, taxonomy "
        "blindness, distributed/emergent errors, observer-effect bias), and "
        "force a derivation: is the parameter estimable in the deployed regime, "
        "or is the decision-critical claim measurement-bound? Identify the specific "
        "deployment regimes where measurement reliability fails."
    ),
    "endogeneity_reflexivity": (
        "Force endogeneity / reflexivity engagement: identify the control "
        "variables the thesis treats as exogenous (regulatory hazard, trust "
        "rate, adoption velocity — substrate-specific) and demand a derivation "
        "of the feedback sign. Show whether the recommended intervention "
        "raises, lowers, or leaves unchanged the variable on which its success "
        "depends. Force the apparatus to handle the positive-feedback case: "
        "either bound the feedback, propose damped intervention, or admit "
        "self-defeating intervention class."
    ),
    "proof_anchor_resolution": (
        "Force proof-anchor resolution: require exact theorem/structure targets, "
        "exact existing source declarations with file paths, a cheap type/name "
        "resolution probe before proof editing, and an explicit refusal path "
        "when the cited witness is absent. The patch must prevent plausible "
        "source-name invention and distinguish type-level wrappers from real "
        "field-level proof objects."
    ),
    "proof_non_circularity": (
        "Force proof non-circularity: require source/end-point separation, "
        "final endpoint forbidden as premise, dependency-direction check, and "
        "an explicit circularity falsifier. The patch should prevent proof-by-"
        "definition, renamed-target imports, and residual-only tautologies."
    ),
    "proof_falsifier_first": (
        "Force falsifier-first proof planning: require every candidate proof "
        "move to name the mathematical escape class, the concrete detector "
        "that would catch it, and the pivot rule if the detector fires."
    ),
    "proof_executable_probe": (
        "Force executable proof probes: require an exact command or Lean/Python "
        "check before editing, pass/fail interpretation, and a post-edit "
        "closure artifact refresh. Move failure cost before expensive proof "
        "attempts."
    ),
    "proof_decomposition_gap": (
        "Force endpoint decomposition: when the target is too wide, require the "
        "smallest intermediate constructor that reduces field count, premise "
        "count, or dependency width, plus the completion rule that makes the "
        "main theorem routing-only."
    ),
    "proof_secondary_observable": (
        "Force secondary closure observables: require workmap, dependency graph, "
        "open-obligation count, failure-cluster, or declaration-index deltas "
        "after proof edits, so a compile pass is not mistaken for endpoint "
        "closure."
    ),
}


def _build_heavy_patch_prompt(
    *,
    reframe_type: str,
    agg: dict,
    evidence_excerpt: str,
    charter_excerpt: str,
    substrate_class: str,
    cold_shot_denylist: list[str],
    cross_run_patch_count: int = 0,
    cross_run_primitive_count: int = 0,
    primitive: str = "",
) -> str:
    goal = _HEAVY_PATCH_GOALS.get(reframe_type, "")
    iters_list = agg.get("iters", []) or []
    excerpts_list = agg.get("excerpts", []) or []
    pairs = list(zip(iters_list, excerpts_list))
    excerpts = "\n\n".join(f"  - iter {ts}: {ex}" for ts, ex in pairs) if pairs else "(no excerpts)"
    deny_block = ", ".join(cold_shot_denylist) if cold_shot_denylist else "(none specified)"
    if cross_run_patch_count >= 3:
        escalation_block = (
            f"\n\n**ESCALATION DIRECTIVE (cross-run patch count = {cross_run_patch_count}).** "
            "The same reframe-type has been patched against this substrate "
            f"{cross_run_patch_count} times. The apparatus has been ENGAGING but not "
            "DELIVERING — it acknowledges the critique without producing the formal "
            "structural derivation the panel demands. This patch must therefore "
            "DEMAND FORMAL DERIVATION, not merely 'force engagement'. Specifically: "
            "demand the apparatus produce (a) an explicit conditional structure "
            "(`if condition X then verdict V; else verdict V'`) covering each shift / "
            "case / variable, OR (b) a constructive proof that the boundary cannot "
            "be derived within the framework AND the precise reason it cannot. "
            "Acknowledgment-without-derivation is no longer admissible. Frame the "
            "patch as 'the panel is refusing to score above the current ceiling "
            "until formal boundary structure is produced; here is the precise "
            "structure demanded.'"
        )
    elif cross_run_patch_count == 2:
        escalation_block = (
            f"\n\n(Cross-run patch count = {cross_run_patch_count}. The apparatus has "
            "engaged this critique once before. Sharpen the patch to demand specifics "
            "the prior patch did not — concrete thresholds, named conditions, sign of "
            "the partial derivative, etc.)"
        )
    else:
        escalation_block = ""
    if cross_run_primitive_count >= 5 and primitive:
        escalation_block += (
            f"\n\n**PRIMITIVE-LEVEL CEILING SIGNAL.** The {primitive} primitive "
            f"has been patched {cross_run_primitive_count} times across multiple "
            "bucket instantiations on this substrate. The thesis is failing "
            f"the {primitive} primitive STRUCTURALLY — not on one axis but on "
            "several. The patch must therefore force a higher-level engagement: "
            f"either (a) DERIVE A META-{primitive} ARGUMENT — show why the "
            f"thesis cannot be {primitive.lower()}-d at this capability tier "
            f"and what would change to make it {primitive.lower()}-able, OR "
            f"(b) ADMIT the substrate is at its {primitive.lower()}ing ceiling "
            "and reformulate the eigenquestion to one the apparatus can answer "
            f"under the current {primitive.lower()}ability constraint. This is "
            "no longer a per-axis critique; it is a structural-cap signal."
        )
    return (
        "You are the GP-226 charter-critic LLM heavy-patch authoring role for a\n"
        "ZTARE qualitative-thesis research apparatus. Your output is appended to\n"
        "an evidence brief or project charter and read by another LLM (the\n"
        "mutator) on its next iteration. Your job is to produce ADVERSARIAL\n"
        "DE-ANCHORING PRESSURE — not a recommendation, not a thesis, not a fix.\n"
        "You are forcing the apparatus to engage a specific structural critique\n"
        "the panel keeps issuing.\n\n"
        f"Substrate class: {substrate_class}\n"
        f"Reframe-type bucket: {reframe_type}\n"
        f"Goal of this patch: {goal}"
        f"{escalation_block}\n\n"
        "Recent weakest-points (the panel's repeated stuck-on critique):\n"
        f"{excerpts}\n\n"
        "EXCERPT OF CURRENT EVIDENCE BRIEF (to avoid redundancy):\n"
        "```\n"
        f"{evidence_excerpt[:4000]}\n"
        "```\n\n"
        "EXCERPT OF CURRENT PROJECT CHARTER:\n"
        "```\n"
        f"{charter_excerpt[:2500]}\n"
        "```\n\n"
        "STRICT OUTPUT RULES:\n"
        "1. Output ONLY the patch body — no preamble, no markdown headers above\n"
        "   the patch's own H2, no commentary, no closing remarks.\n"
        "2. Start the patch with: '## REFRAME PRESSURE — <short label> "
        "(charter-critic GP-226 heavy)'\n"
        "3. **Hard size budget: ≤ 3500 bytes total.** Target ~2200 bytes.\n"
        "   Prefer 2-3 named scenarios over 4-5 with cut-off detail.\n"
        "   Each scenario must finish its own sentence cleanly. Do NOT exceed\n"
        "   3500 bytes — output past that limit will be rejected by the\n"
        "   sanitation gate and the patch will be discarded.\n"
        "4. Do NOT mention specific products, vendors, or proper-noun authors\n"
        "   beyond what is already in the evidence/charter excerpts.\n"
        f"5. Do NOT use the following denylisted vocabulary: {deny_block}\n"
        "6. Do NOT propose answers, theses, or solutions — only force engagement\n"
        "   with the structural critique. The patch is a question/constraint, not\n"
        "   a recommendation.\n"
        "7. If the existing evidence excerpt already engages this critique\n"
        "   substantively, reply with the literal token:\n"
        "   <<NO_PATCH_REDUNDANT>>\n"
        "   (a JSON-like sentinel; do not add explanation around it).\n"
        "8. Never output ground-truth values, derivations, or oracle knowledge.\n"
        "9. Final sentence must end with a complete period — never trail off.\n\n"
        "Begin patch body now:\n"
    )


_HEAVY_PATCH_OUTPUT_DENYLIST = [
    "ground truth", "ground_truth", "verified_axioms",
    "<system>", "ignore previous", "ignore the above",
]


def _count_cross_run_patches_for_reframe(project_dir: Path, reframe_type: str) -> int:
    """Count committed patches of the given reframe-type across all
    prior runs in the project's ledger. Used by the heavy patch
    generator to escalate from 'force engagement' to 'demand formal
    derivation' when the same reframe has been patched repeatedly."""
    entries = _read_ledger_entries(project_dir)
    return sum(
        1 for e in entries
        if e.get("reframe_type") == reframe_type
        and e.get("committed") is True
    )


def _count_cross_run_patches_for_primitive(
    project_dir: Path,
    primitive: str,
    taxonomy: ReframeTaxonomy,
) -> int:
    """Count committed patches across ALL buckets that instantiate the
    given primitive, plus primitive-only patches for that primitive.
    A higher count here than for any single bucket signals that the
    apparatus is failing the primitive across multiple instantiations —
    a stronger 'this dimension cannot be honored at this capability
    tier' signal than per-bucket count."""
    entries = _read_ledger_entries(project_dir)
    count = 0
    for e in entries:
        if e.get("committed") is not True:
            continue
        rtype = e.get("reframe_type", "")
        if rtype == f"primitive_{primitive}":
            count += 1
            continue
        spec = taxonomy.get(rtype) or {}
        if spec.get("primitive") == primitive:
            count += 1
    return count


def _heavy_patch_via_llm(
    *,
    reframe_type: str,
    agg: dict,
    project_dir: Path,
    rubric_data: dict[str, Any],
    value_spec: dict[str, Any],
    runtime_mutator_model_id: str | None,
) -> tuple[str, str, str, str] | None:
    """Generate a substrate-specific patch body via LLM.

    Returns (target, section_id, operation, body) on success, None on
    any failure (caller falls back to V1 light template). Never raises.
    """
    try:
        from src.ztare.common.llm_runtime import LLMRuntime
    except ImportError:
        return None

    raw_model = str(rubric_data.get("charter_critic_model_id") or "@cheap").strip()
    if raw_model in ("@mutator", "mutator"):
        model_id = (runtime_mutator_model_id or "").strip() or "claude-haiku-4-5"
    elif raw_model in ("@cheap", "cheap", ""):
        try:
            from src.ztare.common.llm_runtime import pick_default_model_id_for_scripts
            picked = pick_default_model_id_for_scripts()
            model_id = picked or "claude-haiku-4-5"
        except Exception:
            model_id = "claude-haiku-4-5"
    else:
        try:
            from src.ztare.common.llm_runtime import resolve_model_id
            model_id = resolve_model_id(raw_model)
        except Exception:
            model_id = raw_model

    evidence_path = project_dir / "evidence.txt"
    charter_path = project_dir / "project_charter.md"
    evidence_excerpt = evidence_path.read_text(encoding="utf-8") if evidence_path.exists() else ""
    charter_excerpt = charter_path.read_text(encoding="utf-8") if charter_path.exists() else ""

    substrate_class = str(value_spec.get("substrate_class") or "qualitative_thesis")
    cold_shot_denylist = list(rubric_data.get("cold_shot_prompt_denylist") or [])

    cross_run_patch_count = _count_cross_run_patches_for_reframe(project_dir, reframe_type)
    bucket_primitive = primitive_for_bucket(reframe_type, SUBSTRATE_TAXONOMIES.get(substrate_class, {})) or ""
    cross_run_primitive_count = (
        _count_cross_run_patches_for_primitive(project_dir, bucket_primitive, SUBSTRATE_TAXONOMIES.get(substrate_class, {}))
        if bucket_primitive else 0
    )
    prompt = _build_heavy_patch_prompt(
        reframe_type=reframe_type,
        agg=agg,
        evidence_excerpt=evidence_excerpt,
        charter_excerpt=charter_excerpt,
        substrate_class=substrate_class,
        cold_shot_denylist=cold_shot_denylist,
        cross_run_patch_count=cross_run_patch_count,
        cross_run_primitive_count=cross_run_primitive_count,
        primitive=bucket_primitive,
    )

    try:
        runtime = LLMRuntime()
        from src.ztare.common.dispatch_model import dispatch_call_text

        response = dispatch_call_text(
            "charter_critic_patch",
            prompt,
            llm_response_call=lambda p: runtime.call_text(
                p,
                model_id=model_id,
                timeout_seconds=float(rubric_data.get("charter_critic_timeout_seconds", 30.0)),
                request_label="charter_critic_heavy_patch",
                retries=1,
            ),
            timeout_seconds=int(float(rubric_data.get("charter_critic_timeout_seconds", 30.0))),
        )
        raw = (response.text or "").strip()
    except Exception:
        return None

    if not raw or "<<NO_PATCH_REDUNDANT>>" in raw:
        return None

    body = _strip_llm_preamble(raw)

    for forbidden in _HEAVY_PATCH_OUTPUT_DENYLIST:
        if forbidden.lower() in body.lower():
            return None

    body_bytes = len(body.encode("utf-8"))
    if body_bytes > PATCH_SIZE_BYTES_MAX - 64:
        # Trim from the last complete sentence rather than mid-word.
        truncated = body[:PATCH_SIZE_BYTES_MAX - 256]
        last_period = max(truncated.rfind("."), truncated.rfind("?"), truncated.rfind("!"))
        if last_period > len(truncated) // 2:
            body = truncated[:last_period + 1].rstrip() + "\n"
        else:
            body = truncated.rstrip() + "\n"

    spec_entry = SUBSTRATE_TAXONOMIES.get(substrate_class, {}).get(reframe_type, {})
    target = spec_entry.get("patch_target", "evidence")
    section_id = f"REFRAME PRESSURE — {reframe_type} (heavy)"
    return (target, section_id, "append", body)


def _strip_llm_preamble(raw: str) -> str:
    """Strip common LLM preambles like 'Here is the patch:' or
    'Sure, I'll generate...' before the actual patch body."""
    lines = raw.splitlines()
    while lines and lines[0].strip() and not lines[0].lstrip().startswith("##"):
        first = lines[0].lower()
        if "here" in first or "sure" in first or "patch:" in first or "below" in first:
            lines.pop(0)
            continue
        break
    return "\n".join(lines).strip() + "\n"


# ----------------------------------------------------------------------------
# Sanitation gates
# ----------------------------------------------------------------------------

def sanitize_patch_body(body: str) -> tuple[bool, list[str]]:
    """Run sanitation gates over a patch body. Returns (passed, checks_passed).
    Charter-contamination check + size bound. No oracle file reads."""
    checks: list[str] = []
    if len(body.encode("utf-8")) > PATCH_SIZE_BYTES_MAX:
        return False, ["FAIL:size_bound_exceeded"]
    checks.append("PASS:size_bound")
    for pattern in GT_LEAK_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            return False, [*checks, f"FAIL:gt_leak:{pattern}"]
    checks.append("PASS:no_gt_leak")
    if re.search(r"def\s+_ground_truth", body) or re.search(r"verified_axioms", body):
        return False, [*checks, "FAIL:harness_or_axioms_reference"]
    checks.append("PASS:no_harness_reference")
    return True, checks


# ----------------------------------------------------------------------------
# Patch emission + commit
# ----------------------------------------------------------------------------

def emit_patches(
    project_dir: Path,
    aggregated: list[dict[str, Any]],
    taxonomy: ReframeTaxonomy,
    value_spec: dict[str, Any],
    run_id: str,
    max_patches: int,
    expiry_runs: int,
    rubric_data: dict[str, Any] | None = None,
    runtime_mutator_model_id: str | None = None,
) -> list[CharterPatch]:
    """For each aggregated reframe-type (top-N by recurrence×similarity),
    generate a CharterPatch.

    Path selection:
    - V2 heavy (LLM-assisted) when ``rubric_data['enable_heavy_charter_patches']``
      is true; falls back to V1 light template on any LLM failure.
    - V1 light (deterministic templates) otherwise.

    Both paths run the same sanitation gates."""
    if not aggregated:
        return []
    rubric_data = rubric_data or {}
    use_heavy = bool(rubric_data.get("enable_heavy_charter_patches", False))
    project_slug = project_dir.name
    out: list[CharterPatch] = []
    for agg in aggregated[:max_patches]:
        rtype = agg["reframe_type"]
        spec_entry = taxonomy.get(rtype)
        if not spec_entry:
            continue

        target_op_body: tuple[str, str, str, str] | None = None
        used_heavy = False

        if use_heavy:
            target_op_body = _heavy_patch_via_llm(
                reframe_type=rtype,
                agg=agg,
                project_dir=project_dir,
                rubric_data=rubric_data,
                value_spec=value_spec,
                runtime_mutator_model_id=runtime_mutator_model_id,
            )
            if target_op_body is not None:
                used_heavy = True

        if target_op_body is None:
            template_fn_name = spec_entry.get("patch_template_fn", "")
            template_fn = PATCH_TEMPLATE_REGISTRY.get(template_fn_name)
            if template_fn is None:
                continue
            try:
                target_op_body = template_fn(project_slug, agg, value_spec)
            except Exception:
                continue

        target, section_id, operation, body = target_op_body
        passed, checks = sanitize_patch_body(body)
        if not passed:
            continue

        patch = CharterPatch(
            target=target,                      # type: ignore[arg-type]
            section_id=section_id,
            operation=operation,                # type: ignore[arg-type]
            body=body,
            reframe_type=rtype,
            expiry_runs=expiry_runs,
            fingerprint_match={
                "recurrence": agg["recurrence"],
                "max_similarity": agg["max_similarity"],
                "iters": agg["iters"],
                "reasons": agg["reasons"],
                "generation": "heavy" if used_heavy else "light",
                "primitive": agg.get("primitive") or primitive_for_bucket(rtype, taxonomy),
                "cross_run_patch_count": _count_cross_run_patches_for_reframe(project_dir, rtype),
                "cross_run_primitive_count": (
                    _count_cross_run_patches_for_primitive(
                        project_dir,
                        agg.get("primitive") or primitive_for_bucket(rtype, taxonomy) or "",
                        taxonomy,
                    )
                    if (agg.get("primitive") or primitive_for_bucket(rtype, taxonomy))
                    else 0
                ),
                "is_primitive_only": agg.get("is_primitive_only", False),
            },
            sanitation_checks_passed=checks,
            created_run_id=run_id,
            created_utc=_dt.datetime.now(_dt.timezone.utc).isoformat(),
        )
        out.append(patch)
    return out


def get_pending_advisory_patches(project_dir: Path) -> list[dict[str, Any]]:
    """Return all advisory-mode patches in the ledger that are not yet
    committed. Used by the pre-iter-1 confirmation preflight to surface
    patches the operator never reviewed between runs."""
    entries = _read_ledger_entries(project_dir)
    return [
        e for e in entries
        if e.get("mode") == "advisory" and e.get("committed") is False
    ]


def _entry_to_charter_patch(entry: dict[str, Any]) -> CharterPatch:
    return CharterPatch(
        target=entry["target"],
        section_id=entry["section_id"],
        operation=entry["operation"],
        body=entry["body"],
        reframe_type=entry["reframe_type"],
        expiry_runs=entry.get("expiry_runs", DEFAULT_PATCH_EXPIRY_RUNS),
        fingerprint_match=entry.get("fingerprint_match", {}),
        sanitation_checks_passed=entry.get("sanitation_checks_passed", []),
        created_run_id=entry["created_run_id"],
        created_utc=entry.get("created_utc", ""),
    )


def _mark_entries_committed(project_dir: Path, body_shas: set[str]) -> None:
    ledger = project_dir / "workspace" / AUTO_PATCH_LEDGER
    if not ledger.exists():
        return
    out_lines: list[str] = []
    for raw in ledger.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            out_lines.append(raw)
            continue
        sha = _hashlib.sha256(entry.get("body", "").encode("utf-8")).hexdigest()[:12]
        if entry.get("mode") == "advisory" and sha in body_shas:
            entry["committed"] = True
            entry.setdefault("auto_confirmed_at", _dt.datetime.now(_dt.timezone.utc).isoformat())
        out_lines.append(json.dumps(entry))
    ledger.write_text("\n".join(out_lines) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------
# Pre-iter-1 advisory-patch confirmation (Q1 + Q2)
# ----------------------------------------------------------------------------

_REVIEWER_DEFAULTS_BY_GENERATOR_FAMILY = {
    "openai": "claude-haiku-4-5",
    "anthropic": "gpt-4.1-mini",
    "google": "claude-haiku-4-5",
}


def _resolve_reviewer_model_id(rubric_data: dict[str, Any], mutator_model_id: str | None) -> str:
    raw = str(rubric_data.get("charter_patches_reviewer_model_id") or "@cross_family").strip()
    if raw not in ("@cross_family", "cross_family"):
        if raw in ("@mutator", "mutator"):
            return (mutator_model_id or "").strip() or "claude-haiku-4-5"
        try:
            from src.ztare.common.llm_runtime import resolve_model_id
            return resolve_model_id(raw)
        except Exception:
            return raw
    try:
        from src.ztare.common.llm_runtime import get_model_family
        gen_family = get_model_family(mutator_model_id or "")
    except Exception:
        gen_family = "openai"
    return _REVIEWER_DEFAULTS_BY_GENERATOR_FAMILY.get(gen_family, "claude-haiku-4-5")


def _build_reviewer_prompt(
    patches: list[dict[str, Any]],
    project_dir: Path,
    operator_policy: str,
) -> str:
    evidence_path = project_dir / "evidence.txt"
    charter_path = project_dir / "project_charter.md"
    evidence_excerpt = evidence_path.read_text(encoding="utf-8")[:4000] if evidence_path.exists() else ""
    charter_excerpt = charter_path.read_text(encoding="utf-8")[:2500] if charter_path.exists() else ""
    patches_block = ""
    for i, p in enumerate(patches, 1):
        patches_block += (
            f"\n--- PATCH #{i} ---\n"
            f"reframe_type: {p.get('reframe_type')}\n"
            f"target: {p.get('target')}\n"
            f"generation: {p.get('fingerprint_match', {}).get('generation', 'light')}\n"
            f"created_run_id: {p.get('created_run_id')}\n"
            f"body:\n{p.get('body', '')}\n"
        )
    return (
        "You are a CROSS-FAMILY REVIEWER for GP-226 charter-critic patches awaiting\n"
        "operator approval before being applied to a ZTARE qualitative-thesis project.\n"
        "Your job is to decide which patches to APPLY and which to REJECT, on\n"
        "behalf of an operator who has delegated the review.\n\n"
        f"OPERATOR REVIEW POLICY:\n{operator_policy or '(none — apply standard charter-critic review discipline)'}\n\n"
        "CONTEXT — current evidence brief excerpt:\n"
        f"```\n{evidence_excerpt}\n```\n\n"
        "CONTEXT — current project charter excerpt:\n"
        f"```\n{charter_excerpt}\n```\n\n"
        "PATCHES PENDING REVIEW:\n"
        f"{patches_block}\n"
        "REVIEW CRITERIA — reject a patch if ANY of:\n"
        "1. The patch is substantively REDUNDANT with content already in evidence/charter.\n"
        "2. The patch contains GROUND-TRUTH leakage (oracle knowledge, harness internals, derivations).\n"
        "3. The patch is OFF-TOPIC for the substrate's decisive eigenquestion.\n"
        "4. The patch contains PROPER-NOUN endorsement of vendors/products/authors not already in evidence.\n"
        "5. The patch is an ANSWER/THESIS/SOLUTION rather than adversarial pressure.\n"
        "6. The patch violates the operator policy stated above.\n"
        "Otherwise APPROVE.\n\n"
        "OUTPUT FORMAT — strict JSON only, no preamble, no commentary:\n"
        "{\n"
        '  "verdict": "APPROVE_ALL" | "REJECT_ALL" | "PARTIAL",\n'
        '  "apply_indices": [<1-indexed patch numbers to apply>],\n'
        '  "reject_indices": [<1-indexed patch numbers to reject>],\n'
        '  "reason": "<one paragraph explaining the verdict>"\n'
        "}\n"
    )


def _review_via_llm(
    patches_entries: list[dict[str, Any]],
    project_dir: Path,
    rubric_data: dict[str, Any],
    mutator_model_id: str | None,
) -> tuple[set[int], str, str] | None:
    """Call the reviewer LLM with the pending advisory patches.

    Returns (apply_indices_set, reason, reviewer_model_id) on success;
    None on any failure (caller falls back to skip-on-failure behavior).
    """
    try:
        from src.ztare.common.llm_runtime import LLMRuntime
    except ImportError:
        return None
    operator_policy = str(rubric_data.get("charter_patches_reviewer_policy") or "")
    reviewer_id = _resolve_reviewer_model_id(rubric_data, mutator_model_id)
    prompt = _build_reviewer_prompt(patches_entries, project_dir, operator_policy)
    try:
        runtime = LLMRuntime()
        from src.ztare.common.dispatch_model import dispatch_call_text

        response = dispatch_call_text(
            "charter_critic_reviewer",
            prompt,
            llm_response_call=lambda p: runtime.call_text(
                p,
                model_id=reviewer_id,
                timeout_seconds=float(rubric_data.get("charter_patches_reviewer_timeout_seconds", 30.0)),
                request_label="charter_patches_reviewer",
                retries=1,
            ),
            timeout_seconds=int(float(rubric_data.get("charter_patches_reviewer_timeout_seconds", 30.0))),
        )
        raw = (response.text or "").strip()
    except Exception:
        return None
    obj = _extract_json_object(raw)
    if obj is None:
        return None
    apply_indices = set()
    for idx in obj.get("apply_indices", []) or []:
        try:
            apply_indices.add(int(idx))
        except (TypeError, ValueError):
            pass
    reason = str(obj.get("reason", ""))[:600]
    return apply_indices, reason, reviewer_id


def _extract_json_object(raw: str) -> dict[str, Any] | None:
    raw = raw.strip()
    if raw.startswith("```"):
        # Strip markdown fence
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"```\s*$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Fallback: find first {...} block
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


def confirm_pending_advisory_patches(
    *,
    rubric_data: dict[str, Any],
    project_dir: Path,
    run_id: str,
    mutator_model_id: str | None = None,
    is_tty: bool | None = None,
) -> dict[str, Any]:
    """Pre-iter-1 hook: detect pending advisory patches; confirm + apply
    per ``charter_patches_preflight_mode``.

    Modes:
      - "skip" (default): no-op.
      - "interactive": stdin prompt (falls back to skip in non-tty).
      - "auto_confirm": delegate to reviewer LLM (Q2 path).

    Returns a summary dict for caller logging.
    """
    project_dir = Path(project_dir)
    if not bool(rubric_data.get("enable_charter_critic", False)):
        return {"status": "skipped:charter_critic_disabled"}
    mode = str(rubric_data.get("charter_patches_preflight_mode") or "skip").lower().strip()
    if mode == "skip":
        return {"status": "skipped:mode=skip"}
    pending = get_pending_advisory_patches(project_dir)
    if not pending:
        return {"status": "no_pending_patches"}
    if is_tty is None:
        try:
            is_tty = sys.stdin.isatty()
        except Exception:
            is_tty = False

    if mode == "interactive":
        if not is_tty:
            return {"status": "skipped:non_tty", "pending_count": len(pending)}
        return _confirm_interactive(project_dir, pending)
    if mode == "auto_confirm":
        return _confirm_via_reviewer(
            project_dir, pending, rubric_data, mutator_model_id, run_id,
        )
    return {"status": f"skipped:unknown_mode={mode}"}


def _confirm_interactive(project_dir: Path, pending: list[dict[str, Any]]) -> dict[str, Any]:
    print()
    print("=" * 60)
    print(f"📋 GP-226 charter-critic: {len(pending)} pending advisory patch(es)")
    print("=" * 60)
    for i, p in enumerate(pending, 1):
        gen = p.get("fingerprint_match", {}).get("generation", "light")
        print(f"  [{i}] {p.get('reframe_type')} → {p.get('target')} "
              f"({gen}, run={p.get('created_run_id')})")
    print()
    while True:
        try:
            ans = input("Apply pending patches? [y=all / n=skip / d=details / N=indices] ").strip().lower()
        except EOFError:
            return {"status": "skipped:eof"}
        if ans in ("y", "yes"):
            apply_idx = set(range(1, len(pending) + 1))
            break
        if ans in ("n", "no", "skip", "s"):
            return {"status": "operator_skipped", "pending_count": len(pending)}
        if ans in ("d", "details"):
            for i, p in enumerate(pending, 1):
                print(f"\n--- patch [{i}] ---\n{p.get('body', '')}\n")
            continue
        # Try parse comma-separated indices
        try:
            apply_idx = {int(s.strip()) for s in ans.split(",") if s.strip()}
            if apply_idx and all(1 <= n <= len(pending) for n in apply_idx):
                break
        except ValueError:
            pass
        print("  (invalid input — try y, n, d, or comma-separated indices like '1,3')")
    return _apply_selected(project_dir, pending, apply_idx, source="interactive")


def _confirm_via_reviewer(
    project_dir: Path,
    pending: list[dict[str, Any]],
    rubric_data: dict[str, Any],
    mutator_model_id: str | None,
    run_id: str,
) -> dict[str, Any]:
    review = _review_via_llm(pending, project_dir, rubric_data, mutator_model_id)
    if review is None:
        return {"status": "skipped:reviewer_llm_failed",
                "pending_count": len(pending),
                "behavior": "patches remain pending — operator must commit manually"}
    apply_idx, reason, reviewer_model = review
    print()
    print("=" * 60)
    print(f"🤖 GP-226 charter-critic reviewer: {reviewer_model}")
    print(f"   verdict: applying {len(apply_idx)} of {len(pending)} pending patch(es)")
    print(f"   reason: {reason[:300]}")
    print("=" * 60)
    summary = _apply_selected(project_dir, pending, apply_idx, source="auto_confirm")
    summary["reviewer_model"] = reviewer_model
    summary["reviewer_reason"] = reason
    summary["reviewer_run_id"] = run_id
    # Append reviewer decision telemetry
    decision_log = project_dir / "workspace" / "charter_patches_reviewer_log.jsonl"
    with decision_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "run_id": run_id,
            "reviewer_model": reviewer_model,
            "pending_count": len(pending),
            "approved_count": len(apply_idx),
            "reason": reason,
        }) + "\n")
    return summary


def _apply_selected(
    project_dir: Path,
    pending: list[dict[str, Any]],
    apply_idx: set[int],
    source: str,
) -> dict[str, Any]:
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    committed_shas: set[str] = set()
    for i, entry in enumerate(pending, 1):
        if i not in apply_idx:
            skipped.append({"index": i, "reframe_type": entry.get("reframe_type")})
            continue
        try:
            patch = _entry_to_charter_patch(entry)
            applied_path = _apply_patch(project_dir, patch)
            applied.append({
                "index": i,
                "reframe_type": entry.get("reframe_type"),
                "target": entry.get("target"),
                "applied_path": str(applied_path.relative_to(project_dir)),
            })
            committed_shas.add(patch.body_sha)
        except Exception as exc:
            skipped.append({"index": i, "reframe_type": entry.get("reframe_type"),
                            "error": str(exc)})
    if committed_shas:
        _mark_entries_committed(project_dir, committed_shas)
    return {
        "status": "applied",
        "source": source,
        "applied": applied,
        "skipped": skipped,
    }


# ----------------------------------------------------------------------------
# Patch commit (advisory write-out path; used by run_charter_critic_post_run)
# ----------------------------------------------------------------------------

def commit_patch_advisory(project_dir: Path, patches: list[CharterPatch], run_id: str) -> Path:
    """Write all patches to a single candidate file for operator review.
    Operator commits via ``make charter-commit RUN=<run_id>``."""
    workspace = project_dir / "workspace"
    workspace.mkdir(exist_ok=True)
    out_path = workspace / ADVISORY_PATCH_FILENAME.format(run_id=run_id)
    lines: list[str] = []
    lines.append(f"# Charter-critic patch candidate — run {run_id}\n")
    lines.append(f"_GP-226 V1 advisory mode. Operator reviews each patch and commits via `make charter-commit RUN={run_id}`._\n")
    for i, p in enumerate(patches, 1):
        lines.append(f"\n---\n\n## Patch {i} — `{p.reframe_type}`\n")
        lines.append(f"- **target:** `{p.target}`")
        lines.append(f"- **section_id:** `{p.section_id}`")
        lines.append(f"- **operation:** `{p.operation}`")
        lines.append(f"- **expiry_runs:** {p.expiry_runs}")
        lines.append(f"- **body_sha:** `{p.body_sha}`")
        lines.append(f"- **fingerprint_match:** {json.dumps(p.fingerprint_match)}")
        lines.append(f"- **sanitation:** {p.sanitation_checks_passed}\n")
        lines.append("### Patch body\n\n```\n" + p.body + "\n```\n")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    ledger = workspace / AUTO_PATCH_LEDGER
    with ledger.open("a", encoding="utf-8") as f:
        for p in patches:
            f.write(json.dumps({**p.to_dict(), "mode": "advisory", "committed": False}) + "\n")
    return out_path


def commit_patch_auto(project_dir: Path, patches: list[CharterPatch], run_id: str) -> dict[str, Any]:
    """Auto-apply each patch to its target file, append to ledger,
    return a summary dict."""
    workspace = project_dir / "workspace"
    workspace.mkdir(exist_ok=True)
    summary: dict[str, Any] = {"applied": [], "skipped": []}
    for p in patches:
        try:
            applied_path = _apply_patch(project_dir, p)
            summary["applied"].append({
                "reframe_type": p.reframe_type,
                "target": p.target,
                "applied_path": str(applied_path.relative_to(project_dir)),
                "body_sha": p.body_sha,
            })
        except Exception as exc:
            summary["skipped"].append({
                "reframe_type": p.reframe_type,
                "reason": str(exc),
            })
    ledger = workspace / AUTO_PATCH_LEDGER
    with ledger.open("a", encoding="utf-8") as f:
        for p in patches:
            f.write(json.dumps({**p.to_dict(), "mode": "auto", "committed": True}) + "\n")
    return summary


def _apply_patch(project_dir: Path, patch: CharterPatch) -> Path:
    """Apply a CharterPatch to its target file. V1 supports append-mode
    only; replace/amend operations are V2."""
    if patch.operation != "append":
        raise NotImplementedError(f"V1 supports operation=append only; got {patch.operation}")
    if patch.target == "evidence":
        target_path = project_dir / "evidence.txt"
        existing = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
        new_text = existing.rstrip() + "\n\n" + patch.body + "\n"
        target_path.write_text(new_text, encoding="utf-8")
        return target_path
    if patch.target == "charter":
        target_path = project_dir / "project_charter.md"
        existing = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
        # Avoid double-H2: if the patch body already starts with `## REFRAME
        # PRESSURE` (which all our templates do), skip the section_id wrapper
        # because it would create two consecutive H2 headers and break the
        # briefing-compression block-matching signature.
        body_stripped = patch.body.lstrip()
        if body_stripped.startswith("## "):
            new_text = existing.rstrip() + "\n\n" + body_stripped + "\n"
        else:
            new_text = existing.rstrip() + "\n\n## " + patch.section_id + "\n\n" + patch.body + "\n"
        target_path.write_text(new_text, encoding="utf-8")
        return target_path
    if patch.target == "rubric_dimension":
        # V1 skips rubric_dimension auto-apply — too easy to break the
        # rubric JSON structure. Fall back to advisory write.
        out_path = project_dir / "workspace" / f"_rubric_dimension_pending_{patch.body_sha}.md"
        out_path.parent.mkdir(exist_ok=True)
        out_path.write_text(
            f"## Rubric-dimension patch (pending operator review)\n\n"
            f"reframe_type: {patch.reframe_type}\n"
            f"section_id: {patch.section_id}\n\n"
            f"```\n{patch.body}\n```\n",
            encoding="utf-8",
        )
        return out_path
    raise ValueError(f"unknown patch.target={patch.target}")


# ----------------------------------------------------------------------------
# Post-run dispatcher (V1 entry point)
# ----------------------------------------------------------------------------

def run_charter_critic_post_run(
    *,
    rubric_data: dict[str, Any],
    project_dir: Path,
    run_id: str,
    mutator_model_id: str | None = None,
) -> dict[str, Any] | None:
    """V1 post-run dispatcher. Called from ``run_post_loop_analyses``.

    Returns a small summary dict for caller logging, or None if the
    critic did not fire (gates not met).
    """
    if not bool(rubric_data.get("enable_charter_critic", False)):
        return None
    project_dir = Path(project_dir)

    spec_existed_before = (project_dir / "operator_value_spec.yaml").exists()
    value_spec = load_value_spec(project_dir, rubric_data=rubric_data, auto_generate=True)
    if value_spec is None:
        return {"status": "skipped:value_spec_load_failed"}
    auto_generated = not spec_existed_before

    substrate_class = str(value_spec.get("substrate_class") or "").strip()
    taxonomy = SUBSTRATE_TAXONOMIES.get(substrate_class)
    if not taxonomy:
        return {"status": "skipped:empty_taxonomy",
                "substrate_class": substrate_class,
                "reason": "no reframe types registered for this substrate class"}

    constraints = value_spec.get("constraints", {}) or {}
    max_patches = int(constraints.get("max_charter_patches_per_run", DEFAULT_MAX_PATCHES_PER_RUN))
    expiry_runs = int(constraints.get("patch_expiry_runs", DEFAULT_PATCH_EXPIRY_RUNS))
    mode = str(value_spec.get("mode") or "advisory").lower()

    if os.environ.get("OPERATOR_OVERRIDE_ADVISORY") == "1":
        mode = "advisory"

    weakest_points = extract_recent_weakest_points(project_dir, k=DEFAULT_K_DEBATES_TO_READ)
    if not weakest_points:
        return {"status": "skipped:no_debate_logs"}

    aggregated, unmatched = aggregate_fingerprints(
        weakest_points, taxonomy,
        rubric_data=rubric_data,
        mutator_model_id=mutator_model_id,
    )

    # Emit taxonomy-extension proposal artifact for unmatched fingerprints
    # (seam §8b 4g). Always logged even if patches are emitted — these
    # are operator review items, not blockers.
    proposal_path = None
    if unmatched:
        proposal_path = write_unmatched_fingerprint_artifact(
            project_dir, unmatched, run_id,
        )

    # Check patch expiry (seam §4h charter-rot mitigation)
    expired = check_patch_expiry(project_dir, run_id)

    if not aggregated:
        out = {
            "status": "skipped:no_fingerprint_match",
            "weakest_points_examined": len(weakest_points),
            "unmatched_count": len(unmatched),
        }
        if proposal_path is not None:
            out["taxonomy_proposal_path"] = str(proposal_path.relative_to(project_dir))
        if expired:
            out["expired_patches"] = expired
        return out

    patches = emit_patches(
        project_dir=project_dir,
        aggregated=aggregated,
        taxonomy=taxonomy,
        value_spec=value_spec,
        run_id=run_id,
        max_patches=max_patches,
        expiry_runs=expiry_runs,
        rubric_data=rubric_data,
        runtime_mutator_model_id=mutator_model_id,
    )
    if not patches:
        return {"status": "skipped:no_patches_passed_sanitation",
                "fingerprint_aggregations": len(aggregated)}

    if mode == "auto":
        result = commit_patch_auto(project_dir, patches, run_id)
        out = {
            "status": "committed:auto",
            "patches_applied": len(result.get("applied", [])),
            "patches_skipped": len(result.get("skipped", [])),
            "patch_summaries": [
                {"reframe_type": p.reframe_type,
                 "target": p.target,
                 "primitive": p.fingerprint_match.get("primitive"),
                 "fingerprint_recurrence": p.fingerprint_match.get("recurrence", 0),
                 "fingerprint_max_similarity": round(p.fingerprint_match.get("max_similarity", 0), 2),
                 "cross_run_patch_count": p.fingerprint_match.get("cross_run_patch_count", 0),
                 "cross_run_primitive_count": p.fingerprint_match.get("cross_run_primitive_count", 0),
                 "generation": p.fingerprint_match.get("generation", "light")}
                for p in patches
            ],
            "detail": result,
        }
    else:
        candidate_path = commit_patch_advisory(project_dir, patches, run_id)
        out = {
            "status": "candidate:advisory",
            "patches_emitted": len(patches),
            "candidate_path": str(candidate_path.relative_to(project_dir)),
            "patch_summaries": [
                {"reframe_type": p.reframe_type,
                 "target": p.target,
                 "primitive": p.fingerprint_match.get("primitive"),
                 "fingerprint_recurrence": p.fingerprint_match.get("recurrence", 0),
                 "fingerprint_max_similarity": round(p.fingerprint_match.get("max_similarity", 0), 2),
                 "cross_run_patch_count": p.fingerprint_match.get("cross_run_patch_count", 0),
                 "cross_run_primitive_count": p.fingerprint_match.get("cross_run_primitive_count", 0),
                 "generation": p.fingerprint_match.get("generation", "light")}
                for p in patches
            ],
            "next_step": f"operator review + `make charter-commit PROJECT={project_dir.name} RUN={run_id}`",
        }
    if proposal_path is not None:
        out["taxonomy_proposal_path"] = str(proposal_path.relative_to(project_dir))
        out["unmatched_count"] = len(unmatched)
    if expired:
        out["expired_patches"] = expired
    if auto_generated:
        out["auto_generated_value_spec"] = "operator_value_spec.yaml"
    return out


# ────────────────────────────────────────────────────────────────────
# META_APPARATUS_AUDIT_TAXONOMY templates (v0_experimental, 2026-05-06)
# ────────────────────────────────────────────────────────────────────


def _template_anchored_primitive_class(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — primitive-class anchoring (charter-critic GP-226 / GP-227)\n\n"
        "Recent iters have refined the SAME primitive class for ≥3 consecutive\n"
        "iters without proposing structurally distinct alternatives. The mutator's\n"
        "score-gradient anchored on the first primitive-class proposal that\n"
        "scored well; subsequent iters have produced incremental refinements\n"
        "rather than alternative primitive classes. This is the second-order\n"
        "anchoring failure mode (lane rotation worked, class rotation did not).\n\n"
        "REQUIREMENT for next run: the rubric MUST enforce per-class score\n"
        "capping (1st iter in class → 95 ceiling, 2nd → 80, 3rd → 65, 4th+ → 50).\n"
        "The mutator prompt MUST inject the list of already-explored primitive\n"
        "classes and explicitly forbid same-class refinement after the cap drop\n"
        "begins.\n\n"
        "See _primitive_class_rotation_discipline field in the rubric and\n"
        "src/ztare/orchestrator/prompt.py::primitive_class_history_packet()\n"
        "for the implementation. If next run still anchors, escalate the cap\n"
        "drops (e.g., 80 → 70 at 2nd iter)."
    )
    return ("charter", "PRIMITIVE-CLASS ROTATION DISCIPLINE", "append", body)


def _template_common_mode_unmitigated(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — common-mode mitigation required (charter-critic GP-226)\n\n"
        "The candidate primitive's guarantee depends on an INDEPENDENCE\n"
        "ASSUMPTION (e.g., recorders run on isolated infrastructure; voters\n"
        "have non-overlapping training data; redundant gates use disjoint\n"
        "code paths). The judge has surfaced common-mode vulnerability\n"
        "(supply chain, shared library, protocol overlap, social/legal\n"
        "common ownership) as the Achilles' heel that reintroduces single-\n"
        "point-of-failure invisibly.\n\n"
        "The next candidate proposing this primitive class MUST do EXACTLY ONE OF:\n\n"
        "(a) MITIGATE the common-mode risk with a SPECIFIC technical mechanism\n"
        "    (out-of-band fingerprinting, retrospective replay audit, etc.)\n"
        "    AND name the residual common-mode risk that survives the mitigation.\n\n"
        "(b) ADMIT the common-mode-vulnerability ceiling explicitly — name\n"
        "    the residual risk band and the deployment context where it's\n"
        "    acceptable. Honest scope-bound is a positive finding.\n\n"
        "(c) PIVOT to a different primitive class whose guarantee does NOT\n"
        "    rest on an independence assumption.\n\n"
        "Theses that hand-wave common-mode risk score zero on this pressure."
    )
    return ("evidence", "REFRAME PRESSURE — common-mode mitigation", "append", body)


def _template_single_substrate_fix(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — cross-substrate generality required (charter-critic GP-226)\n\n"
        "The candidate refinement addresses ONE substrate kind only (typically\n"
        "the substrate-specific failure mode that motivated the proposal). The\n"
        "rubric requires apparatus refinements to apply to ≥2 substrate kinds\n"
        "(numeric / qualitative / proof-target) to earn the full ceiling.\n\n"
        "REQUIREMENT for next iter: the candidate must name AT LEAST TWO\n"
        "substrate kinds the refinement applies to, AND demonstrate the named\n"
        "mechanism does not depend on substrate-specific data shapes. Examples\n"
        "of cross-substrate-applicable mechanisms: theorem-packet pre-declaration\n"
        "(applies to any cage'd substrate), cross-source divergence audit\n"
        "(applies to any multi-source mining setup), per-class score-cap\n"
        "rotation (applies to any iter loop with multiple candidate-types).\n\n"
        "Refinements that genuinely apply to one substrate only should be\n"
        "shipped via that substrate's own ZTARE run, not via this meta-\n"
        "apparatus substrate. The judge's score cap (75 for tactical-patch /\n"
        "single-substrate; 95 for primitive-class / cross-substrate) reflects\n"
        "this discipline."
    )
    return ("rubric_dimension", "CROSS-SUBSTRATE GENERALITY DIMENSION", "amend", body)


def _template_kill_criterion_unmeasurable(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — kill-criterion sharpening (charter-critic GP-226)\n\n"
        "The candidate's kill-criterion is unmeasurable as stated. For the\n"
        "v2 expanded-scope substrate, every candidate MUST name:\n\n"
        "  (a) WHICH next-cycle mining output the kill-criterion will be\n"
        "      measured in (trajectory_curves / reference_graph / taste_ledger\n"
        "      / recursive_gain_candidates / etc.)\n"
        "  (b) WHICH SPECIFIC METRIC and threshold (e.g., 'engagement_rate\n"
        "      of new gate ≥ 5%', 'compounding_ratio for week N+1 declines\n"
        "      by ≥0.5')\n"
        "  (c) WHICH DEADLINE (P14D / P28D / P56D / P90D — primitive-class\n"
        "      proposals get the longer deadlines)\n\n"
        "Without all three, the kill-criterion cannot be checked in next\n"
        "week's mining cycle, and the proposal is unreviewable. The rubric's\n"
        "Falsifiable Kill-Criterion dimension scores zero in this case."
    )
    return ("rubric_dimension", "FALSIFIABLE KILL-CRITERION SHARPENING", "amend", body)


def _template_ceremonial_form_overengineering(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — ceremonial PARAMETRIC_FORM (charter-critic GP-226)\n\n"
        "Recent iters have produced PARAMETRIC_FORM that triggers R1\n"
        "compiler-bounces (using disallowed functions like isinstance, sum,\n"
        "is_significant). For meta-apparatus-audit substrates, PARAMETRIC_FORM\n"
        "is CEREMONIAL — the cage doesn't actually fit it; the judge scores\n"
        "on the thesis prose. Complex discriminator logic should live in the\n"
        "thesis prose or the test_model.py harness, NOT inside PARAMETRIC_FORM.\n\n"
        "Use the PARAMETRIC_FORM theorem packet's allowed-function list (see\n"
        "src/ztare/orchestrator/prompt.py::parametric_form_theorem_packet).\n"
        "For audit-class substrates a stub like:\n\n"
        "  1 if rival_active == 0 and loop_revived == 1 else 0\n\n"
        "is sufficient. Multiple R1 bounces in a single iter signal that the\n"
        "mutator is over-engineering the form when complexity belongs in the\n"
        "thesis prose."
    )
    return ("charter", "CEREMONIAL PARAMETRIC_FORM CLAUSE", "append", body)


def _template_evidence_anchor_unverifiable(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — evidence anchor verifiability (charter-critic GP-226)\n\n"
        "Recent candidate(s) cited evidence anchors (JSONPath into mining-output\n"
        "snapshots in raw/) that did NOT resolve when the validator pre-flight\n"
        "checked them. Without verifiable anchoring, the candidate degenerates\n"
        "to verbal apparatus speculation — the v1 GP-134 Run-1 hollow-primitive\n"
        "failure mode at the v2 layer.\n\n"
        "REQUIREMENT for next iter: every evidence_anchor field must:\n\n"
        "  (a) Cite an ACTUAL file in projects/<slug>/raw/ with a snapshot date\n"
        "      within the last 7-14 days\n"
        "  (b) Provide a JSONPath that resolves against that file's actual\n"
        "      content (not a guessed schema)\n"
        "  (c) Provide a verbatim ≤200-char excerpt that matches the resolved\n"
        "      JSON value within whitespace tolerance\n\n"
        "The validator pre-flight will reject candidates whose anchors fail\n"
        "any of (a)-(c). Hand-waving 'this entry shows X is broken' without\n"
        "the resolved anchor is verbal speculation, not evidence-driven\n"
        "refinement."
    )
    return ("rubric_dimension", "EVIDENCE-ANCHOR VERIFIABILITY DIMENSION", "amend", body)


def _template_compounding_unanchored(project_slug: str, agg: dict, _spec: dict) -> tuple[str, str, str, str]:
    body = (
        "## REFRAME PRESSURE — compounding measurement required (charter-critic GP-226 / GP-227)\n\n"
        "The candidate claims its refinement will produce 'compounding gain'\n"
        "or 'next-week effect' but does NOT name the specific mining-output\n"
        "value whose change measures the compounding. The recursive-self-\n"
        "improvement loop the substrate is built on REQUIRES that compounding\n"
        "claims be anchored to a measurable cycle metric.\n\n"
        "REQUIREMENT for next candidate: every refinement that claims\n"
        "compounding effect must name:\n\n"
        "  (a) A SPECIFIC metric in a SPECIFIC mining-output file\n"
        "      (e.g., 'reference_graph.json::weekly_stats[<week>]'\n"
        "      '.n_outbound_to_earlier_weeks')\n"
        "  (b) The expected change DIRECTION and MAGNITUDE\n"
        "      (e.g., '+0.5 in compounding ratio' / '+15% in F-row closures')\n"
        "  (c) The deadline by which the change must be observable\n\n"
        "Without these, 'compounding' is hand-waved. The rubric's\n"
        "Generative Yield dimension scores in the 0-5 range for unanchored\n"
        "compounding claims, regardless of how persuasive the prose is."
    )
    return ("rubric_dimension", "COMPOUNDING-ANCHORED EVIDENCE DIMENSION", "amend", body)
