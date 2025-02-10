import os
import sys
import logging
import importlib
from collections import defaultdict

from gnr.core.gnrconfig import getGnrConfig

# other loggers, hardcoded for the moment
werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.setLevel(logging.WARNING)


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
	    <pglocal impl="gnr.core.loghandlers.postgres.GnrPostgresqlLoggingHandler"
               db="log" user="postgres" host="localhost"/>
	    <gnrdb impl="gnr.core.loghandlers.gnrapp.GnrAppLoggingHandler" gnrapp_name="sandbox"
    table_name="sys.log" />
	    <tmpfile impl="logging.FileHandler" filename="/tmp/mygenro.log"/>
	    <mainlogfile impl="logging.FileHandler" filename="/var/log/mygenro.log"/>
	  </handlers>
	  
	  <filters>
	    <monitordude impl="user" username="badguy"/>
	  </filters>
	  
	  <loggers>
	    <gnr handler="mainlogfile" level="ERROR"/>
	    <sql handler="gnrdb" level="INFO" filter="monitordude"/>
	    <app handler="tmpfile" level="DEBUG"/>
	    <web handler="pglocal" level="DEBUG"/>
	  </loggers>
	  
	</logging>
    
    """
    root_logger = logging.getLogger()
    # load the site configuration
    try:
        config = getGnrConfig()
        logging_conf = config['gnr.siteconfig.default_xml'].get("logging")
    except Exception as e:
        logging_conf = None
        
    if not logging_conf and not conf_bag:
        # no configuration at all, use a classic default configuration
        # with logging on stdout
        root_logger.handlers = []
        root_logger.addHandler(_load_handler("gnr.core.loghandlers.gnrcolour.GnrColourStreamHandler")(stream=sys.stdout))
        auditor = logging.getLogger("gnr.audit")

        # do not propagate messages from the audit to the root
        # we want to keep this separated as default
        auditor.propagate = False
        auditor.handlers = []
        auditor.addHandler(_load_handler("gnr.core.loghandlers.auditor.GnrAuditorHandler")(stream=sys.stdout))

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
                         
def get_gnr_log_configuration(all_loggers=False):
    def logger():
        return dict(level=logging.NOTSET, handlers=[])
    
    logger_conf = defaultdict(logger)


    root_logger = logging.getLogger()
    logger_conf['root']['level'] = logging._levelToName[root_logger.level]
    for h in getattr(root_logger, "handlers", []):
        logger_conf['root']['handlers'].append(h.__class__.__name__)
    
    for k, v in sorted(root_logger.manager.loggerDict.items()):
        if not all_loggers and not k.startswith("gnr"):
            continue
        logger_level = logging._levelToName[getattr(v, "level", 0)]
        logger_conf[k]['level'] = logger_level
        for h in getattr(v, "handlers", []):
            logger_conf[k]['handlers'].append(h.__class__.__name__)

    return logger_conf

        
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



class AuditLoggerFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'user'):
            record.user = os.environ.get("USER")
        return True
    

class AuditLogger(object):
    DEFAULT_LEVEL = logging.DEBUG
    base_logger = 'gnr.audit'
    method_groups = {
        "user": "generic"
    }
    
    def __init__(self):
        
        _ = logging.getLogger(self.base_logger)
        
        self.loggers = {
            k: self._get_logger(k, v) for k, v in self.method_groups.items()
        }

    def _get_logger(self, name, group="unknown"):
        log_name = self._get_logger_name(name, group)
        l = logging.getLogger(log_name)
        l.addFilter(AuditLoggerFilter())
        return l
              
    def _get_logger_name(self, statement, group):
        return f"{self.base_logger}.{group}.{statement}"
    
    def __getattr__(self, name):
        name = name.lower()
        if not name in self.method_groups:
              self.loggers[name] = self._get_logger(name)

        def wrapper(*args, **kwargs):
            return self.log(name, *args, **kwargs)
        return wrapper

    def log(self, statement, *args, **kwargs):
        self.loggers.get(statement).log(self.DEFAULT_LEVEL, *args, **kwargs)

        

