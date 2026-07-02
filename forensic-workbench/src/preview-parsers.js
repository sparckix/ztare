// Pure file-preview parsers + their shared label helpers, extracted from main.js (no React).
// Each *FromPreview takes a filePreview ({path,text,...}) and returns a plain summary object.

export function guidanceText(value) {
  return displayText(value)
    .replace(/\bGP-?233\b/gi, "evidence ledger")
    .replace(/\bgp233\b/gi, "evidence ledger")
    .replace(/\bGP-?230\b/gi, "forecast record")
    .replace(/\bgp230\b/gi, "forecast record")
    .replace(/\bmarkdown-only\b/gi, "doc-only")
    .replace(/\bsurfacing-event ledger\b/gi, "work ledger")
    .replace(/\bsurfacing event ledger\b/gi, "work ledger")
    .replace(/\btrajectory archive\b/gi, "run-history archive");
}

export const GUIDANCE_LABELS = {
  weak_gp233_linkage: "Evidence links need repair",
  stale_trajectory_output: "Run-history archive is stale",
  unconsumed_surface: "Work log is missing",
  source_compilation_defect: "Source compilation needs repair",
  repair_source_emitter: "Repair source logs",
  split_contract: "Split into a smaller question",
  ask_another_independent_agent: "Ask for another independent check",
  defer: "Defer",
  surface_trajectory_cluster: "Review related run history",
  diagnostic_only: "Diagnostic only",
  none_advisory_only: "Suggestion only",
  gp230_read_model: "forecast record summary",
  advisory: "Guidance",
  source_health: "File/evidence warning"
};

export function guidanceLabel(value) {
  const raw = String(value || "");
  const mapped = GUIDANCE_LABELS[raw] || raw;
  return guidanceText(mapped).replace(/_/g, " ");
}

export function sourceBasename(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  const parts = raw.split(/[\\/]/);
  return parts[parts.length - 1] || "";
}

export function uniqueLines(values) {
  const seen = new Set();
  const lines = [];
  (values || []).forEach((value) => {
    const text = String(value || "").trim();
    if (!text || seen.has(text)) return;
    seen.add(text);
    lines.push(text);
  });
  return lines;
}

export function linesFromText(value) {
  return String(value || "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

export function parseJsonLikeText(value) {
  const text = String(value || "").trim();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    if (!text.includes("\n")) return null;
    const rows = linesFromText(text).slice(0, 6);
    const parsed = [];
    for (const row of rows) {
      try {
        parsed.push(JSON.parse(row));
      } catch {
        return null;
      }
    }
    return parsed;
  }
}

export function savedProjectSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  const summary = parsed.project_summary && typeof parsed.project_summary === "object" ? parsed.project_summary : null;
  if (!summary) return null;
  const topLevelAudit = parsed.project_to_thesis_audit && typeof parsed.project_to_thesis_audit === "object"
    ? parsed.project_to_thesis_audit
    : null;
  const projectChecks = Array.isArray(parsed.project_checks)
    ? parsed.project_checks
    : Array.isArray(parsed.items)
      ? parsed.items
      : Array.isArray(parsed.rows)
        ? parsed.rows
        : [];
  const recentReceipts = Array.isArray(parsed.recent_receipts) ? parsed.recent_receipts : [];
  const actionDetails = Array.isArray(parsed.action_details)
    ? parsed.action_details
    : Array.isArray(parsed.audit_commands)
      ? parsed.audit_commands
      : Array.isArray(parsed.command_queue)
        ? parsed.command_queue
        : [];
  return {
    ...summary,
    project_to_thesis_audit: summary.project_to_thesis_audit || topLevelAudit || null,
    project: summary.project || parsed.project || "",
    intake: summary.intake || parsed.intake || "",
    project_check_count: parsed.project_check_count || parsed.item_count || parsed.row_count || projectChecks.length,
    project_checks: projectChecks.filter(Boolean).slice(0, 10),
    recent_receipts: recentReceipts.filter(Boolean).slice(0, 8),
    action_details: actionDetails.filter(Boolean).slice(0, 8)
  };
}

