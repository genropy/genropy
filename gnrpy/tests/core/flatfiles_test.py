# -*- coding: utf-8 -*-
"""
Tests for gnr.core.flatfiles.

These tests import directly from flatfiles (no deprecation warnings) and cover:
  - BaseReader path decomposition with file-like objects
  - File-like input for CsvReader, XlsReader, XlsxReader, XmlReader
  - CsvReader file-ownership semantics (open/close)
  - CsvReader.detect_encoding
  - XmlReader with properly tabular XML
  - getReader dispatch for both paths and file-like objects
  - XlsWriter and XlsxWriter round-trips (write then read back)
"""
import io
import os
import tempfile

import pytest

from gnr.core.flatfiles import (
    CsvReader, XlsReader, XlsxReader, XmlReader,
    getReader, readTab, readCSV, readCSV_new, readXLS,
    XlsWriter, XlsxWriter,
)
from gnr.core.gnrlist import GnrNamedList

TEST_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(TEST_DIR, 'data')

# Minimal tabular XML: two rows, attribute-style values
_TABULAR_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<GenRoBag>
  <row><name>Alice</name><city>NYC</city></row>
  <row><name>Bob</name><city>LA</city></row>
</GenRoBag>
"""


# ===========================================================================
# Direct imports from flatfiles (smoke: no DeprecationWarning)
# ===========================================================================

def test_direct_import_no_warning(recwarn):
    """Importing from flatfiles must not raise DeprecationWarning."""
    from gnr.core.flatfiles import CsvReader as CR  # noqa: F401
    dep_warnings = [w for w in recwarn.list if issubclass(w.category, DeprecationWarning)]
    assert dep_warnings == []


# ===========================================================================
# BaseReader — path decomposition for file-like objects
# ===========================================================================

def test_basereader_filelike_with_name():
    """ext/basename/dirname are derived from .name when the input is a file-like."""
    f = io.StringIO("a,b\n1,2")
    f.name = '/tmp/report.csv'
    r = CsvReader(f)
    assert r.ext == 'csv'
    assert r.basename == 'report'
    assert r.dirname == '/tmp'


def test_basereader_filelike_without_name():
    """File-like with no .name produces empty path components, no crash."""
    f = io.StringIO("a,b\n1,2")
    r = CsvReader(f)
    assert r.ext == ''
    assert r.basename == ''
    assert r.dirname == ''


# ===========================================================================
# CsvReader — file-like support and ownership semantics
# ===========================================================================

def test_CsvReader_stringio_reads_correctly():
    """CsvReader accepts a StringIO and yields correct rows."""
    f = io.StringIO("name,age\nAlice,30\nBob,25")
    r = CsvReader(f)
    assert r.headers == ['name', 'age']
    assert r.ncols == 2
    rows = list(r())
    assert len(rows) == 2
    assert isinstance(rows[0], GnrNamedList)
    assert rows[0]['name'] == 'Alice'
    assert rows[1]['age'] == '25'


def test_CsvReader_filelike_not_closed_after_iteration():
    """Reader does not close a caller-provided file-like after iteration."""
    f = io.StringIO("x,y\n1,2")
    r = CsvReader(f)
    assert r._owns_filecsv is False
    list(r())
    assert not f.closed


def test_CsvReader_path_owns_and_closes_file():
    """Reader opened from a path sets _owns_filecsv and closes after iteration."""
    path = os.path.join(DATA_DIR, 'test.csv')
    r = CsvReader(path)
    assert r._owns_filecsv is True
    list(r())
    assert r.filecsv.closed


def test_CsvReader_filelike_with_name_attribute():
    """Context string in duplicate-column warnings uses .name when available."""
    f = io.StringIO("col,col\n1,2")
    f.name = 'upload.csv'
    r = CsvReader(f)   # duplicate column 'col' triggers a warning
    assert 'col[1]' in r.headers
    assert r.ncols == 2


# ===========================================================================
# CsvReader.detect_encoding
# ===========================================================================

def test_CsvReader_detect_encoding_path():
    """detect_encoding works for common file encodings."""
    pytest.importorskip('chardet')
    for filename in ('test_Enc_UTF8.csv', 'test_Enc_ISO8859_1.csv'):
        path = os.path.join(DATA_DIR, filename)
        r = CsvReader(path, detect_encoding=True)
        rows = list(r())
        assert len(rows) > 0


def test_CsvReader_detect_encoding_filelike_is_noop():
    """detect_encoding is silently skipped for file-like inputs."""
    f = io.StringIO("a,b\n1,2")
    r = CsvReader(f, detect_encoding=True)
    rows = list(r())
    assert len(rows) == 1


# ===========================================================================
# XlsReader — file-like support
# ===========================================================================

def test_XlsReader_bytesio():
    """XlsReader reads from a BytesIO (binary file-like)."""
    xls_path = os.path.join(DATA_DIR, 'test.xls')
    with open(xls_path, 'rb') as f:
        data = io.BytesIO(f.read())
    r = XlsReader(data)
    assert 'a' in r.headers
    rows = list(r())
    assert len(rows) == 1
    assert isinstance(rows[0], GnrNamedList)
    assert 'a' in rows[0]


def test_XlsReader_bytesio_with_name():
    """XlsReader resolves ext/basename from BytesIO.name."""
    xls_path = os.path.join(DATA_DIR, 'test.xls')
    with open(xls_path, 'rb') as f:
        data = io.BytesIO(f.read())
    data.name = 'report.xls'
    r = XlsReader(data)
    assert r.ext == 'xls'
    assert r.basename == 'report'
    rows = list(r())
    assert len(rows) == 1


# ===========================================================================
# XlsxReader — file-like support
# ===========================================================================

def test_XlsxReader_bytesio():
    """XlsxReader reads from a BytesIO (openpyxl accepts file-like natively)."""
    pytest.importorskip('openpyxl')
    xlsx_path = os.path.join(DATA_DIR, 'test.xlsx')
    with open(xlsx_path, 'rb') as f:
        data = io.BytesIO(f.read())
    r = XlsxReader(data)
    assert 'a' in r.headers
    rows = list(r())
    assert len(rows) == 1
    assert isinstance(rows[0], GnrNamedList)
    assert 'a' in rows[0]


def test_XlsxReader_bytesio_with_name():
    """XlsxReader resolves ext/basename from BytesIO.name."""
    pytest.importorskip('openpyxl')
    xlsx_path = os.path.join(DATA_DIR, 'test.xlsx')
    with open(xlsx_path, 'rb') as f:
        data = io.BytesIO(f.read())
    data.name = 'report.xlsx'
    r = XlsxReader(data)
    assert r.ext == 'xlsx'
    assert r.basename == 'report'


# ===========================================================================
# XmlReader — tabular XML and file-like support
# ===========================================================================

def test_XmlReader_path_explicit_row_tag(tmp_path):
    """XmlReader reads a tabular XML file with an explicit row_tag."""
    xml_file = tmp_path / 'data.xml'
    xml_file.write_text(_TABULAR_XML)
    r = XmlReader(str(xml_file), row_tag='row')
    assert 'name' in r.headers
    assert 'city' in r.headers
    rows = list(r())
    assert len(rows) == 2
    assert isinstance(rows[0], GnrNamedList)
    assert rows[0]['name'] == 'Alice'
    assert rows[1]['city'] == 'LA'


def test_XmlReader_auto_row_tag(tmp_path):
    """XmlReader auto-detects the most common tag as row separator."""
    xml_file = tmp_path / 'data.xml'
    xml_file.write_text(_TABULAR_XML)
    r = XmlReader(str(xml_file))
    rows = list(r())
    assert len(rows) == 2
    assert rows[0]['name'] == 'Alice'


def test_XmlReader_filelike(tmp_path):
    """XmlReader accepts a file-like; reads content at construction time."""
    xml_file = tmp_path / 'data.xml'
    xml_file.write_text(_TABULAR_XML)
    with open(str(xml_file)) as f:
        r = XmlReader(f, row_tag='row')
    rows = list(r())
    assert len(rows) == 2
    assert rows[0]['name'] == 'Alice'
    assert rows[1]['name'] == 'Bob'


# ===========================================================================
# getReader — file-like dispatch
# ===========================================================================

def test_getReader_filelike_csv_by_name():
    """getReader dispatches to CsvReader when file-like.name ends in .csv."""
    f = io.StringIO("col_a,col_b\nfoo,bar")
    f.name = 'upload.csv'
    r = getReader(f)
    assert isinstance(r, CsvReader)
    rows = list(r())
    assert rows[0]['col_a'] == 'foo'


def test_getReader_filelike_xls_by_name():
    """getReader dispatches to XlsReader when file-like.name ends in .xls."""
    xls_path = os.path.join(DATA_DIR, 'test.xls')
    with open(xls_path, 'rb') as f:
        data = io.BytesIO(f.read())
    data.name = 'report.xls'
    r = getReader(data)
    assert isinstance(r, XlsReader)
    assert len(list(r())) == 1


def test_getReader_filelike_xlsx_by_name():
    """getReader dispatches to XlsxReader when file-like.name ends in .xlsx."""
    pytest.importorskip('openpyxl')
    xlsx_path = os.path.join(DATA_DIR, 'test.xlsx')
    with open(xlsx_path, 'rb') as f:
        data = io.BytesIO(f.read())
    data.name = 'report.xlsx'
    r = getReader(data)
    assert isinstance(r, XlsxReader)
    assert len(list(r())) == 1


def test_getReader_filelike_explicit_filetype_excel():
    """getReader uses filetype kwarg when file-like has no meaningful name."""
    xls_path = os.path.join(DATA_DIR, 'test.xls')
    with open(xls_path, 'rb') as f:
        data = io.BytesIO(f.read())   # BytesIO has no .name
    r = getReader(data, filetype='excel')
    assert isinstance(r, XlsReader)
    assert len(list(r())) == 1


# ===========================================================================
# XlsWriter round-trip
# ===========================================================================

def test_XlsWriter_round_trip():
    """XlsWriter produces a readable XLS; XlsReader gets the original values back."""
    pytest.importorskip('xlwt')
    pytest.importorskip('xlrd')

    with tempfile.NamedTemporaryFile(suffix='.xls', delete=False) as f:
        xls_path = f.name
    try:
        w = XlsWriter(
            headers=['name', 'city'],
            columns=['name', 'city'],
            coltypes={'name': 'T', 'city': 'T'},
            filepath=xls_path,
            sheet_base_name='Sheet1',
        )
        w.writeHeaders()
        w.writeRow({'name': 'Alice', 'city': 'NYC'})
        w.writeRow({'name': 'Bob', 'city': 'LA'})
        w.workbookSave()

        r = XlsReader(xls_path)
        assert 'name' in r.headers
        assert 'city' in r.headers
        rows = list(r())
        assert len(rows) == 2
        assert rows[0]['name'] == 'Alice'
        assert rows[0]['city'] == 'NYC'
        assert rows[1]['name'] == 'Bob'
    finally:
        os.unlink(xls_path)


# ===========================================================================
# XlsxWriter round-trip
# ===========================================================================

def test_XlsxWriter_round_trip():
    """XlsxWriter produces a readable XLSX; XlsxReader gets the original values back."""
    pytest.importorskip('openpyxl')

    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        xlsx_path = f.name
    try:
        w = XlsxWriter(
            headers=['name', 'city'],
            columns=['name', 'city'],
            coltypes={'name': 'T', 'city': 'T'},
            filepath=xlsx_path,
            sheet_base_name='Sheet1',
        )
        w.writeHeaders()
        w.writeRow({'name': 'Alice', 'city': 'NYC'})
        w.writeRow({'name': 'Bob', 'city': 'LA'})
        w.workbookSave()

        r = XlsxReader(xlsx_path)
        assert 'name' in r.headers
        assert 'city' in r.headers
        rows = list(r())
        assert len(rows) == 2
        assert rows[0]['name'] == 'Alice'
        assert rows[0]['city'] == 'NYC'
        assert rows[1]['name'] == 'Bob'
    finally:
        os.unlink(xlsx_path)


# ===========================================================================
# Legacy functions — smoke tests confirming they still live in flatfiles
# ===========================================================================

def test_legacy_functions_importable_from_flatfiles():
    """readTab, readCSV, readCSV_new, readXLS are accessible from flatfiles."""
    assert callable(readTab)
    assert callable(readCSV)
    assert callable(readCSV_new)
    assert callable(readXLS)
