"""gnrlog — Logging infrastructure for Genro applications.

This module provides a comprehensive logging system for Genro, including:
- Configuration loading from siteconfig XML
- Dynamic runtime log level adjustment
- Audit logging with specialized loggers for tracking user actions
- Integration with various logging handlers (stdout, file, postgres, etc.)

The logging system is initialized at import time via ``init_logging_system()``
and can be reconfigured at runtime using ``apply_dynamic_conf()``.

Example siteconfig.xml logging section::

    <logging>
        <handlers>
            <console impl="gnr.core.loghandlers.gnrcolour.GnrColourStreamHandler"/>
            <mainlog impl="logging.FileHandler" filename="/var/log/mygenro.log"/>
        </handlers>
        <loggers>
            <gnr handler="mainlog" level="ERROR"/>
            <sql handler="console" level="INFO"/>
        </loggers>
    </logging>
"""

from __future__ import annotations

import importlib
import inspect
import logging
import logging.handlers
import os
import sys
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from gnr.core.gnrconfig import getGnrConfig

if TYPE_CHECKING:
    from gnr.core.gnrbag import Bag

# Suppress werkzeug noise (HTTP request logs)
werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.setLevel(logging.WARNING)

LOGGING_LEVELS: dict[str, int] = {
    "notset": logging.NOTSET,
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "warn": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}
"""Mapping of level names to logging constants."""

DEFAULT_LOG_HANDLER_CLS: str = "gnr.core.loghandlers.gnrcolour.GnrColourStreamHandler"
"""Default handler class used when no configuration is provided."""


def _load_handler(implementation_class: str) -> type[logging.Handler]:
    """Load a logging handler class from its fully qualified name.

    Args:
        implementation_class: Fully qualified class name
            (e.g., 'logging.StreamHandler').

    Returns:
        The handler class (not an instance).

    Raises:
        ImportError: If the module cannot be imported.
        AttributeError: If the class does not exist in the module.
    """
    parts = implementation_class.split(".")
    class_name = parts[-1]
    module_pathname = ".".join(parts[:-1])
    module = importlib.import_module(module_pathname)
    return getattr(module, class_name)


def init_logging_system(conf_bag: Bag | None = None) -> logging.Logger:
    """Initialize the Genro logging infrastructure.

    Loads logging configuration from siteconfig and optionally overrides
    it with a custom conf_bag. This function can be called at runtime to
    apply new configurations on the fly.

    If no configuration is found, a default configuration is applied with
    colored output to stdout and WARNING level.

    Sample configuration::

        <logging>
            <handlers>
                <pglocal impl="gnr.core.loghandlers.postgres.GnrPostgresqlLoggingHandler"
                         db="log" user="postgres" host="localhost"/>
                <gnrdb impl="gnr.core.loghandlers.gnrapp.GnrAppLoggingHandler"
                       gnrapp_name="sandbox" table_name="sys.log"/>
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

    Args:
        conf_bag: Optional Bag containing logging configuration that
            overrides siteconfig settings.

    Returns:
        The root 'gnr' logger instance.
    """
    root_logger = logging.getLogger("gnr")

    # Load site configuration
    try:
        config = getGnrConfig()
        logging_conf = config["gnr.siteconfig.default_xml"].get("logging")
    except Exception:  # REVIEW:SMELL — bare except catches too much
        logging_conf = None

    env_log_level = os.environ.get("GNR_LOGLEVEL", None)

    if not logging_conf and not conf_bag:
        # No configuration at all, use default with stdout
        root_logger.handlers = []
        root_logger.addHandler(
            _load_handler(DEFAULT_LOG_HANDLER_CLS)(stream=sys.stdout)
        )
        root_logger.setLevel(LOGGING_LEVELS.get(env_log_level, logging.WARNING))

        # Configure separate auditor logger
        auditor = logging.getLogger("gnraudit")
        # Do not propagate messages from audit to root
        auditor.propagate = False
        auditor.handlers = []
        auditor_default_cls = "gnr.core.loghandlers.auditor.GnrAuditorHandler"
        auditor.addHandler(_load_handler(auditor_default_cls)(stream=sys.stdout))

        return root_logger

    if logging_conf:
        _load_logging_configuration(logging_conf)
    if conf_bag:
        _load_logging_configuration(conf_bag.get("logging"))

    root_logger.info("Logging infrastructure loaded")

    # Set global level if defined in environment
    if env_log_level is not None:
        set_gnr_log_global_level(LOGGING_LEVELS.get(env_log_level))

    return root_logger


