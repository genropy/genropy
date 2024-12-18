# -*- coding: utf-8 -*-


import pytest
import datetime

from gnr.core import gnrdate

def test_relativeDay():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod("today", workdate=workdate)
    assert res == '2008-04-25'
    res = gnrdate.decodeDatePeriod("yesterday", workdate=workdate)
    assert res == '2008-04-24'
    res = gnrdate.decodeDatePeriod("tomorrow", workdate=workdate)
    assert res == '2008-04-26'


    res = gnrdate.decodeDatePeriod("2024-01-01;2024-03-01", workdate=workdate)
    assert res == "2024-01-01;2024-03-01"

    res = gnrdate.decodeDatePeriod("no period", workdate=workdate, locale="en")
    assert res == ""

    
    workdate = datetime.date(2008, 4, 1)
    res = gnrdate.decodeDatePeriod("yesterday", workdate=workdate)
    assert res == '2008-03-31'

    workdate = datetime.date(2008, 4, 30)
    res = gnrdate.decodeDatePeriod("tomorrow", workdate=workdate)
    assert res == '2008-05-01'

def test_relativeDayLocal():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod("oggi", workdate=workdate, locale='it')
    assert res == '2008-04-25'
    res = gnrdate.decodeDatePeriod("ieri", workdate=workdate, locale='it')
    assert res == '2008-04-24'
    res = gnrdate.decodeDatePeriod("domani", workdate=workdate, locale='it')
    assert res == '2008-04-26'

def test_week():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod("this week", workdate=workdate)
    assert res == '2008-04-21;2008-04-27'

    res = gnrdate.decodeDatePeriod("next week", workdate=workdate)
    assert res == '2008-04-28;2008-05-04'

    res = gnrdate.decodeDatePeriod("last week", workdate=workdate)
    assert res == '2008-04-14;2008-04-20'

def test_month():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod("this month", workdate=workdate)
    assert res == '2008-04-01;2008-04-30'

    res = gnrdate.decodeDatePeriod("month", workdate=workdate)
    assert res == '2008-04-01;2008-04-30'

    res = gnrdate.decodeDatePeriod("next month", workdate=workdate)
    assert res == '2008-05-01;2008-05-31'

    res = gnrdate.decodeDatePeriod("last month", workdate=workdate)
    assert res == '2008-03-01;2008-03-31'

def test_monthLocal():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod("questo mese", workdate=workdate, locale='it')
    assert res == '2008-04-01;2008-04-30'

    res = gnrdate.decodeDatePeriod("mese", workdate=workdate, locale='it')
    assert res == '2008-04-01;2008-04-30'

def test_year():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod("2007", workdate=workdate)
    assert res == '2007-01-01;2007-12-31'

    res = gnrdate.decodeDatePeriod("07", workdate=workdate)
    assert res == '2007-01-01;2007-12-31'

    res = gnrdate.decodeDatePeriod("96", workdate=workdate)
    assert res == '1996-01-01;1996-12-31'

def test_monthName():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod("february", workdate=workdate)
    assert res == '2008-02-01;2008-02-29'

def test_periodTo():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod("to tomorrow", workdate=workdate)
    assert res == ';2008-04-26'

    res = gnrdate.decodeDatePeriod("to january", workdate=workdate)
    assert res == ';2008-01-31'

    res = gnrdate.decodeDatePeriod("to april", workdate=workdate)
    assert res == ';2008-04-30'

    res = gnrdate.decodeDatePeriod("to december", workdate=workdate)
    assert res == ';2007-12-31'

    res = gnrdate.decodeDatePeriod("to december 2007", workdate=workdate)
    assert res == ';2007-12-31'


def test_periodFrom():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod("from tomorrow + 2", workdate=workdate)
    assert res == '2008-04-28;'

    res = gnrdate.decodeDatePeriod("from december 07", workdate=workdate)
    assert res == '2007-12-01;'

    res = gnrdate.decodeDatePeriod("from december", workdate=workdate)
    assert res == '2008-12-01;'

    res = gnrdate.decodeDatePeriod("from february", workdate=workdate)
    assert res == '2008-02-01;'

