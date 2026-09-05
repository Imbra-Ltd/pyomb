"""Tests that open a real socket or start a worker thread.

Membership is decided by what a module does -- binds, listens, accepts, or
starts a thread -- never by what it imports or mentions. A module that drives
`StubSocket` or a mock is a unit test whatever its subject is called, which is
why the transport and simulator modules mostly sit a directory up.

The tier is derived from this directory by the collection hook in
`tests/conftest.py`. No module here carries a marker of its own.
"""
