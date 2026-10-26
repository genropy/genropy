from gnr.core.gnrbag import Bag

ESCAPED = 'x &lt;15a &amp; <b>y</b>'


def test_value_roundtrip_keeps_entities():
    b = Bag()
    b['t'] = ESCAPED
    assert Bag(b.toXml())['t'] == ESCAPED


def test_attribute_roundtrip_keeps_entities():
    b = Bag()
    b.setItem('a', 'v', cap=ESCAPED)
    assert Bag(b.toXml()).getAttr('a', 'cap') == ESCAPED


def test_tag_label_roundtrip():
    b = Bag()
    b['a&lt;b'] = 1
    assert Bag(b.toXml()).keys() == ['a&lt;b']


def test_client_xml_cdata_and_attributes():
    source = ("<?xml version='1.0' encoding='UTF-8'?><GenRoBag>"
              "<t cap=\"&amp;lt;15a &lt;b&gt;\"><![CDATA[x &lt;15a <b>y</b>]]></t>"
              "</GenRoBag>")
    b = Bag(source)
    assert b['t'] == 'x &lt;15a <b>y</b>'
    assert b.getAttr('t', 'cap') == '&lt;15a <b>'