def test_periodFull():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod("from february to today", workdate=workdate)
    assert res == '2008-02-01;2008-04-25'

    res = gnrdate.decodeDatePeriod("december to today", workdate=workdate)
    assert res == '2007-12-01;2008-04-25'

    res = gnrdate.decodeDatePeriod("from december 06 to march", workdate=workdate)
    assert res == '2006-12-01;2008-03-31'

    res = gnrdate.decodeDatePeriod("from december to march 06", workdate=workdate)
    assert res == '2005-12-01;2006-03-31'

    res = gnrdate.decodeDatePeriod("from december to this month", workdate=workdate)
    assert res == '2007-12-01;2008-04-30'

    res = gnrdate.decodeDatePeriod("between december and this month", workdate=workdate)
    assert res == '2007-12-01;2008-04-30'

    res = gnrdate.decodeDatePeriod("from last week to next month", workdate=workdate)
    assert res == '2008-04-14;2008-05-31'

def test_periodLocal():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod("da dicembre a mar 06", workdate=workdate, locale='it')
    assert res == '2005-12-01;2006-03-31'

    res = gnrdate.decodeDatePeriod("da dicembre a questo mese", workdate=workdate, locale='it')
    assert res == '2007-12-01;2008-04-30'

    res = gnrdate.decodeDatePeriod("da settimana scorsa al mese prossimo", workdate=workdate, locale='it')
    assert res == '2008-04-14;2008-05-31'

    res = gnrdate.decodeDatePeriod(u"da dicembre", workdate=workdate, locale='it')
    assert res == '2008-12-01;'

    res = gnrdate.decodeDatePeriod(u"a dicembre", workdate=workdate, locale='it')
    assert res == ';2007-12-31'

    res = gnrdate.decodeDatePeriod(u"dal 23-12-07 a aprile", workdate=workdate, locale='it')
    assert res == '2007-12-23;2008-04-30'

def test_weekDay():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod("monday", workdate=workdate)
    assert res == '2008-04-21'

    res = gnrdate.decodeDatePeriod(u"lunedì", workdate=workdate, locale='it')
    assert res == '2008-04-21'

    res = gnrdate.decodeDatePeriod(u"da lunedì a oggi", workdate=workdate, locale='it')
    assert res == '2008-04-21;2008-04-25'

    res = gnrdate.decodeDatePeriod(u"da lunedì a oggi", workdate=workdate, locale='it')
    assert res == '2008-04-21;2008-04-25'

def test_localDate():
    workdate = datetime.date(2008, 4, 25)
    # res = gnrdate.decodeDatePeriod(u"02 01, 2007", workdate=workdate, locale='en') ### TODO: fails in babel.dates.parse_date
    # assert res == '2007-02-01'

    res = gnrdate.decodeDatePeriod(u"02/01/08", workdate=workdate, locale='en_au')
    assert res == '2008-01-02'

    res = gnrdate.decodeDatePeriod(u"02/01/08", workdate=workdate, locale='it')
    assert res == '2008-01-02'

    res = gnrdate.decodeDatePeriod(u"02/01/2008", workdate=workdate, locale='it')
    assert res == '2008-01-02'

    res = gnrdate.decodeDatePeriod(u"02-01-2008", workdate=workdate, locale='it')
    assert res == '2008-01-02'

    res = gnrdate.decodeDatePeriod(u"02 01 2008", workdate=workdate, locale='it')
    assert res == '2008-01-02'

def test_isoDate():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod(u"2008-01-02", workdate=workdate, locale='it')
    assert res == '2008-01-02'

    res = gnrdate.decodeDatePeriod(u"2008-01-02 to 2008-02-02", workdate=workdate)
    assert res == '2008-01-02;2008-02-02'


def test_localDateNoSep():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod(u"02012008", workdate=workdate, locale='it')
    assert res == '2008-01-02'

    res = gnrdate.decodeDatePeriod(u"020108", workdate=workdate, locale='it')
    assert res == '2008-01-02'

def test_localPeriodNoSep():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod(u"01012008 a 31012008", workdate=workdate, locale='it')
    assert res == '2008-01-01;2008-01-31'

    res = gnrdate.decodeDatePeriod(u"010108 a 310108", workdate=workdate, locale='it')
    assert res == '2008-01-01;2008-01-31'

