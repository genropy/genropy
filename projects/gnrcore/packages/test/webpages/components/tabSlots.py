# -*- coding: utf-8 -*-

"Test page description"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"
         
    def test_0_testFrameStack(self,pane):
        """Stack containers with slotToolbar to add and remove containers"""
        frame = pane.framePane(height='300px')
        toolbar = frame.top.slotToolbar('*,stackButtons,deletetab,addtab,*')
        sc = frame.center.stackContainer(selectedPage='^.selectedPage')
        toolbar.deletetab.slotButton(iconClass='iconbox delete_record',action="""
                                            sc._value.popNode(sc.widget.getSelected().sourceNode.label);
                                        """,sc=sc)
        toolbar.addtab.slotButton(iconClass='iconbox add_record',
                                action="""var len = +sc._value.len();
                                          var pane = sc._("contentPane",{title:"StackContainer " +len,pageName:"stc_"+len+1});
                                          pane._('div',{innerHTML:"StackContainer " +len+1});
                                        """,sc=sc)
        sc.contentPane(title='Orange',pageName='orange',background='orange')
        sc.contentPane(title='Green',pageName='green',background='green')
    
    def test_1_testInStack(self,pane):
        """Stack containers with dynamic slotToolbar to change between containers"""
        sc = pane.stackContainer(height='300px')
        frame_1 = sc.framePane(background='orange',pageName='orange',title='orange')
        frame_1.top.slotToolbar('title,*,parentStackButtons',title='Orange container')
        frame_2 = sc.framePane(background='green',pageName='green',title='green')
        frame_2.bottom.slotToolbar('title,*,parentStackButtons,*',title='Green container')