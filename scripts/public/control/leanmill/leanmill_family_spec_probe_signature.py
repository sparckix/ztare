#!/usr/bin/env python3
"""Compat module-alias: ``leanmill_family_spec_probe_signature`` -> sibling ``family_spec_probe_signature``.
The cleanup branch renamed leanmill_*.py siblings to *.py but importers still use
the leanmill_ prefix; this aliases the module so ``from leanmill_family_spec_probe_signature import X`` works.
New code should import ``family_spec_probe_signature`` (or ``ztare.leanmill.*``) directly."""
import importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.modules[__name__] = importlib.import_module("family_spec_probe_signature")
