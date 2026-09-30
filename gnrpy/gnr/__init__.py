import sys
import warnings
import logging

from gnr.core import gnrlog

VERSION = "26.09.29"

gnrlog.init_logging_system()
logger = logging.getLogger("gnr")

if sys.version_info < (3, 12):
    # ensure visibility of the warning, promoting temporarily
    # users won't be able to filter this out.
    warnings.simplefilter("always", FutureWarning)
    warnings.warn(
        "Support for Python versions lower than 3.12 will be dropped in future 2027Q1 release.",
        FutureWarning,
        stacklevel=2,
    )
    warnings.simplefilter("default", FutureWarning)

if sys.version_info < (3, 11):
    raise DeprecationWarning(f"Python < 3.11 is not supported anymore")
