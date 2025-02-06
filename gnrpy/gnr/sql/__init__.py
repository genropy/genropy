# pragma: no cover

import os.path
import glob
import logging
from enum import Enum, auto
from collections import defaultdict

from gnr.core.gnrlog import AuditLogger
from gnr.core.gnrlang import importModule

logger = logging.getLogger("gnr.sql")

class AdapterCapabilities(Enum):
    MIGRATIONS = auto()
    VECTOR = auto()
    SCHEMAS = auto()


# static list of all available db implementations adapters
AVAILABLE_DB_IMPLEMENTATIONS = [os.path.basename(x.replace(".py","").replace("gnr", ""))
                                for x in glob.glob(os.path.join(os.path.dirname(__file__), "adapters/gnr*py"))]
    
ADAPTERS_BY_CAPABILITY = defaultdict(list)

for implementation in AVAILABLE_DB_IMPLEMENTATIONS:
    try:
        adapter_module = importModule(f'gnr.sql.adapters.gnr{implementation}')
        for capability in adapter_module.SqlDbAdapter.CAPABILITIES:
            ADAPTERS_BY_CAPABILITY[capability.name].append(implementation)
    except:
        # the adapter can't be used, since dependencies are missing
        pass

class SqlAuditLogger(AuditLogger):
    base_logger = "gnr.audit.sql"
    method_groups= {
        "insert": "modify",
        "update": "modify",
        "delete": "modify",
        "alter": "modify",
        "select": "read",
    }
    
sqlauditlogger = SqlAuditLogger()
