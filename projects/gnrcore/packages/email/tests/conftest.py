import os
import sys


_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *['..'] * 5))
_GNRPY_DIR = os.path.join(_REPO_ROOT, 'gnrpy')

for _path in (os.path.join(_GNRPY_DIR, 'tests'), _GNRPY_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)
