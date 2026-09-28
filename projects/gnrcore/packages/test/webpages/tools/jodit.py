# -*- coding: utf-8 -*-

"Jodit HTML editor"

SAMPLE_HTML = (
    '<h2>Jodit editor</h2>'
    '<p>Type <strong>here</strong>, or press <em>Source</em> in the toolbar '
    'to edit the HTML with CodeMirror.</p>'
    '<ul><li>one</li><li>two</li></ul>'
)

LEGACY_HTML = (
    '<div style="text-align: center;"><span style="font-size: 18px;"><b>Circular 12</b></span></div>'
    '<div>&nbsp;</div>'
    '<p class="intro" align="justify">Text with <font color="#ff0000">font</font>, '
    '<u>underline</u> and <i>italic</i>.</p>'
    '<table border="1" cellpadding="2" cellspacing="0" style="width: 100%; border-collapse: collapse;">'
    '<tbody><tr><td style="width: 50%;">a</td><td>b</td></tr></tbody></table>'
    '<p><a href="https://www.genropy.org" target="_blank">link</a></p>'
    '<p><iframe width="320" height="120" src="about:blank" frameborder="0"></iframe></p>'
    '<div style="page-break-after: always;"><span style="display: none;">&nbsp;</span></div>'
    '<div style="height: 12px;"></div>'
)


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_00_plain(self, pane):
        "HTML bound to a datapath, stored value shown below"
        pane.data('.html', SAMPLE_HTML)
        pane.joditEditor(value='^.html', height='260px', width='700px')
        pane.div('Stored value (debounced 500ms, flushed on blur):', font_weight='bold', margin_top='12px')
        pane.simpleTextarea(value='^.html', height='100px', width='700px',
                            font_family='monospace', font_size='12px')

    def test_01_toolbar(self, pane):
        "Toolbar presets, a custom button list and no toolbar"
        pane.data('.html', SAMPLE_HTML)
        pane.data('.toolbar', 'standard')
        fb = pane.formbuilder(cols=1)
        fb.filteringSelect(value='^.toolbar', lbl='Toolbar',
                           values='minimal,simple,standard,bold|italic|source:custom list')
        pane.dataFormula('.toolbar_value', "toolbar.indexOf('|')>=0 ? toolbar.split('|').join(',') : toolbar",
                         toolbar='^.toolbar')
        pane.joditEditor(value='^.html', toolbar='^.toolbar_value', height='220px', width='700px')
        pane.div('No toolbar:', font_weight='bold', margin_top='12px')
        pane.joditEditor(value='^.html', toolbar=False, height='120px', width='700px')

    def test_02_mode(self, pane):
        "View switched from the toolbar Source button or from outside through mode"
        pane.data('.html', SAMPLE_HTML)
        pane.data('.mode', 'wysiwyg')
        pane.radioButtonText(value='^.mode', values='wysiwyg:Visual,source:HTML,split:Split')
        pane.joditEditor(value='^.html', mode='^.mode', height='300px', width='900px')
        pane.div('^.mode', margin_top='6px')

    def test_03_readonly_disabled(self, pane):
        "readOnly and disabled toggled at runtime"
        pane.data('.html', SAMPLE_HTML)
        fb = pane.formbuilder(cols=2)
        fb.checkbox(value='^.readOnly', label='readOnly')
        fb.checkbox(value='^.disabled', label='disabled')
        pane.joditEditor(value='^.html', readOnly='^.readOnly', disabled='^.disabled',
                         height='220px', width='700px')

    def test_04_content_styles(self, pane):
        "Content CSS isolated in the editor iframe, edited live"
        pane.data('.html', '<p class="note">A paragraph with class <b>note</b>.</p><p>Plain paragraph.</p>')
        pane.data('.css', 'body{width:12cm;border:1px dashed silver;padding:4px} .note{color:darkred}')
        bc = pane.borderContainer(height='280px', width='900px')
        bc.contentPane(region='right', width='300px', splitter=True).codemirror(
            value='^.css', config_mode='css', height='100%')
        bc.contentPane(region='center').joditEditor(value='^.html', contentStyles='^.css', height='100%')

    def test_05_legacy_markup(self, pane):
        "CKEditor 3 markup (style, class, div, font, table, iframe, page break) kept as written"
        pane.data('.html', LEGACY_HTML)
        pane.joditEditor(value='^.html', nodeId='joditLegacy', height='300px', width='700px')
        pane.button('Compare', action="""
            var d = document.createElement('div');
            d.innerHTML = original;
            var v = genro.nodeById('joditLegacy').externalWidget.value;
            SET .editor_value = v;
            SET .result = v == d.innerHTML ? 'identical' : 'DIFFERENT';
        """, original=LEGACY_HTML)
        pane.div('^.result', font_weight='bold')
        pane.simpleTextarea(value='^.editor_value', height='120px', width='700px',
                            font_family='monospace', font_size='12px')

    def test_06_no_write_on_load(self, pane):
        "Loading a value never writes back: changes equal loads until the user edits"
        pane.data('.html', LEGACY_HTML)
        pane.data('.changes', 0)
        pane.data('.loads', 0)
        pane.dataController("SET .changes = changes + 1;", html='^.html', changes='=.changes')
        fb = pane.formbuilder(cols=3)
        fb.button('Load another value', action="""SET .loads = loads + 1;
                                                  SET .html = legacy + '<p>' + new Date().toLocaleTimeString() + '</p>';""",
                  loads='=.loads', legacy=LEGACY_HTML)
        fb.div('^.loads', lbl='Loads')
        fb.div('^.changes', lbl='Value changes')
        pane.joditEditor(value='^.html', height='200px', width='700px')

    def test_07_shared(self, pane):
        "Two editors sharing the same datapath"
        pane.data('.html', SAMPLE_HTML)
        bc = pane.borderContainer(height='260px', width='900px')
        bc.contentPane(region='left', width='50%', splitter=True).joditEditor(value='^.html', toolbar='minimal',
                                                                              height='100%')
        bc.contentPane(region='center').joditEditor(value='^.html', toolbar='minimal', height='100%')

    def test_08_options(self, pane):
        "Placeholder, statusbar, enter='br', no iframe and a raw Jodit option"
        pane.joditEditor(value='^.html', placeholder='Write something...', statusbar=True, enter='br',
                         iframe=False, config_spellcheck=True, height='200px', width='700px')
        pane.simpleTextarea(value='^.html', height='80px', width='700px',
                            font_family='monospace', font_size='12px', margin_top='8px')

    def test_09_extended(self, pane):
        "ExtendedJoditEditor: side CSS pane applied live, bodyStyle as the printable box"
        pane.data('.html', '<p class="note">Text inside a 12cm box.</p>')
        pane.data('.css', '.note{color:darkred}')
        pane.data('.bodyStyle', 'width:12cm;min-height:4cm;outline:1px dashed silver')
        pane.textbox(value='^.bodyStyle', width='40em')
        pane.ExtendedJoditEditor(value='^.html', css_value='^.css', bodyStyle='^.bodyStyle',
                                 height='300px', width='950px')

    def test_10_textarea_editor(self, pane):
        "simpleTextArea(editor=True) with the floating editor button and voice input"
        pane.data('.html', SAMPLE_HTML)
        pane.simpleTextArea(value='^.html', editor=True, speech=True, height='150px', width='600px')

    def test_11_quickeditor(self, pane):
        "quickEditor in a formbuilder, its dialog opened by the side button"
        pane.data('.html', SAMPLE_HTML)
        fb = pane.formbuilder(cols=1)
        fb.quickEditor(value='^.html', lbl='Quick', height='80px', width='400px')
        fb.textbox(value='^.other', lbl='Next field')
