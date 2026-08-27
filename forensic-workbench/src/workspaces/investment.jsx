import React, { useEffect, useState } from "react";
import {
  Activity, AlertTriangle, ArrowRight, CheckCircle2, CircleDashed, Clock3,
  Database, FileText, GitBranch, Layers3, RefreshCw, Search, ShieldCheck, Target, TrendingUp,
} from "lucide-react";

const VIEWS = new Set([
  "Overview", "Sources & signals", "Opportunities", "Strategy frontier", "Plays", "Portfolio",
  "Shadow book", "World models",
]);

function pct(value, digits = 1) {
  if (value == null || value === "") return "—";
  const number = Number(value);
  return Number.isFinite(number) ? `${(number * 100).toFixed(digits)}%` : "—";
}

function number(value, digits = 2) {
  if (value == null || value === "") return "—";
  const n = Number(value);
  return Number.isFinite(n) ? n.toLocaleString(undefined, { maximumFractionDigits: digits }) : "—";
}

function money(value, currency = "USD") {
  if (value == null || value === "") return "—";
  const n = Number(value);
  return Number.isFinite(n) ? n.toLocaleString(undefined, {
    style: "currency", currency: currency || "USD", maximumFractionDigits: 2,
  }) : "—";
}

function rational(value) {
  if (typeof value === "number") return value;
  const [numerator, denominator = "1"] = String(value || "").split("/");
  const result = Number(numerator) / Number(denominator);
  return Number.isFinite(result) ? result : null;
}

function portfolioRiskEstimate(policy, riskModel) {
  const covariance = riskModel?.return_covariance || {};
  const ids = covariance.entity_ids || [];
  const matrix = covariance.covariance_matrix || [];
  if (!ids.length || matrix.length !== ids.length) return null;
  const weights = ids.map((id) => Number(policy?.weights?.[id] || 0));
  const variance = weights.reduce((sum, left, i) => sum + weights.reduce(
    (rowSum, right, j) => rowSum + left * right * Number(matrix[i]?.[j] || 0), 0,
  ), 0);
  return variance >= 0 ? Math.sqrt(variance) : null;
}

function formatPriorityWitness(witness) {
  if (!witness) return "";
  return Object.entries(witness)
    .map(([name, value]) => [name.replaceAll("_", " "), rational(value)])
    .filter(([, value]) => value != null && value > 0.0005)
    .sort((left, right) => right[1] - left[1])
    .map(([name, value]) => `${name} ${pct(value, 0)}`)
    .join(" · ");
}

function priorityWitness(certificate, alternativeId) {
  const row = (certificate?.regions || []).find((region) => region.alternative_id === alternativeId);
  return formatPriorityWitness(row?.strict_preference_witness || row?.preference_witness);
}

function opportunityReason(row) {
  const coordinates = row.economic_coordinates || {};
  const influence = row.law_policy_influence || {};
  if (row.entity_kind === "public_fund") {
    const parts = [];
    if (coordinates.factor_implied_return != null) parts.push(`${pct(coordinates.factor_implied_return, 1)} factor-assumption-implied return`);
    if (coordinates.residual_alpha != null) parts.push(`${pct(coordinates.residual_alpha, 2)} historical residual alpha (zero decision credit)`);
    if (coordinates.maximum_drawdown != null) parts.push(`${pct(coordinates.maximum_drawdown, 1)} maximum drawdown`);
    if (Number(influence.active_law_count || 0)) parts.push(`${pct(influence.adjustment, 1)} learned research-priority adjustment`);
    return parts.join(" · ") || "Fund exposure requires deeper holdings and implementation review.";
  }
  const parts = [];
  if (coordinates.implied_growth != null) {
    const growth = Number(coordinates.implied_growth);
    parts.push(growth < 0 ? `price discounts ${pct(Math.abs(growth), 1)} annual shrinkage` : `price discounts ${pct(growth, 1)} annual growth`);
  }
  if (coordinates.price_implied_excess_return != null) parts.push(`${pct(coordinates.price_implied_excess_return, 1)} valuation-implied excess over hurdle`);
  if (coordinates.quality != null) parts.push(`${number(Number(coordinates.quality) * 100, 0)}/100 measured quality`);
  if (Number(influence.active_law_count || 0)) parts.push(`${pct(influence.adjustment, 1)} learned research-priority adjustment`);
  return parts.join(" · ") || "Numeric screen passed; causal underwriting remains open.";
}

function potentialRankView(row) {
  const rank = row?.learned_potential_rank || row?.potential_rank || {};
  const fund = row?.entity_kind === "public_fund" && rank.peer_rank;
  const value = fund ? rank.peer_rank : rank.rank || null;
  const count = fund ? rank.peer_ranked_count : rank.ranked_count;
  const scope = String(fund ? rank.comparison_scope : rank.scope || row?.entity_kind || "candidate")
    .replace("implementation_sleeve:", "").replaceAll("public_", "").replaceAll("_", " ");
  return {
    value,
    detail: value ? `${count ? `of ${count} · ` : ""}${scope}${fund ? " sleeve" : " lane"}` : "unranked evidence repair",
  };
}

function researchRankValue(row) {
  const rank = row?.learned_research_rank ?? row?.research_rank;
  return Number(typeof rank === "object" ? rank?.rank : rank) || null;
}

function researchRankDetail(row) {
  const learned = Number(row?.learned_research_rank) || null;
  const base = Number(typeof row?.research_rank === "object" ? row.research_rank?.rank : row?.research_rank) || null;
  const laws = Number((row?.causal_law_target_influence || row?.law_policy_influence || {}).active_law_count || 0);
  return learned && base && learned !== base
    ? `moved from R#${base} by ${laws || "settled"} learned law${laws === 1 ? "" : "s"}`
    : "qualified survivor queue";
}

function researchJobKindLabel(kind) {
  return ({
    jaggedthoughts_subscription_research: "initial public-web dossier",
    jaggedthoughts_subscription_activation_research: "public-web activation repair",
    jaggedthoughts_activation_research: "public-web activation repair",
    jaggedthoughts_subscription_reassessment: "public-web source reassessment",
    jaggedthoughts_strategy_frontier_research: "dossier-only strategy synthesis",
    jaggedthoughts_strategy_outcome_research: "matured strategy-outcome check",
    jaggedthoughts_strategy_cohort_research: "strategy transfer check",
    jaggedthoughts_strategy_program_adoption_research: "integrated strategy-program check",
    jaggedthoughts_strategy_event_refinement_research: "primary-source event-timing check",
    jaggedthoughts_strategy_measurement_research: "strategy measurement-contract search",
    jaggedthoughts_fund_implementation_gap_research: "fund implementation evidence repair",
    jaggedthoughts_autoresearch_project: "sealed model experiment",
  })[kind] || String(kind || "research").replaceAll("jaggedthoughts_", "").replaceAll("_", " ");
}

function dispatchBasisLabel(basis) {
  return ({
    frozen_chain_successor: "closes an already-open evidence chain before widening research",
    activation_service_cadence: "activation evidence is due service",
    fund_service_cadence: "fund evidence is due service",
    candidate_service_cadence: "candidate underwriting is due service",
    queue_priority: "highest executable queue priority",
  })[basis] || null;
}

function candidateRankReason(row) {
  const rank = row.learned_potential_rank || row.potential_rank || {};
  const view = potentialRankView(row);
  const leaders = rank.leading_doctrines || [];
  const components = Object.entries(row.score_families || row.score_components || {})
    .filter(([, value]) => Number.isFinite(Number(value)))
    .sort((left, right) => Number(right[1]) - Number(left[1]))
    .slice(0, 3)
    .map(([name, value]) => `${name.replace(/^potential_/, "").replaceAll("_", " ")} ${number(Number(value) * 100, 0)}/100`);
  const parts = [view.value ? `Potential #${view.value} ${view.detail}.` : "Potential rank is unavailable."];
  if (leaders.length) parts.push(`Leading lens: ${leaders.map((value) => value.replaceAll("_", " ")).join(" + ")}.`);
  if (components.length) parts.push(`Strongest normalized screen inputs: ${components.join(" · ")}.`);
  if (Number(rank.rank_disagreement || 0)) parts.push(`Doctrine spread: ${rank.rank_disagreement} rank places.`);
  return parts.join(" ");
}

function candidateResearchStatus(row, request, activeJob, service, handoff, candidateLane) {
  const payload = activeJob?.payload || {};
  const activeEntity = payload.entity_id || (candidateLane?.currently_serving ? candidateLane.active_entity_id : null);
  if (activeEntity === row.entity_id || (payload.candidate_sha256 && payload.candidate_sha256 === row.candidate_sha256)) {
    return { label: "running", ok: true, detail: `${researchJobKindLabel(activeJob?.kind || candidateLane?.active_kind)} using bounded public sources` };
  }
  if (row.screen_status !== "qualified") {
    return { label: "not queued", ok: false, detail: String(row.next_activation || row.screen_status || "screen blocked").replaceAll("_", " ") };
  }
  if (handoff?.status !== "complete") {
    return { label: "blocked", ok: false, detail: "current rank-to-research handoff is incomplete" };
  }
  if (!request) return { label: "blocked", ok: false, detail: "no request is bound to this candidate epoch" };
  if (request.lifecycle_stage === "researched") return { label: "dossier accepted", ok: true, detail: "kernel-checked public research is available" };
  if (request.lifecycle_stage === "covered_by_prior_dossier") return { label: "evidence reused", ok: true, detail: "unchanged monitored evidence covers this candidate epoch" };
  if (service?.status === "stale" || service?.status === "stopped" || service?.status === "disabled" || service?.ok === false) {
    return { label: "blocked", ok: false, detail: `research consumer ${String(service.status || "unavailable").replaceAll("_", " ")}` };
  }
  const next = candidateLane?.next_entity_id === row.entity_id ? " · next candidate claim" : "";
  return { label: "queued", ok: false, detail: `${String(request.lifecycle_stage || "evidence ready").replaceAll("_", " ")}${next}` };
}

function SourceCards({ rows }) {
  return <div className="capital-source-grid">{rows.map((row) =>
    <article key={row.source_id} className={`capital-source ${row.status}`}>
      <div><Database size={17} /><strong>{row.source_id}</strong></div>
      <span>{String(row.adapter || "source").replaceAll("_", " ")}</span><Status ok={row.status === "consumed"}>{String(row.status).replaceAll("_", " ")}</Status>
      {row.observation_count !== undefined ? <small>{number(row.observation_count, 0)} observations</small> : null}
      {row.error ? <p>{row.error}</p> : null}
    </article>)}</div>;
}

function Status({ ok, children }) {
  return <span className={`capital-status ${ok ? "ok" : "attention"}`}>
    {ok ? <CheckCircle2 size={14} /> : <CircleDashed size={14} />}{children}
  </span>;
}

function Empty({ title, body }) {
  return <div className="capital-empty">
    <CircleDashed size={22} />
    <div><strong>{title}</strong><p>{body}</p></div>
  </div>;
}

function Section({ eyebrow, title, description, actions, children }) {
  return <section className="capital-section">
    <header className="capital-section-head">
      <div>{eyebrow ? <span className="eyebrow">{eyebrow}</span> : null}<h2>{title}</h2>{description ? <p>{description}</p> : null}</div>
      {actions ? <div className="capital-section-actions">{actions}</div> : null}
    </header>
    {children}
  </section>;
}

function ActionButton({ action, inputs = {}, busy, onAction, children, primary = false }) {
  return <button type="button" className={`copy-button ${primary ? "primary" : ""}`} disabled={busy}
    onClick={() => onAction && onAction(action, inputs)}>
    {busy ? <RefreshCw size={15} className="capital-spin" /> : null}{children}
  </button>;
}

function Readiness({ readiness = {} }) {
  const rows = [
    ["Public sources", readiness.public_sources_consumed, readiness.public_sources_consumed ? "cached" : "not refreshed"],
    ["Required sources", readiness.required_sources_ok, readiness.required_sources_ok ? "available" : "blocked"],
    ["Operator decisions", Number(readiness.operator_decision_count) > 0, String(readiness.operator_decision_count || 0)],
    ["Research drafts", Number(readiness.operator_draft_count) === 0, String(readiness.operator_draft_count || 0)],
    ["Fund candidates", Number(readiness.fund_candidate_count) > 0, String(readiness.fund_candidate_count || 0)],
    ["Discovery engine", !readiness.discovery_due, readiness.discovery_due ? "due" : `${readiness.discovery_candidate_count || 0} ranked`],
    ["Capital cycle", !readiness.capital_cycle_due, readiness.capital_cycle_due ? "due" : "current"],
    ["Model experiments", Number(readiness.market_flow_experiment_count) > 0, String(readiness.market_flow_experiment_count || 0)],
    ["Paper allocation", readiness.portfolio_available, readiness.portfolio_available ? "weights compiled" : "cash default"],
    ["Frozen forecasts", Number(readiness.closed_book_run_count) > 0, `${readiness.closed_book_settled_count || 0} settled · ${readiness.closed_book_pending_count || 0} open`],
    ["Golden store", readiness.golden_store_ok, readiness.golden_store_ok ? "verified" : "needs repair"],
  ];
  return <div className="capital-readiness-grid">{rows.map(([label, ok, detail]) =>
    <div className="capital-readiness" key={label}><Status ok={Boolean(ok)}>{label}</Status><strong>{detail}</strong></div>)}</div>;
}

function CapitalCycle({ state, busy, onAction, onPreview }) {
  const cycle = state.capital_cycle || {};
  const run = cycle.latest_run || {};
  const book = cycle.latest_book || {};
  const posture = book.paper_posture || {};
  const rows = book.candidates || [];
  const service = cycle.service || {};
  const lawInfluence = book.law_policy_influence || {};
  const enrollmentPolicy = cycle.policy?.paper_watch_auto_enrollment || {};
  const enrollment = run.paper_watch_auto_enrollment || {};
  const paperWatchEntities = new Set((state.paper_watch_decisions || []).map((row) => row.entity?.entity_id).filter(Boolean));
  return <Section eyebrow="Capital operating loop" title="What should the engine investigate next?"
    description="The server turns each discovery epoch into a research queue, opens due forecast windows, and settles matured outcomes. Rank controls research attention; it is not an expected-return estimate. Only an active operator decision can receive paper weight."
    actions={<ActionButton action="capital-cycle" inputs={{ force: true }} busy={busy} onAction={onAction} primary>Run capital cycle</ActionButton>}>
    <div className="capital-discovery-status">
      <div><span>Paper posture</span><strong>{posture.state || "awaiting first cycle"}</strong><small>{posture.cash_weight == null ? "—" : `${pct(posture.cash_weight)} cash`}</small></div>
      <div><span>Underwriting ready</span><strong>{number(book.qualified_count, 0)}</strong><small>typed screen passed</small></div>
      <div><span>Research queue</span><strong>{number(book.research_count, 0)}</strong><small>monitor or valuation work</small></div>
      <div><span>Input repair</span><strong>{number(book.repair_count, 0)}</strong><small>stale or blocked</small></div>
      <div><span>Forecast windows</span><strong>{number((cycle.due_forecast_windows || []).length, 0)}</strong><small>{number(cycle.matured_run_ids?.length, 0)} outcomes due</small></div>
      <div><span>Learned law influence</span><strong>{number(lawInfluence.active_law_count, 0)}</strong><small>{number((lawInfluence.suppressed_laws || []).length, 0)} withheld by evidence gates</small></div>
      <div><span>Paper-watch policy</span><strong>{enrollmentPolicy.enabled ? "standing" : "manual"}</strong><small>{number(enrollment.new_activation_count, 0)} new · {number(enrollment.eligible_count, 0)} eligible last cycle</small></div>
      <div><span>Autonomous owner</span><strong>{service.status || "awaiting server"}</strong><small>{service.last_action || "event-driven checks"}</small></div>
    </div>
    {run.cycle_id ? <div className="capital-next-action"><TrendingUp size={22} /><div><span>Current capital action</span><strong>{run.next_action || book.next_action}</strong></div></div> : null}
    {rows.length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Research order</th><th>Security</th><th>Research state</th><th>Why it surfaced</th><th>Operator position</th></tr></thead><tbody>
      {rows.slice(0, 10).map((row) => { const researchRank = researchRankValue(row); const rank = potentialRankView(row); const watched = paperWatchEntities.has(row.entity_id); return <tr key={row.candidate_id}><td><strong>{researchRank ? `R#${researchRank}` : rank.value ? `#${rank.value}` : "unranked"}</strong><small>{researchRank ? researchRankDetail(row) : rank.detail}</small></td><td><strong>{row.entity_id}</strong><small>{row.name}</small></td><td><Status ok={row.screen_status === "qualified"}>{String(row.screen_status || "inspect").replaceAll("_", " ")}</Status><small>{watched ? "A zero-weight paper-watch epoch is active; await its frozen evidence or outcome window." : row.next_action}</small></td><td><small>{opportunityReason(row)}</small></td><td>{row.paper_decision ? <><strong>{row.paper_decision.stage}</strong><small>target {pct(row.paper_decision.target_weight)}</small></> : watched ? "zero-weight watch only" : "none"}</td></tr>; })}
    </tbody></table></div> : <Empty title="No opportunity book yet" body="Run the capital cycle after the first discovery epoch. Cash remains the default until an active paper decision earns declared risk." />}
    <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>When institutional learning changes this queue</strong><p>Only a law that survives prospective transfer and multiplicity gates can add a bounded ±5% research-priority adjustment. A later counterexample removes that adjustment on the next cycle. It cannot change qualification, paper weight, or capital authority.</p></div></div>
    <div className="capital-action-row">
      {run.opportunity_book_path ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(run.opportunity_book_path)}><FileText size={14} />Inspect opportunity book</button> : null}
      <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths?.capital_cycle_policy || "capital_cycle.yaml")}><FileText size={14} />Edit cycle policy</button>
    </div>
  </Section>;
}

function InvestorActionBrief({ state, onPreview }) {
  const brief = state.investor_action_brief || {};
  const summary = brief.decision_summary || {};
  const investable = brief.investable_now || {};
  const paper = investable.paper || [];
  const funded = investable.funded || [];
  const implementations = brief.implementation_candidates || [];
  const planningBook = brief.planning_book || {};
  const planningPositions = planningBook.positions || [];
  const shadowBook = brief.automated_shadow_book || {};
  const shadowPolicies = shadowBook.policies || [];
  const householdShadow = brief.household_shadow_book || {};
  const householdShadowPolicies = householdShadow.policies || [];
  const research = brief.research_now || [];
  const companies = research.filter((row) => row.entity_kind === "public_equity").length;
  const funds = research.filter((row) => row.entity_kind === "public_fund").length;
  const cash = brief.cash_posture?.paper || {};
  const next = brief.next_automatic_transition || {};
  const answerChanging = summary.answer_changing_evidence || [];
  const fundBoundary = summary.fund_identity_boundary || {};
  const fundShortlist = summary.attention?.fund_sleeve_candidates || [];
  const fundShortlistCount = Number(summary.attention?.fund_sleeve_candidate_count || 0);
  const blockers = (row) => (row.blockers || []).map((gate) =>
    `${String(gate.owner_gate || "gate").replaceAll("_", " ")}: ${(gate.codes || []).join(", ")}`
  ).join(" · ");
  return <Section eyebrow="Investor action brief" title="What can I do now?"
    description="A read-only answer from the current evidence, proposal, allocation, and service gates. Research priority orders attention only; it does not claim expected return or recommend a trade."
    actions={state.paths?.investor_action_brief_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.investor_action_brief_latest)}><FileText size={14} />Inspect brief</button> : null}>
    {summary.scan ? <div className="capital-activation-grid">
      <article><header><strong>1 · What was scanned</strong></header><p>{summary.scan.text}</p></article>
      <article><header><strong>2 · What deserves research</strong></header><p>{summary.attention?.text}</p></article>
      <article><header><strong>3 · What is investable</strong></header><p>{summary.decision?.text}</p></article>
      <article><header><strong>4 · What happens next</strong></header><p>{summary.next?.text}</p></article>
      <article><header><strong>5 · What changes the answer</strong></header><p>{answerChanging.length ? answerChanging.map((row) => `${row.evidence} (${(row.applies_to || []).join(", ")})`).join(" ") : "No answer-changing evidence contract is currently open."}</p></article>
    </div> : null}
    {fundBoundary.text ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Fund categories stay separate</strong><p>{fundBoundary.text}</p><small>{(fundBoundary.broad_sleeves || []).map((row) => `${row.sleeve_id}: ${row.entity_id}`).join(" · ")} · {number(fundBoundary.challenger_program_count, 0)} challenger programs · {number(fundBoundary.comparison_eligible_count, 0)} comparable on the common core</small></div></div> : null}
    {fundShortlist.length ? <div className="capital-closure-rule"><Search size={20} /><div><strong>Current within-sleeve fund research</strong><p>{fundShortlist.map((row) => {
      const metrics = row.comparison_metrics || {};
      const why = [
        row.factor_assumption_spread_vs_cash == null ? null : `${pct(row.factor_assumption_spread_vs_cash)} assumption spread vs cash`,
        metrics.expense_ratio == null ? null : `${pct(metrics.expense_ratio)} fee`,
        metrics.annualized_volatility == null ? null : `${pct(metrics.annualized_volatility)} observed volatility`,
      ].filter(Boolean).join(", ");
      const gap = row.portfolio_policy_evidence_complete ? "policy evidence complete" : (row.evidence_gaps || []).join(", ") || "policy evidence incomplete";
      return `${String(row.sleeve_id).replaceAll("_", " ")} #${row.rank_within_sleeve}: ${row.entity_id}${why ? ` (${why}; ${gap})` : ` (${gap})`}`;
    }).join(" · ")}</p><small>{number(fundShortlistCount, 0)} candidates ranked within their own sleeves. Assumption spreads exclude residual alpha and are research inputs, not expected-return claims, fund selections, or allocations.</small></div></div> : null}
    {planningPositions.length ? <div className="capital-closure-rule"><Layers3 size={20} /><div><strong>Current assumption-labeled household scenario</strong><p>{planningPositions.map((row) => `${row.entity_id} ${pct(row.weight, 0)} (${String(row.sleeve_id).replaceAll("_", " ")})`).join(" · ")}</p><small>This is the public-proxy implementation of the displayed planning assumptions. It is not adopted, does not replace the operator mandate, and does not authorize a trade.</small></div></div> : null}
    <div className="capital-discovery-status">
      <div><span>Implementation candidates</span><strong>{number(implementations.length, 0)}</strong><small>{implementations.length ? `${implementations.map((row) => row.entity_id).join(", ")} · unselected` : "none has earned current admission"}</small></div>
      <div><span>Paper investable now</span><strong>{number(paper.length, 0)}</strong><small>{paper.length ? paper.map((row) => row.entity_id).join(", ") : "no candidate clears every paper gate"}</small></div>
      <div><span>Funded investable now</span><strong>{number(funded.length, 0)}</strong><small>{funded.length ? funded.map((row) => row.entity_id).join(", ") : "no capital or brokerage authority"}</small></div>
      <div><span>Research now</span><strong>{number(research.length, 0)} queue · {number(fundShortlistCount, 0)} fund shortlist</strong><small>{companies} companies · {funds} dossier funds · within-sleeve ranks stay separate</small></div>
      <div><span>Cash posture</span><strong>{cash.state || "unavailable"}</strong><small>{cash.cash_weight == null ? "paper cash unavailable" : `${pct(cash.cash_weight)} paper cash`}</small></div>
      <div><span>Automated shadow book</span><strong>{number(shadowPolicies.length, 0)} policies</strong><small>{shadowBook.end_at ? `sealed through ${String(shadowBook.end_at).slice(0, 10)}` : "no prospective policy block open"}</small></div>
      <div><span>Household shadow trial</span><strong>{number(householdShadowPolicies.length, 0)} policies</strong><small>{householdShadow.end_at ? `scores after ${String(householdShadow.end_at).slice(0, 10)}` : "no complete-policy trial open"}</small></div>
      <div><span>Next automatic transition</span><strong>{researchJobKindLabel(next.job_kind || next.transition)}</strong><small>{next.subject_id ? `${next.subject_id} · ` : ""}{next.due_epoch || "running now"}</small></div>
    </div>
    {shadowPolicies.length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Sealed shadow method</th><th>Risk / cash</th><th>Frozen positions</th><th>Learning state</th></tr></thead><tbody>
      {shadowPolicies.map((row) => <tr key={row.policy_id}><td><strong>{String(row.policy_id || "policy").replaceAll("_", " ")}</strong><small>{String(row.method || "declared method").replaceAll("_", " ")}</small></td><td><strong>{pct(row.gross_weight, 0)} risk</strong><small>{pct(row.cash_weight, 0)} cash</small></td><td><small>{(row.positions || []).slice(0, 6).map((position) => `${position.entity_id} ${pct(position.weight, 1)}`).join(" · ") || "cash control"}{(row.positions || []).length > 6 ? ` · +${row.positions.length - 6}` : ""}</small></td><td><Status ok={false}>{String(shadowBook.status || "collecting outcomes").replaceAll("_", " ")}</Status><small>{number(shadowBook.learning?.settled_block_count, 0)} / {number(shadowBook.learning?.minimum_inference_blocks, 0)} settled blocks</small></td></tr>)}
    </tbody></table></div> : null}
    {shadowPolicies.length ? <div className="capital-closure-rule"><Clock3 size={20} /><div><strong>The automated engine is invested only in shadow space</strong><p>These weights were frozen before their future return window. They test whether discovery ranking and risk construction outperform cash and simpler controls after costs. They are neither the household policy nor a trade instruction.</p></div></div> : null}
    {householdShadowPolicies.length ? <details className="capital-overview-details"><summary><span><strong>Inspect the frozen household implementation trial</strong><small>{number(householdShadowPolicies.length, 0)} policies · {number(householdShadow.distinct_decision_count, 0)} distinct position decisions · broad-sleeve control: {String(householdShadow.control_policy_id || "none").replaceAll("_", " ")}</small></span></summary><div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Policy</th><th>Method</th><th>Frozen positions</th></tr></thead><tbody>
      {householdShadowPolicies.map((row) => <tr key={row.policy_id}><td><strong>{String(row.policy_id).replaceAll("_", " ")}</strong></td><td><small>{String(row.method || "declared method").replaceAll("_", " ")}</small></td><td><small>{(row.positions || []).map((position) => `${position.entity_id} ${pct(position.weight, 1)}`).join(" · ")}</small></td></tr>)}
    </tbody></table></div></details> : null}
    {research.length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Rank</th><th>Research now</th><th>Why present</th><th>Owning blockers</th><th>Next transition</th></tr></thead><tbody>
      {research.slice(0, 10).map((row) => <tr key={row.candidate_sha256 || row.candidate_id}><td>#{row.existing_research_rank}</td><td><strong>{row.entity_id}</strong><small>{String(row.entity_kind || "").replaceAll("_", " ")} · priority {number(row.research_priority_score, 3)}</small></td><td>{row.why_present?.research_prompt || row.why_present?.next_action || String(row.why_present?.owner_gate || "current research queue").replaceAll("_", " ")}</td><td><small>{blockers(row) || "no research blocker recorded"}</small></td><td><code>{String(row.next_transition || "awaiting gate").replaceAll("_", " ")}</code></td></tr>)}
    </tbody></table></div> : <Empty title="No candidate requires research now" body="The current action brief contains no ranked research transition." />}
  </Section>;
}

function goalDefaults(surface) {
  const matrix = surface.hurdle_matrix || [];
  const horizons = [...new Set(matrix.map((row) => Number(row.horizon_years)))].sort((a, b) => a - b);
  const contributions = [...new Set(matrix.map((row) => Number(row.annual_contribution_base)))].sort((a, b) => a - b);
  const horizon = horizons[Math.floor((horizons.length - 1) / 2)] || 20;
  const contribution = Number(
    surface.budget_evidence?.contribution_capacity_summary?.default_scenario_contribution
    ?? contributions[Math.floor((contributions.length - 1) / 2)] ?? 0
  );
  return {
    annual_contribution: contribution,
    horizon_years: horizon,
    target_wealth: Number(surface.goal?.target_base || 1),
    liquidity_reserve: Math.round(Number(surface.known_balance_sheet?.known_investable_liquidity_base || 0) * 0.25 / 1000) * 1000,
    max_risky_weight_percent: 80,
    max_one_year_loss_percent: 40,
    minimum_success_probability_percent: 80,
    equity_tax_drag_percent: 1,
    defensive_tax_drag_percent: 0.5,
  };
}

function controlsFromScenario(surface, scenario) {
  const defaults = goalDefaults(surface);
  const inputs = scenario?.inputs;
  if (!inputs) return defaults;
  const haircuts = inputs.annual_return_haircuts || {};
  return {
    ...defaults,
    annual_contribution: Number(inputs.annual_contribution),
    horizon_years: Number(inputs.horizon_years),
    target_wealth: Number(inputs.target_wealth),
    liquidity_reserve: Number(inputs.liquidity_reserve),
    max_risky_weight_percent: Number(inputs.max_risky_weight) * 100,
    max_one_year_loss_percent: Number(inputs.max_one_year_loss) * 100,
    minimum_success_probability_percent: Number(inputs.minimum_success_probability) * 100,
    equity_tax_drag_percent: Number(haircuts.us_equity ?? defaults.equity_tax_drag_percent / 100) * 100,
    defensive_tax_drag_percent: Number(haircuts.usd_bonds ?? defaults.defensive_tax_drag_percent / 100) * 100,
  };
}

function GoalTrajectoryChart({ path, outcome, target, horizon, currency }) {
  const rows = path?.annual_wealth_path || [];
  if (!rows.length || !outcome) return null;
  const width = 760, height = 250, left = 70, right = 24, top = 22, bottom = 34;
  const maximum = Math.max(target, ...rows.flatMap((row) => [Number(row.median_base), Number(row.p10_base)]), 1) * 1.05;
  const x = (year) => left + (Number(year) / Number(horizon)) * (width - left - right);
  const y = (wealth) => top + (1 - Number(wealth) / maximum) * (height - top - bottom);
  const medianPoints = rows.map((row) => `${x(row.year)},${y(row.median_base)}`).join(" ");
  const p10Points = rows.map((row) => `${x(row.year)},${y(row.p10_base)}`).join(" ");
  const targetY = y(target);
  const terminal = rows[rows.length - 1];
  return <div className="capital-goal-chart">
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Selected allocation median and tenth-percentile wealth paths compared with the portfolio target">
      <line className="axis" x1={left} y1={height - bottom} x2={width - right} y2={height - bottom} />
      <line className="target" x1={left} y1={targetY} x2={width - right} y2={targetY} />
      <text x={left + 6} y={Math.max(14, targetY - 7)}>Target {money(target, currency)}</text>
      <polyline className="wealth-p10" points={p10Points} />
      <polyline className="wealth" points={medianPoints} />
      <circle className={Number(terminal.median_base) >= target ? "achieved" : "short"} cx={x(terminal.year)} cy={y(terminal.median_base)} r="5" />
      <text className="axis-label" x={left} y={height - 10}>Today</text>
      <text className="axis-label" textAnchor="end" x={width - right} y={height - 10}>Year {terminal.year}</text>
    </svg>
    <div className="capital-goal-result">
      <Status ok={Number(terminal.median_base) >= target}>{Number(terminal.median_base) >= target ? "Median path reaches target" : "Median path below target"}</Status>
      <strong>{money(terminal.median_base, currency)}</strong>
      <small>10th percentile {money(terminal.p10_base, currency)} · {pct(outcome.goal_probability, 0)} simulated target frequency</small>
      <small>Same source-anchored return, covariance, tax-haircut, and common-random-number basis as the selected allocation.</small>
    </div>
  </div>;
}

function HouseholdGoalSurface({ state }) {
  const surface = state.household_goal_surface;
  if (!surface) return null;
  if (surface.available === false) return <Section eyebrow="Private household policy" title="Goal surface unavailable">
    <div className="capital-boundary"><AlertTriangle size={17} /><div><strong>Private planning input failed validation</strong><p>{surface.error}</p></div></div>
  </Section>;
  return <HouseholdGoalScenario surface={surface} initialBasis={state.household_capital_market_basis}
    initialScenario={state.household_default_allocation?.scenario}
    initialMandateFrontier={state.household_mandate_frontier}
    initialTournament={state.household_policy_tournament}
    initialOperatorPolicy={state.operator_household_paper_policy}
    operatorId={state.owner || "local-operator"} />;
}

function HouseholdDecisionBrief({ state }) {
  const scenario = state.household_default_allocation?.scenario || {};
  const implementation = scenario.paper_implementation || {};
  const control = (implementation.proposals || [])
    .find((row) => row.proposal_id === "broad_sleeve_control");
  const selected = scenario.selected_policy || {};
  const returnClosure = scenario.return_model_decision_closure || {};
  const mandate = state.household_mandate_frontier || {};
  const path = state.household_paper_policy_path || {};
  const paperPosture = state.capital_cycle?.latest_book?.paper_posture || {};
  if (!control && !selected.program_id) return null;

  const scenarioCount = (selected.scenario_outcomes || []).length;
  const returnDecisionCount = returnClosure.decision_class_count ?? (scenarioCount ? 1 : 0);
  const returnDecisionInvariant = returnClosure.decision_invariant_across_return_models
    ?? scenarioCount === 1;
  const decisionStable = mandate.status === "decision_invariant_across_declared_completions";
  const nextQuestion = mandate.highest_voi_unresolved_input || {};
  const mandateBlockers = path.private_inputs?.required_mandate_fields || [];
  const fundGaps = path.public_evidence?.fund_comparison_gap_codes || [];
  const positions = (control?.positions || []).map((row) =>
    `${row.entity_id} ${pct(row.target_weight, 0)}`
  ).join(" · ");
  const weightRanges = (mandate.sleeve_weight_ranges || [])
    .filter((row) => Number(row.maximum_weight) > 0)
    .map((row) => `${String(row.sleeve_id).replaceAll("_", " ")} ${pct(row.minimum_weight, 0)}–${pct(row.maximum_weight, 0)}`)
    .join(" · ");

  return <Section eyebrow="Portfolio decision brief" title="What does the current planning control say?"
    description="This separates the broad-market planning benchmark from the active-alpha paper book and from brokerage authority.">
    <div className="capital-discovery-status">
      <div><span>Broad-market control</span><strong>{positions || "not lowered to proxies"}</strong><small>current displayed assumptions</small></div>
      <div><span>Return-model coverage</span><strong>{number(scenarioCount, 0)} models · {number(returnDecisionCount, 0)} decisions</strong><small>{scenarioCount === 1 ? "source-anchor sensitivity not yet tested" : returnDecisionInvariant ? "same weights across source methods" : "source methodology changes selected weights"}</small></div>
      <div><span>Mandate sensitivity</span><strong>{decisionStable ? "stable" : `${number(mandate.decision_class_count, 0)} exact decisions`}</strong><small>{decisionStable ? `${number(mandate.design_world_count, 0)} declared completions` : "operator choice still matters"}</small></div>
      <div><span>Active-alpha paper book</span><strong>{paperPosture.cash_weight == null ? "separate" : `${pct(paperPosture.cash_weight, 0)} cash`}</strong><small>{paperPosture.reason || "no active candidate currently earns incremental risk"}</small></div>
    </div>
    <div className="capital-closure-rule"><Target size={20} /><div><strong>Current broad-market control · {positions || "awaiting proxy lowering"}</strong><p>This is the exact comparison baseline for the displayed contribution, horizon, risk limits, public covariance, and source-bound return-model set. It remains paper-only and unselected by the operator.</p><small>{scenarioCount === 1 ? "Return robustness is incomplete: the basis contains one return scenario." : `${scenarioCount} source-method return worlds are compared by their worst outcome and close to ${number(returnDecisionCount, 0)} exact weight decisions; no probabilities are assigned.`} {decisionStable ? "The same weights survive every declared mandate completion." : `Declared mandate completions span: ${weightRanges || "multiple exact allocations"}.`}</small></div></div>
    <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Decision layer</th><th>Current output</th><th>What changes it</th></tr></thead><tbody>
      <tr><td><strong>Household sleeve policy</strong><small>operator-owned</small></td><td>Assumption-labeled control only</td><td>{nextQuestion.question || mandateBlockers.slice(0, 4).map((value) => String(value).replaceAll("_", " ")).join(" · ") || "Bind the household mandate"}<small>{mandateBlockers.length ? `${mandateBlockers.length} mandate fields remain unbound` : "review and select a policy"}</small></td></tr>
      <tr><td><strong>Within-sleeve funds</strong><small>autonomous public research</small></td><td>Broad proxies retained</td><td>{fundGaps.slice(0, 4).map((value) => String(value).replaceAll("_", " ")).join(" · ") || "No admitted same-sleeve replacement"}<small>fund evidence can replace only its own sleeve proxy</small></td></tr>
      <tr><td><strong>Capital and brokerage</strong><small>operator-only authority</small></td><td>Disabled</td><td>Explicit operator policy and current-account binding<small>no order routing; research rank never grants weight</small></td></tr>
    </tbody></table></div>
  </Section>;
}

function HouseholdGoalScenario({ surface, initialBasis, initialScenario, initialMandateFrontier, initialTournament, initialOperatorPolicy, operatorId }) {
  const balance = surface.known_balance_sheet || {};
  const goal = surface.goal || {};
  const missing = surface.readiness?.missing || [];
  const unresolvedBalance = missing.filter((value) => /property|currency|mortgage|loan/.test(String(value)));
  const nonUsdCurrencies = Object.keys(surface.fx_to_base || {}).filter((currency) => currency !== surface.base_currency);
  const defaults = controlsFromScenario(surface, initialScenario);
  const [inputs, setInputs] = useState(defaults);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [basis, setBasis] = useState(initialBasis || null);
  const [basisRunning, setBasisRunning] = useState(false);
  const [allocation, setAllocation] = useState(initialScenario || null);
  const [freezing, setFreezing] = useState(false);
  const [freezeResult, setFreezeResult] = useState(initialTournament?.latest_run || null);
  const [operatorPolicy, setOperatorPolicy] = useState(initialOperatorPolicy?.latest_policy || null);
  const [operatorFreezing, setOperatorFreezing] = useState(false);
  const [operatorInputs, setOperatorInputs] = useState({
    age: "", tax_residence: "", account_ids: "", selected_proposal_id: "",
    human_capital_reviewed: false, liability_currency_reviewed: false,
  });
  const budget = allocation?.budget_evidence || surface.budget_evidence || {};
  const capacity = budget.contribution_capacity_summary || {};
  const allocationInputs = (values) => ({
    schema: "jaggedthoughts-household-allocation-scenario-input-v1",
    annual_contribution: Number(values.annual_contribution),
    horizon_years: Number(values.horizon_years),
    target_wealth: Number(values.target_wealth),
    liquidity_reserve: Number(values.liquidity_reserve),
    max_risky_weight: Number(values.max_risky_weight_percent) / 100,
    max_one_year_loss: Number(values.max_one_year_loss_percent) / 100,
    max_effective_equity_exposure: Number(values.max_risky_weight_percent) / 100,
    minimum_success_probability: Number(values.minimum_success_probability_percent) / 100,
    annual_return_haircuts: {
      cash: 0,
      us_equity: Number(values.equity_tax_drag_percent) / 100,
      international_equity: Number(values.equity_tax_drag_percent) / 100,
      usd_bonds: Number(values.defensive_tax_drag_percent) / 100,
      us_tips: Number(values.defensive_tax_drag_percent) / 100,
    },
    weight_step: 0.1,
  });
  const requestAllocation = (values) => fetch("/api/investment/household-allocation-scenario", {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(allocationInputs(values)),
  }).then((response) => response.json().then((payload) => ({ response, payload })))
    .then(({ response, payload }) => {
      if (!response.ok) throw new Error(payload.error || `allocation scenario failed: ${response.status}`);
      setAllocation(payload);
      return payload;
    });
  const runScenario = (values) => {
    setRunning(true);
    setError("");
    return requestAllocation(values)
      .catch((cause) => setError(cause.message || String(cause)))
      .finally(() => setRunning(false));
  };
  const freezeComparison = () => {
    if (!allocation?.scenario_sha256 || !allocation?.inputs) return;
    setFreezing(true);
    setError("");
    fetch("/api/investment/household-policy-freeze", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({
        scenario_inputs: allocation.inputs,
        expected_scenario_sha256: allocation.scenario_sha256,
        horizon_days: 365,
        transaction_cost_bps: 10,
      }),
    }).then((response) => response.json().then((payload) => ({ response, payload })))
      .then(({ response, payload }) => {
        if (!response.ok) throw new Error(payload.error || `paper comparison failed: ${response.status}`);
        setFreezeResult(payload);
      })
      .catch((cause) => setError(cause.message || String(cause)))
      .finally(() => setFreezing(false));
  };
  const freezeOperatorPolicy = () => {
    if (!allocation?.scenario_sha256 || !allocation?.inputs) return;
    setOperatorFreezing(true);
    setError("");
    fetch("/api/investment/household-operator-policy-freeze", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({
        scenario_inputs: allocation.inputs,
        expected_scenario_sha256: allocation.scenario_sha256,
        selected_proposal_id: operatorInputs.selected_proposal_id,
        operator_id: operatorId,
        attestation: "paper_only_reviewed",
        transaction_cost_bps: 10,
        mandate_completion: {
          age: Number(operatorInputs.age),
          tax_residence: operatorInputs.tax_residence.trim(),
          account_ids: operatorInputs.account_ids.split(",").map((value) => value.trim()).filter(Boolean),
          human_capital_exclusion_attestation: operatorInputs.human_capital_reviewed ? "exclude_from_paper_policy_reviewed" : "",
          liability_currency_attestation: operatorInputs.liability_currency_reviewed ? "unhedged_liability_currency_risk_reviewed" : "",
        },
      }),
    }).then((response) => response.json().then((payload) => ({ response, payload })))
      .then(({ response, payload }) => {
        if (!response.ok) throw new Error(payload.error || `operator paper policy failed: ${response.status}`);
        setOperatorPolicy(payload);
      })
      .catch((cause) => setError(cause.message || String(cause)))
      .finally(() => setOperatorFreezing(false));
  };
  useEffect(() => {
    const next = controlsFromScenario(surface, initialScenario);
    setInputs(next);
    if (initialScenario?.goal_surface_sha256 === surface.surface_sha256) {
      setAllocation(initialScenario);
    } else {
      runScenario(next);
    }
  }, [surface.surface_sha256, initialScenario?.scenario_sha256]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const budgetDefault = allocation?.budget_evidence?.contribution_capacity_summary
      ?.default_scenario_contribution;
    const surfaceDefault = surface.budget_evidence?.contribution_capacity_summary
      ?.default_scenario_contribution;
    const fallbackDefault = goalDefaults(surface).annual_contribution;
    if (surfaceDefault == null && budgetDefault != null
      && Number(inputs.annual_contribution) === Number(fallbackDefault)
      && Number(budgetDefault) !== Number(fallbackDefault)) {
      const next = { ...inputs, annual_contribution: Number(budgetDefault) };
      setInputs(next);
      runScenario(next);
    }
  }, [allocation?.scenario_sha256]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => setBasis(initialBasis || null), [initialBasis?.artifact_sha256]);
  const change = (field) => (event) => setInputs((current) => ({ ...current, [field]: event.target.value }));
  const submit = (event) => { event.preventDefault(); runScenario(inputs); };
  const refreshBasis = () => {
    setBasisRunning(true);
    setError("");
    fetch("/api/investment/household-basis", {
      method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: "{}",
    }).then((response) => response.json().then((payload) => ({ response, payload })))
      .then(({ response, payload }) => {
        if (!response.ok) throw new Error(payload.error || `public basis failed: ${response.status}`);
        setBasis(payload);
        return requestAllocation(inputs);
      })
      .catch((cause) => setError(cause.message || String(cause)))
      .finally(() => setBasisRunning(false));
  };
  const refreshBudget = () => {
    setRunning(true);
    setError("");
    fetch("/api/investment/household-budget", {
      method: "POST", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: "{}",
    }).then((response) => response.json().then((payload) => ({ response, payload })))
      .then(({ response, payload }) => {
        if (!response.ok) throw new Error(payload.error || `budget refresh failed: ${response.status}`);
        return requestAllocation(inputs);
      })
      .catch((cause) => setError(cause.message || String(cause)))
      .finally(() => setRunning(false));
  };
  const compiledBasis = basis?.capital_market_basis || {};
  const basisScenario = compiledBasis.return_scenarios?.[0]?.expected_returns || {};
  const allocationGoal = allocation?.goal || {};
  const selectedOutcomes = [...(allocation?.selected_policy?.scenario_outcomes || [])]
    .sort((left, right) => Number(left.goal_probability) - Number(right.goal_probability)
      || Number(left.expected_return_assumption) - Number(right.expected_return_assumption)
      || String(left.scenario_id).localeCompare(String(right.scenario_id)));
  const selectedOutcome = selectedOutcomes[0] || null;
  const selectedPath = (allocation?.selected_wealth_paths || [])
    .find((row) => row.scenario_id === selectedOutcome?.scenario_id) || null;
  const mandateQuestion = initialMandateFrontier?.highest_voi_unresolved_input;
  const mandateInvariant = initialMandateFrontier?.status === "decision_invariant_across_declared_completions";
  const mandateAnswers = (mandateQuestion?.answer_cells || []).map((row) => (
    mandateQuestion.input_id === "annual_contribution"
      ? money(row.answer, surface.base_currency)
      : mandateQuestion.input_id === "horizon_years" ? `${row.answer} years` : row.answer
  ));
  const targetProbabilityMet = allocationGoal.target_meets_declared_probability === true;
  const implementation = allocation?.paper_implementation || {};
  const allImplementationProposals = implementation.proposals || [];
  const implementationById = Object.fromEntries(allImplementationProposals.map((row) => [row.proposal_id, row]));
  const displayProposalIds = implementation.display_proposal_ids || [];
  const implementationProposals = displayProposalIds.length
    ? displayProposalIds.map((proposalId) => implementationById[proposalId]).filter(Boolean)
    : allImplementationProposals;
  const decisionClasses = Object.fromEntries((implementation.decision_equivalence_classes || [])
    .map((row) => [row.representative_proposal_id, row]));
  const debtRivals = implementation.debt_rivals || [];
  const rankedAbstentions = implementation.ranked_abstentions || [];
  return <Section eyebrow="Private household policy" title="What could the investable portfolio reach?"
    description="Tune a conservative portfolio-only proxy for the declared net-worth goal. The current balance sheet is shown separately; property value and debt amortization stay outside the portfolio trajectory.">
    <div className="capital-discovery-status">
      <div><span>Known assets</span><strong>{money(balance.known_assets_base, surface.base_currency)}</strong><small>{money(balance.known_investable_liquidity_base, surface.base_currency)} currently identified as investable</small></div>
      <div><span>Known liabilities</span><strong>{money(balance.known_liabilities_base, surface.base_currency)}</strong><small>only sourced and currency-resolved balances</small></div>
      <div><span>Known net position</span><strong>{money(balance.known_net_position_base, surface.base_currency)}</strong><small>{balance.complete ? "complete balance sheet" : "identified assets less identified debts; other accounts may be missing"}</small></div>
      <div><span>Portfolio hurdle</span><strong>{money(goal.target_base, surface.base_currency)}</strong><small>{goal.hurdle_basis === "investable_portfolio_only" ? "investable portfolio only; not a net-worth projection" : "inspect hurdle basis"}</small></div>
      <div><span>Budget contribution scenario</span><strong>{capacity.default_scenario_contribution == null ? "Unavailable" : money(capacity.default_scenario_contribution, surface.base_currency)}</strong><small>{capacity.operator_confirmed ? "confirmed" : "component-recomputed median; tune below"}</small></div>
      <div><span>Unresolved balance sheet</span><strong>{number(unresolvedBalance.length, 0)}</strong><small>{unresolvedBalance.map((value) => String(value).replaceAll("_", " ")).join(" · ") || "none"}</small></div>
    </div>
    <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Balance-sheet item</th><th>Kind</th><th>Original balance</th><th>USD equivalent</th><th>Rate</th></tr></thead><tbody>
      {(balance.assets || []).map((row) => <tr key={`asset:${row.asset_id}`}><td><strong>{String(row.asset_id).replaceAll("_", " ")}</strong></td><td>{row.kind}</td><td>{money(row.value, row.currency)}</td><td>{money(row.value_base, surface.base_currency)}</td><td>—</td></tr>)}
      {(balance.liabilities || []).map((row) => <tr key={`liability:${row.liability_id}`}><td><strong>{String(row.liability_id).replaceAll("_", " ")}</strong></td><td>{row.kind}</td><td>{money(row.balance, row.currency)}</td><td>{money(row.balance_base, surface.base_currency)}</td><td>{row.annual_rate == null ? "—" : pct(row.annual_rate, 1)}</td></tr>)}
    </tbody></table></div>
    <form className="capital-goal-controls" onSubmit={submit}>
      <label><span>Annual contribution</span><input type="number" min="0" step="1000" value={inputs.annual_contribution} onChange={change("annual_contribution")} /></label>
      <label><span>Horizon</span><input type="number" min="1" max="100" step="1" value={inputs.horizon_years} onChange={change("horizon_years")} /><small>years</small></label>
      <label><span>Target</span><input type="number" min="1" step="10000" value={inputs.target_wealth} onChange={change("target_wealth")} /></label>
      <label><span>Liquidity reserve</span><input type="number" min="0" step="1000" value={inputs.liquidity_reserve} onChange={change("liquidity_reserve")} /></label>
      <label><span>Maximum risky sleeves</span><input type="number" min="0" max="100" step="5" value={inputs.max_risky_weight_percent} onChange={change("max_risky_weight_percent")} /><small>% of investable capital</small></label>
      <button type="submit" className="copy-button primary" disabled={running}>{running ? <RefreshCw size={15} className="capital-spin" /> : null}Run scenario</button>
    </form>
    <details className="capital-overview-details"><summary><span><strong>Scenario risk and tax controls</strong><small>Assumptions stay visible and never become your operator policy.</small></span></summary>
      <div className="capital-goal-controls">
        <label><span>Maximum one-year loss proxy</span><input type="number" min="0" max="100" step="5" value={inputs.max_one_year_loss_percent} onChange={change("max_one_year_loss_percent")} /><small>%</small></label>
        <label><span>Minimum goal probability</span><input type="number" min="0" max="100" step="5" value={inputs.minimum_success_probability_percent} onChange={change("minimum_success_probability_percent")} /><small>%</small></label>
        <label><span>Equity annual tax drag</span><input type="number" min="0" max="100" step="0.1" value={inputs.equity_tax_drag_percent} onChange={change("equity_tax_drag_percent")} /><small>%</small></label>
        <label><span>Defensive annual tax drag</span><input type="number" min="0" max="100" step="0.1" value={inputs.defensive_tax_drag_percent} onChange={change("defensive_tax_drag_percent")} /><small>%</small></label>
      </div>
    </details>
    {error ? <div className="capital-boundary"><AlertTriangle size={17} /><div><strong>Scenario rejected</strong><p>{error}</p></div></div> : null}
    {budget.checks?.financing_includes_dependent_care ? <div className="capital-boundary"><AlertTriangle size={17} /><div><strong>Budget formula issue isolated</strong><p>The workbook financing total includes dependent care and the overall expense total adds dependent care again. Medical also includes a percentage row. The displayed contribution default uses the component-recomputed 2027–2030 median; workbook totals remain excluded and the source file was not changed.</p></div></div> : null}
    {initialMandateFrontier?.mandate_frontier_sha256 ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>{mandateInvariant ? "Planning allocation survives every declared completion" : mandateQuestion ? `One answer matters most · ${String(mandateQuestion.input_id).replaceAll("_", " ")}` : "Declared mandate completions compiled"}</strong><p>{mandateInvariant ? `${number(initialMandateFrontier.design_world_count, 0)} bounded completions close to one exact sleeve-weight decision.` : mandateQuestion ? `${mandateQuestion.question} It separates ${number(initialMandateFrontier.decision_class_count, 0)} exact allocation decisions across ${number(initialMandateFrontier.design_world_count, 0)} declared completions.` : `${number(initialMandateFrontier.design_world_count, 0)} completions produce ${number(initialMandateFrontier.decision_class_count, 0)} decision classes.`}</p><small>{mandateQuestion ? `Declared answers: ${mandateAnswers.join(" · ")} · resolves ${pct(mandateQuestion.fraction_of_current_decision_ambiguity, 0)} of design ambiguity` : (initialMandateFrontier.invariant_actions || []).map((row) => `${String(row.sleeve_id).replaceAll("_", " ")} ${pct(row.target_weight, 0)}`).join(" · ")} · finite design, not odds · no policy authority</small></div></div> : null}
    <GoalTrajectoryChart path={selectedPath} outcome={selectedOutcome}
      target={Number(allocationGoal.portfolio_terminal_target_base || inputs.target_wealth)}
      horizon={Number(inputs.horizon_years)} currency={surface.base_currency} />
    {allocation?.selected_policy ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>{targetProbabilityMet ? "Planning allocation meeting the goal floor" : "Best available allocation; goal floor unmet"}</strong><p>{Object.entries(allocation.selected_policy.weights || {}).filter(([, weight]) => Number(weight) > 0).map(([asset, weight]) => `${String(asset).replaceAll("_", " ")} ${pct(weight, 0)}`).join(" · ") || "all cash"}</p><small>{pct(allocation.selected_policy.robust_goal_probability, 0)} worst-scenario goal frequency versus {pct(allocationGoal.minimum_success_probability, 0)} requested · {pct(allocation.selected_policy.robust_expected_return, 1)} source-anchored return assumption versus {pct(allocationGoal.required_constant_return, 1)} constant-return hurdle · {pct(allocation.selected_policy.volatility, 1)} volatility · {number(allocation.enumeration?.feasible_program_count, 0)} feasible allocations exhaustively compared</small></div></div> : null}
    <div className="capital-closure-rule"><Target size={20} /><div><strong>{operatorPolicy ? "Operator paper policy frozen" : "Operator paper policy awaiting completion"}</strong><p>{operatorPolicy ? `${operatorPolicy.selected_proposal_id} is the explicit paper implementation under ${operatorPolicy.policy_id}.` : "The engine may keep testing shadow policies, but it will not infer your household mandate or choose one of these implementation rivals for you."}</p><small>{operatorPolicy ? `Reviewed ${String(operatorPolicy.reviewed_at).slice(0, 10)} · prospective run ${operatorPolicy.prospective_tournament_run_id}` : `${number(missing.length, 0)} private mandate fields remain · use the typed operator-policy CLI/API once they are bound`}</small></div><Status ok={Boolean(operatorPolicy)}>{String(initialOperatorPolicy?.status || "awaiting selection").replaceAll("_", " ")}</Status></div>
    {allocation?.policy_rivals?.length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Rival policy</th><th>Sleeve weights</th><th>Goal frequency</th><th>Return assumption</th><th>Volatility</th></tr></thead><tbody>
      {allocation.policy_rivals.map((row) => <tr key={row.rival_id}><td><strong>{String(row.rival_id).replaceAll("_", " ")}</strong><small>{row.selected ? "selected by goal rule" : String(row.selection_role || "").replaceAll("_", " ")}</small></td><td>{Object.entries(row.program?.weights || {}).filter(([, weight]) => Number(weight) > 0).map(([asset, weight]) => `${String(asset).replaceAll("_", " ")} ${pct(weight, 0)}`).join(" · ") || "all cash"}</td><td>{pct(row.program?.robust_goal_probability, 0)}</td><td>{pct(row.program?.robust_expected_return, 1)}</td><td>{pct(row.program?.volatility, 1)}</td></tr>)}
    </tbody></table></div> : null}
    {implementationProposals.length ? <>
      <div className="capital-closure-rule"><Target size={20} /><div><strong>Paper decision menu · operator selection withheld</strong><p>The household frontier fixes sleeve capacity. Current instrument admissions may replace only their own broad proxy and only up to their position cap. The amounts below are scenario rivals over {money(implementationProposals[0]?.starting_investable_wealth_base, surface.base_currency)}; no order or funded allocation is enabled.</p><small>{pct(implementation.goal_test?.selected_robust_goal_probability, 0)} goal frequency versus {pct(implementation.goal_test?.minimum_success_probability, 0)} requested · {implementation.admitted_instrument_count || 0} admitted instruments · {implementation.enumerated_rule_count || allImplementationProposals.length} stable rules → {implementation.decision_distinct_count || implementationProposals.length} distinct decisions</small></div></div>
      <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Implementation</th><th>Paper positions</th><th>Role</th><th>Status</th></tr></thead><tbody>{implementationProposals.map((row) => <tr key={row.proposal_sha256}><td><strong>{row.proposal_id === "broad_sleeve_control" ? "Broad-market control" : "Admitted-security satellite"}</strong><small>{String(row.method || "").replaceAll("_", " ").replace("existing portfolio policy rule:", "")}</small></td><td>{(row.positions || []).map((position) => `${position.entity_id} ${pct(position.target_weight, 0)} (${money(position.paper_amount_base, surface.base_currency)})`).join(" · ")}</td><td>{row.selection_signal?.signal_class ? String(row.selection_signal.signal_class).replaceAll("_", " ") : row.proposal_id === "broad_sleeve_control" ? "comparison baseline" : "allocation-rule control"}<small>{row.selection_signal ? "selection hypothesis; no realized-return claim" : "no expected-return claim"}</small></td><td><Status>{String(row.selection_status || "paper rival").replaceAll("_", " ")}</Status><small>{(decisionClasses[row.proposal_id]?.proposal_ids || []).length > 1 ? `${decisionClasses[row.proposal_id].proposal_ids.length} rule hypotheses currently share these weights` : "one decision program"}</small></td></tr>)}</tbody></table></div>
      <div className="capital-action-row">
        <button type="button" className="capital-link" disabled={freezing || implementation.prospective_tournament_ready === false} onClick={freezeComparison}>{freezing ? <RefreshCw size={14} className="capital-spin" /> : <Target size={14} />}Freeze one-year paper comparison</button>
        <small>{freezeResult?.run_id ? `${String(freezeResult.activation_status || freezeResult.lifecycle_status || freezeResult.status || "pending outcome").replaceAll("_", " ")} · ${freezeResult.run_id} · outcome after ${String(freezeResult.end_at || "the fixed horizon").slice(0, 10)}` : implementation.prospective_tournament_ready === false ? "No rule currently changes the broad-sleeve decision, so there is no comparison to freeze." : "Locks these exact weights before later prices; the periodic capital cycle settles them against the broad-sleeve control. No brokerage action."}</small>
      </div>
      {!operatorPolicy ? <details className="capital-overview-details"><summary><span><strong>Choose the household paper policy</strong><small>Five explicit inputs; the engine reuses the known balance sheet and displayed scenario.</small></span></summary>
        <div className="capital-control-grid">
          <label><span>Age</span><input type="number" min="18" max="100" value={operatorInputs.age} onChange={(event) => setOperatorInputs({ ...operatorInputs, age: event.target.value })} /></label>
          <label><span>Tax residence</span><input type="text" placeholder="e.g. US" value={operatorInputs.tax_residence} onChange={(event) => setOperatorInputs({ ...operatorInputs, tax_residence: event.target.value })} /></label>
          <label><span>Account identities</span><input type="text" placeholder="taxable, 401k" value={operatorInputs.account_ids} onChange={(event) => setOperatorInputs({ ...operatorInputs, account_ids: event.target.value })} /></label>
          <label><span>Paper implementation</span><select value={operatorInputs.selected_proposal_id} onChange={(event) => setOperatorInputs({ ...operatorInputs, selected_proposal_id: event.target.value })}><option value="">Select one</option>{implementationProposals.map((row) => <option key={row.proposal_sha256} value={row.proposal_id}>{String(row.proposal_id).replaceAll("_", " ")}</option>)}</select></label>
        </div>
        <label className="capital-check"><input type="checkbox" checked={operatorInputs.human_capital_reviewed} onChange={(event) => setOperatorInputs({ ...operatorInputs, human_capital_reviewed: event.target.checked })} /><span>Exclude human capital from this paper allocation; salary remains a contribution source, not a portfolio asset.</span></label>
        <label className="capital-check"><input type="checkbox" checked={operatorInputs.liability_currency_reviewed} onChange={(event) => setOperatorInputs({ ...operatorInputs, liability_currency_reviewed: event.target.checked })} /><span>Accept unhedged EUR liability-currency risk in this paper policy; no USD-listed fund is treated as an EUR hedge.</span></label>
        <div className="capital-action-row"><button type="button" className="capital-link" disabled={operatorFreezing || !operatorInputs.age || !operatorInputs.tax_residence.trim() || !operatorInputs.account_ids.trim() || !operatorInputs.selected_proposal_id || !operatorInputs.human_capital_reviewed || !operatorInputs.liability_currency_reviewed} onClick={freezeOperatorPolicy}>{operatorFreezing ? <RefreshCw size={14} className="capital-spin" /> : <Target size={14} />}Freeze explicit paper policy</button><small>This records a paper-only operator choice and starts or reuses its one-year comparison. It cannot place an order.</small></div>
      </details> : null}
      {debtRivals.length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Debt rival</th><th>Maximum scenario paydown</th><th>Guaranteed nominal return</th><th>Cash hurdle</th><th>Current comparison</th></tr></thead><tbody>{debtRivals.map((row) => <tr key={row.liability_id}><td><strong>{String(row.liability_id).replaceAll("_", " ")}</strong><small>{money(row.remaining_investable_base, surface.base_currency)} would remain investable</small></td><td>{money(row.maximum_scenario_paydown_base, surface.base_currency)}</td><td>{pct(row.guaranteed_nominal_paydown_return, 2)}</td><td>{pct(row.cash_return_assumption, 2)}</td><td>{String(row.posture || "compare").replaceAll("_", " ")}<small>tax and loan terms unresolved</small></td></tr>)}</tbody></table></div> : null}
      {rankedAbstentions.length ? <details className="capital-overview-details"><summary><span><strong>Why ranked opportunities still receive 0%</strong><small>Research rank directs diligence; admission controls eligibility.</small></span></summary><div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Research rank</th><th>Candidate</th><th>Type</th><th>Reason for abstention</th></tr></thead><tbody>{rankedAbstentions.map((row) => <tr key={`${row.entity_kind}:${row.entity_id}`}><td>{row.research_rank ? `#${row.research_rank}` : "unranked"}</td><td><strong>{row.entity_id}</strong></td><td>{String(row.entity_kind).replaceAll("public_", "").replaceAll("_", " ")}</td><td>{String(row.reason).replaceAll("_", " ")}</td></tr>)}</tbody></table></div></details> : null}
    </> : null}
    <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>What the paths include</strong><p>Starting investable liquidity, year-end contributions, and the selected allocation's source-anchored after-tax return distribution. They exclude property value, debt amortization, and other nonportfolio terminal value; reaching this hurdle does not establish the declared net-worth goal.</p></div></div>
    <div className="capital-action-row">
      <button type="button" className="capital-link" disabled={basisRunning} onClick={refreshBasis}>{basisRunning ? <RefreshCw size={14} className="capital-spin" /> : <RefreshCw size={14} />}Refresh public risk basis</button>
      <button type="button" className="capital-link" disabled={running} onClick={refreshBudget}><RefreshCw size={14} />Refresh private budget receipt</button>
      <small>Public adjusted-price covariance and current Treasury/ERP anchors; never refreshed by scenario sliders.</small>
    </div>
    {(compiledBasis.asset_classes || []).length ? <div className="capital-discovery-status">
      {compiledBasis.asset_classes.map((row) => <div key={row.asset_id}><span>{String(row.asset_id).replaceAll("_", " ")}</span><strong>{pct(row.volatility, 1)} volatility</strong><small>{pct(basisScenario[row.asset_id], 1)} source-anchored scenario return</small></div>)}
    </div> : null}
    {compiledBasis.asset_classes?.length ? <div className="capital-boundary"><AlertTriangle size={17} /><div><strong>Currency boundary</strong><p>The planning frontier converts known balances to USD but does not treat a USD-listed international fund as an EUR hedge. {nonUsdCurrencies.length ? `${nonUsdCurrencies.join(", ")} exposure remains outside the sleeve constraint until a currency policy is declared.` : "No non-USD exposure is currently identified."}</p></div></div> : null}
    <div className="capital-boundary"><AlertTriangle size={17} /><div><strong>Why these are planning weights, not an account plan</strong><p>{missing.slice(0, 6).map((value) => String(value).replaceAll("_", " ")).join(" · ")}{missing.length > 6 ? ` · +${missing.length - 6} more` : ""}. The frontier is usable for trade-off exploration now; exact fund placement, taxes, and current-position transitions wait for the account snapshot.</p></div></div>
  </Section>;
}

function SleeveImplementation({ state, onPreview }) {
  const frontier = state.sleeve_implementation_frontier;
  if (!frontier?.sleeves?.length) return null;
  const comparison = state.fund_sleeve_comparison || {};
  const implementationReview = state.fund_implementation_review || {};
  const comparisonPrograms = (comparison.sleeves || []).flatMap((sleeve) =>
    (sleeve.programs || []).map((row) => ({ ...row, sleeve_id: sleeve.sleeve_id }))
  );
  const comparisonBySleeve = Object.fromEntries(
    (comparison.sleeves || []).map((sleeve) => [sleeve.sleeve_id, sleeve])
  );
  const tournament = comparison.portfolio_policy_tournament_input || {};
  const policyPath = state.household_paper_policy_path || {};
  const nextPolicyActivation = policyPath.next_activation || {};
  const policyRivals = policyPath.allocation_policy_rivals || [];
  const blockers = [...new Set([
    ...(frontier.mandate_blockers || []), ...(frontier.implementation_blockers || []),
  ])];
  const candidates = frontier.sleeves.flatMap((sleeve) =>
    (sleeve.eligible_instruments || []).filter((row) => !row.basis_proxy)
      .map((row) => ({ ...row, implementation_sleeve_id: sleeve.sleeve_id }))
  );
  const gapFamilies = (rows) => {
    const gaps = rows.flatMap((row) => row.evidence_gaps || []);
    const families = [];
    if (gaps.some((gap) => gap.includes("expense"))) families.push("fees");
    if (gaps.some((gap) => /spread|volume|assets/.test(gap))) families.push("liquidity");
    if (gaps.some((gap) => gap.includes("factor"))
      || rows.some((row) => !Object.keys(row.factor_fit?.exposures || {}).length)) families.push("factor fit");
    if (gaps.some((gap) => /holding|lookthrough|peer/.test(gap))) families.push("look-through");
    if (gaps.some((gap) => gap.includes("proposal"))) families.push("proposal review");
    return families;
  };
  return <Section eyebrow="Public sleeve implementation" title="Which funds are on each sleeve's risk/cost frontier?"
    description="The five-sleeve allocation basis stays broad; the current fund challenger set is a value-oriented research cohort inside the equity sleeves. Each fund is compared as one normalized substitute before any household weights are considered."
    actions={<>{state.paths?.fund_implementation_review_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.fund_implementation_review_latest)}><FileText size={14} />Inspect fund review lane</button> : null}{state.paths?.allocation_readiness_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.allocation_readiness_latest)}><FileText size={14} />Inspect allocation readiness</button> : null}</>}>
    <div className="capital-discovery-status">
      <div><span>Policy state</span><strong>{frontier.policy_consumed ? "policy consumed" : "evidence only"}</strong><small>{frontier.status || "implementation research"}</small></div>
      <div><span>Public sleeves</span><strong>{number(frontier.sleeves.length, 0)}</strong><small>cash, equity, bonds, and inflation protection</small></div>
      <div><span>Compared funds</span><strong>{number(candidates.length, 0)}</strong><small>candidate-specific sleeve identity</small></div>
      <div><span>Implementation admissions</span><strong>{number(frontier.implementation_review_admitted_count, 0)}</strong><small>{number(frontier.paper_watch_activation_count, 0)} activated paper watches</small></div>
      <div><span>Risk/cost comparisons</span><strong>{number(comparison.comparison_eligible_count, 0)}</strong><small>{String(comparison.status || "not compiled").replaceAll("_", " ")}</small></div>
      <div><span>Comparison review lane</span><strong>{number(implementationReview.request_count, 0)} requests</strong><small>{number(implementationReview.evidence_count, 0)} evidence · {number(implementationReview.proposal_count, 0)} operator-review ready · {String(implementationReview.status || "not compiled").replaceAll("_", " ")}</small></div>
      <div><span>Fund hurdle</span><strong>{comparison.cash_hurdle?.expected_annual_return == null ? "awaiting cash basis" : pct(comparison.cash_hurdle.expected_annual_return, 2)}</strong><small>{number(tournament.cash_hurdle_candidate_count, 0)} core frontier funds have positive assumption spread versus cash</small></div>
      <div><span>Prospective fund trials</span><strong>{number(tournament.prospective_ranking_ticket_count, 0)}</strong><small>{number(tournament.same_information_core_candidate_count, 0)} same-information candidates</small></div>
      <div><span>Look-through ready</span><strong>{number(tournament.lookthrough_quality_candidate_count, 0)}</strong><small>{number(tournament.portfolio_policy_candidate_count, 0)} eligible portfolio candidates</small></div>
      <div><span>Capital authority</span><strong>none</strong><small>research projection only</small></div>
    </div>
    {nextPolicyActivation.activation_id ? <div className="capital-closure-rule"><Clock3 size={20} /><div><strong>Next operator-policy activation · {String(nextPolicyActivation.activation_id).replaceAll("_", " ")}</strong><p>{String(nextPolicyActivation.next_action || "complete the owning contract").replaceAll("_", " ")}. This unlocks {String(nextPolicyActivation.unlocks || "the next portfolio gate").replaceAll("_", " ")}.</p><small>The planning frontier above is already usable · {String(nextPolicyActivation.owner || "unassigned").replaceAll("_", " ")} · {number(nextPolicyActivation.blockers?.length, 0)} activation blocker{nextPolicyActivation.blockers?.length === 1 ? "" : "s"}</small></div><Status ok={nextPolicyActivation.status === "ready"}>{String(nextPolicyActivation.status || "blocked").replaceAll("_", " ")}</Status></div> : null}
    {(policyPath.activation_points || []).length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Activation</th><th>State</th><th>Unlocks</th><th>Next action</th></tr></thead><tbody>
      {policyPath.activation_points.map((row) => <tr key={row.activation_id}>
        <td><strong>{String(row.activation_id).replaceAll("_", " ")}</strong><small>{String(row.owner || "").replaceAll("_", " ")}</small></td>
        <td><Status ok={row.status === "ready"}>{String(row.status || "blocked").replaceAll("_", " ")}</Status></td>
        <td>{String(row.unlocks || "").replaceAll("_", " ")}</td>
        <td>{String(row.next_action || "").replaceAll("_", " ")}<small>{(row.blockers || []).slice(0, 3).map((value) => String(value).replaceAll("_", " ")).join(" · ")}</small></td>
      </tr>)}
    </tbody></table></div> : null}
    {policyRivals.length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Allocation rival</th><th>Policy</th><th>Worst-scenario return</th><th>Goal probability</th></tr></thead><tbody>
      {policyRivals.map((row) => {
        const program = row.program || {};
        const weights = Object.entries(program.weights || {})
          .filter(([, weight]) => Number(weight) > 0)
          .map(([sleeve, weight]) => `${String(sleeve).replaceAll("_", " ")} ${pct(weight, 0)}`)
          .join(" · ");
        return <tr key={row.rival_id}>
          <td><strong>{String(row.rival_id).replaceAll("_", " ")}</strong><small>{String(row.selection_role || "complete policy rival").replaceAll("_", " ")}</small></td>
          <td>{program.program_id ? <><strong>{weights || "all cash"}</strong><small>{row.selected ? "coincides with selected paper policy" : program.program_id}</small></> : <Status ok={false}>{String(row.status || "blocked household mandate").replaceAll("_", " ")}</Status>}</td>
          <td>{program.robust_expected_return == null ? "—" : pct(program.robust_expected_return, 1)}</td>
          <td>{program.robust_goal_probability == null ? "—" : pct(program.robust_goal_probability, 0)}</td>
        </tr>;
      })}
    </tbody></table></div> : null}
    {tournament.prospective_ranking_ticket_count ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>What the fund tournament learns next</strong><p>The engine has frozen {number(tournament.prospective_ranking_ticket_count, 0)} paper ranking trials across the eligible fund set. It will compare later returns for fee-adjusted factor fit and aggregate earnings power using the same candidate information set; holdings-based quality stays excluded until issuer evidence covers enough disclosed fund weight.</p></div></div> : null}
    {tournament.cash_hurdle_candidate_count ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Cash spread is a challenger, not the fund rank</strong><p>{number(tournament.cash_hurdle_candidate_count, 0)} same-information frontier funds currently have a positive fee-adjusted factor-return assumption versus the source-bound cash hurdle. The holistic sleeve rank still combines valuation, factor return and risk, cost, and fit. Later settlements must decide whether either rule selects better funds; the engine does not replace one with the other from this snapshot.</p></div></div> : null}
    <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Sleeve</th><th>Policy state</th><th>Fund evidence</th><th>Non-dominated substitutes</th><th>Open evidence</th></tr></thead><tbody>
      {frontier.sleeves.map((sleeve) => {
        const instruments = sleeve.eligible_instruments || [];
        const funds = instruments.filter((row) => !row.basis_proxy);
        const evidenceRows = funds.length ? funds : instruments;
        const fees = funds.filter((row) => row.fees?.expense_ratio != null).length;
        const liquid = funds.filter((row) => Object.values(row.liquidity || {}).every((value) => value != null)).length;
        const factors = funds.filter((row) => Object.keys(row.factor_fit?.exposures || {}).length).length;
        const lookthrough = funds.filter((row) => row.lookthrough_fit?.snapshot_path).length;
        const compared = comparisonBySleeve[sleeve.sleeve_id];
        const hasRiskCostPrograms = Boolean(compared?.programs?.length);
        const substitutes = hasRiskCostPrograms
          ? (compared.programs || []).filter((row) => row.risk_cost_frontier_status === "frontier")
            .map((row) => row.identity?.subject_id).filter(Boolean)
          : (sleeve.nondominated_substitutes || []).map((row) => row.subject_id);
        const gaps = gapFamilies(evidenceRows);
        return <tr key={sleeve.sleeve_id}>
          <td><strong>{String(sleeve.sleeve_id).replaceAll("_", " ")}</strong><small>basis proxy {sleeve.basis_proxy?.subject_id || "—"}</small></td>
          <td><Status ok={sleeve.policy_status === "selected"}>{String(sleeve.policy_status || "evidence only").replaceAll("_", " ")}</Status></td>
          <td><strong>{funds.length ? `${funds.length} candidate${funds.length === 1 ? "" : "s"}` : "basis proxy only"}</strong><small>{funds.length ? `fees ${fees}/${funds.length} · liquidity ${liquid}/${funds.length} · factor ${factors}/${funds.length} · look-through ${lookthrough}/${funds.length}` : "no compared fund evidence"}</small></td>
          <td><strong>{substitutes.join(", ") || "none"}</strong><small>{hasRiskCostPrograms ? "risk/cost frontier; no portfolio weights" : String(sleeve.dominance_authority || "").replaceAll("_", " ")}</small></td>
          <td>{gaps.join(" · ") || "no recorded evidence gap"}</td>
        </tr>;
      })}
    </tbody></table></div>
    {candidates.length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Fund</th><th>Sleeve</th><th>Choice frontier</th><th>Review admission</th><th>Next transition</th></tr></thead><tbody>
      {candidates.map((row) => {
        const admission = row.implementation_candidate || {};
        return <tr key={`${row.implementation_sleeve_id}:${row.identity?.subject_id}`}>
          <td><strong>{row.identity?.subject_id}</strong><small>{row.name}</small></td>
          <td>{String(row.implementation_sleeve_id || "unbound").replaceAll("_", " ")}</td>
          <td><Status ok={row.fund_frontier_status === "frontier"}>{String(row.fund_frontier_status || "compared").replaceAll("_", " ")}</Status></td>
          <td><strong>{String(admission.status || "research only").replaceAll("_", " ")}</strong><small>{admission.implementation_review_activated ? "active zero-weight implementation review" : admission.paper_watch_activated ? "active zero-weight opportunity watch" : "awaiting typed evidence or operator review"}</small></td>
          <td><code>{String(admission.required_next_transition || "complete evidence").replaceAll("_", " ")}</code><small>{(admission.evidence_gaps || []).slice(0, 3).map((gap) => String(gap).replaceAll("_", " ")).join(" · ") || "no recorded implementation gap"}</small></td>
        </tr>;
      })}
    </tbody></table></div> : null}
    {comparisonPrograms.length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Normalized substitute</th><th>Expected return / cash hurdle</th><th>Risk</th><th>Observed cost</th><th>Frontier</th></tr></thead><tbody>
      {comparisonPrograms.map((row) => {
        const metrics = row.comparison_metrics;
        return <tr key={row.program_id}>
          <td><strong>{row.identity?.subject_id}</strong><small>{String(row.sleeve_id || "").replaceAll("_", " ")} · one sleeve unit, no portfolio weight</small></td>
          <td>{metrics ? <><strong>{pct(metrics.factor_implied_return_less_expense, 1)}</strong><small>{row.cash_comparison?.expected_excess_return == null ? "cash hurdle unavailable" : `${pct(row.cash_comparison.expected_excess_return, 1)} assumption spread vs cash`} · historical residual alpha receives zero rank credit</small></> : "evidence blocked"}</td>
          <td>{metrics ? <><strong>{pct(metrics.annualized_volatility, 1)} volatility</strong><small>{pct(metrics.drawdown_severity, 1)} historical max drawdown</small></> : "—"}</td>
          <td>{metrics ? <><strong>{pct(metrics.expense_ratio, 2)} yearly</strong><small>{pct(metrics.half_spread_entry_cost_proxy, 2)} half-spread entry proxy</small></> : "—"}</td>
          <td><Status ok={row.risk_cost_frontier_status === "frontier"}>{String(row.risk_cost_frontier_status || "blocked").replaceAll("_", " ")}</Status><small>{row.implementation_review_admitted ? "admitted for implementation review" : "research comparison only"}</small></td>
        </tr>;
      })}
    </tbody></table></div> : null}
    {comparison.portfolio_handoff?.blockers?.length ? <div className="capital-boundary"><AlertTriangle size={17} /><div><strong>Why this comparison is not a portfolio yet</strong><p>{comparison.portfolio_handoff.blockers.map((value) => String(value).replaceAll("_", " ")).join(" · ")}. The existing portfolio compiler takes over only after those contracts exist.</p></div></div> : null}
    {!frontier.policy_consumed ? <div className="capital-boundary"><AlertTriangle size={17} /><div><strong>Exact blockers preventing operator-policy activation</strong><p>{blockers.length ? blockers.map((blocker) => `${String(blocker).replaceAll("_", " ")} [${blocker}]`).join(" · ") : "No complete household policy is bound."} Planning weights remain available above without policy authority.</p></div></div> : null}
  </Section>;
}

function CandidateJourney({ state }) {
  const candidates = state.allocation_readiness?.candidates || [];
  const closedRuns = state.closed_book?.runs || [];
  const admissions = state.instrument_portfolio_admissions?.admissions || [];
  const admissionByEntity = Object.fromEntries(admissions.map((row) => [row.subject?.subject_id, row]));
  if (!candidates.length) return null;
  const ranked = [...candidates].sort((left, right) =>
    Number(left.research_priority?.rank ?? 1e9) - Number(right.research_priority?.rank ?? 1e9));
  const currentPaper = ranked.filter((row) => row.paper?.state !== "screened");
  const rows = [...new Map([...currentPaper, ...ranked.slice(0, 10)]
    .map((row) => [row.candidate_sha256, row])).values()]
    .sort((left, right) => Number(left.research_priority?.rank ?? 1e9) - Number(right.research_priority?.rank ?? 1e9))
    .slice(0, 15);
  return <>
    <h3>Current candidate journey</h3>
    <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Candidate</th><th>Discover</th><th>Research</th><th>Forecast / ablation</th><th>Paper portfolio</th><th>Settle / learn</th><th>Next machine action</th></tr></thead><tbody>
      {rows.map((row) => {
        const paper = row.paper || {};
        const admission = admissionByEntity[row.entity_id] || {};
        const projection = admission.portfolio_projection || {};
        const hurdle = projection.required_return_hurdle || {};
        const activeClaims = projection.expected_active_return_claims || [];
        const learning = row.prospective_learning || {};
        const runs = closedRuns.filter((run) => run.entity?.entity_id === row.entity_id);
        const ablation = runs.find((run) => run.underwriting_ablation)?.underwriting_ablation;
        const pending = runs.filter((run) => run.status !== "settled").length + Number(learning.portfolio_policy_pending_count || 0);
        const settled = runs.filter((run) => run.status === "settled").length + Number(learning.portfolio_policy_settled_count || 0);
        const awaitingResearch = (row.activation_gaps || []).some((gap) => String(gap).includes("research") || String(gap).includes("dossier") || String(gap).includes("fund_review"));
        const gapSummary = (row.activation_gaps || []).slice(0, 2).map((value) => String(value).replaceAll("_", " ")).join(" · ");
        return <tr key={row.candidate_sha256}>
          <td><strong>#{number(row.research_priority?.rank, 0)} · {row.entity_id}</strong><small>{String(row.entity_kind || "candidate").replaceAll("_", " ")} · research priority, not expected return</small></td>
          <td><Status ok={row.watchlist?.screen_status === "qualified"}>{String(row.watchlist?.screen_status || "unscored").replaceAll("_", " ")}</Status><small>{String(row.watchlist?.activation_class || "awaiting classification").replaceAll("_", " ")}</small></td>
          <td><Status ok={!awaitingResearch}>{awaitingResearch ? "awaiting evidence" : "evidence joined"}</Status><small>{String(paper.decision_stage || paper.state || "screened").replaceAll("_", " ")}</small></td>
          <td><Status ok={runs.length > 0}>{runs.length ? `${runs.length} sealed` : "not opened"}</Status><small>{ablation ? `${ablation.arms?.length || 0}-arm ${String(ablation.status || "ablation").replaceAll("_", " ")}` : runs.length ? "standard frozen forecast" : "awaiting an eligible paper watch"}</small></td>
          <td><Status ok={admission.eligibility?.research_paper_portfolio_candidate || row.allocation_ready || row.allocated_paper}>{String(admission.eligibility?.status || paper.state || "screened").replaceAll("_", " ")}</Status><small>{hurdle.annualized_excess == null ? (paper.target_weight == null ? "no portfolio weight" : `${pct(paper.target_weight, 1)} paper weight`) : `${pct(hurdle.annualized_excess, 1)} required-return excess (not forecast) · ${activeClaims.length ? activeClaims.map((claim) => `${number(claim.horizon_days, 0)}d ${pct(claim.value, 1)}`).join(" / ") : "no sealed active-return claim"} · ${pct(projection.downside_risk, 1)} downside · cap ${pct(projection.target_weight_cap, 0)}`}</small></td>
          <td><Status ok={settled > 0}>{settled} settled · {pending} pending</Status><small>{pending ? "outcome window is still open" : settled ? "available to learning" : "no prospective episode yet"}</small></td>
          <td><strong>{String(row.next_activation || "monitor").replaceAll("_", " ")}</strong><small>{gapSummary || "No activation blocker"}{(row.activation_gaps || []).length > 2 ? ` · +${row.activation_gaps.length - 2} more` : ""}</small></td>
        </tr>;
      })}
    </tbody></table></div>
    <small>Showing {rows.length} current or highest-ranked candidates from {candidates.length} in the latest discovery epoch.</small>
  </>;
}

function Overview({ state, busy, onAction, onPreview }) {
  const readiness = state.readiness || {};
  const operatorDecisions = (state.decisions || []).filter((row) => row.data_class === "operator");
  const fixtureCount = Number(readiness.reference_fixture_count || 0);
  const brief = state.investor_action_brief || {};
  const decisionSummary = brief.decision_summary || {};
  const implementationCandidates = brief.implementation_candidates || [];
  const paperWatches = state.paper_watch_decisions || [];
  const paperWatchNames = [...new Set(paperWatches.map((row) => row.entity?.entity_id).filter(Boolean))];
  const edgeMap = state.institutional_edge_map || {};
  const economicEdges = edgeMap.edges || [];
  const reviewableEdgeCount = economicEdges.filter((row) => row.reviewable).length;
  const learningDesign = state.learning_experiment_design || {};
  const nextExperiment = learningDesign.next_experiment || {};
  const nextVariation = nextExperiment.variation || {};
  const learningActivation = state.learning_experiment_activation || {};
  const nextLearningTransition = learningActivation.next_transition || {};
  const pointInTimeEvidence = state.point_in_time_evidence || {};
  const researchBudgetTournament = state.research_budget_tournament || {};
  const strategyLawInduction = state.strategy_law_induction || {};
  const strategyValuationBridge = state.strategy_valuation_bridge || {};
  const paperPolicyPath = state.household_paper_policy_path || {};
  const nextPaperActivation = paperPolicyPath.next_activation || {};
  const planningWeights = paperPolicyPath.planning_projection?.selected_sleeve_weights || {};
  const planningWeightText = Object.entries(planningWeights)
    .filter(([, weight]) => Number(weight) > 0)
    .map(([sleeve, weight]) => `${String(sleeve).replaceAll("_", " ")} ${pct(weight, 0)}`)
    .join(" · ");
  const activePaperCash = brief.cash_posture?.paper?.cash_weight;
  const sourceRun = state.source_run || {};
  const discoveryService = state.discovery?.service || {};
  const nextAutomatic = state.live_automatic_transition || brief.next_automatic_transition || {};
  const immediateTransition = (
    nextAutomatic.active || nextAutomatic.subject_id || (nextAutomatic.blocked_reasons || []).length
  ) ? nextAutomatic : (nextLearningTransition.transition ? nextLearningTransition : nextAutomatic);
  const pendingSettlements = Number(readiness.closed_book_pending_count || 0);
  const settledOutcomes = Number(readiness.closed_book_settled_count || 0);
  const excludedForecastEpisodes = Number(state.closed_book?.duplicate_run_count || 0);
  const automationStatus = String(state.capital_cycle?.service?.status || "awaiting server")
    .replaceAll("_", " ");
  const investmentEdgeStatus = settledOutcomes > 0 && reviewableEdgeCount > 0
    ? "prospective evidence accumulating" : "unproven";
  const observationCount = Number(
    sourceRun.observation_count || pointInTimeEvidence.observation_count || 0,
  );
  return <>
    <Section eyebrow="Start here" title="What the investment engine is doing now"
      description="It scans public companies and funds, sends the highest-value evidence gaps to research, keeps decisions in a paper book, and learns only when later outcomes settle."
      actions={<><ActionButton action="sources" busy={busy} onAction={onAction}>Refresh sources</ActionButton><ActionButton action="discover" busy={busy} onAction={onAction} primary>Run discovery</ActionButton></>}>
      <div className="capital-closure-rule"><Activity size={20} /><div><strong>Automation {automationStatus} · investment edge {investmentEdgeStatus}</strong><p>The machinery is operating: it ranks opportunities, acquires evidence, freezes paper decisions, and checks due outcomes. A strategy or portfolio rule earns influence only after later source-bound results beat its fixed control.</p></div></div>
      <div className="capital-activation-grid">
        <article><header><strong>Runs automatically</strong><code>{String(nextAutomatic.status || discoveryService.status || "idle").replaceAll("_", " ")}</code></header><p>{nextAutomatic.active ? `${researchJobKindLabel(nextAutomatic.job_kind)} for ${nextAutomatic.subject_id || "the next ranked candidate"}.` : nextAutomatic.subject_id ? `${researchJobKindLabel(nextAutomatic.job_kind)} for ${nextAutomatic.subject_id} is next${nextAutomatic.not_before ? ` after ${String(nextAutomatic.not_before).slice(0, 16).replace("T", " ")} UTC` : ""}.` : "The server checks public sources, discovery, research, forecasts, and due settlements."}</p><small>{dispatchBasisLabel(nextAutomatic.dispatch_selection_basis) ? `Why this is next: ${dispatchBasisLabel(nextAutomatic.dispatch_selection_basis)}. ` : ""}{(nextAutomatic.blocked_reasons || []).length ? `${number(nextAutomatic.waiting_count, 0)} candidate jobs remain after duplicate-request coalescence · ${nextAutomatic.blocked_reasons.map((value) => String(value).replaceAll("_", " ")).join(" · ")}` : `Discovery: ${String(discoveryService.status || "awaiting server").replaceAll("_", " ")}${discoveryService.poll_seconds ? ` · checks every ${number(Number(discoveryService.poll_seconds) / 60, 0)} minutes` : ""}`}</small></article>
        <article><header><strong>Evidence in hand</strong><code>{String(edgeMap.alpha_evidence_status || "unestablished").replaceAll("_", " ")}</code></header><p>{number(observationCount, 0)} point-in-time observations · {number(readiness.research_dossier_count, 0)} accepted dossiers · {number(readiness.qualified_discovery_candidate_count, 0)} qualified screens.</p><small>{reviewableEdgeCount} of {number(economicEdges.length, 0)} economic edges are reviewable</small></article>
        <article><header><strong>Awaiting outcomes</strong><code>{settledOutcomes} settled</code></header><p>{pendingSettlements} frozen security-return episodes remain open. {number(economicEdges.filter((row) => !row.reviewable).length, 0)} edge contracts still need later outcomes or identification support.</p><small>{excludedForecastEpisodes ? `${excludedForecastEpisodes} duplicate episode${excludedForecastEpisodes === 1 ? "" : "s"} preserved but excluded · ` : ""}No learned edge can set a portfolio weight</small></article>
        <article><header><strong>Next activation</strong><code>{immediateTransition.blocker || (immediateTransition.blocked_reasons || []).length ? "blocked until due" : "machine-owned"}</code></header><p>{researchJobKindLabel(immediateTransition.job_kind || immediateTransition.transition)}{immediateTransition.subject_id ? ` · ${immediateTransition.subject_id}` : ""}.</p><small>{nextPaperActivation.next_action ? `Operator-owned: ${nextPaperActivation.next_action.replaceAll("_", " ")}` : "No operator action is currently required"}</small></article>
      </div>
      <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Current answer — two separate books</strong><p><b>Household core:</b> {planningWeightText ? `${planningWeightText} is the current assumption-labeled planning scenario; it has not been adopted.` : "No household allocation has been bound."} <b>Active ideas:</b> {activePaperCash == null ? "the paper sleeve is awaiting compilation." : `${pct(activePaperCash, 0)} paper cash while concentrated candidates prove themselves.`}</p><small>{decisionSummary.decision?.text || "No current candidate decision summary is available."}{implementationCandidates.length ? ` Compare ${implementationCandidates.map((row) => row.entity_id).join(" · ")} with the broad-sleeve control in Portfolio.` : ""}</small></div></div>
      <div className="capital-frontier-flow capital-first-minute-loop" aria-label="Investment learning loop">
        <article><span>1</span><Search size={22} /><strong>Discover</strong><p>Scan funds and companies, then explain why each candidate surfaced.</p><code>Click Opportunities</code></article>
        <ArrowRight className="capital-frontier-arrow" />
        <article><span>2</span><FileText size={22} /><strong>Underwrite</strong><p>Test earnings power, price expectations, business strategy, and rivals.</p><code>Click Plays · Strategy frontier</code></article>
        <ArrowRight className="capital-frontier-arrow" />
        <article><span>3</span><Layers3 size={22} /><strong>Allocate</strong><p>Apply risk limits and construct the paper book; cash is the default.</p><code>Click Portfolio</code></article>
        <ArrowRight className="capital-frontier-arrow" />
        <article><span>4</span><Clock3 size={22} /><strong>Settle</strong><p>Freeze decisions, wait for due outcomes, and score after-cost results.</p><code>Click Shadow book</code></article>
        <ArrowRight className="capital-frontier-arrow" />
        <article><span>5</span><GitBranch size={22} /><strong>Learn</strong><p>Compare models and strategy moves only after outcomes arrive.</p><code>Click World models</code></article>
      </div>
      <details className="capital-overview-details"><summary><span><strong>Inspect the current candidate pipeline</strong><small>Research order, evidence state, sealed forecasts, paper eligibility, and the next machine action for each leading company or fund.</small></span></summary><CandidateJourney state={state} /></details>
      <details className="capital-overview-details"><summary><span><strong>Inspect evidence, learning, and activation gates</strong><small>Why the engine is still in cash and what must settle before learned mechanisms can influence paper policy.</small></span></summary>
      <h3>What each engine layer can do now</h3><div className="capital-activation-grid">
        <article><header><strong>Evidence memory</strong><code>{String(pointInTimeEvidence.status || "not captured").replaceAll("_", " ")}</code></header><p>{pointInTimeEvidence.enabled ? `${number(pointInTimeEvidence.source_count, 0)} sources and ${number(pointInTimeEvidence.observation_count, 0)} observations are frozen by ingestion time. Future mechanical replays can use only captures available by their cutoff.` : "Refresh sources to create the first point-in-time archive."}</p><small>Model training knowledge remains outside this archive boundary.</small>{state.paths?.point_in_time_evidence_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.point_in_time_evidence_latest)}><FileText size={14} />Inspect evidence capture</button> : null}</article>
        <article><header><strong>Research allocator</strong><code>{String(researchBudgetTournament.status || "awaiting tournament").replaceAll("_", " ")}</code></header><p>{number(researchBudgetTournament.eligible_work_count, 0)} eligible jobs are compared by decision impact per cost. {number(researchBudgetTournament.complete_independent_block_count, 0)}/{number(researchBudgetTournament.minimum_independent_blocks, 0)} independent blocks are complete.</p><small>{researchBudgetTournament.queue_mutation_authority ? "A reviewed policy may change future scheduling." : "The live queue cannot change from this evidence yet."}</small>{state.paths?.research_budget_tournament_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.research_budget_tournament_latest)}><FileText size={14} />Inspect budget tournament</button> : null}</article>
        <article><header><strong>Strategy-law learner</strong><code>{String(strategyLawInduction.status || "awaiting induction").replaceAll("_", " ")}</code></header><p>{number(strategyLawInduction.candidate_count, 0)} falsifiable law candidates survive logical frontier reduction; {number(strategyLawInduction.eligible_candidate_count, 0)} currently clear causal, transfer, power, and multiplicity gates.</p><small>Eligible laws may influence research priority only; they cannot set weights.</small>{state.paths?.strategy_law_induction_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_law_induction_latest)}><FileText size={14} />Inspect strategy laws</button> : null}</article>
        <article><header><strong>Portfolio activator</strong><code>{String(paperPolicyPath.status || "awaiting policy").replaceAll("_", " ")}</code></header><p>{nextPaperActivation.activation_id ? `Next: ${String(nextPaperActivation.activation_id).replaceAll("_", " ")} — ${String(nextPaperActivation.next_action || "complete the owning contract").replaceAll("_", " ")}.` : "No next activation is recorded."}</p><small>{number(paperPolicyPath.activation_points?.filter((row) => row.status !== "ready").length, 0)} portfolio gates remain uncleared.</small>{state.paths?.allocation_readiness_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.allocation_readiness_latest)}><FileText size={14} />Inspect allocation blockers</button> : null}</article>
      </div>
      <div className="capital-closure-rule"><TrendingUp size={20} /><div><strong>Where an edge could come from</strong><p>Find durable businesses or fund exposures whose prices imply weak outcomes; test which management moves improve operating results in comparable conditions; then allocate only when the expected advantage survives downside, overlap, tax, currency, liquidity, and trading-cost checks. Each claim must win on later data before it can influence paper policy.</p></div></div>
      {economicEdges.length ? <><h3>What the institution has learned so far</h3><div className="capital-activation-grid capital-edge-grid">
        {economicEdges.map((row) => <article key={row.edge_id}><header><strong>{row.label}</strong><code>{String(row.status).replaceAll("_", " ")}</code></header><p>{row.question}</p><small>{number(row.issued_count, 0)} {row.issued_unit || "issued"} · {number(row.settled_count, 0)} {row.settled_unit || "settled"} · {number(row.independent_block_count, 0)} {Number(row.minimum_independent_blocks) > 0 ? `/ ${number(row.minimum_independent_blocks, 0)} independent blocks` : "observed blocks"}{row.control_count == null ? "" : ` · ${number(row.control_count, 0)} controls`}</small><small><strong>Next:</strong> {String(row.next_evidence).replaceAll("_", " ")}</small></article>)}
      </div></> : null}
      {nextExperiment.experiment_id ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Next controlled learning experiment</strong><p>Vary {(nextVariation.varied_component_ids || []).map((value) => String(value).replaceAll("_", " ")).join(" and ")} while holding the information set and outcome contract fixed. Compare {(nextVariation.control_ids || []).join(" → ")} against {(nextVariation.treatment_ids || []).join(" → ")}. {number(nextExperiment.remaining_minimum_blocks, 0)} independent blocks remain before this component can earn credit.</p><small>{String(nextExperiment.status || "awaiting activation").replaceAll("_", " ")} · {nextExperiment.experiment_id}</small></div></div> : null}
      {nextLearningTransition.transition ? <div className="capital-closure-rule"><Clock3 size={20} /><div><strong>How it advances</strong><p>{String(nextLearningTransition.transition).replaceAll("_", " ")}{nextLearningTransition.subject_id ? ` for ${nextLearningTransition.subject_id}` : ""}. {nextLearningTransition.blocker ? `Blocked by ${String(nextLearningTransition.blocker).replaceAll("_", " ")}.` : "The owning scheduler can perform this transition when due."}</p><small>{nextLearningTransition.not_before ? `Not before ${String(nextLearningTransition.not_before).slice(0, 10)}` : "Eligible on the next owning cycle"}</small></div></div> : null}
      </details>
      <div className="capital-boundary"><AlertTriangle size={17} /><div><strong>Current boundary</strong><p>{paperWatches.length} zero-weight decision epoch{paperWatches.length === 1 ? "" : "s"} across {paperWatchNames.length} securit{paperWatchNames.length === 1 ? "y" : "ies"} · {pendingSettlements} frozen forecast episode{pendingSettlements === 1 ? "" : "s"} awaiting settlement · 100% paper cash. Research ranks direct attention, not trades; the workspace has no brokerage authority.</p></div></div>
    </Section>
    <details className="capital-overview-details"><summary><span><strong>Open the detailed five-question decision memo</strong><small>Universe coverage, immediate analyst handoffs, investability gates, the next scheduled transition, and evidence that could change the answer.</small></span></summary><InvestorActionBrief state={state} onPreview={onPreview} /></details>
    <CapitalCycle state={state} busy={busy} onAction={onAction} onPreview={onPreview} />
    <Section eyebrow="Operating state" title="From sources to a constrained paper book"
      description="Refresh public evidence, compile bounded decision policies, inspect the frontier, and preserve every outcome in the golden store."
      actions={<><ActionButton action="sources" busy={busy} onAction={onAction}>Refresh sources</ActionButton><ActionButton action="discover" busy={busy} onAction={onAction} primary>Run discovery</ActionButton></>}>
      <div className="capital-next-action"><TrendingUp size={22} /><div><span>Next decisive action</span><strong>{state.next_action}</strong></div></div>
      <Readiness readiness={readiness} />
      {fixtureCount ? <div className="capital-boundary"><AlertTriangle size={17} /><div><strong>{fixtureCount} fictional reference fixture{fixtureCount === 1 ? "" : "s"}</strong><p>These exercise the complete workflow and are excluded from the operator-decision count.</p></div></div> : null}
    </Section>
    <Section eyebrow="Decision inventory" title="Operator plays" description="Only profiles backed by your declared source receipts appear here as operator decisions.">
      {operatorDecisions.length ? <div className="capital-decision-list">{operatorDecisions.map((row) =>
        <DecisionSummary key={row.decision_id} row={row} onPreview={onPreview} compact />)}</div>
        : <Empty title="No operator play has been compiled" body="The source ledger can be populated now. Add an editable profile that states the thesis, rival mechanism, hurdle, falsifiers, and permitted position actions." />}
    </Section>
    <Section eyebrow="Authority boundary" title="Paper decisions only">
      <div className="capital-authority"><ShieldCheck size={28} /><div><strong>No order or capital authority</strong><p>The compiler can propose and settle paper positions. Brokerage execution remains outside this workspace.</p></div></div>
    </Section>
  </>;
}

function MarketScoutForm({ state, busy, onAction, onPreview }) {
  const latest = state.latest_market_scout || {};
  const population = latest.population || {};
  const catalog = state.market_catalog || {};
  const scheduled = state.scheduled_market_scout_cycle || {};
  const periodicScopes = state.universe_breadth?.active_scout_scope || [];
  const periodicEquities = periodicScopes.find((row) => row.mode === "broad_equity") || {};
  const periodicFunds = periodicScopes.find((row) => row.mode === "broad_fund") || {};
  const enrolledEquities = new Set((state.source_statuses || []).filter((row) => row.adapter === "sec_companyfacts").map((row) => String(row.source_id || "").replace(/^sec_/, "").replace(/_companyfacts$/, "").toUpperCase()));
  const enrolledFunds = new Set((state.watchlists || []).flatMap((row) => row.candidates || []).map((row) => row.entity_id));
  const [query, setQuery] = useState("");
  const submit = (event) => {
    event.preventDefault();
    onAction("scout", { query, max_results: 50, refresh_catalog: !catalog.catalog_sha256 });
  };
  return <Section eyebrow="Optional manual scout" title="Ask for a market, fund, theme, or ticker"
    description="This request creates a one-off shortlist and never steers automatic discovery. The periodic engine independently ranks the broad equity and fund universe before deeper evidence, valuation, strategy, and portfolio gates.">
    <form className="capital-scout-form" onSubmit={submit}>
      <Search size={20} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. Compare international value funds or analyze AAPL" required />
      <button type="submit" className="copy-button primary" disabled={busy}>{busy ? <RefreshCw size={15} className="capital-spin" /> : null}Scout market</button>
      <button type="button" className="copy-button" disabled={busy} onClick={() => onAction("universe-refresh")}>Refresh catalog</button>
    </form>
    <div className="capital-discovery-status">
      <div><span>Broad catalog</span><strong>{number(catalog.security_count, 0)}</strong><small>{catalog.retrieved_at || "refresh once"}</small></div>
      <div><span>Equities</span><strong>{number(catalog.counts_by_entity_kind?.public_equity, 0)}</strong><small>listed identities</small></div>
      <div><span>Funds</span><strong>{number(catalog.counts_by_entity_kind?.public_fund, 0)}</strong><small>ETF identities</small></div>
      <div><span>Periodic equities</span><strong>{number(periodicEquities.returned_count, 0)} / {number(periodicEquities.eligible_count, 0)}</strong><small>diverse research sample</small></div>
      <div><span>Periodic funds</span><strong>{number(periodicFunds.returned_count, 0)} / {number(periodicFunds.eligible_count, 0)}</strong><small>distinct exposure cells</small></div>
      <div><span>Interactive shortlist</span><strong>{number(population.returned_count, 0)} / {number(population.eligible_count, 0)}</strong><small>{population.truncated ? "bounded from current request" : "entire current match set"}</small></div>
    </div>
    {latest.intent ? <div className="capital-intent-strip"><div><span>Current interactive scope</span><strong>{(latest.intent.entity_kinds || []).map((value) => value.replaceAll("_", " ")).join(" + ")}</strong></div><div><span>Capitalization</span><strong>{latest.intent.capitalization || "any"}</strong></div><div><span>Styles to measure</span><strong>{(latest.intent.styles || []).join(", ") || "general"}</strong></div><div><span>Theme match terms</span><strong>{(latest.intent.theme_terms || latest.intent.themes || []).join(", ") || "all"}</strong></div></div> : null}
    {(latest.candidates || []).length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Symbol</th><th>Name</th><th>Kind</th><th>Catalog evidence</th><th>Next analysis</th><th>Action</th></tr></thead><tbody>
      {latest.candidates.slice(0, 50).map((row) => {
        const enrolled = row.entity_kind === "public_equity" ? enrolledEquities.has(row.symbol) : enrolledFunds.has(row.symbol);
        return <tr key={row.security_id}><td><strong>{row.symbol}</strong></td><td>{row.name}</td><td>{row.entity_kind.replaceAll("_", " ")}</td><td>{row.entity_kind === "public_equity" ? `${number(Number(row.market_cap || 0) / 1e9, 1)}B cap · ${row.sector || "sector unavailable"}` : row.one_year_return == null ? "identity only" : `${pct(row.one_year_return)} trailing return`}</td><td><code>{row.next_stage}</code></td><td>{enrolled ? <Status ok>enrolled</Status> : <button type="button" disabled={busy} className="capital-link" onClick={() => row.entity_kind === "public_equity" ? onAction("enroll-equity", { ticker: row.symbol }) : onAction("enroll-fund", { ticker: row.symbol, name: row.name, category: `${latest.intent?.capitalization || "all-cap"} ${(latest.intent?.styles || []).join(" ") || "fund"}` })}>Enrich</button>}</td></tr>;
      })}
    </tbody></table></div> : <Empty title="No broad market request yet" body="The first scout refreshes a catalog of US-listed equities and ETFs, then evaluates every row against the compiled request." />}
    <div className="capital-action-row">
      {latest.run_path ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(latest.run_path)}><FileText size={14} />Inspect typed scout receipt</button> : null}
      {scheduled.cycle_sha256 ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview("research_jobs/scheduled/latest.json")}><FileText size={14} />Inspect scheduled scouts</button> : null}
      <button type="button" className="capital-link" onClick={() => onPreview && onPreview("research_jobs/intents.yaml")}><FileText size={14} />Edit recurring intents</button>
    </div>
  </Section>;
}

function OpportunityFunnel({ state, onPreview, busy, onAction }) {
  const watchlists = state.watchlists || [];
  const candidates = watchlists.flatMap((row) => row.candidates || []);
  const rankedFundCandidates = candidates
    .filter((row) => Number(row.investment_potential?.rank) > 0)
    .sort((left, right) => Number(left.investment_potential.rank) - Number(right.investment_potential.rank));
  const unrankedFundCandidateCount = candidates.length - rankedFundCandidates.length;
  const quality = state.company_quality || [];
  const transitions = state.funnel_transition_receipts || [];
  const transitionCounts = state.funnel_transition_counts || {};
  const decisions = state.decisions || [];
  const transitionCount = (next) => number(transitionCounts[next], transitions.filter((row) => row.to_state === next).length);
  const discovery = state.discovery || {};
  const periodicActivation = discovery.service?.periodic_activation || {};
  const learningSchedule = state.learning_schedule || {};
  const researchBudgetTournament = state.research_budget_tournament || {};
  const rankProgramTournament = state.rank_program_tournament || {};
  const latestRankProgramRun = rankProgramTournament.latest_run || {};
  const latestDiagnosticRankRun = rankProgramTournament.latest_diagnostic_run || {};
  const rankEntryBinding = rankProgramTournament.entry_binding || {};
  const nextLearningAction = learningSchedule.next_action || {};
  const discoveryRun = discovery.latest_run || {};
  const ranked = discoveryRun.candidates || [];
  const qualifiedRanked = ranked.filter((row) => row.screen_status === "qualified").sort((left, right) => (
    (researchRankValue(left) || left.rank || Number.MAX_SAFE_INTEGER)
    - (researchRankValue(right) || right.rank || Number.MAX_SAFE_INTEGER)
  ));
  const evidenceRepairRanked = ranked.filter((row) => row.screen_status !== "qualified");
  const candidateLeaves = (discovery.latest_record || {}).candidate_leaves || {};
  const schedule = discovery.schedule || {};
  const enrichmentCycle = state.latest_enrichment_cycle || {};
  const enrichmentExecution = state.latest_enrichment_execution || {};
  const enrichmentSelected = (enrichmentCycle.candidates || []).filter((row) => row.selection_status === "selected");
  const researchQueue = state.research_job_queue || {};
  const subscriptionResearch = state.subscription_research || {};
  const discoveryResearchHandoff = state.discovery_research_handoff || {};
  const subscriptionQueue = subscriptionResearch.queue || {};
  const subscriptionService = subscriptionResearch.service || {};
  const dailyDispatchBudget = subscriptionResearch.daily_dispatch_budget || {};
  const researchRequests = state.research_requests || [];
  const candidateLane = subscriptionResearch.candidate_lane || {};
  const activationLane = subscriptionResearch.activation_lane || {};
  const fundLane = subscriptionResearch.fund_lane || {};
  const nextCandidateResearch = ranked.find((row) => row.entity_id === candidateLane.next_entity_id);
  const activeSubscriptionJob = Array.isArray(subscriptionResearch.active_jobs)
    ? subscriptionResearch.active_jobs[0]
    : (subscriptionQueue.jobs || []).find((row) => row.status === "claimed");
  const activeSubscriptionPayload = activeSubscriptionJob?.payload || {};
  const activeReassessment = activeSubscriptionJob?.kind === "jaggedthoughts_subscription_reassessment";
  const activeCandidateWebResearch = [
    "jaggedthoughts_subscription_research",
    "jaggedthoughts_subscription_activation_research",
  ].includes(activeSubscriptionJob?.kind);
  const activeCandidateStrategy = activeSubscriptionJob?.kind === "jaggedthoughts_strategy_frontier_research";
  const activeCandidateResearch = activeCandidateWebResearch || activeCandidateStrategy;
  const activeResearchCandidate = activeCandidateResearch
    ? ranked.find((row) => row.entity_id === activeSubscriptionPayload.entity_id)
    : null;
  const activePotentialView = potentialRankView({
    entity_kind: activeSubscriptionPayload.entity_kind || activeResearchCandidate?.entity_kind,
    potential_rank: activeSubscriptionPayload.potential_rank || candidateLane.active_potential_rank,
  });
  const nextPotentialView = potentialRankView({
    entity_kind: nextCandidateResearch?.entity_kind,
    potential_rank: candidateLane.next_potential_rank,
  });
  const activeResearchRequest = researchRequests.find((row) => row.request_sha256 === activeSubscriptionPayload.request_sha256);
  const activeQuestionClosure = activeResearchRequest?.research_question_frontier?.closure || {};
  const activeQuestionEnumeration = activeResearchRequest?.research_question_frontier?.enumeration || {};
  const requestForCandidate = (candidate) => researchRequests.find((row) => (
    row.candidate_sha256 === candidate.candidate_sha256
    || (row.discovery_run_id === discoveryRun.run_id && row.entity_id === candidate.entity_id)
  ));
  const candidateResearchStates = qualifiedRanked.map((row) => candidateResearchStatus(
    row, requestForCandidate(row), activeSubscriptionJob, subscriptionService,
    discoveryResearchHandoff, candidateLane,
  ));
  const candidateResearchCounts = candidateResearchStates.reduce((counts, row) => ({
    ...counts, [row.label]: Number(counts[row.label] || 0) + 1,
  }), {});
  const researchDossiers = state.research_dossiers || [];
  const researchLearning = state.research_learning || {};
  const researchLearningWindow = state.served_projection_limits?.research_learning_rows || {};
  const researchMemory = state.research_memory || {};
  const underwritingIndex = state.underwriting_index || {};
  const payoffForecastRows = (underwritingIndex.candidates || []).filter((row) => row.payoff_forecast);
  const payoffForecastQueued = number(
    (subscriptionResearch.live_queued_by_kind || {}).jaggedthoughts_candidate_payoff_forecast,
    0,
  );
  const marketCoordinates = underwritingIndex.market_context || {};
  const statePricing = state.state_pricing || {};
  const statePriceProposals = statePricing.proposal_audit || {};
  const modeledPayoffGrids = statePricing.modeled_grid_audit || {};
  const grammarEvaluations = statePricing.grammar_evaluation_schedule || {};
  const breadth = state.universe_breadth || {};
  const breadthVerdict = breadth.breadth_verdict || {};
  const broadPotential = state.broad_equity_potential || {};
  const broadPotentialCoverage = broadPotential.coverage || {};
  const broadPotentialTop = broadPotential.top_candidates || [];
  const equityProposals = state.equity_paper_proposals || {};
  const equityProposalRows = equityProposals.rows || [];
  const fundProposalAudit = state.fund_paper_proposals || {};
  const fundProposalRows = fundProposalAudit.rows || [];
  const paperWatchDecisions = state.paper_watch_decisions || [];
  const activeProposalHashes = new Set(paperWatchDecisions.map((row) => row.proposal_sha256));
  const paperWatchPolicy = state.capital_cycle?.policy?.paper_watch_auto_enrollment || {};
  const paperWatchEnrollment = state.capital_cycle?.latest_run?.paper_watch_auto_enrollment || {};
  const proposalBlockers = [...equityProposalRows, ...fundProposalRows]
    .filter((row) => !row.activation_eligible)
    .map((row) => `${row.entity_id}: ${(row.blockers || [row.status || "blocked"]).map((value) => String(value).replaceAll("_", " ")).join(" · ")}`);
  const learningCounts = researchLearning.counts || {};
  const calibrationGate = researchLearning.calibration_gate || {};
  const questionPolicy = researchLearning.research_question_policy_experiment || {};
  const questionRouting = questionPolicy.routing_decision || {};
  const questionOutcomes = state.research_question_policy_outcomes || {};
  const latestRunRequests = researchRequests.filter((row) => row.discovery_run_id === discoveryRun.run_id);
  const sourceFundFrontiers = watchlists.map((row) => row.fund_choice_frontier).filter(Boolean);
  const fundFrontier = sourceFundFrontiers[0] || {};
  const fundAlternatives = new Map(sourceFundFrontiers.flatMap((row) => row.alternatives || []).map((row) => [row.entity_id, row]));
  const mergedFundAlternatives = ranked
    .filter((row) => row.entity_kind === "public_fund")
    .map((candidate) => ({ ...(fundAlternatives.get(candidate.entity_id) || {}), discovery_candidate: candidate }))
    .filter((row) => row.entity_id);
  const fundHoldings = watchlists.find((row) => row.fund_holdings_graph)?.fund_holdings_graph || {};
  const fundLookthroughPlan = state.fund_lookthrough_acquisition_plan || {};
  const fundLookthroughAcquisition = state.fund_lookthrough_acquisition || {};
  const broadFundAcquisition = state.broad_fund_acquisition || {};
  const fundReviews = researchDossiers.filter((row) => row.entity_kind === "public_fund");
  const currentFundReviewCount = mergedFundAlternatives.filter((row) => (
    row.discovery_candidate?.candidate_sha256 && fundReviews.some(
      (review) => review.entity_id === row.entity_id
      && review.candidate_sha256 === row.discovery_candidate?.candidate_sha256,
    )
  )).length;
  const activateFundWatch = (row) => {
    const proposal = row.proposal || {};
    const operatorId = window.prompt("Operator identity for this paper-watch receipt:");
    if (!operatorId) return;
    if (!window.confirm(`${proposal.required_operator_confirmation}\n\nThis creates a zero-weight paper watch. It cannot allocate capital or route an order.`)) return;
    onAction("fund-activate", {
      entity_id: row.entity_id,
      proposal_sha256: proposal.proposal_sha256,
      confirmation: proposal.required_operator_confirmation,
      operator_id: operatorId,
    });
  };
  const activateEquityWatch = (row) => {
    const proposal = row.proposal || {};
    const operatorId = window.prompt("Operator identity for this paper-watch receipt:");
    if (!operatorId) return;
    if (!window.confirm(`${proposal.required_operator_confirmation}\n\nThis records an approved zero-weight watch. Position admission, allocation, and orders remain disabled.`)) return;
    onAction("equity-activate", {
      entity_id: row.entity_id,
      proposal_sha256: proposal.proposal_sha256,
      confirmation: proposal.required_operator_confirmation,
      operator_id: operatorId,
    });
  };
  const stages = [
    ["Observed", state.source_run ? 1 : 0],
    ["Screened", quality.length + candidates.length],
    ["Draft", decisions.filter((row) => row.profile_stage === "draft").length],
    ["Active paper", decisions.filter((row) => row.profile_stage === "active").length],
    ["Portfolio candidate", transitionCount("portfolio_candidate")],
    ["Allocated paper", transitionCount("allocated_paper")],
    ["Settled", decisions.filter((row) => row.settlement_status === "settled").length],
    ["Learned", transitionCount("learned")],
  ];
  return <>
    <Section eyebrow="Investor outcome" title="Find mispriced exposure, then earn the right to allocate"
      description="Describe the opportunity you want. JaggedThoughts scans public funds and companies, separates cheap exposure from factor bets, looks through funds to the underlying businesses, tests whether earnings power and strategic choices can support the price, and routes survivors into a constrained paper portfolio.">
      <div className="capital-activation-grid">
        <article><header><strong>1 · Acquisition priority</strong><code>coverage / cost</code></header><p>Chooses which public-data gaps to hydrate next. It improves screen breadth; it does not rank investments.</p></article>
        <article><header><strong>2 · Investment potential</strong><code>within-lane economics</code></header><p>Equities keep quality-only, expectations-only, and balanced ranks on the same evidence-complete population, then interleave their ordinal leaders. Funds retain valuation, factor/risk, cost, and fit comparisons only inside the same implementation sleeve.</p></article>
        <article><header><strong>3 · Research priority</strong><code>bounded residuals</code></header><p>Orders surviving valuation, durability, strategy, and evidence gaps for deeper work. It does not estimate expected return.</p></article>
        <article><header><strong>4 · Portfolio utility</strong><code>account-specific fit</code></header><p>Applies risk, correlation, tax, liquidity, and horizon constraints after underwriting. It can reject the highest research rank.</p></article>
      </div>
      <div className="capital-closure-rule"><Search size={20} /><div><strong>Goldilocks research handoff</strong><p>Bulk SEC facts, prices, and fund data rank the broad population first. Fixed doctrine lenses preserve quality–valuation disagreement without using web prose. Only qualified survivors enter the protected subscription/web lane in interleaved research-rank order; the agent resolves named residuals and the kernel rechecks its dossier.</p></div></div>
      <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Potential-rank tournament</strong><p>{latestRankProgramRun.run_id ? `${number(latestRankProgramRun.lanes?.length, 0)} comparable lanes are frozen on the same full pre-truncation population; ${number(latestRankProgramRun.deferred_lanes?.length, 0)} thin lanes are deferred.` : "The next discovery compiler will freeze the first paired rank block."} {latestRankProgramRun.programs?.length ? `Programs: ${latestRankProgramRun.programs.map((row) => String(row.program_id).replaceAll("_", " ")).join(" · ")}. ` : ""}Each applicable program settles on 365-day adjusted-price returns, rank calibration, top-choice regret, and pairwise ordering. Eight independent blocks are required. {latestDiagnosticRankRun.run_id ? `${number(latestDiagnosticRankRun.horizon_days, 0)}-day diagnostic block ${latestDiagnosticRankRun.run_id} is also sealed.` : "The shorter diagnostic block is awaiting its first seal."} {number(rankEntryBinding.pending_lane_count, 0)} lane windows await their first common post-seal price; {number(rankEntryBinding.bound_lane_count, 0)} are bound. Next: {String(rankProgramTournament.next_activation || "open first paired blocks").replaceAll("_", " ")}. Diagnostic results cannot recommend policy or change capital.</p></div>{latestRankProgramRun.run_path ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(latestRankProgramRun.run_path)}><FileText size={14} />Inspect rank block</button> : null}</div>
      <div className="capital-boundary"><AlertTriangle size={17} /><div><strong>Edge hypothesis under prospective evaluation</strong><p>The proposed advantage is the combined expectations, durability, factor/state-pricing, and strategy-choice view. The workbench does not claim established alpha until frozen paper decisions outperform declared comparators across enough independent periods.</p></div></div>
    </Section>
    <Section eyebrow="Typed underwriting" title="One opportunity view, without blending unlike return concepts"
      description="The join qualifies research priorities only. Security-implied cash-flow return, factor-required return, market ERP, earnings-yield spreads, and implied growth keep distinct identities and evidence lineages.">
      <div className="capital-discovery-status">
        <div><span>Candidates joined</span><strong>{number(underwritingIndex.candidate_count, 0)}</strong><small>{number(underwritingIndex.ranking_eligible_count, 0)} signed-rank eligible · {number(underwritingIndex.underwriting_coordinate_complete_count, 0)} coordinate-complete · {underwritingIndex.current ? "current" : "refresh due"}</small></div>
        <div><span>Cash-flow implied ERP</span><strong>{pct(marketCoordinates.primary_cash_flow_implied_erp?.value)}</strong><small>total index cash-flow return less Treasury</small></div>
        <div><span>Payoff forecasts</span><strong>{number(underwritingIndex.forecast_return_aware_count, 0)} authored</strong><small>{payoffForecastQueued} queued · {number(underwritingIndex.conditional_payoff_aware_count, 0)} price-consistency grids · {number(underwritingIndex.state_price_aware_count, 0)} market-state identified</small></div>
        <div><span>Authority</span><strong>research priority</strong><small>never expected return or position size</small></div>
      </div>
      {payoffForecastRows.length ? <div className="capital-tournament-list">{payoffForecastRows.slice(0, 6).map((row) => { const forecast = row.payoff_forecast || {}; const expected = forecast.expected_active_return_interval || {}; const downside = forecast.underperformance_probability_interval || {}; const diagnostics = forecast.uncertainty_diagnostics || {}; const width = number(expected.high, 0) - number(expected.low, 0); return <article key={forecast.forecast_result_sha256}><Activity size={23} /><div><strong>{row.entity_id} · authored payoff forecast</strong><p>Expected active return {pct(expected.low, 1)} to {pct(expected.high, 1)} vs {forecast.comparator_entity_id} · underperformance probability {pct(downside.low, 0)} to {pct(downside.high, 0)}</p><span>{number(forecast.horizon_days, 0)}-day horizon · worst state {pct(forecast.worst_case_active_return, 1)} · frozen {String(forecast.information_cutoff || "").slice(0, 10)}{diagnostics.next_evidence_target ? ` · research next: ${String(diagnostics.next_evidence_target).replaceAll("_", " ")}` : ""}</span></div><Status ok={width <= 0.5}>{width <= 0.5 ? "bounded challenger" : "too wide for sizing"}</Status></article>; })}</div> : <div className="capital-empty"><Activity size={22} /><div><strong>No candidate payoff forecast yet</strong><p>The subscription author must freeze thesis, rival, and residual worlds before deterministic expected-return bounds can enter underwriting.</p></div></div>}
      {payoffForecastRows.some((row) => number(row.payoff_forecast?.expected_active_return_interval?.high, 0) - number(row.payoff_forecast?.expected_active_return_interval?.low, 0) > 0.5) ? <div className="capital-boundary"><AlertTriangle size={17} /><div><strong>Forecast uncertainty blocks sizing</strong><p>The current authored interval is too wide to discriminate a paper weight. Narrow the state payoff, comparator, and probability intervals with new evidence; never substitute the midpoint.</p></div></div> : null}
      {(marketCoordinates.yield_spread_diagnostics || []).length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Diagnostic</th><th>Spread</th><th>Meaning</th></tr></thead><tbody>{marketCoordinates.yield_spread_diagnostics.map((row) => <tr key={row.metric_id}><td><code>{String(row.metric_id).replaceAll("_", " ")}</code></td><td>{pct(row.value, 2)}</td><td>cheap relative-yield diagnostic; not an expected-return estimate</td></tr>)}</tbody></table></div> : null}
      <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Method identity</strong><p>The current research rank can combine evidence availability and typed screens, but it cannot average ERP, earnings yield, factor return, and security IRR into a single claimed return. Every candidate retains its own coordinates and gaps.</p></div>{state.paths?.underwriting_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.underwriting_latest)}><FileText size={14} />Inspect underwriting index</button> : null}</div>
      <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Payoff-state pricing</strong><p>{statePriceProposals.valid_proposal_count ? `${number(statePriceProposals.valid_proposal_count, 0)} valuation envelopes are ready for payoff-state authorship. ` : ""}{statePricing.next_activation || "Declare exhaustive payoff states, their future asset payoffs, observed prices, and a numeraire."} Risk-neutral probabilities come from normalized Arrow prices; physical probabilities are never inferred from historical frequencies.</p></div>{state.paths?.state_price_proposal_audit ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.state_price_proposal_audit)}><FileText size={14} />Inspect authoring queue</button> : null}</div>
      <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Formal valuation residuals</strong><p>The valuation grammar derived {number(modeledPayoffGrids.eligible_grid_count, 0)} conditional 10-year payoff grids. {number(modeledPayoffGrids.positive_state_price_count, 0)} reconcile with observed price; {number(underwritingIndex.conditional_payoff_aware_count, 0)} current candidate contract is materialized in underwriting. Market-state prices remain identified for {number(underwritingIndex.state_price_aware_count, 0)} candidates. Conditional grids are price-consistency checks, not physical probabilities or return forecasts.</p></div>{state.paths?.modeled_payoff_grid_audit ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.modeled_payoff_grid_audit)}><FileText size={14} />Inspect formal residuals</button> : null}</div>
      <div className="capital-closure-rule"><Activity size={20} /><div><strong>Future-cohort grammar tournament</strong><p>{number(grammarEvaluations.evaluation_count, 0)} one-change revisions are scheduled against the same future company cohort; {number(grammarEvaluations.ready_count, 0)} are executable now. The control grammar remains frozen until a later source epoch and an explicit revision manifest exist.</p></div></div>
      <div className="capital-closure-rule"><AlertTriangle size={20} /><div><strong>Universe breadth</strong><p>The public catalog contains {number(breadth.source_universe?.eligible_count, 0)} eligible securities, while deep analysis currently covers {pct(breadthVerdict.deep_screen_fraction_of_eligible_catalog, 2)}. Current verdict: {String(breadthVerdict.verdict || "audit unavailable").replaceAll("_", " ")}. Unknown style or sector fields remain unknown rather than guessed.</p></div></div>
      {broadFundAcquisition.enabled ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Rotating fund-cell coverage</strong><p>{number(broadFundAcquisition.ready_group_count, 0)} of {number(broadFundAcquisition.comparable_peer_group_count, 0)} exact ETF peer cells have two comparison-ready funds. {number(broadFundAcquisition.residual_peer_group_count, 0)} comparable cells remain, alongside {number(broadFundAcquisition.singleton_cell_count, 0)} singleton cells.</p><small>Next: {(broadFundAcquisition.selected_peer_groups || []).map((group) => `${(group.entity_ids || []).join("/")} · ${String(group.peer_group_id || "unclassified cell").replaceAll("_", " ")}`).join(" · ") || String(broadFundAcquisition.next_activation || "await next acquisition cycle").replaceAll("_", " ")}</small></div>{state.paths?.broad_fund_acquisition_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.broad_fund_acquisition_latest)}><FileText size={14} />Inspect fund coverage plan</button> : null}</div> : null}
      <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Paper activation membrane</strong><p>{number(equityProposals.proposal_count, 0)} qualified equities and {number(fundProposalAudit.proposal_count, 0)} funds have exact evidence-bound, cash-only proposals; {number(Number(equityProposals.eligible_count || 0) + Number(fundProposalAudit.eligible_count || 0), 0)} currently clear every activation blocker. {paperWatchPolicy.enabled ? `The standing policy enrolls at most ${number(paperWatchPolicy.max_new_per_cycle, 0)} current proposals per cycle as zero-weight watches.` : "Review remains manual."} A proposal never creates a position or order.</p></div>{state.paths?.equity_paper_proposals_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.equity_paper_proposals_latest)}><FileText size={14} />Inspect proposals</button> : null}</div>
      {proposalBlockers.length ? <div className="capital-boundary"><AlertTriangle size={17} /><div><strong>Current proposal blockers</strong><p>{proposalBlockers.join(" · ")}</p></div></div> : null}
    </Section>
    <Section eyebrow="Broad deterministic screen" title="Rank preliminary economic potential before spending research"
      description="A cross-sectional SEC screen ranks complete, investable companies on sector-relative cheapness, earnings power, cash quality, and balance-sheet strength. Diversity closure chooses which high-potential names enter bounded web and primary-source underwriting. Deep valuation produces the current within-lane research rank; qualitative evidence may validate, veto, or reopen a candidate but cannot silently rescore it.">
      <div className="capital-discovery-status">
        <div><span>Catalog equities</span><strong>{number(broadPotentialCoverage.catalog_common_equity_count, 0)}</strong><small>{number(broadPotentialCoverage.ticker_cik_join_count, 0)} mapped to SEC identities</small></div>
        <div><span>Comparable</span><strong>{number(broadPotentialCoverage.fully_comparable_ranked_count, 0)}</strong><small>complete aligned accounting</small></div>
        <div><span>Investable screen</span><strong>{number(broadPotentialCoverage.investable_ranked_count, 0)}</strong><small>market-cap and liquidity floor</small></div>
        <div><span>High potential</span><strong>{number(broadPotential.potential_candidate_count, 0)}</strong><small>top decile sent to research allocation</small></div>
        <div><span>Selected next</span><strong>{number(broadPotential.selected_count, 0)}</strong><small>diversity closure inside high potential only</small></div>
        <div><span>Authority</span><strong>research priority</strong><small>not expected return or a buy recommendation</small></div>
      </div>
      {broadPotentialTop.length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Interleaved rank</th><th>Company</th><th>Potential order</th><th>Doctrine ranks</th><th>Research must resolve</th></tr></thead><tbody>{broadPotentialTop.slice(0, 10).map((row) => <tr key={row.security_id}><td>#{number(row.rank, 0)}</td><td><strong>{row.symbol}</strong></td><td>{number(row.research_priority_score, 3)}<small>ordinal research priority</small></td><td><small>{Object.entries(row.doctrine_ranks || {}).map(([name, rank]) => `${name.replaceAll("_", " ")} #${rank}`).join(" · ")}</small></td><td><small>{(row.unresolved_residuals || []).map((value) => String(value).replaceAll("_", " ")).join(" · ")}</small></td></tr>)}</tbody></table></div> : <Empty title="Potential screen is awaiting its first SEC frame" body="The scheduled discovery service will compile the bounded bulk screen before spending qualitative research." />}
      <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Goldilocks research split</strong><p>Deterministic bulk data narrows the universe. Public-source web research is reserved for the surviving residuals: multi-period durability, debt and dilution, market-implied growth, and company strategy. The dossier can admit, veto, or force re-underwriting of that frozen potential hypothesis; only later settled rank tournaments may justify changing the scoring policy.</p></div>{state.paths?.sec_frame_screen_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.sec_frame_screen_latest)}><FileText size={14} />Inspect potential screen</button> : null}</div>
      <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Rank-to-research epoch {discoveryResearchHandoff.status || "blocked"}</strong><p>{discoveryResearchHandoff.discovery_run_id || "No current handoff receipt"}. Candidate providers are claimable only when this receipt is complete and bound to the current discovery identity.</p></div><Status ok={discoveryResearchHandoff.status === "complete"}>{discoveryResearchHandoff.status || "missing"}</Status></div>
    </Section>
    <MarketScoutForm state={state} busy={busy} onAction={onAction} onPreview={onPreview} />
    <Section eyebrow="Bounded active search" title="Leaf-subscribed research funnel"
      description="Saved scouts feed a diversity-aware acquisition policy. The deterministic kernel leases source jobs and emits immutable request leaves. A separately leased subscription agent may gather public qualitative evidence and submit a typed dossier; the kernel revalidates it before any lifecycle change. The priority is an uncalibrated acquisition score, never an expected-return claim."
      actions={<ActionButton action="enrichment-run" busy={busy} onAction={onAction} primary>Run enrichment cycle</ActionButton>}>
      <div className="capital-discovery-status">
        <div><span>Candidate pool</span><strong>{number(enrichmentCycle.candidate_count, 0)}</strong><small>deduplicated scout matches</small></div>
        <div><span>Selected</span><strong>{number(enrichmentCycle.selected_count, 0)}</strong><small>{number(enrichmentCycle.budget_usage?.estimated_total_source_calls, 0)} estimated calls</small></div>
        <div><span>Evidence ready</span><strong>{number(enrichmentExecution.evidence_ready_count, 0)}</strong><small>{number(enrichmentExecution.blocked_count, 0)} typed blocks</small></div>
        <div><span>Enrichment jobs</span><strong>{number(researchQueue.stats?.total, 0)}</strong><small>{Object.entries(researchQueue.stats?.by_status || {}).map(([key, value]) => `${key} ${value}`).join(" · ") || "queue empty"}</small></div>
        <div><span>Agent requests</span><strong>{number(researchRequests.length, 0)}</strong><small>immutable evidence handoffs</small></div>
        <div><span>Research consumer</span><strong>{subscriptionService.status || (subscriptionResearch.enabled ? "awaiting process" : "disabled")}</strong><small>{Object.entries(subscriptionQueue.by_status || {}).map(([key, value]) => `${key} ${value}`).join(" · ") || "queue empty"}</small><small>{number(dailyDispatchBudget.used, 0)}/{number(dailyDispatchBudget.limit, 0)} subscription dispatches · {number(subscriptionResearch.terminal_completions_today, 0)} terminal transitions</small></div>
      </div>
      {activeSubscriptionJob ? <div className="capital-next-action"><Search size={22} /><div><span>{activeCandidateWebResearch ? "Candidate web research now" : activeCandidateStrategy ? "Candidate strategy synthesis now" : activeReassessment ? "Evidence revalidation now" : "Institutional learning now"}</span><strong>{activeSubscriptionPayload.entity_id || String(activeSubscriptionJob.kind || "research").replaceAll("_", " ")}</strong><code>{researchJobKindLabel(activeSubscriptionJob.kind)}</code><small>{activeCandidateResearch ? `${activePotentialView.value ? `frozen potential #${activePotentialView.value} ${activePotentialView.detail}` : "unranked evidence repair"}${activeQuestionClosure.frontier_count ? ` · ${activeQuestionClosure.frontier_count} of ${activeQuestionEnumeration.program_count} formal question programs survived closure` : ""} · ${activeCandidateWebResearch ? "resolving frozen evidence residuals with public web sources" : "compiling strategy choices from the admitted dossier; no new web search"}` : activeReassessment ? "maintenance lane for a changed public source; not a newly ranked opportunity" : researchJobKindLabel(activeSubscriptionJob.kind)}</small></div></div> : null}
      {candidateLane.next_entity_id ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>{candidateLane.currently_serving ? `Candidate lane currently serving ${candidateLane.active_entity_id}` : candidateLane.due_next_claim ? "Candidate research reserved next" : "Candidate-lane leader"}</strong><p>Next candidate: {candidateLane.next_entity_id}{candidateLane.next_research_rank ? ` · research #${candidateLane.next_research_rank}` : ""}{nextPotentialView.value ? ` · within-lane potential #${nextPotentialView.value} ${nextPotentialView.detail}` : ""} · next job: {researchJobKindLabel(candidateLane.next_kind)} · scheduling priority {number(candidateLane.next_queue_priority, 0)}. The candidate and typed residual are fixed before agent invocation; the agent cannot choose the candidate or alter the rank.</p><small>{number(candidateLane.waiting_count, 0)} claimable candidates waiting · at most {number(candidateLane.max_consecutive_non_candidate_calls, 0)} consecutive non-candidate research claims · live {subscriptionResearch.live_observed_at || "status pending"}</small></div></div> : null}
      {activationLane.next_entity_id ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>{activationLane.currently_serving ? "Activation research is running" : activationLane.due_next_claim ? "Activation research reserved next" : "Next activation repair"}</strong><p>Next queued: {activationLane.next_entity_id} · {number(activationLane.waiting_count, 0)} activations waiting · fresh jobs reserve {number(activationLane.fresh_dispatch_budget_units, 2)} subscription calls for the sealed forecast and its assigned public-source search.</p><small>At most {number(activationLane.max_consecutive_non_activation_calls, 0)} non-activation calls may pass while this lane waits. This transition can update research evidence only; it cannot allocate capital.</small></div></div> : null}
      {fundLane.next_entity_id ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>{fundLane.currently_serving ? `Fund implementation research is serving ${fundLane.active_entity_id}` : fundLane.blocked_by_frozen_successor && fundLane.cadence_overdue ? "Fund research follows the frozen successor" : fundLane.due_next_claim ? "Fund research reserved next" : "Fund research lane leader"}</strong><p>Next fund: {fundLane.next_entity_id} · {number(fundLane.waiting_count, 0)} current requests waiting · cross-sleeve scheduling priority {number(fundLane.next_queue_priority, 0)}.</p><small>{fundLane.cadence_overdue ? "The fund cadence is due. " : ""}After an exact frozen successor, at most {number(fundLane.max_consecutive_non_fund_calls, 0)} other provider calls may pass while this lane waits. The engine researches fees, holdings, liquidity, mechanics, and tax evidence; it cannot admit a fund or allocate capital.</small></div></div> : null}
      {periodicActivation.schema ? <div className="capital-closure-rule"><Clock3 size={20} /><div><strong>Next autonomous activation</strong><p>{periodicActivation.next_activation?.work_id || periodicActivation.next_activation?.kind || "next discovery epoch"} · {periodicActivation.next_activation?.at || "when due"}. {(periodicActivation.blocked_activation?.reasons || []).length ? `Waiting on ${periodicActivation.blocked_activation.reasons.map((value) => String(value).replaceAll("_", " ")).join(" · ")}.` : "No recorded activation blocker."}</p></div><Status ok={!periodicActivation.blocked_activation}>{periodicActivation.status || "waiting"}</Status></div> : null}
      {nextLearningAction.work_id ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Last compiled scheduler leader</strong><p>{nextLearningAction.entity_id || "cross-market"} · {String(nextLearningAction.action_class || "research").replaceAll("_", " ")} · lane rank #{number(nextLearningAction.lane_rank, 0)} of {number(nextLearningAction.lane_size, 0)} · {nextLearningAction.ordering_basis === "candidate_potential_rank" ? "candidate potential lane" : "institutional-learning information-yield lane"}. Snapshot {learningSchedule.generated_at || "time unavailable"}; the live cadence preserves exact frozen successors and bounds service for candidate, activation, and fund research.</p></div>{state.paths?.learning_schedule_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.learning_schedule_latest)}><FileText size={14} />Inspect schedule</button> : null}</div> : null}
      {researchBudgetTournament.enabled ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Research-budget tournament</strong><p>{number(researchBudgetTournament.eligible_work_count, 0)} eligible jobs · {(researchBudgetTournament.arms || []).map((arm) => `${String(arm.policy_id).replaceAll("_", " ")}: ${String(arm.selected?.[0]?.work_id || "pending").split(":").at(-1)?.slice(0, 12)}`).join(" · ")}. {number(researchBudgetTournament.complete_independent_block_count, 0)}/{number(researchBudgetTournament.minimum_independent_blocks, 0)} complete blocks; the live scheduler remains unchanged.</p><small>{researchBudgetTournament.exact_blocker || "Decision impact per cost must survive paired and multiplicity gates."}</small></div>{state.paths?.research_budget_tournament_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.research_budget_tournament_latest)}><FileText size={14} />Inspect tournament</button> : null}</div> : null}
      {enrichmentSelected.length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Rank</th><th>Security</th><th>Acquisition score</th><th>Diversity</th><th>Budget</th><th>Lifecycle</th><th>Evidence handoff</th></tr></thead><tbody>
        {enrichmentSelected.map((row) => {
          const request = researchRequests.find((item) => item.entity_id === row.symbol && item.cycle_sha256 === enrichmentCycle.cycle_sha256);
          return <tr key={row.security_id}><td>#{row.selection_rank}</td><td><strong>{row.symbol}</strong><small>{row.name} · {row.entity_kind.replaceAll("_", " ")}</small></td><td>{number(row.acquisition_priority, 3)}<small>routing only</small></td><td>{number(row.marginal_diversity, 3)}</td><td>{number(row.cost?.incremental_source_calls, 0)} calls · {number(row.cost?.research_minutes, 0)}m</td><td><Status ok={Boolean(request)}>{request?.lifecycle_stage || enrichmentExecution.status || "queued"}</Status></td><td>{request?.request_path ? <div className="capital-action-row"><button type="button" className="capital-link" onClick={() => onPreview && onPreview(request.request_path)}><FileText size={14} />Research request</button>{request.dossier_path ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(request.dossier_path)}><FileText size={14} />Dossier</button> : null}</div> : <span>{row.selection_reason}</span>}</td></tr>;
        })}
      </tbody></table></div> : <Empty title="No bounded enrichment cycle yet" body="Run the cycle to select across the saved company and fund scouts under source-call, research-time, diversity, and sector budgets." />}
      <div className="capital-action-row">
        {enrichmentCycle.cycle_sha256 ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview("research_jobs/enrichment/latest.json")}><FileText size={14} />Inspect selection receipt</button> : null}
        {enrichmentExecution.execution_sha256 ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview("research_jobs/enrichment/latest_execution.json")}><FileText size={14} />Inspect execution</button> : null}
        <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths?.enrichment_policy || "research_jobs/enrichment_policy.yaml")}><FileText size={14} />Edit budgets</button>
      </div>
    </Section>
    <Section eyebrow="Prospective learning" title="Acquisition score → research yield → paper consequence"
      description="Every selected job keeps its frozen acquisition score, cost, dossier transition, downstream paper identity, and later benchmark-relative settlement. Pending work is censored; it is not scored as failure.">
      <div className="capital-discovery-status">
        <div><span>Requests</span><strong>{number(learningCounts.requests, 0)}</strong><small>selected cohort</small></div>
        <div><span>Dossiers</span><strong>{number(learningCounts.dossiers, 0)}</strong><small>{pct(researchLearning.descriptive_rates?.dossier_submission_rate)} submitted</small></div>
        <div><span>Paper activations</span><strong>{number(learningCounts.paper_activations, 0)}</strong><small>{paperWatchPolicy.enabled ? `${number(paperWatchEnrollment.new_activation_count, 0)} added by standing policy last cycle` : "manual transition"}</small></div>
        <div><span>Settled pairs</span><strong>{number(learningCounts.settled_score_pairs, 0)} / {number(calibrationGate.minimum_settled_pairs, 0)}</strong><small>before refit review</small></div>
        <div><span>Policy refit</span><strong>{calibrationGate.policy_refit_allowed ? "reviewable" : "disabled"}</strong><small>{String(researchLearning.status || "awaiting cohort").replaceAll("_", " ")}</small></div>
        <div><span>Question-policy ITT units</span><strong>{number(questionPolicy.valid_assignment_unit_count, 0)}</strong><small>{number(questionPolicy.settled_itt_unit_count, 0)} settled · {number(questionPolicy.censored_due_unit_count, 0)} due-censored</small></div>
        <div><span>Question-policy outcome clock</span><strong>{number(questionOutcomes.eligible_count, 0)} eligible</strong><small>{number(questionOutcomes.action_count, 0)} fixed probes · {number(questionOutcomes.abstention_count, 0)} abstentions · {number(questionOutcomes.settled_count, 0)} settled</small></div>
        <div><span>Next research routing</span><strong>{questionRouting.recommended_arm ? questionRouting.recommended_arm.replaceAll("_", " ") : "balanced audit"}</strong><small>{number(questionRouting.reviewed_units_per_arm, 0)} reviewed per arm · p {questionRouting.randomization_inference?.p_value ?? "pending"} · {pct(questionRouting.audit_share)} continuing audit</small></div>
      </div>
      {(researchLearning.rows || []).length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Candidate</th><th>Question policy</th><th>Acquisition score</th><th>Research budget</th><th>Lifecycle</th><th>Paper excess return</th></tr></thead><tbody>
        {researchLearning.rows.slice().reverse().map((row) => <tr key={row.request_id}><td><strong>{row.entity_id}</strong><small>{row.entity_kind?.replaceAll("_", " ")}</small></td><td><code>{row.research_policy_arm ? `${row.research_policy_arm.replaceAll("_", " ")}${row.research_routing_mode === "learned_operational" ? " · learned" : ""}` : "common contract"}</code><small>{row.research_question || "outside randomized research routing"}</small>{row.question_program_atoms?.length ? <small>AST · {row.question_program_atoms.join(" + ")}</small> : null}</td><td>{number(row.acquisition_priority, 3)}<small>routing proxy</small></td><td>{number(row.incremental_source_calls, 0)} calls · {number(row.estimated_research_minutes, 0)}m</td><td><Status ok={row.dossier_submitted || row.prior_dossier_coverage_reused}>{String(row.lifecycle_stage).replaceAll("_", " ")}</Status>{row.question_resolution_rate != null ? <small>{pct(row.question_resolution_rate)} question atoms resolved · {pct(row.question_primary_evidence_rate)} with primary evidence</small> : null}{row.prior_dossier_coverage_reused ? <small>qualitative evidence reused; current valuation remains local</small> : null}</td><td>{row.paper_settled ? pct(row.net_excess_return, 2) : "censored"}</td></tr>)}
      </tbody></table>{number(researchLearningWindow.total, 0) > number(researchLearningWindow.served, 0) ? <small>Showing the latest {number(researchLearningWindow.served, 0)} of {number(researchLearningWindow.total, 0)} immutable learning rows.</small> : null}</div> : <Empty title="No prospective acquisition cohort" body="Run bounded enrichment to freeze the first score-to-outcome rows." />}
      <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Calibration gate</strong><p>{calibrationGate.boundary || "A frozen prospective cohort and later paper settlements are required before acquisition-policy tuning."}</p></div></div>
      <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Research-question experiment</strong><p>{questionPolicy.boundary || "Each future candidate leaf receives a fixed independent research-policy assignment. Only due incremental-return outcomes may change later routing; half of later candidates remain an audit arm."}</p></div></div>
    </Section>
    <Section eyebrow="Compounding research memory" title="Research once, revoke on change, challenge across companies"
      description="Accepted dossiers atomize documents, choices, and reinforcing edges. Unchanged monitored evidence can cover a later quantitative candidate epoch without another full research call. A changed digest revokes that bridge and leases a local reassessment. Choice graphs are canonicalized up to node naming so repeated structures can generate cross-company challenges; topology alone never earns economic or causal status.">
      <div className="capital-discovery-status">
        <div><span>Source documents</span><strong>{number(researchMemory.source_count, 0)}</strong><small>content-addressed evidence</small></div>
        <div><span>Mechanism claims</span><strong>{number(researchMemory.mechanism_claim_count, 0)}</strong><small>choice-level support edges</small></div>
        <div><span>Accepted dossiers</span><strong>{number(researchMemory.dossier_count, 0)}</strong><small>kernel-admitted</small></div>
        <div><span>Evidence bridges</span><strong>{number(researchMemory.research_coverage_count, 0)}</strong><small>full rereads avoided</small></div>
        <div><span>Strategy phenotypes</span><strong>{number(researchMemory.strategy_phenotype_count, 0)}</strong><small>{number(researchMemory.cross_entity_strategy_phenotype_count, 0)} recur across entities</small></div>
        <div><span>Reused sources</span><strong>{number(researchMemory.reused_source_count, 0)}</strong><small>cited by multiple dossiers</small></div>
        <div><span>Monitor subscriptions</span><strong>{number(researchMemory.monitor_subscription_count, 0)}</strong><small>material-source triggers</small></div>
        <div><span>Source changes</span><strong>{number(researchMemory.source_change_event_count, 0)}</strong><small>content-digest events</small></div>
        <div><span>Local reopens</span><strong>{number(researchMemory.reopen_request_count, 0)}</strong><small>{number(researchMemory.reassessment_count, 0)} reassessed</small></div>
      </div>
      {(researchMemory.sources || []).length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Document</th><th>Kind</th><th>Dossiers</th><th>Mechanism claims</th><th>Affected neighborhood</th></tr></thead><tbody>
        {researchMemory.sources.slice(0, 12).map((row) => <tr key={row.source_leaf}><td><strong>{row.title}</strong><small>{row.publisher} · {row.published_at}</small></td><td><code>{row.source_kind}</code></td><td>{row.dossier_count}</td><td>{row.mechanism_claim_count}</td><td>{row.affected_dossier_leaves.length} dossiers · {row.affected_mechanism_claim_leaves.length} claims</td></tr>)}
      </tbody></table></div> : <Empty title="No atomized research evidence yet" body="The next accepted dossier will create source-document and strategy-mechanism leaves with reverse support edges." />}
      {(researchMemory.strategy_phenotypes || []).length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Choice-system phenotype</th><th>Topology</th><th>Entities</th><th>Transfer state</th></tr></thead><tbody>
        {researchMemory.strategy_phenotypes.map((row) => <tr key={row.phenotype_id}><td><code>{row.phenotype_id}</code><small>{row.next_question}</small></td><td>{row.signature.node_count} choices · {row.signature.edge_count} typed edges<small>{row.unresolved_edge_count ? `${row.unresolved_edge_count} legacy endpoints unresolved` : row.signature.identity_method.replaceAll("_", " ")}</small></td><td>{row.entity_ids.join(", ")}</td><td><Status ok={row.cross_entity}>{row.cross_entity ? "challenge ready" : "awaiting recurrence"}</Status></td></tr>)}
      </tbody></table></div> : null}
      <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Current activation</strong><p>{researchMemory.activation || "A changed exact document can reopen only its dependent research neighborhood."}</p></div></div>
    </Section>
    <Section eyebrow="Periodic discovery" title="Process-owned opportunity engine"
      description="While the local workbench server is running, its due-check thread evaluates every saved broad-market intent and applies bounded acquisition and maintenance-refresh budgets. Sources outside a bounded refresh retain their last admissible point-in-time observations under typed age gates; failed dependencies block their candidates. SQLite leases survive worker restarts; the timer itself stops with the server process."
      actions={<ActionButton action="discover" busy={busy} onAction={onAction} primary>Run discovery now</ActionButton>}>
      <div className="capital-discovery-status">
        <div><span>Due-check owner</span><strong>{discovery.service?.status || "starts with local server"}</strong><small>{discovery.service?.last_action || "awaiting heartbeat"} · process-local</small></div>
        <div><span>Cadence</span><strong>{number(schedule.cadence_hours, 0)}h</strong><small>next {schedule.next_due_at || "now"}</small></div>
        <div><span>Latest scope</span><strong>{discoveryRun.frontier_closure?.scope_closed ? "closed" : "incomplete"}</strong><small>{discoveryRun.candidate_count || 0} represented · evidence {discoveryRun.as_of || "unknown"} · compiled {discoveryRun.completed_at || "unknown"}</small></div>
        <div><span>Selected refresh</span><strong>{discoveryRun.evidence_refresh?.complete ? "complete" : "partial"}</strong><small>{(discoveryRun.evidence_refresh?.failed_sources || []).length} failed · {(discoveryRun.evidence_refresh?.not_scheduled_source_ids || []).length} outside this epoch</small></div>
        <div><span>Research requests</span><strong>{latestRunRequests.length}</strong><small>{discoveryRun.qualified_count || 0} qualified for draft</small></div>
        <div><span>Bounded web queue</span><strong>{number(candidateResearchCounts.queued, 0)} queued</strong><small>{number(candidateResearchCounts.running, 0)} running · {number(candidateResearchCounts.blocked, 0)} blocked · {number(Number(candidateResearchCounts["dossier accepted"] || 0) + Number(candidateResearchCounts["evidence reused"] || 0), 0)} covered</small></div>
        <div><span>Research consumer</span><strong>{String(subscriptionService.status || "not running").replaceAll("_", " ")}</strong><small>{number(subscriptionQueue.by_status?.queued, 0)} current queued · {number(subscriptionQueue.by_status?.dead_letter, 0)} retained terminal ledger rows</small></div>
        <div><span>ETF cells covered</span><strong>{number(broadFundAcquisition.ready_group_count, 0)} / {number(broadFundAcquisition.comparable_peer_group_count, 0)}</strong><small>{number(broadFundAcquisition.residual_peer_group_count, 0)} rotate next · {String(broadFundAcquisition.status || "awaiting plan").replaceAll("_", " ")}</small></div>
      </div>
      {qualifiedRanked.length ? <div className="capital-discovery-grid">{qualifiedRanked.map((row) => {
        const valuation = row.valuation || {};
        const summary = valuation.summary || {};
        const metrics = row.metrics || {};
        const potentialRank = potentialRankView(row);
        const researchRank = researchRankValue(row);
        const familyScores = row.score_families || row.investment_potential?.family_scores;
        const request = requestForCandidate(row);
        const researchState = candidateResearchStatus(
          row, request, activeSubscriptionJob, subscriptionService,
          discoveryResearchHandoff, candidateLane,
        );
        return <article key={row.candidate_sha256} className="capital-discovery-card">
          <header><span className="capital-rank">{researchRank ? `R#${researchRank}` : potentialRank.value ? `#${potentialRank.value}` : "—"}</span><div><span className="capital-data-class operator">{row.entity_kind.replaceAll("_", " ")} lane</span><h3>{row.name}</h3><p>{row.candidate_id}</p></div><Status ok>{row.screen_status}</Status></header>
          <div className="capital-score-hero"><span>Normalized screen score</span><strong>{number(row.rank_score, 3)}</strong><small>{row.potential_rank ? `rank ${potentialRank.value} ${potentialRank.detail}` : "unranked evidence repair"}</small></div>
          {row.potential_rank?.doctrine_ranks ? <small>Doctrine ranks · {Object.entries(row.potential_rank.doctrine_ranks).map(([name, rank]) => `${name.replaceAll("_", " ")} #${rank}`).join(" · ")}</small> : null}
          {familyScores ? <small>Family standing · {formatPriorityWitness(familyScores)}</small> : null}
          <div className="capital-candidate-explain">
            <div><span>Why it ranked</span><p>{candidateRankReason(row)}</p><small>Ordinal research screen only; not a return forecast, allocation, or recommendation.</small></div>
            <div><span>Bounded web research</span><Status ok={researchState.ok}>{researchState.label}</Status><small>{researchState.detail}</small></div>
          </div>
          <div className="capital-metric-row"><div><span>Earnings power</span><strong>{pct(metrics.earnings_power_margin ?? summary.earnings_power_margin_of_safety)}</strong></div><div><span>Implied growth</span><strong>{pct(metrics.implied_growth ?? summary.implied_growth_median)}</strong></div><div><span>{row.entity_kind === "public_fund" ? "Factor-required return" : "Price-implied hurdle"}</span><strong>{pct(metrics.implied_required_return ?? metrics.factor_implied_return)}</strong></div><div><span>Quality / fit</span><strong>{number(metrics.quality ?? metrics.leave_one_out_r2, 3)}</strong></div></div>
          <p className="capital-research-request">{row.research_prompt || row.error}</p>
          <footer><code>{String(candidateLeaves[row.candidate_id] || "leaf unavailable").slice(0, 16)}</code><div>{valuation.artifact_path ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(valuation.artifact_path)}><FileText size={14} />Valuation programs</button> : null}<span className="capital-next-activation">{row.next_activation}</span></div></footer>
        </article>;
      })}</div> : <Empty title="No qualified survivor" body="The periodic screen is running, but no candidate currently clears its evidence and economic thresholds." />}
      {evidenceRepairRanked.length ? <details className="capital-overview-details"><summary><span><strong>Inspect {evidenceRepairRanked.length} monitor and blocked candidates</strong><small>Preserved for audit, future source repair, and the score-independent rank tournament; they do not outrank qualified subscription research.</small></span></summary><div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Candidate</th><th>Potential lane</th><th>Status</th><th>Next gate</th></tr></thead><tbody>{evidenceRepairRanked.map((row) => { const potentialRank = potentialRankView(row); return <tr key={row.candidate_sha256}><td><strong>{row.entity_id}</strong><small>{row.entity_kind.replaceAll("_", " ")}</small></td><td>{potentialRank.value ? `#${potentialRank.value}` : "unranked"}<small>{potentialRank.detail}</small></td><td><Status>{String(row.screen_status).replaceAll("_", " ")}</Status></td><td><small>{String(row.next_activation || row.error || "await source repair").replaceAll("_", " ")}</small></td></tr>; })}</tbody></table></div></details> : null}
    </Section>
    <Section eyebrow="Activation contract" title="Where the machine stops">
      <div className="capital-activation-grid">{(discovery.activation_points || []).map((row) => <article key={row.id}><header><strong>{row.id.replaceAll("_", " ")}</strong><code>{row.mode}</code></header><p>{row.meaning}</p><small>{row.owner}</small></article>)}</div>
    </Section>
    <Section eyebrow="Executable lifecycle" title="Opportunity funnel"
      description="Each transition creates a new typed object and receipt. Missing source coverage, valuation evidence, representation, or portfolio compatibility blocks the next state.">
      <div className="capital-funnel">{stages.map(([stage, count], index) => <React.Fragment key={stage}>
        <article><span>{index + 1}</span><strong>{stage}</strong><b>{count}</b></article>{index < stages.length - 1 ? <ArrowRight /> : null}
      </React.Fragment>)}</div>
      <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>New evidence reopens the affected neighborhood</strong><p>Settlement updates the screen, mechanism committee, or next evidence request; it does not rewrite the frozen decision.</p></div></div>
      {transitions.length ? <div className="capital-transition-list">{transitions.slice(-8).reverse().map((row) => <article key={row.receipt_sha256}>
        <code>{row.from_state}</code><ArrowRight size={14} /><strong>{row.event}</strong><ArrowRight size={14} /><code>{row.to_state}</code><span>{row.occurred_at}</span>
      </article>)}</div> : null}
    </Section>
    <Section eyebrow="Public company queue" title="Durable earnings-power screens"
      description="Filing-date-bounded revenue persistence, cash conversion, accruals, owner earnings, and balance-sheet resilience. Competitive advantage and management quality remain separate evidence questions.">
      {quality.length ? <div className="capital-quality-grid">{quality.map((row) => <article className="capital-quality-card" key={row.quality_report_sha256}>
        <header><div><span className="capital-data-class operator">public equity</span><h3>{row.entity_id}</h3><p>{row.coverage?.aligned_annual_periods} aligned annual periods</p></div><Status ok={row.coverage?.status === "sufficient_for_screen"}>{row.coverage?.status}</Status></header>
        <div className="capital-score-hero"><span>Durable earnings power</span><strong>{number(row.scores?.durable_earnings_power, 3)}</strong></div>
        <div className="capital-metric-row"><div><span>Revenue CAGR</span><strong>{pct(row.metrics?.revenue_cagr)}</strong></div><div><span>Growth volatility</span><strong>{pct(row.metrics?.revenue_growth_volatility)}</strong></div><div><span>Cash conversion</span><strong>{number(row.metrics?.median_cash_conversion, 2)}×</strong></div><div><span>Net debt / OE</span><strong>{number(row.metrics?.net_debt_to_owner_earnings, 2)}×</strong></div></div>
        <div className="capital-factor-strip"><span><small>revenue durability</small><b>{number(row.scores?.revenue_durability, 2)}</b></span><span><small>earnings quality</small><b>{number(row.scores?.earnings_quality, 2)}</b></span><span><small>balance sheet</small><b>{number(row.scores?.balance_sheet_resilience, 2)}</b></span></div>
        <div className="capital-boundary"><AlertTriangle size={16} /><div><strong>Screen, then investigate</strong><p>{row.residuals?.[0]}</p></div></div>
        <footer><span>as of {row.as_of}</span><button type="button" className="capital-link" onClick={() => onPreview && onPreview(row.result_path)}><FileText size={14} />Quality report</button></footer>
      </article>)}</div> : <Empty title="No company quality screen" body="Refresh an enrolled SEC company and compile the workspace." />}
    </Section>
    <Section eyebrow="Fund selection" title="Merged implementation-sleeve potential"
      description="The current fund roster is ranked within comparable implementation sleeves, then interleaved by sleeve peer rank. Related valuation measures vote once through a valuation family; factor return/risk, implementation cost, and factor fit remain separate. Raw scores never cross sleeves. Frontier status preserves each source-watchlist tradeoff analysis; account-specific utility remains with the portfolio policy."
      actions={<ActionButton action="hydrate-fund" inputs={{ ticker: "PORTFOLIO", limit: 10 }} busy={busy} onAction={onAction}>Acquire best cross-fund issuers</ActionButton>}>
      <div className="capital-discovery-status">
        <div><span>Comparable funds</span><strong>{number(mergedFundAlternatives.length, 0)}</strong><small>across current sleeves</small></div>
        <div><span>Non-dominated</span><strong>{number(mergedFundAlternatives.filter((row) => row.frontier_status === "frontier").length, 0)}</strong><small>source-frontier tradeoffs retained</small></div>
        <div><span>Holdings coverage</span><strong>{number(mergedFundAlternatives.filter((row) => row.fund_evidence?.holdings_snapshot_path).length, 0)}</strong><small>funds with holdings evidence</small></div>
        <div><span>Current reviews</span><strong>{number(currentFundReviewCount, 0)}</strong><small>exact candidate-bound dossiers</small></div>
      </div>
      {mergedFundAlternatives.length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Fund</th><th>Potential</th><th>Frontier</th><th>Factor hurdle</th><th>Earnings power</th><th>Implied growth</th><th>Fee</th><th>Drawdown</th><th>Nearest substitutes</th><th>Evidence</th></tr></thead><tbody>
        {mergedFundAlternatives.map((row) => {
          const values = row.objective_values || {};
          const currentCandidateSha = row.discovery_candidate?.candidate_sha256;
          const currentReview = currentCandidateSha && fundReviews.find((item) => item.entity_id === row.entity_id
            && item.candidate_sha256 === currentCandidateSha);
          const historicalReview = fundReviews.find((item) => item.entity_id === row.entity_id
            && item.candidate_sha256 !== currentCandidateSha);
          const potential = row.discovery_candidate?.investment_potential || row.investment_potential || {};
          const mergedRank = potentialRankView(row.discovery_candidate);
          return <tr key={row.entity_id}><td><strong>{row.entity_id}</strong><small>{row.name}</small></td><td><strong>{mergedRank.value ? `#${mergedRank.value} ${mergedRank.detail}` : "unranked"}</strong><small>current merged sleeve</small><small>{potential.score == null ? "valuation missing" : `${number(potential.score, 3)} peer-normalized research score`}</small>{potential.family_scores ? <small>Family standing · {formatPriorityWitness(potential.family_scores)}</small> : null}</td><td><Status ok={row.frontier_status === "frontier"}>{row.frontier_status}</Status></td><td>{pct(values.factor_implied_return)}</td><td>{pct(values.earnings_power_margin)}</td><td>{pct(values.implied_growth)}</td><td>{pct(values.expense_ratio, 2)}</td><td>{pct(values.drawdown_resilience)}</td><td>{(row.nearest_substitutes || []).slice(0, 3).map((item) => item.entity_id).join(" · ")}</td><td><div className="capital-action-row">{row.fund_evidence?.holdings_snapshot_path ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(row.fund_evidence.holdings_snapshot_path)}><FileText size={14} />Holdings</button> : null}{currentReview ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(currentReview.dossier_path)}><FileText size={14} />Current review</button> : null}{historicalReview ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(historicalReview.dossier_path)}><FileText size={14} />Historical review</button> : null}</div></td></tr>;
        })}
      </tbody></table></div> : <Empty title="No comparable fund frontier" body="Compile a valued fund watchlist to compare non-dominated substitutes." />}
      <div className="capital-discovery-status">
        <div><span>Fund programs covered</span><strong>{number(fundLookthroughPlan.holdings_snapshot_count, 0)}</strong><small>{number((fundLookthroughPlan.missing_holdings_fund_entity_ids || []).length, 0)} holdings gaps</small></div>
        <div><span>Observed quality weight</span><strong>{pct(fundLookthroughPlan.aggregate_before_company_quality_weight)}</strong><small>summed across fund programs</small></div>
        <div><span>Post-batch potential</span><strong>{pct(fundLookthroughPlan.aggregate_after_company_quality_weight_potential)}</strong><small>conditional on sufficient filings</small></div>
        <div><span>Public-source budget</span><strong>{number(fundLookthroughPlan.source_budget?.estimated_source_calls, 0)}</strong><small>{number((fundLookthroughPlan.selected || []).length, 0)} issuers selected</small></div>
        <div><span>Recurring owner</span><strong>{String(fundLookthroughAcquisition.status || "awaiting service").replaceAll("_", " ")}</strong><small>{fundLookthroughAcquisition.next_due_at || "no later batch due"}</small></div>
      </div>
      {fundLookthroughPlan.selection_policy?.objective ? <div className="capital-closure-rule"><Target size={20} /><div><strong>Acquisition objective</strong><p>{String(fundLookthroughPlan.selection_policy.objective).replaceAll("_", " ")}. Sleeves that already have two funds above 50% holdings-quality coverage are skipped; the solver spends the next bounded batch on an under-covered sleeve, with aggregate reusable fund weight breaking ties. Closed now: {(fundLookthroughPlan.same_sleeve_threshold_closure_projection?.observed_closed_sleeve_ids || []).join(" · ") || "none"}. Still targeted: {(fundLookthroughPlan.same_sleeve_threshold_closure_projection?.target_open_sleeve_ids || []).join(" · ") || "none"}. Current conditional path: {number(fundLookthroughPlan.same_sleeve_threshold_closure_projection?.daily_batches_required, 0)} daily batches / {number(fundLookthroughPlan.same_sleeve_threshold_closure_projection?.total_source_calls_required, 0)} source calls for {(fundLookthroughPlan.same_sleeve_threshold_closure_projection?.target_fund_entity_ids || []).join(" + ") || "no reachable pair"}; optimality gap {number(fundLookthroughPlan.same_sleeve_threshold_closure_projection?.optimization_certificate?.mip_gap, 4)}.</p></div></div> : null}
      {fundLookthroughAcquisition.schema ? <div className="capital-closure-rule"><Clock3 size={20} /><div><strong>Next cross-fund evidence batch</strong><p>{(fundLookthroughAcquisition.selected_entity_ids || []).join(" · ") || "No marginal eligible issuer remains"}. {String(fundLookthroughAcquisition.next_action || "The bounded acquisition queue is complete").replaceAll("_", " ")}. The discovery service owns this transition and the enrichment policy caps each public-source batch.</p></div>{state.paths?.fund_lookthrough_acquisition_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.fund_lookthrough_acquisition_latest)}><FileText size={14} />Last acquisition</button> : null}</div> : null}
      {(fundHoldings.pairwise_overlap || []).length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Holdings pair</th><th>Shared issuers</th><th>Jaccard</th><th>Weighted overlap</th><th>Disclosed active share</th></tr></thead><tbody>
        {fundHoldings.pairwise_overlap.slice(0, 8).map((row) => <tr key={`${row.left_entity_id}:${row.right_entity_id}`}><td><strong>{row.left_entity_id} · {row.right_entity_id}</strong></td><td>{number(row.shared_holding_count, 0)}</td><td>{pct(row.holding_jaccard_similarity)}</td><td>{pct(row.weighted_overlap)}</td><td>{pct(row.disclosed_active_share)}</td></tr>)}
      </tbody></table></div> : null}
      {(fundLookthroughPlan.selected || []).length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Next issuer evidence</th><th>Marginal fund weight</th><th>Funds reused</th><th>Fund memberships</th><th>Next action</th></tr></thead><tbody>
        {fundLookthroughPlan.selected.map((row) => <tr key={row.entity_id}><td><strong>{row.entity_id}</strong><small>{row.name}</small></td><td>{pct(row.aggregate_marginal_covered_weight, 2)}</td><td>{number(row.fund_count, 0)}</td><td>{(row.fund_memberships || []).map((item) => item.fund_entity_id).join(" · ")}</td><td>{String(row.next_action || "inspect").replaceAll("_", " ")}</td></tr>)}
      </tbody></table></div> : null}
      {(fundFrontier.representation_residuals || []).length ? <div className="capital-boundary"><AlertTriangle size={16} /><div><strong>Decision residual</strong><p>{fundFrontier.representation_residuals.join(" ")}</p></div></div> : null}
    </Section>
    <Section eyebrow="Fund underwriting handoff" title="Research that has reached operator review"
      description="Each row joins one current qualified fund, its exact research request, public-source dossier, factor and valuation evidence, and its own holdings graph. Eligible means reviewable as a zero-weight paper watch; it is not a recommendation or allocation.">
      {fundProposalRows.length ? <div className="capital-decision-list">{fundProposalRows.map((row) => <article className="capital-frontier-row" key={row.entity_id}>
        <div><span className="capital-data-class operator">public fund</span><strong>{row.entity_id}</strong><small>{row.proposal?.proposal_id || "research incomplete"}</small></div>
        <div><span>Proposal</span><b>{String(row.status || "unknown").replaceAll("_", " ")}</b></div>
        <div><span>Review state</span><b>{activeProposalHashes.has(row.proposal?.proposal_sha256) ? "active paper watch" : row.activation_eligible ? "operator review" : (row.blockers || []).map((value) => String(value).replaceAll("_", " ")).join(" · ")}</b></div>
        <div className="capital-action-row"><button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths?.fund_paper_proposals_latest || "paper_proposals/funds/latest.json")}><FileText size={14} />{row.activation_eligible ? "Review proposal" : "Inspect blocker"}</button>{row.activation_eligible && !activeProposalHashes.has(row.proposal?.proposal_sha256) ? <button type="button" className="capital-link" disabled={busy} onClick={() => activateFundWatch(row)}><ShieldCheck size={14} />Activate zero-weight watch</button> : null}</div>
      </article>)}</div> : <Empty title="No fund has reached paper review" body="A current qualified fund still needs an exact request-bound dossier and candidate-specific holdings graph." />}
    </Section>
    <Section eyebrow="Equity investment committee" title="Current company proposals"
      description="Approval is keyed to the exact current proposal hash. It creates a visible zero-weight paper watch; company-specific position admission remains a separate transition.">
      {equityProposalRows.length ? <div className="capital-decision-list">{equityProposalRows.map((row) => {
        const active = activeProposalHashes.has(row.proposal?.proposal_sha256);
        const dossier = researchDossiers.find((item) => item.dossier_sha256 === row.proposal?.evidence?.dossier_sha256);
        const thesisConfidence = row.proposal?.research?.thesis?.confidence;
        const positionEligible = row.proposal?.position_admission?.eligible === true;
        const valuation = row.proposal?.valuation_program?.summary || {};
        return <article className="capital-frontier-row" key={row.entity_id}>
          <div><span className="capital-data-class operator">public equity</span><strong>{row.entity_id}</strong><small>{row.proposal?.proposal_id || "research incomplete"}</small></div>
          <div><span>Proposal</span><b>{String(row.status || "unknown").replaceAll("_", " ")}</b></div>
          <div><span>Price / modeled range</span><b>{money(valuation.market_price)} / {money(valuation.intrinsic_value_low)}–{money(valuation.intrinsic_value_high)}</b><small>{pct(valuation.implied_growth_median)} implied growth · {pct(valuation.price_implied_excess_return)} implied excess</small></div>
          <div><span>Research consequence</span><b>{thesisConfidence == null ? "awaiting thesis" : `${pct(thesisConfidence)} thesis confidence`}</b><small>{row.proposal ? (positionEligible ? "position evidence admitted" : "watch only · cash retained") : "no current dossier"}</small></div>
          <div><span>Committee state</span><b>{active ? "active paper watch" : row.activation_eligible ? "operator review" : (row.blockers || []).map((value) => String(value).replaceAll("_", " ")).join(" · ")}</b></div>
          <div className="capital-action-row">{dossier?.dossier_path ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(dossier.dossier_path)}><FileText size={14} />Thesis evidence</button> : null}<button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths?.equity_paper_proposals_latest || "paper_proposals/equities/latest.json")}><FileText size={14} />{row.proposal ? "Review proposal" : "Inspect blocker"}</button>{row.activation_eligible && !active ? <button type="button" className="capital-link" disabled={busy} onClick={() => activateEquityWatch(row)}><ShieldCheck size={14} />Approve zero-weight watch</button> : null}</div>
        </article>;
      })}</div> : <Empty title="No equity has reached committee review" body="A qualified company still needs one exact candidate-bound dossier and current valuation, fingerprint, and payoff-grid evidence." />}
    </Section>
    <Section eyebrow="Public fund queue" title="Factor-aware watchlist"
      description="Only funds with a current within-sleeve potential rank appear here. Historical residual return is conditional on the benchmark, and aggregate or holdings-level valuation evidence is required before a fund can be labelled undervalued.">
      {rankedFundCandidates.length ? <div className="capital-fund-grid">{rankedFundCandidates.map((row) => {
        const analysis = row.analysis || {};
        const historical = analysis.historical || {};
        const implied = analysis.assumption_implied || {};
        const betas = (analysis.coefficients || {}).betas || {};
        const potential = row.investment_potential || {};
        return <article key={row.candidate_id} className="capital-fund-card">
          <header><div><span className="capital-data-class operator">{potential.rank ? `potential #${potential.rank} · ${number(potential.score, 3)}` : "potential unranked"}</span><h3>{row.name}</h3><p>{row.entity_id}</p></div><Status ok={row.screen_status === "qualified"}>factor {row.screen_status}</Status></header>
          <p>{row.thesis_prompt}</p>
          <div className="capital-metric-row"><div><span>Factor hurdle</span><strong>{pct(implied.return_without_residual_alpha)}</strong></div><div><span>Net earnings yield</span><strong>{pct(row.valuation?.net_earnings_yield)}</strong></div><div><span>Fee</span><strong>{pct(row.valuation?.expense_ratio, 2)}</strong></div><div><span>Drawdown</span><strong>{pct(historical.maximum_drawdown)}</strong></div></div>
          {potential.family_scores ? <small>Family standing · {formatPriorityWitness(potential.family_scores)}</small> : null}
          <div className="capital-factor-strip">{Object.entries(betas).map(([name, value]) => <span key={name}><small>{name}</small><b>{number(value, 2)}</b></span>)}</div>
          <div className="capital-boundary"><AlertTriangle size={16} /><div><strong>{row.valuation_claim_allowed ? "Valuation evidence present" : "Factor candidate; valuation incomplete"}</strong><p>{row.next_evidence_request}</p></div></div>
          <footer><span>{analysis.observation_count} aligned returns · LOO R² {number((analysis.fit || {}).leave_one_out_r2, 3)}</span><button type="button" className="capital-link" onClick={() => onPreview && onPreview(watchlists.find((item) => (item.candidates || []).includes(row))?.result_path)}><FileText size={14} />Analysis</button></footer>
        </article>;
      })}</div> : <Empty title="No fund has earned a potential rank" body="Refresh fund economics, implementation, and factor evidence; incomplete candidates stay outside this opportunity surface." />}
      {unrankedFundCandidateCount ? <div className="capital-boundary"><AlertTriangle size={16} /><div><strong>{unrankedFundCandidateCount} funds remain in evidence repair</strong><p>They are retained in the source artifacts and broad scout, but do not occupy ranked opportunity space until the required economic families are comparable.</p></div></div> : null}
    </Section>
  </>;
}

function Sources({ state, busy, onAction, onPreview }) {
  const statuses = state.source_statuses || [];
  const consumed = statuses.filter((row) => row.status === "consumed");
  const failures = statuses.filter((row) => ["failed", "blocked", "stale"].includes(row.status));
  const inactive = statuses.filter((row) => ["not_scheduled", "disabled"].includes(row.status));
  const receipts = state.source_receipts || [];
  const requirements = state.source_requirements || [];
  const observations = state.latest_observations || [];
  const signals = state.signal_receipts || [];
  const metricUniverse = state.metric_universe || {};
  const pointInTimeEvidence = state.point_in_time_evidence || {};
  const sourceRun = state.source_run || {};
  const yahooCompaction = sourceRun.yahoo_identity_compaction || {};
  const schedule = state.discovery?.schedule || {};
  const freshnessGaps = schedule.quality_freshness?.gaps || [];
  const researchService = state.subscription_research?.service || {};
  const researchQueue = state.subscription_research?.queue?.by_status || {};
  const metricDefinitions = metricUniverse.metrics || [];
  const valuationContract = metricUniverse.valuation_ast_contract || {};
  return <>
    <Section eyebrow="Public evidence" title="Usable evidence now"
      description="Provider coverage, failures, and information availability determine which measurements can enter a screen or historical comparison. Archived provider responses preserve provenance and point-in-time replay; their volume is not an investment signal."
      actions={<ActionButton action="sources" busy={busy} onAction={onAction} primary>Refresh public data</ActionButton>}>
      <div className="capital-discovery-status">
        <div><span>Last gathered</span><strong>{sourceRun.retrieved_at ? String(sourceRun.retrieved_at).replace("T", " ").replace("Z", " UTC") : "never"}</strong><small>{number(sourceRun.observation_count, 0)} point-in-time observations</small></div>
        <div><span>Consumed sources</span><strong>{number(consumed.length, 0)} / {number(statuses.length, 0)}</strong><small>{number(receipts.length, 0)} archived provider responses</small></div>
        <div><span>Coverage</span><strong>{number(metricUniverse.observed_registered_count, 0)} / {number(metricUniverse.metric_count, 0)} metrics</strong><small>{number(state.broad_equity_potential?.coverage?.fully_comparable_ranked_count, 0)} comparable equities</small></div>
        <div><span>Failures</span><strong>{number(failures.length, 0)}</strong><small>{number(sourceRun.required_failure_count, 0)} required · {number(Math.max(0, failures.length - Number(sourceRun.required_failure_count || 0)), 0)} optional</small></div>
        <div><span>Freshness</span><strong>{schedule.due ? "refresh due" : sourceRun.ok ? "current by schedule" : "unavailable"}</strong><small>{number(freshnessGaps.length, 0)} candidate binding gaps · next {schedule.next_due_at || "unscheduled"}</small></div>
        <div><span>Web research</span><strong>{String(researchService.status || "not running").replaceAll("_", " ")}</strong><small>{number(researchQueue.queued, 0)} current queued · {number(researchQueue.dead_letter, 0)} retained terminal ledger rows</small></div>
      </div>
      <div className="capital-closure-rule"><Database size={20} /><div><strong>What these counts mean</strong><p>Source responses are saved so an earlier decision can be replayed from the bytes available then. Observation rows are provider- and time-stamped records, so repeated captures or providers may describe the same economic fact. The row count measures evidence volume, not unique facts, coverage quality, or edge.</p></div></div>
      {yahooCompaction.status === "compacted" ? <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Legacy price identities compacted</strong><p>{number(yahooCompaction.collapsed_count, 0)} retrieval-bound Yahoo rows were collapsed onto {number(yahooCompaction.after_count, 0)} distinct price identities while preserving the earliest witnessed availability. SEC filing identities were not included.</p><small>Evidence repair only · no capital authority</small></div></div> : null}
      {failures.length ? <div className="capital-boundary"><AlertTriangle size={17} /><div><strong>{failures.length} source failure{failures.length === 1 ? "" : "s"} need attention</strong><p>{failures.map((row) => `${row.source_id}: ${row.error || row.status}`).join(" · ")}. A failed dependency blocks only candidates that require it.</p></div></div> : null}
      {consumed.length ? <details className="capital-audit-trail"><summary><Database size={17} /><span><strong>Gathered and admitted · {consumed.length} sources</strong><small>Open to see the exact providers and observation counts used by the current data epoch</small></span></summary><SourceCards rows={consumed} /></details> : <Empty title="No source run yet" body="Refresh to consume the enabled SEC, FRED, market-price, or HTTPS CSV adapters." />}
      {inactive.length ? <details className="capital-audit-trail"><summary><CircleDashed size={17} /><span><strong>Outside this bounded refresh · {inactive.length} sources</strong><small>Not scheduled is a budget choice, not a failure; prior admissible observations remain subject to age gates</small></span></summary><SourceCards rows={inactive} /></details> : null}
      {requirements.length ? <details className="capital-audit-trail"><summary><ShieldCheck size={17} /><span><strong>Source configuration · {requirements.length} requirements</strong><small>Disabled sources are intentionally excluded; missing required configuration blocks refresh</small></span></summary><div className="capital-requirements">{requirements.map((row) =>
        <div key={`${row.source_id}:${row.environment_variable}`}><Status ok={row.configured || row.enabled === false}>{row.source_id}{row.enabled === false ? " · disabled" : ""}</Status><code>{row.environment_variable}</code><span>{row.purpose}</span></div>)}</div></details> : null}
    </Section>
    {pointInTimeEvidence.enabled ? <Section eyebrow="Point-in-time archive" title="What the engine could have known at a past cutoff"
      description="Each refresh stores the exact source bytes and the observations knowable at ingestion. A future mechanical replay selects the latest capture available by its cutoff; later captures cannot enter earlier decisions. Model training knowledge is classified separately.">
      <div className="capital-discovery-status">
        <div><span>Archive state</span><strong>{String(pointInTimeEvidence.status || "unknown").replaceAll("_", " ")}</strong><small>{pointInTimeEvidence.integrity_verified ? "content hashes verified" : "integrity not verified"}</small></div>
        <div><span>Captured sources</span><strong>{number(pointInTimeEvidence.source_count, 0)}</strong><small>{number(pointInTimeEvidence.observation_count, 0)} observations</small></div>
        <div><span>Capture clock</span><strong>{String(pointInTimeEvidence.ingestion_clock_authority || "unknown").replaceAll("_", " ")}</strong><small>{pointInTimeEvidence.ingested_at || "no ingestion epoch"}</small></div>
        <div><span>Missing sources</span><strong>{number(pointInTimeEvidence.missing_source_ids?.length, 0)}</strong><small>{(pointInTimeEvidence.missing_source_ids || []).join(" · ") || "declared capture complete"}</small></div>
      </div>
      <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Replay authority</strong><p>{String(pointInTimeEvidence.authority?.evidence_replay || "unclassified").replaceAll("_", " ")}. This archive can support source-chronology checks; it does not establish alpha, permit paper-policy changes, or route capital.</p><small>{(pointInTimeEvidence.leakage_classes || []).map((value) => String(value).replaceAll("_", " ")).join(" · ") || "no leakage class recorded"}</small></div>{state.paths?.point_in_time_evidence_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.point_in_time_evidence_latest)}><FileText size={14} />Inspect capture manifest</button> : null}</div>
    </Section> : null}
    <details className="capital-audit-trail"><summary><Database size={17} /><span><strong>Source audit trail</strong><small>Exact provider responses, retrieval times, and hashes for replay and point-in-time checks</small></span></summary>
      {receipts.length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Source</th><th>Availability</th><th>Retrieved</th><th>Rows</th><th>Archived response</th></tr></thead><tbody>
        {receipts.map((row) => <tr key={row.receipt_sha256}><td><strong>{row.source_id}</strong><small>{row.adapter}</small></td><td><code>{row.availability_mode}</code></td><td>{row.retrieved_at}</td><td>{number(row.observation_count, 0)}</td><td><button type="button" className="capital-link" onClick={() => onPreview && onPreview(row.raw_path)}>{row.content_sha256.slice(0, 12)}</button></td></tr>)}
      </tbody></table></div> : <Empty title="No archived source responses" body="Run the public-source refresh first." />}
    </details>
    <Section eyebrow="Typed metric universe" title="What the engine can observe or derive"
      description="Each metric has one identity, unit, temporal type, producer, and entity scope. The signal DAG handles deterministic indicators; the valuation grammar owns recursive present-value and inverse-price programs.">
      <div className="capital-discovery-status">
        <div><span>Registered metrics</span><strong>{number(metricUniverse.metric_count, 0)}</strong><small>{number(metricUniverse.observed_registered_count, 0)} observed in this workspace</small></div>
        <div><span>Signal operators</span><strong>{number(metricUniverse.signal_ast_contract?.operators?.length, 0)}</strong><small>deterministic DAG</small></div>
        <div><span>Valuation operators</span><strong>{number(valuationContract.operators?.length, 0)}</strong><small>typed recursive AST</small></div>
        <div><span>Unregistered observations</span><strong>{number(metricUniverse.unregistered_observed_metric_ids?.length, 0)}</strong><small>visible residuals</small></div>
      </div>
      {metricDefinitions.length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Metric</th><th>Type</th><th>Time</th><th>Producer</th><th>Scope</th></tr></thead><tbody>
        {metricDefinitions.map((row) => <tr key={row.metric_id}><td><strong>{row.metric_id}</strong><small>{row.description}</small></td><td><code>{row.semantic_type} · {row.unit}</code></td><td>{row.temporal_type}</td><td><Status ok={row.observed}>{row.observed ? "observed" : row.producer.replaceAll("_", " ")}</Status></td><td>{row.entity_kinds.map((value) => value.replaceAll("_", " ")).join(", ")}</td></tr>)}
      </tbody></table></div> : null}
      <div className="capital-action-row"><code>cost_of_equity(RiskFreeRate, EquityRiskPremium, EquityBeta) → DiscountRate</code><code>implied_growth(MarketPrice, OwnerEarnings, DiscountRate, TerminalGrowth, Horizon, ExcessNetCash, Shares) → ImpliedGrowth</code></div>
    </Section>
    <Section eyebrow="Point-in-time state" title="Latest admissible observations" description="These are the latest rows whose availability time does not exceed the source run's as-of time.">
      {observations.length ? <div className="capital-table-wrap"><table className="capital-table"><thead><tr><th>Entity</th><th>Metric</th><th>Value</th><th>Observed</th><th>Available</th><th>Source</th></tr></thead><tbody>
        {observations.slice(0, 120).map((row) => <tr key={row.observation_id}><td>{row.entity_id}</td><td><code>{row.metric_id}</code></td><td>{number(row.value)} {row.unit}</td><td>{row.observed_at}</td><td>{row.available_at}</td><td>{row.source_ref}</td></tr>)}
      </tbody></table></div> : <Empty title="No normalized observations" body="The source run may be unconfigured, disabled, or awaiting a provider credential." />}
    </Section>
    <Section eyebrow="Formal derivations" title="Signal receipts" description="Signals are deterministic grammar programs over named observations; missing inputs block derivation and every output binds its input IDs.">
      {signals.length ? <div className="capital-signal-list">{signals.map((row) => <article key={row.receipt_sha256}><GitBranch size={17} /><div><strong>{row.definition.metric_id}</strong><code>{row.definition.operator}({row.definition.arguments.map((arg) => arg.metric || arg.value).join(", ")})</code><small>{row.input_observation_ids.length} bound inputs · available {row.observation.available_at}</small></div><b>{number(row.observation.value)} {row.observation.unit}</b></article>)}</div>
        : <Empty title="No signal formulas configured" body="Add only signals that change a fingerprint, valuation, falsifier, or policy. The workspace deliberately has no default indicator zoo." />}
    </Section>
  </>;
}

function BusinessStrategyLearning({ state, onPreview }) {
  const subscriptionResearch = state.subscription_research || {};
  const activeResearchJobs = subscriptionResearch.active_jobs || [];
  const activeResearchJob = activeResearchJobs[0] || {};
  const activeResearchPayload = activeResearchJob.payload || {};
  const frozenChainLane = subscriptionResearch.frozen_chain_lane || {};
  const nextResearchJob = subscriptionResearch.next_job || {};
  const nextResearchPayload = nextResearchJob.payload || {};
  const nextPotential = potentialRankView({
    entity_kind: nextResearchPayload.entity_kind,
    potential_rank: nextResearchPayload.potential_rank,
  });
  const nextResearchRank = researchRankValue(nextResearchPayload);
  const nextIsFrozen = Boolean(
    frozenChainLane.next_work_id
    && frozenChainLane.next_work_id === nextResearchJob.work_id
  );
  const nextPriorityEvidence = [
    nextResearchJob.priority != null ? `queue priority ${number(nextResearchJob.priority, 0)}` : null,
    nextResearchPayload.frozen_chain_priority != null
      ? `frozen-chain priority ${number(nextResearchPayload.frozen_chain_priority, 0)}` : null,
    nextPotential.value ? `potential rank #${nextPotential.value}` : null,
    nextResearchRank ? `research rank #${nextResearchRank}` : null,
    nextResearchPayload.learning_schedule_rank
      ? `learning rank #${nextResearchPayload.learning_schedule_rank}` : null,
  ].filter(Boolean).join(" · ");
  const nextPriorityReason = nextIsFrozen
    ? "This is the highest-priority frozen successor. The dispatch arbiter closes the open evidence chain before unrelated work."
    : nextResearchJob.work_id
      ? "The dispatch arbiter selected this job after frozen-chain and reserved-lane rules."
      : "No successor is currently selectable.";
  const strategyMoveLearning = state.strategy_move_learning || {};
  const strategyProgramLearning = state.strategy_program_learning || {};
  const strategyProgramOutcomeAcquisition = state.strategy_program_outcome_acquisition || {};
  const strategyProgramTransfer = state.strategy_program_transfer || {};
  const strategyProgramControlAcquisition = state.strategy_program_control_acquisition || {};
  const strategyProgramComparison = state.strategy_program_comparison || {};
  const nextProgramControl = strategyProgramControlAcquisition.next_transition || {};
  const strategyValuationBridge = state.strategy_valuation_bridge || {};
  const latestStrategyProgram = (strategyProgramLearning.rows || [])[0] || {};
  const latestProgramDiscriminators = (latestStrategyProgram.candidate_programs || [])
    .flatMap((row) => row.discriminating_option_ids || []);
  const strategyCohortResearch = state.strategy_cohort_research || {};
  const strategyActiveComparator = state.strategy_active_comparator || {};
  const activeComparatorAudit = strategyActiveComparator.audit || {};
  const strategyTransfer = state.strategy_transfer || {};
  const strategyTransferAcquisition = state.strategy_transfer_acquisition || {};
  const nextEventRefinement = strategyTransferAcquisition.next_cross_family_acquisition || {};
  const strategyAlphaTournament = state.strategy_alpha_tournament || {};
  const strategyHurdleCalibration = strategyAlphaTournament.evidence?.operating_hurdle_calibration || {};
  const strategyAlphaSources = strategyAlphaTournament.source_readiness || {};
  const strategyAlphaIssuance = strategyAlphaTournament.issuance_gate || {};
  const strategyDualOutcomes = state.strategy_dual_outcomes || {};
  const strategyAlphaBinding = strategyAlphaTournament.binding_activation || {};
  const latestStrategyActivation = (strategyAlphaBinding.activation_statuses || []).find((row) => row.status === "activated") || {};
  const strategyOutcomeAcquisition = state.strategy_outcome_acquisition || {};
  const strategyStateExperiment = state.strategy_state_experiment || {};
  const strategyStateControlAcquisition = state.strategy_state_control_acquisition || {};
  const strategyStateSuccessor = state.strategy_state_successor || {};
  const strategyStateTransitionJoin = state.strategy_state_transition_join || {};
  const strategyPathInput = strategyStateTransitionJoin.strategy_conditioned_path_input || {};
  const strategyPathLagrangian = state.strategy_path_lagrangian || {};
  const strategyPathMissingLabels = {
    observable_post_two_step_paths: "exposed post-event two-step paths",
    certified_unexposed_monitored_paths: "source-complete no-family-adoption paths",
  };
  const maxCaliberRecovery = state.max_caliber_recovery || {};
  const maxCaliberGate = maxCaliberRecovery.recovery_gate || {};
  const maxCaliberReadiness = state.max_caliber_readiness || {};
  const maxCaliberJoinLane = maxCaliberReadiness.strategy_conditioning_lane || {};
  const maxCaliberJoinJob = maxCaliberJoinLane.selected_existing_job || {};
  const nextLearningAction = state.learning_schedule?.next_action || {};
  const nextStateEvent = nextLearningAction.action_class === "sharpen_strategy_treatment_event"
    ? nextLearningAction : {};
  const strategyStateSuccessorPeers = strategyStateSuccessor.peer_control_frontier || {};
  const strategyStateControlAudit = strategyStateControlAcquisition.audit || {};
  const strategyCausalPanel = state.institutional_learning?.strategy_causal_panel || {};
  const strategyLawInduction = state.strategy_law_induction || {};
  const strategyLawCandidates = (state.institutional_learning?.candidates || []).filter((row) => row.origin === "strategy_phenotype_compiler");
  const strategyLawKeys = new Set(strategyLawCandidates.map((row) => row.law_key));
  const strategyEvaluation = (state.institutional_learning?.evaluations || []).find((row) => strategyLawKeys.has(row.law_key))
    || (state.institutional_learning?.evaluations || []).find((row) => String(row.law_key || "").startsWith("reinforcing-strategy-choice-durability@")) || {};
  const strategyHoldout = strategyEvaluation.strategy_regularity?.prospective_holdout || {};
  const strategyHoldoutObserved = strategyHoldout.observed || {};
  const strategyHoldoutRequired = strategyHoldout.required || {};
  const cohortClasses = strategyCohortResearch.classification_counts || {};
  const crossEnvironmentFamilies = (strategyMoveLearning.move_families || []).filter((row) => number(row.environment_count, 0) > 1).length;
  const agentCompiledFrontiers = (state.company_strategy_frontiers || []).filter((row) => row.company?.profile_authority === "subscription_agent_proposal").length;
  const companyStrategyFrontiers = (state.company_strategy_frontiers || []).filter((row) => row.company?.data_class !== "reference_fixture");
  const investmentPath = state.strategy_investment_path || {};
  const pathProgram = investmentPath.highlighted_program || {};
  const pathFeasibility = investmentPath.feasible_programs || {};
  const pathContrast = investmentPath.empirical_contrast || {};
  const pathEarnings = investmentPath.earnings_effect || {};
  const pathValuation = investmentPath.valuation || {};
  const readableOptions = (values) => (values || []).map((value) => String(value).replaceAll("_", " ")).join(" + ");
  const frontierEvolution = strategyMoveLearning.frontier_evolution || [];
  const measurableStrategyMoves = (strategyMoveLearning.moves || []).filter((row) => (row.outcome_contracts || []).length);
  const unmeasuredExactMoves = (strategyMoveLearning.moves || []).filter((row) => (
    (row.implementation_event?.treatment_timing_status === "exact_adoption_event"
      || row.timing_refinement?.classification === "exact_implementation_event_found")
    && !(row.outcome_contracts || []).length
  ));
  const measurementQueueCount = number(
    state.subscription_research?.live_queued_by_kind?.jaggedthoughts_strategy_measurement_research,
    0,
  );
  const nextMeasurementJob = state.subscription_research?.next_job?.kind
    === "jaggedthoughts_strategy_measurement_research"
    ? state.subscription_research.next_job : {};
  const strategyEvidenceLadder = strategyMoveLearning.evidence_ladder || [];
  const currentStrategyEvidenceGrade = (strategyMoveLearning.moves || []).reduce((best, row) => (
    strategyEvidenceLadder.indexOf(row.evidence_grade) > strategyEvidenceLadder.indexOf(best) ? row.evidence_grade : best
  ), strategyEvidenceLadder[0] || "option_only");
  return <Section eyebrow="Business strategy learning" title="Which management moves improve the business—and when?"
    description="A strategic move and a stock purchase are scored separately. The first asks whether management improved the business; the second asks whether the price paid left enough return.">
    <div className="capital-start-status">
      <article className={activeResearchJob.work_id ? "ready" : "blocked"}>
        <span>Active now</span>
        <strong>{activeResearchPayload.entity_id || (activeResearchJob.work_id ? researchJobKindLabel(activeResearchJob.kind) : "Worker idle")}</strong>
        <p>{activeResearchJob.work_id
          ? `${researchJobKindLabel(activeResearchJob.kind)} · ${String(activeResearchJob.status || "active").replaceAll("_", " ")} · attempt ${number(activeResearchJob.attempts, 0)} of ${number(activeResearchJob.max_attempts, 0)}${activeResearchJobs.length > 1 ? ` · ${activeResearchJobs.length} active jobs` : ""}`
          : "No subscription-research job is currently claimed."}</p>
        {activeResearchJob.work_id ? <code title={activeResearchJob.work_id}>{activeResearchJob.work_id}</code> : null}
      </article>
      <article className={frozenChainLane.next_work_id ? "ready" : ""}>
        <span>Frozen successor</span>
        <strong>{frozenChainLane.next_entity_id || "No frozen successor queued"}</strong>
        <p>{frozenChainLane.next_work_id
          ? `${researchJobKindLabel(frozenChainLane.next_kind)} · ${number(frozenChainLane.waiting_count, 0)} frozen successor${Number(frozenChainLane.waiting_count) === 1 ? "" : "s"} waiting`
          : "No already-open evidence chain currently reserves the next claim."}</p>
        {frozenChainLane.next_work_id ? <code title={frozenChainLane.next_work_id}>{frozenChainLane.next_work_id}</code> : null}
      </article>
      <article className={nextResearchJob.work_id ? "ready" : ""}>
        <span>Why it has priority</span>
        <strong>{nextResearchPayload.entity_id || (nextResearchJob.work_id ? researchJobKindLabel(nextResearchJob.kind) : "Queue empty")}</strong>
        <p>{nextPriorityReason}{nextPriorityEvidence ? ` ${nextPriorityEvidence}.` : ""}</p>
        {nextResearchJob.work_id ? <code title={nextResearchJob.work_id}>{nextResearchJob.work_id}</code> : null}
      </article>
    </div>
    {investmentPath.company?.id ? <article className="capital-strategy-result" aria-label="Strategy to valuation path">
      <header><div><span className="capital-data-class operator_research">Worked company path</span><h3>{investmentPath.company.name || investmentPath.company.id}</h3><p>One company carried through six stages. Missing evidence stops the path instead of being filled with a score.</p></div><Status ok={pathValuation.company_specific_result}>{pathValuation.company_specific_result ? "valued" : "valuation blocked"}</Status></header>
      <div className="capital-activation-grid capital-edge-grid">
        <article><header><strong>1 · Choices</strong><code>{number(investmentPath.choices?.length, 0)} sourced</code></header><p>{(investmentPath.choices || []).slice(0, 4).map((row) => row.label).join(" · ")}{investmentPath.choices?.length > 4 ? ` · +${investmentPath.choices.length - 4}` : ""}</p><small>Management actions named from the source-bound company model.</small></article>
        <article><header><strong>2 · Feasible programs</strong><code>{number(pathFeasibility.count, 0)} bundles</code></header><p>Z3 removes combinations that violate declared incompatibilities, prerequisites, resource bounds, or bundle size.</p><small>{number(pathFeasibility.excluded_count, 0)} excluded bundle{number(pathFeasibility.excluded_count, 0) === 1 ? "" : "s"} · {number(pathFeasibility.constraint_witness_count, 0)} predicate witness class{number(pathFeasibility.constraint_witness_count, 0) === 1 ? "" : "es"} · scope {pathFeasibility.scope_closed ? "closed" : "incomplete"}</small></article>
        <article><header><strong>3 · Survivor / local peak</strong><code>{pathProgram.global_frontier ? "Pareto survivor" : "not global"} · {pathProgram.local_peak ? "local peak" : "not local"}</code></header><p>{(pathProgram.option_labels || []).join(" + ") || "No highlighted program"}</p><small>{number(pathProgram.global_frontier_count, 0)} global survivors · {number(pathProgram.local_peak_count, 0)} local peaks</small></article>
        <article><header><strong>4 · One-choice test</strong><code>{String(pathContrast.status || "unavailable").replaceAll("_", " ")}</code></header><p>{pathContrast.added_option_id ? <>{readableOptions(pathContrast.base_option_ids) || "base program"} → add <strong>{pathContrast.added_option_label || readableOptions([pathContrast.added_option_id])}</strong></> : "No exact one-choice contrast compiled."}</p><small>{pathContrast.implementation_event?.occurred_at || "implementation not yet bound"} · {pathContrast.metric_contract?.metric_id ? String(pathContrast.metric_contract.metric_id).replaceAll("_", " ") : "metric contract not yet bound"}</small></article>
        <article><header><strong>5 · Earnings effect</strong><code>{String(pathEarnings.status || "unmeasured").replaceAll("_", " ")}</code></header><p>{pathEarnings.metric_id ? `${String(pathEarnings.metric_id).replaceAll("_", " ")} must ${pathContrast.metric_contract?.direction || "move"} by ${number(pathEarnings.minimum_effect, 3)} ${pathEarnings.unit || ""}` : pathEarnings.economic_coordinate ? `Proposed bridge: ${String(pathEarnings.economic_coordinate).replaceAll("_", " ")}` : "No financial magnitude is inferred from the ordinal strategy score."}</p><small>{pathEarnings.due_at ? `due ${String(pathEarnings.due_at).slice(0, 10)}` : "awaiting a dated operating outcome"}</small></article>
        <article><header><strong>6 · Valuation</strong><code>{String(pathValuation.status || "blocked").replaceAll("_", " ")}</code></header><p>{pathValuation.company_specific_result ? "The measured earnings effect can now enter priced cash-flow worlds." : "No company valuation changes until an operating effect with units survives the evidence gate."}</p><small>{pathValuation.next_activation || "Bind the operating effect to a valuation baseline."}</small></article>
      </div>
      <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>What the frontier labels mean</strong><p><b>Pareto survivor:</b> {investmentPath.definitions?.pareto} <b>Local peak:</b> {investmentPath.definitions?.local_peak}</p></div></div>
      <details className="capital-audit-trail"><summary><GitBranch size={17} /><span><strong>How recursion and Z3 work in this example</strong><small>Language, solver predicates, and proof boundary</small></span></summary><div className="capital-strategy-options">
        <div><code>choice(id) → Strategy</code><span>Each source-bound management choice is a typed terminal.</span></div>
        <div><code>combine(Strategy, Strategy) → Strategy</code><span>{(pathProgram.option_ids || []).length >= 2 ? `The highlighted tree combines ${pathProgram.option_ids[0]} with ${pathProgram.option_ids[1]}.` : "The grammar recursively joins compatible choices."} The set enumerator emits one canonical balanced AST for each admitted option set.</span></div>
        <div><code>cardinality_ge · cardinality_le · not_all_selected</code><span>Bundle-size bounds and declared incompatibilities lower to Boolean constraints.</span></div>
        <div><code>implies_all_selected · linear_sum_le</code><span>Prerequisites and typed resource budgets lower to implication and linear arithmetic.</span></div>
        <div><code>certificate ≠ evidence</code><span>Z3 can close the authored compatibility space. Sources and later outcomes must establish implementation, operating effects, and investor returns.</span></div>
      </div></details>
      {(investmentPath.choices || []).length ? <details className="capital-audit-trail"><summary><Layers3 size={17} /><span><strong>Read the source-bound choices</strong><small>Plain-language option descriptions; the formal AST remains in the frontier certificate</small></span></summary><div className="capital-strategy-options">{investmentPath.choices.map((choice) => <div key={choice.option_id}><code>{choice.label}</code><span>{choice.description}</span></div>)}</div></details> : null}
    </article> : null}
    <details className="capital-audit-trail">
      <summary><Activity size={17} /><span><strong>Engine diagnostics</strong><small>Acquisition, transfer, causal, and settlement counters</small></span></summary>
      <div className="capital-discovery-status">
      <div><span>Exact moves</span><strong>{number(strategyMoveLearning.move_count, 0)}</strong><small>versioned company choices</small></div>
      <div><span>Mechanism phenotypes</span><strong>{number(strategyMoveLearning.mechanism_phenotype_count, 0)}</strong><small>{number(strategyMoveLearning.move_count / Math.max(1, strategyMoveLearning.mechanism_phenotype_count), 2)} moves per form · compression target</small></div>
      <div><span>Company models</span><strong>{number(companyStrategyFrontiers.length, 0)} / {number(agentCompiledFrontiers, 0)}</strong><small>source-bound / subscription-compiled</small></div>
      <div><span>Granular laws</span><strong>{number(strategyLawInduction.candidate_count ?? strategyLawCandidates.length, 0)}</strong><small>{number(strategyLawInduction.eligible_candidate_count, 0)} eligible for policy review</small></div>
      <div><span>Strategy → value</span><strong>{number(strategyValuationBridge.direct_financial_effect_count, 0)}</strong><small>direct financial translations · {number(strategyValuationBridge.conditional_translation_request_count, 0)} conjectures needed</small></div>
      <div><span>Cross-environment</span><strong>{number(crossEnvironmentFamilies, 0)}</strong><small>transfer questions, not proven rules</small></div>
      <div><span>Epoch comparisons</span><strong>{number(frontierEvolution.length, 0)}</strong><small>representation drift checks</small></div>
      <div><span>Observed execution</span><strong>{number(strategyMoveLearning.implementation_observed_move_count, 0)}</strong><small>source-bound implementation events</small></div>
      <div><span>Exact adoption</span><strong>{number(strategyMoveLearning.treatment_event_ready_move_count, 0)}</strong><small>eligible to seed treated panels</small></div>
      <div><span>Timing searches</span><strong>{number(strategyTransferAcquisition.census?.active_event_refinement_count, 0)}</strong><small>primary-source leaves queued for exact adoption dates</small></div>
      <div><span>Coarse timing identified</span><strong>{number(strategyCausalPanel.coarse_period_identified_interval_count, 0)}</strong><small>censored dates mapping to one annual treatment cohort</small></div>
      <div><span>Measurement acquisition</span><strong>{measurementQueueCount}</strong><small>{number(unmeasuredExactMoves.length, 0)} exact implemented move awaiting a metric contract</small></div>
      <div><span>Program questions</span><strong>{number(strategyProgramLearning.result_count, 0)} / {number(strategyProgramLearning.request_count, 0)}</strong><small>classified / frozen integrated bundles</small></div>
      <div><span>Program readouts</span><strong>{number(strategyProgramLearning.settled_program_outcome_count, 0)} / {number(strategyProgramOutcomeAcquisition.unsettled_readout_count, 0)}</strong><small>settled / prospective operating readouts</small></div>
      <div><span>Program transfer</span><strong>{number(strategyProgramTransfer.cross_company_card_count, 0)} / {number(strategyProgramTransfer.comparison_ready_card_count, 0)}</strong><small>cross-company / comparison-ready forms</small></div>
      <div><span>Program controls</span><strong>{number(strategyProgramControlAcquisition.admitted_source_control_count, 0)} / {number(strategyProgramControlAcquisition.candidate_control_count, 0)}</strong><small>admitted / candidate composition controls</small></div>
      <div><span>Program comparison</span><strong>{number(strategyProgramComparison.treated_episode_count, 0)} / {number(strategyProgramComparison.control_episode_count, 0)}</strong><small>integrated / assessment-time control outcomes</small></div>
      <div><span>Peers classified</span><strong>{number(strategyCausalPanel.research_result_count ?? strategyCohortResearch.result_count, 0)} / {number(strategyCausalPanel.research_request_count ?? strategyCohortResearch.request_count, 0)}</strong><small>primary-source event searches</small></div>
      <div><span>Treated / related</span><strong>{number(strategyCausalPanel.treated_unit_count, 0)} / {number(strategyCausalPanel.family_only_excluded_count ?? cohortClasses.family_adoption_only, 0)}</strong><small>panel units / excluded family matches</small></div>
      <div><span>Active alternatives</span><strong>{number(activeComparatorAudit.partition_counts?.eligible_active_alternative, 0)}</strong><small>{number(activeComparatorAudit.floor_ready_cell_count, 0)} P:Q cells meet firm floors</small></div>
      <div><span>Evidence gaps</span><strong>{number(strategyCausalPanel.source_gap_excluded_count, 0)}</strong><small>exhausted searches; excluded from inference</small></div>
      <div><span>Panel histories</span><strong>{number(strategyCausalPanel.treated_unit_count, 0)} / {number(strategyCausalPanel.control_unit_count, 0)}</strong><small>treated / provisional control units</small></div>
      <div><span>Viable grains</span><strong>{number(strategyCausalPanel.projection_frontier_count, 0)}</strong><small>coverage × specificity frontier; unselected</small></div>
      <div><span>Causal test</span><strong>{String(strategyEvaluation.status || "awaiting panel").replaceAll("_", " ")}</strong><small>no promotion without support and pretrend checks</small></div>
      <div><span>Promotion evidence</span><strong>{number(strategyHoldoutObserved.independent_treated_units, 0)} / {number(strategyHoldoutRequired.treated_units, 4)}</strong><small>independent treated · {number(strategyHoldoutObserved.bounded_control_units, 0)}/{number(strategyHoldoutRequired.control_units, 4)} controls · {number(strategyHoldoutObserved.transfer_environments, 0)}/{number(strategyHoldoutRequired.transfer_environments, 2)} environments</small></div>
      <div><span>Settled outcomes</span><strong>{number(strategyMoveLearning.outcome_episode_count, 0)}</strong><small>operating results, separate from returns</small></div>
      <div><span>Outcome contracts</span><strong>{number(strategyOutcomeAcquisition.due_contract_count, 0)} / {number(strategyOutcomeAcquisition.unsettled_contract_count, 0)}</strong><small>due now / unsettled</small></div>
      <div><span>Dual episodes</span><strong>{number(strategyDualOutcomes.settled_count, 0)} / {number(strategyDualOutcomes.episode_count, 0)}</strong><small>both consequences settled / issued</small></div>
      <div><span>Evidence ceiling</span><strong>{String(currentStrategyEvidenceGrade).replaceAll("_", " ")}</strong><small>highest rung reached</small></div>
      </div>
    </details>
    <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>The compounding unit</strong><p>Business state × strategic move × implementation conditions → operating outcome. Price-implied expectations × later cash flows → investor return. {number(strategyMoveLearning.move_count, 0)} exact moves currently form {number(strategyMoveLearning.mechanism_phenotype_count, 0)} mechanism phenotypes and {number(strategyMoveLearning.move_family_count, 0)} broad families. The current {number(strategyMoveLearning.move_count / Math.max(1, strategyMoveLearning.mechanism_phenotype_count), 2)} moves per phenotype shows that transfer compression is still weak; with {number(strategyMoveLearning.outcome_episode_count, 0)} settled outcomes, none is yet a trusted strategy rule.</p></div></div>
    {nextEventRefinement.move_sha256 ? <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Exact-event acquisition · {nextEventRefinement.entity_id}</strong><p>{nextEventRefinement.description}</p><small>{nextEventRefinement.issue_now ? `Queued as ${nextEventRefinement.work_id}; the result can refine causal timing without rewriting the authored move.` : "Requires a bounded primary-source timing search before causal-panel use."}</small></div><Status ok={nextEventRefinement.queue_status === "done"}>{String(nextEventRefinement.queue_status || nextEventRefinement.current_timing_status || "not queued").replaceAll("_", " ")}</Status></div> : null}
    <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Adoption → measurement activation</strong><p>The engine searches primary documents for a metric, comparator, start date, horizon, and frozen hurdle only after an exact implemented move exists. A successful result creates a new immutable company frontier; a metric or source gap stays explicit.</p><small>{number(unmeasuredExactMoves.length, 0)} exact move without a contract · {measurementQueueCount} queued measurement search{nextMeasurementJob.payload?.entity_id ? ` · next ${nextMeasurementJob.payload.entity_id} / ${nextMeasurementJob.payload.option_id}` : " · event refinement is the current gate"}</small></div><Status ok={measurementQueueCount > 0}>{nextMeasurementJob.status ? String(nextMeasurementJob.status).replaceAll("_", " ") : "waiting for exact event"}</Status>{nextMeasurementJob.payload?.request_path ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(nextMeasurementJob.payload.request_path)}><FileText size={14} />Inspect measurement request</button> : null}</div>
    {latestStrategyProgram.request_sha256 ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Integrated-program discriminator · {latestStrategyProgram.entity_id}</strong><p>{number(latestStrategyProgram.candidate_program_count, 0)} compatible bundles share {number(latestStrategyProgram.observed_exact_option_event_count, 0)} observed option anchors. Status: {String(latestStrategyProgram.status).replaceAll("_", " ")}. An option event cannot establish adoption of the whole bundle.</p>{latestProgramDiscriminators.length ? <small>Common spine: {(latestStrategyProgram.common_option_ids || []).join(" + ")} · choices that distinguish the live programs: {latestProgramDiscriminators.join(" · ")}</small> : null}<small>{latestStrategyProgram.next_activation}{latestStrategyProgram.learning_schedule_rank ? ` · learning-queue rank ${latestStrategyProgram.learning_schedule_rank} · ${number(latestStrategyProgram.attempts, 0)} attempts` : ""}</small></div><Status ok={latestStrategyProgram.status === "prospective_outcome_plan_frozen"}>{latestStrategyProgram.classification ? String(latestStrategyProgram.classification).replaceAll("_", " ") : "primary-source search queued"}</Status>{latestStrategyProgram.artifact_path ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(latestStrategyProgram.artifact_path)}><FileText size={14} />Inspect program evidence</button> : null}</div> : null}
    {strategyProgramControlAcquisition.card_count ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Composition-control acquisition</strong><p>The engine compares each integrated program with the same constituent move phenotypes executed without joint-program evidence, plus same-size local peaks under the same operating readout. This isolates program composition from merely owning the ingredients.</p><small>{number(strategyProgramControlAcquisition.admitted_fragmented_control_count, 0)} fragmented control · {number(strategyProgramControlAcquisition.admitted_local_peak_control_count, 0)} local-peak control{nextProgramControl.work_id ? ` · next ${nextProgramControl.entity_id} via ${nextProgramControl.work_id}` : " · awaiting a matched source-bound control"}</small></div><Status ok={number(strategyProgramControlAcquisition.admitted_source_control_count, 0) > 0}>{number(strategyProgramControlAcquisition.admitted_source_control_count, 0) > 0 ? "source control admitted" : "acquiring controls"}</Status>{state.paths?.strategy_program_control_acquisition_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_program_control_acquisition_latest)}><FileText size={14} />Inspect composition controls</button> : null}</div> : null}
    {strategyProgramComparison.comparison_sha256 ? <div className="capital-closure-rule"><Activity size={20} /><div><strong>Integrated-program operating comparison</strong><p>Every admitted control receives its own assessment-time baseline and future horizon; constituent move outcomes are never recycled onto the program clock. Exact environment strata compare integrated frontier programs with the same moves lacking joint evidence, exact one-choice-less programs, and local-only peaks.</p><small>{number(strategyProgramComparison.treated_episode_count, 0)} integrated outcomes · {number(strategyProgramComparison.control_episode_count, 0)} matched control outcomes · {number(strategyProgramComparison.reviewable_composition_card_count, 0)} composition / {number(strategyProgramComparison.reviewable_one_choice_card_count, 0)} one-choice associations reviewable. These are operating associations, not causal or security-return credit.</small></div><Status ok={Boolean(strategyProgramComparison.operating_association_reviewable)}>{String(strategyProgramComparison.status || "collecting").replaceAll("_", " ")}</Status>{state.paths?.strategy_program_comparison_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_program_comparison_latest)}><FileText size={14} />Inspect program comparison</button> : null}</div> : null}
    {strategyStateExperiment.experiment_sha256 ? <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Frozen move → company state → operating outcome test</strong><p>{strategyStateExperiment.strategy_action?.entity_id}: {strategyStateExperiment.evaluation_contract?.primary_question}</p><small>{number(strategyStateControlAudit.bound_request_count, 0)} same-plan peer result bound · {number(strategyStateControlAudit.eligible_control_count, 0)} usable untreated peer · industry-state baseline {String(strategyStateControlAcquisition.industry_state_control?.status || "missing").replaceAll("_", " ")}. {strategyStateControlAcquisition.next_activation || "Run the strategy business clock."}</small></div><Status ok={Boolean(strategyStateControlAcquisition.eligible_no_family_controls_exist) && strategyStateControlAcquisition.industry_state_control?.status === "ready"}>{strategyStateControlAcquisition.status === "no_eligible_same_environment_control" ? "comparison unavailable" : String(strategyStateControlAcquisition.status || strategyStateExperiment.status).replaceAll("_", " ")}</Status>{state.paths?.strategy_state_control_acquisition_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_state_control_acquisition_latest)}><FileText size={14} />Inspect control audit</button> : state.paths?.strategy_state_experiment_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_state_experiment_latest)}><FileText size={14} />Inspect experiment</button> : null}</div> : null}
    {strategyStateSuccessor.readiness_sha256 ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Successor design verdict</strong><p>{number(strategyStateSuccessorPeers.contaminated_count, 0)} of {number(strategyStateSuccessorPeers.same_environment_count, 0)} same-environment peers made the focal move family; {number(strategyStateSuccessorPeers.clean_count, 0)} remain usable as untreated controls and {number(strategyStateSuccessorPeers.pending_count, 0)} remain unresolved.</p><small>{strategyStateSuccessor.status === "same_environment_candidate_set_exhausted" ? "This matched-peer design is exhausted. The engine will not relabel family adopters or spend calls repeating settled semantic queries." : `Next: ${String(strategyStateSuccessor.next_activation?.transition || "compile successor").replaceAll("_", " ")}.`} Successor deadline {String(strategyStateSuccessor.state_horizon?.successor_must_open_before || "unknown").slice(0, 10)}.</small></div><Status ok={number(strategyStateSuccessorPeers.clean_count, 0) > 0}>{String(strategyStateSuccessor.status || "awaiting successor").replaceAll("_", " ")}</Status>{state.paths?.strategy_state_successor_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_state_successor_latest)}><FileText size={14} />Inspect successor audit</button> : null}</div> : null}
    {strategyStateTransitionJoin.join_sha256 ? <div className="capital-closure-rule"><Activity size={20} /><div><strong>Strategy × company-state path model</strong><p>{number(strategyStateTransitionJoin.transition_episode_count, 0)} entity transitions · {number(maxCaliberJoinLane.certified_unexposed_two_step_path_count ?? strategyPathInput.rows?.filter((row) => row.strategy_exposure === "unexposed").length, 0)} certified unexposed two-step paths · {number(maxCaliberJoinLane.exposed_two_step_path_count ?? strategyPathInput.rows?.filter((row) => row.strategy_exposure === "exposed").length, 0)} exposed two-step paths · {number(strategyStateTransitionJoin.fit_qualified_issuer_count, 0)} fit-qualified issuers.</p><small>The executable challenger is ordinary directed-Markov path odds tilted by one pre-outcome strategy phenotype × sustained-durability feature. It is also an offset path-logit, so value must come from transfer across later periods and unseen issuers. Missing input: {(strategyPathInput.missing_inputs || ["none"]).map((value) => strategyPathMissingLabels[value] || String(value).replaceAll("_", " ")).join(" · ")}. Activation: {String(strategyPathLagrangian.status || "awaiting gates").replaceAll("_", " ")}. {nextStateEvent.work_id ? `Next evidence job: ${nextStateEvent.entity_id} exact-event refinement at scheduler rank #${number(nextStateEvent.rank, 0)}${subscriptionResearch.daily_dispatch_budget?.exhausted ? "; waiting for the next UTC subscription window" : ""}. ` : ""}{strategyStateTransitionJoin.next_activation} No causal or trading authority.</small></div><Status ok={strategyPathLagrangian.status === "survived_initial_controls"}>{String(strategyStateTransitionJoin.status || "collecting").replaceAll("_", " ")}</Status>{state.paths?.strategy_path_lagrangian_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_path_lagrangian_latest)}><FileText size={14} />Inspect activation</button> : state.paths?.strategy_state_transition_join_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_state_transition_join_latest)}><FileText size={14} />Inspect path join</button> : null}</div> : null}
    {maxCaliberRecovery.result_sha256 ? <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>MaxCal recovery gate</strong><p>The engine planted a known path tilt and a zero-signal null into the exact {Object.values(maxCaliberRecovery.partition_row_counts || {}).reduce((sum, value) => sum + Number(value || 0), 0)}-row company-path panel, fit on visible rows only, and scored both sealed partitions. False promotion was {pct(maxCaliberRecovery.null?.false_promotion_rate, 1)} (must be ≤5%); injected power was {pct(maxCaliberRecovery.injected?.power, 1)} (must be ≥80%); sign recovery was {pct(maxCaliberRecovery.injected?.fitted_theta_sign_recovery_rate, 1)}.</p><small>Verdict: {String(maxCaliberGate.status || "unavailable").replaceAll("_", " ")}. The observed historical tilt does not pass. The same-feature offset path-logit reproduces MaxCal to maximum probability error {number(maxCaliberRecovery.same_feature_offset_logit?.max_abs_probability_error, 18)}, so this form can earn compact-transfer credit but not a distinct physics-model claim. {maxCaliberJoinJob.work_id ? `${maxCaliberJoinJob.entity_id} exact-event refinement at scheduler rank #${number(maxCaliberJoinJob.rank, 0)} can improve the separate strategy-join lane; it cannot change this recovery score. ` : ""}{maxCaliberReadiness.next_activation || maxCaliberGate.next_activation}</small></div><Status ok={maxCaliberReadiness.status === "ready_for_conditioned_tournament"}>{maxCaliberReadiness.status === "ready_for_conditioned_tournament" ? "tournament ready" : "fit blocked"}</Status>{state.paths?.max_caliber_recovery_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.max_caliber_recovery_latest)}><FileText size={14} />Inspect recovery audit</button> : null}</div> : null}
    {strategyLawInduction.schema ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Recursive law induction</strong><p>The typed grammar generated {number(strategyLawInduction.source_program_count, 0)} candidate predicates and retained {number(strategyLawInduction.source_frontier_count, 0)} non-dominated law forms after logical subsumption and current-evidence equivalence checks. The executable predicates are eq, ne, same-as-focal, exact-adoption, all-of, and any-of; each is run against the target move and environment before transfer. {number(strategyLawInduction.eligible_candidate_count, 0)} can influence policy review; the rest remain falsifiable conjectures.</p><small>Next evidence: {(strategyLawInduction.next_activation || []).slice(0, 3).map((value) => String(value).replaceAll("_", " ")).join(" · ") || "no next evidence recorded"}</small></div>{state.paths?.strategy_law_induction_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_law_induction_latest)}><FileText size={14} />Inspect induced laws</button> : null}</div> : strategyLawCandidates.length ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>First granular law under test</strong><p>{strategyLawCandidates[0].name}. It asks whether this exact source-bound move phenotype improves earnings durability; the mechanism graph then tests whether durability plus price-implied expectations predicts return. Current verdict: {String(strategyEvaluation.status || "awaiting panel").replaceAll("_", " ")}.</p></div></div> : null}
    <div className="capital-closure-rule"><TrendingUp size={20} /><div><strong>Strategy consequence → priced worlds</strong><p>{strategyValuationBridge.activation_point || "Freeze a measurable operating hurdle and price baseline and hurdle worlds. The probability forecaster never sees their payoff difference."} Current law-transfer status: {String(strategyValuationBridge.status || "awaiting strategy learning cycle").replaceAll("_", " ")}.</p><small>Ordinal option scores never become financial magnitudes. The current direct bridge assumes zero incremental payoff when the hurdle fails and has no separate implementation-cost/downside world; it can earn only conditional paper-challenger status.</small></div>{state.paths?.strategy_valuation_bridge_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_valuation_bridge_latest)}><FileText size={14} />Inspect activation point</button> : null}</div>
    <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>What must happen before the system learns a rule</strong><p>The current conjecture needs {number(strategyHoldoutRequired.treated_units, 4)} independent adopters, {number(strategyHoldoutRequired.control_units, 4)} bounded non-adopters, and {number(strategyHoldoutRequired.transfer_environments, 2)} environments after its freeze date, plus the declared power, direction, pretrend, and multiplicity checks. It currently has {number(strategyHoldoutObserved.independent_treated_units, 0)}, {number(strategyHoldoutObserved.bounded_control_units, 0)}, and {number(strategyHoldoutObserved.transfer_environments, 0)}. Related-family companies are excluded rather than reused as controls.</p></div><Status ok={Boolean(strategyHoldout.eligible)}>{strategyHoldout.eligible ? "promotion evidence met" : "still a conjecture"}</Status></div>
    <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Transfer memory</strong><p>{number(strategyTransfer.card_count, 0)} exact law card{number(strategyTransfer.card_count, 0) === 1 ? "" : "s"} preserve moderator slices, {number(strategyTransfer.settled_operating_outcome_count, 0)} settled operating outcomes, and {number(strategyTransfer.counterexample_count, 0)} break cases. Status: {String(strategyTransfer.status || "awaiting compilation").replaceAll("_", " ")}.</p></div>{state.paths?.strategy_transfer_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_transfer_latest)}><FileText size={14} />Inspect transfer index</button> : null}</div>
    <div className="capital-closure-rule"><TrendingUp size={20} /><div><strong>Strategy-to-alpha discriminator</strong><p>The registered tournament compares zero-residual, momentum, valuation, fixed value-quality, and typed strategy-residual forecasts frozen under one procedure identity. The first four are deterministic. One web-disabled subscription call sees business evidence and the operating hurdle—but not valuation, security control, or payoff—and estimates only the hurdle probability. The hurdle forecast receives its own Brier score; the derived return must separately beat every control after costs, factor adjustment, and multiplicity correction. Status: {String(strategyAlphaTournament.status || "awaiting outcomes").replaceAll("_", " ")} · {number(strategyAlphaBinding.bound_count, 0)} bound diagnostic/prospective block · {number(strategyAlphaTournament.eligible_episode_count, 0)} matured eligible blocks · {number(strategyHurdleCalibration.settled_forecast_count, 0)} operating probabilities scored.</p></div></div>
    <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>First prospective strategy experiment</strong><p>{number(strategyAlphaSources.exact_event_source_count, strategyAlphaSources.exact_direct_source_count)} exact event across {number(strategyAlphaSources.exact_event_issuer_count, 0)} issuers · {number(strategyAlphaSources.exact_direct_source_count, 0)} with terminal operating hurdles · {number(strategyAlphaSources.eligible_source_count, 0)} issuance-ready · gate {String(strategyAlphaIssuance.status || "unknown").replaceAll("_", " ")}. {strategyAlphaSources.next_activation || "Acquire a candidate-bound strategy frontier, then issue the blind operating-hurdle forecast."}</p><small>{Object.entries(strategyAlphaSources.gap_counts || {}).map(([gap, count]) => `${count} ${String(gap).replaceAll("_", " ")}`).join(" · ") || "No source-readiness gap recorded."}{strategyAlphaIssuance.open_issuer_limit ? ` · prospective cohort ${number(strategyAlphaIssuance.current_abi_open_issuer_count, 0)}/${number(strategyAlphaIssuance.open_issuer_limit, 8)} issuers; ${number(strategyAlphaIssuance.cohort_enrollment_days, 1)}-day enrollment; overlapping windows remain one inference block` : ""}{(strategyAlphaSources.lineage_repair_entity_ids || []).length ? ` · lineage repair: ${strategyAlphaSources.lineage_repair_entity_ids.join(", ")}` : ""}{strategyAlphaSources.activation?.queued_event_refinements?.length ? ` · exact-date frontier: ${strategyAlphaSources.activation.queued_event_refinements.map((row) => row.entity_id).join(", ")}` : ""}{number(strategyAlphaIssuance.legacy_unsettled_count, 0) ? ` · ${number(strategyAlphaIssuance.legacy_unsettled_count, 0)} legacy open windows retained but nonblocking` : ""}{strategyAlphaIssuance.experiment_not_before ? ` · next cohort after ${strategyAlphaIssuance.experiment_not_before}` : ""}{strategyAlphaSources.activation?.queued_acquisitions?.[0] ? ` · acquiring ${strategyAlphaSources.activation.queued_acquisitions[0].entity_id} ${String(strategyAlphaSources.activation.queued_acquisitions[0].option_id).replaceAll("_", " ")} terminal hurdle` : ""}{strategyAlphaSources.activation?.queued_repairs?.[0] ? ` · worker ${strategyAlphaSources.activation.owner} owns ${strategyAlphaSources.activation.queued_repairs[0].work_id} at priority ${number(strategyAlphaSources.activation.queued_repairs[0].priority, 0)}` : ""}{strategyAlphaSources.activation?.next_dispatch_at ? ` · next budget window ${strategyAlphaSources.activation.next_dispatch_at}` : ""}</small></div><Status ok={number(strategyAlphaSources.eligible_source_count, 0) > 0}>{String(strategyAlphaSources.status || "awaiting source").replaceAll("_", " ")}</Status></div>
    <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Issue-time binding gate</strong><p>{number(strategyAlphaBinding.bound_count, 0)} bound · {number(strategyAlphaBinding.bindable_count, 0)} awaiting binding · {number(strategyAlphaBinding.run_count, 0)} nominated runs retained. Deterministic controls, target-blind probability, residual, and procedure hash must be frozen before the return window opens.{latestStrategyActivation.run_id ? ` Latest: ${latestStrategyActivation.run_id} via ${latestStrategyActivation.action_id}; capital weight remains zero.` : ""}</p></div><Status ok={number(strategyAlphaTournament.eligible_episode_count, 0) > 0}>{number(strategyAlphaTournament.eligible_episode_count, 0) > 0 ? "eligible prospective evidence" : number(strategyAlphaBinding.bound_count, 0) > 0 ? "legacy lineage only" : "awaiting contract"}</Status></div>
    <div className="capital-closure-rule"><TrendingUp size={20} /><div><strong>One move, two consequences</strong><p>The capital cycle can reserve one zero-weight research slot that freezes the exact move, operating metric, horizon, benchmark, and available factor controls. The operating consequence asks whether the business changed; the security consequence asks what the stock returned after benchmark or factor control. {strategyDualOutcomes.next_activation || "Issue the first eligible dual contract."} Neither consequence proves the other, and the join cannot change rank or portfolio weight.</p></div><Status ok={number(strategyDualOutcomes.settled_count, 0) > 0}>{String(strategyDualOutcomes.status || "awaiting issue").replaceAll("_", " ")}</Status></div>
    <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Automatic operating settlement</strong><p>{strategyOutcomeAcquisition.next_activation || "Declare a measurable outcome contract."} The selector freezes the latest admitted pre-event baseline and earliest eligible post-horizon observation; it cannot choose a favorable endpoint after seeing the result.</p></div></div>
    <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Automatic program settlement</strong><p>{strategyProgramOutcomeAcquisition.next_activation || "Confirm an integrated program before measuring its later operating readout."} The same point-in-time selector uses the latest pre-assessment baseline and earliest post-horizon observation. The resulting episode describes company performance after the bundle; causal program credit remains disabled.</p></div></div>
    <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Integrated-program transfer memory</strong><p>{strategyProgramTransfer.next_activation || "Accumulate independent integrated-program outcomes."} Programs transfer only when their sorted constituent mechanism phenotypes match; company-specific option names do not create equivalence.</p><small>{number(strategyProgramTransfer.card_count, 0)} program phenotype card · {number(strategyProgramTransfer.settled_episode_count, 0)} settled episode · causal and rank authority disabled</small></div>{state.paths?.strategy_program_transfer_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_program_transfer_latest)}><FileText size={14} />Inspect program memory</button> : null}</div>
    {frontierEvolution.length ? <><div className="capital-tournament-list">{frontierEvolution.slice(-6).reverse().map((row) => { const exactFamilyPersistence = number(row.mechanism_families?.jaccard, 0) === 1; const constraints = row.constraint_evolution || {}; const constraintChangeCount = number(constraints.added?.length, 0) + number(constraints.removed?.length, 0) + number(constraints.revised?.length, 0); return <article key={row.evolution_sha256}><GitBranch size={23} /><div><strong>{row.entity_id} · representation drift</strong><p>Broad family overlap {pct(row.mechanism_families?.jaccard, 0)} · phenotype overlap {pct(row.mechanism_phenotypes?.jaccard, 0)} · option-id overlap {pct(row.option_ids?.jaccard, 0)}</p><span>Predicates +{number(constraints.added?.length, 0)} / −{number(constraints.removed?.length, 0)} / revised {number(constraints.revised?.length, 0)} · bundles newly admitted {number(constraints.newly_admitted_bundles?.length, 0)} / excluded {number(constraints.newly_excluded_bundles?.length, 0)}</span><span>{String(row.earlier_evidence_epoch).slice(0, 10)} → {String(row.later_evidence_epoch).slice(0, 10)} · source-representation revision, not an observed business outcome</span></div><Status ok={exactFamilyPersistence && constraintChangeCount === 0}>{exactFamilyPersistence && constraintChangeCount === 0 ? "representation preserved" : "inspect revision"}</Status></article>; })}</div>{frontierEvolution.length > 6 ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Representation-drift audit</strong><p>Showing the six newest comparisons of {number(frontierEvolution.length, 0)}. The complete immutable history remains in the move-library artifact.</p></div>{state.paths?.strategy_move_learning_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_move_learning_latest)}><FileText size={14} />Inspect all comparisons</button> : null}</div> : null}</> : null}
    <div className="capital-tournament-list">{measurableStrategyMoves.map((move) => <article key={move.move_sha256}><Layers3 size={23} /><div><strong>{move.entity_id} · {String(move.kind).replaceAll("_", " ")}</strong><p>{move.description}</p><span>{String(move.causal_panel_status || "requires_adoption_event").replaceAll("_", " ")} · {(move.outcome_contracts || []).map((row) => `${String(row.metric_id).replaceAll("_", " ")} · due ${String(row.due_at || "unknown").slice(0, 10)}`).join(" · ")}</span></div><Status ok={Boolean((move.outcome_episodes || []).length)}>{String(move.evidence_grade || "option_only").replaceAll("_", " ")}</Status></article>)}</div>
    <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Next evidence</strong><p>{strategyMoveLearning.next_activation || "Compile an exact move and outcome contract."} Before/after observations remain descriptive; comparator-adjusted episodes still require the causal-learning lane to validate identification assumptions.</p></div>{state.paths?.strategy_move_learning_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_move_learning_latest)}><FileText size={14} />Inspect move library</button> : null}</div>
    <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Comparable-company acquisition</strong><p>{strategyCohortResearch.next_activation || "Select peers and search primary sources for exact phenotype adoptions."} Exact phenotype, related-family treatment, provisional no-family observation, and source gap are separate. Related treatment remains excluded from the strict P-versus-no-adoption panel.</p></div>{state.paths?.strategy_cohort_research_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(strategyCohortResearch.pilot_plan_path || state.paths.strategy_cohort_research_latest)}><FileText size={14} />Inspect cohort plan</button> : null}</div>
    {strategyCohortResearch.law_blind_environment_probe_count ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Law-blind exploration firewall</strong><p>{number(strategyCohortResearch.law_blind_environment_probe_count, 0)} of each five strategy dispatches is reserved for an environment selected without promoted laws, adoption labels, outcomes, support status, or cohort-gap scores. Current probe: {(strategyCohortResearch.law_blind_environment_probes || []).map((row) => `${row.peer_entity_id} · ${row.selected_industry_id}`).join(" · ")}.</p><small>This lane searches for counterexamples and missing moderators; it cannot rank a security or allocate capital.</small></div><Status ok>active</Status></div> : null}
    {strategyActiveComparator.active_comparator_frontier_sha256 ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Exact phenotype P versus active family alternative Q</strong><p>The separate eligibility frontier found {number(activeComparatorAudit.partition_counts?.eligible_active_alternative, 0)} eligible Q memberships, {number(activeComparatorAudit.partition_counts?.missing_history, 0)} source-history gaps, {number(activeComparatorAudit.partition_counts?.awaiting_post_outcome, 0)} recent events awaiting a future fiscal outcome, and {number(activeComparatorAudit.partition_counts?.ambiguous_or_contaminated, 0)} ambiguous, bundled, repeated, or crossover-contaminated memberships across {number(activeComparatorAudit.comparison_group_count, 0)} grammar projections. It ran no effect estimate because {number(activeComparatorAudit.floor_ready_cell_count, 0)} same-industry/calendar cells meet the independent-firm floors.</p><small>Next Company Facts: {(strategyActiveComparator.next_company_facts_acquisition_entities || []).join(", ") || "none"}. Complete source attempted but history still insufficient: {(strategyActiveComparator.company_facts_source_gap_entities || []).join(", ") || "none"}. Q is a typed relation to P; the engine does not invent an unseen full Q phenotype.</small></div>{state.paths?.strategy_active_comparator_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_active_comparator_latest)}><FileText size={14} />Inspect active-comparator frontier</button> : null}</div> : null}
    <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Point-in-time panel</strong><p>{strategyEvaluation.reason || strategyCausalPanel.next_activation || "Derive filing-bounded durability histories after peer classification."} The grammar may close while grain selection stays open; operating outcomes must decide among viable projections. Agent classifications cannot promote a law or alter capital policy.</p></div>{strategyCausalPanel.projection_frontier_path ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(strategyCausalPanel.projection_frontier_path)}><FileText size={14} />Inspect grain frontier</button> : null}</div>
  </Section>;
}

function StrategyFrontier({ state, onPreview }) {
  const decisions = state.decisions || [];
  const representationReplay = (state.market_flow_experiments || []).find(
    (row) => row.schema === "jaggedthoughts-company-state-representation-replay-v1",
  ) || {};
  const representationLosses = representationReplay.mean_cross_entropy || {};
  const reversibleComparison = representationReplay.comparisons?.reversible_joint || {};
  const constraintEvidenceJobs = state.strategy_constraint_evidence_jobs || [];
  const liveConstraintEvidence = constraintEvidenceJobs.find(
    (row) => ["queued", "claimed"].includes(row.status),
  ) || constraintEvidenceJobs[0] || {};
  const liveConstraintPayload = liveConstraintEvidence.payload || {};
  const liveConstraintMode = number(liveConstraintPayload.candidate_effect_count, 0) >= 2
    ? "competing-rule discrimination"
    : "single-rule falsification only";
  const liveConstraintLearning = (state.learning_schedule?.actions || []).find(
    (row) => row.work_id === liveConstraintEvidence.work_id,
  ) || {};
  const liveConstraintYield = liveConstraintLearning.components || {};
  const constraintBudget = state.subscription_research?.daily_dispatch_budget || {};
  const constraintChain = state.subscription_research?.frozen_chain_lane || {};
  const constraintIsNext = constraintChain.next_work_id === liveConstraintEvidence.work_id;
  const workedFrontier = (state.company_strategy_frontiers || []).find(
    (row) => row.company?.data_class === "reference_fixture",
  ) || {};
  const workedChoiceSpace = workedFrontier.choice_space_certificate || {};
  const workedProgram = (workedFrontier.frontier_programs || []).find(
    (row) => (row.unique_option_ids || []).length > 2,
  ) || (workedFrontier.frontier_programs || [])[0] || {};
  const workedRejection = (workedChoiceSpace.excluded_bundles || [])[0] || {};
  const companyFrontiers = (state.company_strategy_frontiers || []).filter(
    (row) => row.company?.data_class !== "reference_fixture",
  );
  const strategyMoves = state.strategy_move_learning?.moves || [];
  const strategyPathShadow = state.strategy_path_shadow || {};
  const strategyEventResearchQueue = strategyPathShadow.event_research_queue || [];
  const strategyEventResearchAcquisition = state.strategy_event_research_acquisition || {};
  const strategyEventDiscoveryOutcomes = strategyEventResearchAcquisition.discovery_outcomes || [];
  const strategyEventResearchActivations = strategyEventResearchAcquisition.research_activations || [];
  const strategyEventPriorityUpdates = strategyEventResearchAcquisition.research_priority_updates || [];
  const strategyEventLearningUnits = state.strategy_event_learning_units || {};
  const strategyCorpus = state.historical_strategy_bulk_learning || {};
  const strategyLawSearch = state.historical_strategy_law_search || {};
  const strategyLawTrial = state.historical_strategy_law_trial || {};
  const strategyLawSupport = (strategyLawTrial.results || [])[0]?.support || {};
  const transferableStrategyLaws = (state.institutional_learning?.evaluations || []).filter(
    (row) => row.status === "prospective_transfer_candidate",
  ).length;
  return <>
    <Section eyebrow="JaggedThoughts" title="Three nested strategy frontiers"
      description="The shared form is a configuration of interacting choices evaluated under rival mechanisms. Each layer keeps its own identity and constraints.">
      <div className="capital-frontier-flow">
        <article><span>1</span><Layers3 size={22} /><strong>Company strategy</strong><p>Choice graph, reinforcing activities, tensions, credible moves, and failure transitions.</p><code>choices → local moves</code></article>
        <ArrowRight className="capital-frontier-arrow" />
        <article><span>2</span><GitBranch size={22} /><strong>Investment policy</strong><p>Evidence-conditioned watch, size, hold, trim, exit, and hedge programs.</p><code>state → contingent action</code></article>
        <ArrowRight className="capital-frontier-arrow" />
        <article><span>3</span><TrendingUp size={22} /><strong>Portfolio strategy</strong><p>Compatible plays under shared capital, downside, turnover, and concentration limits.</p><code>plays → allocation frontier</code></article>
      </div>
      <div className="capital-discovery-status">
        <div><span>Source events classified</span><strong>{number(strategyCorpus.classified_event_count, 0)}</strong><small>point-in-time public evidence</small></div>
        <div><span>Frozen child laws</span><strong>{number(strategyLawSearch.frozen_child_candidate_count ?? state.strategy_business_clock?.historical_strategy_frozen_child_candidate_count, 0)}</strong><small>outcome-blind recursive search</small></div>
        <div><span>Sealed trial support</span><strong>{number(strategyLawSupport.treated_entity_count, 0)} + {number(strategyLawSupport.future_adopter_entity_count, 0)}</strong><small>treated + future adopters; target 4 + 4</small></div>
        <div><span>Transferable laws</span><strong>{number(transferableStrategyLaws, 0)}</strong><small>only settled prospective survivors count</small></div>
      </div>
      <div className="capital-closure-rule"><Activity size={20} /><div><strong>What the engine is doing now</strong><p>Public filings become typed strategy events. The grammar recursively searches coherent mechanism slices without reading their outcomes. A sparse candidate is frozen, new disjoint evidence tries to break it, and only a settled survivor may influence a later paper-policy tournament.</p><small>Search coverage is not learned edge: the four counters above separate acquired evidence, generated conjectures, sealed support, and transferable knowledge.</small></div><Status ok={transferableStrategyLaws > 0}>{transferableStrategyLaws > 0 ? "transfer evidence exists" : "learning in progress"}</Status></div>
      {workedFrontier.strategy_frontier_sha256 ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>One executable example · fictional Alpha Components</strong><p>Four source-declared choices create {number(workedChoiceSpace.bounded_bundle_count, 0)} nonempty bundles up to size {number(workedChoiceSpace.max_bundle_size, 0)}. Z3 admits {number(workedChoiceSpace.feasible_bundle_count, 0)} and rejects {number(workedChoiceSpace.excluded_bundle_count, 0)}. One recursive Pareto survivor is <code>{workedProgram.expression}</code>.</p><small>{workedRejection.option_ids?.length ? `Rejected world: ${workedRejection.option_ids.join(" + ")} ⇒ ${(workedRejection.violated_constraint_ids || []).join(", ")}. ` : ""}Compiler contract {number(workedFrontier.compiler_contract_version, 0)} · fixture for mechanics only · no empirical or capital authority</small></div></div> : null}
      {liveConstraintEvidence.work_id ? <div className="capital-closure-rule"><Search size={20} /><div><strong>Live blind constraint test · {liveConstraintPayload.entity_id || "company"}</strong><p>The candidate rule set is frozen, and the dependent strategy rewrite is held until this test settles. The subscription search sees the business choices, cutoff, and an opaque source embargo—but no candidate predicates or prior source trail. New primary evidence is replayed against every frozen rule before any constraint can receive source-disjoint credit.</p><small>{liveConstraintMode} · {constraintIsNext ? `next research claim${constraintBudget.exhausted ? " when the UTC call budget reopens" : ""}` : String(liveConstraintEvidence.status || "queued").replaceAll("_", " ")} · acquisition rank {liveConstraintLearning.rank ? `#${number(liveConstraintLearning.rank, 0)} of ${number(state.learning_schedule?.queued_action_count, 0)}` : "awaiting schedule refresh"} · {number(liveConstraintPayload.informative_probe_bundle_count, 0)} discriminating feasible worlds → {number(liveConstraintPayload.probe_target_count, 0)} search targets · candidate discrimination {pct(liveConstraintYield.constraint_discrimination_upper_bound, 0)} · falsification surface {pct(liveConstraintYield.constraint_falsification_surface_upper_bound, 0)} · source-disjoint replay {liveConstraintYield.source_disjoint_replay_readiness ? "ready" : "not ready"}</small></div><Status ok={liveConstraintEvidence.status === "claimed" || constraintIsNext}>{liveConstraintEvidence.status === "claimed" ? "running" : constraintIsNext ? "next claim" : "queued"}</Status>{liveConstraintPayload.request_path ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(liveConstraintPayload.request_path)}><FileText size={14} />Inspect frozen request</button> : null}</div> : null}
      {representationReplay.replay_sha256 ? <div className="capital-closure-rule"><Activity size={20} /><div><strong>Did recursive state composition add information?</strong><p>No on the current language. Across {number(representationReplay.inference_block_count, 0)} prior-only next-quarter blocks, the enumerator selected the 2×2 valuation × durability state. Its directed joint loss was {number(representationLosses.directed_joint, 4)}, versus {number(representationLosses.factorized_axes, 4)} for separate axes and {number(representationLosses.reversible_joint, 4)} for the reversible joint control.</p><small>Directed minus reversible {number(reversibleComparison.observed_delta, 4)} · paired p {number(reversibleComparison.p_value, 4)} · a changed axis or separately sealed trial is required before reopening this mechanism family</small></div><Status ok={false}>representation rejected</Status><button type="button" className="capital-link" onClick={() => onPreview && onPreview(representationReplay.summary_path)}><FileText size={14} />Inspect replay</button></div> : null}
      {strategyEventResearchQueue.length ? <div className="capital-closure-rule"><Search size={20} /><div><strong>What does a new strategy event make the investor do?</strong><p>An admitted filing opens a bounded company refresh. Cases where the typed and untyped operating forecasts disagree are inspected first because they can distinguish the models—not because they are presumed attractive.</p><small>{strategyEventResearchQueue.map((row) => `#${number(row.research_priority_rank, 0)} ${row.entity_id} · model gap ${pct(row.operating_model_disagreement, 2)}`).join(" · ")}. {strategyEventDiscoveryOutcomes.length ? `Latest compiler result: ${strategyEventDiscoveryOutcomes.map((row) => `${row.entity_id} → ${String(row.state || "unknown").replaceAll("_", " ")}${row.reason ? ` (${row.reason})` : ""}`).join(" · ")}.` : "The next capital cycle will fetch public fundamentals and compile exact candidate states."}{strategyEventResearchActivations.length ? ` Research handoff: ${strategyEventResearchActivations.map((row) => `${row.entity_id} → ${String(row.research_population || row.status).replaceAll("_", " ")}`).join(" · ")}.` : ""}{strategyEventPriorityUpdates.length ? ` Information-value queue priority: ${strategyEventPriorityUpdates.map((row) => `${row.entity_id} ${number(row.research_priority, 0)}`).join(" · ")}.` : ""}</small></div>{strategyEventResearchActivations.length ? <Status ok>{strategyEventResearchActivations.map((row) => row.research_population === "strategy_learning" ? "strategy learning queued" : "underwriting queued").join(" · ")}</Status> : null}{state.paths?.strategy_event_research_acquisition_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_event_research_acquisition_latest)}><FileText size={14} />Inspect event research</button> : <Status ok={false}>queued</Status>}</div> : null}
      {(strategyEventLearningUnits.units || []).length ? <div className="capital-decision-list">{strategyEventLearningUnits.units.map((row) => <article key={row.unit_sha256}><Activity size={22} /><div><strong>{row.entity_id} · {String(row.stage || "unknown").replaceAll("_", " ")}</strong><p>{row.next_activation}</p><span>Operating: {row.operating_settlement_sha256 ? "settled" : row.operating_due_at ? `due ${String(row.operating_due_at).slice(0, 10)}` : "not contracted"} · Return: {row.return_settlement_sha256 ? "settled" : row.return_due_at ? `due ${String(row.return_due_at).slice(0, 10)}` : "not contracted"}</span></div><Status ok={row.joined_evidence_ready}>{row.joined_evidence_ready ? "joined evidence ready" : "awaiting activation"}</Status></article>)}</div> : null}
      <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Closure is always scope-relative</strong><p>A certificate closes only the declared grammar, depth, mechanism committee, and constraints. Representation residuals record what the language may have missed.</p></div></div>
    </Section>
    <BusinessStrategyLearning state={state} onPreview={onPreview} />
    <Section eyebrow="Industry response compiler" title="Company choice-system frontiers"
      description="A source-bound industry model names customers, suppliers, rivals, entrants, substitutes, complements, and material changes. Accepted dossiers can now activate a subscription agent that proposes options and counterfactuals; the typed compiler rejects source drift and recursively enumerates reinforcing systems and tensions. Scenario consequences place them on global and single-choice local frontiers.">
      {companyFrontiers.length ? <div className="capital-decision-list">{companyFrontiers.map((row) => {
        const grammar = row.grammar || {};
        const choiceSpace = row.choice_space_certificate || {};
        const constraintAuthority = choiceSpace.constraint_authority || {};
        const prerequisite = (row.feasibility_constraints?.prerequisites || [])[0];
        const explanation = row.explanation_chain || (prerequisite ? {
          evidence_refs: prerequisite.evidence_refs || [],
          predicates: [{
            expression: `${prerequisite.option_id} => ${(prerequisite.requires || []).join(" + ")}`,
          }],
          gate: {
            status: "accepted",
            sha256: row.company?.strategy_constraint_gate_sha256,
            evidence_grade: row.company?.strategy_constraint_evidence_grade || "legacy_ungraded",
            research_claim_eligible: row.company?.strategy_constraint_research_claim_eligible === true,
          },
          z3_delta: {
            bounded_bundle_count: choiceSpace.bounded_bundle_count,
            feasible_bundle_count: choiceSpace.feasible_bundle_count,
            excluded_bundle_count: choiceSpace.excluded_bundle_count,
          },
          representation: {
            residuals: row.representation_residuals || (row.use_boundary ? [row.use_boundary] : []),
          },
          valuation: { next_transition: row.economic_bridge?.next_transition },
        } : {});
        const explanationPredicates = explanation.predicates || [];
        const z3Delta = explanation.z3_delta || {};
        const firstResidual = (explanation.representation?.residuals || [])[0];
        const exactMoves = strategyMoves.filter((move) => move.strategy_frontier_sha256 === row.strategy_frontier_sha256);
        const settledOutcomes = exactMoves.reduce((total, move) => total + (move.outcome_episodes || []).length, 0);
        const learningStates = [...new Set(exactMoves.map((move) => move.learning_status || move.evidence_grade).filter(Boolean))];
        const contingentPolicies = row.contingent_policy_catalog || [];
        const oneChoiceEdges = row.neighborhood?.edges || [];
        return <article className="capital-strategy-result" key={row.strategy_frontier_sha256}>
        <header><div><span className={`capital-data-class ${row.company?.data_class || "operator"}`}>{row.company?.data_class === "reference_fixture" ? "fictional fixture" : row.company?.profile_authority === "subscription_agent_proposal" ? "agent-compiled · source bound" : "source-bound company"}</span><h3>{row.company?.name || row.company?.id}</h3><p>{row.industry_state?.boundary}</p></div><Status ok={row.scope_closed}>{row.scope_closed ? "declared scope closed" : "enumeration incomplete"}</Status></header>
        <div className="capital-metric-row"><div><span>Compatible bundles</span><strong>{number(row.enumeration?.program_count, 0)}</strong></div><div><span>Exclusion cores</span><strong>{number(row.constraint_witnesses?.length, 0)}</strong></div><div><span>Global frontier</span><strong>{number(row.frontier_program_ids?.length, 0)}</strong></div><div><span>Contingent policies</span><strong>{number(contingentPolicies.length, 0)}</strong></div><div><span>Local peaks</span><strong>{number(row.local_peak_program_ids?.length, 0)}</strong></div><div><span>Decision closed</span><strong>{row.decision_closed ? "yes" : "no"}</strong></div></div>
        <div className="capital-strategy-options">{(row.frontier_programs || []).slice(0, 8).map((program) => { const witness = priorityWitness(row.objective_weight_regions, program.program_id); return <div key={program.program_id}><code>{program.expression}</code><span>coverage {pct(program.objective_values?.industry_pressure_coverage)} · downside resilience {number(program.objective_values?.downside_resilience, 2)} · {witness ? `can lead when priorities are ${witness}` : "Pareto-only; no linear-priority region"}</span></div>; })}</div>
        {contingentPolicies.map((policy) => {
          const regions = policy.policy_action_regions || {};
          const finals = new Map((policy.final_programs || []).map((row) => [row.program_id, row.final_option_ids || []]));
          return <div key={policy.contingent_policy_sha256}><div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Commit, observe, then choose · {String(policy.policy_id).replaceAll("_", " ")}</strong><p>Commit {(policy.commit_option_ids || []).join(" + ") || "nothing"}; no earlier than {policy.recourse_not_before}, select among {(policy.final_programs || []).length} feasible final bundles using {(policy.conditions || []).length} typed evidence conditions.</p><small>Z3 region certificate: {regions.total_over_condition_space ? "complete" : "gap found"} · {regions.deterministic_over_condition_space ? "non-overlapping" : "overlap found"} · {number(regions.unreachable_regions?.length, 0)} unreachable branch{regions.unreachable_regions?.length === 1 ? "" : "es"} · outcomes and thresholds remain empirical</small></div></div><div className="capital-strategy-options">{(regions.regions || []).map((region) => <div key={region.region_sha256}><code>{(region.conditions || []).map((condition) => `${condition.path.replace("firm.", "")} ${condition.operator} ${condition.value}`).join(" AND ") || "otherwise"}</code><span>choose {(finals.get(region.action_id) || []).join(" + ") || region.action_id}</span></div>)}</div></div>;
        })}
        <details className="capital-audit-trail"><summary><GitBranch size={17} /><span><strong>Inspect bounded search anatomy</strong><small>Language, feasible bundles, exclusion proofs, peaks, and exact-frontier outcomes</small></span></summary>
          <div className="capital-strategy-options">
            <div><code>Evidence → predicate → gate → Z3 → blocker</code><span>{(explanation.evidence_refs || []).join(" · ") || "no source-bound business predicate"} → {explanationPredicates[0]?.expression || "cardinality only"}{explanationPredicates.length > 1 ? ` · +${explanationPredicates.length - 1} predicates` : ""} → {explanation.gate?.sha256 ? `accepted ${explanation.gate.sha256.slice(0, 12)}…` : "no accepted gate"} → {number(z3Delta.bounded_bundle_count, 0)} bounded → {number(z3Delta.feasible_bundle_count, 0)} feasible ({number(z3Delta.excluded_bundle_count, 0)} excluded)</span><span>{firstResidual || "no projected representation residual"}{explanation.valuation?.next_transition ? ` · valuation next: ${String(explanation.valuation.next_transition).replaceAll("_", " ")}` : ""} · epistemic grade {String(explanation.gate?.evidence_grade || "not applicable").replaceAll("_", " ")}{explanation.gate?.research_claim_eligible ? " · eligible for research credit" : " · no learning credit"}</span></div>
            <div><code>Proof boundary</code><span>Z3 proves bundle size, declared incompatibilities, prerequisites, and linear resource bounds over this frozen option list. Authored quantities, scenario scores, profitability, causal effects, and security returns remain empirical.</span></div>
            <div><code>{grammar.grammar_id || "strategy grammar"} · {grammar.version || "unversioned"}</code><span>terminals: {(grammar.terminals || []).slice(0, 8).map((item) => item.terminal_id).join(" · ") || "none"}{(grammar.terminals || []).length > 8 ? ` · +${grammar.terminals.length - 8}` : ""}</span><span>operators: {(grammar.operators || []).slice(0, 8).map((item) => `${item.operator_id}(${(item.input_types || []).join(", ")}) → ${item.output_type}`).join(" · ") || "none"}</span></div>
            <div><code>Feasible bundles · {number(choiceSpace.feasible_bundle_count, 0)}</code><span>{(choiceSpace.feasible_bundles || []).slice(0, 8).map((bundle) => (bundle.option_ids || []).join(" + ")).join(" · ") || "none"}{(choiceSpace.feasible_bundles || []).length > 8 ? ` · +${choiceSpace.feasible_bundles.length - 8}` : ""}</span><span>{number(choiceSpace.excluded_bundle_count, 0)} of {number(choiceSpace.bounded_bundle_count, 0)} bounded bundles excluded · {choiceSpace.solver?.name ? `${choiceSpace.solver.name} ${choiceSpace.solver.version || ""} · ${choiceSpace.solver.logic || ""}` : "solver receipt unavailable"}</span></div>
            <div><code>Rejected worlds · {number(choiceSpace.excluded_bundles?.length, 0)}</code><span>{(choiceSpace.excluded_bundles || []).slice(0, 6).map((bundle) => `${(bundle.option_ids || []).join(" + ")} ⇒ ${(bundle.violated_constraint_ids || []).join(", ")}`).join(" · ") || "Older certificate: only aggregate exclusions retained"}{(choiceSpace.excluded_bundles || []).length > 6 ? ` · +${choiceSpace.excluded_bundles.length - 6}` : ""}</span><span>Every rejected bundle names the compiled predicate that made its Z3 assignment unsatisfiable.</span></div>
            <div><code>Predicate ABI</code><span>{(choiceSpace.predicate_catalog || []).map((predicate) => `${predicate.predicate_id} × ${number(predicate.active_constraint_count, 0)}`).join(" · ") || "unavailable"}</span><span>{number(constraintAuthority.dossier_bound_predicate_count, 0) ? `${number(constraintAuthority.dossier_bound_predicate_count, 0)} current-dossier predicate${number(constraintAuthority.dossier_bound_predicate_count, 0) === 1 ? "" : "s"} are source-bound.` : number(constraintAuthority.legacy_profile_predicate_count, 0) ? `${number(constraintAuthority.legacy_profile_predicate_count, 0)} legacy profile predicate${number(constraintAuthority.legacy_profile_predicate_count, 0) === 1 ? "" : "s"} lack the new pair-level source contract.` : (choiceSpace.predicate_catalog || []).some((predicate) => !["cardinality_ge", "cardinality_le"].includes(predicate.predicate_id) && number(predicate.active_constraint_count, 0) > 0) ? "Business predicates are active, but this older certificate lacks the current dossier-authority receipt." : "Only cardinality is active; Z3 closes enumeration but adds no business constraint."}</span></div>
            <div><code>Z3 exclusion witnesses · {number(row.constraint_witnesses?.length, 0)}</code><span>{(row.constraint_witnesses || []).slice(0, 6).map((witness) => `${(witness.option_ids || []).join(" + ")} ⇒ ${(witness.unsat_core_constraint_ids || []).join(", ")}`).join(" · ") || "no declared incompatibilities"}{(row.constraint_witnesses || []).length > 6 ? ` · +${row.constraint_witnesses.length - 6}` : ""}</span></div>
            <div><code>Execution constraints</code><span>{number(row.feasibility_constraints?.incompatibilities?.length, 0)} sourced incompatibility · {number(row.feasibility_constraints?.prerequisites?.length, 0)} prerequisite relation · {number(row.feasibility_constraints?.resources?.length, 0)} bounded resource{number(row.feasibility_constraints?.resources?.length, 0) === 1 ? "" : "s"}</span></div>
            <div><code>Contingent recourse · {number(contingentPolicies.length, 0)}</code><span>{contingentPolicies.length ? contingentPolicies.map((policy) => `${policy.policy_id}: ${(policy.conditions || []).map((condition) => `${condition.path} ${condition.operator} ${condition.value} [${condition.threshold_basis}]`).join("; ")}`).join(" · ") : "no company-level contingent policy declared for this frontier"}</span></div>
            <div><code>Scoring interactions · {number(row.interaction_catalog?.length, 0)}</code><span>{(row.interaction_catalog || []).map((interaction) => `${interaction.interaction_id}: ${(interaction.option_ids || []).join(" + ")}`).join(" · ") || "legacy frontier: interaction lineage not compiled"}</span></div>
            <div><code>One-choice calibration edges · {number(oneChoiceEdges.length, 0)}</code><span>{oneChoiceEdges.slice(0, 4).map((edge) => `${edge.base_expression} → + ${edge.added_option_id}`).join(" · ") || "compile the current frontier to expose exact P → P + option contrasts"}{oneChoiceEdges.length > 4 ? ` · +${oneChoiceEdges.length - 4}` : ""}</span><span>{row.neighborhood?.use_boundary || "Each edge becomes useful only after an observed transition and a credible contrast."}</span></div>
            <div><code>Search topology</code><span>{number(row.neighborhood?.search_edge_count ?? oneChoiceEdges.length, 0)} add/remove/substitute edges · {number(row.neighborhood?.substitution_edge_count, 0)} substitutions</span><span>Local peaks use the wider search topology; operating measurement stays on addition-only contrasts.</span></div>
            <div><code>Global frontier · {number(row.frontier_programs?.length, 0)}</code><span>{(row.frontier_programs || []).slice(0, 6).map((program) => program.expression).join(" · ") || "none"}{(row.frontier_programs || []).length > 6 ? ` · +${row.frontier_programs.length - 6}` : ""}</span></div>
            <div><code>Local peaks · {number(row.local_peak_programs?.length, 0)}</code><span>{(row.local_peak_programs || []).slice(0, 6).map((program) => program.expression).join(" · ") || "none"}{(row.local_peak_programs || []).length > 6 ? ` · +${row.local_peak_programs.length - 6}` : ""}</span></div>
            <div><code>Outcome learning · exact frontier hash</code><span>{exactMoves.length ? `${exactMoves.length} move${exactMoves.length === 1 ? "" : "s"} · ${settledOutcomes} settled operating outcome${settledOutcomes === 1 ? "" : "s"}` : "not yet registered in the move library"}</span><span>{learningStates.length ? learningStates.map((value) => String(value).replaceAll("_", " ")).join(" · ") : "no status inferred from company identity"}</span></div>
          </div>
        </details>
        <footer><span>{row.use_boundary}</span><button type="button" className="capital-link" onClick={() => onPreview && onPreview(row.result_path)}><FileText size={14} />Inspect frontier certificate</button></footer>
      </article>; })}</div> : <Empty title="No company option frontier yet" body="Candidate research can author an industry-state and option profile, then compile it with the company strategy frontier command. Effects and interactions must carry evidence references." />}
    </Section>
    <Section eyebrow="Compiled frontiers" title="Current policy populations">
      {decisions.length ? <div className="capital-decision-list">{decisions.map((row) => <article className="capital-frontier-row" key={row.decision_id}>
        <div><span className={`capital-data-class ${row.data_class}`}>{row.data_class === "operator" ? "operator" : "fixture"}</span><strong>{row.entity?.name || row.entity?.entity_id}</strong><small>{row.decision_id}</small></div>
        <div><span>frontier</span><b>{number(row.frontier_count, 0)}</b></div><div><span>representation</span><b>{row.representation_status || "—"}</b></div><div><span>selected</span><b>{row.selected_action_id || "—"}</b></div>
      </article>)}</div> : <Empty title="No policy frontier compiled" body="Compile an investment profile to enumerate and close its bounded policy population." />}
    </Section>
  </>;
}

function DecisionSummary({ row, onPreview, compact = false, busy = false, onAction }) {
  return <article className={`capital-decision ${row.data_class === "reference_fixture" ? "fixture" : ""}`}>
    <header><div><span className={`capital-data-class ${row.data_class}`}>{row.data_class === "operator" ? row.profile_stage === "draft" ? "operator draft" : "operator active" : "fictional fixture"}</span><h3>{row.entity?.name || row.entity?.entity_id}</h3><p>{row.play?.play_key || row.profile_id}</p></div><Status ok={row.settlement_status === "settled"}>{row.profile_stage === "draft" ? "review required" : row.settlement_status}</Status></header>
    {!compact ? <p className="capital-thesis">{row.thesis_claim || "No thesis claim in the read model."}</p> : null}
    <div className="capital-metric-row"><div><span>Fingerprint</span><strong>{number(row.fingerprint_score, 3)}</strong></div><div><span>Implied excess</span><strong>{pct(row.price_implied_excess_return)}</strong></div><div><span>Hurdle</span><strong>{pct(row.hurdle_rate)}</strong></div><div><span>Robust buy-below</span><strong>{money(row.robust_maximum_price, row.entity?.currency)}</strong></div><div><span>Action</span><strong>{row.selected_action_id || "—"}</strong></div><div><span>Target</span><strong>{pct(row.target_weight)}</strong></div></div>
    {!compact && row.selected_policy_priority_witness ? <div className="capital-decisive"><span>When this policy can lead</span><p>{formatPriorityWitness(row.selected_policy_priority_witness)}</p></div> : null}
    {!compact && row.decisive_observation ? <div className="capital-decisive"><span>Decisive observation</span><p>{row.decisive_observation}</p></div> : null}
    <footer><span>as of {row.as_of}</span><div>{row.profile_stage === "draft" && onAction ? <button type="button" disabled={busy} className="capital-link" onClick={() => onAction("activate", { profile_id: row.profile_id, confirmation: `activate ${row.profile_id} for paper tracking` })}><ShieldCheck size={14} />Activate for paper tracking</button> : null}<button type="button" className="capital-link" onClick={() => onPreview && onPreview(row.decision_path)}><FileText size={14} />Decision</button><button type="button" className="capital-link" onClick={() => onPreview && onPreview(row.report_path)}><FileText size={14} />Memo</button></div></footer>
  </article>;
}

function EquityDraftForm({ busy, onAction }) {
  const [entityId, setEntityId] = useState("IBM");
  const [entityName, setEntityName] = useState("International Business Machines");
  const [thesis, setThesis] = useState("IBM's hybrid-cloud and mission-critical installed base may sustain owner earnings above the expectations embedded in its current price if software mix and cash conversion offset infrastructure maturity.");
  const submit = (event) => {
    event.preventDefault();
    onAction("seed-equity", { entity_id: entityId, entity_name: entityName, benchmark_id: "SPY", benchmark_name: "SPDR S&P 500 ETF Trust", thesis_claim: thesis });
  };
  return <form className="capital-draft-form" onSubmit={submit}>
    <label><span>Ticker</span><input value={entityId} onChange={(event) => setEntityId(event.target.value.toUpperCase())} required /></label>
    <label><span>Company</span><input value={entityName} onChange={(event) => setEntityName(event.target.value)} required /></label>
    <label className="wide"><span>Initial thesis</span><textarea value={thesis} onChange={(event) => setThesis(event.target.value)} rows={4} required /></label>
    <button type="submit" className="copy-button primary" disabled={busy}><Search size={15} />Enroll, refresh & create draft</button>
  </form>;
}

function Plays({ state, onPreview, busy, onAction }) {
  const decisions = state.decisions || [];
  return <>
    <Section eyebrow="Source → draft" title="Start company underwriting"
      description="A new ticker is resolved through the SEC registry, enrolled in the public-source universe, refreshed, screened, and compiled. The profile remains a draft until you review its thesis, assumptions, rival mechanism, and falsifiers.">
      <EquityDraftForm busy={busy} onAction={onAction} />
    </Section>
    <Section eyebrow="Compiled plays" title="Thesis → policy → paper action"
      description="Each record freezes the source epoch, valuation programs, rival mechanisms, frontier certificate, selected action, and paper-book transition.">
      {decisions.length ? <div className="capital-decision-list">{decisions.map((row) => <DecisionSummary key={row.decision_id} row={row} onPreview={onPreview} busy={busy} onAction={onAction} />)}</div>
        : <Empty title="No decisions compiled" body="Create a source-bound draft after refreshing the required public observations." />}
    </Section>
  </>;
}

function Portfolio({ state, onPreview }) {
  const portfolio = state.portfolio;
  const policySurface = <><HouseholdDecisionBrief state={state} /><HouseholdGoalSurface state={state} /><SleeveImplementation state={state} onPreview={onPreview} /></>;
  if (!portfolio) return <>{policySurface}<Section eyebrow="Portfolio" title="Constrained paper assembly"><Empty title="No positive-weight paper book yet" body="The household mandate, current positions, fund evidence, and prospective policy gates appear above. Until they clear, paper watches remain at zero weight and the book stays in cash." /></Section></>;
  const weights = Object.entries(portfolio.selected_target_weights || {});
  const allocationEnvelope = portfolio.continuous_allocation_envelope || {};
  const capacitySummary = (allocationEnvelope.candidate_capacity || []).map((row) => `${row.entity_id} ${pct(row.maximum_feasible_weight)}`).join(" · ");
  const exposureRanges = (allocationEnvelope.exposure_ranges || []).map((row) => {
    const band = row.declared_band || [];
    const declared = `${band[0] == null ? "−∞" : number(band[0])} to ${band[1] == null ? "+∞" : number(band[1])}`;
    return `${row.exposure_id}: ${number(row.minimum_attainable)}–${number(row.maximum_attainable)} attainable (mandate ${declared})`;
  });
  const exposureActivations = (portfolio.feasibility_certificate?.acceptance_checks || []).flatMap((candidate) =>
    (candidate.exposure_activation_ranges || []).flatMap((row) => {
      if (row.maximum_must_be_at_least != null) return [`${candidate.entity_id}: ${row.exposure_id} cap must reach ${number(row.maximum_must_be_at_least)}`];
      if (row.minimum_must_be_at_most != null) return [`${candidate.entity_id}: ${row.exposure_id} floor must fall to ${number(row.minimum_must_be_at_most)}`];
      return [];
    })
  );
  const patientCapital = portfolio.patient_capital || {};
  const patientPolicy = patientCapital.policy || {};
  const patientReview = patientCapital.selected_review || {};
  const rotationActivations = (patientCapital.rejected_rotations || []).flatMap((row) =>
    (row.review?.blockers || []).map((blocker) => blocker.minimum_return_edge_must_be_at_most == null
      ? `${blocker.incumbent_entity_id}: no qualifying replacement capacity`
      : `${blocker.incumbent_entity_id}: rotation edge must fall to ${pct(blocker.minimum_return_edge_must_be_at_most)}`)
  );
  const mechanismCounts = Object.values(portfolio.uncertainty_set?.candidate_mechanism_counts || {}).reduce((total, value) => total + Number(value || 0), 0);
  const metricLabels = {
    expected_excess_return: "mechanism-safe return floor",
    weighted_downside: "mechanism-safe downside ceiling",
    thesis_confidence: "mechanism-safe confidence floor",
    nominal_expected_excess_return: "nominal expected excess",
    nominal_weighted_downside: "nominal weighted downside",
    nominal_thesis_confidence: "nominal thesis confidence",
    robustness_return_cost: "return conservatism",
    robustness_downside_buffer: "downside reserve",
  };
  const selectedRegion = (portfolio.objective_weight_regions?.regions || []).find((row) => row.alternative_id === portfolio.selected_alternative_id);
  const mechanismCertificate = portfolio.mechanism_weight_regions?.certificate || {};
  const mechanismRanges = (mechanismCertificate.regions || []).filter((row) => row.supported).map((row) => {
    const bounds = row.coordinate_bounds?.mechanism_safe_utility || {};
    const lower = rational(bounds.lower_exact);
    const upper = rational(bounds.upper_exact);
    const label = row.alternative_id === portfolio.selected_alternative_id
      ? "mechanism-safe allocation"
      : row.alternative_id === portfolio.nominal_selected_alternative_id
        ? "nominal allocation"
        : `alternative ${String(row.alternative_id).slice(0, 8)}`;
    return `${label}: ${pct(lower, 0)}–${pct(upper, 0)} mechanism weight`;
  });
  const priorityExplanation = selectedRegion?.optimal_across_entire_preference_simplex
    ? "Only one distinct feasible allocation remains, so changing priority weights cannot change the choice."
    : priorityWitness(portfolio.objective_weight_regions, portfolio.selected_alternative_id)
      ? `The selected allocation can lead when priorities are ${priorityWitness(portfolio.objective_weight_regions, portfolio.selected_alternative_id)}.`
      : "Inspect the assembly for constraint and objective witnesses.";
  return <>
    {policySurface}
    <Section eyebrow="Portfolio frontier" title={portfolio.portfolio_id}
      description="Exact accept-or-decline combinations under the configured population bound; the selected allocation is chosen only after the Pareto frontier is retained."
      actions={<button type="button" className="capital-link" onClick={() => onPreview && onPreview("portfolio/latest_assembly.json")}><FileText size={14} />Inspect assembly</button>}>
      <div className="capital-portfolio-summary"><div><span>Combinations</span><strong>{number(portfolio.combination_count, 0)}</strong></div><div><span>Constraint-feasible</span><strong>{number(portfolio.feasibility_certificate?.feasible_assignment_count, 0)}</strong></div><div><span>Rival worlds</span><strong>{number(mechanismCounts, 0)}</strong></div><div><span>Frontier</span><strong>{number((portfolio.frontier_alternative_ids || []).length, 0)}</strong></div><div><span>Mechanism regions</span><strong>{number((mechanismCertificate.supported_alternative_ids || []).length, 0)}</strong></div><div><span>Priority regions</span><strong>{number((portfolio.objective_weight_regions?.supported_alternative_ids || []).length, 0)}</strong></div><div><span>Scope closed</span><strong>{portfolio.scope_closed ? "yes" : "no"}</strong></div></div>
      <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Exact mechanism-safe certificate</strong><p>Z3 admitted {number(portfolio.feasibility_certificate?.feasible_assignment_count, 0)} accept-or-decline combinations against each nominal state and {number(mechanismCounts, 0)} authored rival worlds. No probability was assigned. {priorityExplanation}</p></div></div>
      {mechanismRanges.length ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Exact policy-switch boundaries</strong><p>{mechanismRanges.join(" · ")}. These weights express decision conservatism, not event probabilities.</p></div></div> : null}
      {patientReview.schema ? <div className="capital-closure-rule"><Clock3 size={20} /><div><strong>Patient-owner policy · {String(patientReview.status || "unknown").replaceAll("_", " ")}</strong><p>Holding is the default. A sound incumbent can be reduced only when every reduced unit is matched to a challenger with at least {pct(patientPolicy.minimum_after_cost_return_edge)} more mechanism-safe expected return after both proposal costs. A return floor at {pct(patientPolicy.impairment_return_floor)} or confidence below {pct(patientPolicy.impairment_confidence_floor)} permits an impairment exit. {number(patientCapital.rejected_rotation_count, 0)} portfolio alternatives were rejected for weak rotation.</p>{rotationActivations.length ? <small>{rotationActivations.join(" · ")}</small> : null}</div></div> : null}
      {exposureRanges.length ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Exact exposure boundaries</strong><p>{exposureRanges.join(" · ")}. Coefficients come from the cited factor or classification receipts; Z3 only certifies their portfolio consequences.</p></div></div> : null}
      {exposureActivations.length ? <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Candidate activation points</strong><p>{exposureActivations.join(" · ")}. Each point forces that candidate into the book, changes only the named exposure band, and keeps every other mandate fixed.</p></div></div> : null}
      {allocationEnvelope.schema ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Partial-sizing envelope</strong><p>Maximum feasible weights inside the already-underwritten current-to-target corridors: {capacitySummary || "none"}. The solver cannot widen a corridor or activate capital.</p></div></div> : null}
      <div className="capital-allocation">{weights.map(([entity, weight]) => <div key={entity}><div><strong>{entity}</strong><span>{pct(weight)}</span></div><span className="capital-weight-bar"><i style={{ width: `${Math.max(0, Math.min(100, Number(weight) * 100))}%` }} /></span></div>)}</div>
    </Section>
    <Section eyebrow="Selected metrics" title="Portfolio consequences"><div className="capital-metric-row wide">{Object.entries(portfolio.selected_metrics || {}).map(([key, value]) => <div key={key}><span>{metricLabels[key] || key.replaceAll("_", " ")}</span><strong>{key.includes("return") || key.includes("downside") || key.includes("turnover") ? pct(value) : number(value)}</strong></div>)}</div></Section>
  </>;
}

function OutcomeCapture({ row, busy, onAction }) {
  const entityId = row.entity?.entity_id || "ENTITY";
  const benchmarkId = row.play?.benchmark_id || "BENCHMARK";
  const now = new Date().toISOString().slice(0, 16);
  const [entityPrice, setEntityPrice] = useState("");
  const [benchmarkPrice, setBenchmarkPrice] = useState("");
  const [observedAt, setObservedAt] = useState(now);
  const [availableAt, setAvailableAt] = useState(now);
  const [sourceRef, setSourceRef] = useState("");
  const submit = (event) => {
    event.preventDefault();
    onAction("settle-prices", {
      decision_id: row.decision_id,
      observed_at: new Date(observedAt).toISOString(),
      available_at: new Date(availableAt).toISOString(),
      prices: { [entityId]: Number(entityPrice), [benchmarkId]: Number(benchmarkPrice) },
      source_refs: [sourceRef],
    });
  };
  return <form className="capital-outcome-form" onSubmit={submit}>
    <label><span>{entityId} close</span><input type="number" min="0.000001" step="any" value={entityPrice} onChange={(event) => setEntityPrice(event.target.value)} required /></label>
    <label><span>{benchmarkId} close</span><input type="number" min="0.000001" step="any" value={benchmarkPrice} onChange={(event) => setBenchmarkPrice(event.target.value)} required /></label>
    <label><span>Observed</span><input type="datetime-local" value={observedAt} onChange={(event) => setObservedAt(event.target.value)} required /></label>
    <label><span>Available</span><input type="datetime-local" value={availableAt} onChange={(event) => setAvailableAt(event.target.value)} required /></label>
    <label className="wide"><span>Cached price receipt or source reference</span><input value={sourceRef} onChange={(event) => setSourceRef(event.target.value)} placeholder="provider receipt / archived export" required /></label>
    <button type="submit" className="copy-button" disabled={busy}>Settle paper decision</button>
  </form>;
}

function ShadowBook({ state, onPreview, busy, onAction }) {
  const legacy = state.pending_decisions || [];
  const readiness = state.capital_cycle?.settlement_readiness || {};
  const readinessByRun = new Map((readiness.closed_book?.runs || []).map((row) => [row.run_id, row]));
  const pending = (state.closed_book?.runs || []).filter((row) => row.status !== "settled").map((row) => {
    const current = readinessByRun.get(row.run_id);
    return current ? { ...row, end_at: current.end_at, status: current.status } : row;
  });
  const policyPending = Number(readiness.portfolio_policy?.pending_count || 0);
  return <Section eyebrow="Prospective ledger" title="Frozen forecasts awaiting public outcomes"
    description="The capital-cycle service seals forecasts before their outcome windows, binds the first synchronized post-seal prices, and settles them automatically when public prices become available.">
    {pending.length ? <div className="capital-shadow-list">{pending.map((row) => {
      const ablation = row.underwriting_ablation;
      return <article key={row.run_id}>
        <Clock3 size={20} /><div><span className="capital-data-class">prospective</span><strong>{row.entity?.name || row.entity?.entity_id || row.subject?.subject_id || "Unknown subject"}</strong><p>{String(row.status || "pending settlement").replaceAll("_", " ")} · {row.end_at ? `outcome due ${String(row.end_at).slice(0, 10)}` : "waiting for the post-seal entry price"} · {String(row.subject?.kind || "forecast").replaceAll("_", " ")}</p>{ablation ? <p>{ablation.arms?.length || 0}-arm underwriting ablation · {String(ablation.status || "sealed").replaceAll("_", " ")} · {(ablation.arms || []).map((arm) => String(arm).replaceAll("_", " ")).join(" → ")}</p> : <p>Standard frozen forecast; no underwriting-information ablation is attached.</p>}</div>{row.run_path ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(row.run_path)}>Inspect</button> : null}
      </article>;
    })}</div> : <Empty title="No prospective forecast is pending" body="The recurring capital cycle opens the next eligible forecast or ablation block from a current paper watch." />}
    <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Learning queue</strong><p>{pending.length} company or fund forecast block{pending.length === 1 ? "" : "s"} and {policyPending} portfolio-policy block{policyPending === 1 ? "" : "s"} await settlement. They earn model or policy credit only after the fixed horizon closes.</p></div></div>
    {legacy.length ? <details className="capital-overview-details"><summary><span><strong>Legacy manual decision settlements</strong><small>{legacy.length} earlier operator or reference-fixture decision{legacy.length === 1 ? "" : "s"}; retained for audit, outside the recurring capital-cycle queue.</small></span></summary><div className="capital-shadow-list">{legacy.map((row) => <article key={row.decision_id}>
      <Clock3 size={20} /><div><span className={`capital-data-class ${row.data_class}`}>{row.data_class === "operator" ? "operator" : "fixture"}</span><strong>{row.entity?.name || row.entity?.entity_id} · {row.selected_action_id}</strong><p>Target {pct(row.target_weight)} · due {row.due_at || "by declared falsifier"}</p><OutcomeCapture row={row} busy={busy} onAction={onAction} /></div><button type="button" className="capital-link" onClick={() => onPreview && onPreview(row.decision_path)}>Inspect</button>
    </article>)}</div></details> : null}
  </Section>;
}

function WorldModels({ state, onPreview, busy, onAction }) {
  const rows = state.tournaments || [];
  const experiments = state.market_flow_experiments || [];
  const researchProjects = state.research_projects || [];
  const companyPathProject = researchProjects.find((row) => row.project_id === "jaggedthoughts_company_state_path_newton") || {};
  const companyPathAdmission = companyPathProject.historical_admission || {};
  const companyPathHoldout = companyPathAdmission.partitions?.holdout || {};
  const companyPathTail = companyPathAdmission.partitions?.farther_tail || {};
  const executionMarket = state.adaptive_execution || {};
  const executionRun = executionMarket.latest_run || {};
  const executionPlan = executionRun.market_after || {};
  const executionLanes = executionRun.lanes || [];
  const executionAgentLanes = executionLanes.filter((lane) => lane?.executor?.mode !== "deterministic_program");
  const closedBook = state.closed_book || {};
  const closedRun = closedBook.latest_run || {};
  const closedRuns = closedBook.runs || [];
  const closedIntegrity = closedRun.evaluation_integrity || closedBook.evaluation_integrity || {};
  const closedCandidates = closedRun.candidate_forecasts || [];
  const closedScoreboard = closedBook.scoreboard || {};
  const sealedReplay = state.sealed_walk_forward_readiness || {};
  const sealedReplayCounts = sealedReplay.counts || {};
  const sealedReplayWaiting = Number(sealedReplayCounts.awaiting_evaluation_time || 0)
    + Number(sealedReplayCounts.awaiting_archive || 0);
  const forecastLearning = closedBook.forecast_learning || {};
  const forecastBundles = forecastLearning.bundles || [];
  const disagreement = (forecastLearning.disagreement_queue || [])[0] || {};
  const marketState = state.market_state || {};
  const marketStateRun = marketState.latest_run || {};
  const marketStateSnapshot = marketStateRun.snapshot || {};
  const marketStateVector = marketStateSnapshot.state || {};
  const marketStateForecasts = marketStateRun.candidate_forecasts || [];
  const unavailableStateModels = marketStateRun.unavailable_challengers || [];
  const marketStateSchedule = marketState.schedule || {};
  const marketStateHorizons = Object.values(marketState.latest_by_horizon || {});
  const modelResearchActivations = marketState.model_research_activations || [];
  const institutionalLearning = state.institutional_learning || {};
  const historicalStrategyReplay = state.historical_strategy_event_replay || {};
  const historicalStrategyWalkForward = state.historical_strategy_walk_forward || {};
  const historicalStrategySecurityWalkForward = state.historical_strategy_security_walk_forward || {};
  const strategyAlphaTournament = state.strategy_alpha_tournament || {};
  const strategyAlphaEvidence = strategyAlphaTournament.evidence || {};
  const strategyAlphaEvaluation = strategyAlphaTournament.evaluation || {};
  const strategyAlphaPredictionComparisons = strategyAlphaEvaluation.incremental_comparisons || [];
  const strategyAlphaEconomicComparisons = strategyAlphaEvaluation.economic_comparisons || [];
  const strategyAlphaControls = [
    ["valuation_only_control", "Valuation only"],
    ["durability_valuation_control", "Durability + valuation"],
  ].map(([controlId, label]) => ({
    controlId,
    label,
    prediction: strategyAlphaPredictionComparisons.find((row) => row.control_model_id === controlId) || {},
    economic: strategyAlphaEconomicComparisons.find((row) => row.control_model_id === controlId) || {},
  }));
  const historicalSecurityInference = historicalStrategySecurityWalkForward.dependence_adjusted_inference || {};
  const historicalForecastInterval = historicalSecurityInference.forecast_absolute_error_advantage?.confidence_interval_95 || [];
  const historicalReturnInterval = historicalSecurityInference.paper_return_increment_after_cost?.confidence_interval_95 || [];
  const historicalStrategyRepresentation = state.historical_strategy_representation_learning || {};
  const strategyPathConjecture = (historicalStrategyRepresentation.conjectures || [])[0] || {};
  const strategyPathQualification = strategyPathConjecture.same_epoch_behavior_qualification || {};
  const strategyPathShadow = state.strategy_path_shadow || {};
  const strategyOperatingForecasts = strategyPathShadow.operating_forecasts || [];
  const historicalControlDesign = state.historical_strategy_control_design || {};
  const historicalControlAcquisition = state.historical_strategy_control_acquisition || {};
  const historicalBulkCorpus = state.historical_strategy_bulk_corpus || {};
  const historicalBulkLearning = state.historical_strategy_bulk_learning || {};
  const historicalBulkOutcomes = state.historical_strategy_bulk_outcomes || {};
  const historicalBulkPanel = state.historical_strategy_bulk_panel_readiness || {};
  const historicalBulkEffects = state.historical_strategy_bulk_effects || {};
  const historicalOutcomeRobustness = state.historical_strategy_outcome_robustness || {};
  const historicalLawSearch = state.historical_strategy_law_search || {};
  const historicalLawTrial = state.historical_strategy_law_trial || {};
  const historicalLawTrialResults = historicalLawTrial.results || [];
  const historicalLawTrialSupport = historicalLawTrialResults.reduce((sum, row) => sum
    + Number(row.support?.treated_entity_count || 0)
    + Number(row.support?.future_adopter_entity_count || 0), 0);
  const historicalLawTrialScored = historicalLawTrialResults.filter((row) => row.status === "sealed_holdout_scored").length;
  const historicalLawTrialCandidate = (historicalLawTrial.candidates || [])[0] || {};
  const historicalLawTrialCandidateIdentity = historicalLawTrialCandidate.candidate_identity || {};
  const historicalLawTrialCurrentSupport = historicalLawTrialResults[0]?.support || {};
  const historicalLawTrialDesign = historicalLawTrial.trial_design || {};
  const historicalLawTrialStatus = historicalBulkLearning.sealed_law_trial_status
    || historicalLawTrial.status || "awaiting evidence";
  const strategyBusinessClock = state.strategy_business_clock || {};
  const researchBudget = state.research_budget_tournament || {};
  const matrixPolicy = state.activation_matrix_policy_learning || {};
  const accountingReplay = institutionalLearning.historical_accounting_replay || {};
  const strategyCohortMemory = institutionalLearning.strategy_causal_panel || {};
  const trialCensus = state.search_trial_census || {};
  const portfolioPolicy = state.portfolio_policy || {};
  const portfolioPolicyRun = portfolioPolicy.latest_run || {};
  const portfolioPolicies = portfolioPolicyRun.policies || [];
  const portfolioPolicyVersions = [...new Set(Object.values(portfolioPolicyRun.trial_family?.policy_versions || {}))];
  const portfolioAllocationUniverse = portfolioPolicyRun.allocation_universe || {};
  const portfolioPolicyScores = portfolioPolicy.scoreboard || {};
  const portfolioPolicyReview = portfolioPolicyScores.latest_policy_review || {};
  const portfolioReturnWindow = portfolioPolicyRun.settlement_contract?.prospective_return_window || {};
  const portfolioSurvivors = portfolioPolicyReview.survivor_set?.survivor_model_ids || [];
  const portfolioAttribution = portfolioPolicyRun.attribution_contract || portfolioPolicyRun.attribution_projection || {};
  const portfolioRiskModel = portfolioPolicyRun.risk_model || {};
  const portfolioComparisons = portfolioAttribution.comparisons || [];
  const lawEvaluations = institutionalLearning.evaluations || [];
  const lawSearch = institutionalLearning.law_search || {};
  const lawSearches = lawSearch.searches || [];
  const searchedPrograms = lawSearches.reduce((sum, search) => sum + Number(search?.enumeration?.score_program_count || 0), 0);
  const searchDepth = Math.max(0, ...lawSearches.map((search) => Number(search?.enumeration?.max_depth || 0)));
  const searchScopesClosed = lawSearches.length > 0 && lawSearches.every((search) => search?.frontier?.scope_closed);
  const mechanismGraph = institutionalLearning.mechanism_graph || {};
  const pendingWindows = Number(closedBook.pending_count || 0) + Number(marketState.pending_count || 0) + Number(portfolioPolicy.pending_count || 0);
  const settledWindows = Number(closedBook.settled_count || 0) + Number(marketState.settled_count || 0) + Number(portfolioPolicy.settled_count || 0);
  const nextMaturity = [...closedRuns, ...marketStateHorizons]
    .map((run) => String(run?.end_at || run?.scheduled_end_at || ""))
    .filter(Boolean)
    .sort()[0];
  return <>
    <Section eyebrow="Start here" title="What is this page deciding?"
      description="It asks whether any research or forecasting method deserves influence over later portfolio decisions. Predictions are locked before prices arrive, scored on the same future window, and promoted only after repeated after-cost wins.">
      <div className="capital-discovery-status">
        <div><span>Inputs</span><strong>Public data</strong><small>filings, fund data, prices, rates, and ERP</small></div>
        <div><span>Now</span><strong>{pendingWindows} locked windows</strong><small>collecting future outcomes</small></div>
        <div><span>Learned</span><strong>{settledWindows ? `${settledWindows} scored` : "No method promoted"}</strong><small>failed challengers remain visible</small></div>
        <div><span>Next scoring date</span><strong>{nextMaturity ? nextMaturity.slice(0, 10) : "Awaiting a window"}</strong><small>earliest scheduled window · entry binds to later public prices</small></div>
        <div><span>Capital effect</span><strong>Paper only</strong><small>no brokerage or trading authority</small></div>
      </div>
      <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>How the learning loop compounds</strong><p>Public evidence → competing methods → locked predictions → future outcomes → influence over paper policy. Each settlement updates method records without rewriting the prediction that was made.</p></div></div>
      <div className="capital-activation-grid">
        <article><header><strong>Research clock</strong><code>{number(researchBudget.complete_independent_block_count, 0)} / {number(researchBudget.minimum_independent_blocks, 8)}</code></header><p>Which queued job changes an underwriting decision per unit of research effort?</p><small>May eventually change future work order only.</small></article>
        <article><header><strong>Next-best-question clock</strong><code>{number(matrixPolicy.complete_pair_count, 0)} / {number(matrixPolicy.minimum_pairs, 20)}</code></header><p>For each company, three rival explanations predict what each available research question will reveal. The challenger asks where their probability forecasts disagree most per estimated source request; actual-call calibration is still missing.</p><small>{String(matrixPolicy.status || "collecting matched settlements").replaceAll("_", " ")} · {matrixPolicy.preferred_arm ? `future preference: ${String(matrixPolicy.preferred_arm).replaceAll("_", " ")}` : "paired against the incumbent question"} · later public evidence updates model weights, never capital</small>{state.paths?.activation_matrix_policy_learning_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.activation_matrix_policy_learning_latest)}><FileText size={14} />Inspect question policy</button> : null}</article>
        <article><header><strong>Business clock</strong><code>{number(institutionalLearning.settled_episode_count, 0)} prospective · {number(historicalStrategyReplay.episode_count, 0)} replayed</code></header><p>Which strategy moves improve a named operating outcome in comparable environments?</p><small>{number(historicalStrategyReplay.matured_event_count, 0)} matured public events are in the frozen historical search; {number(institutionalLearning.pending_episode_count, 0)} prospective phenotype episodes are waiting.</small></article>
        <article><header><strong>Market clock</strong><code>{settledWindows} settled</code></header><p>Which frozen forecasts and complete paper policies outperform simple rivals after costs?</p><small>{pendingWindows} forecast windows are waiting.</small></article>
      </div>
      {strategyPathShadow.shadow_sha256 ? <div className="capital-closure-rule"><Clock3 size={20} /><div><strong>Prospective strategy representation observer</strong><p>Every source-typed move now opens a frozen typed-phenotype versus untyped forecast. A later connected same-company path enters a separate three-arm composition tournament, so faster single-move learning cannot masquerade as path evidence.</p><small>{String(strategyPathShadow.status || "collecting").replaceAll("_", " ")} · {number(strategyPathShadow.postcutoff_event_count, 0)} later filings · {number(strategyPathShadow.move_count, 0)} admitted moves · {number(strategyPathShadow.single_move_forecast_count, 0)} single-move forecasts · {number(strategyPathShadow.typed_path_count, 0)} connected paths · {number(strategyPathShadow.connected_path_forecast_count, 0)} path forecasts · {number(strategyPathShadow.diagnostic_settled_forecast_count, 0)} short scores · {number((strategyPathShadow.acquisition_queue || []).length, 0)} documents due.</small></div>{state.paths?.strategy_path_shadow_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_path_shadow_latest)}><FileText size={14} />Inspect observer</button> : null}</div> : null}
      {strategyOperatingForecasts.length ? <div className="capital-closure-rule"><Activity size={20} /><div><strong>Did the strategy move improve the business?</strong><p>{strategyOperatingForecasts.map((row) => { const predictions = row.predicted_deltas || {}; const causal = predictions.group_time_strategy_family; return `${row.entity_id}: phenotype ${pct(predictions.typed_operating_phenotype, 2)} · base ${pct(predictions.untyped_operating_global_median, 2)}${causal == null ? "" : ` · cohort law ${pct(causal, 2)}`}` }).join(" · ")}</p><small>{number(strategyOperatingForecasts.length, 0)} owner-earnings-margin delta forecasts are frozen against the latest public pre-move baseline. {strategyOperatingForecasts.map((row) => `${row.entity_id} uses ${String(row.typed_prediction_basis || "unknown").replaceAll("_", " ")}${row.group_time_prediction_basis ? `; cohort law ${String(row.group_time_prediction_basis).replaceAll("_", " ")}` : ""} and settles after ${String(row.settlement_contract?.not_before || "—").slice(0, 10)}`).join(" · ")}. Every frozen model is scored on the same future fiscal-year blocks; the tournament requires {number(strategyPathShadow.operating_tournament?.minimum_independent_blocks, 8)} blocks.</small></div><Status ok={false}>{String(strategyPathShadow.operating_tournament?.status || "collecting").replaceAll("_", " ")}</Status></div> : null}
      <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Sealed archive replay</strong><p>{number(sealedReplay.subject_count, 0)} stocks and funds × 2 fixed controls × {number(sealedReplay.window_count, 0)} non-overlapping windows create {number(sealedReplay.program_cell_count, 0)} sealed program cells. {number(sealedReplayCounts.settled, 0)} are settled and {number(sealedReplayWaiting, 0)} await a due horizon or later source capture. The first control outcome is due {sealedReplay.first_window_evaluated_at ? String(sealedReplay.first_window_evaluated_at).slice(0, 10) : "after the first complete window"}.</p><small>{String(sealedReplay.status || "awaiting profile").replaceAll("_", " ")} · adjusted prices · implementation fingerprint {sealedReplay.plan?.implementation_matches ? "matches" : "requires inspection"} · the richer engine is tested by the locked prospective forecasts below</small></div>{state.paths?.sealed_walk_forward_profile ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.sealed_walk_forward_profile)}><FileText size={14} />Inspect replay schedule</button> : null}</div>
    </Section>
    <Section eyebrow="Strategy alpha" title="Does understanding the business improve the investment forecast?"
      description="The same dated evidence feeds nested rivals. The strategy arm earns credit only if it predicts later after-cost active returns better than valuation alone and durability plus valuation.">
      <div className="capital-discovery-status">
        <div><span>Verdict</span><strong>{strategyAlphaEvaluation.status ? String(strategyAlphaEvaluation.status).replaceAll("_", " ") : "Unknown"}</strong><small>{strategyAlphaEvaluation.status ? "prospective nested comparison" : "awaiting compatible settlements"}</small></div>
        <div><span>Independent blocks</span><strong>{number(strategyAlphaEvidence.independent_block_count, 0)} / 8</strong><small>{number(strategyAlphaEvidence.eligible_issuer_count, 0)} / 8 issuers · {number(strategyAlphaEvidence.compatible_family_count, 0)} compatible families · one primary episode per issuer</small></div>
        <div><span>Operating forecasts scored</span><strong>{number(strategyAlphaEvidence.operating_hurdle_calibration?.settled_forecast_count, 0)}</strong><small>probability calibration is scored separately</small></div>
        <div><span>Capital effect</span><strong>Zero</strong><small>paper challenger only after the full gate clears</small></div>
      </div>
      <div className="capital-tournament-list">{strategyAlphaControls.map((row) => {
        const predictionReady = row.prediction.target_minus_control_prediction_loss != null;
        const economicReady = row.economic.target_minus_control_economic_loss != null;
        const cleared = Boolean(row.prediction.target_better_after_fdr && row.economic.target_better_after_fdr);
        return <article key={row.controlId}><TrendingUp size={23} /><div><strong>Strategy vs {row.label}</strong><p>{predictionReady ? `Prediction-loss delta ${number(row.prediction.target_minus_control_prediction_loss, 4)} · ${row.prediction.target_better_after_fdr ? "clears FDR" : "does not clear FDR"}` : "No compatible prospective comparison has settled."}</p><span>{economicReady ? `After-cost economic-loss delta ${number(row.economic.target_minus_control_economic_loss, 4)} · ${row.economic.target_better_after_fdr ? "clears FDR" : "does not clear FDR"}` : "The result remains unknown until the same frozen blocks score both arms."}</span></div><Status ok={cleared}>{predictionReady || economicReady ? (cleared ? "conditional challenger" : "inconclusive") : "awaiting evidence"}</Status></article>;
      })}</div>
      <div className="capital-closure-rule"><Activity size={20} /><div><strong>Historical phenotype prior · separate diagnostic</strong><p>Typed strategy conditioning improved historical forecast MAE by {pct(historicalStrategySecurityWalkForward.policy_summary?.relative_mae_improvement, 2)} and the after-cost paper-book point estimate by {pct(historicalStrategySecurityWalkForward.policy_summary?.mean_book_active_return_increment_after_cost, 2)} versus an untyped residual. The 95% HAC intervals are {historicalForecastInterval.length === 2 ? `${pct(historicalForecastInterval[0], 1)} to ${pct(historicalForecastInterval[1], 1)}` : "unavailable"} for forecast advantage and {historicalReturnInterval.length === 2 ? `${pct(historicalReturnInterval[0], 1)} to ${pct(historicalReturnInterval[1], 1)}` : "unavailable"} for return increment.</p><small>{number(historicalStrategySecurityWalkForward.inference_block_count, 0)} of {number(historicalStrategySecurityWalkForward.minimum_inference_blocks, 8)} calendar cohorts; both intervals cross zero. This prior enters a future prospective block as its own challenger and contributes zero blocks to the nested valuation/durability test.</small></div><Status ok={false}>diagnostic only</Status></div>
      <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Why the gate is strict</strong><p>Recursive enumeration chooses coherent strategy programs; Z3 verifies the authored choice constraints and search closure. Later outcomes decide whether those programs add predictive value. A solver certificate cannot manufacture business evidence or alpha.</p><small>{strategyAlphaTournament.next_activation || "Accumulate eight compatible frozen blocks."}</small></div></div>
    </Section>
    <Section eyebrow="Institutional learning" title="Which investment regularities survive outside the cases that suggested them?"
      description="The engine turns dated company and fund fingerprints into comparable cohorts, executes each conjecture as a typed program, and searches industries, regimes, and subgroups for counterexamples. A narrower law starts a new evidence epoch; it cannot rewrite the sample that broke its parent."
      actions={<><ActionButton action="institutional-learning" busy={busy} onAction={onAction}>Refresh learning state</ActionButton><ActionButton action="strategy-event-learning" inputs={{ document_limit: 8, semantic_limit: 4 }} busy={busy} onAction={onAction} primary>Advance strategy corpus</ActionButton></>}>
      <div className="capital-closure-rule"><Activity size={20} /><div><strong>Is the engine working?</strong><p>Source acquisition, typed strategy classification, recursive hypothesis search, and sealed holdout settlement are executing automatically. An investment edge has not yet earned promotion.</p><small>{number(historicalBulkLearning.sealed_law_trial_holdout_queue_count, 0)} SEC documents are routed toward {number(historicalLawTrialResults.length || historicalLawTrial.candidates?.length, 0)} fixed laws · {number(historicalBulkLearning.sealed_law_trial_ambiguous_queue_count, 0)} trial filing awaiting semantic adjudication · {number(historicalLawTrialSupport, 0)} newly admitted company-role matches · {number(historicalLawTrialScored, 0)} sufficiently supported laws scored · zero capital authority.</small></div><Status ok={historicalLawTrialScored > 0}>{String(historicalLawTrialStatus).replaceAll("_", " ")}</Status></div>
      <div className="capital-discovery-status">
        <div><span>Conjectures</span><strong>{number(institutionalLearning.candidate_count, 0)}</strong><small>{number(institutionalLearning.generated_candidate_count, 0)} generated · {number(institutionalLearning.new_abduced_law_count, 0)} this cycle</small></div>
        <div><span>Phenotype episodes</span><strong>{number(institutionalLearning.phenotype_episode_count, 0)}</strong><small>{number(institutionalLearning.inference_block_count, 0)} independent market-history blocks</small></div>
        <div><span>Outcomes</span><strong>{number(institutionalLearning.settled_episode_count, 0)}</strong><small>{number(institutionalLearning.pending_episode_count, 0)} pending</small></div>
        <div><span>Program search</span><strong>{number(searchedPrograms, 0)}</strong><small>typed scores · depth {number(searchDepth, 0)} · {searchScopesClosed ? "scopes exhausted" : "bounded residual"}</small></div>
        <div><span>Mechanism links</span><strong>{number((mechanismGraph.composable_paths || []).length, 0)}</strong><small>strategy → earnings → return compositions</small></div>
        <div><span>Strategy research reused</span><strong>{number(strategyCohortMemory.recovered_compatible_result_count, 0)}</strong><small>{number(strategyCohortMemory.pending_research_count, 0)} peer questions still open</small></div>
        <div><span>Strategy comparison set</span><strong>{number(strategyCohortMemory.treated_unit_count, 0)} / {number(strategyCohortMemory.control_unit_count, 0)}</strong><small>treated / admissible controls · no forced matches</small></div>
        <div><span>Transfer candidates</span><strong>{number(institutionalLearning.transfer_candidate_count, 0)}</strong><small>must hold across compatible environments</small></div>
        <div><span>Policy eligible</span><strong>{number(institutionalLearning.promotion_eligible_count, 0)}</strong><small>still no capital authority</small></div>
      </div>
      <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Recursive law search</strong><p>Typed programs are selected and content-hashed on training blocks before the historical holdout is scored. The holdout may reject that frozen set but cannot choose a replacement. Any surviving conjecture then starts a separate prospective evidence epoch.</p></div></div>
      {accountingReplay.episode_count ? <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Filing-time replay: the simpler rival won</strong><p>Across {number(accountingReplay.episode_count, 0)} next-year accounting episodes, {number(accountingReplay.entity_count, 0)} companies, and {number(accountingReplay.inference_block_count, 0)} fiscal-year blocks, durability ranked the target at {number(accountingReplay.durability_model?.pooled_rank_correlation, 3)} versus {number(accountingReplay.persistence_control?.pooled_rank_correlation, 3)} for current-margin persistence. In the stricter expanding-time test, persistence averaged {number(accountingReplay.incremental_out_of_time_comparison?.mean_persistence_control_rho, 3)} across {number(accountingReplay.incremental_out_of_time_comparison?.holdout_block_count, 0)} later blocks; adding durability reduced that to {number(accountingReplay.incremental_out_of_time_comparison?.mean_persistence_plus_durability_rho, 3)}. The adverse-transition follow-up stays unopened. Current-universe sampling and post-period formula choice prohibit return or policy inference.</p></div>{accountingReplay.artifact ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(accountingReplay.artifact)}><FileText size={14} />Inspect replay</button> : null}</div> : null}
      {historicalStrategyReplay.replay_sha256 ? <div className="capital-closure-rule"><Activity size={20} /><div><strong>Historical strategy-event replay</strong><p>The frozen SEC Item 2.01 search found {number(historicalStrategyReplay.event_count, 0)} exact transaction events; {number(historicalStrategyReplay.matured_event_count, 0)} are mature and {number(historicalStrategyReplay.outcome_ready_event_count, 0)} have compatible filing-time owner-earnings observations. Exact filing documents currently support {number(historicalStrategyReplay.episode_count, 0)} classified episodes across {number(historicalStrategyReplay.entity_count, 0)} companies and {number(historicalStrategyReplay.evidence_block_count, 0)} evidence blocks.</p><small>{(historicalStrategyReplay.cohort_summaries || []).map((row) => `${String(row.implementation_mode).replaceAll("_", " ")}: ${number(row.episode_count, 0)} episodes · mean owner-earnings-margin change ${pct(row.mean_effect, 1)}`).join(" · ") || "Awaiting the first classified event"}. This replay can reject broad move claims; controls and pre-trends are still required before causal or policy credit.</small></div>{state.paths?.historical_strategy_event_replay_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.historical_strategy_event_replay_latest)}><FileText size={14} />Inspect events</button> : null}</div> : null}
      {historicalStrategyWalkForward.tournament_sha256 ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Strategy grammar forecast challenge</strong><p>At each annual boundary, the engine selected a strategy-phenotype program using only earlier scored blocks, then opened the next block. Across {number(historicalStrategyWalkForward.fold_count, 0)} folds and {number(historicalStrategyWalkForward.scored_episode_count, 0)} episodes, the selected policy's mean absolute error is {number(historicalStrategyWalkForward.policy_summary?.walk_forward_selected_policy?.mean_absolute_error, 3)} versus {number(historicalStrategyWalkForward.policy_summary?.incumbent?.mean_absolute_error, 3)} for the untyped global-median control.</p><small>{historicalStrategyWalkForward.status === "typed_policy_outperformed_incumbent_retrospectively" ? "Typed conditioning won this retrospective challenge, but remains ineligible for policy use." : "The simpler control won; strategy conditioning receives no predictive credit."} This forecasts operating outcomes, not stock returns, and carries no causal or capital authority.</small></div>{state.paths?.historical_strategy_walk_forward_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.historical_strategy_walk_forward_latest)}><FileText size={14} />Inspect forecast challenge</button> : null}</div> : null}
      {historicalStrategySecurityWalkForward.tournament_sha256 ? <div className="capital-closure-rule"><TrendingUp size={20} /><div><strong>Did strategy understanding predict a later stock edge?</strong><p>The engine retained {number(historicalStrategySecurityWalkForward.eligible_security_outcome_count, 0)} isolated moves after requiring a filing-CIK and filing-era-symbol match; {number(historicalStrategySecurityWalkForward.excluded_episode_count, 0)} unresolved or overlapping episodes stayed out. It waited two daily sessions, froze pre-event market, value, size, momentum, and quality betas, settled one-year factor-controlled returns after {number(historicalStrategySecurityWalkForward.execution_contract?.round_trip_cost_bps, 0)} bps, and selected each typed program using earlier completed windows only. Across {number(historicalStrategySecurityWalkForward.inference_block_count ?? historicalStrategySecurityWalkForward.fold_count, 0)} event-year cohorts, one-year overlap is adjusted with Newey–West uncertainty over {number(historicalStrategySecurityWalkForward.scored_episode_count, 0)} paired events; the connected-window diagnostic contains {number(historicalStrategySecurityWalkForward.independent_block_count, 0)} component. Typed conditioning changed forecast error by {pct(historicalStrategySecurityWalkForward.policy_summary?.relative_mae_improvement, 2)} and paper-book active return by {pct(historicalStrategySecurityWalkForward.policy_summary?.mean_book_active_return_increment_after_cost, 2)} versus the untyped control.</p><small>{!historicalStrategySecurityWalkForward.inference_sufficient ? `Only ${number(historicalStrategySecurityWalkForward.inference_block_count ?? historicalStrategySecurityWalkForward.fold_count, 0)} of ${number(historicalStrategySecurityWalkForward.minimum_inference_blocks ?? historicalStrategySecurityWalkForward.minimum_independent_blocks, 8)} required calendar cohorts exist, so the point estimates and confidence intervals earn no alpha credit.` : historicalStrategySecurityWalkForward.status === "typed_policy_outperformed_forecast_and_economic_controls_retrospectively" ? "Candidate effect only; prospective confirmation is still required." : "It failed the joint forecast-and-economic gate, so the engine assigns zero alpha credit."} Cached histories were retrieved later than the events; the overlap component is diagnostic and is not treated as sample size.</small></div>{state.paths?.historical_strategy_security_walk_forward_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.historical_strategy_security_walk_forward_latest)}><FileText size={14} />Inspect stock-edge challenge</button> : null}</div> : null}
      {historicalStrategyRepresentation.learning_sha256 ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>What the failed strategy model taught the engine</strong><p>The isolated-event phenotype remains barred from security ranking. Its exclusions exposed {number(strategyPathConjecture.support_path_count, 0)} connected same-company paths containing {number(strategyPathConjecture.support_episode_count, 0)} moves across {number(strategyPathConjecture.support_entity_count, 0)} issuers. The compiler retained 16 incumbent projections, added two canonical path projections, and compared every distinct behavior on one executable surface.</p><small>{strategyPathQualification.status === "qualified" ? `Exact path reconstruction, invalid-tuple rejection, invariance, incumbent retention, and strict frontier improvement passed. The path grammar can enter at least ${number(strategyPathConjecture.future_evaluation_contract?.minimum_independent_blocks, 8)} later paired shadow blocks.` : `${number(strategyPathQualification.repair_targets?.length, 0)} executable behavior gates failed. No shadow trial opened.`} Lagrangian/current models stay separate until a path improves company-state forecasts over a first-order control.</small></div>{state.paths?.historical_strategy_representation_learning_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.historical_strategy_representation_learning_latest)}><FileText size={14} />Inspect grammar repair</button> : null}</div> : null}
      {historicalBulkCorpus.corpus_sha256 ? <div className="capital-closure-rule"><Database size={20} /><div><strong>Market-wide strategy population</strong><p>{number(historicalBulkCorpus.event_count, 0)} source-timestamped SEC transaction events span {number(historicalBulkCorpus.event_entity_count, 0)} issuers from {historicalBulkCorpus.start_year || 2010} through {historicalBulkCorpus.end_year || "now"}; {number(historicalBulkCorpus.current_common_equity_event_count, 0)} events across {number(historicalBulkCorpus.current_common_equity_event_entity_count, 0)} issuers map to today’s U.S. common-equity catalog. Keeping both populations prevents today’s survivors from defining the historical learning sample.</p><small>{number(historicalBulkLearning.supported_design_cell_count, 0)} industry/adoption-year cells have repeated treated and future-adopter support · {number(historicalBulkLearning.classified_event_count, 0)} filing documents typed · {number(historicalBulkLearning.queue_count, 0)} ranked next · {number(historicalBulkLearning.sealed_law_trial_holdout_queue_count, 0)} routed to the sealed law trial · {number(historicalBulkLearning.ambiguous_semantic_queue_count, 0)} await the source-quote semantic leaf. This is a design and acquisition surface, not an outcome claim.</small></div>{state.paths?.historical_strategy_bulk_learning_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.historical_strategy_bulk_learning_latest)}><FileText size={14} />Inspect learning queue</button> : null}</div> : null}
      {historicalBulkOutcomes.outcomes_sha256 ? <div className="capital-closure-rule"><Activity size={20} /><div><strong>As-filed operating outcome lake</strong><p>{number(historicalBulkOutcomes.observation_count, 0)} accession-bound annual observations cover {number(historicalBulkOutcomes.covered_entity_count, 0)} of {number(historicalBulkOutcomes.event_entity_count, 0)} event issuers. Reporting period and filing availability remain separate, and later restatements do not overwrite what was knowable earlier.</p><small>{number(historicalBulkOutcomes.missing_entity_count, 0)} issuers are absent from the Company Facts archive · {number(historicalBulkOutcomes.uncovered_no_selected_facts_count, 0)} have no selected annual facts. {historicalBulkOutcomes.next_activation}</small></div>{state.paths?.historical_strategy_bulk_outcomes_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.historical_strategy_bulk_outcomes_latest)}><FileText size={14} />Inspect outcomes</button> : null}</div> : null}
      {historicalBulkPanel.readiness_sha256 ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Market-wide causal-panel gate</strong><p>{number(historicalBulkPanel.eligible_typed_event_count, 0)} typed operating events are joined to filing-time financial histories; {number(historicalBulkPanel.history_ready_event_count, 0)} have at least three pre-event and one post-event annual observations, and {number(historicalBulkPanel.first_adoption_ready_event_count, 0)} also have their complete prior issuer event history typed. {number(historicalBulkPanel.structural_support_ready_cell_count, 0)} industry × move × adoption-year cells pass marginal 4/4 support; {number(historicalBulkPanel.group_time_ready_cell_count, 0)} also share an admissible pre/post calendar.</p><small>{String(historicalBulkPanel.estimation_status || "awaiting evidence").replaceAll("_", " ")}. {historicalBulkPanel.next_activation} No effect estimate runs before joint support passes.</small></div>{state.paths?.historical_strategy_bulk_panel_readiness_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.historical_strategy_bulk_panel_readiness_latest)}><FileText size={14} />Inspect panel gate</button> : null}</div> : null}
      {historicalBulkEffects.diagnostics_sha256 ? <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Strategy-law diagnostic</strong><p>{(historicalBulkEffects.diagnostics || []).map((row) => `${String(row.cell?.implementation_mode || "move").replaceAll("_", " ")} ${row.cell?.adoption_year}: ${String(row.evaluation?.diagnostic_status || "awaiting").replaceAll("_", " ")}`).join(" · ") || "No structurally supported cell yet."}</p><small>{historicalBulkEffects.next_activation} These are post-hoc diagnostics with no multiplicity, causal, promotion, or capital credit.</small></div>{state.paths?.historical_strategy_bulk_effects_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.historical_strategy_bulk_effects_latest)}><FileText size={14} />Inspect diagnostics</button> : null}</div> : null}
      {historicalOutcomeRobustness.robustness_sha256 ? <div className="capital-closure-rule"><Activity size={20} /><div><strong>Outcome scale stress</strong><p>The fixed family compares economic owner-earnings margin with a unit-invariant bounded balance score for every eligible cell; no best-result selection is allowed. {(historicalOutcomeRobustness.families || []).map((row) => `${String(row.cell?.implementation_mode || "move").replaceAll("_", " ")} ${row.cell?.adoption_year}: ${row.direction_agreement ? "same direction" : "direction unresolved"}, ${row.all_parallel_trend_gates_pass ? "pretrend gates pass" : "pretrend challenged"}`).join(" · ")}</p><small>{historicalOutcomeRobustness.next_activation} The bounded score diagnoses tail dependence and cannot replace the economic estimand.</small></div>{state.paths?.historical_strategy_outcome_robustness_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.historical_strategy_outcome_robustness_latest)}><FileText size={14} />Inspect outcome family</button> : null}</div> : null}
      {historicalLawSearch.law_search_sha256 ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Outcome-blind child-law frontier</strong><p>The grammar exhausted {number(historicalLawSearch.enumeration?.program_count, 0)} source-defined transaction projections after the broad parent diagnostics. {number(historicalLawSearch.frozen_child_candidate_count, 0)} narrower cells currently have a shared pre/post calendar; {number(historicalLawSearch.acquisition_frontier_count, 0)} near-support cells define the next evidence queue.</p><small>{historicalLawSearch.next_activation} Child outcomes were excluded from selection, so a failed broad claim cannot be rescued by searching the same sample for a flattering subgroup.</small></div>{state.paths?.historical_strategy_law_search_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.historical_strategy_law_search_latest)}><FileText size={14} />Inspect child frontier</button> : null}</div> : null}
      {historicalLawTrial.trial_sha256 ? <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Sparse sealed strategy-law trial</strong><p>{historicalLawTrial.schema?.endsWith("v4") ? `${String(historicalLawTrialCandidateIdentity.moderators?.issuer_role || "typed issuer").replaceAll("_", " ")} ${String(historicalLawTrialCandidateIdentity.parent?.implementation_mode || "strategy move").replaceAll("_", " ")} · SIC2 ${historicalLawTrialCandidateIdentity.parent?.sic2 || "—"} · ${historicalLawTrialCandidateIdentity.parent?.adoption_year || "—"}` : `${number(historicalLawTrial.candidates?.length, historicalLawTrial.multiplicity?.trial_count || 0)} fixed child laws`}. Current independent support is {number(historicalLawTrialCurrentSupport.treated_entity_count, 0)} / 4 treated and {number(historicalLawTrialCurrentSupport.future_adopter_entity_count, 0)} / 4 future adopters.</p><small>{historicalLawTrialDesign.solver ? `${String(historicalLawTrialDesign.solver.kind).replaceAll("_", " ")} proved ${number(historicalLawTrialDesign.selected_candidate_count, 0)} maximal feasible candidate with ${number(historicalLawTrialDesign.reserve_per_role, 0)} frozen reserves per side. ` : ""}{historicalLawTrial.status === "support_exhausted" ? "No untouched candidate admits a fresh 4 + 4 disjoint reserve; this acquisition lane is stopped until the outcome-blind law universe changes. " : `${number(historicalBulkLearning.sealed_law_trial_holdout_queue_count, 0)} next SEC documents pay down exact support deficits · ${number(historicalBulkLearning.sealed_law_trial_reachable_candidate_count, 0)} reachable · ${number(historicalBulkLearning.sealed_law_trial_exhausted_candidate_count, 0)} exhausted. `}Historical evidence can kill or prioritize the mechanism; it cannot authorize a portfolio.</small></div><Status ok={historicalLawTrial.status === "sealed_holdout_scored"}>{String(historicalLawTrial.status || "collecting").replaceAll("_", " ")}</Status>{state.paths?.historical_strategy_law_trial_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.historical_strategy_law_trial_latest)}><FileText size={14} />Inspect sealed trial</button> : null}</div> : null}
      {historicalControlDesign.control_design_sha256 ? <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Moderator and control frontier</strong><p>The typed grammar exhausts 16 transaction-grain programs and preserves {number(historicalControlDesign.moderator_frontier?.certificate?.frontier_program_ids?.length, 0)} nondominated projections. {number(historicalControlDesign.activation_cell_count, 0)} cells have repeated treated companies and event years; {number(historicalControlDesign.treated_history_ready_count, 0)} treated episodes have sufficient pre/post history. The ranked public-source batch contains {number(historicalControlDesign.control_source_request_count, 0)} requests, with {number(historicalControlDesign.pretrend_rankable_control_count, 0)} candidates currently ready for joint matching.</p><small>{historicalControlDesign.next_activation || "Acquire source-bound controls."} Raw before/after averages do not choose the moderator grain, and every control remains unadmitted until its bounded event history, pretrend, and environment gates resolve.</small></div>{state.paths?.historical_strategy_control_design_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.historical_strategy_control_design_latest)}><FileText size={14} />Inspect design</button> : null}</div> : null}
      {historicalControlAcquisition.acquisition_sha256 ? <div className="capital-closure-rule"><Database size={20} /><div><strong>Control evidence actually acquired</strong><p>The latest bounded cycle extracted {number(historicalControlAcquisition.attempted_entity_count, 0)} peer packets from the existing SEC bulk archives in one pass, without a subscription call. Public-history gaps moved from {number(historicalControlAcquisition.before?.source_gap_count, 0)} to {number(historicalControlAcquisition.after?.source_gap_count, 0)} before the cross-corpus contamination veto ran.</p><small>The current frontier above is authoritative: company-strategy events learned elsewhere can remove an apparent control after source hydration. {historicalControlAcquisition.next_activation || "Continue the bounded acquisition frontier."}</small></div>{state.paths?.historical_strategy_control_acquisition_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.historical_strategy_control_acquisition_latest)}><FileText size={14} />Inspect acquisition</button> : null}</div> : null}
      {strategyBusinessClock.clock_sha256 ? <div className="capital-closure-rule"><Clock3 size={20} /><div><strong>Business clock owner</strong><p>The periodic capital cycle owns due public observations, strategy replay, comparison-set refresh, and law recompilation. Latest clock: {String(strategyBusinessClock.advanced_at || "unknown time").slice(0, 19)}; {number(strategyBusinessClock.admissible_control_count, 0)} admissible controls and {number(strategyBusinessClock.due_outcome_contract_count, 0)} due operating contracts.</p></div>{state.paths?.strategy_business_clock_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.strategy_business_clock_latest)}><FileText size={14} />Inspect clock</button> : null}</div> : null}
      <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Cohort memory compounds by evidence interval</strong><p>A later clock does not invalidate the same peer-and-mechanism question. Completed source coverage is preserved, changed phenotypes start a new identity, and only the uncovered interval can trigger more research.</p></div></div>
      <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Complete search census</strong><p>{number(trialCensus.observed_candidate_count, 0)} candidates are visible across {number(trialCensus.observed_search_surface_count, 0)} search surfaces. {number(trialCensus.registered_trial_count, 0)} current trials are committed before outcomes; {number(trialCensus.uncovered_empirical_surface_count, 0)} older empirical surfaces remain diagnostic-only. Recursive enumeration becomes alpha evidence only when its entire candidate family was registered before the outcome boundary.</p></div><Status ok={Boolean(trialCensus.census_complete)}>{trialCensus.census_complete ? "complete" : "partial"}</Status></div>
      <div className="capital-tournament-list">{lawSearches.map((search) => <article key={search.entity_kind}><GitBranch size={23} /><div><strong>{String(search.entity_kind || "entity").replaceAll("_", " ")}</strong><p>{(search.features || []).join(" · ") || "Awaiting typed predictors"}</p><span>{String(search.status || "awaiting search").replaceAll("_", " ")} · {number(search?.enumeration?.score_program_count, 0)} score programs · {number(search?.chronological_partition?.training_block_ids?.length, 0)} train / {number(search?.chronological_partition?.holdout_block_ids?.length, 0)} holdout blocks · {number(search?.frozen_selection?.program_ids?.length, 0)} frozen candidates</span></div><Status ok={Boolean(search?.frontier?.scope_closed)}>{search?.frontier?.scope_closed ? "scope closed" : "collecting"}</Status></article>)}</div>
      {(mechanismGraph.composable_paths || []).length ? <div className="capital-tournament-list">{mechanismGraph.composable_paths.map((path) => <article key={`${path.producer_law_key}:${path.consumer_law_key}`}><GitBranch size={23} /><div><strong>{String(path.via_concept).replaceAll("_", " ")}</strong><p>{String(path.producer_law_key).split("@")[0].replaceAll("-", " ")} → {String(path.consumer_law_key).split("@")[0].replaceAll("-", " ")}</p><span>A strategy consequence becomes an input to a return conjecture.</span></div><Status ok={false}>prospective</Status></article>)}</div> : null}
      <div className="capital-tournament-list">{lawEvaluations.map((row) => {
        const candidate = (institutionalLearning.candidates || []).find((item) => item.law_key === row.law_key) || {};
        const firstEnvironment = (row.environment_evaluations || [])[0] || {};
        const collecting = ["awaiting_outcomes", "awaiting_causal_panel", "collecting_or_inconclusive", "awaiting_compatible_phenotypes"].includes(row.status);
        return <article key={row.evaluation_sha256 || row.law_key}><GitBranch size={23} /><div><strong>{candidate.name || String(row.law_key || "law").replaceAll("_", " ")}</strong><p>{candidate.question || row.reason || "Typed investment-law candidate"}</p><span>{String(row.estimator_kind || "").replaceAll("_", " ")} · {number(row.phenotype_episode_count ?? row.panel_row_count, 0)} episodes · {number(firstEnvironment.scored_inference_block_count, 0)} scored blocks</span></div><Status ok={row.status === "prospective_transfer_candidate"}>{collecting ? "collecting" : String(row.status || "inspect").replaceAll("_", " ")}</Status></article>;
      })}</div>
      <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>What happens next</strong><p>{institutionalLearning.next_activation || "Compile the first point-in-time cohort."} Cross-sectional rank correlation is predictive evidence only. Causal credit requires a source-bound treatment panel, a valid comparison group, and a parallel-trend diagnostic.</p></div>{state.paths?.institutional_learning_latest ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(state.paths.institutional_learning_latest)}><FileText size={14} />Inspect learning state</button> : null}</div>
    </Section>
    <Section eyebrow="Capital allocation tournament" title="Does the equity-satellite policy beat cash and the market?"
      description="One common starting epoch freezes qualified public equities and compares cash, equal weight, discovery-priority, learned-law-priority, and fully gated paper candidates when available. A minimum-variance arm diagnoses covariance risk but cannot win a return-policy recommendation. Funds remain same-sleeve ranking tickets; broad household sleeve weights remain outside this tournament.">
      {portfolioPolicyRun.run_id ? <>
        <div className="capital-discovery-status">
          <div><span>Observed universe</span><strong>{number((portfolioPolicyRun.universe || []).length, 0)}</strong><small>{(portfolioPolicyRun.universe || []).map((row) => row.entity_id).join(" · ")}</small></div>
          <div><span>Allocation scope</span><strong>{String(portfolioAllocationUniverse.identity || "legacy mixed candidate family").replaceAll("_", " ")}</strong><small>{(portfolioAllocationUniverse.entity_ids || []).join(" · ") || "immutable prior run; successor uses equities only"}</small></div>
          <div><span>Policies</span><strong>{number(portfolioPolicies.length, 0)}</strong><small>{portfolioPolicyVersions.length ? `policy contract v${portfolioPolicyVersions.join("/")} · ` : ""}{number((portfolioPolicyRun.equivalent_policies || []).length, 0)} equivalent aliases withheld</small></div>
          <div><span>Tradable window</span><strong>{number(portfolioPolicyRun.horizon_days, 0)} days</strong><small>{portfolioReturnWindow.entry_rule ? "entry binds to first synchronized post-seal price" : "legacy run withheld from scoring"}</small></div>
          <div><span>Cash hurdle</span><strong>{pct(portfolioPolicyRun.cash_contract?.annual_yield, 2)}</strong><small>frozen annual yield</small></div>
          <div><span>Settled blocks</span><strong>{number(portfolioPolicyScores.inference_block_count, 0)}</strong><small>{number(portfolioPolicyScores.minimum_inference_blocks, 8)} needed for comparison</small></div>
          <div><span>Policy review</span><strong>{String(portfolioPolicyReview.activation_status || "collecting").replaceAll("_", " ")}</strong><small>{portfolioPolicyReview.recommended_policy_id ? `candidate: ${String(portfolioPolicyReview.recommended_policy_id).replaceAll("_", " ")}` : `${portfolioSurvivors.length || portfolioPolicies.length} survivors`}</small></div>
          <div><span>Decision paths</span><strong>{number((portfolioAttribution.rows || []).filter((row) => Math.abs(Number(row.delta_weight_vs_reference || 0)) > 1e-12).length, 0)}</strong><small>{portfolioComparisons.map((row) => `${String(row.policy_id).replaceAll("_", " ")} vs ${String(row.reference_policy_id).replaceAll("_", " ")}`).join(" · ") || "weight deltas bound to frozen inputs"}</small></div>
        </div>
        {!portfolioAllocationUniverse.identity ? <div className="capital-boundary"><AlertTriangle size={17} /><div><strong>Legacy trial remains frozen</strong><p>This pending block predates the equity/fund identity split and keeps its original weights for valid settlement. After it matures, the next block allocates only the public-equity satellite while comparing funds inside their declared sleeves.</p></div></div> : null}
        <div className="capital-tournament-list">{portfolioPolicies.map((policy) => { const risk = portfolioRiskEstimate(policy, portfolioRiskModel); const diagnostic = policy.evaluation_role === "diagnostic_risk_comparator"; return <article key={policy.policy_sha256}><Layers3 size={23} /><div><strong>{String(policy.policy_id).replaceAll("_", " ")}</strong><p>{Object.entries(policy.weights || {}).map(([entity, weight]) => `${entity} ${pct(weight, 1)}`).join(" · ") || "100% cash"}</p><span>{pct(policy.gross_weight, 1)} gross · {pct(policy.cash_weight, 1)} cash · {String(policy.method).replaceAll("_", " ")}{risk != null ? ` · ${pct(risk, 1)} covariance risk estimate` : ""}</span></div><Status ok={diagnostic}>{diagnostic ? "risk diagnostic" : "pending return"}</Status></article>; })}</div>
        {portfolioPolicies.some((policy) => policy.evaluation_role === "diagnostic_risk_comparator") ? <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Risk-policy comparison</strong><p>The fixed and walk-forward ridge covariance arms make no expected-return claim. Their frozen contract later compares synchronized adjusted-price volatility, drawdown, round-trip turnover, and after-cost mean-variance utility. Eight independent blocks are required; a winner may create a future paper review but cannot change positions.</p></div></div> : null}
        <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>Paired policy-learning gate</strong><p>{portfolioPolicyReview.activation_status ? `Current state: ${String(portfolioPolicyReview.activation_status).replaceAll("_", " ")}. ` : "No policy outcome has settled. "}The engine starts returns at the first synchronized public price after the policy seal, measures the full horizon from that entry, clusters overlapping market windows, corrects the paired trial family for multiple comparisons, and requires eight independent blocks. A unique promotion-eligible survivor creates a paper-policy review candidate; it never changes positions automatically.</p></div>{portfolioPolicyReview.policy_review_sha256 ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(`portfolio_policy/reviews/${portfolioPolicyReview.trial_family?.trial_family_id}.json`)}><FileText size={14} />Inspect policy review</button> : null}</div>
        <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Score + attribution contract</strong><p>Later same-basis prices settle after-cost portfolio return, excess return versus SPY, and security-selection contribution versus equal benchmark exposure. Cash and discovery compare with equal weight; learned-law and operator policies compare with discovery. Each weight delta is multiplied by its later active return and linked to the frozen candidate, sources, research question, and law contributions. Shared inputs receive no causal credit without separate policy variation.</p></div></div>
      </> : <Empty title="No complete-policy block yet" body="The recurring capital cycle opens one after at least two qualified candidates have point-in-time prices." />}
    </Section>
    <Section eyebrow="Company and fund forecasts" title="Which research process predicts better?"
      description="Each block gives several methods the same dated evidence about one company or fund. Later, all methods are scored on entity return relative to the declared benchmark. New qualifying opportunities enter automatically through the recurring capital cycle."
      actions={<><ActionButton action="closed-book-open" inputs={{ horizon_days: 90 }} busy={busy} onAction={onAction} primary>Open 90-day block</ActionButton><ActionButton action="closed-book-settle" busy={busy} onAction={onAction}>Settle due blocks</ActionButton></>}>
      {closedRun.run_id ? <>
        <div className="capital-discovery-status">
          <div><span>Entity</span><strong>{closedRun.evidence_packet?.entity?.entity_id || "—"}</strong><small>{String(closedRun.subject?.kind || "paper_decision").replaceAll("_", " ")} · vs {closedRun.evidence_packet?.benchmark?.entity_id || "benchmark"}</small></div>
          <div><span>Window</span><strong>{closedRun.horizon_days} days</strong><small>ends {String(closedRun.end_at || "").slice(0, 10)}</small></div>
          <div><span>Forecasts</span><strong>{closedCandidates.length}</strong><small>same frozen packet</small></div>
          <div><span>Outcomes</span><strong>{number(closedBook.settled_count, 0)}</strong><small>{number(closedBook.pending_count, 0)} pending</small></div>
          <div><span>Comparison</span><strong>{closedScoreboard.comparison_ready ? "available" : "collecting"}</strong><small>{number(closedScoreboard.inference_block_count, 0)} / {number(closedScoreboard.minimum_inference_blocks, 8)} blocks</small></div>
          <div><span>Evidence status</span><strong>{String(closedIntegrity.evidence_authority || "unclassified").replaceAll("_", " ")}</strong><small>{closedIntegrity.paper_policy_authority === false ? "does not authorize a paper policy" : "authority receipt missing"}</small></div>
        </div>
        <div className="capital-tournament-list">{closedCandidates.map((candidate) => <article key={candidate.forecast_sha256}><Activity size={23} /><div><strong>{String(candidate.candidate_id || "forecast").replaceAll("_", " ")}</strong><p>active return {pct(candidate.predicted_values?.active_return, 2)} · underperform {pct(candidate.predicted_values?.underperformance_event, 1)} · weight {pct(candidate.target_weight, 1)}</p><span>{String(candidate.producer?.mode || "").replaceAll("_", " ")} · frozen before outcome</span></div><Status ok={true}>pending</Status></article>)}</div>
        <div className="capital-closure-rule"><Activity size={20} /><div><strong>Compounding memory</strong><p>{number(forecastLearning.settled_bundle_count, 0)} of {number(forecastLearning.bundle_count, 0)} exact mechanism bundles have settled evidence. {disagreement.entity_id ? `${disagreement.entity_id} currently has the widest forecast spread at ${pct(disagreement.active_return_range, 2)}.` : "Disagreement appears after the first block."} Component credit remains withheld until a separately varied comparison identifies it.</p></div></div>
        {forecastBundles.some((row) => row.cross_entity_observed) ? <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Transfer candidates</strong><p>{forecastBundles.filter((row) => row.cross_entity_observed).length} bundle{forecastBundles.filter((row) => row.cross_entity_observed).length === 1 ? "" : "s"} have settled across more than one entity. Transfer stays descriptive until comparable blocks survive the shared tournament.</p></div></div> : null}
        <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Temporal boundary</strong><p>Web, shell, and repository tools are unavailable to the frontier lane. Returns begin only at a synchronized price after the forecast is sealed, and overlapping horizons share one inference block. Historical frontier replay stays diagnostic because disabling tools cannot erase market history embedded in model parameters; a subscription-agent winner also remains blocked while the resolved account model identity is unavailable.</p></div>{closedRun.run_path ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(closedRun.run_path)}><FileText size={14} />Inspect block</button> : null}</div>
      </> : <Empty title="No closed-book block yet" body="Open the first 90-day block from the latest operator decision. The outcome is scored only after its fixed horizon and public price observations arrive." />}
    </Section>
    <Section eyebrow="Whole-market forecasts" title="What do today’s valuation and rate conditions imply?"
      description="The engine freezes a cash-flow-implied equity return, its nominal and real risk premia, simple earnings/dividend yield spreads, and the Treasury curve. Competing methods predict SPY return and the next spread change over separate 90-day and one-year windows."
      actions={<ActionButton action="market-state-cycle" inputs={{ refresh_sources: true }} busy={busy} onAction={onAction} primary>Refresh + issue due state forecasts</ActionButton>}>
      {marketStateRun.run_id ? <>
        <div className="capital-discovery-status">
          <div><span>Nominal implied ERP</span><strong>{pct(marketStateVector.nominal_implied_equity_risk_premium ?? marketStateVector.implied_equity_risk_premium, 2)}</strong><small>S&amp;P price + cash payout + growth</small></div>
          <div><span>Implied equity return</span><strong>{pct(marketStateVector.implied_nominal_equity_return, 2)}</strong><small>nominal cash-flow IRR</small></div>
          <div><span>Real ERP vs TIPS</span><strong>{pct(marketStateVector.implied_real_equity_risk_premium, 2)}</strong><small>same IRR converted to real terms</small></div>
          <div><span>10y TIPS / breakeven</span><strong>{pct(marketStateVector.treasury_10y_real_yield, 2)} / {pct(marketStateVector.breakeven_inflation_10y, 2)}</strong><small>FRED point-in-time coordinates</small></div>
          <div><span>Cash-flow ERP range</span><strong>{(marketStateVector.cash_flow_implied_erp_range || []).length === 2 ? `${pct(marketStateVector.cash_flow_implied_erp_range[0], 2)}–${pct(marketStateVector.cash_flow_implied_erp_range[1], 2)}` : "—"}</strong><small>payout and normalization rivals</small></div>
          <div><span>Trailing E/P − TIPS</span><strong>{pct(marketStateVector.valuation_spreads?.trailing_earnings_yield_minus_tips_diagnostic, 2)}</strong><small>valuation diagnostic; omits growth and payout conversion</small></div>
          <div><span>Forward E/P − nominal 10y</span><strong>{pct(marketStateVector.valuation_spreads?.forward_earnings_yield_minus_nominal_10y, 2)}</strong><small>one-year earnings snapshot; not an equity IRR</small></div>
          <div><span>Dividend yield − TIPS</span><strong>{pct(marketStateVector.valuation_spreads?.dividend_yield_minus_tips_income_diagnostic, 2)}</strong><small>income-only spread; omits buybacks and growth</small></div>
          <div><span>10y–3m</span><strong>{pct(marketStateVector.term_spread_10y_3m, 2)}</strong><small>exact-maturity spread</small></div>
          <div><span>Windows</span><strong>{marketStateHorizons.length ? marketStateHorizons.map((run) => run.horizon_days === 365 ? "1 year" : `${run.horizon_days} days`).join(" + ") : Number(marketState.run_count || 0) >= 2 ? "90 days + 1 year" : `${marketStateRun.horizon_days} days`}</strong><small>showing the latest {marketStateRun.horizon_days}-day candidates below</small></div>
          <div><span>Joint forecasts</span><strong>{marketStateForecasts.length}</strong><small>{unavailableStateModels.length} waiting for compatible evidence</small></div>
          <div><span>Outcomes</span><strong>{number(marketState.settled_count, 0)}</strong><small>{number(marketState.pending_count, 0)} pending</small></div>
          <div><span>Activation</span><strong>{marketStateSchedule.due ? "due now" : "automatic"}</strong><small>server due-check · {(marketStateSchedule.due_horizons || []).length} issue / {(marketStateSchedule.matured_run_ids || []).length} settlement events</small></div>
          <div><span>Model evolution</span><strong>{modelResearchActivations.length ? `${modelResearchActivations.length} decision due` : "collecting"}</strong><small>successor or retirement only after 8 independent blocks</small></div>
        </div>
        <div className="capital-tournament-list">{marketStateForecasts.map((candidate) => <article key={candidate.forecast_sha256}><Activity size={23} /><div><strong>{String(candidate.model_id || "forecast").replaceAll("_", " ")}</strong><p>SPY total return {pct(candidate.predicted_values?.spy_total_return, 2)} · spread change {pct(candidate.predicted_values?.term_spread_change, 2)} · paper probe {pct(candidate.target_weight, 1)}</p><span>{candidate.promotion_eligible ? "eligible only after settled tournament evidence" : "diagnostic / prior rejection preserved"}</span></div><Status ok={candidate.promotion_eligible !== false}>{candidate.promotion_eligible ? "collecting" : "shadow only"}</Status></article>)}</div>
        <div className="capital-closure-rule"><Activity size={20} /><div><strong>Why these ERP numbers differ</strong><p>The 4.28% figure back-solves the index’s total cash-flow return and subtracts its matched valuation Treasury. Policy v5 recomposes that same Treasury plus ERP into the return forecast; horizon cash remains only the economic comparator. Frozen v4 runs used horizon cash plus ERP and stay unchanged. Earnings/dividend spreads, factor-required returns, and Arrow prices remain diagnostics with different definitions, not substitute forecasts.</p></div></div>
        {modelResearchActivations.map((activation) => <div className="capital-closure-rule" key={activation.activation_sha256}><GitBranch size={20} /><div><strong>{String(activation.action).replaceAll("_", " ")}</strong><p>{String(activation.model_id).replaceAll("_", " ")}: {activation.reason}. The agent may propose a separately identified evidence project; the kernel cannot rewrite the ancestor or change positions.</p></div></div>)}
        <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>Category boundary</strong><p>The implied-required-return challenger is a valuation expectation, not a state price. ERP change is recorded as a diagnostic because it mechanically shares the future equity-price outcome; only independently observed term-spread change receives linked-mechanism credit. The rejected Newton candidate cannot enter the authority-eligible survivor set.</p></div>{marketStateRun.run_path ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(marketStateRun.run_path)}><FileText size={14} />Inspect state block</button> : null}</div>
      </> : <Empty title="No prospective market-state block yet" body="Refresh the three-source public bundle to freeze the first 90-day and one-year state episodes. No API credential is required." />}
    </Section>
    <Section eyebrow="Neurosymbolic execution" title="Capability-adaptive valuation market"
      description="The same source-bound valuation task is offered to the typed interpreter, direct frontier reasoning, a frontier-authored bounded program, and their agreement-gated hybrid. One independent numeric carrier checks all agent outputs. Routing follows same-family receipts for the current model/runtime epoch rather than a fixed belief about what agents can do."
      actions={<ActionButton action="execution-market" busy={busy} onAction={onAction} primary>Run live valuation tournament</ActionButton>}>
      {executionRun.run_id ? <>
        <div className="capital-discovery-status">
          <div><span>Task</span><strong>{executionRun.task?.input_payload?.entity_id || "valuation"}</strong><small>implied growth · source-bound</small></div>
          <div><span>Route</span><strong>{String(executionPlan.routing_mode || "shadow").replaceAll("_", " ")}</strong><small>{executionPlan.primary_executor_id || "valuation interpreter"}</small></div>
          <div><span>Agent passes</span><strong>{number(executionRun.agent_verification_pass_count, 0)} / {executionAgentLanes.length}</strong><small>direct + program + hybrid</small></div>
          <div><span>Receipts</span><strong>{number(executionMarket.receipt_count, 0)}</strong><small>{number(executionMarket.run_count, 0)} task run{Number(executionMarket.run_count) === 1 ? "" : "s"}</small></div>
          <div><span>Authority</span><strong>analytical shadow</strong><small>no capital transition</small></div>
        </div>
        <div className="capital-tournament-list">{executionLanes.map((lane) => {
          const executor = lane.executor || {};
          const verification = lane.verification || {};
          const output = lane.output || {};
          const holdout = verification.counterfactual_case_count
            ? ` · unseen cases ${verification.counterfactual_pass_count}/${verification.counterfactual_case_count}`
            : "";
          return <article key={executor.executor_sha256 || executor.executor_id}><Activity size={23} /><div><strong>{String(executor.executor_id || "executor").replaceAll("_", " ")}</strong><p>{String(executor.mode || "").replaceAll("_", " ")} · implied growth {pct(output.implied_growth, 3)}</p><span>{executor.runtime} / {executor.model} · residual {verification.relative_value_residual == null ? "—" : Number(verification.relative_value_residual).toExponential(2)}{holdout}</span></div><div><Status ok={Boolean(verification.passed)}>{verification.passed ? "verified" : "rejected"}</Status></div></article>;
        })}</div>
        <div className="capital-closure-rule"><ShieldCheck size={20} /><div><strong>The model may search beyond the grammar</strong><p>It may reason directly, compose tools, or write a new program. The task hash, evidence hashes, output type, residual tolerance, and authority ceiling stay fixed. A route changes only after the new executor earns current-epoch receipts.</p></div>{executionRun.run_path ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(executionRun.run_path)}><FileText size={14} />Inspect receipt</button> : null}</div>
      </> : <Empty title="No capability receipt yet" body="Run the tournament against the latest operator valuation. The interpreter remains the baseline while the frontier lanes accumulate independently checked same-family evidence." />}
    </Section>
    <Section eyebrow="Isolated model-family leaves" title="Probability current under control"
      description="One lane tests return-density actions. The company lanes test whether directed movement and two-quarter path geometry through valuation × durable-earnings states add information beyond simpler controls."
      actions={<><ActionButton action="market-flow" busy={busy} onAction={onAction}>Return-state diagnostic</ActionButton><ActionButton action="company-state-flow" busy={busy} onAction={onAction}>Company-state diagnostic</ActionButton><ActionButton action="company-state-path-action" busy={busy} onAction={onAction} primary>Open/replay path challenger</ActionButton></>}>
      {experiments.length ? <div className="capital-tournament-list">{experiments.map((row) => {
        if (row.schema === "jaggedthoughts-company-state-representation-replay-v1") {
          const losses = row.mean_cross_entropy || {};
          const reversible = row.comparisons?.reversible_joint || {};
          return <article key={row.replay_sha256}><Activity size={23} /><div><strong>Recursive state-representation replay</strong><p>{number(row.inference_block_count, 0)} prior-only next-quarter blocks · selected {Object.entries(row.selected_partition_counts || {}).map(([id, count]) => `${String(id).replaceAll("_", " ")} (${count})`).join(", ")}</p><span>loss {number(losses.directed_joint, 4)} directed · {number(losses.factorized_axes, 4)} separate axes · {number(losses.reversible_joint, 4)} reversible · directed minus reversible {number(reversible.observed_delta, 4)} (p {number(reversible.p_value, 4)})</span></div><div><Status ok={Boolean(row.representation_supported)}>{row.representation_supported ? "interaction survived" : "representation rejected"}</Status><button type="button" className="capital-link" onClick={() => onPreview && onPreview(row.summary_path)}>Full replay</button></div></article>;
        }
        if (row.schema === "jaggedthoughts-company-state-path-action-run-v1") {
          const checks = row.structural_checks || {};
          const contracts = row.outcome_contracts || [];
          const terminal = contracts.at(-1) || {};
          const settlement = row.settlement_status || {};
          const activation = settlement.model_research_activation || {};
          return <article key={row.run_sha256}><Activity size={23} /><div><strong>Two-quarter company-state path action</strong><p>{number(row.source_snapshot?.assignments?.length, 0)} frozen companies · {number(checks.total_structural_path_count, 0)} paths · {number(row.required_control_ids?.length, 0)} controls</p><span>circulation effect {number(checks.minimum_current_ablation_l1, 5)}–{number(checks.maximum_current_ablation_l1, 5)} L1 · next evidence {String(settlement.next_due_at || terminal.settlement_not_before || "").slice(0, 10)} · {activation.empirical_markov_control_present ? "empirical Markov frozen" : "empirical Markov owed only if this survives"}</span></div><div><Status ok={false}>{String(settlement.status || "prospective shadow").replaceAll("_", " ")}</Status><button type="button" className="capital-link" onClick={() => onPreview && onPreview(row.summary_path)}>Full contract</button></div></article>;
        }
        if (row.schema === "jaggedthoughts-company-state-flow-evidence-v1") {
          const holdout = row.partition_summaries?.holdout || {};
          const directed = holdout.directed || {};
          const reversible = holdout.reversible || {};
          const passed = Object.values(row.gates || {}).filter(Boolean).length;
          const total = Object.keys(row.gates || {}).length;
          return <article key={row.evidence_sha256}><Activity size={23} /><div><strong>{row.experiment_id}</strong><p>{row.panel_count} quarterly panels · {row.transition_block_count} transitions · gates {passed}/{total}</p><span>holdout state loss {number(directed.state_cross_entropy, 4)} directed vs {number(reversible.state_cross_entropy, 4)} reversible · current {number(holdout.mean_circulation_strength, 5)}</span></div><div><Status ok={Boolean(row.promotion_eligible)}>{row.promotion_eligible ? "incremental edge" : "rejected"}</Status><button type="button" className="capital-link" onClick={() => onPreview && onPreview(row.summary_path)}>Full result</button></div></article>;
        }
        const candidate = (row.model_metrics || []).find((metric) => metric.model_id === "lagrangian_probability_current") || {};
        const integrity = row.evaluation_integrity || {};
        return <article key={row.market_flow_backtest_sha256}><Activity size={23} /><div><strong>{row.experiment_id}</strong><p>{row.episode_count} episodes · direction {pct(candidate.directional_accuracy)} · error {number(candidate.mean_absolute_return_error, 5)} · after-cost return {pct(candidate.mean_net_directional_return, 2)}</p><span>{row.screen_pass ? "beat all declared controls" : `failed control screen · best economic control ${row.best_economic_control || "unavailable"}`} · {String(integrity.evidence_authority || "temporal authority unverified").replaceAll("_", " ")}</span></div><div><Status ok={Boolean(row.screen_pass && integrity.backtest_evidence_eligible)}>{row.screen_pass ? (integrity.backtest_evidence_eligible ? "backtest evidence" : "diagnostic only") : "rejected"}</Status><button type="button" className="capital-link" onClick={() => onPreview && onPreview(row.summary_path)}>Full result</button></div></article>;
      })}</div> : <Empty title="No market-flow diagnostic" body="Run the bounded retrospective leaf. A later prospective collection must be a distinct profile and evidence epoch." />}
      {experiments.length ? <div className="capital-closure-rule"><AlertTriangle size={18} /><div><strong>Current result: no path model influences selection</strong><p>The retrospective return-density model lost to simpler controls. Prior-only recursive state enumeration repeatedly selected the 2×2 valuation × durability representation, but its directed joint dynamics lost to separate-axis and reversible controls. The two-quarter challenger is frozen and awaiting its September and December company-state outcomes.</p></div></div> : null}
    </Section>
    <Section eyebrow="Evidence-backed mechanism search" title="Newton research projects"
      description="Each project freezes a source epoch and chronological partitions. A signed-in subscription research agent proposes executable equations; the fixed harness fits them on visible rows and scores unchanged code on later rows. No API key or capital authority is involved.">
      {researchProjects.length ? <div className="capital-tournament-list">{researchProjects.map((project) => {
        const rows = project.row_counts || {};
        const gates = Object.values(project.partition_gates || {});
        const gatePasses = gates.reduce((count, row) => count + Object.values(row).filter(Boolean).length, 0);
        const gateTotal = gates.reduce((count, row) => count + Object.keys(row).length, 0);
        const shadow = project.prospective_shadow || {};
        return <article key={project.project_id}><Activity size={23} /><div><strong>{project.label}</strong><p>{number(project.search_lineage?.evaluation_row_count, project.iteration_count)} evaluation rows · {number(project.search_lineage?.submission_count, 0)} submitted candidates · current candidate {String(project.search_lineage?.current_candidate_source || "unknown").replaceAll("_", " ")}</p><span>deterministic score {project.score ?? "—"} · gates {gatePasses}/{gateTotal || 0} · {number(rows.visible, 0)} visible · {number(rows.holdout, 0)} holdout · {number(rows.farther_tail, 0)} farther-tail episodes</span>{shadow.schema ? <small>Prospective shadow · {number(shadow.pending_count, 0)} pending / {number(shadow.settled_count, 0)} settled · state date {shadow.latest_state_date || "awaiting public prices"} · next {String(shadow.next_activation || "settlement").replaceAll("_", " ")}</small> : null}</div><div><Status ok={Boolean(project.screen_pass)}>{String(project.status || "unknown").replaceAll("_", " ")}</Status><code>{project.mode}</code>{project.result_path ? <button type="button" className="capital-link" onClick={() => onPreview && onPreview(project.result_path)}>Full result</button> : null}</div></article>;
      })}</div> : <Empty title="No registered mechanism project" body="Register a frozen-evidence autoresearch project in workspace.yaml." />}
      <div className="capital-closure-rule"><GitBranch size={20} /><div><strong>What the Lagrangian / Newton lane did</strong><p>The single-security density, ERP × term-spread, and cross-sectional current families lost to simpler controls. {companyPathAdmission.status === "complete" ? `The subscription-searched company-path candidate also failed its locked one-shot admission: holdout cross-entropy ${number(companyPathHoldout.metrics?.candidate?.cross_entropy, 3)} versus ${number(companyPathHoldout.metrics?.first_order_markov?.cross_entropy, 3)} for first-order Markov, and farther-tail ${number(companyPathTail.metrics?.candidate?.cross_entropy, 3)} versus ${number(companyPathTail.metrics?.first_order_markov?.cross_entropy, 3)}. It cannot become the prospective successor.` : "The company-path successor has not completed its one-shot historical admission."} The separate September and December path contracts remain frozen and have no selection authority.</p></div></div>
    </Section>
    <Section eyebrow="Shared world-model interface" title="Prospective model tournaments"
      description="Frozen forecasts cover the same point-in-time episodes. Survivor committees reflect corrected paired comparisons and never receive capital authority.">
      {rows.length ? <div className="capital-tournament-list">{rows.map((row) => <article key={row.tournament_id}><Activity size={23} /><div><strong>{row.tournament_id}</strong><p>{row.episode_count} episodes · {row.inference_block_count} blocks · survivors {(row.survivor_model_ids || []).join(", ")}</p><span>{String(row.evaluation_integrity?.evaluation_class || row.mode || "unclassified").replaceAll("_", " ")}</span></div><div><Status ok={false}>{row.capital_authority === false || row.evaluation_integrity?.paper_policy_authority === false ? "no capital authority" : "authority unverified"}</Status><button type="button" className="capital-link" onClick={() => onPreview && onPreview(row.report_path)}>Report</button></div></article>)}</div>
        : <Empty title="No tournament result" body="Add a frozen model/episode matrix under tournaments/ and compile the workspace." />}
    </Section>
  </>;
}

export function InvestmentPanel({ view = "Overview", state, message, busy, onAction, onPreview }) {
  const active = VIEWS.has(view) ? view : "Overview";
  const payload = state && typeof state === "object" ? state : {};
  const preview = (relative) => {
    if (!relative || !onPreview) return;
    const absoluteRoot = String(payload.workspace_path || "").replace(/\/$/, "");
    const previewRoot = String(payload.workspace_preview_root || "").replace(/\/$/, "");
    let path = String(relative);
    if (absoluteRoot && path.startsWith(`${absoluteRoot}/`)) path = path.slice(absoluteRoot.length + 1);
    if (path.startsWith("/") || !previewRoot) return;
    onPreview({
      type: "file",
      value: path.startsWith(`${previewRoot}/`) ? path : `${previewRoot}/${path}`,
    });
  };
  if (!payload.initialized) return <Section eyebrow="JaggedThoughts Capital" title="Initialize the investment workspace"
    description="Create the private local operating directories, public-source manifest, golden store, and visibly labelled acceptance fixture. No brokerage connection is created."
    actions={<ActionButton action="init" busy={busy} onAction={onAction} primary>Initialize workspace</ActionButton>}>
    {message ? <div className="capital-message">{message}</div> : null}
    <div className="capital-authority"><ShieldCheck size={28} /><div><strong>Local and paper-only by construction</strong><p>The capital workspace is unavailable when the server runs in public project scope.</p></div></div>
  </Section>;
  return <div className="capital-workspace">
    {message ? <div className="capital-message">{message}</div> : null}
    {active === "Overview" ? <Overview state={payload} busy={busy} onAction={onAction} onPreview={preview} /> : null}
    {active === "Sources & signals" ? <Sources state={payload} busy={busy} onAction={onAction} onPreview={preview} /> : null}
    {active === "Opportunities" ? <OpportunityFunnel state={payload} onPreview={preview} busy={busy} onAction={onAction} /> : null}
    {active === "Strategy frontier" ? <StrategyFrontier state={payload} onPreview={preview} /> : null}
    {active === "Plays" ? <Plays state={payload} onPreview={preview} busy={busy} onAction={onAction} /> : null}
    {active === "Portfolio" ? <Portfolio state={payload} onPreview={preview} /> : null}
    {active === "Shadow book" ? <ShadowBook state={payload} onPreview={preview} busy={busy} onAction={onAction} /> : null}
    {active === "World models" ? <WorldModels state={payload} onPreview={preview} busy={busy} onAction={onAction} /> : null}
  </div>;
}
