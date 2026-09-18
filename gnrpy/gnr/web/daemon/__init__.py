"""Daemon package, optionally overridden by an alternative provider.

An installed package can declare a ``gnr.web:daemon`` entry point to replace
this whole namespace (``.handler``, ``.siteregister``, ``.processes``, ...).
The override is *not* automatic: it happens only when the
``GNR_DAEMON_PROVIDER`` environment variable names the provider, so the
classic stack and an alternative provider can live in the same environment
and be chosen per process instead of per virtualenv.

With the variable unset this module is a plain package: no entry-point scan,
no ``sys.modules`` surgery.
"""
import importlib
import importlib.metadata
import os
import sys

from gnr.web import logger

DAEMON_PROVIDER_ENV = 'GNR_DAEMON_PROVIDER'
DAEMON_ENTRY_POINT_GROUP = 'gnr.web'
DAEMON_ENTRY_POINT_NAME = 'daemon'


def _resolve_provider(provider, eps):
    """Return the ``gnr.web:daemon`` entry point requested by *provider*.

    *provider* is matched against both the entry-point module and the name of
    the distribution declaring it. The module is read from ``ep.module``
    rather than ``ep.value``: the entry-point spec allows ``module:attr``,
    which ``ep.value`` carries verbatim and no importable name ever equals.

    Anything other than exactly one match raises ``ImportError``. An
    explicitly requested provider is a configuration statement, so neither a
    missing one nor an ambiguous one may degrade into running a daemon the
    caller did not ask for.
    """
    matching = [ep for ep in eps
                if provider in (ep.module, getattr(ep.dist, 'name', None))]
    if len(matching) != 1:
        installed = ', '.join(sorted(
            f'{ep.module} ({getattr(ep.dist, "name", "unknown distribution")})'
            for ep in eps)) or 'none'
        raise ImportError(
            f'{DAEMON_PROVIDER_ENV}={provider!r} matches {len(matching)} '
            f'{DAEMON_ENTRY_POINT_GROUP}:{DAEMON_ENTRY_POINT_NAME} entry '
            f'points; installed: {installed}')
    logger.info('%s=%r resolved to %s', DAEMON_PROVIDER_ENV, provider,
                matching[0].module)
    return matching[0]


_provider = os.environ.get(DAEMON_PROVIDER_ENV)
if _provider:
    _ep = _resolve_provider(_provider, importlib.metadata.entry_points(
        group=DAEMON_ENTRY_POINT_GROUP, name=DAEMON_ENTRY_POINT_NAME))
    _mod = importlib.import_module(_ep.module)
    _mod.__name__ = __name__
    sys.modules[__name__] = _mod
