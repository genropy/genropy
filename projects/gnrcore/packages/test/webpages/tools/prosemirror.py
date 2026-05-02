# -*- coding: utf-8 -*-

"ProseMirror"


SAMPLE_HTML = (
    '<h2>ProseMirror demo</h2>'
    '<p>Type <strong>here</strong>. Use <em>markdown-style</em> shortcuts:</p>'
    '<ul>'
    '<li><code>## </code> for a heading</li>'
    '<li><code>&gt; </code> for a blockquote</li>'
    '<li><code>1. </code> or <code>* </code> for a list</li>'
    '<li><code>```</code> for a code block</li>'
    '</ul>'
    '<p>Undo with <code>Cmd-Z</code>, redo with <code>Cmd-Shift-Z</code>.</p>'
)


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"

    def test_0_html(self, pane):
        "ProseMirror with HTML output bound to a datapath"
        pane.data('.html', SAMPLE_HTML)
        pane.proseMirrorEditor(value='^.html', height='240px', width='600px',
                               border='1px solid silver', padding='8px')
        pane.div('Output (HTML, debounced 500ms):', font_weight='bold', margin_top='12px')
        pane.simpleTextarea(value='^.html', height='120px', width='600px',
                            font_family='monospace', font_size='12px')

    def test_1_readonly(self, pane):
        "ProseMirror in read-only mode"
        pane.data('.ro', '<h3>Read only</h3><p>You cannot edit this content.</p>')
        pane.proseMirrorEditor(value='^.ro', readOnly=True, height='180px', width='600px',
                               border='1px solid silver', padding='8px')

    def test_2_json(self, pane):
        "ProseMirror with JSON document output"
        initial = (
            '{"type":"doc","content":['
            '{"type":"heading","attrs":{"level":2},"content":[{"type":"text","text":"JSON document"}]},'
            '{"type":"paragraph","content":[{"type":"text","text":"Edits are serialized as a "},'
            '{"type":"text","marks":[{"type":"strong"}],"text":"ProseMirror JSON"},'
            '{"type":"text","text":" tree."}]}'
            ']}'
        )
        pane.data('.doc', initial)
        pane.proseMirrorEditor(value='^.doc', format='json', height='200px', width='600px',
                               border='1px solid silver', padding='8px')
        pane.div('Output (JSON, debounced 500ms):', font_weight='bold', margin_top='12px')
        pane.simpleTextarea(value='^.doc', height='160px', width='600px',
                            font_family='monospace', font_size='12px')

    def test_3_shared(self, pane):
        "Two editors sharing the same HTML datapath"
        pane.data('.shared', '<p>Type in one, the other one updates after the debounce.</p>')
        bc = pane.borderContainer(height='280px', width='100%', border='1px solid silver')
        left = bc.contentPane(region='left', width='50%', splitter=True)
        left.div('Editor A', font_weight='bold', padding='4px')
        left.proseMirrorEditor(value='^.shared', height='220px', padding='8px')
        right = bc.contentPane(region='center')
        right.div('Editor B', font_weight='bold', padding='4px')
        right.proseMirrorEditor(value='^.shared', height='220px', padding='8px')
