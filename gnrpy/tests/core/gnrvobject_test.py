from gnr.core import gnrvobject
from gnr.core.gnrbag import Bag

def test_vobject():
    
    x = Bag()
    x['n.family']='Smith'
    x['n.given']='Jeff'
    x['n.additional']='G.'
    x['fn.fn']='Jeff Smith'
    x['nickname.nickname']='Eddie'
    x['bday.bday']='1961-10-21'
    x['org.org']='Goodsoftware Pty Ltd'
    x.setItem('email.email','jeffsmith@me.com', param_list=['Home','type=INTERNET','type=pref'])
    x.addItem('email.email','jeffsmith@mac.com', param_list=['Work','type=INTERNET'])
    x['adr.street']='32 Smith Waters Rd'
    x['adr.city']='Kincumber'
    x['adr.code']='2251'
    x['adr.country']='Australia'
    x.setItem('tel.tel','02 4332 0368', param_list=['Home','type=pref'])
    x.addItem('tel.tel','0421 232 249', param_list=['CELL'])
    x.setItem('url.url','02 4332 0368', param_list=['Work'])

    c = gnrvobject.VCard(x)
    ser = c.doserialize()
    pp = c.doprettyprint()
