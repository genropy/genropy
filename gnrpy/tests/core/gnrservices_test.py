import os
import threading
import time

import pytest

from gnr.lib.services import BaseServiceType

SERVICE_MODULE = """
class Service(object):
    def __init__(self, parent=None, **kwargs):
        self.parent = parent
        self.kwargs = kwargs
"""


class FakeResourceLoader(object):
    def getResourceList(self, resourceDirs, path, ext=None, pkg=None):
        result = []
        for d in resourceDirs:
            fpath = os.path.join(d, path)
            if os.path.isdir(fpath):
                result.append(fpath)
        return result


class FakeApp(object):
    packages = {}


class FakeSite(object):
    def __init__(self, resources_dirs):
        self.resources_dirs = resources_dirs
        self.resource_loader = FakeResourceLoader()
        self.gnrapp = FakeApp()


@pytest.fixture
def service_type(tmp_path):
    implementations_dir = tmp_path / 'services' / 'dummytype'
    implementations_dir.mkdir(parents=True)
    for name in ('alpha', 'beta'):
        (implementations_dir / ('%s.py' % name)).write_text(SERVICE_MODULE)
    (implementations_dir / 'broken.py').write_text('import _no_such_module_gnrservices_test\n')
    (implementations_dir / 'noclass.py').write_text('X = 1\n')
    site = FakeSite([str(tmp_path)])
    return BaseServiceType(site=site, service_type='dummytype')


def test_implementations_registry(service_type):
    implementations = service_type.implementations
    assert set(implementations) == {'alpha', 'beta'}
    assert all(callable(f) for f in implementations.values())
    assert service_type.baseImplementation in ('alpha', 'beta')


def test_get_implementations_compat(service_type):
    implementations, baseImplementation = service_type.getImplementations()
    assert implementations is service_type.implementations
    assert baseImplementation == service_type.baseImplementation


def test_get_service_factory(service_type):
    alpha = service_type.getServiceFactory('alpha')
    assert alpha is service_type.implementations['alpha']
    base = service_type.implementations[service_type.baseImplementation]
    assert service_type.getServiceFactory('missing') is base
    assert service_type.getServiceFactory() is base


def test_add_service_creates_instance(service_type):
    service = service_type.addService('one', implementation='alpha', foo='bar')
    assert service.service_name == 'one'
    assert service.service_type == 'dummytype'
    assert service.service_implementation == 'alpha'
    assert service.kwargs == {'foo': 'bar'}
    assert service_type.service_instances['one'] is service


def test_concurrent_first_access_is_atomic(service_type):
    build_calls = []
    original_build = service_type._buildImplementations

    def slow_build():
        build_calls.append(1)
        time.sleep(0.2)
        return original_build()

    service_type._buildImplementations = slow_build
    factories = []
    errors = []

    def worker():
        try:
            factories.append(service_type.getServiceFactory('alpha'))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(build_calls) == 1
    assert len(factories) == 8
    assert all(f is factories[0] and callable(f) for f in factories)


class FakeGlobalStore(object):
    def __init__(self):
        self.getitem_calls = 0

    def getItem(self, key):
        self.getitem_calls += 1
        return None


class FakeRegister(object):
    def __init__(self):
        self.global_store = FakeGlobalStore()

    def globalStore(self, triggered=False):
        return self.global_store


def test_cached_non_db_service_skips_register(service_type):
    service_type.site.register = FakeRegister()
    service = service_type('one', implementation='alpha')
    assert service._config_from_db is False
    # creation path reads the register once
    assert service_type.site.register.global_store.getitem_calls == 1
    # cached non-db service: no further register reads
    assert service_type('one') is service
    assert service_type('one') is service
    assert service_type.site.register.global_store.getitem_calls == 1


def test_cached_db_service_keeps_freshness_check(service_type):
    service_type.site.register = FakeRegister()
    service_type.getServiceConfigurationFromDb = lambda service_name: {'implementation': 'alpha'}
    service = service_type('one')
    assert service._config_from_db is True
    assert service_type('one') is service
    # db-configured service: the register is read on every call
    assert service_type.site.register.global_store.getitem_calls == 2
