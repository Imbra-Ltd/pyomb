"""A logger writing to stdout, which attaches a file handler on request."""

# The handler annotations below subscript logging.StreamHandler, which only
# became subscriptable at runtime in 3.11; this defers them to strings.
from __future__ import annotations

import logging
import os
import sys
from typing import TextIO


class Logger(logging.Logger):
    """Logger that writes to stdout and, optionally, to a file.

    Handlers are attached to this logger only. A library must not reconfigure
    logging for the host application, so nothing here touches the root logger.
    """

    def __init__(self, name: str, level: int | str = logging.NOTSET) -> None:
        """Set the format every handler uses and attach the stdout handler.

        Args:
            name : Name this logger is registered and reported under
            level : Threshold below which a record is discarded
        """
        super().__init__(name, level)

        self.log_format = "%(asctime)s %(levelname)-8s - %(name)s: %(message)s"
        self.addHandler(self.console_handler())

    def console_handler(self) -> logging.StreamHandler[TextIO]:
        """Build the stdout handler every Logger attaches on construction.

        Returns:
            logging.StreamHandler : The handler, admitting INFO and above
        """
        # No encoding is set here: an entry point sets its own, a library takes
        # what it is handed. See PLAYBOOK, entry-point output encoding.
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.INFO)
        stdout_handler.setFormatter(logging.Formatter(str(self.log_format)))

        return stdout_handler

    def file_handler(self, filename: str | None = None) -> logging.FileHandler:
        """Build a file handler, defaulting to the entry point's name.

        The name is derived by appending to the extension-stripped path, not by
        substituting the extension: str.replace with an empty search string
        inserts between every character, so an entry point without an extension
        ('server', or '-c' under python -c) produced names such as
        '.logs.loge.logr.logv.loge.logr.log'.
        """
        if filename is None:
            f_name, _ = os.path.splitext(sys.argv[0])
            filename = f_name + ".log"

        file_handler = logging.FileHandler(filename=filename, mode="a")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(str(self.log_format)))

        return file_handler

    def log_to_file(self, filename: str | None = None) -> logging.FileHandler:
        """Attach a file handler. Opt-in: constructing a Logger writes no file."""
        handler = self.file_handler(filename)
        self.addHandler(handler)

        return handler
