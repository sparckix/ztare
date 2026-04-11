## Paper 4 Manuscript Seed

This program turns the frozen Paper 4 outline into first-pass manuscript prose without reopening the locked outline claims silently.

Upstream frozen contract:
- `research_areas/drafts/paper4_drafting_paper_outline.md`
- `research_areas/specs/paper4_drafting_paper_outline_prose_spec.json`
- `research_areas/private/papers/paper4.md`

Manuscript pressure points that must be handled explicitly:
1. Principal scalability:
   explain whether the M-form hits a bottleneck if one human principal must approve many concurrent programs, and how principal delegation or layered oversight would work without collapsing governance.
2. Native primitive versus hard governance:
   explain why Constitutional AI or prompt-level alignment is not the same category as hard-gated M-form governance, and why the paper does not assume a native mathematical U-form alignment primitive exists today.
3. Title framing:
   pressure-test whether the title should continue to lead with `Managerial Capitalism`, or whether the paper should foreground AI governance, principal-agent control, or bounded recursive self-improvement more directly.

Operating rule:
- use the frozen outline as the default contract
- if manuscript drafting reveals a real thesis mismatch, record it explicitly in debate before changing the manuscript direction
- do not silently reintroduce dropped claims such as capital-efficiency superiority or broad operator-bandwidth proof

Target output for the first manuscript run:
- a first-pass manuscript draft or a bounded manuscript section, depending on the active target
- prose that carries the locked outline forward while addressing the three pressure points above in the manuscript itself
