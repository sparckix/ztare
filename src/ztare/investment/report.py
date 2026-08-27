"""Human-readable views over compiled investment artifacts."""

from __future__ import annotations

from typing import Any, Mapping


def _pct(value: Any) -> str:
    return f"{100 * float(value):.2f}%"


def decision_report(decision: Mapping[str, Any]) -> str:
    summary = decision["summary"]
    entity = decision["entity"]
    play = decision["play"]
    market = decision["market_state"]
    fingerprint = decision["fingerprint"]
    valuation = decision["valuation_envelope"]
    valuation_summary = valuation["summary"]
    selection = decision["policy_selection"]
    proposal = decision["position_proposal"]
    certificate = decision["policy_synthesis"]["certificate"]
    underwriting = decision["underwriting_case"]
    lifecycle = decision.get("profile_lifecycle") or {"data_class": "operator", "stage": "active"}
    lines = [
        f"# Investment decision: {decision['decision_id']}",
        "",
        f"- Authority: `{decision['authority']}`",
        f"- Profile lifecycle: `{lifecycle.get('data_class')}/{lifecycle.get('stage')}`",
        f"- Decision time: `{decision['as_of']}`",
        f"- Entity: {entity['name']} (`{entity['entity_id']}`)",
        f"- Play: `{play['play_key']}` against `{play['benchmark_id']}`",
        f"- Evidence snapshot: `{decision['point_in_time_snapshot']['snapshot_sha256']}`",
        f"- Decision record: `{decision['decision_record_sha256']}`",
        "",
        "## State and thesis",
        "",
        f"Fingerprint score: **{float(fingerprint['aggregate_score']):.3f}**. "
        f"Premium committee: **{_pct(market['weighted_premium'])}** annualized; "
        f"downside estimate: **{_pct(market['weighted_downside'])}**; "
        f"dispersion: **{_pct(market['premium_dispersion'])}**.",
        "",
        str(decision["thesis"]["claim"]),
        "",
        "Falsifiers:",
        "",
        *(f"- {row}" for row in decision["thesis"]["falsifiers"]),
        "",
        "## Underwriting challenge",
        "",
        f"Outside view: {underwriting['outside_view_reference']} "
        f"(declared base rate: **{_pct(underwriting['outside_view_base_rate'])}**).",
        "",
        f"Hurdle: **{_pct(underwriting['hurdle_rate'])}** expected excess return. "
        f"Next-best alternative: {underwriting['next_best_alternative']}",
        "",
        f"Rival view: {underwriting['rival_view']}",
        "",
        f"Decisive observation: {underwriting['decisive_observation']}",
        "",
        "Failure sequence:",
        "",
        *(f"{index}. {row}" for index, row in enumerate(underwriting["failure_sequence"], 1)),
        "",
        "## Price-implied expectations",
        "",
        f"The valuation grammar produced {len(valuation['results'])} source-bound results "
        f"across {len(valuation['scenarios'])} strategy scenarios and rejected "
        f"{len(valuation['failures'])} incompatible or invalid programs. "
        f"Earnings-power value spans {float(valuation_summary['earnings_power_value_low']):,.2f}–"
        f"{float(valuation_summary['earnings_power_value_high']):,.2f} {entity['currency']} per share; "
        f"the explicit-period growth implied by price spans "
        f"{_pct(valuation_summary['implied_growth_low'])}–"
        f"{_pct(valuation_summary['implied_growth_high'])}.",
        "",
        f"Median price-implied required return: "
        f"**{_pct(valuation_summary['implied_required_return_median'])}**; "
        f"excess over the declared risk-free rate: "
        f"**{_pct(valuation_summary['price_implied_excess_return'])}**.",
        "",
        "## Recursive policy result",
        "",
        f"The bounded grammar enumerated {len(decision['policy_synthesis']['enumeration']['programs'])} programs; "
        f"{summary['frontier_count']} survived the robust frontier. "
        f"Scope closed: `{str(summary['scope_closed']).lower()}`; "
        f"decision closed: `{str(summary['decision_closed']).lower()}`; "
        f"representation: `{summary['representation_status']}`.",
        "",
        f"Selected `{selection['action_id']}` via `{selection['expression']}` "
        f"with utility `{float(selection['utility']):.6f}`.",
        "",
        "## Paper-book proposal",
        "",
        f"- Current weight: {_pct(proposal['current_weight'])}",
        f"- Target weight: {_pct(proposal['target_weight'])}",
        f"- Trade notional: {float(proposal['trade_notional']):,.2f} {entity['currency']}",
        f"- Estimated cost: {float(proposal['estimated_cost']):,.2f} {entity['currency']}",
        "- Economic status: pending later settlement",
        "",
    ]
    return "\n".join(lines)


