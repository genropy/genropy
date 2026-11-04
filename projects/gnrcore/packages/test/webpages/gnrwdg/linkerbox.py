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

    def test_3_flex(self, pane):
        """Flex linker boxes are as tall as their content; max_height makes the center scroll."""
        pane.button('Check heights', action="""
            const failures = [];
            document.querySelectorAll('.linkerbox_flex_test .th_linkerBoxFlex').forEach(function(box, index){
                const center = box.querySelector('.th_linkerBoxFlexCenter');
                const capped = box.classList.contains('linkerbox_flex_capped');
                const scrolls = center.scrollHeight > center.clientHeight + 1;
                if(scrolls !== capped){
                    failures.push(index + 1);
                }
            });
            this.setRelativeData('.flex_result', failures.length ?
                'FAIL: boxes ' + failures.join(', ') : 'PASS: heights follow the content');
        """)
        pane.div('^.flex_result')
        cases = (dict(label='User', _class='pbl_roundedGroup'),
                 dict(label='User (formResource)', formResource='Form', _class='pbl_roundedGroup'),
                 dict(label='User, max 60px', max_height='60px',
                      _class='pbl_roundedGroup linkerbox_flex_capped'))
        for index, case in enumerate(cases):
            form = pane.frameForm(frameCode='linker_flex_test_%s' % index, datapath='.flex_%s' % index,
                                  store='memory', height='220px', margin_bottom='12px', table='adm.user_tag')
            column = form.record.div(display='flex', flex_direction='column', gap='8px', padding='6px',
                                     _class='linkerbox_flex_test')
            column.linkerBox(field='user_id', frameCode='linker_flex_box_%s' % index, flex=True,
                             newRecordOnly=False, openIfEmpty=True, embedded=False, **case)
            column.div('Content below the box follows it', _class='linkerbox_flex_below')
            pane.dataController('frm.newrecord();', frm=form.js_form, _onStart=True)

    def test_4_field_air(self, pane):
        """An open linker field never touches its bar: theme tokens give it air above and below."""
        pane.button('Check field air', action="""
            const failures = [];
            document.querySelectorAll('.th_linkerBar').forEach(function(bar, index){
                const linker = bar.querySelector('.th_linker');
                if(!linker || !linker.offsetHeight){return;}
                const open = linker.classList.contains('th_enableLinker') || bar.closest('.th_linkerAlwaysOpen');
                if(!open){return;}
                const br = bar.getBoundingClientRect();
                const lr = linker.getBoundingClientRect();
                if(lr.top - br.top < 1 || br.bottom - lr.bottom < 1){
                    failures.push(index + 1);
                }
            });
            this.setRelativeData('.air_result', failures.length ?
                'FAIL: bars ' + failures.join(', ') : 'PASS: open fields keep their air');
        """)
        pane.div('^.air_result')
        form = pane.frameForm(frameCode='linker_air_test', datapath='.air', store='memory',
                              height='240px', table='adm.user_tag')
        column = form.record.div(display='flex', flex_direction='column', gap='8px', padding='6px')
        column.linkerBox(field='user_id', frameCode='linker_air_flex', flex=True, alwaysOpen=True,
                         label='Flex, always open', newRecordOnly=False, embedded=False, formResource='Form')
        classic = column.div(height='90px', position='relative')
        classic.linkerBox(field='tag_id', frameCode='linker_air_classic', alwaysOpen=True,
                          label='Classic, always open', newRecordOnly=False, embedded=False)
        pane.dataController('frm.newrecord();', frm=form.js_form, _onStart=True)
