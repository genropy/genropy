# -*- coding: utf-8 -*-

"""Regression page for the wizard stepper-bar collapse under a stackContainer.

StackContainer hides non-selected pages with display:none; a layout pass
performed in that state measures the wizard's top/bottom slots at 0 and
ContentPane.resize stamps that 0 as an inline pixel height on the inner bar.
The 0 then latches: every later pass re-measures the stamped height and
re-stamps 0, so the stepper never recovers.
"""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/grouplet/grouplet:GroupletHandler"""

    def test_1_wizard_in_stack(self, pane):
        """Wizard on page one of a stackContainer, a plain pane on page two.
        Go to the other page, press 'Resize while hidden' (the deterministic
        trigger: a layout pass while the wizard is display:none), then come
        back: the stepper bar and the bottom bar must keep their height."""
        bc = pane.borderContainer(height='500px', border='1px solid silver',
                                  datapath='.wizard_stack')
        bc.data('.current_page', 'wizard')
        top = bc.contentPane(region='top', height='40px', padding='5px')
        top.button('Wizard page', action="SET .current_page='wizard';")
        top.button('Other page', action="SET .current_page='other';")
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