export function projectIntakeSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  if (!parsed.bounded_claim && !parsed.source_refs && !parsed.evidence_refs) return null;
  return {
    project: parsed.project || "",
    task: parsed.task || "",
    claim: parsed.bounded_claim || parsed.claim || "",
    nextFalsifier: parsed.next_falsifier || "",
    command: parsed.expected_command || "",
    sourceRefs: Array.isArray(parsed.source_refs) ? parsed.source_refs.filter(Boolean).slice(0, 12) : [],
    evidenceRefs: Array.isArray(parsed.evidence_refs) ? parsed.evidence_refs.filter(Boolean).slice(0, 12) : [],
    nonClaims: Array.isArray(parsed.non_claims) ? parsed.non_claims.filter(Boolean).slice(0, 6) : []
  };
}

export function projectLaunchBundleSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  const path = String((filePreview && filePreview.path) || "");
  const displayKind = String((filePreview && filePreview.display_kind) || "");
  if (!path.endsWith("_packet.json") && displayKind !== "Project launch bundle") return null;
  if (!parsed.bounded_claim && !parsed.expected_command && !parsed.execution_boundary) return null;
  return {
    project: parsed.project || projectKeyFromPreviewPath(path),
    claim: parsed.bounded_claim || parsed.claim || "",
    task: parsed.task || "",
    executionBoundary: parsed.execution_boundary || "",
    expectedCommand: parsed.expected_command || "",
    nextFalsifier: parsed.next_falsifier || "",
    notes: parsed.notes || "",
    sourceRefs: Array.isArray(parsed.source_refs) ? parsed.source_refs.filter(Boolean).slice(0, 12) : [],
    evidenceRefs: Array.isArray(parsed.evidence_refs) ? parsed.evidence_refs.filter(Boolean).slice(0, 12) : [],
    nonClaims: Array.isArray(parsed.non_claims) ? parsed.non_claims.filter(Boolean).slice(0, 8) : []
  };
}

export function scoringGuideSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  const path = String((filePreview && filePreview.path) || "");
  const displayKind = String((filePreview && filePreview.display_kind) || "");
  if (!path.startsWith("rubrics/") && displayKind !== "Scoring guide") return null;
  const dimensions = Array.isArray(parsed.dimensions)
    ? parsed.dimensions.filter((row) => row && typeof row === "object").slice(0, 12)
    : [];
  const criteriaObject = parsed.criteria && typeof parsed.criteria === "object" && !Array.isArray(parsed.criteria)
    ? parsed.criteria
    : {};
  const criteriaRows = Object.entries(criteriaObject).slice(0, 12).map(([key, value]) => ({
    name: key,
    text: value && typeof value === "object" ? JSON.stringify(value) : String(value || "")
  }));
  const totalWeight = dimensions.reduce((sum, row) => {
    const weight = Number(row.weight);
    return Number.isFinite(weight) ? sum + weight : sum;
  }, 0);
  const rubricName = sourceBasename(path).replace(/\.json$/i, "");
  return {
    project: parsed.project || rubricName,
    description: parsed.description || "",
    persona: parsed.persona || "",
    mode: parsed.rubric_mode || parsed.falsification_mode || parsed.rubric_version || "",
    modeReason: parsed.rubric_mode_reason || "",
    dimensions: dimensions.map((row, index) => ({
      name: row.name || `Dimension ${index + 1}`,
      weight: row.weight,
      description: row.description || ""
    })),
    criteriaRows,
    totalWeight,
    hasDimensions: dimensions.length > 0,
    penaltyRows: criteriaRows.filter((row) => /penalty|deduct|-/.test(`${row.name} ${row.text}`.toLowerCase())).slice(0, 4)
  };
}

export function projectKeyFromPreviewPath(path) {
  const parts = String(path || "").split("/");
  return parts[0] === "projects" && parts[1] ? parts[1] : "";
}

