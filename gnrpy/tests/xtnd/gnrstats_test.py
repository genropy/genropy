import pytest
from gnr.core.gnrbag import Bag
from gnr.xtnd import gnrstats as gs

class TestGnrStats():
    """
    Testing for gnr.xtnd.gnrstas module
    """
    @classmethod
    def setup_class(cls):
        cls.ts = gs.TotalizeSelection()
        cls.test_bag = Bag(dict(a=Bag(pkey="a", b=dict(pkey="two",d="four"))))
    def test_riwPreprocess(self):
        assert self.ts.rowPreprocess(None) is None

    def test_sortKey(self):
        r = self.ts.sortKey([1,2,3], [3,2,1])
        assert r == "3_2"

    def test_anag_base(self):
        totals = ["a", "b", "c"]
        r = self.ts.anag_base([1,2,3], totals, 2)
        assert totals[2] == 3
        r = self.ts.anag_base([1,2,3], totals, 0)
        assert totals[0] == 1

    def test_fillFilter(self):
        dpath = "a"
        fltquery = "WHERE"
        r1, r2 = self.ts.fillFilter(self.test_bag, dpath, fltquery)
        assert r1[0] is None
        assert r1[1] is None
        assert r2 == f"AND {fltquery}"
        
        r1, r2 = self.ts.fillFilter(self.test_bag, "b", fltquery)
        assert r1 is None
        assert r2 == ''

