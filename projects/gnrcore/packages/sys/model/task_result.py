# encoding: utf-8


class Table(object):

    def config_db(self, pkg):
        tbl =  pkg.table('task_result', pkey='id',name_long='!!Task log')
        self.sysFields(tbl)
        tbl.column('task_id',size='22',name_long='!!Task ID').relation('sys.task.id', mode='foreignkey',relation_name='logs')
        tbl.column('result','X',name_long='!!result') # varchar(40)
        tbl.column('result_time',dtype='DH',name_long='!!Result Time') # date
        tbl.column('start_time',dtype='DH',name_long='!!Start Time') # date
        tbl.column('end_time',dtype='DH',name_long='!!Start Time') # date
        tbl.column('is_error','B',name_long='!!Is Error')

        
        # dtype -> sql
        #   C       char (can be omitted; you have to specify its size)
        #   D       date
        #   DH      datetime
        #   H       time
        #   I       integer
        #   L       long integer
        #   R       float
        #   T       text (can be omitted; you must not specify its size)
        #   X       XML/Bag