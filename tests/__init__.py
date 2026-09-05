"""The library suite, tiered by directory.

This file exists to make the directory a package, and that is load-bearing
rather than incidental. Under the prepend import mode the suite runs with, only
a module's own directory lands on the search path, so a helper in `tests/` is
invisible from `tests/integration/` and the failure is a `ModuleNotFoundError`
at collection. A package puts the repository root on the path instead, which is
what lets every tier import `tests.helpers.stub_socket` from any depth.

It also makes a repeated basename legal, so a later split into per-subject
directories is available. Nothing here asks for one.
"""
