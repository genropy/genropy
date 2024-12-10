# pragma: no cover

from enum import Enum, auto

class AdapterCapabilities(Enum):
    MIGRATIONS = auto()
    VECTOR = auto()
    SCHEMAS = auto()

