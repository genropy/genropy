import gnr.app.gnrapp as ga


app_name = 'gnrdocker'
app = ga.GnrApp('gnrdocker')

def test_nullloader():
    import sys
    a = ga.NullLoader()
    r = a.load_module('sys')
    assert r == sys
    r = a.load_module('babbala')
    assert r == None

def test_ApplicationCache():
    ac = ga.ApplicationCache()
    assert ac.application is None
    assert len(ac.cache.items()) == 0

    ac = ga.ApplicationCache(app)
    assert ac.application.instanceName == app_name

    ac.setItem(1, "one")
    assert len(ac.cache.items()) == 1

    r = ac.getItem(1)
    assert r == "one"

    assert ac.expiredItem(1) == False
    
    ac.updatedItem(1)
    assert len(ac.cache.items()) == 0

    assert ac.expiredItem(1) == True

def test_GnrMixinObj():
    mo = ga.GnrMixinObj()
