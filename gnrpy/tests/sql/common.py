import os.path
from testing.postgresql import Postgresql

from gnr.core.gnrbag import Bag

def setup_module(module):
    base_path = os.path.join(os.path.dirname(__file__), "data")
    module.CONFIG = Bag(os.path.join(base_path, 'configTest.xml'))
    module.SAMPLE_XMLSTRUCT = os.path.join(base_path, 'dbstructure_base.xml')
    module.SAMPLE_XMLDATA = os.path.join(base_path, 'dbdata_base.xml')
    module.SAMPLE_XMLSTRUCT_FINAL = os.path.join(base_path, 'dbstructure_final.xml')

    module.pg_instance = Postgresql()
    module.pg_conf = module.pg_instance.dsn()
    
def teardown_module(module):
    module.pg_instance.stop()

__all__ = ['setup_module', 'teardown_module']
    
