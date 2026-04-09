"""
bayesian_updater.py — V2 Epistemic Engine

Reads a champion_probability_dag.json (falling back to latest_probability_dag.json), accepts a real-world observation
for one node, and recalculates all downstream probabilities using exponential
decay (from recursive_bayesian v2_score_65 spec).

Usage:
    python -m src.ztare.experiments.bayesian_updater --project ai_inference_collapse \
        --node hyperscaler_routing --actual 0.55 --market 0.80

    --node      : the node id to update (from champion_probability_dag.json / latest_probability_dag.json)
    --actual    : the observed real-world value (0.0 - 1.0)
    --market    : the market's current implied probability (for EV calculation)
"""

import json
import math
import argparse
import os
from datetime import datetime
from src.ztare.common.paths import PROJECTS_DIR

parser = argparse.ArgumentParser()
parser.add_argument("--project", required=True)
parser.add_argument("--node", required=True, help="Node ID to update with real-world observation")
parser.add_argument("--actual", type=float, required=True, help="Observed real-world probability (0.0-1.0)")
parser.add_argument("--market", type=float, default=None, help="Market implied probability for EV calc")
args = parser.parse_args()

PROJECT_DIR = str(PROJECTS_DIR / args.project)
PRIMARY_DAG_PATH = f"{PROJECT_DIR}/champion_probability_dag.json"
FALLBACK_DAG_PATH = f"{PROJECT_DIR}/latest_probability_dag.json"
WEIGHTS_PATH = f"{PROJECT_DIR}/axiom_weights.json"
AXIOM_PATH = f"{PROJECT_DIR}/verified_axioms.json"

# From recursive_bayesian v2_score_65 spec
DECAY_RATE_SCALAR = 1.1
MIN_AXIOM_WEIGHT = 0.05
EPSILON = 1e-9


def load_dag():
    dag_path = PRIMARY_DAG_PATH if os.path.exists(PRIMARY_DAG_PATH) else FALLBACK_DAG_PATH
    if not os.path.exists(dag_path):
        print(f"❌ No champion_probability_dag.json or latest_probability_dag.json found in {PROJECT_DIR}")
        print("   Run V1 first: python -m src.ztare.validator.autoresearch_loop --project <project> --rubric <rubric> --dynamic")
        exit(1)
    with open(dag_path) as f:
        return json.load(f)


def load_weights():
    if os.path.exists(WEIGHTS_PATH):
        with open(WEIGHTS_PATH) as f:
            return json.load(f)
    # Initialize from verified_axioms if no weights yet
    if os.path.exists(AXIOM_PATH):
        with open(AXIOM_PATH) as f:
            axioms = json.load(f)
        return {ax: 1.0 for ax in axioms}
    return {}


def exponential_decay(prior, penalty):
    """From recursive_bayesian v2_score_65: non-linear decay prevents catastrophic collapse."""
    return max(prior * math.exp(-DECAY_RATE_SCALAR * penalty), 0.0)


def calculate_relative_error(predicted, actual):
    """Normalized error — decoupled from scale."""
    return abs(predicted - actual) / max(actual, EPSILON)


