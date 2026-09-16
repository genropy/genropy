"""Retired Bag features must not leak through native activation."""

from .test_native_bag_data_regressions import _config, _run


def test_native_module_does_not_export_formulas_or_validation(tmp_path):
    result = _run(_config(tmp_path, 'True'), '''
import gnr.core.gnrbag as module
for name in ('BagFormula', 'BagValidationList', 'BagValidationError'):
    assert not hasattr(module, name), name
bag = module.Bag()
for name in ('formula', 'defineFormula', 'defineSymbol'):
    assert not hasattr(bag, name), name
node = bag.set_item('x', 1)
assert not hasattr(node, 'is_valid')
''')
    assert result.returncode == 0, result.stdout + result.stderr
