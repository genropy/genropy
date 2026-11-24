"""Packages hook a table method of another package with ``@oncalling`` / ``@oncalled`` (#1883).

The model folders go through the real ``loadTableMixinDict`` (``fromPkg`` for the
``_packages`` ones) and the result is mixed into a ``GnrObject`` as the table
object does, so both ``instanceMixin`` hops are exercised.
"""

from gnr.app.gnrapp import GnrPackage
from gnr.core.gnrlang import GnrObject, instanceMixin


class _ScanOnly:
    """The three attributes ``loadTableMixinDict`` touches, and nothing else."""

    baseTableMixinCls = None
    baseTableMixinClsCustom = None

    def __init__(self):
        self.tableMixinDict = {}

    loadTableMixinDict = GnrPackage.loadTableMixinDict


OWNER_TABLE = '''
from gnr.core.gnrdecorator import customizable


class Table(object):
    @customizable
    def updateBalance(self, amount):
        self.calls.append('owner')
        return amount
'''

HOOK_TABLE = '''
from gnr.core.gnrdecorator import {decorator}


class Table(object):
    @{decorator}
    def updateBalance(self, amount, **kwargs):
        self.calls.append('{label}')
'''


def _model_folder(folder, source):
    folder.mkdir(parents=True)
    (folder / 'invoice.py').write_text(source)
    return str(folder)


def test_hooks_of_two_packages_run_around_the_owner_method(tmp_path):
    scanner = _ScanOnly()
    scanner.loadTableMixinDict(None, _model_folder(tmp_path / 'owner' / 'model', OWNER_TABLE))
    for pkg, decorator in (('first', 'oncalling'), ('second', 'oncalled')):
        folder = _model_folder(tmp_path / pkg / 'model' / '_packages' / 'owner',
                               HOOK_TABLE.format(decorator=decorator, label=pkg))
        scanner.loadTableMixinDict(None, folder, fromPkg=pkg)

    table = GnrObject()
    table.calls = []
    instanceMixin(table, scanner.tableMixinDict['invoice'])

    assert table.updateBalance(10) == 10
    assert table.calls == ['first', 'owner', 'second']
    assert not hasattr(table, 'updateBalance_')
