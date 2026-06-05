# encoding: utf-8

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires='gnrcomponents/externalcall:BaseRpc'

    @public_method
    def get_dbstores(self,*args,**kwargs):
        if not self.db.multidomain:
            #in multidb not multidomain task table is only on mainstore
            return 
        return self.db.dbstores
    
    @public_method
    def get_tasks(self,*args,**kwargs):
        if not self.db.multidomain:
            #in multidb not multidomain task table is only on mainstore
            return self.db.table('sys.task').findTasks()
        with self.db.tempEnv(storename='*'):
            return self.db.table('sys.task').findTasks()
