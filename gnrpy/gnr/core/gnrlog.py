import os
import sys
import logging
import logging.handlers
import inspect
import importlib
import traceback
import datetime
import hashlib
import linecache
import json
from collections import defaultdict

from gnr.core.gnrconfig import getGnrConfig
from gnr.core.gnrstructures import GnrStructData
from gnr.core.gnrbag import Bag
from gnr.core.gnrstring import toText
from gnr.utils.gnrmail import sendmail

# other loggers, hardcoded for the moment
werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.setLevel(logging.WARNING)

LOGGING_LEVELS = {
    'notset': logging.NOTSET,
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'warn': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}

DEFAULT_LOG_HANDLER_CLS = "gnr.core.loghandlers.gnrcolour.GnrColourStreamHandler"

def _load_handler(implementation_class):
    s = implementation_class.split(".")
    class_name = s[-1]
    module_pathname = ".".join(s[:-1])
    m = importlib.import_module(module_pathname)
    return getattr(m, class_name)


def init_logging_system(conf_bag=None):
    """
    Load the logging infrastructure configuration from a siteconfig
    configuration, and optionally override it using a custom conf_bag,
    if given. This function can be invoked also at runtime, to apply
    custom configurations on the fly.

    Here is a sample configuration to explain the capabilities:

        <logging>
        <handlers>
            <pglocal
                impl="gnr.core.loghandlers.postgres.GnrPostgresqlLoggingHandler"
                db="log" user="postgres" host="localhost"/>
            <gnrdb impl="gnr.core.loghandlers.gnrapp.GnrAppLoggingHandler"
                 gnrapp_name="sandbox"
                 table_name="sys.log" />
            <tmpfile impl="logging.FileHandler" filename="/tmp/mygenro.log"/>
            <mainlogfile impl="logging.FileHandler"
                        filename="/var/log/mygenro.log"/>
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
    root_logger = logging.getLogger('gnr')
    # load the site configuration
    
    try:
        config = getGnrConfig() 
        logging_conf = config['gnr.siteconfig.default_xml'].get("logging")
    except:
        logging_conf = None

    env_log_level= os.environ.get("GNR_LOGLEVEL", None)
    
    if not logging_conf and not conf_bag:
        # no configuration at all, use a classic default configuration
        # with logging on stdout
        root_logger.handlers = []
        root_logger.addHandler(_load_handler(DEFAULT_LOG_HANDLER_CLS)(stream=sys.stdout))
        root_logger.setLevel(LOGGING_LEVELS.get(env_log_level, logging.WARNING))

        auditor = logging.getLogger("gnraudit")
        # do not propagate messages from the audit to the root
        # we want to keep this separated as default
        auditor.propagate = False
        auditor.handlers = []
        auditor_default_cls = "gnr.core.loghandlers.auditor.GnrAuditorHandler"
        auditor.addHandler(_load_handler(auditor_default_cls)(stream=sys.stdout))

        return root_logger

    if logging_conf:
        _load_logging_configuration(logging_conf)
    if conf_bag:
        _load_logging_configuration(conf_bag.get("logging"))

    # configuration completed
    root_logger.info("Logging infrastrucure loaded")

    # set the global level if defined in environment

    if env_log_level is not None:
        set_gnr_log_global_level(LOGGING_LEVELS.get(env_log_level))
    return root_logger


def get_all_handlers():

    stdlib_handlers = [
        (f"{obj.__module__}.{obj.__qualname__}", obj.__qualname__)
        for name, obj in inspect.getmembers(logging.handlers, inspect.isclass)
        if issubclass(obj, logging.Handler) and obj is not logging.Handler
    ]
    return stdlib_handlers


def apply_dynamic_conf(conf_bag):
    """
    Apply the logging configuration from a Bag used in the UI to alter
    dynamically the logging configuration state
    """

    def p(node):
        clogger = logging.getLogger(node.getAttr("path"))
        clogger.setLevel(node.getAttr('level'))
    conf_bag.walk(p)


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
            raise ValueError(f"Logging handler {handler.label} is missing impl detail")
        handler_impl = handler.attr.pop("impl")
        try:
            handlers[handler.label] = (_load_handler(handler_impl), handler.attr)
        except ValueError as e:
            print(f"Logging handler '{handler.label}':'{handler_impl}' cannot be loaded: {e}",
                  file=sys.stderr)
            raise

    # load loggers config
    loggers = defaultdict(list)
    for logger in logging_conf.get("loggers", []):
        if logger.label.strip():
            loggers[logger.label].append(logger.attr)

    for logger, conf_handlers in loggers.items():
        if logger == 'gnr':
            l = logging.getLogger('gnr')
        else:
            clogger = logging.getLogger(f"gnr.{logger}")

        clogger.handlers = []
        for handler in conf_handlers:
            handler_key = handler.get("handler")
            handler_level = handler.get("level")
            new_handler = handlers.get(handler_key)[0](**handlers.get(handler_key)[1])
            new_handler.setLevel(handler_level)
            clogger.addHandler(new_handler)


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
        logger_level = logging._levelToName.get(getattr(v, "level", 0), "CRITICAL")
        logger_conf[k]['level'] = logger_level
        logger_conf[k]['propagate'] = getattr(v, 'propagate', True)
        for h in getattr(v, "handlers", []):
            q = f"{h.__module__}.{h.__class__.__qualname__}"
            logger_conf[k]['handlers'].append(q)

    return logger_conf


def set_gnr_log_global_level(level):
    """
    Set the new logging level for all gnr* loggers
    """

    root_logger = logging.getLogger('gnr')
    root_logger.debug("Setting global GNR logger configuration to %s", level)
    root_logger.setLevel(level)
    for k, v in root_logger.manager.loggerDict.items():
        if not k.startswith("gnr."):
            continue 
        try:
            v.setLevel(level)
        except AttributeError:
            # ignore PlaceHolder loggers            
            pass

class AuditLoggerFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'user'):
            record.user = os.environ.get("USER", "NA")
        return True


class AuditLogger(object):
    DEFAULT_LEVEL = logging.DEBUG
    base_logger = 'gnraudit'
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
        ret_logger = logging.getLogger(log_name)
        ret_logger.addFilter(AuditLoggerFilter())
        return ret_logger

    def _get_logger_name(self, statement, group):
        return f"{self.base_logger}.{group}.{statement}"

    def __getattr__(self, name):
        name = name.lower()
        if name not in self.method_groups:
            self.loggers[name] = self._get_logger(name)

        def wrapper(*args, **kwargs):
            return self.log(name, *args, **kwargs)
        return wrapper

    def log(self, statement, *args, **kwargs):
        self.loggers.get(statement).log(self.DEFAULT_LEVEL, *args, **kwargs)


def _is_library_frame(filename):
    if filename.startswith('<'):
        return True
    _library_markers = (
        os.sep + 'site-packages' + os.sep,
        os.sep + 'lib' + os.sep + 'python',
        os.sep + 'Lib' + os.sep,
    )
    for marker in _library_markers:
        if marker in filename:
            return True
    return False

def tracebackBag(limit=None, full_stack=False):
    result = Bag()
    if limit is None:
        if hasattr(sys, 'tracebacklimit'):
            limit = sys.tracebacklimit
    n = 0
    hash_cache = {}
    tb = sys.exc_info()[2]
    frames = []
    last_own_idx = 0
    while tb is not None and (limit is None or n < limit):
        tb_bag = Bag()
        f = tb.tb_frame
        lineno = tb.tb_lineno
        co = f.f_code
        filename = co.co_filename
        name = co.co_name
        linecache.checkcache(filename)
        line = linecache.getline(filename, lineno)
        if line: line = line.strip()
        else: line = None
        if filename not in hash_cache:
            try:
                with open(filename, 'rb') as fh:
                    hash_cache[filename] = hashlib.sha256(fh.read()).hexdigest()[:12]
            except Exception:
                hash_cache[filename] = None
        tb_bag['module'] = os.path.basename(os.path.splitext(filename)[0])
        tb_bag['filename'] = filename
        tb_bag['file_hash'] = hash_cache[filename]
        tb_bag['lineno'] = lineno
        tb_bag['name'] = name
        tb_bag['line'] = line
        loc = Bag()
        for k,v in list(f.f_locals.items()):
            try:
                if isinstance(v,GnrStructData):
                    v = '*STRUCTURE*'
                elif isinstance(v,Bag):
                    v = '*BAG*'
                elif isinstance(v,(dict,list,tuple)):

                    json.dumps(v)
                loc[k] = v
            except Exception:
                loc[k] = '*UNSERIALIZABLE* %s' %v.__class__
        tb_bag['locals'] = loc
        label = '%s method %s line %s' % (tb_bag['module'], name, lineno)
        frames.append((label, tb_bag, filename))
        if not _is_library_frame(filename):
            last_own_idx = n
        tb = tb.tb_next
        n = n + 1
    if not full_stack:
        frames = frames[:last_own_idx + 1]
    for label, tb_bag, _filename in frames:
        result[label] = tb_bag
    return Bag(root=result)

def errorTxt():
    el = sys.exc_info()
    tb_text = traceback.format_exc()
    e = el[2]
    while e.tb_next:
        e = e.tb_next

    locals_list = []
    for k, v in list(e.tb_frame.f_locals.items()):
        try:
            strvalue = toText(v)
        except:
            strvalue = 'unicode error'
        locals_list.append('%s: %s' % (k, strvalue))
    return u'%s\n\nLOCALS:\n\n%s' % (tb_text, '\n'.join(locals_list))

def errorLog(proc_name, host=None, from_address='', to_address=None, user=None, password=''):
    gnr_logger = logging.getLogger('gnr')
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S: ')
    title = '%s - Error in %s' % (ts, proc_name)
    gnr_logger.error(title)
    tb_text = errorTxt()
    gnr_logger.error(tb_text.encode('ascii', 'ignore'))

    if (host and to_address):
        try:
            sendmail(host=host,
                     from_address=from_address,
                     to_address=to_address,
                     subject=title,
                     body=tb_text,
                     user=user,
                     password=password
                     )
        except:
            gnr_logger.exception("While sending errorLog email")

    return tb_text
