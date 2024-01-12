import pytest
from builtins import str
import datetime
import socket, os
import gnr.core.gnrbag as bm
from gnr.core.gnrbag import Bag, BagNode, BagResolver


def setup_module(module):
    module.BAG_DATA = os.path.join(os.path.dirname(__file__), 'data/testbag.xml')

class TestBasicBag(object):
    def setup_class(cls):
        cls.mybag = Bag(BAG_DATA)

    def test_setItem_addItem(self):
        b = Bag()
        b['name'] = 'John'
        b['surname'] = 'Doe'
        b['birthday'] = datetime.date(1974, 11, 23)
        b['phone'] = Bag()
        b['phone'].setItem('office', 555450210)
        b.setItem('phone.home', 555345670, private=True)
        b.setItem('phone.mobile', 555230450, sim='vadophone', fbplayer='gattuso')
        b.addItem('phone.mobile', 444230450, sim='tom') #add is used for multiple keys
        #b.toXml('data/testbag.xml')

        assert b == self.mybag

    def test_fillFromUrl(self):
        b = Bag('https://www.genropy.org/feed/')
        assert b['rss.channel.title'] == 'Genropy'

    def test_fillFromXml(self):
        b = Bag("<name>John</name>")
        assert b['name'] == 'John'

    def test_fillFromBag(self):
        c = Bag(self.mybag)
        assert c == self.mybag

    def test_fillFromDict(self):
        b = Bag({'a': 3, 'k': Bag({'n': 9})})
        assert b['a'] == 3
        assert b['k.n'] == 9

    def test_fillFromListTuple(self):
        b = Bag([('s', 3), ('a', 5), ('m', Bag([('k', 8)]))])
        assert b['s'] == 3
        assert b['#1'] == 5
        assert b['m.k'] == 8

    def test_toXml(self):
        b = Bag(self.mybag.toXml())
        assert b == self.mybag

    def test_in(self):
        assert 'name' in Bag(BAG_DATA)

    def test_getItem(self):
        assert self.mybag['phone.home'] == 555345670
        assert self.mybag['#1'] == 'Doe'
        assert self.mybag['phone.#3'] == 444230450
        assert self.mybag['phone.#sim=tom'] == 444230450

    def test_setItemPos(self):
        b = Bag({'a': 1})
        b.setItem('b', 2)
        b.setItem('c', 3)
        b.setItem('d', 4)
        b.setItem('e', 5, _position='<')
        assert b['#0'] == 5
        b.setItem('f', 6, _position='<c')
        assert b['#3'] == 6
        b.setItem('g', 7, _position='<#3')
        assert b['#3'] == 7

    def test_attributes(self):
        #set & get
        b = Bag(BAG_DATA)
        b.setAttr('phone.home', private=False)
        assert not b.getAttr('phone.home', 'private')
        b.setAttr('phone.home', private=True, test='is a test')
        assert b['phone.home?test'] == 'is a test' #diverso dalla documentazione track
        assert b.getAttr('phone.#sim=vadophone', 'fbplayer') == 'gattuso'
        assert b['phone.#sim=vadophone?fbplayer'] == 'gattuso'
        b.delAttr('phone.home', 'test')
        assert not b['phone.home?test']

    def test_update(self):
        b = Bag(BAG_DATA)
        c = Bag()
        c.setItem('hobbie.sport', 'soccer', role='forward')
        c.setItem('name', 'John K.')
        b.update(c)
        assert b['name'] == 'John K.'
        assert b.getAttr('hobbie.sport', 'role') == 'forward'

    def test_sort(self):
        b = Bag({'d': 1, 'z': 2, 'r': 3, 'a': 4})
        b.sort()
        assert b['#0'] == 4
        b.sort('#k:d')
        assert b['#0'] == 2
        b.sort('#v:a')
        assert b['#0'] == 1
        b.sort('#v:d')
        assert b['#0'] == 4

    def test_keys(self):
        k = list(self.mybag.keys())
        print(k)
        assert k == [u'name', u'surname', u'birthday', u'phone']

    def test_values(self):
        v = list(self.mybag.values())
        assert v[0] == 'John'

    def test_items(self):
        i = list(self.mybag.items())
        assert i[0][1] == 'John'

    def test_iterators(self):
        pass

    def test_sum(self):
        b = Bag()
        b.setItem('a', 3, k=10)
        b.setItem('b', 7, k=4)
        c = b.sum()
        assert c == 10
        c = b.sum('#a.k') #it can sums the result of a digest with the same param
        # you can sum only int
        assert c == 14

    def test_normalizeItemPath(self):
        res = bm.normalizeItemPath(("a", ".b", ".c"))
        assert res == "('a', '_b', '_c')"
        res = bm.normalizeItemPath("babbala")
        assert res == 'babbala'
        res = bm.normalizeItemPath("babbala.ragazzo")
        assert res == 'babbala.ragazzo'

        class PathStrangeClass(object):
            def __init__(self, string):
                self.string = string

            def __str__(self):
                return self.string

        test_path = PathStrangeClass("babbala.ragazzo")

        res = bm.normalizeItemPath(test_path)
        assert res == 'babbala_ragazzo'

    def test_BagNodeInternals(self):
        b = Bag()
        bn = BagNode(b, "testnode", 10, _attributes=dict(test1=2, test2=1))
        assert "test1" in bn.attr
        assert bn.attr.get('test2') == 1

        assert str(bn) == "BagNode : testnode"
        assert repr(bn) == "BagNode : testnode at {}".format(id(bn))
        assert bn.tag == "testnode"
        assert bn.label == "testnode"
        bn.setLabel("testnodelabel")
        assert bn.getLabel() == "testnodelabel"

        res = bn._get_fullpath()
        assert res == None

        bn.parentbag = b
        assert bn.parentbag == b

        bn2 = BagNode(b, "testnode2", "hellohellohello", validators=dict(length="10,20",
                                                                        inList="hellohellohello,bubu"))

        assert len(bn2._validators) == 2
        b2 = Bag()
        b2.parent = b
        bn2.parentbag = b2
        res = bn2.fullpath
        print(res)
        
        with pytest.raises(bm.BagValidationError) as excinfo:
            bn = BagNode(b, "testnode3", "hello", validators=dict(length="10,20"))
        assert "Value hello too short" in str(excinfo.value)

        with pytest.raises(bm.BagValidationError) as excinfo:
            bn = BagNode(b, "testnode4", "hello", validators=dict(length="1,3"))
        assert "Value hello too long" in str(excinfo.value)

        with pytest.raises(bm.BagValidationError) as excinfo:
            bn = BagNode(b, "testnode5", 1, validators=dict(case="lower"))
        assert "not a string value 1" in str(excinfo.value)
        
        assert False

        
    def test_BagAsXml(self):
        bax = bm.BagAsXml("babbala")
        assert bax.value == "babbala"

    def test_BagDeprecatedCall(self):
        e = bm.BagDeprecatedCall("ab", "cb")
        try:
            raise e
        except Exception as e:
            assert e.errcode == "ab"
            assert e.message == "cb"
        
    def test_digest(self):
        result = self.mybag.digest()
        assert result[0][0] == 'name'
        myattr = self.mybag['phone'].digest('#a')
        assert myattr[2]['fbplayer'] == 'gattuso'
        result = self.mybag.digest('phone:#a.sim,#v', condition=lambda node: node.getAttr('sim') is not None)
        assert result == [('vadophone', 555230450), ('tom', 444230450)]

    def test_analyze(self):
        """docstring for test_analyze"""
        pass

    def test_has_key(self):
        assert 'name' in self.mybag

    def test_iterators(self):
        ik = iter(self.mybag.keys())
        assert next(ik) == 'name'
        iv = iter(self.mybag.values())
        next(iv)
        assert next(iv) == 'Doe'
        ii = iter(self.mybag.items())
        assert next(ii) == ('name', 'John')

    def test_pop(self):
        b = Bag(BAG_DATA)
        b.pop('phone.office')
        assert b != self.mybag

    def test_clear(self):
        b = Bag(BAG_DATA)
        b.clear()
        assert list(b.items()) == []

    def test_copy(self):
        b = self.mybag.copy()
        assert b == self.mybag and b is not self.mybag

    def test_getNode(self):
        b = self.mybag.getNode('phone')
        assert isinstance(b, BagNode)
        assert isinstance(b.getValue(), Bag)

    def test_getNodeByAttr(self):
        b = self.mybag.getNodeByAttr('sim', 'tom')
        assert isinstance(b, BagNode)
        assert b.getValue() == 444230450

    def test_fullpath(self):
        b = Bag()
        b['just.a.simple.test'] = 123
        assert b.fullpath == None
        bag = b['just.a.simple']
        assert isinstance(bag, Bag)
        assert bag.fullpath == None

        b.setBackRef()
        assert b['just.a.simple'].fullpath == 'just.a.simple'

