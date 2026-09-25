"""Compare Bag helpers, explicitly excluding struct overrides."""

from .test_native_bag_data_regressions import _config, _run


def test_bag_child_and_rowchild_match_legacy_and_warn_in_native_mode(tmp_path):
    code = '''
import warnings
from gnr.core.gnrbag import Bag, BagException
b = Bag()
b.setBackRef()
with warnings.catch_warnings(record=True) as notices:
    warnings.simplefilter('always')
    assert b.rowchild(caption='Row') is None
    assert b.keys() == ['R_00000000']
    assert b.getItem('#0') is None
    assert b.getAttr('#0', '_pkey') == 'R_00000000'
    b.rowchild('named', _pkey='key', caption='Named')
    b.rowchild('named', caption='Changed')
    assert b.getAttr('named', '_pkey') == 'named'
    assert b.getAttr('named', 'caption') == 'Changed'
    child = b.child('section', 'branch.*_#', title='First')
    assert type(child) is Bag
    assert child is b.getItem('branch.section_0')
    assert b.getAttr('branch.section_0', 'tag') == 'section'
    assert b.child('text', 'leaf', childcontent='hello') is None
    assert b.getItem('leaf') == 'hello'
    try:
        b.child('different', 'leaf')
    except BagException:
        pass
    else:
        raise AssertionError('tag mismatch must fail')
    root = Bag()
    root.setBackRef()
    nested = root.child('outer', outer='allowed')
    assert nested.child('outer', _parentTag='allowed') is not None
    try:
        nested.child('outer', _parentTag='forbidden')
    except BagException:
        pass
    else:
        raise AssertionError('parent restriction must fail')
    # Exercise the Bag implementation directly, not a struct override.
    assert root.child('outer', 'outer_0', title='again') is nested
    assert nested.attributes['title'] == 'again'
if hasattr(b, 'set_item'):
    assert any('Bag.child is deprecated' in str(n.message) for n in notices)
    assert any('Bag.rowchild is deprecated' in str(n.message) for n in notices)
else:
    assert not notices
'''
    for mode in ('False', 'True'):
        result = _run(_config(tmp_path, mode), code)
        assert result.returncode == 0, result.stdout + result.stderr
