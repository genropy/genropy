import sys
import logging
import platform
import importlib
from collections import defaultdict

from gnr.core.gnrconfig import getGnrConfig

ESC = '\033['

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = list(range(8))

RESET_SEQ = f"{ESC}0m"
COLOR_SEQ = f"{ESC}1;%dm"
BOLD_SEQ = f"{ESC}1m"

COLORS = {
    'WARNING': YELLOW,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': YELLOW,
    'ERROR': RED
}

root_logger = None

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

    Sample from siteconfig configuration:
    
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
	    <root handler="mainlogfile" level="ERROR"/>
	    <sql handler="pgremote" level="INFO" filter="monitordude"/>
	    <app handler="tmpfile" level="DEBUG"/>
	    <web handler="pglocal" level="DEBUG"/>
	  </loggers>
	  
	</logging>
    
    """
    global root_logger
    root_logger = logging.getLogger()
    # load the configuration
    config = getGnrConfig()
    logging_conf = config['gnr.siteconfig.default_xml'].get("logging")
    if not logging_conf:
        # use a classic default configuration, log to stdout
        root_logger.addHandler(logging.StreamHandler(sys.stdout))
        logging.basicConfig(level=logging.WARNING)

    # load handler config
    handlers = dict()
    for handler in logging_conf.get("handlers", []):
        if "impl" not in handler.attr:
            raise Exception(f"Logging handler {handler.label} is missing impl detail")
        handler_impl = handler.attr.pop("impl")
        handlers[handler.label] = (_load_handler(handler_impl), handler.attr)
    
    # load loggers config
    loggers = defaultdict(list)
    for logger in logging_conf.get("loggers", []):
        loggers[logger.label].append(logger.attr)

    for logger, conf_handlers in loggers.items():
        if logger == 'root':
            l = root_logger
        else:
            l = logging.getLogger(f"gnr.{logger}")
        l.handlers = []
        for handler in conf_handlers:
            handler_key = handler.get("handler")
            handler_level = handler.get("level")
            new_handler = handlers.get(handler_key)[0](**handlers.get(handler_key)[1])
            new_handler.setLevel(handler_level)
            l.addHandler(new_handler)
                         
    # configuration completed
    root_logger.info("Logging infrastrucure loaded")
    return root_logger


def formatter_message(message, use_color=True):
    """Change the format message. Return the message with the new format
    
    :param message: the message to be changed
    :param use_color: boolean. If ``True``, add color to the message"""
    if use_color and platform.system() in ['Linux', 'Darwin']:
        message = message.replace("$RESET", RESET_SEQ).replace("$BOLD", BOLD_SEQ)
    else:
        message = message.replace("$RESET", "").replace("$BOLD", "")
    return message
    

class ColoredFormatter(logging.Formatter):
    """A formatter for the python :mod:`logging` module that colors the log messages depending on their severity"""
    
    def __init__(self, fmt, use_color=True):
        logging.Formatter.__init__(self, fmt)
        self.use_color = use_color
        
    def format(self, record):
        """TODO
        
        :param record: TODO"""
        levelname = record.levelname
        if self.use_color and levelname in COLORS:
            levelname_color = COLOR_SEQ % (30 + COLORS[levelname]) + levelname + RESET_SEQ
            record.levelname = levelname_color
        return logging.Formatter.format(self, record)
        
FORMAT = "[$BOLD%(name)-20s$RESET][%(levelname)-18s]  %(message)s ($BOLD%(filename)s$RESET:%(lineno)d)"
COLOR_FORMAT = formatter_message(FORMAT, True)


# db_settings = dict(
#     dbname="log",
#     user="postgres",
#     password="",
#     host="localhost"
#     )
#root_logger.addHandler(PostgresLogHandler(db_settings))



def enable_colored_logging(stream=sys.stderr, level=None, reset_handlers=False):
    """Enable colored logging
    
    :param stream: TODO
    :param level: TODO"""
    global root_logger
    if not root_logger:
        root_logger = logging.getLogger()
        if reset_handlers:
            root_logger.handlers = []
        if len(root_logger.handlers) == 0:
            hdlr = logging.StreamHandler(stream)
            if hasattr(stream, 'isatty') and stream.isatty():
                hdlr.setFormatter(ColoredFormatter(COLOR_FORMAT))
            root_logger.addHandler(hdlr)
    if level is not None:
        root_logger.setLevel(level)

def log_styles():
    return dict(
        color_blue = f"{ESC}94m" if platform.system() in ['Linux', 'Darwin'] else '',
        color_yellow = f"{ESC}33m" if platform.system() in ['Linux', 'Darwin'] else '',
        style_underlined = f"{ESC}4m" if platform.system() in ['Linux', 'Darwin'] else '',
        nostyle = f"{ESC}0m" if platform.system() in ['Linux', 'Darwin'] else '',
        )