class TestBagTrigger(object):
    def setup_class(cls):
        cls.mybag = Bag(BAG_DATA)
        cls.updNodeValue = False
        cls.updNodeAttr = False
        cls.delNode = False
        cls.insNode = False

        def onUpdate(node=None, pathlist=None, oldvalue=None, evt=None, **kwargs):
            """docstring for onUpdate"""
            if evt == 'upd_value':
                TestBagTrigger.updNodeValue = True
            elif evt == 'upd_attrs':
                TestBagTrigger.updNodeAttr = True

        def onDelete(node=None, pathlist=None, ind=None, **kwargs):
            """docstring for onDelete"""
            TestBagTrigger.delNode = True

        def onInsert(pathlist=None, **kwargs):
            """docstring for onInsert"""
            TestBagTrigger.insNode = True

        cls.mybag.subscribe(1, update=onUpdate, insert=onInsert, delete=onDelete)

    def test_updTrig(self):
        """docstring for test_updTrig"""
        self.mybag['name'] = 'Jack'
        assert self.updNodeValue is True and self.updNodeAttr is False
        self.updNodeValue = False
        self.mybag.setAttr('phone.home', private=False)
        assert self.updNodeValue is False and self.updNodeAttr is True

    def test_insTrig(self):
        self.mybag['test.ins'] = 'hello'
        assert self.insNode is True

    def test_delTrig(self):
        self.mybag.pop('phone.office')
        assert self.delNode is True

