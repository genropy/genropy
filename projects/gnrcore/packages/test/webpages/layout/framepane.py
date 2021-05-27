# -*- coding: utf-8 -*-

"""framePane"""

from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerBase,th/th:TableHandler,
                        dashboard_component/dashboard_component:DashboardItem"""
    
    def windowTitle(self):
        return 'framePane'

    def test_0_regions(self,pane):
        "framePane object provides slotBar regions which in this case we fill with a simple div"
        frame = pane.framePane(height='200px',width='300px',shadow='3px 3px 5px gray',
                               border='1px solid #bbb',margin='10px',design='sidebar')     
        sidebar = frame.right.slotBar(slots='*,mytree,*',width='60px',border_left='1px solid gray',closable='close',splitter=True)
        sidebar.mytree.div('aaa<br/>bbb')
        
    def test_1_regions(self,pane):
        "Same as before, but with different regions filled in different ways"
        frame = pane.framePane(height='200px',width='300px',shadow='3px 3px 5px gray',
                               border='1px solid #bbb',margin='10px',design='sidebar')
        top = frame.top.slotToolbar(slots='30,foo,*,bar,30',height='20px',closable='close',closable_backround='blue')
        bottom = frame.bottom.slotBar(slots='btoh,*,|,bt2,30',height='30px',closable='close',border_top='1px solid gray')
        bottom.btoh.slotButton(label='Ok',action='alert("Hello!")')
        bottom.bt2.slotButton(label='ciao ciao',action='alert("Hello again!")')
        
        left = frame.left
        sidebar = left.slotBar(slots='*,mytree,*',border_right='1px solid gray',closable='close',
                    closable_background='darkblue',closable_transition='2s',splitter=True)
        sidebar.mytree.button('Pippo')        
        sidebar = frame.right.slotBar(slots='*,mytree,*',width='60px',border_left='1px solid gray',closable='close',splitter=True)
       
        sidebar.mytree.div('aaa<br/>bbb')
        frame.textbox(value='^.placeholder',placeholder='Insert text here',margin='20px')
        frame.textbox(value='^.aaa',placeholder='^.placeholder',margin='20px')
        frame.input(value='^.ccc',placeholder='^.aaa',margin='20px')

    def test_2_splitter_margins(self,pane):
        "Instead of closable areas, you can use splitter to separate dynamically containers and content"
        frame = pane.framePane(height='300px',design='sidebar')
        left = frame.left
        left.attributes.update(splitter=True)
        bar = frame.left.slotBar('pippo,pluto,0',width='200px',border_right='1px solid silver')
        bar.pippo.div('slot 1')
        bar.pluto.div('slot 2')

        frame.div('Pippo',font_size='30px')