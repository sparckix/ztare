"""Back-compat shim for the shared validation-operator router.

The implementation moved to ``ztare.common.cognitive_gym`` on 2026-06-06 so
regression and proof-substrate connectors could share one dispatch surface. New
code should import from ``ztare.common.cognitive_gym``. This module keeps older
``research_director.cognitive_gym_hooks`` imports working.
"""
from ztare.common.cognitive_gym import *  # noqa: F401,F403
from ztare.common.cognitive_gym import (  # noqa: F401  (explicit; no __all__ in source)
    CognitiveGymRequest, CognitiveGymResponse, dispatch, invert, compress, disagree, all_three,
    register_leg_connector, maybe_dispatch_to_inner, call_gemini,
)
