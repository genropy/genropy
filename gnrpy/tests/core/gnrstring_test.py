# -*- coding: utf-8 -*-
from gnr.core import gnrstring
from gnr.core.gnrbag import Bag
import datetime

import pytest

def test_getUntil():
    """docstring for test_getUntil"""
    assert gnrstring.getUntil('teststring', 'st') == 'te'
    assert gnrstring.getUntil('teststring', 'te') == ''
    assert gnrstring.getUntil('teststring', 'te') == ''

def test_getUntilLast():
    """docstring for test_getUntilLast"""
    assert gnrstring.getUntilLast('teststring', 'st') == 'test'
    assert gnrstring.getUntilLast('teststring', 'te') == ''
    assert gnrstring.getUntilLast('teststring', 'co') == ''

def test_getFrom():
    """docstring for test_getFrom"""
    assert gnrstring.getFrom('teststring', 'st') == 'string'
    assert gnrstring.getFrom('teststring', 'te') == 'ststring'
    assert gnrstring.getFrom('teststring', 'co') == ''

def test_getFromLast():
    """docstring for test_getFromLast"""
    assert gnrstring.getFromLast('teststring', 'st') == 'ring'
    assert gnrstring.getFromLast('teststring', 'ng') == ''
    assert gnrstring.getFromLast('teststring', 'co') == ''

def test_wordSplit():
    """docstring for test_wordSplit"""
    assert gnrstring.wordSplit('hello, my dear friend') == ['hello', 'my', 'dear', 'friend']

def splitLast():
    """docstring for splitLast"""
    assert gnrstring.splitLast('hello my dear friend', 'e') == ('hello my dear fri', 'nd')

def getBetween():
    """docstring for getBetween"""
    assert gnrstring.getBetween('teststring', 'st', 'in') == 'str'
    assert gnrstring.getBetween('teststring', 'st', 'te') == ''
    assert gnrstring.getBetween('teststring', 'te', 'te') == ''

def test_like():
    """docstring for test_like"""
    assert gnrstring.like('*dog*', 'adogert', '*')
    assert not gnrstring.like('dog*', 'adogert', '*')
    assert not gnrstring.like('*dog', '*adogert', '*')

def test_filter():
    """docstring for Test_filter"""
    txt = "hello my beautiful princess"
    assert gnrstring.filter(txt, '*my*', '', '*')
    assert not gnrstring.filter(txt, 'my*', '', '*')
    assert gnrstring.filter(txt, '$beauti$', '$cwp$', '$')
    assert gnrstring.filter(txt, include='*my*', wildcard='*')
    print(not gnrstring.filter(txt, exclude='%princess'))

def test_regexDelete():
    """docstring for test_regexDelete"""
    assert gnrstring.regexDelete("hello my beautiful princess", 'utiful') == "hello my bea princess"

def test_templateReplace():
    """docstring for test_templateReplace"""
    assert gnrstring.templateReplace('$foo loves $bar but she loves $aux and not $foo',
                                     {'foo': 'John', 'bar': 'Sandra',
                                      'aux': 'Steve'}) == 'John loves Sandra but she loves Steve and not John'

def test_conditionalTemplate_is_presence_only():
    """``${...}`` only checks that the symbol is present and not None/empty: it never
    compares the symbol's value, whatever that value is."""
    assert gnrstring.templateReplace('${Dear $name, }Hello', {'name': 'John'}) == 'Dear John, Hello'
    assert gnrstring.templateReplace('${Dear $name, }Hello', {'name': 'Anyone'}) == 'Dear Anyone, Hello'
    assert gnrstring.templateReplace('${Dear $name, }Hello', {'name': ''}) == 'Hello'
    assert gnrstring.templateReplace('${Dear $name, }Hello', {'name': None}) == 'Hello'

def test_templateReplace_bag_format_already_branches_on_boolean_and_numeric():
    """The Variables grid's existing ``format`` column already branches on
    dtype-intrinsic states, with no code change: see gnrlocale.localize_boolean
    (boolean) and gnrlocale.localize_number (numeric sign/zero)."""
    b = Bag()
    b.setItem('is_paid', True, format='PAGATA;DA SALDARE', dtype='B')
    b.setItem('is_paid_no', False, format='PAGATA;DA SALDARE', dtype='B')
    b.setItem('amount', 1234.5, format='#,##0.00;(#,##0.00);—', dtype='N')
    b.setItem('amount_zero', 0, format='#,##0.00;(#,##0.00);—', dtype='N')

    assert gnrstring.templateReplace('$is_paid', b) == 'PAGATA'
    assert gnrstring.templateReplace('$is_paid_no', b) == 'DA SALDARE'
    assert gnrstring.templateReplace('$amount', b) == '1,234.50'
    assert gnrstring.templateReplace('$amount_zero', b) == '—'

