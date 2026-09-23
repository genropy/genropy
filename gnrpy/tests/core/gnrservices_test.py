import os
import threading
import logging
import traceback
import time

import pytest

from gnr.lib.services import BaseServiceType, GnrUnresolvedService
from gnr.core.gnrlang import GnrException

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
    service = service_type.addService('svc', implementation='broken')
    with pytest.raises(GnrException) as excinfo:
        service.send()
    message = str(excinfo.value)
    assert 'broken' in message
    assert '_no_such_module_gnrservices_test' in message
    assert isinstance(excinfo.value.__cause__, ImportError)


def test_add_service_reports_an_unknown_implementation(service_type):
    service = service_type.addService('svc', implementation='missing')
    with pytest.raises(GnrException, match='missing'):
        service.send()


def test_add_service_reports_a_missing_default(service_type):
    """A configuration naming no implementation, on a type with more than one."""
    service = service_type.addService('svc', foo='bar')
    with pytest.raises(GnrException, match='defaultImplementation'):
        service.send()


def test_unresolved_service_does_not_stop_registration(service_type):
    """A configuration that no longer resolves must not take down the site."""
    service = service_type.addService('svc', implementation='missing')
    assert isinstance(service, GnrUnresolvedService)
    assert service_type.service_instances['svc'] is service
    # the name that was asked for is reported, never a substitute
    assert service.service_implementation == 'missing'
    assert service.service_name == 'svc'
    assert service.service_type == 'dummytype'


def test_unresolved_service_raises_on_every_use(service_type):
    service = service_type.addService('svc', implementation='missing')
    with pytest.raises(GnrException, match='no implementation') as first:
        service.anything
    with pytest.raises(GnrException, match='no implementation'):
        service()
    with pytest.raises(GnrException, match='no implementation') as last:
        service.send('a message')
    # a new exception each time, never the recorded one: re-raising one instance
    # appends to the traceback it already carries
    assert first.value is not service.unresolved_reason
    assert last.value is not first.value


def test_unresolved_service_traceback_does_not_grow(service_type):
    """Re-raising one instance would pin every caller frame for the worker's life."""
    service = service_type.addService('svc', implementation='missing')
    depths = []
    for _ in range(5):
        try:
            service.send('a message')
        except GnrException as err:
            depths.append(len(traceback.extract_tb(err.__traceback__)))
    assert len(set(depths)) == 1, depths
    assert service.unresolved_reason.__traceback__ is None


def test_unresolved_service_keeps_the_original_reason_chained(service_type):
    service = service_type.addService('svc', implementation='broken')
    with pytest.raises(GnrException) as excinfo:
        service.send('a message')
    assert isinstance(excinfo.value.__cause__, ImportError)
    assert '_no_such_module_gnrservices_test' in str(excinfo.value)


def test_unresolved_service_answers_protocol_lookups(service_type):
    """hasattr() must return False rather than raise, or copy and pickle break."""
    service = service_type.addService('svc', implementation='missing')
    assert hasattr(service, '__deepcopy__') is False
    assert service.unresolved_reason is service_type.service_instances['svc']._error


def test_unresolved_service_is_logged_at_registration(service_type, caplog):
    with caplog.at_level(logging.ERROR):
        service_type.addService('svc', implementation='missing')
    assert any('missing' in record.getMessage() for record in caplog.records)


def test_working_service_is_unaffected_by_a_broken_sibling(service_type):
    """The site keeps every service whose implementation does resolve."""
    service_type.addService('bad', implementation='missing')
    good = service_type.addService('good', implementation='alpha')
    assert not isinstance(good, GnrUnresolvedService)
    assert type(good) is service_type.implementations['alpha']


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
