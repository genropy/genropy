from gnr.core import gnrnumber as gn
import decimal

def test_decimalRound():
    res = gn.decimalRound(17.382)
    assert res == decimal.Decimal('17.38')
    
    res = gn.decimalRound(17.382, places=3)
    assert res == decimal.Decimal('17.382')
    
    res = gn.decimalRound(17.382, places=1, rounding=decimal.ROUND_UP)
    assert res == decimal.Decimal('17.4')


def test_floatToDecimal():

    res = gn.floatToDecimal(None)
    assert res is None

    res = gn.floatToDecimal(17.352)
    assert res == decimal.Decimal("17.352")

    res = gn.floatToDecimal(17.352, places=2)
    assert res == decimal.Decimal("17.35")


def test_calculateMultiPerc():
    # FIXME: this function is not used, apparently
    # and I'm wondering what it could be used for - CRG
    res = gn.calculateMultiPerc(None)
    assert res is None
    res = gn.calculateMultiPerc("10+100")
    assert res == decimal.Decimal('100.00')


def test_partitionTotals():
    # FIXME: same as above. maybe it's black magic?
    res = list(gn.partitionTotals([1,2,3], [10,70,20]))
    assert res[0][0] == decimal.Decimal('0.10')

    res = list(gn.partitionTotals("1234", [10,70,20]))
    assert res[0][0] == decimal.Decimal('123.4')
    
