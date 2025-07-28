from gnr.core import gnrbasetask as gbt 

def test_GnrBaseTask():
    t = gbt.GnrBaseTask("page1")
    assert t.page == "page1"
    assert t.do() == None
