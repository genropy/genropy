from gnr.web.gnrbaseclasses import BaseComponent


class Form(BaseComponent):
    def th_form(self,form):
        form.record



class View(BaseComponent):
    def th_struct(self,struct):
        r=struct.view().rows()
        r.fieldcell('setting_code')


