# -*- coding: utf-8 -*-
from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"
        
    def test_0_validatePassword(self,pane):
        """First test description"""
        pane.textbox(value='^.testpwd', lbl='Password', validate_notnull=True)
        pane.button('test').dataRpc(self.checkPwd, value='=.testpwd', _if='value', _onResult='console.log(result);')
    
    @public_method
    def checkPwd(self, value=None,**kwargs):
        user = self.db.table('adm.user').record(username=self.user).output('bag')
        return self.application.validatePassword(value, user=user)
    