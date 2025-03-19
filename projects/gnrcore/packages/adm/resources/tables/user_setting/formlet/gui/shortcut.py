from gnr.web.gnrbaseclasses import BaseComponent

info=dict(code='shortcut',caption='!![en]Keyboard shortcuts',editing_path="sys.shortcuts")

class Formlet(BaseComponent):
    def flt_main(self,pane):
        fb = pane.formlet(cols=1)
        fb.comboBox(value='^.save',values='f1,alt+s,cmd+s',lbl='!![en]Save',placeholder='f1')
        fb.comboBox(value='^.reload',values='f9,alt+r',lbl='!![en]Reload',placeholder='f9')
        fb.comboBox(value='^.dismiss',values='alt+up,alt+q',lbl='!![en]Dismiss',placeholder='alt+up')
        fb.comboBox(value='^.next_record',values='alt+right',lbl='!![en]Next record',placeholder='alt+right')
        fb.comboBox(value='^.prev_record',values='alt+left',lbl='!![en]Prev record',placeholder='alt+left')
        fb.comboBox(value='^.last_record',values='ctrl+alt+right',lbl='!![en]Last record',placeholder='ctrl+alt+right')
        fb.comboBox(value='^.first_record',values='ctrl+alt+left',lbl='!![en]First record',placeholder='ctrl+alt+left')
        fb.comboBox(value='^.jump_record',values='alt+j',lbl='!![en]Jump record',placeholder='alt+j')

