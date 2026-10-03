"""Legacy callback traversal remains available through native activation."""

from .test_native_bag_data_regressions import _config, _run


def test_native_walk_matches_legacy_skip_paths_and_first_result(tmp_path):
    code = r'''
import warnings
from gnr.core.gnrbag import Bag
b = Bag()
b.setItem('a.skip.child', 1)
b.setItem('a.keep', 2)
b.setItem('tail', 3)
seen = []
def callback(node, _pathlist, _indexlist, marker):
    seen.append((node.label, _pathlist, _indexlist, marker))
    if node.label == 'skip':
        return False
    if node.label == 'keep':
        return node
with warnings.catch_warnings(record=True) as notices:
    warnings.simplefilter('always')
    result = b.walk(callback, _pathlist=[], _indexlist=[], marker=42)
assert result is b.getNode('a.keep')
assert seen == [('a', [], [], 42), ('skip', ['a'], [0], 42),
                ('keep', ['a'], [0], 42)], seen
if hasattr(b, 'for_each'):
    assert any('Bag.walk is deprecated' in str(n.message) for n in notices)
'''
    for mode in ('False', 'True'):
        result = _run(_config(tmp_path, mode), code)
        assert result.returncode == 0, result.stdout + result.stderr
