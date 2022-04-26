# encoding: utf-8


class Table(object):

    def sysRecord_ORGN_AGENT(self):
        username='ORGN_AGENT' 
        self.db.deferToCommit(self.linkTagToOrgnAgent,username=username,_deferredId='ORGN_AGENT')
        return self.newrecord(username=username,md5pwd=self.newPkeyValue())


    def linkTagToOrgnAgent(self,username=None,**kwargs):
        tag_id = self.db.table('adm.htag').sysRecord('ORGN_AGENT')['id']
        self.db.table('adm.user_tag').insert({'tag_id':tag_id,'user_id':self.sysRecord('ORGN_AGENT')['id']})