export function sourceIndexSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  const sources = Array.isArray(parsed.sources)
    ? parsed.sources.filter((source) => source && typeof source === "object").slice(0, 12)
    : [];
  if (!sources.length && !parsed.generated_on && !parsed.project) return null;
  const project = parsed.project || projectKeyFromPreviewPath(filePreview && filePreview.path);
  return {
    project,
    generatedOn: parsed.generated_on || parsed.generated_at || "",
    sourceCount: Array.isArray(parsed.sources) ? parsed.sources.length : sources.length,
    sources: sources.map((source, index) => ({
      id: source.source_id || source.id || `S${index + 1}`,
      path: source.path || source.source_path || "",
      notePath: source.note_path || "",
      type: source.source_type || source.type || "",
      kind: source.kind || "",
      charsUsed: source.chars_used,
      truncated: source.truncated,
      sha256: source.sha256 || "",
    }))
  };
}

export function sourceNoteSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  if (!parsed.source_id && !parsed.source_path && !parsed.source_summary) return null;
  const project = parsed.project || projectKeyFromPreviewPath(filePreview && filePreview.path);
  return {
    project,
    sourceId: parsed.source_id || "",
    sourcePath: parsed.source_path || "",
    sourceType: parsed.source_type || "",
    sourceKind: parsed.source_kind || "",
    summary: parsed.source_summary || "",
    facts: Array.isArray(parsed.immutable_ground_truth) ? parsed.immutable_ground_truth.filter(Boolean).slice(0, 6) : [],
    claimsToTest: Array.isArray(parsed.candidate_claims_to_test) ? parsed.candidate_claims_to_test.filter(Boolean).slice(0, 6) : [],
    gaps: Array.isArray(parsed.epistemic_voids) ? parsed.epistemic_voids.filter(Boolean).slice(0, 6) : [],
    constraints: Array.isArray(parsed.numerical_ranges_and_constraints) ? parsed.numerical_ranges_and_constraints.filter(Boolean).slice(0, 5) : [],
    conflicts: Array.isArray(parsed.potentially_conflicting_assertions) ? parsed.potentially_conflicting_assertions.filter(Boolean).slice(0, 5) : []
  };
}

export function evidenceGapSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  const gapRows = Array.isArray(parsed.evidence_gaps)
    ? parsed.evidence_gaps
    : Array.isArray(parsed.active_gaps)
      ? parsed.active_gaps
      : [];
  const gaps = gapRows
    .filter((gap) => gap && typeof gap === "object" && !Array.isArray(gap))
    .slice(0, 8);
  if (!gaps.length && !parsed.weakest_point && !parsed.score) return null;
  return {
    project: parsed.project || "",
    score: parsed.score,
    weakestPoint: parsed.weakest_point || "",
    generatedOn: parsed.generated_on || parsed.generated_at || "",
    gaps,
    firstGap: gaps[0] || null
  };
}

export function evidenceGapResolutionSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  const resolutions = Array.isArray(parsed.resolutions)
    ? parsed.resolutions.filter((row) => row && typeof row === "object").slice(0, 10)
    : [];
  if (!resolutions.length && parsed.schema !== "ztare-evidence-gap-resolutions-v1") return null;
  const project = parsed.project || projectKeyFromPreviewPath(filePreview && filePreview.path);
  return {
    project,
    updatedAt: parsed.updated_at || "",
    resolutionCount: parsed.resolution_count ?? resolutions.length,
    llmCalls: parsed.llm_calls,
    resolutions: resolutions.map((row, index) => ({
      id: row.resolution_id || `resolution ${index + 1}`,
      target: row.target || row.gap_id || "Evidence gap",
      status: row.status || "",
      reason: row.reason || "",
      resolvedAt: row.resolved_at || "",
      gapSourcePath: row.gap_source_path || "",
      evidenceRefs: Array.isArray(row.evidence_refs) ? row.evidence_refs.filter(Boolean).slice(0, 8) : []
    }))
  };
}

