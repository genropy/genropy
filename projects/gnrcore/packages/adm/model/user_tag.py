# encoding: utf-8

from builtins import object
class Table(object):
    def config_db(self, pkg):
        tbl =  pkg.table('user_tag',pkey='id',name_long='!!User tag',
                      name_plural='!!User tags')
        self.sysFields(tbl)
        tbl.column('group_code',size=':15',name_long='!!Group').relation('group.code',relation_name='tags',mode='foreignkey',onDelete='cascade')
        tbl.column('user_id',size='22',group='_',name_long='User',_sendback=True).relation('user.id', mode='foreignkey', 
                                                                            onDelete='cascade',relation_name='tags')
        tbl.column('tag_id',size='22',group='_',name_long='Tag id').relation('htag.id', mode='foreignkey', onDelete='cascade',
                                                                          relation_name='users')
        tbl.aliasColumn('user',relation_path='@user_id.username')
        tbl.aliasColumn('fullname',relation_path='@user_id.fullname')
        tbl.aliasColumn('email',relation_path='@user_id.email')
        tbl.aliasColumn('tag_description',relation_path='@tag_id.description')
        tbl.aliasColumn('tag_note',relation_path='@tag_id.note')
        tbl.aliasColumn('linked_table',relation_path='@tag_id.linked_table', static=True)
        tbl.aliasColumn('require_2fa','@tag_id.require_2fa')
        tbl.aliasColumn('tag_code','@tag_id.authorization_tag')
        tbl.formulaColumn('user_or_group',"COALESCE($user,$group_code)")

        #tbl.aliases(relation='@user_id',user='username')
    
    def trigger_onInserted(self, record_data):
        self.setUserAuthTags(record_data)
    
    def trigger_onUpdated(self, record_data, old_record):
        self.setUserAuthTags(record_data)

    def trigger_onDeleted(self, record):
        if self.currentTrigger.parent:
            return
        self.setUserAuthTags(record)

    def setUserAuthTags(self,record):
        user_id = record.get('user_id')
        if not user_id:
            return

        self.db.deferToCommit(self.db.table('adm.user').onChangedTags, user_id=user_id, _deferredId=user_id)
        
