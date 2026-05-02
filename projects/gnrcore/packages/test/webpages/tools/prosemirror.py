# -*- coding: utf-8 -*-

"ProseMirror"

from gnr.core.gnrbag import Bag


def _sample_bag():
    """Build a sample document as gnr.Bag using the canonical schema:
    - block nodes carry tag = type name (paragraph, heading, ...) and PM attrs
    - inline text runs use tag='txt' with the text as cell value, mark names
      joined as a comma-separated 'markers' attribute, and per-mark attrs
      spread on the cell.
    Note: we use 'tag' (not '_tag') because the latter is a Bag framework
    reserved attribute that the XML deserializer interprets as the cell label.
    """
    b = Bag()
    b.setItem('doc', Bag(), tag='doc')
    doc = b['doc']

    doc.setItem('heading_0', Bag(), tag='heading', level=2)
    heading_0 = doc['heading_0']
    heading_0.setItem('txt_0', 'Bag document', tag='txt')

    doc.setItem('paragraph_0', Bag(), tag='paragraph')
    paragraph_0 = doc['paragraph_0']
    paragraph_0.setItem('txt_0', 'Edits are mirrored to a ', tag='txt')
    paragraph_0.setItem('txt_1', 'gnr.Bag', tag='txt', markers='bold')
    paragraph_0.setItem('txt_2', ' tree, ready to query from Python.', tag='txt')

    doc.setItem('paragraph_1', Bag(), tag='paragraph')
    paragraph_1 = doc['paragraph_1']
    paragraph_1.setItem('txt_0', 'See the ', tag='txt')
    paragraph_1.setItem('txt_1', 'Genropy site',
                        tag='txt', markers='link',
                        href='https://genropy.org', title='Genropy')
    paragraph_1.setItem('txt_2', ' for the framework.', tag='txt')

    return b


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
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

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

    def test_4_bag(self, pane):
        "ProseMirror with gnr.Bag output (canonical Tiptap-biased schema)"
        pane.data('.docbag', _sample_bag())
        pane.proseMirrorEditor(value='^.docbag', format='bag',
                               height='220px', width='600px',
                               border='1px solid silver', padding='8px')
        pane.div('Output (gnr.Bag — live tree of the document, Shift+click a node to inspect its attributes):',
                 font_weight='bold', margin_top='12px')
        pane.div(height='280px', width='600px', border='1px solid silver',
                 overflow='auto').tree(storepath='.docbag',
                                       hideValues=False, inspect='shift',
                                       autoCollapse=False,
                                       _class='branchtree noIcon')