export function runResultSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  if (parsed.score === undefined && !parsed.weakest_point && !parsed.debate_summary && !parsed.score_contract) return null;
  const scoreContract = parsed.score_contract && typeof parsed.score_contract === "object" ? parsed.score_contract : {};
  const probabilityDag = parsed.probability_dag && typeof parsed.probability_dag === "object" ? parsed.probability_dag : {};
  const usage = parsed.usage_telemetry && typeof parsed.usage_telemetry === "object" ? parsed.usage_telemetry : {};
  const project = parsed.project || scoreContract.rubric_name || projectKeyFromPreviewPath(filePreview && filePreview.path);
  const gaps = Array.isArray(parsed.evidence_gaps)
    ? parsed.evidence_gaps.filter((gap) => gap && typeof gap === "object").slice(0, 6)
    : [];
  const constraints = Array.isArray(parsed.derived_constraints)
    ? parsed.derived_constraints.filter((row) => row && typeof row === "object").slice(0, 6)
    : [];
  const axioms = Array.isArray(parsed.verified_axioms)
    ? parsed.verified_axioms.filter(Boolean).slice(0, 6)
    : [];
  const probabilityNodes = Array.isArray(probabilityDag.nodes)
    ? probabilityDag.nodes.filter((row) => row && typeof row === "object").slice(0, 6)
    : [];
  return {
    project,
    score: parsed.score,
    weakestPoint: parsed.weakest_point || "",
    debateSummary: parsed.debate_summary || "",
    alignment: parsed.adversarial_alignment || "",
    artifactRole: parsed.artifact_role || "",
    judgeModel: scoreContract.judge_model || scoreContract.requested_judge_model || usage.model_name || "",
    evidenceGapCount: scoreContract.evidence_gap_count ?? gaps.length,
    derivedConstraintCount: scoreContract.derived_constraint_proposal_count ?? constraints.length,
    testSuiteStatus: scoreContract.test_suite_status || "",
    evidencePath: scoreContract.evidence_path || "",
    estimatedCostUsd: usage.estimated_cost_usd,
    gaps,
    constraints,
    axioms,
    probabilityOutcome: probabilityDag.outcome && typeof probabilityDag.outcome === "object" ? probabilityDag.outcome : {},
    probabilityNodes
  };
}

export function probabilityModelSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  const outcome = parsed.outcome && typeof parsed.outcome === "object" ? parsed.outcome : {};
  const nodes = Array.isArray(parsed.nodes)
    ? parsed.nodes.filter((node) => node && typeof node === "object").slice(0, 12)
    : [];
  const edges = Array.isArray(parsed.edges)
    ? parsed.edges.filter((edge) => edge && typeof edge === "object").slice(0, 20)
    : [];
  if (!outcome.label && !nodes.length && !edges.length) return null;
  return {
    outcome,
    nodes,
    edges,
    topNodes: [...nodes].sort((left, right) => Number(right.probability || 0) - Number(left.probability || 0)).slice(0, 6),
    strongEdges: [...edges].sort((left, right) => Number(right.weight || 0) - Number(left.weight || 0)).slice(0, 6)
  };
}

export function evidenceFetchSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed) return null;
  const records = Array.isArray(parsed) ? parsed.filter((row) => row && typeof row === "object") : [parsed];
  const record = records.find((row) =>
    row &&
    typeof row === "object" &&
    (row.schema === "ztare-forensic-workbench-evidence-fetch-receipt-v1" ||
      row.fetches ||
      row.manifest_path ||
      row.total_attempted !== undefined)
  );
  if (!record) return null;
  const fetches = Array.isArray(record.fetches) ? record.fetches : [];
  const failureCounts = record.failure_counts && typeof record.failure_counts === "object" ? record.failure_counts : {};
  const failureText = Object.entries(failureCounts)
    .map(([key, value]) => `${displayText(key)}=${value}`)
    .join(", ");
  const receiptHints = Array.isArray(record.recovery_hints) ? record.recovery_hints.filter(Boolean) : [];
  const fetchHint = fetches.map((row) => row && row.recovery_hint).find(Boolean);
  return {
    backend: record.search_backend || record.search_backend_selector || "",
    attempted: record.total_attempted,
    accepted: record.total_accepted,
    failureText,
    hint: receiptHints[0] || fetchHint || "",
    firstTarget: fetches.map((row) => row && (row.gap_target || row.target)).find(Boolean) || ""
  };
}

