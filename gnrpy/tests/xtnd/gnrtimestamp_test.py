import datetime
import pytest
from gnr.xtnd import gnrtimestamp as gt

class TestGnrTimestamp():
    def test_gnrtimestamp(self):
        t = gt.GnrTimeStamp()
        assert t.get(station=1, base=100) is not None
        with pytest.raises(ZeroDivisionError):
            t.get(station=2, base=0)

        v = t.get(station=1, base=10)
        assert len(v) == 10

        now = datetime.datetime.now()
        d = t.getDate(v)
        assert d.year == now.year
        assert d.month == now.month
        assert d.hour == 0
        assert d.minute == 0
