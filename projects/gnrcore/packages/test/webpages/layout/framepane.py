# -*- coding: utf-8 -*-

"""framePane"""

from gnr.web.gnrwebstruct import struct_method


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"
    
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

    def test_3_slotbar_base(self,pane):
        "top slotToolbar and bottom slotBar filled with slotButtons, the plain framePane layout"
        frame = pane.framePane(frameCode='frame0',height='200px',width='300px',shadow='3px 3px 5px gray',
                               border='1px solid #bbb',margin='10px',center_border='1px solid #bbb',
                               center_background='gray')

        top = frame.top.slotToolbar(slots='3,curr_user,*,add_btn,5',height='20px')
        top.curr_user.div('^gnr.avatar.user')
        top.add_btn.button('Add new element')

        bottom = frame.bottom.slotBar(slots='5,cancel_btn,*,|,*,save_btn,5',height='30px')
        bottom.cancel_btn.slotButton(label='Cancel',action='alert("Cancel!")')
        bottom.save_btn.slotButton(label='Save',action='alert("Saving")')

    def test_4_slotbar_sidebar(self,pane):
        "design='sidebar': the right slotToolbar carries an icon48 slotButton, the bottom one a localized label"
        frame = pane.framePane(frameCode='frame1',height='200px',width='300px',shadow='3px 3px 5px gray',
                               border='1px solid #bbb',xmargin='10px',
                               center_background='gray',rounded=20,design='sidebar')
        right = frame.right.slotToolbar(slots='30,pp,*',width='100px',_class='icon48')
        right.pp.slotButton('aaa',iconClass='iconbox tray')
        bottom = frame.bottom.slotToolbar(slots='30,foo,*,bar,30',height='20px')
        bottom.foo.slotButton('!!Save',iconClass="icnBaseOk",showLabel=False)

    def test_5_slotbar_rounded(self,pane):
        "rounded corners on the frame with a slotToolbar on each of the four sides"
        frame = pane.framePane(frameCode='frame3',height='200px',width='300px',shadow='3px 3px 5px gray',
                               border='1px solid #bbb',margin='10px',center_border='1px solid #bbb',
                               center_background='gray',rounded=10,rounded_bottom=0)
        frame.top.slotToolbar(slots='30,foo,*,bar,30',height='20px')
        frame.left.slotToolbar(slots='30,foo,*,bar,30',width='20px')
        frame.bottom.slotToolbar(slots='30,foo,*,bar,30',height='20px')
        frame.right.slotToolbar(slots='30,foo,*,bar,30',width='20px')

    def test_6_slotbar_commands(self,pane):
        "slotButtons publishing on a named slotbarCode, and a custom slot added through a struct_method"
        frame = pane.framePane(frameCode='frame5',height='200px',width='300px',shadow='3px 3px 5px gray',
                               border='1px solid #bbb',margin='10px',center_border='1px solid #bbb',
                               center_background='gray',rounded_top=10)
        top = frame.top.slotToolbar(slotbarCode='myslotbar',slots='*,foo,bar,xx,myaction,10',
                                    myaction_action='console.log(genro.getFrameNode("frame5"));',height='20px')
        top.foo.slotButton(label='Add',iconClass='icnBaseAdd',publish='add')
        top.bar.slotButton(label='remove',iconClass='icnBaseDelete',publish='remove')
        frame.numberTextbox(value='^.value',default=1,width='5em',
                            subscribe_myslotbar_add="""SET .value=(GET .value)+1;""",   # It doesn't work!
                            subscribe_myslotbar_remove='SET .value= (GET .value) -1;')  # It doesn't work!

    @struct_method
    def mypage_slotbar_myaction(self,pane,_class=None,action=None,publish=None,**kwargs):
        "Custom slot used by test_6_slotbar_commands: a slotButton visible only while ^pippo is true"
        pane.slotButton(label='action',iconClass='icnBaseAction',publish=publish,action=action,visible='^pippo')

    def test_7_slotbar_js(self,pane):
        "A slotBar built client side inside a quickDialog, slot by slot, from javascript"
        pane.button('Test',action="""var dlg = genro.dlg.quickDialog('Test');
                                     dlg.center._('div',{innerHTML:'Hi there!'});
                                     var slotbar = dlg.bottom._('slotBar',{slotbarCode:'chooser',slots:'*,discard,cancel,save'})
                                     slotbar._('slotButton','discard',{label:'Discard',publish:'discard'});
                                     slotbar._('slotButton','cancel',{label:'Cancel',publish:'cancel'});
                                     slotbar._('slotButton','save',{label:'Save',publish:'save'});
                                     dlg.show_action();""")

    def test_8_slotbar_retina_icons(self,pane):
        "Navigation slotButtons drawn with the rbox24 retina icon set"
        frame = pane.framePane(height='200px',width='800px',shadow='3px 3px 5px gray',
                               border='1px solid #bbb',margin='10px',design='sidebar')
        bar = frame.top.slotToolbar('5,first,prev,next,last,*')
        bar.first.slotButton(iconClass='rbox24 first')
        bar.prev.slotButton(iconClass='rbox24 prev')
        bar.next.slotButton(iconClass='rbox24 next')
        bar.last.slotButton(iconClass='rbox24 last')
