# encoding: utf-8
from gnr.core.gnrbag import Bag

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('user_setting', pkey='identifier',pkey_columns='user_id,setting_code', name_long='User setting', name_plural='User setting',caption_field='')
        self.sysFields(tbl,id=False)
        tbl.column('user_id',size='22', group='_', name_long='User'
                    ).relation('adm.user.id', relation_name='settings', mode='foreignkey', onDelete='cascade')
        tbl.column('setting_code', size=':20', name_long='Setting code')
        tbl.column('setting_data', dtype='X', name_long='Setting data')
        tbl.column('identifier',size=':42',name_long='Setting identifier')
    
    def getSettingData(self,setting_code=None,user_id=None):
        user_id = user_id or self.db.currentEnv.get('user_id')

        result = Bag()
        if setting_code:
            return Bag(self.readColumns(columns='$setting_data',where='$user_id=:uid AND $setting_code=:sc',uid=user_id,sc=setting_code))
        else:
            #faccio una bag di tutti i setting dell'utente
            return

    def getCurrentSettings(self):
        return self.query(where='$user_id=:env_user_id').fetchAsDict('setting_code')

    def defaultValues(self):
        return dict(user_id=self.db.currentEnv.get('user_id'))