def test_quarter():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod("1st quarter", workdate=workdate, locale='en')
    assert res == '2008-01-01;2008-03-31'

    res = gnrdate.decodeDatePeriod(u"from 1st quarter to 2nd quarter", workdate=workdate, locale='en')
    assert res == '2008-01-01;2008-06-30'

    res = gnrdate.decodeDatePeriod(u"Q1", workdate=workdate, locale='en')
    assert res == '2008-01-01;2008-03-31'

    res = gnrdate.decodeDatePeriod(u"from Q1 to Q2", workdate=workdate, locale='en')
    assert res == '2008-01-01;2008-06-30'

    # FIXME: apparently, this kind of parsing is not, and never was, supported by babel
    #res = gnrdate.decodeDatePeriod(u"1° trimestre", workdate=workdate, locale='it')
    #assert res == '2008-01-01;2008-03-31'

    #res = gnrdate.decodeDatePeriod(u"dal 1° trimestre al 2° trimestre", workdate=workdate, locale='it')
    #assert res == '2008-01-01;2008-06-30'

    res = gnrdate.decodeDatePeriod(u"T1", workdate=workdate, locale='it')
    assert res == '2008-01-01;2008-03-31'

    res = gnrdate.decodeDatePeriod(u"da T1 a T2", workdate=workdate, locale='it')
    assert res == '2008-01-01;2008-06-30'

def test_addToDay():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod(u"today + 1", workdate=workdate)
    assert res == '2008-04-26'

    res = gnrdate.decodeDatePeriod(u"today + 6", workdate=workdate)
    assert res == '2008-05-01'

    res = gnrdate.decodeDatePeriod(u"tomorrow + 6", workdate=workdate)
    assert res == '2008-05-02'

    res = gnrdate.decodeDatePeriod(u"yesterday + 6", workdate=workdate)
    assert res == '2008-04-30'

    res = gnrdate.decodeDatePeriod(u"today - 6", workdate=workdate)
    assert res == '2008-04-19'

    res = gnrdate.decodeDatePeriod(u"from today - 6 to tomorrow + 2", workdate=workdate)
    assert res == '2008-04-19;2008-04-28'


def test_addToMonth():
    workdate = datetime.date(2008, 4, 25)
    res = gnrdate.decodeDatePeriod(u"this month + 1", workdate=workdate)
    assert res == '2008-05-01;2008-05-31'

    res = gnrdate.decodeDatePeriod(u"this month - 1", workdate=workdate)
    assert res == '2008-03-01;2008-03-31'

    res = gnrdate.decodeDatePeriod(u"from this month - 1 to this month + 1", workdate=workdate)
    assert res == '2008-03-01;2008-05-31'

    res = gnrdate.decodeDatePeriod(u"from this month - 6 to this month + 6", workdate=workdate)
    assert res == '2007-10-01;2008-10-31'

    res = gnrdate.decodeDatePeriod(u"from this month - 12 to this month + 12", workdate=workdate)
    assert res == '2007-04-01;2009-04-30'

def test_toTime():
    dt = datetime.datetime(2010, 4, 8, 10, 30)
    t = datetime.time(10, 30)
    assert isinstance(gnrdate.toTime(dt), datetime.time)
    assert isinstance(gnrdate.toTime(t), datetime.time)
    assert isinstance(gnrdate.toTime('10:30'), datetime.time)
    assert gnrdate.toTime(dt) == t
    assert gnrdate.toTime('10:30') == t

    with pytest.raises(ValueError) as excinfo:
        gnrdate.toTime("antani come se fosse per tre")
    assert "unrecognized string" in str(excinfo.value)
    
    with pytest.raises(ValueError) as excinfo:
        gnrdate.toTime(dict())
    assert "accepts only times" in str(excinfo.value)


def test_toDHZ():
    d = datetime.date(2024,1,2)
    t = datetime.time(10,30)

    # this can't actually be tests, being
    # tied to the machine where the tests
    # are being executed. We just run
    # with "LOCAL" for coverage pourposes
    res = gnrdate.toDHZ(d, t, "LOCAL")

    
    res = gnrdate.toDHZ(d, t, "Europe/Rome")
    assert res.tzinfo.zone == "Europe/Rome"
    res = gnrdate.toDHZ(d, t, "UTC")
    assert res.tzinfo.zone == "UTC"
    res = gnrdate.toDHZ(d, t)
    assert res.tzinfo.zone == "UTC"
    

