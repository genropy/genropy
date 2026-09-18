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


def test_oversized_filename_stops_the_whole_run(tmp_path, caplog):
    """One rejected candidate and nothing runs.

    Executing the rest would apply the stack with a hole in it: an upgrade
    depending on the skipped one runs against a database that never got its
    change, which is worse than not upgrading at all.
    """
    pkg = 'mypkg'
    long_name = 'x' * 90  # 'mypkg|' + 90 chars overflows the codekey :80 budget
    short_name = 'normal_upgrade'
    table = _make_table(tmp_path, [f'{long_name}.py', f'{short_name}.py'], pkg=pkg)
    executed = []
    table.runUpgrade = lambda codekey: executed.append(codekey)

    with caplog.at_level(logging.INFO, logger='gnr.pkg'):
        errors = table.runUpgrades()

    long_key = f'{pkg}|{long_name}'
    assert executed == []
    assert [key for key, _ in errors] == [long_key]

    # the report must be an error: the root logger defaults to WARNING, so a
    # lower level would leave the operator with no trace of the aborted run
    logged = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert any(long_key in message for message in logged)
    assert any('No upgrade was run' in message for message in logged)


def test_normal_length_filenames_all_run(tmp_path, caplog):
    pkg = 'mypkg'
    table = _make_table(tmp_path, ['first_upgrade.py', 'second_upgrade.py'], pkg=pkg)
    executed = []
    table.runUpgrade = lambda codekey: executed.append(codekey)

    with caplog.at_level(logging.INFO, logger='gnr.pkg'):
        table.runUpgrades()

    assert executed == [f'{pkg}|first_upgrade', f'{pkg}|second_upgrade']
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


def test_a_name_at_the_filesystem_ceiling_fits_the_shipped_codekey(tmp_path):
    """The shipped sizes leave the pre-flight unreachable.

    255 is the ceiling a filesystem puts on a single name component, and pkg is
    sized like adm.pkginfo.pkgid: a 50-char package plus the separator plus a
    255-char filename is exactly the codekey budget, so no name that can exist
    on disk can be rejected.
    """
    table = _make_table(tmp_path, ['short.py'], pkg='p' * 50, codekey_size=':306')
    executed = []
    table.runUpgrade = lambda codekey: executed.append(codekey)
    table.runUpgrades()
    assert len(executed) == 1
    assert len('%s|%s' % ('p' * 50, 'f' * 255)) == 306
