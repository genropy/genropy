import os
import sys
local_dir = os.path.dirname(__file__)
sys.path.append(os.path.join(local_dir, ".."))
from core.common import BaseGnrTest


class BaseGnrAppTest(BaseGnrTest):
    pass
