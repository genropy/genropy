import logging
from gnr.core import gnrlog

VERSION = "24.12.23"
GLOBAL_DEBUG = False

gnrlog.init_logging_system()
logger = logging.getLogger("gnr")

