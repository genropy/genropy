import pytz
import datetime
from decimal import Decimal

from gnr.core.gnrbag import Bag
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