export function evidencePacketSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  if (!parsed.compiler_summary || !Array.isArray(parsed.provenance)) return null;
  return {
    project: parsed.project || "",
    summary: parsed.compiler_summary || "",
    facts: Array.isArray(parsed.immutable_ground_truth) ? parsed.immutable_ground_truth.filter(Boolean).slice(0, 6) : [],
    claimsToTest: Array.isArray(parsed.candidate_claims_to_test) ? parsed.candidate_claims_to_test.filter(Boolean).slice(0, 6) : [],
    gaps: Array.isArray(parsed.epistemic_voids) ? parsed.epistemic_voids.filter(Boolean).slice(0, 6) : [],
    contradictions: Array.isArray(parsed.identified_contradictions) ? parsed.identified_contradictions.filter(Boolean).slice(0, 4) : [],
    ranges: Array.isArray(parsed.numerical_ranges_and_constraints) ? parsed.numerical_ranges_and_constraints.filter(Boolean).slice(0, 6) : [],
    provenance: Array.isArray(parsed.provenance) ? parsed.provenance.filter(Boolean).slice(0, 10) : []
  };
}

export function evidenceProvenanceSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  if (!parsed.output_path && !parsed.packet_output_path && !parsed.evidence_replay_manifest_path) return null;
  return {
    status: parsed.status || parsed.mode || "",
    sourceCount: parsed.source_count,
    gapCount: parsed.evidence_gap_count,
    outputPath: parsed.output_path || "",
    packetPath: parsed.packet_output_path || "",
    replayPath: parsed.evidence_replay_manifest_path || "",
    gapBriefPath: parsed.evidence_gap_brief_path || "",
    gapActionPath: parsed.evidence_gap_action_path || "",
    warnings: Array.isArray(parsed.warnings) ? parsed.warnings.filter(Boolean).slice(0, 6) : [],
    sources: Array.isArray(parsed.sources) ? parsed.sources.filter(Boolean).slice(0, 8) : []
  };
}

export function reportSupportSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  if (!parsed.report_action_authority && !parsed.review_readiness && !parsed.source_claim_support) return null;
  const authority = parsed.report_action_authority && typeof parsed.report_action_authority === "object" ? parsed.report_action_authority : {};
  const readiness = parsed.review_readiness && typeof parsed.review_readiness === "object" ? parsed.review_readiness : {};
  const claimSupport = parsed.source_claim_support && typeof parsed.source_claim_support === "object" ? parsed.source_claim_support : {};
  return {
    project: parsed.project || "",
    status: parsed.status || "",
    ok: parsed.ok,
    reasons: Array.isArray(parsed.status_reasons) ? parsed.status_reasons.filter(Boolean).slice(0, 6) : [],
    hardestConclusion: parsed.hardest_conclusion && typeof parsed.hardest_conclusion === "object" ? parsed.hardest_conclusion : {},
    allowed: Array.isArray(authority.allowed_now) ? authority.allowed_now.filter(Boolean).slice(0, 8) : [],
    conditional: Array.isArray(authority.conditional) ? authority.conditional.filter(Boolean).slice(0, 6) : [],
    forbidden: Array.isArray(authority.forbidden_upgrades) ? authority.forbidden_upgrades.filter(Boolean).slice(0, 6) : [],
    nextActions: Array.isArray(parsed.next_actions) ? parsed.next_actions.filter(Boolean).slice(0, 8) : [],
    runtimeCaveats: Array.isArray(parsed.runtime_caveats) ? parsed.runtime_caveats.filter(Boolean).slice(0, 6) : [],
    runtimeRisks: Array.isArray(parsed.runtime_risks) ? parsed.runtime_risks.filter(Boolean).slice(0, 6) : [],
    sourcePaths: Array.isArray(parsed.source_artifact_paths) ? parsed.source_artifact_paths.filter(Boolean).slice(0, 8) : [],
    claimCount: claimSupport.claim_count,
    problemRows: Array.isArray(claimSupport.problem_rows) ? claimSupport.problem_rows.filter(Boolean).slice(0, 6) : [],
    sampleRows: Array.isArray(claimSupport.sample_rows) ? claimSupport.sample_rows.filter(Boolean).slice(0, 6) : [],
    traceStatus: readiness.trace_status || "",
    traceReadiness: readiness.trace_readiness || "",
    launchPreflightOk: readiness.launch_preflight_ok
  };
}

