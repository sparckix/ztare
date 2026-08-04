# Post-transition epoch-sibling operation-0 result

Date: 2026-07-26

Status: confirmed; adapter epoch boundary

The no-worker probe selected the exact 66-action route and executed it as three
22-action legs. The first two legs ended in known context transitions and
replanned without exclusions. The third reached source `495dd39e5a54…` and
executed operation 0. The live controller initially returned the row as an
observed acquisition, with no new non-discharge marker.

One row was admitted at index 65. The sealed slice is
`eval_20260727T003326766130Z.jsonl`, SHA-256
`048d772cb6dff329eee3749cab1501528ae686e31e5247e678dc64f8486fa3f1`.
No worker selected an action. The external completed-level counter stayed at
two.

Sealed recompilation applies the transition identity carried by the row and
classifies operation 0 as `epoch_boundary`. The intermediate audit that called
it a context transition used the archive-order-defective 240-node chart and is
superseded by H21's trajectory-owned compilation. In the compact graph,
operations 0 and 1 are both epoch boundaries at this source; operation 2 was
the next sibling intervention.