def test_nextMonth():
    d = datetime.date(2024,1,2)
    res = gnrdate.nextMonth(d)
    assert res.month == 2
    assert res.year == 2024
    d = datetime.date(2024,12,2)
    res = gnrdate.nextMonth(d)
    assert res.month == 1
    assert res.year == 2025

def test_prevMonth():
    d = datetime.date(2024,1,2)
    res = gnrdate.prevMonth(d)
    assert res.month == 12
    assert res.year == 2023
    d = datetime.date(2024,12,2)
    res = gnrdate.prevMonth(d)
    assert res.month == 11
    assert res.year == 2024


def test_monthsFromDateRange():
    startd = datetime.date(2024,1,2)
    endd =  datetime.date(2024,4,23)
    res = gnrdate.monthsFromDateRange(startd, endd, locale="IT-it")
    assert len(res) == 4

    endd = datetime.date(2025,1,1)
    res = gnrdate.monthsFromDateRange(startd, endd, locale="IT_it")
    assert len(res) == 13
    assert "Giugno 2024" in res

    res = gnrdate.monthsFromDateRange(startd, endd, locale="EN-gb")
    assert "Giugno 2024" not in res
    assert "June 2024" in res

def test_decodeOneDate():
    # most of the implementation is already covered
    # by testing decodeDatePeriod, this are just the missing bits
    r = gnrdate.decodeOneDate("2024-01-02 alle 14:57", locale="it")
    assert r == datetime.datetime(2024, 1, 2, 14, 57)

    today = datetime.date.today()
    r = gnrdate.decodeOneDate("this week + 2", locale="en")
    exp = today + datetime.timedelta(days=((7*2) - today.weekday()))
    assert r == exp
    
    r = gnrdate.decodeOneDate("this week - 2", locale="en")
    exp = today + datetime.timedelta(days=-((7*2) + today.weekday()))
    assert r == exp


def test_periodCaption():
    startd = "2024-01-01"
    endd = "2024-03-17"
    r = gnrdate.periodCaption(startd, endd, locale="en")
    assert r == "from 2024-01-01 to 2024-03-17"
    r = gnrdate.periodCaption(startd, endd, locale="it")
    assert r == "da 2024-01-01 a 2024-03-17"

    r = gnrdate.periodCaption(startd, locale="it")
    assert r == f"da {startd}"
    r = gnrdate.periodCaption(startd, locale="en")
    assert r == f"from {startd}"

    r = gnrdate.periodCaption(None, endd, locale="it")
    assert r == f"a {endd}"
    r = gnrdate.periodCaption(None, endd, locale="en")
    assert r == f"to {endd}"

    r = gnrdate.periodCaption(None, None, locale="en")
    assert r == "no period"
    r = gnrdate.periodCaption(None, None, locale="it")
    assert r == "-"
    
def test_toDate():
    dt = datetime.datetime(2010, 4, 8, 10, 30)
    d = datetime.date(2010, 4, 8)
    assert isinstance(gnrdate.toDate(dt), datetime.date)
    assert isinstance(gnrdate.toDate(d), datetime.date)
    assert gnrdate.toDate(dt) == d
    with pytest.raises(ValueError) as excinfo:
        gnrdate.toDate(dict())
    assert "accepts only dates or datetimes" in str(excinfo.value)

    

def test_dateRange():
    dtstart = datetime.datetime(2010, 4, 1)
    dtstop = datetime.datetime(2010, 4, 10)
    expected = [datetime.datetime(2010, 4, d) for d in range(1, 10)]
    assert list(gnrdate.dateRange(dtstart, dtstop)) == expected

