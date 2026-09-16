"""Fresh-process contracts for the instance Bag implementation switch."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


_GNRPY = Path(__file__).resolve().parents[2]
_READ_MODE = """
import json, sys, gnr
from gnr.core.gnrbag import Bag
print(json.dumps({"mode": gnr.BAG_MODE, "class": Bag.__module__,
                  "native_imported": "genro_bag" in sys.modules}))
"""


def _run(config, code=_READ_MODE, *, explicit=True, arguments=()):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(_GNRPY), env.get("PYTHONPATH", "")]
    )
    env.pop("GNR_INSTANCE_CONFIG", None)
    if explicit:
        env["GNR_INSTANCE_CONFIG"] = str(config)
    else:
        env["GNR_LOCAL_PROJECTS"] = str(config.parents[3])
    return subprocess.run(
        [sys.executable, "-c", code, *arguments], env=env,
        capture_output=True, text=True, timeout=20,
    )


@pytest.mark.parametrize("flag", [None, "legacy", "legacy::T"])
def test_legacy_default_does_not_import_native_dependency(tmp_path, flag):
    config = tmp_path / "instanceconfig.xml"
    content = "" if flag is None else f'<experimental><bag implementation="{flag}"/></experimental>'
    config.write_text(f"<GenRoBag>{content}</GenRoBag>")
    result = _run(config)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "mode": "legacy", "class": "gnr.core.gnrbag", "native_imported": False,
    }


@pytest.mark.parametrize("flag", ["genro-bag", "genro-bag::T"])
def test_native_opt_in_uses_native_class_and_inherits_instance(tmp_path, flag):
    config = tmp_path / "instanceconfig.xml"
    config.write_text(f'<GenRoBag><experimental><bag implementation="{flag}"/></experimental></GenRoBag>')
    code = _READ_MODE + """
import os, subprocess
assert os.environ['GNR_INSTANCE_CONFIG']
from genro_bag import Bag as NativeBag
assert Bag is NativeBag
child = subprocess.check_output([sys.executable, '-c',
    "import gnr;from gnr.core.gnrbag import Bag;assert gnr.BAG_MODE == 'genro-bag';assert Bag.__module__.startswith('genro_bag.')"])
"""
    result = _run(config, code)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["mode"] == "genro-bag"


def test_cli_instance_discovery_reads_switch_before_consumers(tmp_path):
    config = tmp_path / "projects/demo/instances/pilot/instanceconfig.xml"
    config.parent.mkdir(parents=True)
    config.write_text('<GenRoBag><experimental><bag implementation="genro-bag"/></experimental></GenRoBag>')
    result = _run(config, explicit=False, arguments=("pilot",))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["mode"] == "genro-bag"


def test_invalid_flag_fails_instead_of_silently_selecting_mode(tmp_path):
    config = tmp_path / "instanceconfig.xml"
    config.write_text('<GenRoBag><experimental><bag implementation="invalid"/></experimental></GenRoBag>')
    result = _run(config)
    assert result.returncode != 0
    assert "Invalid experimental/bag implementation" in result.stderr


def test_switch_change_requires_new_process(tmp_path):
    config = tmp_path / "instanceconfig.xml"
    config.write_text('<GenRoBag><experimental><bag implementation="genro-bag"/></experimental></GenRoBag>')
    code = _READ_MODE + """
from pathlib import Path
import os
Path(os.environ['GNR_INSTANCE_CONFIG']).write_text('<GenRoBag/>')
from gnr.core.gnrbag import Bag as StillNative
assert StillNative is Bag
"""
    result = _run(config, code)
    assert result.returncode == 0, result.stderr
    result = _run(config)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["mode"] == "legacy"


@pytest.mark.parametrize('native', ['True', 'False'])
def test_virtual_columns_keep_names_in_real_sql_query(tmp_path, native):
    config = tmp_path / 'instanceconfig.xml'
    implementation = "genro-bag" if native == "True" else "legacy"
    config.write_text(f'<GenRoBag><experimental><bag implementation="{implementation}"/></experimental></GenRoBag>')
    code = '''
import os
from pathlib import Path
from gnr.sql.gnrsql import GnrSqlDb
path = str(Path(os.environ['GNR_INSTANCE_CONFIG']).parent / 'virtual.sqlite')
db = GnrSqlDb(implementation='sqlite', dbname=path)
try:
    db.createDb(path)
    pkg = db.packageSrc('checkbag')
    pkg.attributes.update(name_short='checkbag', name_long='Check Bag')
    tbl = pkg.table('person', pkey='id', name_long='Person')
    tbl.column('id', 'L')
    tbl.column('name')
    tbl.formulaColumn('display_name', '$name', static=True)
    tbl.formulaColumn('name_pair', composed_of='name,display_name')
    db.startup()
    db.checkDb(applyChanges=True)
    table = db.table('checkbag.person')
    assert table.model.static_virtual_columns.keys() == ['display_name']
    assert table.model.composite_columns.keys() == ['name_pair']
    table.insert(dict(id=1, name='Example'))
    db.commit()
    rows = table.query(columns='*').fetch()
    assert len(rows) == 1
    assert rows[0]['display_name'] == 'Example'
finally:
    db.closeConnection()
'''
    result = _run(config, code)
    assert result.returncode == 0, result.stderr


def test_native_mixin_keeps_real_classes_and_application_overrides(tmp_path):
    config = tmp_path / 'instanceconfig.xml'
    config.write_text('<GenRoBag><experimental><bag implementation="genro-bag"/></experimental></GenRoBag>')
    code = '''
from gnr.core.gnrbag import Bag
from genro_bag import Bag as NativeBag
from gnr.core.gnrlang import classMixin, instanceMixin, cloneClass
class Target(Bag):
    def answer(self):
        return 1
class Extension:
    def answer(self):
        return 2
    def make_bag(self):
        return Bag()
classMixin(Target, Extension)
assert Target.answer_(Target()) == 1
assert type(Target().make_bag()) is NativeBag
cloned = cloneClass('Cloned', Target)
assert issubclass(cloned, NativeBag)
obj = cloned()
instanceMixin(obj, Extension, methods='answer', prefix='custom')
assert obj.custom_answer() == 2
assert type(obj.make_bag()) is NativeBag
'''
    result = _run(config, code)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('public_mode', ['legacy', 'genro-bag'])
def test_legacy_file_cannot_be_loaded_by_changing_public_mode(tmp_path, public_mode):
    config = tmp_path / 'instanceconfig.xml'
    config.write_text('<GenRoBag><experimental><bag implementation="genro-bag"/></experimental></GenRoBag>')
    code = """
