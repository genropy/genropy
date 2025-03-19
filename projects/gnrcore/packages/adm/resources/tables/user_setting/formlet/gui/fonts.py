
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import metadata

info = {
    "caption":"!![en]Font configurations",
    "iconClass":'fonts',
    "editing_path":"sys.theme"
}

FONTFAMILIES = """Arial, Helvetica, sans-serif
Verdana, Geneva, sans-serif
'Palatino Linotype', 'Book Antiqua', Palatino, serif
'Times New Roman', Times, serif
Roboto condensed
Fira Sans condensed"""


class Formlet(BaseComponent):
    py_requires = 'th/th'
    def flt_main(self,pane):


        fb = pane.formlet(cols=1, border_spacing='4px')
       #fb.filteringSelect('^.device_mode',lbl='!![en]Device mode',
       #                values='std:Standard,mobile:Mobile,xmobile:Large mobile')
        #fb.checkbox(value='^.bordered_icons',label='Bordered icons')
        if not self.isMobile:
            fb.comboBox(value='^.desktop.font_family',values=FONTFAMILIES,lbl='Desktop Font family')
            fb.filteringSelect(value='^.desktop.zoom', values='0.8:Small,1:Medium,1.1:Large,1.25:Extra Large',
                           default=1, lbl='!!Desktop Zoom', width='15em')
        else:
            fb.filteringSelect(value='^.mobile.zoom', values='0.8:Small,1:Medium,1.1:Large,1.25:Extra Large',
                            default=1, lbl='!!Mobile Zoom', width='15em')
            fb.comboBox(value='^.mobile.font_family',values=FONTFAMILIES,lbl='Mobile Font family')