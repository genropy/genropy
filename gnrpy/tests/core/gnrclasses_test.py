import pytest
import pytz
import datetime
from decimal import Decimal

from gnr.core.gnrbag import Bag
from gnr.core import gnrclasses
import gnr.core.gnrstring as gs

class TestTypedJSON(object):
    
    def setup_method(self) -> None:
        now = datetime.datetime.now()
        self.values = dict(
            val_I = 42,
            val_L = 29344,
            val_F = 2.4,
            val_B = True,
            val_N = Decimal('3991.44'),
            val_DH = now,
            val_D = now.date(),
            val_H = now.time(),
            val_DHZ = datetime.datetime.now(pytz.utc),
            val_A = 'Foo',
            val_NN = None
        )
        val_X = Bag(self.values)
        val_X.setItem('test_attributes',None,**self.values)
        #self.values['val_X'] = val_X

    def toJSONValues(self,v=None):
        return gs.toTypedJSON(v or self.values)

    def fromJSONValues(self,j):
        return gs.fromTypedJSON(j)

    
    def compare(self,original=None,restored=None):
        if isinstance(original,dict):
            result = {}
            for k,v in restored.items():
                result[k] = self.compare(original[k],v)
        elif isinstance(original,list):
            result = [self.compare(original[idx],v) for idx,v in enumerate(restored)]
        else:
            result = original == restored
        return result
        
    def test_main1(self):
        ttj = self
        val = ttj.values
        dumped_original = ttj.toJSONValues()
        restored = ttj.fromJSONValues(dumped_original)
        assert(ttj.compare(ttj.values,restored))

    def test_main2(self):
        b = Bag()
        ttj = self
        val = ttj.values
        b.addItem('val_D',val['val_D'])
        b.addItem('val_LL',[val['val_D'],val['val_B'],val['val_N']])
        b.addItem('val_ZZ',None,ll=[val['val_D'],val['val_B'],val['val_N']])
        b.addItem('val_ZZ',None,val_D = val['val_D'],val_B = val['val_B'],val_N = val['val_N'])
        x = b.toXml(pretty=True)
        r = Bag(x)
        assert(r==b)



def test_gnrclasscatalog():
    gnrclasses.GnrClassCatalog.convert()
    cc = gnrclasses.GnrClassCatalog()
    cc.addClass(int, "integer")
    res = cc.getEmpty("foo")
    assert res is None
    res = cc.getEmpty("integer")
    assert res is None
    res = cc.getEmpty("BAG")
    assert res.__class__ == Bag

    res = cc.getAlign("BAG")
    assert res == 'L'
    res = cc.getAlign(Bag)
    assert res == 'L'
    res = cc.getAlign(1)
    assert res == 'L'

    res = cc.getClassKey(1)
    assert res == 'integer'
    res = cc.getClass('integer')
    assert res == int

    res = cc.asText(1)
    assert res == '1'
    
    res = cc.asText('integer', translate_cb=lambda x: f'{x} translated')
    assert res == "integer translated"

    res = cc.asText('integer', quoted=True,
                    translate_cb=lambda x: f'{x} translated')
    assert res == '"integer translated"'

    res = cc.quoted('"foobar"')
    assert res == '\'"foobar"\''

    res = cc.isTypedText("foobar")
    assert res == False

    res = cc.isTypedText("foobar::HTML")
    assert res == True
    res = cc.isTypedText("foobar::SARCHIAPONE")
    assert res == False

    res = cc.fromTypedText(1)
    assert res == 1

    res = cc.asTypedText(1, quoted=True)
    assert res == '"1::integer"'

    
    res = cc.asTextAndType(1)
    assert res[0] == '1'
    assert res[1] == 'integer'

    res = cc.asTextAndType(b"asdasdasd")
    assert res[1] == 'T'

    # cover for getType using a GnrClassCatalog.typegetters
    res = cc.getType(datetime.datetime.now())
    assert res == "DH"

    # classes without __safe__
    with pytest.raises(Exception) as excinfo:
        cc.parseClass("gnr.core.gnrbag:Bag")
    assert "Unsecure class" in str(excinfo.value)

    with pytest.raises(Exception) as excinfo:
        cc.parseClass("datetime:datetime")
    assert "Unsecure class" in str(excinfo.value)

    # not a valid input
    with pytest.raises(ValueError) as excinfo:
        cc.parseClass("babbala")
    assert "not enough values to unpack" in str(excinfo.value)

    # valid input, non-existing module/cls
    with pytest.raises(Exception) as excinfo:
        cc.parseClass("colin:ford")
    assert "No module named 'colin'" in str(excinfo.value)

    res = cc.serializeClass(datetime.datetime)
    assert res == "datetime:datetime"

    # parse_float method
    
    res = cc.parse_float("1.10")
    assert res == 1.1

    with pytest.raises(ValueError) as excinfo:
        cc.parse_float("babbala")
    assert "could not convert string to float" in str(excinfo.value)

    res = cc.parse_float("inf")
    assert res is None

    # typegetter_datetime
    res = cc.typegetter_datetime(datetime.datetime.now())
    assert res == "DH"
    res = cc.typegetter_datetime(datetime.datetime.utcnow())
    assert res == "DH"
    res = cc.typegetter_datetime(datetime.datetime.now(pytz.utc))
    assert res == "DHZ"


    # serialize_datetime
    res = cc.serialize_datetime(datetime.datetime(2024,1,4,12,6,39))
    assert "2024-01-04T12:06:39" in res
    res = cc.serialize_datetime(datetime.datetime(2024,1,4,12,6,39, tzinfo=pytz.utc))
    assert "2024-01-04T12:06:39" in res

    # parse_timedelta - apparently, to be removed or to
    # have a real implementation
    with pytest.raises(Exception) as excinfo:
        cc.parse_timedelta("Hello")
    assert str(excinfo.value) is ""

    # serialize_timedelta
    res = cc.serialize_timedelta(datetime.timedelta(days=1))
    assert res == "1 days 00:00:0.000"
    res = cc.serialize_timedelta(datetime.timedelta(seconds=3600))
    assert res == "01:00:0.000"
    res = cc.serialize_timedelta(datetime.timedelta(days=200, seconds=(3600*3)+50))
    assert res == "200 days 03:00:50.000"

    # parse_date
    res = cc.parse_date("2024-01-04")
    assert res.year == 2024 and res.month == 1 and res.day == 4

    res = cc.parse_date("0000-00-00")
    assert res is None

    res = cc.parse_date(None)
    assert res[0] is None and res[1] is None
            
    print(res)
    assert False