def update_dag(dag, node_id, actual_value):
    """Update a node's probability and propagate downstream."""
    nodes = {n["id"]: n for n in dag["nodes"]}
    edges = dag["edges"]

    if node_id not in nodes:
        print(f"❌ Node '{node_id}' not found in DAG.")
        print(f"   Available nodes: {list(nodes.keys())}")
        exit(1)

    # Calculate penalty for the observed node
    prior = nodes[node_id]["probability"]
    error = calculate_relative_error(prior, actual_value)
    penalty = error  # RAG latency decoupled per spec
    new_prob = exponential_decay(prior, penalty)

    print(f"\n{'='*50}")
    print(f"NODE UPDATE: {node_id}")
    print(f"  Prior probability : {prior:.3f}")
    print(f"  Observed actual   : {actual_value:.3f}")
    print(f"  Relative error    : {error:.3f}")
    print(f"  Posterior         : {new_prob:.3f}")
    print(f"{'='*50}")

    nodes[node_id]["probability"] = new_prob

    # Propagate to outcome via edges
    outcome = dag["outcome"]
    outcome_edges = [e for e in edges if e["to"] == "outcome"]

    if outcome_edges:
        # Recalculate outcome probability as weighted sum of upstream nodes
        weighted_sum = sum(
            nodes[e["from"]]["probability"] * e["weight"]
            for e in outcome_edges
            if e["from"] in nodes
        )
        total_weight = sum(e["weight"] for e in outcome_edges)
        new_outcome_prob = weighted_sum / total_weight if total_weight > 0 else 0.0

        old_outcome = outcome["probability"]
        outcome["probability"] = new_outcome_prob

        print(f"\nOUTCOME: {outcome['label']}")
        print(f"  Before update : {old_outcome:.3f}")
        print(f"  After update  : {new_outcome_prob:.3f}")
        print(f"  Delta         : {new_outcome_prob - old_outcome:+.3f}")

        # Kelly Criterion / EV if market probability provided
        if args.market is not None:
            edge = new_outcome_prob - args.market
            print(f"\nSUPERFORECASTING EDGE:")
            print(f"  Market implied  : {args.market:.3f}")
            print(f"  Engine estimate : {new_outcome_prob:.3f}")
            print(f"  Edge            : {edge:+.3f}")
            if edge > 0.05:
                kelly = edge / (1 - args.market) if args.market < 1 else 0
                print(f"  Kelly fraction  : {kelly:.3f} (bet YES)")
                print(f"  Signal          : ✅ POSITIVE EDGE — market underpricing this outcome")
            elif edge < -0.05:
                kelly = abs(edge) / args.market if args.market > 0 else 0
                print(f"  Kelly fraction  : {kelly:.3f} (bet NO)")
                print(f"  Signal          : ✅ POSITIVE EDGE — market overpricing this outcome")
            else:
                print(f"  Signal          : ⚖️  NO SIGNIFICANT EDGE — within noise threshold")

    dag["nodes"] = list(nodes.values())
    dag["last_updated"] = datetime.now().isoformat()
    return dag


def update_axiom_weights(weights, node_id, error):
    """Propagate error back to verified_axioms that map to this node."""
    # Nodes map loosely to axioms — degrade axioms containing the node's concept
    updated = {}
    for axiom, weight in weights.items():
        if node_id.lower().replace("_", " ") in axiom.lower():
            penalty = error / 3  # Distribute across likely related axioms
            new_weight = exponential_decay(weight, penalty)
            if new_weight < MIN_AXIOM_WEIGHT:
                new_weight = 0.0
                print(f"  ⚠️  Axiom RETIRED (weight below threshold): {axiom[:60]}...")
            updated[axiom] = new_weight
        else:
            updated[axiom] = weight
    return updated


if __name__ == "__main__":
    print(f"\n🔄 BAYESIAN UPDATER — Project: {args.project}")
    print(f"   Updating node '{args.node}' with observed value {args.actual:.3f}")

    dag = load_dag()
    weights = load_weights()

    # Calculate error before update for axiom weight propagation
    nodes_by_id = {n["id"]: n for n in dag["nodes"]}
    prior_prob = nodes_by_id.get(args.node, {}).get("probability", 0.5)
    error = calculate_relative_error(prior_prob, args.actual)

    # Update DAG
    updated_dag = update_dag(dag, args.node, args.actual)

    # Update axiom weights
    updated_weights = update_axiom_weights(weights, args.node, error)

    # Save
    with open(DAG_PATH, "w") as f:
        json.dump(updated_dag, f, indent=2)

    with open(WEIGHTS_PATH, "w") as f:
        json.dump(updated_weights, f, indent=2)

    print(f"\n✅ Saved updated DAG → {DAG_PATH}")
    print(f"✅ Saved updated axiom weights → {WEIGHTS_PATH}")
    print(f"\nNext run of V1 will use updated priors automatically.\n")
