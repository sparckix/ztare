"""Back-compat shim. The cognitive-gym hooks ENGINE + the substrate-keyed leg-connector registry moved
to the substrate-agnostic home `ztare.common.cognitive_gym` (2026-06-06): the dispatcher now routes the
Three Legs across BOTH the regression substrate (inverter_agent / compress_champion / margin_of_safety)
and the lean substrate (the leanmill moves), so it is not RD-specific. Import from
`ztare.common.cognitive_gym`; this re-export keeps older `research_director.cognitive_gym_hooks` imports
working."""
from ztare.common.cognitive_gym import *  # noqa: F401,F403
from ztare.common.cognitive_gym import (  # noqa: F401  (explicit; no __all__ in source)
    CognitiveGymRequest, CognitiveGymResponse, dispatch, invert, compress, disagree, all_three,
    register_leg_connector, maybe_dispatch_to_inner, call_gemini,
)