export function sourceWarningIssueLabel(row = {}) {
  const overrides = {
    weak_gp233_linkage: "Evidence links need repair",
    stale_trajectory_output: "Run-history archive is stale",
    unconsumed_surface: "Work log is missing",
    source_compilation_defect: "Source compilation needs repair"
  };
  return row.display_issue_type || overrides[row.issue_type] || guidanceLabel(row.issue_type || row.recommended_action || "File/evidence warning");
}

export function sourceWarningIssueAction(row = {}) {
  const issueType = row.issue_type || row.recommended_action || "";
  if (issueType === "weak_gp233_linkage") return "Bind this warning to a concrete project file, run, or evidence file before using it to justify a stronger next move.";
  if (issueType === "stale_trajectory_output") return "Refresh the run-history archive from saved history, or keep the warning diagnostic.";
  if (issueType === "unconsumed_surface") return "Record whether the surfaced work was used, rejected, or deferred before treating it as project state.";
  return row.display_recommended_action || guidanceLabel(row.recommended_action || "Inspect the backing file");
}

export function sourceWarningSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  const path = String((filePreview && filePreview.path) || "");
  const issues = Array.isArray(parsed.issues)
    ? parsed.issues.filter((row) => row && typeof row === "object").slice(0, 12)
    : [];
  const sourcePaths = parsed.source_paths && typeof parsed.source_paths === "object" && !Array.isArray(parsed.source_paths)
    ? parsed.source_paths
    : {};
  if (!issues.length && !path.includes("source_health") && !parsed.counts) return null;
  const counts = parsed.counts && typeof parsed.counts === "object" ? parsed.counts : {};
  return {
    generatedAt: parsed.generated_at || "",
    issueCount: counts.issues ?? issues.length,
    warningCount: counts.warning,
    blockingCount: counts.blocking,
    sourcePaths,
    issues: issues.map((row, index) => ({
      id: row.issue_id || `source-warning-${index + 1}`,
      label: sourceWarningIssueLabel(row),
      severity: row.display_severity || guidanceLabel(row.severity || "warning"),
      scope: row.display_scope || guidanceLabel(row.scope || ""),
      detail: row.display_blocking_rule || guidanceText(row.blocking_rule || row.recommended_action || ""),
      denominator: row.display_denominator || guidanceText(row.denominator || ""),
      observed: row.observed_count,
      expected: row.expected_count,
      action: sourceWarningIssueAction(row),
      evidenceRefs: Array.isArray(row.evidence_refs) ? row.evidence_refs.filter(Boolean).slice(0, 6) : []
    }))
  };
}

export function actionRecommendationSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  const path = String((filePreview && filePreview.path) || "");
  const recommendations = Array.isArray(parsed.recommendations)
    ? parsed.recommendations.filter((row) => row && typeof row === "object").slice(0, 12)
    : [];
  if (!recommendations.length && !path.includes("shadow_recommendations")) return null;
  const counts = parsed.counts && typeof parsed.counts === "object" ? parsed.counts : {};
  return {
    generatedAt: parsed.generated_at || "",
    counts,
    recommendations: recommendations.map((row, index) => ({
      id: row.recommendation_id || `recommendation-${index + 1}`,
      label: row.display_recommended_action || guidanceLabel(row.recommended_action || "Suggested next move"),
      domain: row.display_domain || guidanceLabel(row.domain || ""),
      confidence: row.display_confidence || guidanceLabel(row.confidence || ""),
      authority: row.display_execution_authority || guidanceLabel(row.execution_authority || ""),
      rationale: row.display_rationale || guidanceText(row.rationale || ""),
      evidenceRefs: Array.isArray(row.evidence_refs) ? row.evidence_refs.filter(Boolean).slice(0, 4) : []
    }))
  };
}

