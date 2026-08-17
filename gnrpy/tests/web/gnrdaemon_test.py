"""Coverage for the ``gnr.web.daemon`` entry-point override gate.

The scenario numbering in the test names follows the table in issue #1067.
Note that rows 1 (no provider installed) and 3 (provider installed, variable
unset) are the same code path: genropy declares no ``gnr.web:daemon`` entry
point of its own, so with the variable unset the entry points are never even
looked up.
"""
import importlib
import importlib.metadata
import logging
import os
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest

import gnr.web.daemon  # noqa: F401

DAEMON_PKG = 'gnr.web.daemon'
PROVIDER_ENV = 'GNR_DAEMON_PROVIDER'
FAKE_PROVIDER_MODULE = 'gnrdaemon_test_fake_provider'
FAKE_PROVIDER_DIST = 'gnr-daemon-test-provider'


def _entry_point(value, dist_name):
    """Stub with the attributes ``_resolve_provider`` actually reads."""
    return SimpleNamespace(value=value, dist=SimpleNamespace(name=dist_name))


def _daemon_modules():
    return [name for name in list(sys.modules)
            if name == DAEMON_PKG or name.startswith(f'{DAEMON_PKG}.')]


@pytest.fixture
def daemon_sandbox(monkeypatch):
    """Allow re-importing ``gnr.web.daemon`` without poisoning the suite.

    ``gnr.web.gnrwsgisite`` imports the package at module level, so by the
    time this test module runs the real package and some of its submodules
    are already in ``sys.modules``: they must be put back verbatim, otherwise
    every sibling test inherits a half-imported daemon package.
    """
    saved = {name: sys.modules[name] for name in _daemon_modules()}
    provider = ModuleType(FAKE_PROVIDER_MODULE)
    provider.MARKER = 'fake provider'
    monkeypatch.setitem(sys.modules, FAKE_PROVIDER_MODULE, provider)
    for name in saved:
        del sys.modules[name]
    yield provider
    for name in _daemon_modules():
        del sys.modules[name]
    sys.modules.update(saved)


def _patch_entry_points(monkeypatch, eps):
    def fake_entry_points(**kwargs):
        if (kwargs.get('group'), kwargs.get('name')) == ('gnr.web', 'daemon'):
            return list(eps)
        return []
    monkeypatch.setattr(importlib.metadata, 'entry_points', fake_entry_points)


def test_import_smoke():
    """The import smoke test #688 replaced its unit tests with."""
    assert sys.modules[DAEMON_PKG] is gnr.web.daemon


# --- _resolve_provider, pure unit tests -----------------------------------

def test_resolve_provider_matches_entry_point_value():
    eps = [_entry_point(FAKE_PROVIDER_MODULE, FAKE_PROVIDER_DIST)]
    assert gnr.web.daemon._resolve_provider(FAKE_PROVIDER_MODULE, eps) is eps[0]


def test_resolve_provider_matches_distribution_name():
    eps = [_entry_point(FAKE_PROVIDER_MODULE, FAKE_PROVIDER_DIST)]
    assert gnr.web.daemon._resolve_provider(FAKE_PROVIDER_DIST, eps) is eps[0]


def test_resolve_provider_ignores_unrelated_entry_points():
    """Row 5: the variable names a provider that is not installed."""
    eps = [_entry_point('other.provider', 'other-dist')]
    with pytest.raises(ImportError) as excinfo:
        gnr.web.daemon._resolve_provider(FAKE_PROVIDER_MODULE, eps)
    assert PROVIDER_ENV in str(excinfo.value)
    assert FAKE_PROVIDER_MODULE in str(excinfo.value)


def test_resolve_provider_raises_without_entry_points():
    with pytest.raises(ImportError):
        gnr.web.daemon._resolve_provider(FAKE_PROVIDER_MODULE, [])


def test_resolve_provider_warns_on_multiple_matches(caplog):
    """Today's ``_eps[0]`` picks an undefined winner silently."""
    eps = [_entry_point('first.provider', FAKE_PROVIDER_DIST),
           _entry_point('second.provider', FAKE_PROVIDER_DIST)]
    with caplog.at_level(logging.WARNING, logger='gnr.web'):
        assert gnr.web.daemon._resolve_provider(FAKE_PROVIDER_DIST, eps) is eps[0]
    assert 'first.provider' in caplog.text
    assert 'second.provider' in caplog.text


# --- the gate itself, on a real import ------------------------------------

def test_provider_installed_but_variable_unset(daemon_sandbox, monkeypatch):
    """Rows 1 and 3: the classic package, entry point or no entry point."""
    monkeypatch.delenv(PROVIDER_ENV, raising=False)
    _patch_entry_points(monkeypatch,
                        [_entry_point(FAKE_PROVIDER_MODULE, FAKE_PROVIDER_DIST)])
    daemon = importlib.import_module(DAEMON_PKG)
    assert daemon is not daemon_sandbox
    assert daemon.__file__.endswith(os.path.join('gnr', 'web', 'daemon', '__init__.py'))
    assert importlib.import_module(f'{DAEMON_PKG}.handler').__package__ == DAEMON_PKG


def test_provider_installed_and_requested(daemon_sandbox, monkeypatch):
    """Row 4: the whole namespace is replaced by the provider package."""
    monkeypatch.setenv(PROVIDER_ENV, FAKE_PROVIDER_MODULE)
    _patch_entry_points(monkeypatch,
                        [_entry_point(FAKE_PROVIDER_MODULE, FAKE_PROVIDER_DIST)])
    daemon = importlib.import_module(DAEMON_PKG)
    assert daemon is daemon_sandbox
    assert daemon.MARKER == 'fake provider'
    assert sys.modules[DAEMON_PKG] is daemon_sandbox


def test_requested_provider_not_installed(daemon_sandbox, monkeypatch):
    """Row 5 end to end: the import fails instead of falling back."""
    monkeypatch.setenv(PROVIDER_ENV, FAKE_PROVIDER_MODULE)
    _patch_entry_points(monkeypatch, [])
    with pytest.raises(ImportError):
        importlib.import_module(DAEMON_PKG)


# --- out of process -------------------------------------------------------

def _run_python(code, **env_overrides):
    env = os.environ.copy()
    env.pop(PROVIDER_ENV, None)
    for key, value in env_overrides.items():
        env[key] = value
    return subprocess.run([sys.executable, '-c', code], env=env,
                          capture_output=True, text=True)


def test_pyro4_is_imported_by_the_handler_not_by_the_package():
    """The package import alone is Pyro4-free; ``.handler`` is not.

    Cannot be asserted in process: Pyro4 is already in ``sys.modules`` by the
    time this module runs.
    """
    pytest.importorskip('Pyro4')
    result = _run_python(
        'import sys\n'
        'import gnr.web.daemon\n'
        'print("package:", "Pyro4" in sys.modules)\n'
        'import gnr.web.daemon.handler\n'
        'print("handler:", "Pyro4" in sys.modules)\n')
    assert result.returncode == 0, result.stderr
    assert 'package: False' in result.stdout
    assert 'handler: True' in result.stdout


def test_the_gate_is_per_process():
    """Same interpreter, same installation, two processes, two outcomes."""
    code = 'import gnr.web.daemon; print("imported")'
    classic = _run_python(code)
    assert classic.returncode == 0, classic.stderr
    assert 'imported' in classic.stdout
    overridden = _run_python(code, **{PROVIDER_ENV: FAKE_PROVIDER_MODULE})
    assert overridden.returncode != 0
    assert 'ImportError' in overridden.stderr
    assert PROVIDER_ENV in overridden.stderr
