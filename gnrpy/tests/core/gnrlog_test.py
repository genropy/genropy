import logging
import sys

from gnr.core import gnrlog as gl
from gnr.core.gnrbag import Bag

def test_global_level():
    gl.set_gnr_log_global_level(logging.DEBUG)

    logger = logging.getLogger("gnr")
    assert logger.level == logging.DEBUG
    
def test_configuration():
    configuration = """
    <logging>
      <handlers> 
	<standard impl="gnr.core.loghandlers.gnrcolour.GnrColourStreamHandler"/>
      </handlers> 
      <loggers> 
        <sql handler="standard" level="WARNING"/>
        <app handler="standard" level="DEBUG"/> 
        <web handler="standard" level="INFO"/> 
      </loggers> 
    </logging>
    """
    
    conf_bag = Bag()
    conf_bag.fromXml(source=configuration)
    gl.init_logging_system(conf_bag=conf_bag)

    checks = [
        ("sql", logging.WARNING),
        ("app", logging.DEBUG),
        ("web", logging.INFO)
    ]
    
    for logger, level in checks:
        l = logging.getLogger(f"gnr.{logger}")
        assert l.handlers[0].level == level
