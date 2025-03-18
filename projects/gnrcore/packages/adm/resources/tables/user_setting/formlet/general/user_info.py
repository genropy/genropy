from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import metadata

info = {
    "code":'user_info',
    "caption":"!![en]User info",
    "iconClass":'user',
    "priority":0,
    "legacy_path":"adm.userinfo"
}

class Formlet(BaseComponent):
    py_requires='th/th:TableHandler'
    def flt_main(self,pane):
        bc = pane.borderContainer(datapath='#FORM.user_form')
        bc.contentPane(region='top',height='30px',background='orange')
        bc.contentPane(region='center')
        #.thFormHandler(table='adm.user',startKey=self.db.currentEnv.get('user_id'),
        #                    formResource='FormFromUserInfo')

