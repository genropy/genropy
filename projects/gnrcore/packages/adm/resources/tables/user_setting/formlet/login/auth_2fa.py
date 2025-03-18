from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import metadata

info = {
    "caption":"!![en]Authentication 2fa",
}

class Formlet(BaseComponent):
    def flt_main(self,pane):
        fb = pane.formlet(cols=1)
        fb.button('2fa')