def get_all_handlers() -> list[
    tuple[str, str]
]:  # REVIEW:DEAD — zero callers found in codebase
    """Get all available logging handler classes from the stdlib.

    Returns:
        List of tuples (fully_qualified_name, class_name) for each
        handler class in logging.handlers.
    """
    stdlib_handlers = [
        (f"{obj.__module__}.{obj.__qualname__}", obj.__qualname__)
        for name, obj in inspect.getmembers(logging.handlers, inspect.isclass)
        if issubclass(obj, logging.Handler) and obj is not logging.Handler
    ]
    return stdlib_handlers


def apply_dynamic_conf(conf_bag: Bag) -> None:
    """Apply logging configuration dynamically from a Bag.

    Used by the UI to alter logging configuration state at runtime.

    Args:
        conf_bag: Bag where each node has 'path' and 'level' attributes.
    """

    def apply_node(node: Any) -> None:
        clogger = logging.getLogger(node.getAttr("path"))
        clogger.setLevel(node.getAttr("level"))

    conf_bag.walk(apply_node)


def _load_logging_configuration(logging_conf: Bag) -> None:
    """Apply logging configuration from a Bag structure.

    Internal function that parses handlers and loggers sections from
    a Bag (typically from siteconfig XML) and configures the logging
    infrastructure accordingly.

    Args:
        logging_conf: Bag containing 'handlers' and 'loggers' sections.

    Raises:
        ValueError: If a handler is missing the 'impl' attribute.
    """
    # Load handler configuration
    handlers: dict[str, tuple[type[logging.Handler], dict[str, Any]]] = {}
    for handler in logging_conf.get("handlers", []):
        if "impl" not in handler.attr:
            raise ValueError(f"Logging handler {handler.label} is missing impl detail")
        handler_impl = handler.attr.pop(
            "impl"
        )  # REVIEW:BUG — mutates caller's attr dict
        try:
            handlers[handler.label] = (_load_handler(handler_impl), handler.attr)
        except ValueError as e:
            print(
                f"Logging handler '{handler.label}':'{handler_impl}' cannot be loaded: {e}",
                file=sys.stderr,
            )
            raise

    # Load loggers configuration
    loggers: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for logger in logging_conf.get("loggers", []):
        if logger.label.strip():
            loggers[logger.label].append(logger.attr)

    for logger_name, conf_handlers in loggers.items():
        if logger_name == "gnr":
            clogger = logging.getLogger(
                "gnr"
            )  # REVIEW:SMELL — `l` was assigned but `clogger` used
        else:
            clogger = logging.getLogger(f"gnr.{logger_name}")

        clogger.handlers = []
        for handler in conf_handlers:
            handler_key = handler.get("handler")
            handler_level = handler.get("level")
            handler_cls, handler_kwargs = handlers.get(handler_key)
            new_handler = handler_cls(**handler_kwargs)
            new_handler.setLevel(handler_level)
            clogger.addHandler(new_handler)


def get_gnr_log_configuration(all_loggers: bool = False) -> dict[str, dict[str, Any]]:
    """Get the current logging configuration for all gnr loggers.

    Args:
        all_loggers: If True, include non-gnr loggers as well.

    Returns:
        Dict mapping logger names to their configuration with keys:
        - level: Current logging level name
        - handlers: List of handler class names
        - propagate: Whether messages propagate to parent (optional)
    """

    def make_logger_dict() -> dict[str, Any]:
        return dict(level=logging.NOTSET, handlers=[])

    logger_conf: dict[str, dict[str, Any]] = defaultdict(make_logger_dict)

    root_logger = logging.getLogger()
    logger_conf["root"]["level"] = logging._levelToName[root_logger.level]
    for h in getattr(root_logger, "handlers", []):
        logger_conf["root"]["handlers"].append(h.__class__.__name__)

    for k, v in sorted(root_logger.manager.loggerDict.items()):
        if not all_loggers and not k.startswith("gnr"):
            continue
        logger_level = logging._levelToName.get(getattr(v, "level", 0), "CRITICAL")
        logger_conf[k]["level"] = logger_level
        logger_conf[k]["propagate"] = getattr(v, "propagate", True)
        for h in getattr(v, "handlers", []):
            q = f"{h.__module__}.{h.__class__.__qualname__}"
            logger_conf[k]["handlers"].append(q)

    return logger_conf


