# encoding: utf-8
from __future__ import print_function
from __future__ import unicode_literals

import logging
import os
import sys


class Logger(logging.Logger):
    """Logger that writes to stdout and, optionally, to a file.

    Handlers are attached to this logger only. A library must not reconfigure
    logging for the host application, so nothing here touches the root logger.
    """

    def __init__(self, *args, **kwargs):
        super(Logger, self).__init__(*args, **kwargs)

        self.log_format = "%(asctime)s %(levelname)-8s - %(name)s: %(message)s"
        self.addHandler(self.console_handler())

    def console_handler(self):
        # No encoding is set here: an entry point sets its own, a library takes
        # what it is handed. See PLAYBOOK, entry-point output encoding.
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.INFO)
        stdout_handler.setFormatter(logging.Formatter(str(self.log_format)))

        return stdout_handler

    def file_handler(self, filename=None):
        """Build a file handler, defaulting to the entry point's name.

        The name is derived by appending to the extension-stripped path, not by
        substituting the extension: str.replace with an empty search string
        inserts between every character, so an entry point without an extension
        ('server', or '-c' under python -c) produced names such as
        '.logs.loge.logr.logv.loge.logr.log'.
        """

        if filename is None:
            f_name, _ = os.path.splitext(sys.argv[0])
            filename = f_name + str(".log")

        file_handler = logging.FileHandler(filename=filename, mode=str("a"))
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(str(self.log_format)))

        return file_handler

    def log_to_file(self, filename=None):
        """Attach a file handler. Opt-in: constructing a Logger writes no file."""

        handler = self.file_handler(filename)
        self.addHandler(handler)

        return handler