def test_templateReplace_valuemap_resolves_text_symbol():
    """New: a text/enum symbol picks one of several literal fragments through a
    ``key:label,...,*:default`` value map stored in the same ``format`` column,
    mirroring the client-side objectFromString(valueattr.values)[value] lookup."""
    b = Bag()
    b.setItem('status', 'A', format='A:Approvato,R:Respinto,*:In esame', dtype='T')
    b.setItem('status_unmatched', 'Z', format='A:Approvato,R:Respinto,*:In esame', dtype='T')
    b.setItem('status_no_wildcard', 'Z', format='A:Approvato,R:Respinto', dtype='T')

    assert gnrstring.templateReplace('$status', b) == 'Approvato'
    assert gnrstring.templateReplace('$status_unmatched', b) == 'In esame'
    # no wildcard and no match: falls back to the raw value, unaffected
    assert gnrstring.templateReplace('$status_no_wildcard', b) == 'Z'

def test_valueMapFormat():
    """docstring for test_valueMapFormat"""
    assert gnrstring.valueMapFormat('A:Approvato,R:Respinto,*:In esame', 'A') == 'Approvato'
    assert gnrstring.valueMapFormat('A:Approvato,R:Respinto,*:In esame', 'R') == 'Respinto'
    assert gnrstring.valueMapFormat('A:Approvato,R:Respinto,*:In esame', 'Z') == 'In esame'
    assert gnrstring.valueMapFormat('A:Approvato,R:Respinto', 'Z') is None
    assert gnrstring.valueMapFormat('#,##0.00;(#,##0.00)', '5') is None
    assert gnrstring.valueMapFormat('tf', 'A') is None
    assert gnrstring.valueMapFormat(None, 'A') is None
    assert gnrstring.valueMapFormat('', 'A') is None

def test_valueMapFormat_label_separators():
    # a comma inside a label used to discard the whole map, silently
    assert gnrstring.valueMapFormat('A:Approvato, con riserva,R:Respinto',
                                    'A') == 'Approvato, con riserva'
    assert gnrstring.valueMapFormat('A:Approvato, con riserva,R:Respinto',
                                    'R') == 'Respinto'
    # a colon inside a label is kept: only the first one separates
    assert gnrstring.valueMapFormat('A:Time 10:30', 'A') == 'Time 10:30'
    # the label is stripped like the key
    assert gnrstring.valueMapFormat('A: Approvato,R:Respinto', 'A') == 'Approvato'
    # nothing to rejoin to, so it is not a value map
    assert gnrstring.valueMapFormat('Approvato,R:Respinto', 'A') is None

def test_valueMapFormat_unmatched_value_renders_raw():
    """An unmatched value renders as the value, never as nothing: here the raw
    fallback comes from toText, on the client from valueMapFormat itself."""
    assert gnrstring.toText('M::T', format='A:Approvato,R:Respinto') == 'M'
    b = Bag()
    b.setItem('status', 'M', format='A:Approvato,R:Respinto', dtype='T')
    assert gnrstring.templateReplace('$status', b) == 'M'

def test_valueMapFormat_label_keeps_the_raw_value():
    # %s, the token of the mask column, so a wildcard does not lose the code
    assert gnrstring.valueMapFormat('A:Approvato,R:Respinto,*:Altro [%s]', 'M') == 'Altro [M]'
    assert gnrstring.valueMapFormat('A:Approvato,R:Respinto,*:Altro', 'M') == 'Altro'
    assert gnrstring.valueMapFormat('A:Approvato [%s],R:Respinto', 'A') == 'Approvato [A]'
    assert gnrstring.valueMapFormat('*:%s/%s', 'M') == 'M/M'
    b = Bag()
    b.setItem('status', 'M', format='A:Approvato,*:Altro [%s]', dtype='T')
    assert gnrstring.templateReplace('$status', b) == 'Altro [M]'

