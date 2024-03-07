#!/usr/bin/env python
# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('prov_test', pkey='sigla', name_long='Provincia',
                         rowcaption='$nome,$sigla:%s (%s)',caption_field='sigla',lookup=True)
        tbl.column('sigla', size='2', readOnly=True, name_long='!![it]Sigla', indexed=True,validate_notnull=True,
                    validate_len='2',validate_case='u')
        tbl.column('regione', size='3', name_long='!![it]Regione',validate_notnull=True).relation('glbl.regione.sigla',
                                                                        relation_name='prov_test',
                                                                        eager_one=True)
        tbl.column('nome', size=':128', name_long='!![it]Nome', indexed=True,validate_notnull=True)
        tbl.column('codice_istat', size='3', name_long='!![it]Codice Istat')
        
    def importer_find_regions_from_name(self, reader): 
        regioni = self.db.table('glbl.regione').query(columns='$sigla,$nome').fetchAsDict('nome') 
        for row in reader(): 
            if row['reg']: 
                 regione_sigla = regioni[row['reg']]['sigla'] 
            else: 
                 regione_sigla = None 
            new_provincia = self.newrecord(regione=regione_sigla, **row) 
            self.insert(new_provincia) 
        self.db.commit()