def test_TimeInterval():
    i = gnrdate.TimeInterval('8:30-10:30')
    assert str(i) == '8:30-10:30'
    assert repr(i) == "TimeInterval('8:30-10:30')"
    assert i.start == datetime.time(8, 30)
    assert i.stop == datetime.time(10, 30)
    assert str(gnrdate.TimeInterval(datetime.time(8, 30), datetime.time(10, 30))) == str(i)
    assert str(gnrdate.TimeInterval((datetime.time(8, 30), datetime.time(10, 30)))) == str(i)

    with pytest.raises(ValueError) as excinfo:
        gnrdate.TimeInterval(datetime.time(8,30), datetime.time(10,30), minutes=5)
    assert "please specify either 'start' or 'stop' when specifying 'minutes'" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        gnrdate.TimeInterval(datetime.time(10,30), datetime.time(8,30))
    assert "start must be earlier than stop" in str(excinfo.value)

    r = gnrdate.TimeInterval(start=datetime.time(10,30), stop=None, minutes=5)
    assert str(r) == "10:30-10:35"

    r = gnrdate.TimeInterval(start=i)
    assert str(r) == str(i)
    assert i == r
    assert i != "hello there"

    t1 = gnrdate.TimeInterval("10:30-10:35")
    assert t1 < "10:40-10:50"
    assert "10:30-10:32" in t1
    
    a = r <= i
    a = t1 <= "10:40-10:50"
    

def test_seconds_to_text():
    r = gnrdate.seconds_to_text(0)
    assert r == "0s"

    r = gnrdate.seconds_to_text(10)
    assert r == "10s"

    r = gnrdate.seconds_to_text(60)
    assert r == "1m"

    r = gnrdate.seconds_to_text(100)
    assert r == "1m 40s"

    r = gnrdate.seconds_to_text(23478)
    assert r == "6h 31m 18s"


def test_TimeInterval_alt_construction():
    i = gnrdate.TimeInterval('8:30-10:30')
    i2 = gnrdate.TimeInterval(stop='10:30', minutes=120)
    assert i == i2

def test_TimeInterval_operators():
    ti = gnrdate.TimeInterval
    assert ti('8:30-10:30') == '8:30-10:30'
    assert ti('8:30-10:30') == ti('8:30-10:30')
    assert not (ti('8:30-10:30') != ti('8:30-10:30'))
    assert ti('8:30-10:30') < ti('11:00-12:00')
    assert ti('8:30-10:30') <= ti('11:00-12:00')
    assert not (ti('8:30-10:30') < ti('10:00-12:00'))
    assert      ti('8:30-10:30') <= ti('10:00-12:00')
    assert ti('11:00-12:00') > ti('8:30-10:30')
    assert ti('11:00-12:00') >= ti('8:30-10:30')
    assert not (ti('10:00-12:00') > ti('8:30-10:30'))
    assert      ti('10:00-12:00') >= ti('8:30-10:30')

    assert ti('8:30-10:30') in ti('10:00-12:00')
    assert ti('8:30-10:30') not in ti('11:00-12:00')
    assert ti('8:30-9:30') in ti('8:00-12:00')

def test_TimeInterval_minutes():
    ti = gnrdate.TimeInterval
    i = ti('8:30-9:30')
    assert i.minutes == 60
    i.minutes = 30
    assert ti('8:30-9:00') == i

def test_TimeInterval_overlaps():
    ti = gnrdate.TimeInterval
    assert ti('8:00-10:00').overlaps(ti('14:00-16:00')) == ti.NO_OVERLAP
    assert ti('8:30-10:30').overlaps(ti('9:00-9:30')) == ti.FULLY_CONTAINS
    assert ti('9:00-9:30').overlaps(ti('8:30-10:30')) == ti.FULLY_CONTAINED
    assert ti('8:00-10:00').overlaps(ti('9:00-12:00')) == ti.COVER_LEFT
    assert ti('9:00-12:00').overlaps(ti('8:00-10:00')) == ti.COVER_RIGHT

    t = ti('8:00-10:00')
    assert t.overlaps(t) == ti.FULLY_CONTAINS

def test_TimeInterval_sorted():
    ti = gnrdate.TimeInterval('9:00-10:00')
    tp = gnrdate.TimePeriod('8:00-12:00')
    tp.remove(ti)
    assert tp == gnrdate.TimePeriod('8:00-9:00, 10:00-12:00')
    lst = [ti] + tp.intervals
    assert gnrdate.TimeInterval.sorted(lst) == ['8:00-9:00', '9:00-10:00', '10:00-12:00']

