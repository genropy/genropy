"""The JS compatibility writer must remain readable by both Python Bag modes."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize('mode', ['legacy', 'genro-bag'])
def test_js_context_xml_is_readable_in_python(tmp_path, mode):
    root = Path(__file__).resolve().parents[3]
    harness = root / 'gnrjs/tests/bag_audit_harness.cjs'
    script = '''
const {loadPair} = require(process.argv[1]);
const {gnr} = loadPair().selected;
const b = new gnr.GnrBag();
b.setItem('count', 12, {enabled:true, total:4});
b.setItem('flag', true);
b.setItem('ratio', 1.5);
b.setItem('text', '<hello> & world');
b.setItem('missing', null);
b.setItem('child', new gnr.GnrBag({leaf:'hello'}));
b.setItem('empty', new gnr.GnrBag());
process.stdout.write(JSON.stringify(b.toXml()));
'''
    produced = subprocess.run(['node', '-e', script, str(harness)],
                              capture_output=True, text=True, check=True, timeout=20)
    wire = tmp_path / 'context.xml'
    wire.write_text(json.loads(produced.stdout))
    config = tmp_path / 'instanceconfig.xml'
    config.write_text(f'<GenRoBag><experimental><bag implementation="{mode}"/></experimental></GenRoBag>')
    env = os.environ.copy()
    env['GNR_INSTANCE_CONFIG'] = str(config)
    env['PYTHONPATH'] = os.pathsep.join([str(root / 'gnrpy'), env.get('PYTHONPATH', '')])
    consumed = subprocess.run([sys.executable, '-c', '''
import sys
from pathlib import Path
from gnr.core.gnrbag import Bag
b = Bag(Path(sys.argv[1]).read_text())
assert b['count'] == 12 and type(b['count']) is int
assert b.getAttr('count', 'enabled') is True
assert b.getAttr('count', 'total') == 4
assert b['flag'] is True
assert b['ratio'] == 1.5
assert b['text'] == '<hello> & world'
assert b['missing'] is None
assert b['child.leaf'] == 'hello'
assert isinstance(b['empty'], Bag) and len(b['empty']) == 0
''', str(wire)], env=env, capture_output=True, text=True, timeout=20)
    assert consumed.returncode == 0, consumed.stderr
