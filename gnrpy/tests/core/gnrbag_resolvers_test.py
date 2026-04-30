import re
import time
from datetime import datetime

import pytest

from gnr.core.gnrbag import Bag, EnvResolver, UidResolver, TsResolver


# ---------- EnvResolver ----------

def test_env_default(monkeypatch):
    monkeypatch.delenv('GNRTEST_NOT_SET', raising=False)
    b = Bag()
    b['x'] = EnvResolver('GNRTEST_NOT_SET', default='fallback')
    assert b['x'] == 'fallback'


def test_env_read(monkeypatch):
    monkeypatch.setenv('GNRTEST_VAR', 'hello')
    b = Bag()
    b['x'] = EnvResolver('GNRTEST_VAR')
    assert b['x'] == 'hello'


def test_env_change_visible_with_cache_zero(monkeypatch):
    monkeypatch.setenv('GNRTEST_VAR', 'first')
    b = Bag()
    b['x'] = EnvResolver('GNRTEST_VAR')
    assert b['x'] == 'first'
    monkeypatch.setenv('GNRTEST_VAR', 'second')
    assert b['x'] == 'second'


def test_env_frozen_with_cache_negative_one(monkeypatch):
    monkeypatch.setenv('GNRTEST_VAR', 'first')
    b = Bag()
    b['x'] = EnvResolver('GNRTEST_VAR', cacheTime=-1)
    assert b['x'] == 'first'
    monkeypatch.setenv('GNRTEST_VAR', 'second')
    assert b['x'] == 'first'


# ---------- UidResolver ----------

def test_uid_default_is_22_chars():
    b = Bag()
    b['uid'] = UidResolver()
    val = b['uid']
    assert isinstance(val, str)
    assert len(val) == 22
    assert re.fullmatch(r'[A-Za-z0-9_]{22}', val)


def test_uid_stable_across_accesses():
    b = Bag()
    b['uid'] = UidResolver()
    assert b['uid'] == b['uid']


def test_uid_regenerates_with_cache_zero():
    b = Bag()
    b['uid'] = UidResolver(cacheTime=0)
    assert b['uid'] != b['uid']


def test_uid_uuid4_format():
    b = Bag()
    b['uid'] = UidResolver(version='uuid4')
    val = b['uid']
    assert len(val) == 36
    assert val.count('-') == 4


def test_uid_uuid1_format():
    b = Bag()
    b['uid'] = UidResolver(version='uuid1')
    val = b['uid']
    assert len(val) == 36
    assert val.count('-') == 4


def test_uid_invalid_version_raises():
    b = Bag()
    b['uid'] = UidResolver(version='bogus')
    with pytest.raises(ValueError):
        b['uid']


# ---------- TsResolver ----------

def test_ts_returns_datetime():
    b = Bag()
    b['now'] = TsResolver()
    assert isinstance(b['now'], datetime)


def test_ts_live_default_changes():
    b = Bag()
    b['now'] = TsResolver()
    t1 = b['now']
    time.sleep(0.002)
    t2 = b['now']
    assert t1 != t2


def test_ts_frozen_when_cache_negative_one():
    b = Bag()
    b['created'] = TsResolver(cacheTime=-1)
    t1 = b['created']
    time.sleep(0.002)
    t2 = b['created']
    assert t1 == t2


def test_ts_window_with_cache_seconds():
    b = Bag()
    b['ts'] = TsResolver(cacheTime=2)
    t1 = b['ts']
    time.sleep(0.05)
    t2 = b['ts']
    assert t1 == t2


def test_ts_utc_branch():
    if time.timezone == 0 and not time.daylight:
        pytest.skip('local timezone is UTC; cannot distinguish from utc branch')
    b = Bag()
    b['local'] = TsResolver(tz='local', cacheTime=-1)
    b['utc'] = TsResolver(tz='utc', cacheTime=-1)
    delta = abs((b['local'] - b['utc']).total_seconds())
    assert delta > 60


def test_ts_invalid_tz_raises():
    b = Bag()
    b['ts'] = TsResolver(tz='bogus')
    with pytest.raises(ValueError):
        b['ts']
