# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl =  pkg.table('postcode',name_long='Postcode',name_plural='Postcodes',pkey='id',caption_field='postcode',lookup=False)
        self.sysFields(tbl)
        tbl.column('postcode',size=':10',name_long='postcode',legacy_name='postcode',unique=False,indexed=True)
        tbl.column('suburb',size=':100',name_long='suburb',legacy_name='suburb')
        tbl.column('state',size=':5',name_long='state',legacy_name='state').relation('state.code',relation_name='postcodes',mode='foreignkey')
        tbl.column('lat',name_long='lat',legacy_name='lat')
        tbl.column('lon',name_long='lon',legacy_name='lon')
