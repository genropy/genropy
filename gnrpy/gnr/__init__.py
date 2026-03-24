import sys
import logging

from gnr.core import gnrlog

VERSION = "26.03.24.1"

gnrlog.init_logging_system()
logger = logging.getLogger("gnr")

if sys.version_info < (3, 11):
    raise DeprecationWarning(f"Python < 3.11 is not supported anymore")
