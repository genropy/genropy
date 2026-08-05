# -*- coding: utf-8 -*-

"""
TEST 07 - Positioned Toast (target element)

EXPECTED BEHAVIOR:
- Toast appears centered on the target element instead of the global
  top-right container.
- Uses pop-in/pop-out animation (scale) instead of slide-in/slide-out.
- Auto-dismisses normally with progress bar.
- The target can be a sourceNode, a DOM node, or a widget.

VERIFY:
- [ ] Toast appears centered on the colored box, not top-right
- [ ] Scale animation (pop-in) instead of slide-in
- [ ] Auto-dismisses after the specified duration
- [ ] Each target box shows its own positioned toast
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_target_toast(self, pane):
        """Click each colored box to see a toast centered on it"""
        container = pane.div(display='flex', gap='40px', margin='20px',
                             justify_content='center')
        for color, level in [('#3b82f6', 'info'), ('#22c55e', 'success'),
                             ('#f59e0b', 'warning'), ('#ef4444', 'error')]:
            box = container.div(
                level.upper(), text_align='center', line_height='100px',
                width='120px', height='100px', border_radius='8px',
                background=color, color='white', font_weight='bold',
                cursor='pointer', nodeId='target_%s' % level,
                connect_onclick="""
                    var domNode = this.widget ? this.widget.domNode : this.domNode;
                    genro.toast.show({
                        message: '%s toast on target',
                        level: '%s',
                        target: domNode,
                        duration: 3000
                    });
                """ % (level.capitalize(), level))

    def test_1_toast_with_onclose(self, pane):
        """Toast with onClose callback - alert fires when toast is dismissed"""
        pane.button('Toast with onClose', action="""
            genro.toast.show({
                title: 'Callback Test',
                message: 'Dismiss me to trigger onClose callback.',
                level: 'info',
                duration: 4000,
                onClose: function(){ alert('onClose callback fired!'); }
            });
        """)
