# -*- coding: utf-8 -*-

"""tabContainer"""

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    
    def windowTitle(self):
        return 'tabContainer'
        
    def test_0_tabcontainer_closable(self, pane):
        "tabContainer with closable tabs. Select by name (alfio, bieto) or number (1,2)"
        tc = pane.tabContainer(height='300px',selectedPage='^.pippo',selected='^.pluto')
        pane.textbox(value='^.pippo')
        pane.numbertextbox(value='^.pluto')
        pane.button('Distruggi alfio',action="""tc._value.popNode('#0');""",tc=tc)
        pane = tc.contentPane(title='Alfio',closable=True,pageName='alfio',nodeId='alfio').div('Hi there')
        tc.contentPane(title='Bieto',closable=True,pageName='bieto')
    
    def test_1_opener(self,pane):
        "tabContainers can include closable areas"
        bc = pane.borderContainer(height='200px',margin='10px',border='1px solid silver',_class='tinySplitter')
        left = bc.tabContainer(region='bottom',height='150px',closable='close',splitter=True,
                            closable_background='green',margin='2px',border_top='1px solid silver')
        left.contentPane(title='Pippo')
        left.contentPane(title='Paperino')
        bc.contentPane(region='center')

    def test_2_tab_hidden(self, pane):
        "Show and hide tabs with button"
        bc = pane.borderContainer(height='300px')
        top = bc.contentPane(region='top')
        tc = bc.tabContainer(region='center')
        tc.contentPane(title='tab1')
        tab2 = tc.contentPane(title='tab2',display='none')
        tab2.div('aaa')
        top.button('toggle tab 2',action="""
                                        if(!this._pendingTab){
                                            this._pendingTab = tc._value.popNode(tab2.label);
                                        }else{
                                            tc._value.setItem(this._pendingTab.label,this._pendingTab);
                                            this._pendingTab = null;
                                        }
                                        """,tc=tc,tab2=tab2)

    def test_3_tab_hidden(self, pane):
        "Show and hide tabs with checkbox"
        bc = pane.borderContainer(height='300px')
        bc.data('.hidden_tab2',True)
        top = bc.contentPane(region='top', margin='5px')
        tc = bc.tabContainer(region='center',nodeId='mytc')
        tc.contentPane(title='tab1',hidden='^.hidden_tab1').div('Hello tab 1')
        tc.contentPane(title='tab2',hidden='^.hidden_tab2').div('Hello tab 2')
        top.checkbox(value='^.hidden_tab1',label='Hidden tab 1')
        top.checkbox(value='^.hidden_tab2',label='Hidden tab 2')
        top.button('Test hidden',hidden='^.hidden_tab2')

    def test_4_tabcontainer(self, pane):
        "Choose active tab with numbertextbox (e.g. 0,1,2)"
        bc = pane.borderContainer(height='200px')
        top = bc.contentPane(region='top', height='30px', background='red').numberTextbox(value='^.selected')
        tc = bc.tabContainer(region='center', selected='^.selected', nodeId='t0', _class='supertab')
        tc.contentPane(background='lime', title='lime').div('lime')
        tc.contentPane(background='pink', title='pink', closable=True).div('pink')
        pane = tc.contentPane(background='blue', title='blue')
        fb = pane.formbuilder(cols=1).simpleTextArea(value='^.blue', lbl='blue')
        
    def test_5_iframe(self, pane):
        tc = pane.tabContainer(height='400px')
        tc.contentPane(title='No iframe').div('hello')
        tc.contentPane(title='iframe test',overflow='hidden').iframe(main='iframetest',height='100%',width='100%',border=0)
        tc.contentPane(title='iframe genropy',overflow='hidden').htmliframe(
                                            src='https://www.genropy.org/docs/widgetpedia/layout/tabcontainer.html',
                                            height='100%',width='100%',border=0)
        tc.contentPane(title='iframe html',overflow='hidden').iframe(src=self.getResourceUri('test.html'),height='100%',width='100%',border=0)
        
    def rpc_iframetest(self,pane,**kwargs):
        pane.div('hello again, this is a test rpc')
