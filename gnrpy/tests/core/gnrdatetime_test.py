# -*- coding: utf-8 -*-

from datetime import timezone
import pytz

from gnr.core import gnrdatetime as gdt

ISO_TEST_TS = "1978-04-23 23:10:00"
ISO_TEST_TS_AWARE = f"{ISO_TEST_TS}+02:00"
TEST_ZONE = "Europe/Rome"

def test_awareness():
    t = gdt.datetime.now()
    assert t.tzinfo is not None
    t = gdt.datetime.utcnow()
    assert t.tzinfo is not None
    t = gdt.datetime.fromiso(ISO_TEST_TS)
    assert t.tzinfo is not None
    t = gdt.datetime.fromiso(ISO_TEST_TS_AWARE)
    assert t.tzinfo is not None
    t = gdt.now()
    assert t.tzinfo is not None
    t = gdt.utcnow()
    assert t.tzinfo is not None
    
def test_custom_tz():
    ctz =timezone.utc

    t = gdt.datetime.now(ctz)
    assert t.tzinfo is ctz
    t = gdt.now(ctz)
    assert t.tzinfo is ctz
    t = gdt.datetime.fromiso(ISO_TEST_TS, tz=ctz)
    assert t.tzinfo is ctz
    t = gdt.datetime.fromiso(ISO_TEST_TS_AWARE, tz=ctz)
    assert t.tzinfo is ctz
    
    ctz = pytz.timezone(TEST_ZONE)
    
    t = gdt.datetime.now(ctz)
    assert t.tzinfo.zone is ctz.zone
    t = gdt.now(ctz)
    assert t.tzinfo.zone is ctz.zone
    t = gdt.datetime.fromiso(ISO_TEST_TS, tz=ctz)
    assert t.tzinfo is ctz
    t = gdt.datetime.fromiso(ISO_TEST_TS_AWARE, tz=ctz)
    assert t.tzinfo.zone == TEST_ZONE

def test_tzdatetime_default():
    ctz = timezone.utc
    c = gdt.datetime(year=1978, month=4, day=23,
                     hour=23, minute=10, second=0, tz=ctz)
    assert c.tzinfo is not None
    c = gdt.datetime(year=1978, month=4, day=23,
                     hour=23, minute=10, second=0)
    assert c.tzinfo is not None
    