def test_TimePeriod():
    p = gnrdate.TimePeriod('8:30-10:30', '9:30-11:00')
    assert p.intervals == [gnrdate.TimeInterval('8:30-11:00')]
    assert str(p) == '8:30-11:00'
    p.add(gnrdate.TimeInterval('14:00-16:00')) # non-overlapping => add
    assert str(p) == '8:30-11:00, 14:00-16:00'
    p.remove(gnrdate.TimeInterval('10:30-12:00')) # overlapping => reduce existing interval
    assert str(p) == '8:30-10:30, 14:00-16:00'
    p.remove(gnrdate.TimeInterval('12:00-13:00')) # non-overlapping => noop
    assert str(p) == '8:30-10:30, 14:00-16:00'
    p.remove(gnrdate.TimeInterval('14:00-16:00')) # fully overlapping => remove
    assert str(p) == '8:30-10:30'

def test_TimePeriod_complex():
    p = gnrdate.TimePeriod('8:00-12:00', '16:00-20:00')
    print("p=", p)
    for i in ('8:00-9:00', '9:30-10:00', '10:00-11:30', '16:00-16:30', '17:00-18:00', '18:00-19:00', '19:00-20:00'):
        print("removing", i)
        p.remove(i)
        print("p=", p)
    assert str(p) == '9:00-9:30, 11:30-12:00, 16:30-17:00'

def test_TimePeriod_complex_attributes():
    iv1 = gnrdate.TimeInterval('8:00-12:00')
    iv1.name = 'morning'
    iv2 = gnrdate.TimeInterval('16:00-20:00')
    iv2.name = 'afternoon'
    p = gnrdate.TimePeriod(iv1, iv2)
    print("p=", p)
    for i in ('8:00-9:00', '9:30-10:00', '10:00-11:30', '16:00-16:30', '17:00-18:00', '18:00-19:00', '19:00-20:00'):
        print("removing", i)
        p.remove(i)
        print("p=", p)
    assert str(p) == '9:00-9:30, 11:30-12:00, 16:30-17:00'
    assert p.intervals[0].name == 'morning'
    assert p.intervals[1].name == 'morning'
    assert p.intervals[2].name == 'afternoon'

def test_TimePeriod_sequence():
    p = gnrdate.TimePeriod('8:30-10:30', '16:00-20:00')
    assert len(p) == 2
    assert str(p[0]) == '8:30-10:30'
    assert str(p[1]) == '16:00-20:00'
    it = iter(p)
    assert str(next(it)) == '8:30-10:30'
    assert str(next(it)) == '16:00-20:00'

def test_TimePeriod_TimePeriod():
    tp = gnrdate.TimePeriod
    p = tp('8:30-10:30', '16:00-20:00')
    p.add(tp('10:00-12:00', '13:00-16:00'))
    assert str(p) == '8:30-12:00, 13:00-20:00'
    p.remove(tp('10:00-16:00'))
    assert str(p) == '8:30-10:00, 16:00-20:00'
    p1 = tp('8:30-10:30', '16:00-20:00')
    p2 = tp('8:30-10:30', '16:00-20:00')
    assert p1 == p2
    p3 = tp('8:30-10:30', '16:00-18:00')
    assert p1 != p3

def test_TimePeriod_BugAtEnd():
    tp = gnrdate.TimePeriod
    p = tp('8:00-12:00')
    p.remove('10:00-12:00')
    assert str(p) == '8:00-10:00'

def test_monthStart():
    r = gnrdate.monthStart(2024,1)
    assert r == datetime.date(2024,1,1)

    r = gnrdate.monthStart(2024,1, datetime.date(2025,3,17))
    assert r == datetime.date(2025,3,1)

def test_dateLastYear():
    r = gnrdate.dateLastYear(None)
    assert not r
    
    r = gnrdate.dateLastYear(datetime.date(2024,1,2))
    assert r == datetime.date(2023,1,2)

    r = gnrdate.dateLastYear(datetime.date(2024,2,29))
    assert r == datetime.date(2023,2,28)
    r = gnrdate.dateLastYear(datetime.date(2025,2,28))
    assert r == datetime.date(2024,2,29)

def test_dayIterator():
    r = gnrdate.dayIterator("2024-01-01;2024-03-01")
    assert datetime.date(2024,1,18) in r
    r = gnrdate.dayIterator("2024-01-01;2024-03-01", asDate=False)
    assert datetime.datetime(2024,1,18,0,0) in r

    
if __name__ == "__main__":
    test_TimePeriod_BugAtEnd()
