"""Unified inbound-message channel.

One ``MessageSource`` ABC; concrete sources for telegram, orbit, and
interactive terminals. Operator steering arrives through one
abstraction so the agent treats all delivery rails identically.

Input-only and advisory: output-side discipline is the membrane's job
in ``ztare.gates``. A missed inbound message is a missed signal, never
a laundering hole.
"""
