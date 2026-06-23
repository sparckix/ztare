"""Damage-signal channel (GP-129 Matzinger pull-forward).

Any process can emit a damage signal — an orthogonal channel to the
identity-based authorization in src.ztare.roles.authorization. The
manager-agent mandate requires listing active damage signals before
deciding on the next action.
"""

from ztare.signals.damage import emit, list_recent, clear

__all__ = ["emit", "list_recent", "clear"]
