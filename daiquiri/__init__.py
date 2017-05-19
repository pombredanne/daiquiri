#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import logging
import logging.config
import logging.handlers
import sys
import traceback
import weakref

from daiquiri import handlers
from daiquiri import output


class KeywordArgumentAdapter(logging.LoggerAdapter):
    """Logger adapter to add keyword arguments to log record's extra data

    Keywords passed to the log call are added to the "extra"
    dictionary passed to the underlying logger so they are emitted
    with the log message and available to the format string.

    Special keywords:

    extra
      An existing dictionary of extra values to be passed to the
      logger. If present, the dictionary is copied and extended.

    """

    def process(self, msg, kwargs):
        # Make a new extra dictionary combining the values we were
        # given when we were constructed and anything from kwargs.
        extra = self.extra.copy()
        if 'extra' in kwargs:
            extra.update(kwargs.pop('extra'))
        # Move any unknown keyword arguments into the extra
        # dictionary.
        for name in list(kwargs.keys()):
            if name == 'exc_info':
                continue
            extra[name] = kwargs.pop(name)
        extra['_daiquiri_extra'] = extra
        kwargs['extra'] = extra
        return msg, kwargs


_LOGGERS = weakref.WeakValueDictionary()


def getLogger(name=None, **kwargs):
    """Build a logger with the given name.

    :param name: The name for the logger. This is usually the module
                 name, ``__name__``.
    :type name: string
    """
    if name not in _LOGGERS:
        # NOTE(jd) Keep using the `adapter' variable here because so it's not
        # collected by Python since _LOGGERS contains only a weakref
        adapter = KeywordArgumentAdapter(logging.getLogger(name), kwargs)
        _LOGGERS[name] = adapter
    return _LOGGERS[name]


def setup(level=logging.INFO, outputs=[output.STDERR], binary=None):
    """Setup Python logging.

    This will setup basic handlers for Python logging.

    :param level: Root log level.
    :param outputs: Iterable of outputs to log to.
    :param binary: The name of the program. Auto-detected if not set.
    """
    # Sometimes logging occurs before logging is ready
    # To avoid "No handlers could be found," temporarily log to sys.stderr.
    root_logger = logging.getLogger(None)
    if not root_logger.handlers:
        root_logger.addHandler(logging.StreamHandler())

    binary = binary or handlers._get_binary_name()

    def logging_excepthook(exc_type, value, tb):
        logging.getLogger(binary).critical(
            "".join(traceback.format_exception_only(exc_type, value)))

    sys.excepthook = logging_excepthook

    # Remove all handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Add configured handlers
    for o in outputs:
        o.add_to_logger(root_logger)

    root_logger.setLevel(level)