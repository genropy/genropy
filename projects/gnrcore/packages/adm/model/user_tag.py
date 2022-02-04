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
        tbl.aliasColumn('tag_code',relation_path='@tag_id.hierarchical_code')
        tbl.aliasColumn('tag_description',relation_path='@tag_id.description')
        tbl.aliasColumn('tag_note',relation_path='@tag_id.note')
        tbl.aliasColumn('linked_table',relation_path='@tag_id.linked_table', static=True)
        tbl.formulaColumn('user_or_group',"COALESCE($user,$group_code)")

        #tbl.aliases(relation='@user_id',user='username')
    
    def trigger_onInserted(self, record_data):
        self.setUserAuthTags(record_data)
        self.linkedTableCallback(record=record_data, evt='i')
    
    def trigger_onUpdated(self, record_data, old_record):
        self.setUserAuthTags(record_data)
        self.linkedTableCallback(record=record_data,old_record=old_record, evt='u')

    def trigger_onDeleted(self, record):
        self.setUserAuthTags(record)
        self.linkedTableCallback(record=record, evt='d')

    def linkedTableCb(self, record=None, old_record=None, evt=None):
        if record['linked_table']:
            linked_tbl = self.db.table(record['linked_table'])
            if hasattr(linked_tbl, 'userTagCb'):
                linked_tbl.userTagCb(self, user_id=record['user_id'], evt=evt)
    
    def setUserAuthTags(self,record):
        user_id = record.get('user_id')
        if not user_id:
            return
        rows = self.query(where='$user_id=:u_id',u_id=user_id,columns='$tag_code',addPkeyColumn=False).fetch()
        tags = ','.join([r['tag_code'] for r in rows])
        self.db.table('adm.user').batchUpdate(dict(auth_tags=tags),where='$id=:pkey',pkey=user_id)


        