def scorecard_report(scorecard: Mapping[str, Any]) -> str:
    return "\n".join([
        f"# Investment settlement: {scorecard['decision_id']}",
        "",
        f"- Decision record: `{scorecard['decision_record_sha256']}`",
        f"- Outcome: `{scorecard['outcome_sha256']}`",
        f"- Paper return: {_pct(scorecard['paper_return'])}",
        f"- Frozen no-action return: {_pct(scorecard['no_action_return'])}",
        f"- Benchmark return: {_pct(scorecard['benchmark_return'])}",
        f"- Net excess return: {_pct(scorecard['net_excess_return'])}",
        f"- Incremental return vs no action: {_pct(scorecard['incremental_return_vs_no_action'])}",
        f"- Charged transaction cost: {float(scorecard['transaction_cost']):,.2f}",
        f"- Scorecard: `{scorecard['scorecard_sha256']}`",
        "",
    ])


def tournament_report(result: Mapping[str, Any]) -> str:
    """Render a compact comparison view without hiding the authority boundary."""
    lines = [
        f"# World-model tournament: {result['tournament_id']}",
        "",
        f"- Mode: `{result['mode']}`",
        f"- As of: `{result['as_of']}`",
        f"- Baseline: `{result['baseline_model_id']}`",
        f"- Episodes / inference blocks: {result['episode_count']} / {result['inference_block_count']}",
        f"- Inference sufficient: `{str(result['inference_sufficient']).lower()}`",
        f"- Survivor committee: {', '.join(f'`{row}`' for row in result['survivor_model_ids'])}",
        f"- Capital authority: `{str(result['capital_authority']).lower()}`",
        f"- Tournament artifact: `{result['tournament_sha256']}`",
        "",
        "## Model scorecard",
        "",
        "| Model | Prediction loss | Linked loss | Net excess return | Active cumulative | Information ratio | Max drawdown |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["model_metrics"]:
        lines.append(
            f"| `{row['model_id']}` | {float(row['prediction_loss']['mean']):.4f} | "
            f"{float(row['linked_loss']['mean']):.4f} | {_pct(row['net_excess_return']['mean'])} | "
            f"{_pct(row['economic_backtest']['cumulative_active_return'])} | "
            f"{float(row['economic_backtest']['information_ratio']):.2f} | "
            f"{_pct(row['economic_backtest']['max_book_drawdown'])} |"
        )
    lines.extend(["", "## Corrected pairwise comparisons", ""])
    for row in result["paired_comparisons"]:
        fdr = row.get("fdr")
        if fdr is None:
            conclusion = "underpowered"
        else:
            conclusion = (
                f"q={float(fdr['q_value']):.4f}; "
                f"different={str(fdr['rejected_at_alpha']).lower()}"
            )
        lines.append(
            f"- `{row['left_model_id']}` vs `{row['right_model_id']}` on "
            f"`{row['dimension']}`: delta `{row.get('observed_delta')}`; {conclusion}"
        )
    lines.extend(["", str(result["use_boundary"]), ""])
    return "\n".join(lines)


__all__ = ["decision_report", "scorecard_report", "tournament_report"]
