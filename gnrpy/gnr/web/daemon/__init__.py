import importlib                                                                                                                      
import importlib.metadata                                       
import sys

_eps = list(importlib.metadata.entry_points(group='gnr.web', name='daemon'))
if _eps:
    _mod = importlib.import_module(_eps[0].value)
    _mod.__name__ = __name__
    sys.modules[__name__] = _mod
