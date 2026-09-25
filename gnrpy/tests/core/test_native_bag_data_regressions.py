"""Fresh-process regressions for Bag-backed GenroPy data paths."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


_GNRPY = Path(__file__).resolve().parents[2]


def _run(config, code):
    env = os.environ.copy()
    env.update(
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONNOUSERSITE="1",
        GNR_INSTANCE_CONFIG=str(config),
        PYTHONPATH=os.pathsep.join([str(_GNRPY), env.get("PYTHONPATH", "")]),
    )
    return subprocess.run(
        [sys.executable, "-W", "error::RuntimeWarning", "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _config(tmp_path, native):
    config = tmp_path / "instanceconfig.xml"
    implementation = "genro-bag" if native == "True" else "legacy"
    config.write_text(
        f'<GenRoBag><experimental><bag implementation="{implementation}"/></experimental></GenRoBag>'
    )
    return config


@pytest.mark.parametrize("native", ["False", "True"], ids=["legacy", "native"])
def test_sql_selection_grid_keeps_named_rows_and_attributes(tmp_path, native):
    code = r'''
import os
from pathlib import Path
from gnr.sql.gnrsql import GnrSqlDb

dbpath = str(Path(os.environ["GNR_INSTANCE_CONFIG"]).with_name("selection.sqlite"))
db = GnrSqlDb(implementation="sqlite", dbname=dbpath)
try:
    db.createDb(dbpath)
    pkg = db.packageSrc("regression")
    pkg.attributes.update(name_short="regression", name_long="Regression")
    table_src = pkg.table("item", pkey="id", name_long="Item")
    table_src.column("id", "L")
    table_src.column("name")
    db.startup()
    db.checkDb(applyChanges=True)
    table = db.table("regression.item")
    table.insert(dict(id=1, name="First"))
    table.insert(dict(id=2, name="Second"))
    db.commit()
    grid = table.query(columns="$id,$name", order_by="$id").selection().output("grid")
    assert grid.keys() == ["1", "2"]
    assert [node.attr["name"] for node in grid] == ["First", "Second"]
    assert [node.attr["_pkey"] for node in grid] == ["1", "2"]
    first = grid.getNode("1").value
    assert first["id"] == 1
    assert first["name"] == "First"
finally:
    db.closeConnection()
'''
    result = _run(_config(tmp_path, native), code)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("native", ["False", "True"], ids=["legacy", "native"])
def test_config_resource_load_is_safe_inside_asyncio(tmp_path, native):
    code = r'''
import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
from gnr.core.gnrbag import Bag
from gnr.core.gnrbag import DirectoryResolver
from gnr.web.gnrwsgisite import GnrWsgiSite

root = Path(os.environ["GNR_INSTANCE_CONFIG"]).parent
config_dir = root / "config"
config_dir.mkdir()
resources = root / "resources"
(resources / "sample").mkdir(parents=True)
(config_dir / "environment.xml").write_text(
    '<GenRoBag><resources><local path="%s"/></resources></GenRoBag>' % resources
)
site = SimpleNamespace(
    site_path=str(root / "site"),
    gnr_config=Bag({"gnr": DirectoryResolver(str(config_dir))}),
)

async def connected():
    path = GnrWsgiSite.resource_name_to_path(site, "sample")
    assert path == str(resources / "sample")
    assert isinstance(site.gnr_config["gnr.environment_xml"], Bag)
    assert "resources" in site.gnr_config["gnr.environment_xml"]

asyncio.run(connected())
'''
    result = _run(_config(tmp_path, native), code)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("native", ["False", "True"], ids=["legacy", "native"])
def test_file_selection_builds_named_metadata_rows(tmp_path, native):
    code = r'''
import os
from pathlib import Path
from types import SimpleNamespace
from gnr.web.gnrwebpage_proxy.apphandler.misc import MiscMixin

class TempStorageNode:
    def __init__(self, path):
        self.path = Path(path)
        self.service = SimpleNamespace(service_name="temp")
    @property
    def basename(self):
        return self.path.name
    @property
    def fullpath(self):
        return str(self.path)
    @property
    def ext_attributes(self):
        stat = self.path.stat()
        return stat.st_mtime, stat.st_size, self.path.is_dir()
    def children(self):
        return [TempStorageNode(path) for path in self.path.iterdir()]
    def url(self):
        return self.path.as_uri()
    def internal_url(self):
        return self.path.as_uri()

class TempSite:
    def storageNode(self, value):
        return value if isinstance(value, TempStorageNode) else TempStorageNode(value)

folder = Path(os.environ["GNR_INSTANCE_CONFIG"]).with_name("files")
folder.mkdir()
(folder / "sample.txt").write_text("sample")
proxy = SimpleNamespace(page=SimpleNamespace(site=TempSite()))
result, attributes = MiscMixin.getFileSystemSelection(
    proxy, folders=str(folder), include="*.txt"
)
assert attributes == {}
assert len(result) == 1
node = result.getNode("#0")
assert node.label == "r_1"
assert node.value is None
assert node.attr["file_ext"] == "txt"
assert node.attr["_pkey"].endswith("sample.txt")
'''
    result = _run(_config(tmp_path, native), code)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("native", ["False", "True"], ids=["legacy", "native"])
def test_package_metadata_accepts_a_single_node_triple(tmp_path, native):
    result = _run(_config(tmp_path, native), '''
from gnr.core.gnrbag import Bag
info = Bag(('project', None, dict(name='demo', code='demo', language='en')))
assert info.keys() == ['project']
assert info.getNode('project').attr == dict(name='demo', code='demo', language='en')
assert info.getNode('project').value is None
''')
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("native", ["False", "True"], ids=["legacy", "native"])
@pytest.mark.parametrize("folder_name", [".gnr", "custom"])
def test_actual_gnr_config_accepts_directory_source(tmp_path, native, folder_name):
    folder = tmp_path / folder_name
    folder.mkdir()
    (folder / 'environment.xml').write_text('<GenRoBag><setting>ready</setting></GenRoBag>')
    code = f"""
import asyncio
import os
from pathlib import Path
from gnr.core.gnrconfig import getGnrConfig
async def read():
    folder = Path(os.environ['GNR_INSTANCE_CONFIG']).parent / {folder_name!r}
    config = getGnrConfig(str(folder))
    assert config.keys() == [{folder_name.lstrip('.')!r}]
    assert config[{(folder_name.lstrip('.') + '.environment_xml.setting')!r}] == 'ready'
asyncio.run(read())
"""
    result = _run(_config(tmp_path, native), code)
    assert result.returncode == 0, result.stderr