class TestBagResolver(object):
    def setup_class(cls):
        cls.mybag = Bag(BAG_DATA)
        cls.mybag['connection.info'] = MyResolver()

    def test_load(self):
        """docstring for test_load"""
        print(self.mybag['connection.info.hostname'] == socket.gethostname())


class TestBagFormula(object):
    def setup_class(cls):
        cls.mybag = Bag(BAG_DATA)

class MyResolver(BagResolver):
    """docstring for MyResolver"""
    classKwargs = {'cacheTime': 500,
                   'readOnly': True,
    }
    classArgs = ['hostname', 'id']

    def load(self):
        """load is re-implemented for every resolver subclass"""
        result = Bag()
        try:
            result['hostname'] = socket.gethostname()
            result['ip'] = socket.gethostbyname(result['hostname'])
        except:
            result['hostname'] = 'localhost'
            result['ip'] = 'unknown'

        result['pid'] = os.getpid()
        result['user'] = os.getenv('USER')
        result['ID'] = result['ip'] + '-' + str(result['pid']) + '-' + result['user']
        return result

def testToTree():
    b = Bag()
    b['alfa'] = Bag(dict(number=1, text='group1', title='alfa', date=datetime.date(2010, 0o5, 10)))
    b['beta'] = Bag(dict(number=1, text='group2', title='beta', date=datetime.date(2010, 0o5, 0o5)))
    b['gamma'] = Bag(dict(number=2, text='group1', title='gamma', date=datetime.date(2010, 0o5, 10)))
    b['delta'] = Bag(dict(number=2, text='group2', title='delta', date=datetime.date(2010, 0o5, 0o5)))
    treeBag = b.toTree(group_by=('number', 'text'), caption='title', attributes=('date', 'text'))

    expectedStr =\
"""0 - (Bag) 1: 
    0 - (Bag) group1: 
        0 - (None) alfa: None  <date='2010-05-10' text='group1'>
    1 - (Bag) group2: 
        0 - (None) beta: None  <date='2010-05-05' text='group2'>
1 - (Bag) 2: 
    0 - (Bag) group1: 
        0 - (None) gamma: None  <date='2010-05-10' text='group1'>
    1 - (Bag) group2: 
        0 - (None) delta: None  <date='2010-05-05' text='group2'>"""

    assert str(treeBag) == expectedStr
    treeBag2 = b.toTree(group_by='number,text', caption='alfa', attributes=('date', 'text'))
    assert treeBag == treeBag2
