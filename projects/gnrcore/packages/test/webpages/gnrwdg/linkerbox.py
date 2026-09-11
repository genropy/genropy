"""Linker boxes follow the available width."""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler"

    def test_1_responsive(self, pane):
        """Resize each box; search, add and validation must stay inside its header."""
        pane.button('Check layout', action="""
            const boxes = document.querySelectorAll('.linkerbox_test .slotbar');
            const failures = [];
            boxes.forEach(function(bar, index){
                const linker = bar.querySelector('.th_linker');
                if(!linker){return;}
                const field = linker.querySelector('.th_linkerField');
                const bounds = bar.getBoundingClientRect();
                const lr = linker.getBoundingClientRect();
                const fr = field.getBoundingClientRect();
                if(lr.left < bounds.left || lr.right > bounds.right ||
                   (fr.width && (fr.left < lr.left || fr.right > lr.right))){
                    failures.push(index + 1);
                }
            });
            this.setRelativeData('.layout_result', failures.length ?
                'FAIL: boxes ' + failures.join(', ') : 'PASS: all boxes fit');
        """)
        pane.div('^.layout_result')
        for index, width in enumerate(('180px', '280px', '480px', '240px')):
            layout = pane.borderContainer(height='180px', margin_bottom='12px')
            box = layout.contentPane(region='left', width=width, splitter=True,
                                     _class='linkerbox_test')
            layout.contentPane(region='center').div('Drag the splitter')
            form = box.frameForm(
                frameCode='linker_test_%s' % index, datapath='.form_%s' % index,
                store='memory', height='100%', table='adm.user_tag')
            form.record.linkerBox(
                field='user_id', frameCode='linker_box_%s' % index,
                label='User', newRecordOnly=False, openIfEmpty=True,
                embedded=False,
                _class='pbl_roundedGroup th_linkerAlwaysOpen'
                if index == 3 else 'pbl_roundedGroup',
                formResource='Form' if index else None,
                validate_notnull=index == 2)
            pane.dataController('frm.newrecord();', frm=form.js_form,
                                _onStart=True)

    def test_2_standalone(self, pane):
        """Standalone linkers retain their natural and explicit field widths."""
        form = pane.frameForm(frameCode='standalone_linker_test',
                             datapath='.standalone', store='memory',
                             height='100px', table='adm.user_tag')
        fb = form.record.formbuilder(cols=2)
        fb.div().linker(field='user_id', openIfEmpty=True, embedded=False)
        fb.div().linker(field='tag_id', width='20em',
                        openIfEmpty=True, embedded=False)
        pane.dataController('frm.newrecord();', frm=form.js_form,
                            _onStart=True)
