"""Doubles and reflection helpers shared across the tiers.

Two of the three have importers in more than one tier, so co-locating each
helper with its callers is not available.

`conftest.py` is not here. Its location is what scopes the autouse leak guard,
which has to reach every tier, so it stays at the root of the suite.
"""
