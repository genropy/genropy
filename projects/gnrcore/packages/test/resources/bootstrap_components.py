from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrwebstruct import struct_method

class BootstrapComponents(BaseComponent):

    @struct_method
    def bsCard(self, parent, image=None, title=None, text=None, btn_link=None, btn_text=None, width=None, **kwargs):
        card_box = parent.div(_workspace=True, _class='card', width=width or '18rem', **kwargs)
        card_box.img(src=image, _class="card-img-top")
        card_body = card_box.div(_class="card-body")
        card_body.h3(title, _class="card-title")
        card_body.div(text, _class="card-text")
        card_body.a(btn_text or "Go to link", href=btn_link, _class="btn btn-primary")        
        return card_box