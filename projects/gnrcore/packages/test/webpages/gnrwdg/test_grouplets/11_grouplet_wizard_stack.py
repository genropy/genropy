# -*- coding: utf-8 -*-

"""Regression page for the wizard stepper-bar collapse under a stackContainer.

StackContainer hides non-selected pages with display:none; a layout pass
performed in that state measures the wizard's top/bottom slots at 0 and
ContentPane.resize stamps that 0 as an inline pixel height on the inner bar.
The 0 then latches: every later pass re-measures the stamped height and
re-stamps 0, so the stepper never recovers.
"""

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler,
                     gnrcomponents/grouplet/grouplet:GroupletHandler,
                     th/th:TableHandler"""

    def test_1_wizard_in_stack(self, pane):
        """Wizard on page one of a stackContainer, a plain pane on page two.
        Go to the other page, press 'Resize while hidden' (the deterministic
        trigger: a layout pass while the wizard is display:none), then come
        back: the stepper bar and the bottom bar must keep their height."""
        pane.data('.wizard_stack.wiz_height', '500px')
        bc = pane.borderContainer(height='^.wiz_height',
                                  border='1px solid silver',
                                  datapath='.wizard_stack')
        bc.data('.current_page', 'wizard')
        top = bc.contentPane(region='top', height='40px', padding='5px')
        top.button('Wizard page', action="SET .current_page='wizard';")
        top.button('Other page', action="SET .current_page='other';")
        top.button('Low (200px)', action="SET .wiz_height='200px';")
        top.button('High (500px)', action="SET .wiz_height='500px';")
        top.button('Resize while hidden',
                   action="""var bar = document.querySelector('.wizard_stepper_bar');
                             dijit.byNode(bar.parentElement.parentElement).resize();""")
        sc = bc.stackContainer(region='center', selectedPage='^.current_page')
        sc.borderContainer(pageName='wizard').groupletWizard(
            topic='submethodtesting',
            value='^.data',
            frameCode='stack_wizard',
            region='center')
        sc.contentPane(pageName='other', padding='20px').div(
            'Switch back to the wizard page: the stepper bar must still show '
            'its numbered steps at full height.')

    def test_2_grouplet_follows_resize(self, pane):
        """A handler grouplet painted red, in a container whose height is
        driven by data: shrink it, then enlarge it. The red pane must fill
        the container at every size — a red area stuck at the small height
        is the center-chain latch."""
        pane.data('.box_height', '400px')
        bar = pane.div(padding='5px')
        bar.button('Low (120px)', action="SET .box_height='120px';")
        bar.button('High (400px)', action="SET .box_height='400px';")
        bc = pane.borderContainer(height='^.box_height',
                                  border='1px solid silver')
        bc.contentPane(region='center').grouplet(value='^.red_data',
                                                 handler=self.grp_red)

    @public_method
    def grp_red(self, pane, **kwargs):
        pane.attributes.update(background='red')

    def test_3_wizard_dialog_ratio(self, pane):
        """The cedi shape: a dialogTableHandler whose form is a stack page
        split with the wizard on page one, in a windowRatio-sized dialog.
        The first step is an empty red pane: it must fill the wizard center
        at every window size."""
        pane.borderContainer(height='400px').contentPane(
            region='center').dialogTableHandler(
            table='test.booking',
            datapath='.redstack',
            viewResource='ViewStack',
            formResource='FormStack',
            view_store__onStart=True)
