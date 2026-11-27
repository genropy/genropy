import pytest

import datetime
import re
import socket, os
from decimal import Decimal
import gnr.core.gnrbag as bm
from gnr.core.gnrbag import Bag, BagNode, BagResolver, BagCbResolver


BAG_DATA = os.path.join(os.path.dirname(__file__), 'data/testbag.xml')

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
        b = Bag('https://www.genropy.org/sitemap.xml')
        assert b['urlset.url']

    def test_fillFromXml(self):
        b = Bag("<name>John</name>")
        assert b['name'] == 'John'

    def test_template_kwargs(self):
        source = "<name>{TESTVAR}</name>"
        test_kwargs = dict(TESTVAR="admin", TESTVAR2="admin2")
        b = Bag(source, _template_kwargs=test_kwargs)
        assert b['name'] == "admin"

    def test_template_kwargs_from_file(self, tmp_path):
        source = tmp_path / 'instanceconfig.xml'
        source.write_text("<?xml version='1.0' encoding='UTF-8'?><GenRoBag><name>{TESTVAR}</name></GenRoBag>")
        b = Bag(str(source), _template_kwargs=dict(TESTVAR="admin"))
        assert b['name'] == "admin"

    def test_template_kwargs_unresolved(self, tmp_path):
        source = tmp_path / 'instanceconfig.xml'
        source.write_text("<?xml version='1.0' encoding='UTF-8'?>"
                          "<GenRoBag><name>{MISSINGVAR}</name><code>{\"a\": 1}</code></GenRoBag>")
        b = Bag(str(source), _template_kwargs=dict(TESTVAR="admin"))
        assert b['name'] == "{MISSINGVAR}"
        assert b['code'] == '{"a": 1}'

    def test_template_kwargs_xml_escaped(self, tmp_path):
        secret = 'p&ss<w>"\'rd'
        source = tmp_path / 'instanceconfig.xml'
        source.write_text("<?xml version='1.0' encoding='UTF-8'?>"
                          "<GenRoBag><db password=\"{SECRET}\" user='{SECRET}'>{SECRET}</db></GenRoBag>")
        b = Bag(str(source), _template_kwargs=dict(SECRET=secret))
        assert b['db'] == secret
        assert b.getAttr('db', 'password') == secret
        assert b.getAttr('db', 'user') == secret
        
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

    def test_update_preservePattern(self):
        import re
        b = Bag()
        b.setItem('name', '$placeholder', caption='${title}')
        b.setItem('code', '{template}', label='{dynamic}')
        b.setItem('value', 'normal', desc='static')

        c = Bag()
        c.setItem('name', 'NewName', caption='New Caption')
        c.setItem('code', 'NewCode', label='New Label')
        c.setItem('value', 'updated', desc='new desc')

        b.update(c, preservePattern=re.compile(r'^[\$\{]'))

        # values starting with $ or { are preserved
        assert b['name'] == '$placeholder'
        assert b['code'] == '{template}'
        # attributes starting with $ or { are preserved
        assert b.getAttr('name', 'caption') == '${title}'
        assert b.getAttr('code', 'label') == '{dynamic}'
        # values and attributes not matching are updated
        assert b['value'] == 'updated'
        assert b.getAttr('value', 'desc') == 'new desc'

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

        # FIXME: this raises an exception, is it correct?
        #res = bn2.fullpath
        
        with pytest.raises(bm.BagValidationError) as excinfo:
            bn = BagNode(b, "testnode3", "hello", validators=dict(length="10,20"))
        assert "Value hello too short" in str(excinfo.value)

        with pytest.raises(bm.BagValidationError) as excinfo:
            bn = BagNode(b, "testnode4", "hello", validators=dict(length="1,3"))
        assert "Value hello too long" in str(excinfo.value)

        with pytest.raises(bm.BagValidationError) as excinfo:
            bn = BagNode(b, "testnode5", 1, validators=dict(case="lower"))
        assert "not a string value 1" in str(excinfo.value)


        
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

    def test_deepcopy_keeps_dotted_labels(self):
        b = Bag()
        b.setItem(['a.b'], Bag())
        b['#0'].setItem(['c.d'], 7)
        c = b.deepcopy()
        assert c.keys() == ['a.b']
        assert c['#0'].keys() == ['c.d']
        assert c['#0.#0'] == 7
        assert c['#0'] is not b['#0']

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

    def test_getLeaves(self):
        b = Bag()
        b['a.b.c'] = 1
        b['a.d'] = 2
        b['e'] = 3
        assert b.getLeaves() == [('a.b.c', 1), ('a.d', 2), ('e', 3)]
        assert [p for p, n in b.getIndex()] == [['a'], ['a', 'b'], ['a', 'b', 'c'],
                                                ['a', 'd'], ['e']]

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
        result['ID'] = f"{result['ip']}-{result['pid']}-{result['user']}"
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


