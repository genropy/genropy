
class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('cap', pkey='cap', name_long='CAP', caption_field='descrizione_cap')
        # self.sysFields(tbl)
        tbl.column('cap', size='5', name_long='CAP')
        tbl.column('provincia', size='2', name_long='Provincia', name_short='Prov.'
                   ).relation('glbl.provincia.sigla', relation_name='cap', onDelete='raise')  # mode='foreignkey',

        tbl.column('geocoords', name_long='Coordinate Geocoder')
        tbl.formulaColumn('geopoint', 'CAST ($geocoords AS point)', group='_')
        tbl.formulaColumn('geolocalizzato', '$geopoint IS NOT NULL', dtype='B', name_long='Geo?')

        tbl.formulaColumn('geospot', 'CAST (:env_spot AS point)', group='_')
        tbl.formulaColumn('distanza_da_punto', """CASE
                                                    WHEN $geocoords IS NULL THEN 9999
                                                    ELSE ($geopoint <@> $geospot)*1.60934
                                                  END""",
                          dtype='N', format='#.0',
                          name_long='Distanza', name_short='Dist.')

        tbl.aliasColumn('regione', '@provincia.regione', name_long='Regione')
        tbl.formulaColumn('descrizione_cap',"$provincia || ' - '||$cap")

