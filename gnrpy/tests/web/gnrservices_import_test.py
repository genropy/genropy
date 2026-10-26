"""Startup imports must not need optional dependencies.

ServiceHandler imports every module in gnr/lib/services when a site starts,
so a module there that hard-imports an optional extra (genro_storage, ...)
breaks every site that does not install it. The CI job running on the base
install (no extras) runs this file to catch the next such import.
"""

import os

import pytest

import gnr.lib.services as services_pkg
from gnr.core.gnrlang import gnrImport

SERVICES_ROOT = os.path.dirname(services_pkg.__file__)
SERVICE_MODULES = sorted(
    name for name, ext in map(os.path.splitext, os.listdir(SERVICES_ROOT))
    if ext.lower() == '.py' and name != '__init__')


@pytest.mark.parametrize('service_type', SERVICE_MODULES)
def test_service_module_imports(service_type):
    # same call ServiceHandler.__init__ makes for each module of the folder
    module = gnrImport(os.path.join(SERVICES_ROOT, f'{service_type}.py'))
    assert module is not None


def test_storage_handler_imports():
    # the site imports it at startup; genro-storage stays optional there too
    from gnr.web.gnrwsgisite_proxy import gnrstoragehandler
    assert hasattr(gnrstoragehandler, 'GenroStorageHandler')
