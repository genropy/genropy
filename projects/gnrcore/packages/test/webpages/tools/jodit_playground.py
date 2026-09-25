# -*- coding: utf-8 -*-

"Jodit Playground"

SAMPLE_WELCOME = (
    '<h2>joditEditor</h2>'
    '<p>A WYSIWYG HTML editor whose <strong>HTML view is CodeMirror 6</strong>: '
    'press <em>Source</em> in the toolbar, or pick a view on the right.</p>'
    '<ul><li>Split view: type in either side, the other follows.</li>'
    '<li>The stored HTML below updates on blur and after a short pause.</li>'
    '<li>Markup is kept as written: no schema rewrites your content.</li></ul>'
    '<table style="width: 100%; border-collapse: collapse;" border="1" cellpadding="4">'
    '<tbody><tr><th>Feature</th><th>Attribute</th></tr>'
    '<tr><td>Toolbar presets</td><td>toolbar</td></tr>'
    '<tr><td>View</td><td>mode</td></tr>'
    '<tr><td>Content CSS</td><td>contentStyles</td></tr>'
    '<tr><td>Page box</td><td>bodyStyle</td></tr></tbody></table>'
)

SAMPLE_LEGACY = (
    '<div style="text-align: center;"><span style="font-size: 18px;"><b>Circular 12</b></span></div>'
    '<div>&nbsp;</div>'
    '<p class="note" align="justify">Content written with CKEditor 3: <font color="#ff0000">font</font>, '
    '<u>underline</u>, <i>italic</i>, a class and inline styles, all kept on save.</p>'
    '<table border="1" cellpadding="2" cellspacing="0" style="width: 100%; border-collapse: collapse;">'
    '<tbody><tr><td style="width: 50%;">a</td><td>b</td></tr></tbody></table>'
    '<div style="page-break-after: always;"><span style="display: none;">&nbsp;</span></div>'
    '<p><a href="https://www.genropy.org" target="_blank">genropy.org</a></p>'
)

SAMPLE_LETTER = (
    '<p style="text-align: right;">Milan, 24 September 2026</p>'
    '<p>Dear customer,</p>'
    '<p class="note">this letter is edited inside the printable box of the letterhead: '
    'switch <em>Page box</em> on and off to see it.</p>'
    '<p>Kind regards,</p>'
    '<p><strong>Softwell</strong></p>'
)

SAMPLES = {'welcome': SAMPLE_WELCOME, 'legacy': SAMPLE_LEGACY, 'letter': SAMPLE_LETTER}

PAGE_BOX = 'width:120mm;min-height:80mm;outline:1px dashed silver'


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_playground(self, pane):
        "Live joditEditor playground: toolbar, view, read only, content CSS, page box and samples"
        pane.data('.source', SAMPLE_WELCOME)
        pane.data('.config.toolbar', 'standard')
        pane.data('.config.mode', 'wysiwyg')
        pane.data('.config.sample', 'welcome')
        pane.data('.config.css', '.note{color:#1d4f91;font-style:italic}')
        bc = pane.borderContainer(height='820px', width='100%', border='1px solid silver')

        controls = bc.contentPane(region='right', width='300px', splitter=True, padding='8px',
                                  border_left='1px solid silver', background='#f7f7f7')
        controls.div('Editor settings', font_weight='bold', padding_bottom='6px')
        fb = controls.formbuilder(cols=1, border_spacing='4px', width='100%')
        fb.filteringSelect(value='^.config.sample', lbl='Sample',
                           values='welcome:Welcome,legacy:CKEditor 3 content,letter:Letter')
        fb.filteringSelect(value='^.config.toolbar', lbl='Toolbar',
                           values='minimal:minimal,simple:simple,standard:standard')
        fb.radioButtonText(value='^.config.mode', lbl='View',
                           values='wysiwyg:Visual,source:HTML,split:Split')
        fb.checkbox(value='^.config.readOnly', label='Read only')
        fb.checkbox(value='^.config.disabled', label='Disabled')
        fb.checkbox(value='^.config.pageBox', label='Page box (bodyStyle)')
        controls.div('Content CSS (contentStyles)', font_weight='bold', padding='10px 0 4px 0')
        controls.div(height='180px', border='1px solid silver').codemirror(value='^.config.css',
                                                                           config_mode='css', height='100%')
        controls.div('Changing the toolbar rebuilds the editor, keeping the content.',
                     font_size='0.85em', color='#666', padding_top='8px')
        controls.dataController("SET .source = samples[sample];", sample='^.config.sample', samples=SAMPLES,
                                _onStart=False)
        controls.dataFormula('.config.bodyStyle', "pageBox ? box : null", pageBox='^.config.pageBox', box=PAGE_BOX)

        bc.contentPane(region='center', overflow='hidden', padding='4px').joditEditor(
            nodeId='joditplay_editor', value='^.source', toolbar='^.config.toolbar', mode='^.config.mode',
            readOnly='^.config.readOnly', disabled='^.config.disabled',
            contentStyles='^.config.css', bodyStyle='^.config.bodyStyle',
            placeholder='Write something...', statusbar=True, height='100%')

        mirror = bc.contentPane(region='bottom', height='200px', splitter=True, padding='6px',
                                border_top='1px solid silver', background='#fafbfc')
        mirror.div('Stored HTML (what goes to the database)', font_weight='bold', font_size='0.9em',
                   padding_bottom='4px', color='#555')
        mirror.div(height='160px', border='1px solid #ddd').codemirror(value='^.source', config_mode='html',
                                                                       lineWrapping=True, readOnly=True,
                                                                       height='100%')
