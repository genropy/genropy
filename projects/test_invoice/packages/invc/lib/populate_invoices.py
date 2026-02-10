from gnr.app.gnrapp import GnrApp
from random import randint
from datetime import date, timedelta
from decimal import Decimal

class Populator(object):

    basi_qta = dict(PV=0,NG=15,GD=100)
    max_fatture_giorno = 10

    def __init__(self,app):
        self.app = app
        self.db = db = app.db
        self.tbl_invoice = db.table('invc.invoice')
        self.tbl_invoice_row = db.table('invc.invoice_row')
        self.tbl_customer = db.table('invc.customer')
        self.tbl_product = db.table('invc.product')
        data_ultima_fattura = self.tbl_invoice.query('max($date) as max_date').fetch()[0]['max_date']
        if data_ultima_fattura:
            anno, mese, giorno =data_ultima_fattura.split('-')
            data_ultima_fattura = date(int(anno),int(mese),int(giorno))
        self.prodotti = self.tbl_product.query('*,@tipo_iva_codice.aliquota as aliquota_prodotto').fetch()
        self.clienti = self.tbl_customer.query().fetch()
        self.len_prodotti = len(self.prodotti)
        self.len_clienti = len(self.clienti)
        start_date = date(2015,1,1) if not data_ultima_fattura else max(date(2015,1,1),data_ultima_fattura)
        print start_date, data_ultima_fattura
        end_date = date.today()
        day_adder = timedelta(days=1)
        d = start_date
        self.dates = []
        while d<=end_date:
            if d.weekday()<5:
                self.dates.append(d)
            d = d + day_adder
        

    def crea_riga(self, fattura_id, base_qta):
        record_riga = dict(fattura_id=fattura_id)
        prodotto = self.prodotti[randint(0,self.len_prodotti-1)]
        qta = base_qta*randint(0,5)+randint(0,base_qta)+randint(1,10)
        record_riga['aliquota_iva'] = prodotto['aliquota_prodotto']
        record_riga['quantita'] = qta
        record_riga['prodotto_id'] = prodotto['id']
        record_riga['prezzo_unitario'] = prodotto['prezzo_unitario']
        record_riga['prezzo_totale'] = prodotto['prezzo_unitario'] * qta
        record_riga['iva'] = record_riga['prezzo_totale'] * record_riga['aliquota_iva'] / Decimal(100)

        self.tbl_invoice_row.insert(record_riga)

    def crea_fattura(self, cliente, data):
        record_fattura = dict(cliente_id=cliente['id'], data=data)
        base_qta = self.basi_qta[cliente['cliente_tipo_codice']]
        self.tbl_invoice.insert(record_fattura)
        for _ in range(randint(1,8)): 
            self.crea_riga(record_fattura['id'], base_qta)
        

    def popola(self):
        for data in self.dates:
            for _ in range(randint(0,self.max_fatture_giorno)):
                cliente = self.clienti[randint(0,self.len_clienti-1)]
                self.crea_fattura(cliente,data)
        self.db.commit()

if __name__ == '__main__':
    sb = GnrApp('sandbox')
    pop = Populator(sb)
    pop.popola()