import importlib.util
import sys
from pathlib import Path
import gnr, gnr.core
from gnr.core.gnrbag import Bag
from genro_bag import Bag as NativeBag
gnr.BAG_MODE = sys.argv[1]
path = Path(gnr.core.__file__).parent / 'gnrbag.py'
spec = importlib.util.spec_from_file_location('historical_bag_probe', path)
old = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(old)
except ImportError as exc:
    assert 'Historical gnrbag.py is disabled' in str(exc)
else:
    raise AssertionError('Legacy file executed')
assert not any(name in vars(old) for name in ('Bag', 'BagNode', 'BagResolver'))
assert Bag is NativeBag
"""
    result = _run(config, code, arguments=(public_mode,))
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('operation', ['export', 'class_hook', 'instance_hook'])
def test_native_mixin_detects_binding_replacement(tmp_path, operation):
    config = tmp_path / 'instanceconfig.xml'
    config.write_text('<GenRoBag><experimental><bag implementation="genro-bag"/></experimental></GenRoBag>')
    code = """
import sys
import gnr.core.gnrbag as public
from gnr.core.gnrlang import classMixin, instanceMixin
from gnr.core.nativebag import ActivationError
class Target:
    pass
class Extension:
    @classmethod
    def __on_class_mixin__(cls, target, **kwargs):
        public.Bag = object
    def __onmixin__(self, **kwargs):
        public.Bag = object
operation = sys.argv[1]
try:
    if operation == 'export':
        public.Bag = object
        classMixin(Target, Target)
    elif operation == 'class_hook':
        classMixin(Target, Extension)
    else:
        instanceMixin(Target(), Extension())
except ActivationError as exc:
    assert 'export was replaced' in str(exc)
else:
    raise AssertionError('Replaced native export accepted')
"""
    result = _run(config, code, arguments=(operation,))
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('native', ['True', 'False'])
@pytest.mark.parametrize('load_first', [False, True])
def test_historical_file_guard_covers_alias_and_first_import(tmp_path, native, load_first):
    config = tmp_path / 'instanceconfig.xml'
    implementation = "genro-bag" if native == "True" else "legacy"
    config.write_text(f'<GenRoBag><experimental><bag implementation="{implementation}"/></experimental></GenRoBag>')
    code = """
import importlib.util
from pathlib import Path
import sys
if sys.argv[2] == 'False':
    import gnr
path = Path(sys.argv[3]) / 'gnr/core/gnrbag.py'
spec = importlib.util.spec_from_file_location('alternate_historical_bag', path)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
try:
    spec.loader.exec_module(module)
except ImportError as exc:
    assert sys.argv[1] == 'True', str(exc)
    assert 'Historical gnrbag.py is disabled' in str(exc)
    assert not any(name in vars(module) for name in
                   ('Bag', 'BagNode', 'BagResolver', 'BagCbResolver', 'DirectoryResolver'))
else:
    assert sys.argv[1] == 'False', 'Historical file was imported in native mode'
    assert all(hasattr(module, name) for name in ('Bag', 'BagNode', 'BagResolver'))
from gnr.core.gnrbag import Bag, BagNode, BagResolver
if sys.argv[1] == 'True':
    from genro_bag import Bag as NativeBag, BagNode as NativeNode, BagResolver as NativeResolver
    assert (Bag, BagNode, BagResolver) == (NativeBag, NativeNode, NativeResolver)