def clinicalRecord(rischio='2', parto=None, peso=62.5, unit='cm'):
    record = Bag()
    record['gravidanza.UM'] = datetime.date(2026, 3, 1)
    record['gravidanza.LivelloRischio'] = rischio
    if parto:
        record['gravidanza.ModalitaParto'] = parto
    if peso is not None:
        record['misure.Peso'] = peso
    record.setItem('misure.Altezza', 165, unit=unit)
    return record


def visits(*outcomes):
    result = Bag()
    for k, outcome in enumerate(outcomes):
        result.addItem('visita', Bag(dict(esito=outcome)), n=k)
    return result


def compact(records):
    return [(r['event'], r['path'], r['changed_attribute'], r['oldvalue'], r['newvalue'])
            for r in records]


def unstyled(html):
    return re.sub(r' style="[^"]*"', '', html)


class TestBagDiff(object):
    def test_clinical_record(self):
        old = clinicalRecord()
        new = clinicalRecord(rischio='3', parto='cesareo', peso=None, unit='mm')
        assert compact(old.diff(new)) == [
            ('changed', 'gravidanza.LivelloRischio', None, '2', '3'),
            ('added', 'gravidanza.ModalitaParto', None, None, 'cesareo'),
            ('changed', 'misure.Altezza', 'unit', 'cm', 'mm'),
            ('removed', 'misure.Peso', None, 62.5, None),
        ]

    def test_record_fields(self):
        records = clinicalRecord().diff(clinicalRecord(unit='mm'))
        assert records == [dict(event='changed', path='misure.Altezza', label='Altezza',
                                changed_attribute='unit', oldvalue='cm', newvalue='mm',
                                attributes=dict(unit='mm'))]

    def test_equal_bags(self):
        assert clinicalRecord().diff(clinicalRecord()) == []
        assert len(clinicalRecord().getDiffBag(clinicalRecord())) == 0
        assert Bag().diff(Bag()) == []

    def test_node_order_is_not_a_change(self):
        old = Bag()
        old['a'] = 1
        old['b'] = 2
        new = Bag()
        new['b'] = 2
        new['a'] = 1
        assert old.diff(new) == []

    def test_none_is_an_empty_bag(self):
        record = clinicalRecord()
        assert compact(Bag().diff(None)) == []
        records = Bag().diff(record)
        assert [(r['event'], r['path']) for r in records] == \
            [('added', 'gravidanza'), ('added', 'misure')]
        assert [(r['event'], r['path']) for r in record.diff(None)] == \
            [('removed', 'gravidanza'), ('removed', 'misure')]

    def test_not_a_bag(self):
        with pytest.raises(TypeError):
            Bag().diff({'a': 1})

    def test_whole_subbag_added_is_one_record(self):
        old = clinicalRecord()
        new = clinicalRecord()
        new.setItem('ecografia', Bag(dict(settimana=12, esito='regolare')), operatore='X')
        records = old.diff(new)
        assert len(records) == 1
        record = records[0]
        assert (record['event'], record['path'], record['attributes']) == \
            ('added', 'ecografia', dict(operatore='X'))
        assert record['newvalue'] == new['ecografia']
        record['newvalue']['esito'] = 'changed'
        assert new['ecografia.esito'] == 'regolare'

    def test_whole_subbag_removed_is_one_record(self):
        old = clinicalRecord()
        new = clinicalRecord()
        new.pop('misure')
        records = old.diff(new)
        assert compact(records) == [('removed', 'misure', None, old['misure'], None)]
        assert records[0]['oldvalue'] is not old['misure']

    def test_typed_values(self):
        old = Bag(dict(a='2', b=1, c=Decimal('1.50'), d=datetime.date(2026, 1, 1), e=None))
        new = Bag(dict(a=2, b=True, c=Decimal('1.5'), d=datetime.datetime(2026, 1, 1), e=''))
        assert compact(old.diff(new)) == [
            ('changed', 'a', None, '2', 2),
            ('changed', 'b', None, 1, True),
            ('changed', 'd', None, datetime.date(2026, 1, 1), datetime.datetime(2026, 1, 1)),
            ('changed', 'e', None, None, ''),
        ]

    def test_bag_replaced_by_scalar(self):
        old = clinicalRecord()
        new = clinicalRecord()
        new['misure'] = 'non rilevate'
        assert compact(old.diff(new)) == \
            [('changed', 'misure', None, old['misure'], 'non rilevate')]
        assert compact(new.diff(old)) == \
            [('changed', 'misure', None, 'non rilevate', old['misure'])]

    def test_attribute_changes(self):
        old = Bag()
        old.setItem('pressione', 120, unit='mmHg', metodo='manuale')
        new = Bag()
        new.setItem('pressione', 125, unit='mmHg', strumento='digitale')
        assert compact(old.diff(new)) == [
            ('changed', 'pressione', 'metodo', 'manuale', None),
            ('changed', 'pressione', 'strumento', None, 'digitale'),
            ('changed', 'pressione', None, 120, 125),
        ]

    def test_attribute_change_on_a_bag_node(self):
        old = clinicalRecord()
        new = clinicalRecord(rischio='3')
        new.setAttr('gravidanza', valutata=True)
        assert compact(old.diff(new)) == [
            ('changed', 'gravidanza', 'valutata', None, True),
            ('changed', 'gravidanza.LivelloRischio', None, '2', '3'),
        ]

    def test_duplicated_labels(self):
        old = Bag()
        old['visite'] = visits('ok', 'controllo')
        new = Bag()
        new['visite'] = visits('ok', 'ricovero', 'ok')
        records = old.diff(new)
        assert compact(records) == [
            ('changed', 'visite.#1.esito', None, 'controllo', 'ricovero'),
            ('added', 'visite.#2', None, None, new['visite.#2']),
        ]
        for record in records:
            assert new[record['path']] == record['newvalue']

    def test_duplicated_labels_removed(self):
        old = Bag()
        old['visite'] = visits('ok', 'controllo', 'ok')
        new = Bag()
        new['visite'] = visits('ok', 'controllo')
        records = old.diff(new)
        assert compact(records) == [('removed', 'visite.#2', None, old['visite.#2'], None)]
        assert old[records[0]['path']] == records[0]['oldvalue']

    def test_duplicated_label_among_unique_siblings(self):
        old = Bag()
        old['nome'] = 'A'
        old.addItem('nota', 'prima')
        new = Bag()
        new['nome'] = 'B'
        new.addItem('nota', 'prima')
        new.addItem('nota', 'seconda')
        assert compact(old.diff(new)) == [
            ('changed', 'nome', None, 'A', 'B'),
            ('added', '#2', None, None, 'seconda'),
        ]

    def test_dotted_label_added(self):
        new = Bag()
        new.setItem(['a.b'], 7)
        records = Bag().diff(new)
        assert compact(records) == [('added', '#0', None, None, 7)]
        assert records[0]['label'] == 'a.b'
        assert new[records[0]['path']] == 7

    def test_dotted_label_changed(self):
        old = Bag()
        old['nome'] = 'A'
        old.setItem(['a.b'], 1)
        new = Bag()
        new['nome'] = 'A'
        new.setItem(['a.b'], 2)
        records = old.diff(new)
        assert compact(records) == [('changed', '#1', None, 1, 2)]
        assert old[records[0]['path']] == 1
        assert new[records[0]['path']] == 2

    def test_dotted_label_nested(self):
        old = Bag()
        old['x'] = Bag()
        old['x'].setItem(['a.b'], 1)
        old['x'].setItem(['c.d'], 3)
        new = Bag()
        new['x'] = Bag()
        new['x'].setItem(['a.b'], 2)
        records = old.diff(new)
        assert compact(records) == [
            ('changed', 'x.#0', None, 1, 2),
            ('removed', 'x.#1', None, 3, None),
        ]
        assert new['x.#0'] == 2
        assert old['x.#1'] == 3

    def test_dotted_label_subtree_added(self):
        new = Bag()
        new['grp'] = Bag()
        new['grp'].setItem(['a.b'], 7)
        records = Bag().diff(new)
        assert [r['event'] for r in records] == ['added']
        assert records[0]['path'] == 'grp'
        assert records[0]['newvalue'].keys() == ['a.b']
        assert records[0]['newvalue']['#0'] == 7
        assert Bag().getDiffBag(new)['grp'].keys() == ['a.b']

    def test_dotted_label_subtree_removed(self):
        old = Bag()
        old['grp'] = Bag()
        old['grp'].setItem(['a.b'], 7)
        records = old.diff(Bag())
        assert [r['event'] for r in records] == ['removed']
        assert records[0]['path'] == 'grp'
        assert records[0]['oldvalue'].keys() == ['a.b']
        assert records[0]['oldvalue']['#0'] == 7
        assert old.getDiffBag(Bag())['grp'].keys() == ['a.b']

    def test_label_with_question_mark(self):
        old = Bag()
        old.setItem(['ok?'], False)
        new = Bag()
        new.setItem(['ok?'], True)
        new.setItem(['why?'], 'no')
        records = old.diff(new)
        assert compact(records) == [
            ('changed', '#0', None, False, True),
            ('added', '#1', None, None, 'no'),
        ]
        for record in records:
            assert new[record['path']] == record['newvalue']

    def test_paths_follow_each_side(self):
        old = Bag()
        old.addItem('x', 1)
        old.addItem('x', Bag(dict(v=1)))
        new = Bag()
        new.addItem('y', 0)
        new.addItem('x', 1)
        new.addItem('x', Bag(dict(w=2)))
        records = old.diff(new)
        assert compact(records) == [
            ('added', 'y', None, None, 0),
            ('added', '#2.w', None, None, 2),
            ('removed', '#1.v', None, 1, None),
        ]
        assert new['#2.w'] == 2
        assert old['#1.v'] == 1

    def test_xml_roundtrip(self):
        old = Bag(clinicalRecord().toXml())
        new = Bag(clinicalRecord(rischio='3', parto='cesareo', peso=None, unit='mm').toXml())
        assert compact(old.diff(new)) == compact(clinicalRecord().diff(
            clinicalRecord(rischio='3', parto='cesareo', peso=None, unit='mm')))
        assert old.diff(new)[0]['oldvalue'] == '2'

    def test_resolvers_are_not_called(self):
        calls = []

        def load():
            calls.append(1)
            return Bag(dict(a=1))

        old = Bag()
        old.setItem('remote', BagCbResolver(load))
        new = Bag()
        new.setItem('remote', BagCbResolver(load))
        new['local'] = 1
        assert compact(old.diff(new)) == [('added', 'local', None, None, 1)]
        assert calls == []

    def test_node_diff(self):
        old = clinicalRecord(rischio='2').getNode('gravidanza')
        new = clinicalRecord(rischio='3', parto='cesareo').getNode('gravidanza')
        assert [r['path'] for r in old.diff(new)] == \
            ['gravidanza.LivelloRischio', 'gravidanza.ModalitaParto']
        assert [r['path'] for r in old.diff(new, path='rev1', otherpath='rev2')] == \
            ['rev2.LivelloRischio', 'rev2.ModalitaParto']
        assert old.diff(clinicalRecord(rischio='2').getNode('gravidanza')) == []

    def test_diff_bag(self):
        old = clinicalRecord()
        new = clinicalRecord(rischio='3', parto='cesareo', peso=None, unit='mm')
        new['ecografia.settimana'] = 12
        tree = old.getDiffBag(new)
        assert tree.keys() == ['gravidanza', 'misure', 'ecografia']
        assert tree.getAttr('gravidanza') == dict(path='gravidanza')
        assert tree.getAttr('gravidanza.LivelloRischio') == \
            dict(path='gravidanza.LivelloRischio', event='changed', oldvalue='2', newvalue='3')
        assert tree.getAttr('gravidanza.ModalitaParto') == \
            dict(path='gravidanza.ModalitaParto', event='added', newvalue='cesareo')
        assert tree.getAttr('misure.Altezza') == \
            dict(path='misure.Altezza', event='changed', changed_attributes='unit',
                 old_unit='cm', new_unit='mm')
        assert tree.getAttr('misure.Peso') == \
            dict(path='misure.Peso', event='removed', oldvalue=62.5)
        assert tree.getAttr('ecografia') == dict(path='ecografia', event='added')
        assert tree['ecografia.settimana'] == 12
        assert 'UM' not in tree['gravidanza']

    def test_diff_bag_duplicated_labels(self):
        old = Bag()
        old['visite'] = visits('ok', 'controllo')
        new = Bag()
        new['visite'] = visits('ok', 'ricovero', 'ok')
        tree = old.getDiffBag(new)
        assert tree['visite'].keys() == ['visita', 'visita']
        assert tree.getAttr('visite.#0.esito') == dict(path='visite.#1.esito', event='changed',
                                                       oldvalue='controllo', newvalue='ricovero')
        assert tree.getAttr('visite.#1') == dict(path='visite.#2', event='added')

    def test_diff_bag_dotted_labels(self):
        old = Bag()
        old['x'] = Bag()
        old['x'].setItem(['a.b'], 1)
        new = Bag()
        new['x'] = Bag()
        new['x'].setItem(['a.b'], 2)
        new.setItem(['c?d'], 3)
        tree = old.getDiffBag(new)
        assert tree.keys() == ['x', 'c?d']
        assert tree['x'].keys() == ['a.b']
        assert tree.getAttr('x.#0') == dict(path='x.#0', event='changed', oldvalue=1, newvalue=2)
        assert tree.getAttr('#1') == dict(path='#1', event='added', newvalue=3)

    def test_diff_html_clinical_record(self):
        old = clinicalRecord()
        new = clinicalRecord(rischio='3', parto='cesareo', peso=None, unit='mm')
        assert unstyled(old.diffHtml(new)) == (
            '<ul><li>gravidanza<ul>'
            '<li>LivelloRischio: <del>2</del> &rarr; <ins>3</ins></li>'
            '<li>+ ModalitaParto: cesareo</li></ul></li>'
            '<li>misure<ul>'
            '<li>Altezza <span>[unit: <del>cm</del> &rarr; <ins>mm</ins>]</span></li>'
            '<li>&minus; Peso: 62.5</li></ul></li></ul>')

    def test_diff_html_styles(self):
        html = clinicalRecord().diffHtml(clinicalRecord(parto='cesareo', peso=None))
        assert '<li style="color:#1a7f37;text-decoration:none">+ ModalitaParto' in html
        assert '<li style="color:#cf222e;text-decoration:line-through">&minus; Peso' in html

    def test_diff_html_nothing_changed(self):
        assert clinicalRecord().diffHtml(clinicalRecord()) == ''

    def test_diff_html_escapes_labels_and_values(self):
        old = Bag()
        old['nota'] = 'a < b'
        new = Bag()
        new['nota'] = 'a & b'
        assert unstyled(old.diffHtml(new)) == (
            '<ul><li>nota: <del>a &lt; b</del> &rarr; <ins>a &amp; b</ins></li></ul>')

    def test_diff_html_locale(self):
        old = clinicalRecord()
        new = clinicalRecord()
        new['gravidanza.UM'] = datetime.date(2026, 3, 8)
        assert '<del>01/03/26</del> &rarr; <ins>08/03/26</ins>' in unstyled(
            old.diffHtml(new, locale='it'))

    def test_diff_html_same_text_shows_types(self):
        old = Bag(dict(codice='2'))
        new = Bag(dict(codice=2))
        assert unstyled(old.diffHtml(new)) == (
            '<ul><li>codice: <del>2 (str)</del> &rarr; <ins>2 (int)</ins></li></ul>')

    def test_diff_html_subbags_and_duplicated_labels(self):
        old = Bag()
        old['visite'] = visits('ok', 'controllo')
        new = Bag()
        new['visite'] = visits('ok', 'ricovero')
        new['ecografia'] = Bag(dict(settimana=12))
        assert unstyled(old.diffHtml(new)) == (
            '<ul><li>visite<ul><li>visita #1<ul>'
            '<li>esito: <del>controllo</del> &rarr; <ins>ricovero</ins></li></ul></li></ul></li>'
            '<li>+ ecografia: <ul><li>settimana: 12</li></ul></li></ul>')

    def test_diff_html_dotted_labels(self):
        old = Bag()
        old['x'] = Bag()
        old['x'].setItem(['a.b'], 1)
        new = Bag()
        new['x'] = Bag()
        new['x'].setItem(['a.b'], 2)
        new.setItem(['c?d'], 3)
        assert unstyled(old.diffHtml(new)) == (
            '<ul><li>x<ul><li>a.b #0: <del>1</del> &rarr; <ins>2</ins></li></ul></li>'
            '<li>+ c?d #1: 3</li></ul>')
