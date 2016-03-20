# encoding: utf-8

class Table(object):
    def config_db(self,pkg):
        tbl =  pkg.table('annotation',pkey='id',name_long='Annotation',
                            name_plural='Annotations',caption_field='annotation_caption',
                            order_by='$__ins_ts')
        self.sysFields(tbl,user_upd=True)
        tbl.column('rec_type',size='2',values='AN:[!!Annotation],AC:[!!Action]')
        #belong to annotation
        tbl.column('author_user_id',size='22',group='_',name_long='User').relation('adm.user.id',relation_name='annotations',onDelete='raise')

        tbl.column('description',name_long='!!Description')
        tbl.column('annotation_type_id',size='22',name_long='!!Annotation type',group='_').relation('annotation_type.id',mode='foreignkey', onDelete='raise')
        tbl.column('annotation_fields',dtype='X',name_long='!!Annotation Fields',subfields='annotation_type_id')
        
        #belong to actions
        tbl.column('parent_annotation_id',size='22' ,group='_',name_long='!!Parent annotation').relation('annotation.id',relation_name='orgn_related_actions',mode='foreignkey',onDelete='cascade')
        tbl.column('action_type_id',size='22',name_long='!!Action type',group='_').relation('action_type.id',mode='foreignkey', onDelete='raise')
        tbl.column('action_fields',dtype='X',name_long='!!Action Fields',subfields='action_type_id')
        tbl.column('assigned_user_id',size='22',group='*',name_long='!!User').relation('adm.user.id',relation_name='orgn_actions',onDelete='raise')
        tbl.column('assigned_tag',size=':50',name_long='!!User Tag')
        tbl.column('priority',size='1',name_long='!!Priority',values='L:[!!Low],M:[!!Medium],H:[!!High]')
        tbl.column('days_before',dtype='I',name_long='!!Days before',name_short='D.Before')
        tbl.column('date_due',dtype='D',name_long='!!Date due',indexed=True)
        tbl.column('time_due',dtype='H',name_long='!!Time due',indexed=True)
        tbl.column('done_ts',dtype='DH',name_long='!!Done ts',indexed=True)
        tbl.column('linked_table',name_long='!!Linked table')
        tbl.column('linked_entity',name_long='!!Linked entity')
        tbl.column('linked_fkey',name_long='!!Linked fkey')

        tbl.aliasColumn('assigned_username','@assigned_user_id.username',name_long='!!Assigned username')
        tbl.formulaColumn('annotation_caption',"""CASE WHEN rec_type='AC' 
                                                 THEN @action_type_id.description || '-' || $assigned_to
                                                 ELSE @annotation_type_id.description END
                                                    """,name_long='!!Annotation')
        tbl.formulaColumn('annotation_background',"COALESCE(@action_type_id.background_color,@annotation_type_id.background_color)",name_long='!!Background',group='*')
        tbl.formulaColumn('annotation_color',"COALESCE(@action_type_id.color,@annotation_type_id.color)",name_long='!!Foreground',group='*')

        tbl.formulaColumn('assigned_to',"""COALESCE($assigned_username,$assigned_tag,'unassigned')""",name_long='Assigment')
        tbl.formulaColumn('connected_description',"'override me'")
        tbl.formulaColumn('_assignment_base',
                                """($rec_type ='AC' AND ( CASE WHEN $assigned_user_id IS NOT NULL THEN  $assigned_user_id=:env_user_id
                                    WHEN $assigned_tag IS NOT NULL THEN $assigned_by_tag IS TRUE
                                   ELSE TRUE END))""",
                                dtype='B',group='_')
        tbl.formulaColumn("assigned_by_tag","""(',' || :env_userTags || ',' LIKE '%%,'|| COALESCE($assigned_tag,'') || ',%%')""",
                        dtype='B')

        tbl.pyColumn('template_cell',dtype='A',group='_',py_method='templateColumn', template_name='action_tpl',template_localized=True)

    def trigger_onInserting(self,record_data=None):
        record_data['author_user_id'] = self.db.currentEnv.get('user_id')
        for colname,colobj in self.columns.items():
            related_table = colobj.relatedTable()
            if colname.startswith('le_') and record_data[colname]:
                fkey = record_data[colname]
                record_data['linked_table'] = related_table.fullname
                record_data['linked_fkey'] = fkey
                record_data['linked_entity'] = record_data['linked_entity'] or self.linkedEntityName(related_table)

    def formulaColumn_pluggedFields(self):
        desc_fields = []
        assigments_restrictions = ["$_assignment_base"]
        for colname,colobj in self.columns.items():
            if colname.startswith('_assignment'):
                assigments_restrictions.append(colname)
            elif colname.startswith('le_'):
                related_table = colobj.relatedTable()
                if related_table and related_table.column('orgn_description') is not None:
                    desc_fields.append('@%s.orgn_description' %colname)
        description_formula = "COALESCE(%s)" %','.join(desc_fields) if desc_fields else "'NOT PLUGGED'"
        assigment_formula = ' AND '.join(assigments_restrictions)
        return [dict(name='connected_description',sql_formula=description_formula),
                dict(name='plugin_assigment',sql_formula='(%s)' %assigment_formula,dtype='B',name_long='Assigned to me')]

    def getLinkedEntities(self):
        result = []
        for colname,colobj in self.columns.items():
            if colobj.attributes.get('linked_entity'):
                result.extend(colobj.attributes['linked_entity'].split(','))
        return ','.join(result)

    def linkedEntityName(self,tblobj):
        joiner = tblobj.relations.getNode('@annotations').attr['joiner']
        pkg,tbl,fkey = joiner['many_relation'].split('.')
        restrictions = self.db.table('orgn.annotation').column(fkey).attributes.get('restrictions')
        if restrictions:
            restrictions = ','.join([r.split(':')[0] for r in restrictions.split(',')])
            return restrictions[0]
        else:
            return tblobj.name