export function derivedConstraintSummaryFromPreview(filePreview) {
  const parsed = parseJsonLikeText(filePreview && filePreview.text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
  if (!Array.isArray(parsed.confirmed_constraints) && !Array.isArray(parsed.provisional_constraints)) return null;
  return {
    project: parsed.project || "",
    updatedOn: parsed.updated_on || "",
    threshold: parsed.confirmation_threshold_runs,
    confirmedCount: parsed.confirmed_constraint_count,
    provisionalCount: parsed.provisional_constraint_count,
    confirmed: Array.isArray(parsed.confirmed_constraints) ? parsed.confirmed_constraints.filter(Boolean).slice(0, 6) : [],
    provisional: Array.isArray(parsed.provisional_constraints) ? parsed.provisional_constraints.filter(Boolean).slice(0, 8) : []
  };
}

export function jsonLineRecordsFromPreview(filePreview, limit = 10) {
  const text = String((filePreview && filePreview.text) || "").trim();
  if (!text) return [];
  const records = [];
  for (const line of text.split(/\r?\n/)) {
    if (!line.trim()) continue;
    try {
      const parsed = JSON.parse(line);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) records.push(parsed);
    } catch {
      return [];
    }
    if (records.length >= limit) break;
  }
  return records;
}

export function receiptRecordTitle(record, index) {
  return record.item_label || record.row || record.label || record.action || record.decision || record.schema || `Saved change ${index + 1}`;
}

export function receiptRecordStatus(record) {
  if (record.accepted === true) return "accepted";
  if (record.accepted === false) return "not accepted";
  return record.decision || record.status || record.action || "";
}

export function receiptRecordArtifactPaths(record) {
  return uniqueLines([
    record.review_file_path,
    record.action_file_path,
    record.source_path,
    record.source_receipt_path,
    record.project_file_path,
    record.case_file_path,
    record.report_path,
    record.contract_path,
    record.manifest_path,
    record.evidence_manifest_path,
    record.receipt_path,
    ...(Array.isArray(record.write_paths) ? record.write_paths : []),
    ...(Array.isArray(record.receipt_paths) ? record.receipt_paths : [])
  ].filter((path) => typeof path === "string" && path.trim()));
}

export function receiptLedgerSummaryFromPreview(filePreview) {
  const path = String((filePreview && filePreview.path) || "");
  const displayKind = String((filePreview && filePreview.display_kind) || "");
  if (!path.includes("forensic_workbench") && !displayKind.toLowerCase().includes("saved")) return null;
  let records = [];
  if ((filePreview && filePreview.format) === "JSON lines" || path.endsWith(".jsonl")) {
    records = jsonLineRecordsFromPreview(filePreview, 160);
  } else {
    const parsed = parseJsonLikeText(filePreview && filePreview.text);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) records = [parsed];
  }
  const receiptRecords = records.filter((record) =>
    record &&
    typeof record === "object" &&
    (
      String(record.schema || "").includes("forensic-workbench") ||
      record.applied_at ||
      record.write_boundary ||
      record.review_file_path ||
      record.action_file_path ||
      record.project_file_path ||
      record.source_receipt_path
    )
  );
  if (!receiptRecords.length) return null;
  const latest = receiptRecords[receiptRecords.length - 1] || {};
  const latestArtifacts = receiptRecordArtifactPaths(latest).slice(0, 8);
  return {
    project: latest.project || receiptRecords.map((record) => record.project).find(Boolean) || projectKeyFromPreviewPath(path),
    receiptCount: receiptRecords.length,
    latest,
    latestTitle: receiptRecordTitle(latest, receiptRecords.length - 1),
    latestStatus: receiptRecordStatus(latest),
    latestArtifacts,
    records: receiptRecords.slice(-12).reverse().map((record, index) => ({
      key: `${record.applied_at || record.schema || "receipt"}:${index}`,
      title: receiptRecordTitle(record, index),
      status: receiptRecordStatus(record),
      appliedAt: record.applied_at || record.created_at || record.updated_at || "",
      note: record.note || record.summary || record.reason || record.command || "",
      schema: record.schema || "",
      contentChanged: record.project_file_content_changed ?? record.case_file_content_changed ?? record.content_changed,
      artifacts: receiptRecordArtifactPaths(record).slice(0, 5)
    }))
  };
}

