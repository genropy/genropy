from gnr.core.gnrbag import Bag
from gnr.web.gnrbaseclasses import BaseComponent

info = {
    "caption":"!![en]Change password",
}

class Formlet(BaseComponent):
    py_requires='login:LoginComponent'
    def flt_main(self,pane):
        pane.data('change_pwd',Bag())
        fb = pane.formlet(cols=1,datapath='change_pwd')
        fb.passwordTextBox(value='^.current_password',lbl='!!Password')
        fb.passwordTextBox(value='^.password',lbl='!!New password',
                    validate_remote=self.db.table('adm.user').validateNewPassword)
        fb.passwordTextBox(value='^.password_confirm',lbl='!!Confirm password',
                    validate_call='return value==GET .password;',validate_call_message='!!Passwords must be equal')
        
        fb.button('Apply').dataRpc(self.login_changePassword,_fired='^set_new_password',
                    current_password='=.current_password',
                    newusername='=.newusername',
                    password='=.password',password_confirm='=.password_confirm',
                    _if='password==password_confirm',
                    _else="genro.dlg.floatingMessage(_box,{message:'Passwords must be equal',messageType:'error',yRatio:.95})",
                    _onResult="""if(result){
                        genro.dlg.floatingMessage(kwargs._box,{message:'Wrong password',messageType:'error',yRatio:.95});
                        return;
                    }
                    genro.dlg.floatingMessage(this.form.sourceNode,{message:'Password changed',messageType:'message',yRatio:.95});
                    genro.setData('change_pwd',null)""")

