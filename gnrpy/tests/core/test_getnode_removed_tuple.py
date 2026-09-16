"""Record formatting must not pass a default as the removed tuple flag."""

from .test_native_bag_data_regressions import _config, _run


def test_record_formatter_defaults_do_not_request_tuple_lookup(tmp_path):
    code = r'''
from types import SimpleNamespace
from gnr.core.gnrbag import Bag
from gnr.web.gnrtablescript import RecordToHtml
from gnr.web.gnrtablescript_new import RecordToHtml as NewRecordToHtml
record = Bag(dict(blank=None, zero=0))
formatter = SimpleNamespace(_data={'record': record}, encoding='utf-8',
                            toText=lambda value, *args: value)
for cls in (RecordToHtml, NewRecordToHtml):
    assert cls.field(formatter, 'blank', default=42) == 42
    assert cls.field(formatter, 'zero', default=42) == 0
'''
    for mode in ('False', 'True'):
        result = _run(_config(tmp_path, mode), code)
        assert result.returncode == 0, result.stdout + result.stderr