export function runSetupDecisionSummaryFromPreview(filePreview) {
  const path = String((filePreview && filePreview.path) || "");
  const displayKind = String((filePreview && filePreview.display_kind) || "");
  if (!path.includes("cold_shot_runs") && displayKind !== "Run setup choices") return null;
  const records = jsonLineRecordsFromPreview(filePreview, 80).filter((record) => Array.isArray(record.families));
  if (!records.length) return null;
  const latest = records[records.length - 1] || {};
  const latestFamilies = latest.families.filter((row) => row && typeof row === "object");
  return {
    project: latest.project || records.map((record) => record.project).find(Boolean) || projectKeyFromPreviewPath(path),
    decisionCount: records.length,
    latestEvent: latest.event || "",
    latestTimestamp: latest.timestamp || latest.timestamp_utc || "",
    mode: latest.mode || "",
    lifecycle: latest.lifecycle || "",
    routerReason: latest.router_reason || "",
    selectedFamilies: latestFamilies.filter((row) => row.selected).map((row) => row.family_id || row.artifact_name || "selected").slice(0, 8),
    eligibleCount: latestFamilies.filter((row) => row.eligible).length,
    skippedCount: latestFamilies.filter((row) => !row.selected).length,
    families: latestFamilies.slice(0, 8).map((row, index) => ({
      id: row.family_id || row.artifact_name || `family ${index + 1}`,
      status: row.selected ? "selected" : row.eligible ? "eligible" : "not selected",
      reason: row.reason || "",
      lifecycle: row.lifecycle || "",
      mode: row.mode || ""
    }))
  };
}

export function reportSynthesisAttemptSummaryFromPreview(filePreview) {
  const path = String((filePreview && filePreview.path) || "");
  const displayKind = String((filePreview && filePreview.display_kind) || "");
  if (!path.includes("post_run_synthesis_attempts") && displayKind !== "Report synthesis attempts") return null;
  const records = jsonLineRecordsFromPreview(filePreview, 80).filter((record) =>
    record && typeof record === "object" && (record.attempts_count !== undefined || Array.isArray(record.attempts))
  );
  if (!records.length) return null;
  const latest = records[records.length - 1] || {};
  const attempts = Array.isArray(latest.attempts) ? latest.attempts.filter(Boolean) : [];
  return {
    project: latest.project || projectKeyFromPreviewPath(path),
    recordCount: records.length,
    latestTimestamp: latest.timestamp_utc || latest.timestamp || "",
    note: latest.note || "",
    attemptsCount: latest.attempts_count ?? attempts.length,
    attempts: attempts.slice(0, 6)
  };
}

export function runHistorySummaryFromPreview(filePreview) {
  const records = jsonLineRecordsFromPreview(filePreview, 80);
  if (!records.length) return null;
  const runRecords = records.filter((record) =>
    record &&
    typeof record === "object" &&
    (
      record.run_id !== undefined ||
      record.record_type === "run_start" ||
      record.record_type === "run_end" ||
      record.record_type === "iteration"
    )
  );
  if (!runRecords.length) return null;
  const scored = runRecords.filter((record) =>
    record.score !== undefined ||
    record.final_score !== undefined ||
    record.raw_judge_score !== undefined
  );
  const latestScored = [...scored].reverse().find((record) =>
    record.score !== undefined ||
    record.final_score !== undefined ||
    record.raw_judge_score !== undefined
  ) || {};
  const scores = scored
    .map((record) => Number(record.score ?? record.final_score ?? record.raw_judge_score))
    .filter((value) => Number.isFinite(value));
  const bestScore = scores.length ? Math.max(...scores) : null;
  const firstScore = scores.length ? scores[0] : null;
  const latestScore = Number(latestScored.score ?? latestScored.final_score ?? latestScored.raw_judge_score);
  const project = runRecords.map((record) => record.project).find(Boolean) || projectKeyFromPreviewPath(filePreview && filePreview.path);
  return {
    project,
    totalRecords: runRecords.length,
    scoredCount: scored.length,
    preflightCount: runRecords.filter((record) => record.preflight_only).length,
    bestScore,
    latestScore: Number.isFinite(latestScore) ? latestScore : null,
    scoreDelta: Number.isFinite(latestScore) && firstScore !== null ? latestScore - firstScore : null,
    latestWeakestPoint: latestScored.weakest_point || "",
    records: runRecords.slice(-12).reverse()
  };
}

