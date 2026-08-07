import importlib.util
import logging
import os

# sys.upgrade's Table model lives under projects/gnrcore/, which is not on
# the default test sys.path and is not wired to a full GenroPy site here.
# Load it directly from the file system so the pre-flight guard can be
# exercised without a database or application bootstrap. Same technique as
# gnrpy/tests/web/test_s3_temporary_filename.py.
_UPGRADE_MODULE_PATH = os.path.normpath(os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, os.pardir,
    'projects', 'gnrcore', 'packages', 'sys', 'model', 'upgrade.py',
))


def _get_upgrade_table_class():
    spec = importlib.util.spec_from_file_location('sys_upgrade_model', _UPGRADE_MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Table


Table = _get_upgrade_table_class()


class _FakeColumn:
    """Stands in for the real column struct; only getAttr('size') is used."""

    def __init__(self, size):
        self._size = size

    def getAttr(self, name):
        assert name == 'size'
        return self._size


class _FakeQuery:
    def fetchAsDict(self, key):
        return {}


class _FakePackage:
    def __init__(self, folder):
        self.packageFolder = folder


class _FakeApplication:
    def __init__(self, packages):
        self.packages = packages


class _FakeDb:
    def __init__(self, packages):
        self.application = _FakeApplication(packages)


def _make_table(tmp_path, filenames, pkg='mypkg', codekey_size=':80'):
    """Build a sys.upgrade Table instance wired to a fake upgrade folder.

    Only the collaborators runUpgrades() actually touches (query, column,
    db.application.packages) are faked; runUpgrade itself is stubbed by the
    caller to record what would have executed, without running real upgrade
    scripts or touching a database.
    """
    upgrades_dir = tmp_path / 'lib' / 'upgrades'
    upgrades_dir.mkdir(parents=True)
    for fname in filenames:
        (upgrades_dir / fname).write_text('def main(db):\n    return None\n')
    table = Table()
    table.db = _FakeDb({pkg: _FakePackage(str(tmp_path))})
    table.query = lambda **kwargs: _FakeQuery()
    table.column = lambda name: _FakeColumn(codekey_size)
    return table


def test_oversized_filename_is_reported_and_not_executed(tmp_path, caplog):
    pkg = 'mypkg'
    long_name = 'x' * 90  # 'mypkg|' + 90 chars overflows the codekey :80 budget
    short_name = 'normal_upgrade'
    table = _make_table(tmp_path, [f'{long_name}.py', f'{short_name}.py'], pkg=pkg)
    executed = []
    table.runUpgrade = lambda codekey: executed.append(codekey)

    with caplog.at_level(logging.INFO, logger='gnr.pkg'):
        table.runUpgrades()

    long_key = f'{pkg}|{long_name}'
    short_key = f'{pkg}|{short_name}'
    assert long_key not in executed
    assert short_key in executed

    # the report must be an error: the root logger defaults to WARNING, so a
    # lower level would leave the operator with no trace of the skipped upgrade
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) == 1
    assert long_key in errors[0].getMessage()


def test_normal_length_filenames_all_run(tmp_path, caplog):
    pkg = 'mypkg'
    table = _make_table(tmp_path, ['first_upgrade.py', 'second_upgrade.py'], pkg=pkg)
    executed = []
    table.runUpgrade = lambda codekey: executed.append(codekey)

    with caplog.at_level(logging.INFO, logger='gnr.pkg'):
        table.runUpgrades()

    assert executed == [f'{pkg}|first_upgrade', f'{pkg}|second_upgrade']
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
