import os
import threading
import time

import pytest

from gnr.core.gnrlang import GnrException
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


class FakeSite(object):
    def __init__(self, resources_dirs):
        self.resources_dirs = resources_dirs
        self.resource_loader = FakeResourceLoader()


@pytest.fixture
def service_type(tmp_path):
    implementations_dir = tmp_path / 'services' / 'dummytype'
    implementations_dir.mkdir(parents=True)
    for name in ('alpha', 'beta'):
        (implementations_dir / ('%s.py' % name)).write_text(SERVICE_MODULE)
    (implementations_dir / 'broken.py').write_text('import _no_such_module_gnrservices_test\n')
    (implementations_dir / 'noclass.py').write_text('X = 1\n')
    (implementations_dir / 'exploding.py').write_text('raise ValueError("boom at import")\n')
    site = FakeSite([str(tmp_path)])
    return BaseServiceType(site=site, service_type='dummytype')


@pytest.fixture
def single_service_type(tmp_path):
    """A service type with exactly one working implementation."""
    implementations_dir = tmp_path / 'services' / 'lonelytype'
    implementations_dir.mkdir(parents=True)
    (implementations_dir / 'only.py').write_text(SERVICE_MODULE)
    return BaseServiceType(site=FakeSite([str(tmp_path)]), service_type='lonelytype')


def test_implementations_registry(service_type):
    implementations = service_type.implementations
    assert set(implementations) == {'alpha', 'beta'}
    assert all(callable(f) for f in implementations.values())


def test_broken_implementation_does_not_take_down_its_siblings(service_type):
    """exploding.py raises a ValueError, not an ImportError, at import time."""
    assert set(service_type.implementations) == {'alpha', 'beta'}
    assert set(service_type._implementation_failures) == {'broken', 'noclass', 'exploding'}


def test_get_implementations_compat(service_type):
    implementations, defaultImplementation = service_type.getImplementations()
    assert implementations is service_type.implementations
    assert defaultImplementation == service_type.defaultImplementation


def test_get_service_factory_resolves_a_named_implementation(service_type):
    assert service_type.getServiceFactory('alpha') is service_type.implementations['alpha']


def test_get_service_factory_never_substitutes_a_named_implementation(service_type):
    """A named implementation resolves or fails: it is never replaced by another one."""
    assert service_type.getServiceFactory('missing') is None
    assert service_type.getServiceFactory('broken') is None
    assert service_type.getServiceFactory('noclass') is None


def test_get_service_factory_without_a_name_needs_a_declared_default(service_type):
    """Two implementations and no defaultImplementation: nothing is picked."""
    assert service_type.getServiceFactory() is None
    service_type.defaultImplementation = 'beta'
    assert service_type.getServiceFactory() is service_type.implementations['beta']


def test_get_service_factory_without_a_name_takes_the_only_one(single_service_type):
    assert single_service_type.getServiceFactory() is single_service_type.implementations['only']


def test_add_service_names_the_reason_a_named_implementation_failed(service_type):
    with pytest.raises(GnrException) as excinfo:
        service_type.addService('svc', implementation='broken')
    message = str(excinfo.value)
    assert 'broken' in message
    assert '_no_such_module_gnrservices_test' in message
    assert isinstance(excinfo.value.__cause__, ImportError)


def test_add_service_reports_an_unknown_implementation(service_type):
    with pytest.raises(GnrException, match='missing'):
        service_type.addService('svc', implementation='missing')


def test_add_service_reports_a_missing_default(service_type):
    """A configuration naming no implementation, on a type with more than one."""
    with pytest.raises(GnrException, match='defaultImplementation'):
        service_type.addService('svc', foo='bar')


def test_add_service_uses_the_declared_default(service_type):
    service_type.defaultImplementation = 'beta'
    service = service_type.addService('svc', foo='bar')
    assert service is not None
    assert type(service) is service_type.implementations['beta']


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
