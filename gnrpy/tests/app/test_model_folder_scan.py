"""``loadTableMixinDict`` turns the files of a model folder into mixin keys.

``__init__.py`` is an ordinary packaging habit and declares no table, so it must
not become one: with the build refusing a module that declares no table of its
own name (#106), a key for it stops the boot with advice that does not apply to
it.
"""

import os

from gnr.app.gnrapp import GnrPackage


class _ScanOnly:
    """The three attributes ``loadTableMixinDict`` touches, and nothing else."""

    baseTableMixinCls = None
    baseTableMixinClsCustom = None

    def __init__(self):
        self.tableMixinDict = {}

    loadTableMixinDict = GnrPackage.loadTableMixinDict


def _model_folder(tmp_path, *filenames):
    folder = tmp_path / 'model'
    folder.mkdir()
    for name in filenames:
        (folder / name).write_text('class Table:\n    pass\n')
    return str(folder)


def test_a_model_module_becomes_a_mixin_key(tmp_path):
    scanner = _ScanOnly()

    scanner.loadTableMixinDict(None, _model_folder(tmp_path, 'real.py'))

    assert sorted(scanner.tableMixinDict.keys()) == ['real']


def test_init_is_not_a_model_module(tmp_path):
    scanner = _ScanOnly()

    scanner.loadTableMixinDict(None, _model_folder(tmp_path, '__init__.py', 'real.py'))

    assert sorted(scanner.tableMixinDict.keys()) == ['real']


def test_an_absent_model_folder_yields_nothing(tmp_path):
    scanner = _ScanOnly()

    scanner.loadTableMixinDict(None, os.path.join(str(tmp_path), 'model'))

    assert scanner.tableMixinDict == {}
