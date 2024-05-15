
# # -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# Copyright (c) : 2004 - 2007 Softwell sas - Milano 
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA


from gnr.core.gnrdecorator import public_method

FONTFAMILIES = """Arial, Helvetica, sans-serif
Verdana, Geneva, sans-serif
'Palatino Linotype', 'Book Antiqua', Palatino, serif
'Times New Roman', Times, serif
Roboto condensed
Fira Sans condensed"""

class AppPref(object):
    def prefpane_sys(self, tc, **kwargs):
        tc = tc.tabContainer(margin='2px',**kwargs)
        self.stylingPreferences(tc.contentPane(title='!![en]Styling'))
        self.printPreferences(tc.borderContainer(title='!![en]Print'))
        self.xlsxPrintPreferences(tc.contentPane(title='!![en]XLSX Print', datapath='.xlsx_print'))
        self.pdfPreferences(tc.borderContainer(title='!![en]PDF Preferences'))
        self.developerPreferences(tc.contentPane(title='!![en]Developer'))
        self.site_config_override(tc.contentPane(title='!![en]Site config',datapath='.site_config'))
        self.tablesConfiguration(tc.contentPane(title='!![en]Tables Configuration'))
        self.notificationPreferences(tc.contentPane(title='!![en]Notification'))
        
    def stylingPreferences(self, pane):
        fb = pane.formbuilder(cols=1, border_spacing='4px',datapath='.theme')
        fb.filteringSelect(value='^.theme_variant',values='blue,red,green,yellow,orange,',lbl='!![en]Theme variant')       
        fb.textbox(value='^.palette_colors',lbl='!![en]Default color palette')
        fb.textbox(value='^.palette_steps',lbl='!![en]Default color steps')

    def printPreferences(self, pane):
        fb = pane.roundedGroup(title='!![en]Print Modes',
                                    region='top',height='80px').formbuilder(cols=1, border_spacing='4px')
        fb.checkbox(value='^.print.ask_options_enabled',label='!![en]Print Options Enabled')
        fb.checkBoxText(value='^.print.modes',values='pdf:PDF,server_print:Server Print,mail_pdf:PDF Mail,mail_deliver:Mail Deliver',lbl='Print modes')
        
        fb = pane.roundedGroup(title='!![en]PDF Render',region='center').formbuilder(cols=1, border_spacing='4px',datapath='.pdf_render')
        fb.checkbox(value='^.keep_html',label='!![en]Keep HTML (for debug)')
        fb.checkbox(value='^.wk_legacy',label='!![en]Legacy mode (use wkhtmltopdf)')
        fb.textbox(value='^.margin_top',lbl='!![en]Margin top', hidden='^.wk_legacy?=!#v')
        fb.textbox(value='^.margin_bottom',lbl='!![en]Margin bottom', hidden='^.wk_legacy?=!#v')
        fb.textbox(value='^.margin_left',lbl='!![en]Margin left', hidden='^.wk_legacy?=!#v')
        fb.textbox(value='^.margin_right',lbl='!![en]Margin right', hidden='^.wk_legacy?=!#v')
        fb.textbox(value='^.zoom',lbl='!![en]Pdf zoom',width='5em', hidden='^.wk_legacy?=!#v')
        
    def pdfPreferences(self, pane):
        fbf = pane.roundedGroup(title='!![en]PDF Form',
                                    region='top',height='60px').formbuilder(cols=1, border_spacing='4px')
        fbf.checkbox(value='^.print.enable_pdfform',label='!![en]Enable pdf forms (Requires pdftk)')

        fbv = pane.roundedGroup(title='!![en]PDF Viewer', region='center').mobileFormBuilder(cols=1, border_spacing='4px')
        fbv.checkbox(value='^.jsPdfViewer',label='!![en]Enable PDF viewer')
        fbv.checkboxtext(value='^.jsPdfViewerOptions', lbl='!![en]PDF viewer options', 
                         values="""editorFreeText:[!![en]Free text],editorInk:[!![en]Draw],editorStamp:[!![en]Image],\
                                    print:[!![en]Print],download:[!![en]Download],secondaryToolbarToggle:[!![en]Tools]""",
                         cols=3, hidden='^.jsPdfViewer?=!#v',lbl_hidden='^.jsPdfViewer?=!#v')
        fbv.checkboxtext(value='^.jsPdfViewerTools', lbl='!![en]PDF viewer tools', 
                         values="""secondaryOpenFile:[!![en]Open],presentationMode:[!![en]Presentation mode],viewBookmark:[!![en]View bookmark],\
                                    firstPage:[!![en]First page],lastPage:[!![en]Last page],pageRotateCw:[!![en]Page rotate clockwise],\
                                    pageRotateCcw:[!![en]Page rotate counterclockwise],cursorToolButtons:[!![en]Cursor tools],\
                                    scrollPage:[!![en]Scroll page],scrollVertical:[!![en]Scroll vertical],scrollHorizontal:[!![en]Scroll Horizontal],\
                                    spreadModeButtons:[!![en]Spread mode buttons],documentProperties:[!![en]Document properties]""",
                         cols=3,hidden='^.jsPdfViewer?=!#v',lbl_hidden='^.jsPdfViewer?=!#v')
        
    def developerPreferences(self, pane):
        fb = pane.formbuilder()
        fb.comboBox(value='^.experimental.remoteForm',lbl='!![en]Remote forms',values='onEnter,delayed')
        fb.checkbox(value='^.experimental.wsk_enabled',lbl='!![en]WSK Enabled')
        
    def tablesConfiguration(self, pane):
        fb = pane.formbuilder(cols=1,border_spacing='3px',datapath='.tblconf')
        fb.textbox(value='^.archivable_tag',lbl='!![en]Archivable tag')
        
    def xlsxPrintPreferences(self, pane):
        xfb = pane.formbuilder(cols=1, border_spacing='4px')
        xfb.numbertextbox(value='^.top',lbl='!![en]Print Margin top')
        xfb.numbertextbox(value='^.bottom',lbl='!![en]Print Margin bottom')
        xfb.numbertextbox(value='^.left',lbl='!![en]Print Margin left')
        xfb.numbertextbox(value='^.right',lbl='!![en]Print Margin right')
        xfb.numbertextbox(value='^.footer',lbl='!![en]Print Margin footer')
        xfb.numbertextbox(value='^.header',lbl='!![en]Print Margin header')
        xfb.numbertextbox(value='^.scale',lbl='!![en]Print Scale')
        xfb.numbertextbox(value='^.fitToWidth',lbl='!![en]Fit To Width')
        xfb.numbertextbox(value='^.fitToHeight',lbl='!![en]Fit To Height')
        xfb.filteringSelect(value='^.orientation',lbl='!![en]Print orientation', values='portrait,landscape')
        xfb.filteringSelect(value='^.show_title',lbl='!![en]Print title', values='footer,header')
    
    def notificationPreferences(self, pane):
        nfb = pane.formbuilder(cols=1, border_spacing='4px')
        nfb.checkbox(value='^.notifications_enabled',label='!![en]Notification enabled')
        nfb.textbox(value='^.notification_claim_email',lbl='!![en]Claim email')
        
    def site_config_override(self,pane):
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.numberTextBox(value='^.cleanup?interval',lbl='!![en]Cleanup interval',placeholder=self.site.config['cleanup?interval'])
        fb.numberTextBox(value='^.cleanup?page_max_age',lbl='!![en]Page max age',placeholder=self.site.config['cleanup?page_max_age'])
        fb.numberTextBox(value='^.cleanup?connection_max_age',lbl='!![en]Connection max age',placeholder=self.site.config['cleanup?connection_max_age'])

    @public_method
    def _resetMemcached(self):
        self.site.shared_data.flush_all()


