import pytz
import datetime
from decimal import Decimal
from gnr.core.gnrbag import Bag
import gnr.core.gnrstring as gs

class TestTypedJSON(object):
    def __init__(self) -> None:
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

    def test_toJSONValues(self,v=None):
        return gs.toTypedJSON(v or self.values)

    def test_fromJSONValues(self,j):
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
            if result is False:
                print('ERROR',original,'DIFF',restored)
        return result
        
        



if __name__ ==  '__main__':
    ttj = TestTypedJSON()
    val = ttj.values
    #original_data = [{'date':val['val_D'],'foo':33},{'spam':8,'zuz':[1,2,{'bar':'ccc','uden':['agua','fuego',88]}]},Decimal('44.3'),False] #[val['val_D'],38]
    dumped_original = ttj.test_toJSONValues()
    restored = ttj.test_fromJSONValues(dumped_original)
    print('restored',restored)
    result = ttj.compare(ttj.values,restored)
    print('result',result)


