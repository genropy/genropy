# -*- coding: utf-8 -*-

"""stackButtons: driving a stackContainer from a slotToolbar

The stackButtons slot renders one button per page of a stackContainer and
switches between them. It finds its stack automatically when the toolbar and
the stack belong to the same framePane, and it accepts the stack explicitly
through stackButtons_stackNode when they do not; parentStackButtons is the
mirror case, a page of the stack driving the stack it belongs to.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_testFrameStack(self, pane):
        """Stack containers with slotToolbar to add and remove containers

        The toolbar is the top of the same framePane holding the stack, so
        stackButtons binds to it with no configuration. The two custom slots
        add and remove pages by editing the stack's own value Bag.
        """
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

    def test_1_testInStack(self, pane):
        """Stack containers with dynamic slotToolbar to change between containers

        Here the toolbars live inside the pages of the stack, so each one uses
        parentStackButtons to drive the stack it is contained in — and each
        page is free to put its toolbar wherever it wants, top or bottom.
        """
        sc = pane.stackContainer(height='300px')
        frame_1 = sc.framePane(background='orange',pageName='orange',title='orange')
        frame_1.top.slotToolbar('title,*,parentStackButtons',title='Orange container')
        frame_2 = sc.framePane(background='green',pageName='green',title='green')
        frame_2.bottom.slotToolbar('title,*,parentStackButtons,*',title='Green container')

    def test_2_testFrameStackNested(self, pane):
        """Stack nested in a borderContainer: binding stackButtons explicitly

        The stack is no longer a direct child of the framePane — a
        borderContainer sits in between — so automatic binding does not apply
        and the toolbar is told which stack to drive through
        stackButtons_stackNode.
        """
        frame = pane.framePane(height='300px')
        bc = frame.center.borderContainer()
        bc.contentPane(region='top').div('This pane is above the stack')
        sc = bc.stackContainer(selectedPage='^.selectedPage', region='center')
        toolbar = frame.top.slotToolbar('*,stackButtons,deletetab,addtab,*', stackButtons_stackNode=sc)

        toolbar.deletetab.slotButton(iconClass='iconbox delete_record',action="""
                                            sc._value.popNode(sc.widget.getSelected().sourceNode.label);
                                        """,sc=sc)
        toolbar.addtab.slotButton(iconClass='iconbox add_record',
                                action="""var len = +sc._value.len();
                                          var pane = sc._("contentPane",{title:"StackContainer " +len,pageName:"stc_"+len});
                                          pane._('div',{innerHTML:"StackContainer " +len});
                                        """,sc=sc)
        sc.contentPane(title='Orange',pageName='orange',background='orange')
        sc.contentPane(title='Green',pageName='green',background='green')
