# H127 result — raw history now compiles directly to sparse recall

Status: **passed within the preregistered offline boundary**.

The compiler consumed H119's raw Level-1 transitions, terminal predecessor,
boundary action, current Level-2 grid, exact five-axis recall scope, budget,
and evidence/cost bindings. It received no target palette, coordinates, route,
prefix, entity bearing, selected direction, or selected action.

It produced one palette/D4-quotiented source memory revision, extracted the
current graph, found the longest common approach of competing feasible routes
(`up,right,right`), classified the `right/down` branch competition, and selected
`down`/action 1. The ordinary wake-sleep selector admitted exactly that
candidate under the frozen scope. Mutating task, controller, context, choice
set, or action vocabulary independently produced zero selections.

The audit also caught a goal-identity leak inherited from H125: matching the
source goal's literal color had passed because source and target palettes were
permuted together. The corrected goal identity uses graph attachment and the
learned connector relation. Changing target entity and goal colors now leaves
the source memory and canonical frontier unchanged. All eight D4 target
presentations do the same.

This removes the probe-authored semantic translation used by H126. The next
test must inject the compiler's serialized output at the full Level-2 start and
measure controller/task effect against a mechanically redacted equal-byte
control. Online target settlement and later-task acquisition savings remain
after that.

Evidence:

- `h127_autonomous_relational_affordance_recall_result.json`
  (`9a61127622e25ad4f16fb16edffa2ccf6f8ea2f2e835dda89281d1c52422df4b`)
- `h127_autonomous_relational_affordance_recall_audit.py`
- `src/ztare/worldmodel/relational_affordance_recall.py`
