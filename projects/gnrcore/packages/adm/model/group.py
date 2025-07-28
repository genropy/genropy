#!/usr/bin/env python
# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('group', pkey='code', name_long='Group', 
                        name_plural='!!Groups',caption_field='description')
        self.sysFields(tbl, id=False,counter=True)
        tbl.column('code' ,size=':15',name_long='!!Code',unmodifiable=True)
        tbl.column('description' ,name_long='!!Description')
        tbl.column('custom_menu', dtype='X', name_long='!!Custom menu')
        tbl.column('rootpage', name_long='!![en]Root Page')
        tbl.column('require_2fa', dtype='B', name_long='Require 2fa', name_short='2FA')
        tbl.column('no2fa_alternative_group',size=':15', group='_', name_long='Without 2FA'
                    ).relation('adm.group.code', one_one=True, 
                               mode='foreignkey', onDelete='setnull')
        tbl.formulaColumn('group_tags', self.db.adapter.string_agg('#tg',separator=','),
                                                select_tg=dict(columns='$tag_code',where='$group_code=#THIS.code',
                                                               distinct=True,table='adm.user_tag'))
        

    def linkGroupTag(self,group_code=None,tags=None,**kwargs):
        if tags:
            tags = tags.split(',')
        else:
            tags = [group_code]
        for tag in tags:
            tag_id = self.db.table('adm.htag').sysRecord(tag)['id']
            self.db.table('adm.user_tag').insert({'tag_id':tag_id,'group_code':group_code})
