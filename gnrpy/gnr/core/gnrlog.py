import sys
import logging
import importlib
from collections import defaultdict

from gnr.core.gnrconfig import getGnrConfig


def _load_handler(implementation_class):
    s = implementation_class.split(".")
    class_name = s[-1]
    module_pathname = ".".join(s[:-1])
    m = importlib.import_module(module_pathname)
    return getattr(m, class_name)

def init_logging_system(conf_bag=None):
    """
    Load the logging infrastructure configuration from a siteconfig configuration, and
    eventually override it using a custom conf_bag, if given. This function
    can be invoked also at runtime, to apply custom configurations on the fly.

    Here is a sample configuration to explain the capabilities:

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
    root_logger = logging.getLogger()
    # load the configuration
    config = getGnrConfig()
    logging_conf = config['gnr.siteconfig.default_xml'].get("logging")
    if not logging_conf and not conf_bag:
        # no configuration at all, use a classic default configuration
        # with logging on stdout
        root_logger.addHandler(_load_handler("gnr.core.loghandlers.gnrcolour.GnrColourStreamHandler")(stream=sys.stdout))
        root_logger.setLevel(logging.WARNING)
        return root_logger

    if logging_conf:
        _load_logging_configuration(logging_conf)
    if conf_bag:
        _load_logging_configuration(conf_bag.get("logging"))

    # configuration completed
    root_logger.info("Logging infrastrucure loaded")
    return root_logger


def _load_logging_configuration(logging_conf):
    """
    Apply the logging configuration starting from Bag coming from siteconfig
    or rather a custom one, which the user can place wherever he wants as long
    as it's a Bag object.
    """
    
    # load handler config
    handlers = dict()
    for handler in logging_conf.get("handlers", []):
        if "impl" not in handler.attr:
            raise Exception(f"Logging handler {handler.label} is missing impl detail")
        handler_impl = handler.attr.pop("impl")
        try:
            handlers[handler.label] = (_load_handler(handler_impl), handler.attr)
        except ValueError as e:
            raise
            print(f"Logging handler '{handler.label}' with implementation '{handler_impl}' cannot be loaded", file=sys.stderr)

    # load loggers config
    loggers = defaultdict(list)
    for logger in logging_conf.get("loggers", []):
        if logger.label.strip():
            loggers[logger.label].append(logger.attr)

    for logger, conf_handlers in loggers.items():
        if logger == 'gnr':
            l = logging.getLogger()
        else:
            l = logging.getLogger(f"gnr.{logger}")
            
        l.handlers = []
        for handler in conf_handlers:
            handler_key = handler.get("handler")
            handler_level = handler.get("level")
            new_handler = handlers.get(handler_key)[0](**handlers.get(handler_key)[1])
            new_handler.setLevel(handler_level)
            l.addHandler(new_handler)
                         

def set_gnr_log_global_level(level):
    """
    Set the new logging level for all gnr* loggers
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for k, v in root_logger.manager.loggerDict.items():
        if not k.startswith("gnr"):
            continue 
        try:
            v.setLevel(level)
        except AttributeError:
            # ignore PlaceHolder loggers            
            pass

