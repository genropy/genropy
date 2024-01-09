from gnr.core import gnrdict as gd

def test_dictExtract():
    test_dict = dict(prefix1_a=1, prefix1_b=2, prefix2_a=3)

    res = gd.dictExtract(test_dict, "prefix1")
    assert "_a" in res
    assert "_b" in res
    assert res["_a"] == 1

    res = gd.dictExtract(test_dict, "prefix1", slice_prefix=False)
    assert "_a" not in res
    assert "prefix1_a" in res
    assert "prefix1_b" in res
    assert "prefix2_a" not in res


def test_FakeDict():
    res = gd.FakeDict()
    res['babbala'] = "ti proteggo"
    assert 'babbala' in res


def test_GnrDict():
    source_dict = dict(sd1=1, sd2=2)
    res = gd.GnrDict(source_dict, p1=1, p2=2)
    assert 'sd1' in res
    assert 'sd2' in res
    assert 'p1' in res
    assert 'p2' in res

    source_data = [("sd1", 1), ("sd2", 2)]
    res = gd.GnrDict(source_data, p1=1, p2=2)
    assert 'sd1' in res
    assert 'sd2' in res
    assert 'p1' in res
    assert 'p2' in res

    keys = list(res)
    del(res['sd1'])
    assert 'sd1' not in res

    i = res.get('sd2')
    assert i == 2
    i = res.get('sd3', 3)
    assert i == 3
    
    assert res.get("babbala") == None
    assert res['p1'] == 1


    # label convert

    res['#1'] = "foobar"
    assert res['p1'] == "foobar"

    res['#1000'] = "goober"
    assert "#1000" in res
    assert res['#1000'] == "goober"
    r1 = res._label_convert("#100.0")
    assert r1 == "#100.0"

    # items
    items = list(res.items())
    assert ('sd2',2) in items

    # keys
    k = res.keys()
    assert "#1000" in k
    assert "sd2" in k
    assert "sd1" not in k


    # index

    i = res.index("#1000")
    assert i == 3
    i = res.index("babbala")
    assert i == -1

    # values

    vals = res.values()
    assert 2 in vals
    assert "goober" in vals
    assert 1 not in vals

    # pop

    p = res.pop("#1000")
    assert "#1000" not in res
    assert p == "goober"

    p_nonexist = res.pop("abc123")
    assert p_nonexist == None
    p_nonexist = res.pop("abc123", 3.141592)
    assert p_nonexist == 3.141592

    # copy
    res2 = res.copy()
    assert "#1000" not in res
    assert id(res) is not id(res2)
    
    # clear
    i = res.clear()
    assert i == None
    assert len(res.keys()) == 0

    # str
    assert str(res) == "{}"

    # update

    res.update(dict(sd1=1))
    assert "sd1" in res

    res.update(dict(sd2=None), removeNone=True)
    assert "sd2" not in res

    # reverse
    res.update(dict(sd2=2))
    assert res[list(res)[0]] == 1
    res.reverse()
    assert res[list(res)[0]] == 2

    # popitem
    r = res.popitem()
    assert r[0] == 'sd1'
    assert 'sd1' not in res
    assert res['sd2'] == 2

    # setdefault
    res.setdefault("sd3", d=3)
    assert 'sd3' in res
    assert res['sd3'] == 3

    # __add__
    ares = res + dict(ad1=1, ad2=2)
    assert 'ad1' not in res
    assert 'ad1' in ares
    assert 'sd3' in res

    # __sub__
    sres = res - dict(ad1=1, ad2=2, sd3=3)
    assert 'sd3' not in sres
    assert 'sd2' in sres
    assert 'ad1' not in sres
    assert 'ad2' not in sres

    # iterkeys
    assert 'sd2' in res.iterkeys()
    assert 'sd3' in res.iterkeys()

    # itervalues
    assert 2 in res.itervalues()
    assert 3 in res.itervalues()
    assert 1 not in res.itervalues()

    # iteritems
    assert ('sd2', 2) in res.iteritems()
    assert ('sd3', 3) in res.iteritems()
    assert ('sd3', 2) not in res.iteritems()

    # sort
    res.sort()
    assert res.keys()[0] == 'sd2'
    assert res.keys()[1] == 'sd3'
    res.sort(reverse=True)
    assert res.keys()[0] == 'sd3'
    assert res.keys()[1] == 'sd2'


def test_GnrNumericDict():
    sd = gd.GnrNumericDict({1:"hello", 2:"there"}, sd1=1,sd2=3)
    assert 1 in sd
    assert "sd1" in sd
    i = list(sd)
    assert "there" in i
