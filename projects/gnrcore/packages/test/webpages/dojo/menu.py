# -*- coding: utf-8 -*-

"""Menu"""
from __future__ import print_function
import datetime
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
        ddm = pane.div(height='50px', width='50px', background='lime')
        m = ddm.menu(modifiers='*', _class='menupane')
        m.menuItem(label='Line 1')
        box = m.menuItem().div(max_height='350px',min_width='300px',overflow='auto')
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
        menudiv = pane.div(height='50px',width='50px',background='lime')
        ddb = pane.dropDownButton('test')
        ddb.menu(action='alert($1.code)',modifiers='*',storepath='.menudata')
        menu = menudiv.menu(action='alert($1.code)',modifiers='*',storepath='.menudata')
        menu.data('.menudata',self.menudata())
        pane.button('add menuline',
                    action='this.setRelativeData(".menudata.r6",12,{"code":"PP","caption":"Palau port"})',
                    disabled='^.disabled')

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
        ddm = pane.div(height='50px', width='50px', background='lime')
        menu = ddm.menu(action='alert($1.code)', modifiers='*', storepath='.menudata', _class='smallmenu',
                        id='test5menu')
        ddm2 = pane.div(height='50px', width='50px', background='red', connectedMenu='test4menu')
        pane.dataRemote('.menudata', 'menudata', cacheTime=5)
        
    def test_6_dir_resolver(self,pane):
        "Menu built with options coming from DirectoryResolver"
        pane.data('.store',DirectoryResolver(expandpath('~/'),cacheTime=10,
                            include='*.py', exclude='_*,.*',dropext=True,readOnly=False)())
        ddm = pane.div(height='50px', width='50px', background='lime')
        ddm.menu(action='console.log($1)', modifiers='*', storepath='.store', _class='smallmenu',
                        id='test99menu')
    
    def test_7_controller(self, pane):
        "Attach controller directly to menuline"
        menu = pane.menudiv(iconClass='iconbox menu_icon')
        line = menu.menuline('Alert')
        line.dataController('alert("Be careful")')

    def test_8_datarpc(self, pane):
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