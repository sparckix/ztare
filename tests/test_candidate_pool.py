from __future__ import annotations

import hashlib

from ztare.worldmodel.candidate_pool import add_candidate, surviving_committee
from ztare.worldmodel.episode_log import EpisodeLog


def test_candidate_pool_loads_patch_base_through_canonical_carrier_door(tmp_path):
    base = tmp_path / "workspace" / "submissions" / "base.py"
    base.parent.mkdir(parents=True)
    base.write_text(
        "def step(state, action, time):\n"
        "    return ((1,),)\n",
        encoding="utf-8",
    )
    base_sha = hashlib.sha256(base.read_bytes()).hexdigest()
    source = (
        "PATCH_BASE = {'source_ref': 'workspace/submissions/base.py', "
        f"'sha256': '{base_sha}'}}\n"
        "def PATCH_DELTA(base_next, state, action):\n"
        "    return ((2,),)\n"
    )
    add_candidate(tmp_path, source, carrier="PATCH_BASE", origin="fixture")
    log = EpisodeLog()
    log.append(((0,),), 0, ((2,),), t=0)

    committee = surviving_committee(tmp_path, log)

    assert len(committee) == 1
    assert committee[0](((0,),), 0, 0) == ((2,),)