def test_valueMapFormat_real_format_strings_fall_through():
    # these do parse as maps; they return None because no value matches a key
    # and no wildcard is declared (localize_img, a time mask)
    assert gnrstring.valueMapFormat('auto:.5', 'A') is None
    assert gnrstring.valueMapFormat('x:34,y:56,z:1', 'A') is None
    assert gnrstring.valueMapFormat('HH:mm', 'A') is None

def test_asDict():
    """docstring for asDict"""
    d = gnrstring.asDict('height=22, weight=73')
    assert d['height'] == '22' and d['weight'] == '73' and isinstance(d, dict)
    d = gnrstring.asDict('height=$myheight, weight=73', symbols={'myheight': 55})
    assert d['height'] == '55' and d['weight'] == '73' and isinstance(d, dict)

def test_stringDict():
    """docstring for test_stringDict"""
    assert gnrstring.stringDict({'height': 22, 'width': 33}) in ['width=33,height=22',
                                                                 'height=22,width=33']

def test_updateString():
    """docstring for test_updateString"""
    assert gnrstring.updateString('I drink cola', 'beer') == 'I drink cola,beer'
    assert gnrstring.updateString('I drink cola', 'beer', ' and ') == 'I drink cola and beer'

def test_makeSet():
    """docstring for test_makeSet"""
    assert  gnrstring.makeSet('a', 'b') == set(['a', 'b'])

def test_splitAndStrip():
    """docstring for test_splitAndStrip"""
    assert gnrstring.splitAndStrip('cola, beer, milk') == ['cola', 'beer', 'milk']
    assert gnrstring.splitAndStrip('cola, beer, milk', n=1) == ['cola', 'beer, milk']
    assert gnrstring.splitAndStrip('cola, beer, milk', fixed=1) == ['cola']
    assert gnrstring.splitAndStrip('cola, beer, milk', fixed=5) == ['cola', 'beer', 'milk', '', '']
    assert gnrstring.splitAndStrip('cola, beer, milk', fixed=-5) == ['', '', 'cola', 'beer', 'milk']
    assert gnrstring.splitAndStrip('cola, beer, milk', fixed=5, n=1) == ['cola', 'beer, milk', '', '', '']

def test_countOf():
    """docstring for test_countOf"""
    assert gnrstring.countOf('hello bello', 'lo') == 2

def test_split():
    """docstring for test_split"""
    assert gnrstring.split('here.you.are') == ['here', 'you', 'are']
    assert gnrstring.split('here/you/are', '/') == ['here', 'you', 'are']
    assert gnrstring.split('here/(you/are)/again', '/') == ['here', '(you/are)', 'again']
    with pytest.raises(ValueError):
        gnrstring.split('(Something is wrong/here', '/')

def test_smartjoin():
    """docstring for test_smartjoin"""
    assert gnrstring.smartjoin(['Hello, dog', 'you', 'are', 'yellow'], ',') == 'Hello\\, dog,you,are,yellow'

def test_smartsplit():
    """docstring for smartsplit"""
    assert gnrstring.smartsplit('Hello\\, dog,you,are,yellow', ',') == ['Hello\\, dog', 'you', 'are', 'yellow']

def test_fromIsoDate():
    """docstring for test_fromIsoDate"""
    assert isinstance(gnrstring.fromIsoDate('1983/01/29'), datetime.date)

def test_toJson():
    res = gnrstring.toJson([{'a': 2}, {'b': 3, 'c': 6}, {'z': 9}])
    assert res in [
        '[{"a": 2}, {"b": 3, "c": 6}, {"z": 9}]',
        '[{"a": 2}, {"c": 6, "b": 3}, {"z": 9}]'
    ]


def test_stringWidth_empty():
    assert gnrstring.stringWidth('', 'Helvetica', 10) == 0.0


def test_stringWidth_known_char():
    # Helvetica 'A' is 667 units at 10pt -> 6.67pt
    assert gnrstring.stringWidth('A', 'Helvetica', 10) == pytest.approx(6.67)


def test_stringWidth_courier_monospaced():
    # Courier is monospaced at 600 units, so two chars = twice one char
    w1 = gnrstring.stringWidth('A', 'Courier', 10)
    w2 = gnrstring.stringWidth('AB', 'Courier', 10)
    assert w2 == pytest.approx(w1 * 2)


def test_stringWidth_unknown_font_falls_back_to_helvetica():
    assert gnrstring.stringWidth('A', 'UnknownFont', 10) == gnrstring.stringWidth('A', 'Helvetica', 10)
        
