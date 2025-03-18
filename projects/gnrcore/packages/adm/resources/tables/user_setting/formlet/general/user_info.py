from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import metadata

info = {
    "code":'user_info',
    "caption":"!![en]Profile",
    "iconClass":'user',
    "priority":0,
}

class Formlet(BaseComponent):
    py_requires='th/th:TableHandler'
    def flt_main(self,pane):
        bc = pane.borderContainer(datapath='#FORM.user_form')
        bc.contentPane(region='center').thFormHandler(table='adm.user',formId='user_info_form',startKey=self.db.currentEnv.get('user_id'),
                                                    formResource='FormFromUserInfo')

