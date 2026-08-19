"""The file handler is opt-in, and derives its name by appending.

Constructing a Logger attaches a console handler and nothing else -- a library
that opened a file on import would write into whatever directory the host
application happened to start in. log_to_file is the opt-in.

The derivation is the part with history. An earlier implementation built the
default name with str.replace on the extension, and an empty search string
makes str.replace insert between every character, so an entry point carrying
no extension ('server', or '-c' under python -c) produced names such as
'.logs.loge.logr.logv.loge.logr.log'. The tests below pin the appending form
against both shapes of argv[0].
"""

import logging
import os
import sys
import tempfile
import unittest

from pyomb.errors import ModbusBaseError
from pyomb.logger import Logger


class FileHandlerNaming(unittest.TestCase):
    """Pins the name file_handler picks when the caller supplies none."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.logger = Logger("naming")
        self.opened = []
        self.argv_zero = sys.argv[0]

    def tearDown(self):
        # A handler holding the file open stops the directory being removed on
        # Windows, so every handler this test opened is closed by hand
        for handler in self.opened:
            self.logger.removeHandler(handler)
            handler.close()

        sys.argv[0] = self.argv_zero
        self.directory.cleanup()

    def build(self, filename=None):
        handler = self.logger.file_handler(filename)
        self.opened.append(handler)

        return handler

    def path(self, name):
        return os.path.join(self.directory.name, name)

    def test_an_entry_point_with_an_extension_keeps_only_its_stem(self):
        sys.argv[0] = self.path("server.py")

        handler = self.build()

        self.assertEqual(handler.baseFilename, os.path.abspath(self.path("server.log")))

    def test_an_entry_point_without_an_extension_gains_one_suffix(self):
        """The shape that produced '.logs.loge.logr...' under str.replace."""

        sys.argv[0] = self.path("server")

        handler = self.build()

        self.assertEqual(handler.baseFilename, os.path.abspath(self.path("server.log")))

    def test_the_derived_name_carries_exactly_one_log_suffix(self):
        """A count survives a change of separator where an equality does not."""

        sys.argv[0] = self.path("server")

        handler = self.build()

        self.assertEqual(os.path.basename(handler.baseFilename).count(".log"), 1)

    def test_an_explicit_filename_is_used_as_given(self):
        target = self.path("explicit.log")

        handler = self.build(target)

        self.assertEqual(handler.baseFilename, os.path.abspath(target))

    def test_the_handler_carries_the_loggers_level_and_format(self):
        handler = self.build(self.path("configured.log"))

        self.assertIsInstance(handler, logging.FileHandler)
        self.assertEqual(handler.level, logging.INFO)
        self.assertEqual(handler.formatter._fmt, self.logger.log_format)


class FileLoggingIsOptIn(unittest.TestCase):
    """Pins what log_to_file attaches, and that nothing attaches it early."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.logger = Logger("opt-in")
        self.attached = None

    def tearDown(self):
        if self.attached is not None:
            self.logger.removeHandler(self.attached)
            self.attached.close()

        self.directory.cleanup()

    def path(self, name):
        return os.path.join(self.directory.name, name)

    def test_constructing_a_logger_opens_no_file(self):
        handlers = [h for h in self.logger.handlers if isinstance(h, logging.FileHandler)]

        self.assertEqual(handlers, [])

    def test_log_to_file_attaches_the_handler_it_returns(self):
        self.attached = self.logger.log_to_file(self.path("attached.log"))

        self.assertIn(self.attached, self.logger.handlers)

    def test_a_record_reaches_the_file_after_opting_in(self):
        target = self.path("written.log")
        self.attached = self.logger.log_to_file(target)

        self.logger.info("a record the file has to carry")
        self.attached.flush()

        with open(target, encoding="utf-8") as written:
            self.assertIn("a record the file has to carry", written.read())

    def test_a_directory_that_does_not_exist_fails_at_the_call(self):
        """Opening eagerly is what makes a bad path a caller's error, not a lost record."""

        missing = self.path(os.path.join("absent", "nested.log"))

        with self.assertRaises(OSError) as raised:
            self.logger.log_to_file(missing)

        self.assertNotIsInstance(raised.exception, ModbusBaseError)


if __name__ == "__main__":
    unittest.main()
