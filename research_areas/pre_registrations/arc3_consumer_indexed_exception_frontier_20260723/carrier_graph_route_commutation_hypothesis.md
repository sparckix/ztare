# Carrier/evidence-route commutation

Date: 2026-07-26  
Hypothesis ID: `H-ARC3-CARRIER-GRAPH-ROUTE-COMMUTATION-20260726-32`  
Status: preregistered

## Eigenquestion

Why can the evidence-compiled partial action system reach the observed H29
target while the accepted predictive carrier's factored search cannot?

## Hypothesis

The H29 route is transported faithfully by the carrier: starting from the same
trace state and time, carrier replay of each nonterminal operation preserves
the evidence graph representative's terminal key
`(controlled_base, finite_configuration)` at every step and reaches the
observed H29 target before the terminal operation. If this holds while H31
search fails, the defect is in search equality/dominance. If it fails, the
first divergent edge localizes a predictive-carrier or graph-to-carrier
transport defect.

## Fixed lowering

- rebuild the H29 active mechanism problem from the same trace, report, carrier
  identity, sealed trajectory ledger, and current seed;
- require the reconstructed graph counts and H29 source/route identity to
  match the frozen H29 result;
- recover the 28-edge graph prefix to source `26bcf98b…`; operation `1` remains
  the terminal edge and is not predicted;
- replay that prefix from trace row zero at recorded time through the unchanged
  carrier;
- after every operation compare all compiled fiber factors, with
  `controlled_base` and `finite_configuration` reported separately as the
  terminal key;
- bind each graph edge to its deterministic target, boundary/context flags,
  lineage digests, and evidence references.

## Discriminating test

Produce a step table containing graph source/target identities, action,
carrier-predicted state digest, graph representative digest, factor differences
and graph edge lineage. Record the first terminal-key divergence, first
any-factor divergence, and final H29 goal-edge result. Also report whether
either divergence precedes a typed context transition or boundary.

## Success criterion

- reconstructed graph and route match H29 with zero ambiguity;
- every prefix edge is deterministic and non-boundary;
- all 28 carrier images preserve the graph target terminal key;
- the final predicted state satisfies the observed H29 target problem for
  operation `1`.

## Kill conditions

Reject on graph drift, route drift, missing edge/representative/lineage,
carrier `None`, any terminal-key divergence, final goal miss, or environment
contact. An earlier difference confined to nonterminal presentation factors is
recorded but does not by itself refute terminal-key transport.

## Claim boundary

A pass localizes H31 to search pruning. A failure localizes the earliest
carrier/evidence transport defect. It does not repair the model or authorize a
live route.
