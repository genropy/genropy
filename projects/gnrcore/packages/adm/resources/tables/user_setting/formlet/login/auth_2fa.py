from gnr.web.gnrbaseclasses import BaseComponent

info = {
    "caption":"!![en]Authentication 2fa",
}

class Formlet(BaseComponent):
    py_requires='th/th:TableHandler'
    def flt_main(self,pane):
        bc = pane.borderContainer(datapath='#FORM.user_form')
        bc.contentPane(region='center').thFormHandler(table='adm.user',formId='user_2fa_form',startKey=self.db.currentEnv.get('user_id'),
                                                    formResource='FormFrom2FaSettings')

