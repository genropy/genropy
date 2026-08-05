# -*- coding: utf-8 -*-

"""
TEST 08 - Grouplet Semaphore (Form Status Indicator)

EXPECTED BEHAVIOR:
- Grouplet forms now have a semaphore indicator that shows three states:
  * semaphore_ok: form is clean/saved (default state)
  * semaphore_changed: form has been modified but not saved
  * semaphore_error: form has validation errors
- The semaphore replaces the old title-based error indicator.
- Test by opening app preferences (which use grouplet forms).

VERIFY:
- [ ] Open preferences: semaphore shows OK state (no special indicator)
- [ ] Modify a field: semaphore changes to 'changed' state
- [ ] Trigger validation error: semaphore shows 'error' state
- [ ] Save/Apply: semaphore returns to OK state
- [ ] Button text is "Apply" (not "Save")
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_open_preferences(self, pane):
        """Open the app preferences page to test grouplet semaphore behavior.
        Navigate to: menu -> Adm -> Preferences"""
        pane.div('Open the application preferences page to test grouplet forms.')
        pane.div('Steps:', font_weight='bold', margin_top='10px')
        pane.ul().li('Navigate to Adm > Preferences')
        pane.ul().li('Observe the grouplet panel semaphore (small dot/indicator)')
        pane.ul().li('Modify a preference value -> semaphore should change')
        pane.ul().li('Click "Apply" to save -> semaphore returns to OK')
        pane.button('Go to Preferences',
                     action="genro.pageBack('adm/app_preference');")

    def test_1_semaphore_states(self, pane):
        """Visual reference for the three semaphore states"""
        container = pane.div(margin='20px')
        for cls, label, desc in [
            ('semaphore_ok', 'OK', 'Form is clean / saved'),
            ('semaphore_changed', 'Changed', 'Form has unsaved modifications'),
            ('semaphore_error', 'Error', 'Form has validation errors')
        ]:
            row = container.div(display='flex', align_items='center', gap='12px',
                                margin_bottom='12px')
            row.div(width='12px', height='12px', border_radius='50%',
                    _class=cls)
            row.div('%s: %s' % (label, desc))