def set_gnr_log_global_level(level: int | None) -> None:
    """Set the logging level for all gnr* loggers.

    Args:
        level: Logging level constant (e.g., logging.DEBUG).
            If None, no action is taken.
    """
    if level is None:
        return

    root_logger = logging.getLogger("gnr")
    root_logger.debug("Setting global GNR logger configuration to %s", level)
    root_logger.setLevel(level)

    for k, v in root_logger.manager.loggerDict.items():
        if not k.startswith("gnr."):
            continue
        try:
            v.setLevel(level)
        except AttributeError:
            # Ignore PlaceHolder loggers
            pass


class AuditLoggerFilter(logging.Filter):
    """Filter that adds user information to log records.

    If the log record does not have a 'user' attribute, it is set
    to the value of the USER environment variable or 'NA' if not set.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add user attribute to record if missing.

        Args:
            record: The log record to filter.

        Returns:
            Always True (record is never filtered out).
        """
        if not hasattr(record, "user"):
            record.user = os.environ.get("USER", "NA")
        return True


class AuditLogger:
    """Specialized logger for audit trail purposes.

    Provides dynamic method access for logging different types of
    audit events. Methods are created on-demand based on the
    method_groups mapping.

    Usage::

        audit = AuditLogger()
        audit.user("User %s logged in", username)
        audit.custom_action("Something happened")

    Attributes:
        DEFAULT_LEVEL: Default logging level for audit messages.
        base_logger: Base name for the audit logger hierarchy.
        method_groups: Mapping of method names to their group names.
    """

    DEFAULT_LEVEL: int = logging.DEBUG
    base_logger: str = "gnraudit"
    method_groups: dict[str, str] = {"user": "generic"}

    def __init__(self) -> None:
        """Initialize the AuditLogger with configured sub-loggers."""
        # Ensure base logger exists
        _ = logging.getLogger(self.base_logger)

        self.loggers: dict[str, logging.Logger] = {
            k: self._get_logger(k, v) for k, v in self.method_groups.items()
        }

    def _get_logger(self, name: str, group: str = "unknown") -> logging.Logger:
        """Get or create a logger for the given name and group.

        Args:
            name: The statement/action name.
            group: The group name for categorization.

        Returns:
            Configured logger instance with AuditLoggerFilter.
        """
        log_name = self._get_logger_name(name, group)
        ret_logger = logging.getLogger(log_name)
        ret_logger.addFilter(AuditLoggerFilter())
        return ret_logger

    def _get_logger_name(self, statement: str, group: str) -> str:
        """Build the full logger name from parts.

        Args:
            statement: The action/statement name.
            group: The group name.

        Returns:
            Full logger name like 'gnraudit.group.statement'.
        """
        return f"{self.base_logger}.{group}.{statement}"

    def __getattr__(self, name: str) -> Any:
        """Provide dynamic method access for logging.

        Args:
            name: Method name (converted to lowercase).

        Returns:
            A callable that logs the message with the given statement name.
        """
        name = name.lower()
        if name not in self.method_groups:
            self.loggers[name] = self._get_logger(name)

        def wrapper(*args: Any, **kwargs: Any) -> None:
            return self.log(name, *args, **kwargs)

        return wrapper

    def log(self, statement: str, *args: Any, **kwargs: Any) -> None:
        """Log a message under the given statement.

        Args:
            statement: The statement/action name.
            *args: Positional arguments passed to logger.log().
            **kwargs: Keyword arguments passed to logger.log().
        """
        self.loggers.get(statement).log(self.DEFAULT_LEVEL, *args, **kwargs)
