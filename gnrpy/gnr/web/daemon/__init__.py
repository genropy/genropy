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

    *provider* is matched against both the entry-point value (the dotted
    module path) and the name of the distribution declaring it. Raise
    ``ImportError`` when nothing matches: an explicitly requested provider
    that is not installed is a configuration error, not a reason to silently
    fall back to the classic daemon. When more than one entry point matches,
    warn and pick the first one instead of choosing silently.
    """
    matching = [ep for ep in eps
                if provider in (ep.value, getattr(ep.dist, 'name', None))]
    if not matching:
        raise ImportError(
            f'{DAEMON_PROVIDER_ENV}={provider!r}: no '
            f'{DAEMON_ENTRY_POINT_GROUP}:{DAEMON_ENTRY_POINT_NAME} '
            'entry point matches')
    if len(matching) > 1:
        logger.warning('%s=%r matches %d %s:%s entry points (%s): using %r',
                       DAEMON_PROVIDER_ENV, provider, len(matching),
                       DAEMON_ENTRY_POINT_GROUP, DAEMON_ENTRY_POINT_NAME,
                       ', '.join(ep.value for ep in matching),
                       matching[0].value)
    return matching[0]


_provider = os.environ.get(DAEMON_PROVIDER_ENV)
if _provider:
    _ep = _resolve_provider(_provider, importlib.metadata.entry_points(
        group=DAEMON_ENTRY_POINT_GROUP, name=DAEMON_ENTRY_POINT_NAME))
    _mod = importlib.import_module(_ep.value)
    _mod.__name__ = __name__
    sys.modules[__name__] = _mod
