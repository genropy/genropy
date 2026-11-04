"""A modal dialog keeps Tab inside itself."""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_1_tab_trap(self, pane):
        """Tab past the last field goes back to the first, Shift+Tab the other way, never to the page behind."""
        pane.button('Behind the dialog', nodeId='tab_trap_behind')
        dlg = pane.dialog(title='Tab trap', nodeId='tab_trap_dlg')
        fb = dlg.div(padding='10px').formlet(cols=1)
        fb.textbox(value='^.first', lbl='First', nodeId='tab_trap_first')
        fb.textbox(value='^.middle', lbl='Middle')
        fb.textbox(value='^.last', lbl='Last', nodeId='tab_trap_last')
        pane.button('Open dialog', action="genro.wdgById('tab_trap_dlg').show();")
        pane.button('Check Tab trap', action="""
            const dlg = genro.wdgById('tab_trap_dlg');
            dlg.show();
            const first = genro.nodeById('tab_trap_first').widget.focusNode;
            const last = genro.nodeById('tab_trap_last').widget.focusNode;
            const behind = genro.nodeById('tab_trap_behind').widget.focusNode;
            const tab = function(node, shift){
                node.focus();
                node.dispatchEvent(new KeyboardEvent('keydown', {key: 'Tab', keyCode: 9, which: 9,
                                                                 shiftKey: !!shift, bubbles: true, cancelable: true}));
                return document.activeElement;
            };
            const failures = [];
            if(tab(last) !== first){ failures.push('Tab on the last field'); }
            if(tab(first, true) !== last){ failures.push('Shift+Tab on the first field'); }
            if(!dojo.isDescendant(tab(behind), dlg.domNode)){ failures.push('Tab from the page behind'); }
            dlg.hide();
            this.setRelativeData('.trap_result', failures.length ?
                'FAIL: ' + failures.join(', ') : 'PASS: Tab stays inside the dialog');
        """)
        pane.div('^.trap_result')
