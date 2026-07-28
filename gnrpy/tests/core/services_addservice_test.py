"""Regression tests for BaseServiceType.addService factory resolution.

A missing service implementation used to crash with a bare
``TypeError: 'NoneType' object is not callable`` at the factory call site
(``service = service_factory(self.site, **service_conf)``): the same opaque
error a cold-start race on ``site.resources_dirs`` produced in production
(see issue #984). ``addService`` must instead raise a clear ``GnrException``
naming the implementation and the service type.

The harness exercises the real ``BaseServiceType`` and the real
``ResourceLoader.getResourceList`` over the repository's own ``resources/common``
tree — no site instance, no register daemon needed.
"""

import os
from types import SimpleNamespace

import pytest

from gnr.core.gnrlang import GnrException
from gnr.lib.services import BaseServiceType
from gnr.web.gnrwsgisite_proxy.gnrresourceloader import ResourceLoader

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
COMMON_RESOURCES = os.path.join(REPO_ROOT, 'resources', 'common')


def make_site():
    """A minimal site facade: a real ResourceLoader over the repo resources."""
    site = SimpleNamespace(
        site_path=REPO_ROOT,
        site_name='servicetest',
        gnr_config=None,
        debug=False,
        getStatic=lambda name: None,
        default_page=None,
    )
    site.resource_loader = ResourceLoader(site)
    site.resources_dirs = [COMMON_RESOURCES]
    return site


def test_get_service_factory_finds_real_implementation():
    """Positive control: the scan resolves a real implementation from resources/common."""
    handler = BaseServiceType(site=make_site(), service_type='storage')
    factory = handler.getServiceFactory('symbolic')
    assert factory is not None
    assert factory.__name__ in ('Service', 'Main')


def test_add_service_missing_implementation_raises_clear_error():
    """No implementations for the service type: a clear error, not a bare TypeError."""
    handler = BaseServiceType(site=make_site(), service_type='faketype')
    with pytest.raises(GnrException, match='faketype'):
        handler.addService('x', implementation='any')
