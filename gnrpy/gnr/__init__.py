import sys
import warnings
import logging

from gnr.core import gnrlog

VERSION = "25.09.17"

gnrlog.init_logging_system()
logger = logging.getLogger("gnr")

if sys.version_info < (3, 10):
    # ensure visibility of the warning, promoting temporarily
    # users won't be able to filter this out.
    warnings.simplefilter("always", FutureWarning)
    warnings.warn(
        "Support for Python versions earlier than 3.10 will be dropped in future 2026Q1 release.",
        FutureWarning,
        stacklevel=2,
    )
    warnings.simplefilter("default", FutureWarning)

