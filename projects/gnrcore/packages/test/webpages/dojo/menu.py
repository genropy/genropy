# -*- coding: utf-8 -*-

"""Menu"""

from gnr.core.gnrbag import Bag,DirectoryResolver
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrsys import expandpath

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"
    
    def test_0_dropdown_button(self, pane):
        "Popup menu from dropdown button"
        ddb = pane.dropdownbutton('Menu')
        menu = ddb.menu(action='alert($1.foo)',modifiers='*')
        menu.menuline('Save',foo='Saved!')
        menu.menuline('Save As...',foo=60)
        menu.menuline('Load',action='alert("I\'m different")')
        menu.menuline('-')
        submenu = menu.menuline('Sub').menu(action='alert("sub "+$1.bar)')
        submenu.menuline('cat',bar=35)
        submenu.menuline('dog',bar=60)
    
    def test_1_colored_div(self, pane):
        "Popup menu from colored div"
        ddm = pane.div(height='25px', width='25px', background='lime')
        m = ddm.menu(modifiers='*', _class='menupane')
        m.menuItem(label='Line 1')
        box = m.menuItem().div(max_height='325px',min_width='300px',overflow='auto')
        box.horizontalSlider(value='^.scaleX',width='8em',intermediateChanges=True)
        box.verticalSlider(value='^.scaleY',height='8em',intermediateChanges=True)
        m.menuItem(label='Line last')
        pane.div('^.scaleX')
        pane.div('^.scaleY')

    def test_2_plus_disable(self, pane):
        "Popup with options from + icon. Flag checkbox to disable"
        pane.menudiv(disabled='^.disabled',storepath='.menudata',iconClass='add_row',label='Piero')
        pane.dataRemote('.menudata', 'menudata', cacheTime=5)
        pane.checkbox(value='^.disabled', label='Disable Menu')

    def test_3_text_div(self, pane):
        "Popup with options from text div"
        pane.menudiv(value='^.opzione',values='p:Pippo,z:Zio,r:Rummo,g:Gennaro o pizzaiolo',
                    placeholder='Choose',color='red',font_size='20px')

    def test_4_bag(self, pane):
        "Menu built with options coming from a Bag. Click add menuline to add Palau port"
        menudiv = pane.div(height='25px',width='25px',background='lime')
        ddb = pane.dropDownButton('test')
        ddb.menu(action='alert($1.code)',modifiers='*',storepath='.menudata')
        menu = menudiv.menu(action='alert($1.code)',modifiers='*',storepath='.menudata')
        menu.data('.menudata',self.menudata())
        pane.button('add menuline',
                    action='this.setRelativeData(".menudata.r6",12,{"code":"PP","caption":"Palau port"})',
                    disabled='^.disabled')

    def test_5_text_div(self, pane):
        "Popup with options from text div"
        pane.menudiv(value='^.opzione',values='p:Pippo,z:Zio,r:Rummo,g:Gennaro o pizzaiolo',
                    placeholder='Choose',color='red',font_size='20px')


    def test_11_singleLineAsButton(self, pane):
        "Popup with options from text div"
        pane.checkbox(value='^.disabled',label='Disabled')
        m = pane.menudiv(iconClass='iconbox gear',singleOption='button')
        m.menuline('Ciao',disabled='^.disabled').dataController('alert("gear")')

        m = pane.menudiv(iconClass='iconbox chat',singleOption='ask')
        m.menuline('Chat').dataController('alert("chat")')





    @public_method
    def menudata(self):
        result = Bag()
        result.setItem('r1', None, code='CA', caption='California')
        result.setItem('r2', None, code='IL', caption='Illinois', disabled=True)
        result.setItem('r3', None, code='NY', caption='New York', checked='^.checked')
        result.setItem('r4', None, code='TX', caption='Texas', disabled='^.disabled')
        result.setItem('r5', None, code='AL', caption='Alabama')
        return result
                    
    def test_5_resolver(self, pane):
        "Menu built with options coming from Resolver"
        ddm = pane.div(height='25px', width='25px', background='lime')
        menu = ddm.menu(action='alert($1.code)', modifiers='*', storepath='.menudata', _class='smallmenu',
                        id='test5menu')
        ddm2 = pane.div(height='25px', width='25px', background='red', connectedMenu='test4menu')
        pane.dataRemote('.menudata', 'menudata', cacheTime=5)
        
    def test_6_dir_resolver(self,pane):
        "Menu built with options coming from DirectoryResolver"
        pane.data('.store',DirectoryResolver(expandpath('~/'),cacheTime=10,
                            include='*.py', exclude='_*,.*',dropext=True,readOnly=False)())
        ddm = pane.div(height='25px', width='25px', background='lime')
        ddm.menu(action='console.log($1)', modifiers='*', storepath='.store', _class='smallmenu',
                        id='test99menu')
    
    def test_7_datarpc(self, pane):
        "Download a file from menuline with dataRpc. Please insert your OpenWeatherMap API key first"
        pane.textbox('^.APPID', lbl='OWM API key')
        menu = pane.menudiv(iconClass='iconbox menu_icon')
        line = menu.menuline('Download Bag')
        line.dataRpc(self.buildBag, APPID='^.APPID')

    @public_method
    def buildBag(self, APPID=None):
        #APPID = self.site.getApiKeys('openweathermap')['APPID']
        #DP Alternatively, it is possible to store api keys in instanceconfig.xml file and retrieve them with getApiKeys
        b = Bag()
        b.fromXml(f'http://api.openweathermap.org/data/2.5/weather?q=Milano,IT&APPID={APPID}&mode=xml&units=metric')
        b.toXml('/Users/dgpaci/Downloads/weather.xml') 

    def test_8_menudiv(self,pane):
        "Click on menu can trigger a dataController or a dataRpc"
        m = pane.menudiv(iconClass='iconbox gear')
        m.menuline('Use dataController').dataController('alert(message + cognome)', message='Hello ',
                                                cognome='Pippo',
                                                _ask=dict(title='Complete parameters',
                                                            fields=[dict(name='cognome',lbl='Cognome')]))
        m.menuline('Use dataRpc').dataRpc('.info_string', self.menulineRpc,
                    _ask=dict(title='Confirm',
                              fields=[
                                dict(name='surname', lbl='Surname', validate_notnull=True),
                                dict(name='title', lbl='Title', tag='filteringSelect', values='Mr,Miss,Mrs')]))
        pane.div('^.info_string')

    def test_9_menudiv_label(self,pane):
        bar = pane.slotToolbar('*,mymenu,*')
        bar.mymenu.menudiv(value='^.code',storepath='.menudata',
                        caption_path='.caption',
                        placeholder='!![en]Select', _class='smallmenu')
        pane.data('.menudata', self.menudata())

    def test_10_combomenu(self,pane):
        bar = pane.slotToolbar('*,mymenu,*')
        bar.data('.caption','Select')
        bar.mymenu.textbox('^.caption',width='15em').comboMenu(storepath='.menudata', selected_caption='.caption',_class='smallmenu')
        pane.data('.menudata', self.menudata())

    def test_12_menudiv_token_static(self, pane):
        "Static values resolve the caption from the stored code"
        pane.data('.choice', 'r')
        row = pane.div(display='flex', align_items='center', gap='6px')
        row.div('Status:')
        row.menudiv(value='^.choice',
                    values='r:Ready,w:Waiting,d:Done',
                    placeholder='Choose',
                    btn_id='menudiv_static_token')

        fb = pane.formbuilder(cols=2, border_spacing='6px', margin_top='12px')
        fb.div('^.choice', lbl='Stored code')
        fb.div("^.choice?label?=#v||'not set'", lbl='Label attribute')
        pane.button('Set Waiting externally', action="SET .choice='w';")
        pane.button('Clear externally', action='SET .choice=null;')

    def test_13_menudiv_token_dynamic(self, pane):
        "Dynamic values and storepath menus retain the caption-path contract"
        pane.data('.dynamic_values', 'a:Alpha,b:Beta,g:Gamma')
        pane.data('.dynamic_choice', 'a')
        pane.data('.dynamic_caption', 'Alpha')
        pane.data('.store_choice', 'CA')
        pane.data('.store_caption', 'California')
        pane.data('.menudata', self.menudata())

        fb = pane.formbuilder(cols=2, border_spacing='8px')
        fb.menudiv(value='^.dynamic_choice',
                   values='=.dynamic_values',
                   caption_path='.dynamic_caption',
                   btn_id='menudiv_dynamic_token',
                   lbl='Bound values')
        fb.div('^.dynamic_choice')
        fb.menudiv(value='^.store_choice',
                   storepath='.menudata',
                   key='code', caption='caption',
                   caption_path='.store_caption',
                   btn_id='menudiv_store_token',
                   lbl='Storepath')
        fb.div('^.store_choice')

    def test_14_menudiv_token_states(self, pane):
        "Token variants preserve opt-out, dark-surface and disabled states"
        pane.data('.choice', 'r')
        pane.data('.disabled', False)
        values = 'r:Ready,w:Waiting,d:Done'

        pane.div('Default token', font_weight='bold', margin_bottom='4px')
        pane.menudiv(value='^.choice', values=values,
                     btn_id='menudiv_default_token')

        dark = pane.div(background='#2A2A2E', padding='8px', margin_top='10px')
        dark.menudiv(value='^.choice', values=values, colorWhite=True,
                     btn_id='menudiv_white_token')

        pane.div('Explicit legacy-button opt-out', font_weight='bold',
                 margin_top='10px', margin_bottom='4px')
        pane.menudiv(value='^.choice', values=values,
                     btn__class='menuButtonDiv buttonDiv',
                     btn_id='menudiv_legacy_button')

        pane.div('Disabled token', font_weight='bold',
                 margin_top='10px', margin_bottom='4px')
        pane.menudiv(value='^.choice', values=values,
                     disabled='^.disabled',
                     btn_id='menudiv_disabled_token')
        pane.checkbox(value='^.disabled', label='Disable token')


    @public_method
    def menulineRpc(self,surname=None,title=None,**kwargs):
        info_string = 'Hello '+title+' '+surname
        print(info_string)
        return info_string
