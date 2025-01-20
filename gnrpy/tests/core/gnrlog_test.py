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
	<pglocal impl="postgresql" db="log" user="postgres" host="localhost"/> 
        <pgremote impl="postgresql" db="log" user="postgres" password="mysecret" host="remote.server.com"/> 
        <tmpfile impl="file" filename="/tmp/mygenro.log"/> 
        <mainlogfile impl="file" filename="/var/log/mygenro.log"/> 
        <elastic impl="elk" host="elasticsearch.server.com" user="elastic" password="mysecret" index="mygenroapp"/> 
      </handlers> 
      <filters> 
        <monitordude impl="user" username="badguy"/> 
      </filters> 
      <loggers> 
        <gnr handler="mainlogfile" level="ERROR"/> 
        <sql handler="pgremote" level="INFO" filter="monitordude"/> 
        <app handler="tmpfile" level="DEBUG"/> 
        <web handler="pglocal" level="DEBUG"/> 
      </loggers> 
    </logging>
    """

    conf_bag = Bag.fromXml(configuration)
    print(conf_bag)
    assert False