class UserPref(object):
    def prefpane_sys(self, tc, **kwargs):
        tc = tc.tabContainer(margin='2px',**kwargs)
        self.pref_cache(tc.contentPane(title='!![en]Caching', padding='10px', datapath='.cache'))
        self.pref_sound(tc.contentPane(title='!![en]Sounds', padding='10px', datapath='.sounds'))
        self.pref_shortcuts(tc.contentPane(title='!![en]Shortcuts', padding='10px', datapath='.shortcuts'))
        self.pref_theme(tc.contentPane(title='!![en]Theme', padding='10px', datapath='.theme'))



    def pref_theme(self, pane):
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.filteringSelect('^.device_mode',lbl='!![en]Device mode',
                        values='std:Standard,mobile:Mobile,xmobile:Large mobile')

        #fb.checkbox(value='^.bordered_icons',label='Bordered icons')
        fb.filteringSelect(value='^.desktop.font_size',values='!!12px:Default,12px:Small,13px:Medium,14px:Large,15px:Extra Large',lbl='Desktop Font size')
        fb.comboBox(value='^.desktop.font_family',values=FONTFAMILIES,lbl='Desktop Font family')
        fb.filteringSelect(value='^.mobile.font_size',values='!!12px:Default,12px:Small,13px:Medium,14px:Large,15px:Extra Large',lbl='Mobile Font size')
        fb.comboBox(value='^.mobile.font_family',values=FONTFAMILIES,lbl='Mobile Font family')
        fb.checkbox(value='^.#parent.jsPdfViewer',label='!![en]Extended pdf viewer')

       #fb.horizontalSlider(value='^.body.filter_rotate',intermediateChanges=True,width='150px',default_value=0,
       #                minimum=0,maximum=360,lbl='Color rotate',livePreference=True)
       #fb.horizontalSlider(value='^.body.filter_invert',intermediateChanges=True,width='150px',default_value=0,
       #                minimum=0,maximum=1,lbl='Color invert',livePreference=True)

       #fb.numberTextBox(value='^.body.zoom',intermediateChanges=True,width='150px',default_value=0,
       #                minimum=0,maximum=1,lbl='Zoom',livePreference=True)

        #fb.filteringSelect(value='^.default_fontsize',values='!!12px:Small,13px:Medium,14px:Large,15px:Extra Large',lbl='Font size')
        #fb.comboBox(value='^.body.font_family',values=FONTFAMILIES,lbl='Font family',width='20em',livePreference=True) 

    def pref_sound(self, pane):
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.filteringSelect(value='^.onsaving', lbl='!![en]On saving', values=self._allSounds(),
                           validate_onAccept='if(value){genro.playSound(value);}')
        fb.filteringSelect(value='^.onsaved', lbl='!![en]On saved', values=self._allSounds(),
                           validate_onAccept='if(value){genro.playSound(value);}')
        fb.filteringSelect(value='^.error', lbl='!![en]On error', values=self._allSounds(),
                           validate_onAccept='if(value){genro.playSound(value);}')

    def pref_cache(self, pane):
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.button('!![en]Reset session storage', action='if(sessionStorage){sessionStorage.clear();}')
        fb.button('!![en]Reset local storage', action='if(localStorage){localStorage.clear();}')

    def pref_shortcuts(self,pane):
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.comboBox(value='^.save',values='f1,alt+s,cmd+s',lbl='!![en]Save',placeholder='f1')
        fb.comboBox(value='^.reload',values='f9,alt+r',lbl='!![en]Reload',placeholder='f9')
        fb.comboBox(value='^.dismiss',values='alt+up,alt+q',lbl='!![en]Dismiss',placeholder='alt+up')
        fb.comboBox(value='^.next_record',values='alt+right',lbl='!![en]Next record',placeholder='alt+right')
        fb.comboBox(value='^.prev_record',values='alt+left',lbl='!![en]Prev record',placeholder='alt+left')
        fb.comboBox(value='^.last_record',values='ctrl+alt+right',lbl='!![en]Last record',placeholder='ctrl+alt+right')
        fb.comboBox(value='^.first_record',values='ctrl+alt+left',lbl='!![en]First record',placeholder='ctrl+alt+left')
        fb.comboBox(value='^.jump_record',values='alt+j',lbl='!![en]Jump record',placeholder='alt+j')




    def _allSounds(self):
        return """Basso:Basso,Blow:Blow,Bottle:Bottle,Frog:Frog,Funk:Funk,Glass:Glass,Hero:Hero,Morse:Morse,NewMessage:NewMessage,Ping:Ping,Pop:Pop,Purr:Purr,Sosumi:Sosumi,sound1:Sound1,Submarine:Submarine,Tink:Tink"""