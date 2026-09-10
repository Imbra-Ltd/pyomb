"""Pins the TLS integration suite's certificate directory to the generator's.

The five TLS integration tests gate on file existence (`HAVE_CERTS`), not on
path correctness, so a certificate directory that drifts from what
`scripts/gen_test_certs.py` actually writes produces a clean "5 skipped"
report instead of a failure -- exactly what happened when the test file moved
into `tests/integration/` and its path climbed one directory too few. This
test has no such gate: it compares the two path computations directly, so it
fails the moment they diverge, whether or not a chain happens to be on disk.
"""

import pathlib
import unittest

from scripts.gen_test_certs import DEFAULT_OUT
from tests.integration.test_tls_integration import CERTS


class TheCertificateDirectoryMatchesTheGenerator(unittest.TestCase):
    """Pins the suite's expected directory to the generator's output directory."""

    def test_the_suite_looks_where_the_generator_writes(self):
        """A drifted path makes every TLS integration test skip, not fail."""

        repo_root = pathlib.Path(__file__).resolve().parent.parent
        expected = (repo_root / DEFAULT_OUT).resolve()

        self.assertEqual(pathlib.Path(CERTS).resolve(), expected)


if __name__ == "__main__":
    unittest.main()
