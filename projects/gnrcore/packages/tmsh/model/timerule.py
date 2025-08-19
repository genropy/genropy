# encoding: utf-8


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('timerule', pkey='id', name_long='!![en]Timerule',
                        name_plural='!![en]Timerules',broadcast=True)
        self.sysFields(tbl)
        tbl.column('rule_order', 'L', name_long='!![en]Order')
        tbl.column('is_exception','B', name_long='!![en]Exception')
        tbl.column('on_su', 'B', name_long='!![en]Sunday')
        tbl.column('on_mo', 'B', name_long='!![en]Monday')
        tbl.column('on_tu', 'B', name_long='!![en]Tuesday')
        tbl.column('on_we', 'B', name_long='!![en]Wednesday')
        tbl.column('on_th', 'B', name_long='!![en]Thursday')
        tbl.column('on_fr', 'B', name_long='!![en]Friday')
        tbl.column('on_sa', 'B', name_long='!![en]Saturday')
        tbl.column('am_start_time', 'H', name_long='!![en]Start AM')
        tbl.column('am_end_time', 'H', name_long='!![en]End AM')
        tbl.column('pm_start_time', 'H', name_long='!![en]Start PM')
        tbl.column('pm_end_time', 'H', name_long='!![en]End PM')
        tbl.column('notes', name_long='!![en]Notes')
        tbl.column('deny', 'B', name_long='!![en]Deny rule')
        tbl.column('valid_from', dtype='D', name_long='!![en]Valid from')
        tbl.column('valid_to', dtype='D', name_long='!![en]Valid to')
        tbl.column('month_frequency', size=':2', name_long='!![en]Month frequency')
        tbl.formulaColumn('frequency_name', """CASE 
                                           WHEN #THIS.month_frequency ='1' THEN 'First'
                                           WHEN #THIS.month_frequency ='2' THEN 'Second'
                                           WHEN #THIS.month_frequency ='3' THEN 'Third'
                                           WHEN #THIS.month_frequency ='4' THEN 'Fourth'
                                           WHEN #THIS.month_frequency ='l' THEN 'Last'
                                           WHEN #THIS.month_frequency ='w2' THEN 'Every 2 weeks'
                                           WHEN #THIS.month_frequency ='w3' THEN 'Every 3 weeks'
                                           WHEN #THIS.month_frequency ='w4' THEN 'Every 4 weeks'
                                           ELSE 'Any'
                                           END""")
        tbl.formulaColumn('is_valid', """CASE 
                                          WHEN #THIS.valid_from IS NULL OR #THIS.valid_to IS NULL OR ((#THIS.valid_from <=:env_workdate) AND (#THIS.valid_to>:env_workdate)) THEN true 
                                          ELSE false END""", dbtype='B',name_long='!![en]Valid')
        tbl.formulaColumn('rule_type',"CASE WHEN #THIS.deny IS true THEN 'deny' ELSE 'normal' END", name_long='!![en]Priority code')
        
    def trigger_onInserting(self, record_data):
        if record_data['is_exception']:
            record_data['valid_to'] = record_data['valid_from']
            weekday = ['mo','tu','we','th','fr','sa','su'][record_data['valid_from'].weekday()]
            record_data['on_%s' %weekday] = True

