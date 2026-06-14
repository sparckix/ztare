#!/usr/bin/env python3
"""Weakest-link failure taxonomy — GP-148 Stage 2, Ticket A.

PURPOSE
Reads the enriched trajectory archive (1825 records, 84 projects) and clusters
the weakest_point field into a taxonomy of recurring failure families.  Each
cluster represents a distinct class of judge-identified weakness that appears
across multiple projects and iterations.  The output is the Falsification
Dictionary described in GP-148 seam §2.1: a precise mapping from "mathematical
intuitions frontier LLMs consistently hallucinate" to "judge verdict that kills
them."

METHODOLOGY
Keyword-taxonomy with prioritized regex rules.  Each cluster is defined by a
set of regex patterns applied to the lowercased weakest_point string.  When a
record matches multiple clusters, the FIRST matching cluster in priority order
wins (priority reflects specificity: harness defects are unambiguous and checked
first; vague over-claim patterns are checked last).  Records matching no cluster
are assigned to an "other_unclustered" catch-all.

Regex-taxonomy was chosen over TF-IDF + agglomerative clustering because:
(a) it requires no external dependencies beyond the standard library,
(b) the weakest_point vocabulary is structured (judge outputs follow a template),
(c) it produces deterministic, interpretable, auditable cluster definitions,
(d) it avoids the hyperparameter sensitivity (distance threshold, linkage) of
    agglomerative clustering on short heterogeneous text.

KNOWN LIMITATIONS
1. Regex rules are hand-crafted from a sample of ~15 records + domain knowledge
   of ZTARE judge outputs.  New failure families may emerge in future runs that
   fall through to "other_unclustered."
2. Multi-label assignment is not supported; a record belongs to exactly one
   cluster.  Some weakest_point strings exhibit compound failures (e.g., both
   circularity and over-claim) but are assigned to the first matching cluster.
3. The taxonomy reflects the JUDGE's assessment of weakness, not ground truth.
   Per GP-148 §3.1 Oracle Illusion, these are patterns of LLM-judge behavior
   and should not be treated as physical-reality verdicts without cross-judge
   validation.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
ARCHIVE = REPO / "analytics" / "trajectory_archive_enriched.jsonl"
OUTPUT_JSON = REPO / "analytics" / "public" / "queries" / "weakest_link_clusters_2026-04-24.json"
OUTPUT_README = REPO / "analytics" / "public" / "queries" / "weakest_link_clusters_2026-04-24_README.md"

# ── Cluster definitions ──────────────────────────────────────────────────
# Each tuple: (cluster_id, display_name, list_of_regex_patterns)
# Order matters: first match wins.  More specific patterns first.

CLUSTER_DEFS: list[tuple[str, str, list[str]]] = [
    # ── Tier 1: unambiguous infrastructure failures ──
    (
        "harness_defect",
        "Harness / Test-Suite Defect",
        [
            r"harness",
            r"fail_runtime",
            r"fail_assert",
            r"suite did not run",
            r"test.*(?:crash|exception|error|timeout)",
            r"falsification suite.*(?:fail|error|crash|did not)",
            r"level\s*3.*(?:fail|defect|error|crash|did not run)",
            r"runtime\s*(?:exception|error|failure)",
            r"unit\s+test.*(?:fail|maximum\s+absolute\s+residual)",
            r"fit\s+accuracy.*(?:exceed|fail|threshold)",
        ],
    ),
    (
        "no_thesis_proposed",
        "No Thesis / Placeholder Submission",
        [
            r"no\s+model\s+proposed",
            r"intentionally\s+wrong",
            r"no\s+(?:current\s+)?(?:attempt|thesis|proposal|model)",
            r"placeholder",
            r"empty\s+(?:thesis|submission|proposal)",
            r"fails?\s+to\s+(?:address|propose|present)\s+(?:the\s+)?core\s+(?:mandate|task|requirement)",
        ],
    ),
    # ── Tier 2: structural logic errors ──
    (
        "circularity",
        "Circularity / Tautology / Self-Reference",
        [
            r"circular",
            r"tautolog",
            r"self.?referenti",
            r"hard\s+self.?reference",
            r"semantic.?gate\s+derivation\s+classified.*(?:self.?reference|hard)",
            r"structured\s+semantic.?gate",
            r"assumes?\s+(?:what|the\s+thing)\s+(?:it|to)\s+(?:prove|show|demonstrate)",
            r"begs?\s+the\s+question",
        ],
    ),
    # ── Tier 3: core mathematical/evidential failures ──
    (
        "tail_generalization",
        "Tail / Extrapolation / Far-Field Generalization Failure",
        [
            r"farther.?tail",
            r"tail\s+(?:generali|extrapol|predict|behavi|ratio|decay|scaling|region)",
            r"(?:poor|fail|weak|bad|no)\s+(?:farther.?)?tail\s+(?:generali|fit|predict|extrapol)",
            r"beyond\s+(?:the\s+)?(?:training|observed|visible|fitted)\s+(?:data|range|domain|region)",
            r"large.?(?:n|x|u|phi)\s+(?:behavi|scaling|asymptot|extrapol|limit)",
            r"(?:asymptot|scaling\s+law)\s+(?:assumption|claim|not\s+(?:valid|robust|support))",
            r"arbitrarily\s+large",
            r"indefinite\s+robustness.*(?:farther|tail|beyond)",
        ],
    ),
    (
        "unverified_bound",
        "Unverified Bound / Unproven Claim",
        [
            r"unproven",
            r"unverified",
            r"no\s+(?:explicit\s+)?derivation",
            r"non.?constructive",
            r"without\s+(?:explicit\s+)?(?:proof|derivation|justification|verification)",
            r"asserted?\s+without",
            r"claimed?\s+without\s+(?:proof|evidence|justification)",
            r"no\s+(?:formal\s+)?proof",
            r"lacks?\s+(?:formal\s+)?(?:proof|derivation|justification)",
            r"not\s+(?:formally\s+)?(?:derived|proven|justified|verified)",
            r"unjustified\s+(?:inference|claim|assumption|extrapolation)",
        ],
    ),
    (
        "exhaustiveness_claim",
        "Exhaustiveness / Completeness Over-Claim",
        [
            r"exhaustive",
            r"completeness",
            r"coverage\s+proof",
            r"assumes?\s+every",
            r"no\s+(?:coverage|completeness)\s+(?:proof|guarantee|argument)",
            r"all\s+(?:possible|relevant)\s+(?:cases|modes|scenarios)",
            r"structurally\s+incomplete",
        ],
    ),
    (
        "model_class_restriction",
        "Model Class / Functional Form Restriction",
        [
            r"model\s+class\s+restriction",
            r"functional\s+form\s+(?:restriction|assumption|limitation)",
            r"restricts?\s+(?:to|the)\s+(?:a\s+)?(?:particular|specific|single|two|linear|exponential|polynomial)",
            r"(?:assumes?|limited\s+to)\s+(?:a\s+)?(?:specific|particular|single)\s+(?:functional|model)\s+(?:form|class)",
            r"model\s+(?:may\s+)?misrepresent",
            r"alternative\s+(?:functional\s+)?forms?\s+(?:not\s+)?(?:consider|explor|test)",
            r"(?:assumes?\s+)?(?:a\s+)?(?:closed.?form|analytic)\s+(?:expression|function|form)",
            r"single\s+(?:logarithmic|exponential|polynomial|algebraic)\s+(?:functional\s+)?form",
            r"other\s+(?:sub.?exponential|power.?law|stretched)\s+(?:model|form)",
            r"empirically\s+motivated\s+but\s+not\s+uniquely",
            r"(?:rational|algebraic)\s+(?:function|form)\s+in\s+(?:log|n|x)",
        ],
    ),
    (
        "fit_parameter_overclaim",
        "Fit Parameter / Over-Interpretation of Numerical Artifact",
        [
            r"fit\s+parameter\s+(?:without|not|lack)",
            r"(?:parameter|coefficient)\s+(?:value|choice)\s+(?:not|un)\s*(?:derived|justified)",
            r"(?:no|lack\s+of|without)\s+(?:explicit\s+)?(?:derivation|justification)\s+(?:of|for)\s+(?:every|all|each|the)?\s*(?:fit\s+)?param",
            r"over.?interpret(?:ation|ed|ing)",
            r"catastrophic\s+over.?interpret",
            r"numerical\s+coincidence",
            r"treating\s+(?:a\s+)?(?:numerical|fitted|empirical)\s+(?:coincidence|artifact|value)\s+as\s+(?:evidence|proof|structural)",
        ],
    ),
    # ── Tier 4: assumption / inference errors ──
    (
        "catastrophic_assumption",
        "Catastrophic / Load-Bearing Assumption",
        [
            r"catastrophic\s+(?:assumption|reliance|weakness)",
            r"most\s+catastrophic",
            r"load.?bearing\s+assumption",
            r"(?:core|fundamental|critical|decisive)\s+(?:assumption|flaw|weakness)\s+(?:is|that)",
            r"(?:single\s+most|most\s+critical)\s+(?:catastrophic\s+)?(?:assumption|weakness|flaw|vulnerability)",
        ],
    ),
    (
        "causal_assumption",
        "Causal / Identification Assumption",
        [
            r"causal\s+(?:logic|claim|inference|identification|assumption)",
            r"(?:un)?proven\s+(?:causal|identification)\s+(?:assumption|claim)",
            r"(?:cannot|does\s+not)\s+(?:establish|prove|demonstrate)\s+(?:causal|causation)",
            r"endogen",
            r"confound",
            r"selection\s+bias",
            r"omitted\s+variable",
            r"(?:hinges?|rests?|relies?)\s+on\s+(?:an?\s+)?unprovable\s+assumption",
            r"counterfactual.*(?:unbound|unverif|not\s+(?:establish|bound|quantif))",
        ],
    ),
    (
        "generalization_overclaim",
        "Over-Claim of Generalization",
        [
            r"over.?claim",
            r"generali[sz](?:ation|ability|e)\s+(?:not|un|without|lack|limit)",
            r"(?:cannot|does\s+not|fails?\s+to)\s+generali[sz]e",
            r"out.?of.?(?:sample|distribution|domain)\s+(?:fail|collaps|break|not)",
            r"only\s+(?:works?|valid|holds?|tested)\s+(?:for|on|within)\s+(?:a\s+)?(?:single|one|this|the\s+training)",
            r"systemic\s+inability\s+to\s+generalize",
            r"no\s+function\s+inference",
            r"collapses?\s+out.?of.?sample",
        ],
    ),
    # ── Tier 5: secondary structural issues ──
    (
        "empirical_tuning",
        "Empirically Tuned / Ad-Hoc Parameter",
        [
            r"empirically\s+tuned",
            r"ad.?hoc\s+(?:parameter|constant|coefficient|value|choice)",
            r"magic\s+(?:number|constant|value)",
            r"(?:parameter|constant|coefficient|value)\s+(?:not|un)\s*(?:derived|justified|motivated)",
            r"fitted?\s+(?:parameter|constant)\s+(?:without|not|lack)",
            r"calibrat(?:ed|ion)\s+(?:without|not|lack)",
        ],
    ),
    (
        "gate_boundary",
        "Gate / Threshold Boundary Issue",
        [
            r"gate\s+(?:boundary|threshold|too\s+strict|too\s+lenient)",
            r"threshold\s+(?:arbitrary|unjustified|too\s+strict|too\s+lenient)",
            r"tolerance\s+(?:arbitrary|unjustified|not\s+derived)",
            r"cutoff\s+(?:arbitrary|unjustified|not\s+derived)",
            r"±\s*\d+%?\s*(?:threshold|tolerance|cutoff)",
        ],
    ),
    (
        "data_validity",
        "Data Validity / Source Reliability Issue",
        [
            r"data\s+(?:source|quality|reliab|validity|integrity)",
            r"(?:median|mean|average)\s+(?:wages?|rents?|prices?|values?)\s+(?:from|via|using)\s+",
            r"combining\s+(?:regional|city|county|state|national)",
            r"(?:zillow|bls|census|hud|fmr)\b",
            r"ecological\s+fallacy",
            r"aggregat(?:ed|ion)\s+bias",
        ],
    ),
    (
        "numerical_instability",
        "Numerical Instability / Precision Issue",
        [
            r"numerical\s+(?:instability|precision|overflow|underflow|error)",
            r"(?:floating|finite)\s+(?:point|precision)\s+(?:error|issue|problem|artifact)",
            r"catastrophic\s+cancellation",
            r"ill.?condition",
            r"(?:over|under)flow",
            r"convergence\s+(?:fail|not\s+guarantee|issue)",
        ],
    ),
    # ── Tier 6: broad catch patterns (low priority, last resort before "other") ──
    (
        "finite_data_extrapolation",
        "Finite-Data Inference / Unjustified Extrapolation",
        [
            r"finite.?(?:range|data|sample|observation|window)\s+(?:data\s+)?(?:cannot|does\s+not|insufficient|inadequate)",
            r"(?:fitted?|trained|observed)\s+(?:on|to|from)\s+(?:finite|limited|small|narrow)",
            r"(?:no|without|lack)\s+(?:theoretical|deep|physical|mathematical)\s+(?:justification|grounding|motivation|derivation)",
            r"(?:locali[sz]ed|finite|limited)\s+(?:log.?space|data|evidence|observation).*(?:global|universal|general|analytic)",
            r"deterministic.*(?:algebraic|analytic).*(?:capture|explain|account).*(?:discrete|integer|irregular)",
        ],
    ),
    (
        "valuation_incomplete",
        "Incomplete Valuation / Quantification Gap",
        [
            r"valuation\s+(?:bridge|gap|incomplete|missing)",
            r"never\s+quantif",
            r"(?:no|without|lack)\s+(?:explicit\s+)?quantif(?:ication|ied)",
            r"(?:does\s+not|fails?\s+to)\s+quantif",
            r"(?:structurally|analytically)\s+incomplete",
            r"(?:no|without)\s+(?:explicit\s+)?(?:numerical|quantitative)\s+(?:benchmark|target|bound)",
        ],
    ),
]


def classify_weakest_point(text: str) -> str:
    """Return the cluster_id for the given weakest_point text."""
    lower = text.lower()
    for cluster_id, _name, patterns in CLUSTER_DEFS:
        for pat in patterns:
            if re.search(pat, lower):
                return cluster_id
    return "other_unclustered"


def extract_top_keywords(texts: list[str], top_n: int = 10) -> list[str]:
    """Simple keyword extraction: tokenize, remove stopwords, count."""
    STOP = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "through", "during",
        "before", "after", "above", "below", "between", "out", "off", "over",
        "under", "again", "further", "then", "once", "and", "but", "or",
        "nor", "not", "no", "so", "yet", "both", "either", "neither", "each",
        "every", "all", "any", "few", "more", "most", "other", "some", "such",
        "only", "own", "same", "than", "too", "very", "just", "also", "now",
        "its", "it", "this", "that", "these", "those", "he", "she", "they",
        "we", "you", "i", "me", "him", "her", "us", "them", "my", "your",
        "his", "our", "their", "what", "which", "who", "whom", "when",
        "where", "why", "how", "if", "because", "while", "although", "unless",
        "until", "about", "up", "down", "s", "t", "re", "ve", "d", "ll",
        "m", "o", "don", "didn", "doesn", "won", "wouldn", "couldn",
        "shouldn", "isn", "aren", "wasn", "weren", "hasn", "haven", "hadn",
    }
    TOKEN_RE = re.compile(r"[a-z_]{3,}")
    counts: dict[str, int] = defaultdict(int)
    for text in texts:
        for tok in TOKEN_RE.findall(text.lower()):
            if tok not in STOP:
                counts[tok] += 1
    return [w for w, _ in sorted(counts.items(), key=lambda x: -x[1])[:top_n]]


def main() -> int:
    if not ARCHIVE.is_file():
        print(f"ERROR: {ARCHIVE} not found.", file=sys.stderr)
        return 1

    # Load records
    records: list[dict[str, Any]] = []
    with ARCHIVE.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    print(f"Loaded {len(records)} records")

    # Classify
    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    cluster_labels: dict[tuple[str, int], str] = {}  # (project, iter_ts) -> cluster_id

    for rec in records:
        wp = rec.get("weakest_point")
        if not wp:
            cluster_id = "null_weakest_point"
        else:
            cluster_id = classify_weakest_point(wp)
        clusters[cluster_id].append(rec)
        ts = rec.get("iter_timestamp")
        if ts is not None:
            cluster_labels[(rec["project"], ts)] = cluster_id

    # Build cluster names lookup
    cluster_names = {cid: name for cid, name, _ in CLUSTER_DEFS}
    cluster_names["other_unclustered"] = "Other / Unclustered"
    cluster_names["null_weakest_point"] = "Null Weakest Point"

    # Build output
    output_clusters = []
    for cluster_id in sorted(clusters.keys(), key=lambda c: -len(clusters[c])):
        recs = clusters[cluster_id]
        # Exemplars: pick 3 diverse weakest_point strings (from different projects)
        seen_projects = set()
        exemplars = []
        for r in recs:
            wp = r.get("weakest_point", "")
            proj = r["project"]
            if proj not in seen_projects and wp:
                exemplars.append(wp[:300])
                seen_projects.add(proj)
            if len(exemplars) >= 3:
                break

        # Top keywords from all weakest_point strings in this cluster
        all_wps = [r.get("weakest_point", "") for r in recs if r.get("weakest_point")]
        top_kw = extract_top_keywords(all_wps)

        # Project coverage
        projects_in_cluster = set(r["project"] for r in recs)

        # (project, iter_ts) tuples
        members = [(r["project"], r["iter_timestamp"]) for r in recs]

        output_clusters.append({
            "cluster_id": cluster_id,
            "cluster_name": cluster_names.get(cluster_id, cluster_id),
            "size": len(recs),
            "project_count": len(projects_in_cluster),
            "exemplars": exemplars,
            "top_keywords": top_kw,
            "members": members,
        })

    output = {
        "generated": "2026-04-24",
        "source": str(ARCHIVE),
        "total_records": len(records),
        "total_classified": sum(len(v) for v in clusters.values()),
        "methodology": "keyword-taxonomy with prioritized regex rules",
        "cluster_count": len(output_clusters),
        "clusters": output_clusters,
    }

    # Also emit a flat label file for downstream scripts to consume
    label_records = []
    for (proj, ts), cid in sorted(cluster_labels.items()):
        label_records.append({"project": proj, "iter_timestamp": ts, "cluster_id": cid})

    output["_labels"] = label_records

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSON.open("w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Wrote {OUTPUT_JSON}")

    # ── README ────────────────────────────────────────────────────────────
    readme_lines = [
        "# Weakest-Link Failure Taxonomy (2026-04-24)",
        "",
        f"Generated from {len(records)} iteration records across "
        f"{len(set(r['project'] for r in records))} projects.",
        "",
        "Methodology: keyword-taxonomy with prioritized regex rules (see script docstring).",
        "",
        "---",
        "",
    ]
    for cl in output_clusters:
        cid = cl["cluster_id"]
        size = cl["size"]
        pcount = cl["project_count"]
        name = cl["cluster_name"]
        readme_lines.append(f"## {name} (`{cid}`)")
        readme_lines.append("")
        readme_lines.append(
            f"**Size:** {size} iterations across {pcount} projects."
        )
        readme_lines.append("")
        # Write a descriptive paragraph
        CLUSTER_DESCRIPTIONS = {
            "harness_defect": (
                "Iterations where the Level-3 falsification test suite itself failed to "
                "execute correctly -- runtime exceptions, assertion failures, timeouts, or "
                "crashes in the harness rather than substantive thesis weaknesses. These are "
                "infrastructure failures, not epistemic ones: the judge could not evaluate the "
                "thesis because the test machinery broke. Fixing harness defects is a "
                "prerequisite, not a scientific improvement."
            ),
            "no_thesis_proposed": (
                "Iterations where no actual thesis was submitted -- the mutator produced a "
                "placeholder, an 'intentionally wrong' baseline, or explicitly stated 'no "
                "model proposed yet.' These represent the cold-start phase before the mutator "
                "has enough signal to construct a substantive proposal."
            ),
            "circularity": (
                "Iterations where the thesis was flagged for circular reasoning, tautological "
                "structure, or hard self-reference -- the conclusion presupposes the premise, "
                "or the derivation assumes the result it claims to prove. Includes iterations "
                "where the structured semantic-gate derivation classified the proof as 'hard "
                "self-reference.' This is a structural logic error that requires architectural "
                "restructuring of the argument."
            ),
            "tail_generalization": (
                "Iterations where the thesis failed to generalize to the far tail of the data "
                "distribution -- good fits on observed/training data but catastrophic failure "
                "beyond the fitted range. The judge identified that asymptotic, large-n, or "
                "large-parameter behavior was assumed rather than derived, making extrapolation "
                "unreliable. This is the dominant failure mode in numerical-law-discovery tasks."
            ),
            "unverified_bound": (
                "Iterations where a critical bound, derivation step, or quantitative claim "
                "was asserted without formal proof or constructive derivation. The judge "
                "identified a decision-critical assumption that the mutator treated as given but "
                "never justified."
            ),
            "exhaustiveness_claim": (
                "Iterations where the thesis claimed completeness or exhaustiveness without "
                "providing a coverage proof. The mutator asserted 'all cases are handled' or "
                "'every relevant scenario is addressed' but the judge found no argument that "
                "the enumeration is actually exhaustive."
            ),
            "model_class_restriction": (
                "Iterations where the thesis restricted itself to a specific functional form "
                "or model class without justifying why alternatives were excluded. The judge "
                "flagged that closed-form analytic expressions, single-logarithmic forms, or "
                "restricted algebraic compositions may misrepresent the underlying phenomenon."
            ),
            "fit_parameter_overclaim": (
                "Iterations where the thesis over-interpreted a fitted parameter value, "
                "ratio, or delta -- treating a numerical coincidence or empirical artifact as "
                "evidence for a structural claim without deriving why that specific value is "
                "expected from the model."
            ),
            "catastrophic_assumption": (
                "Iterations where the judge identified a single catastrophic or decision-critical "
                "assumption that the entire thesis rests on. If that assumption is wrong, the "
                "thesis collapses entirely. These are structural single-points-of-failure in "
                "the argument architecture."
            ),
            "causal_assumption": (
                "Iterations where a causal or identification assumption was flagged as "
                "unproven -- the thesis inferred causation from correlation, ignored "
                "confounders, relied on an untestable identification strategy, or failed to "
                "bound its counterfactual claims."
            ),
            "generalization_overclaim": (
                "Iterations where the thesis claimed broader applicability than the evidence "
                "supports -- out-of-sample collapse, inability to generalize beyond the "
                "training distribution, or single-dataset conclusions presented as universal."
            ),
            "empirical_tuning": (
                "Iterations where parameters were empirically tuned or calibrated without "
                "derivation from the model structure. Ad-hoc constants, magic numbers, and "
                "fitted parameters without physical or mathematical motivation."
            ),
            "gate_boundary": (
                "Iterations where an arbitrary or unjustified threshold, tolerance, or "
                "gate boundary was identified as the weakest element. The numerical cutoff "
                "is decision-critical but its value was not derived from first principles."
            ),
            "data_validity": (
                "Iterations where the judge identified concerns about data source reliability, "
                "aggregation bias, ecological fallacy, or mismatched geographic/temporal "
                "granularity in the evidence supporting the thesis."
            ),
            "numerical_instability": (
                "Iterations where numerical precision, floating-point artifacts, or "
                "convergence failures were identified as the weakest link. The mathematical "
                "claim may be correct in theory but the computational implementation is "
                "unreliable."
            ),
            "finite_data_extrapolation": (
                "Iterations where the thesis extrapolated from finite, limited, or localized "
                "data to make global or universal claims without theoretical grounding. The "
                "judge flagged that the fitted or observed data window is insufficient to "
                "support the scope of the conclusion."
            ),
            "valuation_incomplete": (
                "Iterations where the thesis was structurally incomplete in its quantification "
                "-- key claims were made without explicit numerical benchmarks, bounds, or "
                "targets, leaving the argument unanchored."
            ),
            "other_unclustered": (
                "Iterations whose weakest_point text did not match any of the defined "
                "failure-family regex patterns. These may represent novel failure modes "
                "not yet captured in the taxonomy, or weakest_point strings that use "
                "unusual phrasing for a known failure family."
            ),
            "null_weakest_point": (
                "Iterations where the weakest_point field was null or empty in the "
                "enriched archive. These are typically early-stage iterations where the "
                "judge output could not be parsed, or harness-level failures that "
                "prevented judge evaluation entirely."
            ),
        }
        desc = CLUSTER_DESCRIPTIONS.get(cid, f"Cluster '{cid}' -- no description available.")
        if isinstance(desc, str):
            readme_lines.append(desc)
        readme_lines.append("")
        readme_lines.append(f"**Top keywords:** {', '.join(cl['top_keywords'][:10])}")
        readme_lines.append("")

    with OUTPUT_README.open("w") as f:
        f.write("\n".join(readme_lines) + "\n")
    print(f"Wrote {OUTPUT_README}")

    # Summary
    print("\n=== Cluster Summary ===")
    for cl in output_clusters:
        cross_note = ""
        if cl["project_count"] < 3:
            cross_note = " [PROVISIONAL: <3 projects]"
        print(f"  {cl['cluster_id']:30s}  size={cl['size']:5d}  projects={cl['project_count']:3d}{cross_note}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
