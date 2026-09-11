"""Document endpoints keep explicit storage versions after cache invalidation."""

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from gnr.core.gnrlang import gnrImport
from gnr.lib.services.storage import StorageNode


ENDPOINT_PATH = (Path(__file__).resolve().parents[3] / 'projects' / 'gnrcore'
                 / 'packages' / 'sys' / 'webpages' / 'ep_table.py')
endpoint = gnrImport(str(ENDPOINT_PATH), avoidDup=True)


class VersionedStorage:
    is_versioned = True

    def __init__(self, folder):
        self.folder = folder

    def expandpath(self, path):
        return path

    def fullpath(self, path):
        return path

    def exists(self, path):
        return (self.folder / 'latest').exists()

    def autocreate(self, path, autocreate=None):
        return

    def open(self, path, mode='rb', version_id=None):
        return (self.folder / (version_id or 'latest')).open(mode)

    def versions(self, path):
        return [dict(VersionId='previous', IsLatest=False, LastModified=datetime(2026, 1, 1)),
                dict(VersionId='current', IsLatest=True, LastModified=datetime(2026, 2, 1))]


@pytest.fixture
def document(db_sqlite, tmp_path):
    table = db_sqlite.table('invc.invoice')
    pkey = table.query(columns='$id', limit=1).fetch()[0]['id']
    storage = VersionedStorage(tmp_path)
    (tmp_path / 'previous').write_bytes(b'previous document')
    (tmp_path / 'latest').write_bytes(b'current document')
    generated = []

    def generate(record_id, **kwargs):
        generated.append(record_id)
        (tmp_path / 'latest').write_bytes(b'regenerated document')
        return f'archive:{record_id}.pdf'

    generate.tags = False
    generate.pathTemplate = 'archive:{0[id]}.pdf'
    generate.outdatedWatermark = 'Version of {localized_date}'
    page = endpoint.GnrCustomWebPage()
    page.db = db_sqlite
    page.site = SimpleNamespace(
        storageNode=lambda path, version=None: StorageNode(service=storage, path=path, version=version),
        register=SimpleNamespace(page=lambda *args, **kwargs: None))
    page.getPublicMethod = lambda *args: generate
    page.toText = lambda value, **kwargs: value.date().isoformat()
    page._ = lambda value: value
    return SimpleNamespace(page=page, table=table, pkey=pkey, folder=tmp_path,
                           generate=generate, generated=generated)


@pytest.mark.parametrize('latest_exists', [True, False])
def test_explicit_version_returns_historical_bytes(document, latest_exists):
    if not latest_exists:
        (document.folder / 'latest').unlink()
    node = document.page._get_documentNode(document.table, pkey=document.pkey,
                                           source='document', version='previous')
    with node.open() as source:
        assert source.read() == b'previous document'
    assert node.version == 'previous'
    assert node.watermark == 'Version of 2026-01-01'
    assert document.generated == []
    assert (document.folder / 'latest').exists() is latest_exists


@pytest.mark.parametrize('version', [None, '_latest_'])
@pytest.mark.parametrize('latest_exists', [True, False])
def test_latest_uses_cache_or_regenerates(document, version, latest_exists):
    if not latest_exists:
        (document.folder / 'latest').unlink()
    node = document.page._get_documentNode(document.table, pkey=document.pkey,
                                           source='document', version=version)
    with node.open() as source:
        assert source.read() == (b'current document' if latest_exists else b'regenerated document')
    assert node.version is None
    assert node.watermark is None
    assert document.generated == ([] if latest_exists else [document.pkey])


def test_missing_version_never_falls_back_to_latest(document):
    (document.folder / 'latest').unlink()
    node = document.page._get_documentNode(document.table, pkey=document.pkey,
                                           source='document', version='missing')
    with pytest.raises(FileNotFoundError):
        node.open()
    assert document.generated == []


def test_version_without_path_does_not_generate(document):
    document.generate.pathTemplate = None
    assert document.page._get_documentNode(document.table, pkey=document.pkey,
                                           source='document', version='previous') is None
    assert document.generated == []


def test_historical_version_still_requires_permission(document):
    document.generate.tags = 'admin'
    with pytest.raises(endpoint.NotAllowedError):
        document.page._get_documentNode(document.table, pkey=document.pkey,
                                       source='document', version='previous')
    assert document.generated == []
