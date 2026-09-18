"""Run native transport contracts without changing the parent process Bag mode."""
import os
from pathlib import Path
import subprocess
import sys


def test_native_transport_contracts(tmp_path):
    config = tmp_path / 'instanceconfig.xml'
    config.write_text(
        '<GenRoBag><experimental><bag implementation="genro-bag"/>'
        '</experimental></GenRoBag>')
    env = os.environ.copy()
    env['GNR_INSTANCE_CONFIG'] = str(config)
    root = Path(__file__).resolve().parents[2]
    env['PYTHONPATH'] = os.pathsep.join([str(root), env.get('PYTHONPATH', '')])
    cases = Path(__file__).with_name('bag_tytx_transport_cases.py')
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', str(cases), '-q',
         '-o', f'cache_dir={tmp_path / "pytest-cache"}'],
        env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