else:
    assert Bag.__module__ == 'gnr.core.gnrbag'
"""
    result = _run(config, code, arguments=(native, str(load_first), str(_GNRPY)))
    assert result.returncode == 0, result.stderr



def test_old_boolean_switch_requires_explicit_migration(tmp_path):
    config = tmp_path / 'instanceconfig.xml'
    config.write_text('<GenRoBag><experimental><bag native="True"/></experimental></GenRoBag>')
    result = _run(config)
    assert result.returncode != 0
    assert 'implementation="genro-bag"' in result.stderr


def test_missing_genro_bag_dependency_fails_without_legacy_fallback(tmp_path):
    config = tmp_path / 'instanceconfig.xml'
    config.write_text('<GenRoBag><experimental><bag implementation="genro-bag"/></experimental></GenRoBag>')
    result = _run(config, """
import sys
class MissingPackage:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'genro_bag':
            raise ModuleNotFoundError('Unavailable in this test', name=fullname)
sys.meta_path.insert(0, MissingPackage())
try:
    import gnr
except ImportError as error:
    assert 'genropy[genro-bag]' in str(error)
    assert 'gnr.core.gnrbag' not in sys.modules
else:
    raise AssertionError('Missing implementation fell back silently')
""")
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('action', ['reload', 'reimport', 'reconfigure', 'reload_config', 'delete_export'])
def test_native_import_selection_is_stable(tmp_path, action):
    config = tmp_path / 'instanceconfig.xml'
    config.write_text('<GenRoBag><experimental><bag implementation="genro-bag"/></experimental></GenRoBag>')
    code = '''
import importlib, os, sys
from pathlib import Path
import gnr
import gnr.core.gnrbag as public
from gnr.core.nativebag import activate, ActivationError
from gnr._bag_mode import configure_bag_mode
from genro_bag import Bag
original = public
original_classes = (public.Bag, public.BagNode, public.BagResolver)
action = sys.argv[1]
if action == 'reload':
    public = importlib.reload(public)
elif action == 'reimport':
    del sys.modules['gnr.core.gnrbag']
    del gnr.core.gnrbag
    public = importlib.import_module('gnr.core.gnrbag')
elif action in ('reconfigure', 'reload_config'):
    Path(os.environ['GNR_INSTANCE_CONFIG']).write_text('<GenRoBag/>')
    gnr.BAG_MODE = 'legacy'
    if action == 'reload_config':
        import gnr._bag_mode
        importlib.reload(gnr._bag_mode)
        importlib.reload(gnr)
    assert configure_bag_mode() == 'genro-bag'
    assert activate() is original
else:
    try:
        del public.Bag
    except ActivationError:
        pass
    else:
        raise AssertionError('Export deletion accepted')
assert public is original
assert (public.Bag, public.BagNode, public.BagResolver) == original_classes
assert public.Bag is Bag
from gnr.core.gnrbag import Bag as Imported
assert Imported is Bag
'''
    result = _run(config, code, arguments=(action,))
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('load_bag_first', [False, True])
def test_legacy_process_rejects_late_native_activation(tmp_path, load_bag_first):
    config = tmp_path / 'instanceconfig.xml'
    config.write_text('<GenRoBag/>')
    code = '''
import gnr, sys
if sys.argv[1] == 'True':
    from gnr.core.gnrbag import Bag
from gnr.core.nativebag import activate, ActivationError
gnr.BAG_MODE = 'genro-bag'
try:
    activate()
except ActivationError as exc:
    assert 'fixed at startup' in str(exc)
else:
    raise AssertionError('Late activation accepted')
from gnr.core.gnrbag import Bag
assert Bag.__module__ == 'gnr.core.gnrbag'
'''
    result = _run(config, code, arguments=(str(load_bag_first),))
    assert result.returncode == 0, result.stderr


def test_mixin_composition_does_not_rescan_existing_functions(tmp_path):
    config = tmp_path / 'instanceconfig.xml'
    config.write_text('<GenRoBag><experimental><bag implementation="genro-bag"/></experimental></GenRoBag>')
    code = '''
import sys
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import classMixin, instanceMixin, cloneClass, moduleClasses
import gnr.core.gnrbag as public
import gnr.core.nativebag as nativebag
assert 'Bag' in moduleClasses(public)
class Target:
    pass
calls = []
def profile(frame, event, arg):
    if event == 'call' and frame.f_code.co_filename == nativebag.__file__:
        calls.append(frame.f_code.co_name)
sys.setprofile(profile)
try:
    for i in range(100):
        def method(self):
            return Bag()
        extension = type('Extension', (), {'make_' + str(i): method})
        classMixin(Target, extension)
    obj = cloneClass('Cloned', Target)()
    instanceMixin(obj, extension)
finally:
    sys.setprofile(None)
assert calls == [], calls
assert isinstance(obj.make_0(), Bag)
assert isinstance(obj.make_99(), Bag)
'''
    result = _run(config, code)
    assert result.returncode == 0, result.stderr
