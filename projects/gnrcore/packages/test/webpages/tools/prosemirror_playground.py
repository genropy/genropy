# -*- coding: utf-8 -*-

"ProseMirror Playground"

from gnr.core.gnrbag import Bag


SAMPLE_SIMPLE = (
    '<p>Type something here. The editor is bound to a datapath; '
    'the bottom mirror updates after a 500ms debounce.</p>'
)

SAMPLE_FORMATTED = (
    '<h2>Formatted document</h2>'
    '<p>This sample uses <strong>bold</strong>, <em>italic</em>, '
    '<code>inline code</code> and <a href="https://genropy.org">links</a>.</p>'
    '<blockquote><p>Block quotes are also part of the basic schema.</p></blockquote>'
    '<p>Try <code>Cmd-B</code>, <code>Cmd-I</code>, <code>Cmd-Z</code> '
    'and the markdown-ish input rules (<code># </code>, <code>&gt; </code>, '
    '<code>* </code>, <code>1. </code>, <code>```</code>).</p>'
)

SAMPLE_LISTS = (
    '<h3>Lists</h3>'
    '<ul>'
    '<li>First bullet</li>'
    '<li>Second bullet'
    '<ul><li>Nested item A</li><li>Nested item B</li></ul>'
    '</li>'
    '<li>Third bullet</li>'
    '</ul>'
    '<ol>'
    '<li>Numbered one</li>'
    '<li>Numbered two</li>'
    '<li>Numbered three</li>'
    '</ol>'
    '<p>Use <code>Tab</code> / <code>Shift-Tab</code> to nest / lift list items.</p>'
)

SAMPLE_HEADINGS = (
    '<h1>Heading level 1</h1>'
    '<p>Body text under H1.</p>'
    '<h2>Heading level 2</h2>'
    '<p>Body text under H2.</p>'
    '<h3>Heading level 3</h3>'
    '<p>Body text under H3.</p>'
    '<h4>Heading level 4</h4>'
    '<p>Body text under H4.</p>'
)

SAMPLE_MIXED = (
    '<h2>Mixed content</h2>'
    '<p>Paragraph with <strong>bold</strong>, <em>italic</em> and a '
    '<a href="https://prosemirror.net">link to ProseMirror</a>.</p>'
    '<table>'
    '<tr><th>Header A</th><th>Header B</th><th>Header C</th></tr>'
    '<tr><td>cell 1A</td><td>cell 1B</td><td>cell 1C</td></tr>'
    '<tr><td>cell 2A</td><td>cell 2B</td><td>cell 2C</td></tr>'
    '</table>'
    '<p>Tables only render with the <code>basicWithListsAndTables</code> '
    'schema. Switch the schema selector to see them in action.</p>'
    '<ul><li>list item</li><li>another item</li></ul>'
    '<blockquote><p>Block quote at the end.</p></blockquote>'
)

SAMPLES_HTML = {
    'simple': SAMPLE_SIMPLE,
    'formatted': SAMPLE_FORMATTED,
    'lists': SAMPLE_LISTS,
    'headings': SAMPLE_HEADINGS,
    'mixed': SAMPLE_MIXED,
}


def _bag_simple():
    b = Bag()
    b.setItem('doc', Bag(), tag='doc')
    doc = b['doc']
    doc.setItem('paragraph_0', Bag(), tag='paragraph')
    doc['paragraph_0'].setItem('txt_0', 'Type something here. The Bag tree '
                               'updates live after each debounce.', tag='txt')
    return b


def _bag_formatted():
    b = Bag()
    b.setItem('doc', Bag(), tag='doc')
    doc = b['doc']
    doc.setItem('heading_0', Bag(), tag='heading', level=2)
    doc['heading_0'].setItem('txt_0', 'Formatted document', tag='txt')
    doc.setItem('paragraph_0', Bag(), tag='paragraph')
    p0 = doc['paragraph_0']
    p0.setItem('txt_0', 'This sample uses ', tag='txt')
    p0.setItem('txt_1', 'bold', tag='txt', markers='bold')
    p0.setItem('txt_2', ', ', tag='txt')
    p0.setItem('txt_3', 'italic', tag='txt', markers='italic')
    p0.setItem('txt_4', ' and ', tag='txt')
    p0.setItem('txt_5', 'links', tag='txt', markers='link',
               href='https://genropy.org', title='Genropy')
    p0.setItem('txt_6', '.', tag='txt')
    return b


SAMPLES_BAG = {
    'simple': _bag_simple,
    'formatted': _bag_formatted,
}


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_playground(self, pane):
        "Live ProseMirror playground: switch schema, setup, format and sample on the fly. Each change rebuilds the editor preserving content where possible."
        pane.data('.config.schema', 'basicWithLists')
        pane.data('.config.setup', 'full')
        pane.data('.config.format', 'html')
        pane.data('.config.sample', 'formatted')
        pane.data('.config.menubar', True)
        pane.data('.config.readOnly', False)
        pane.data('.source', SAMPLE_FORMATTED)

        bc = pane.borderContainer(height='820px', width='100%',
                                  border='1px solid silver')

        # ---- Right panel: controls ----
        controls = bc.contentPane(region='right', width='280px',
                                  splitter=True, padding='8px',
                                  border_left='1px solid silver',
                                  background='#f7f7f7')
        controls.div('Editor settings', font_weight='bold',
                     padding_bottom='6px')
        fb = controls.formbuilder(cols=1, border_spacing='4px', width='100%')
        fb.filteringSelect(value='^.config.schema', lbl='Schema',
                           values='basic:basic,'
                                  'basicWithLists:basic + lists,'
                                  'basicWithListsAndTables:basic + lists + tables')
        fb.filteringSelect(value='^.config.setup', lbl='Setup',
                           values='minimal:minimal (no rules / no toolbar),'
                                  'example:example (markdown rules),'
                                  'full:full (toolbar + tables + trailing)')
        fb.filteringSelect(value='^.config.format', lbl='Format',
                           values='html:HTML,'
                                  'json:ProseMirror JSON,'
                                  'bag:gnr.Bag tree')
        fb.filteringSelect(value='^.config.sample', lbl='Sample content',
                           values='simple,formatted,lists,headings,mixed')
        fb.checkbox(value='^.config.menubar', label='Menubar (toolbar)')
        fb.checkbox(value='^.config.readOnly', label='Read only')

        controls.div('Tip: switching schema or setup rebuilds the editor.',
                     font_size='0.85em', color='#666', padding_top='8px')

        # When schema/setup/menubar/format/readOnly change at runtime, ask
        # the editor (resolved by domid via getNodes) to rebuild itself.
        # The mixin routes through gnr.GnrEditorPlugin.rebuild which preserves
        # the current content (re-serializing in the previous format).
        controls.dataController("""
            var nodes = genro.dom.getNodes('proseMirrorEditor', 'pmplay_editor');
            if(!nodes || !nodes.length){ return; }
            var view = nodes[0].externalWidget;
            if(!view){ return; }
            view.gnr.rebuild(view.sourceNode, {
                schema: schema, setup: setup, format: format,
                menubar: menubar, editable: !readOnly
            });
        """, schema='^.config.schema', setup='^.config.setup',
            format='^.config.format', menubar='^.config.menubar',
            readOnly='^.config.readOnly',
            _onStart=False)

        # When the sample selector changes, swap the source datapath with the
        # right Python-side sample. Bag samples come from a callable factory
        # since Bag instances are mutable and we want a fresh tree each time.
        controls.dataController("""
            if(format === 'bag'){
                var fn = SAMPLES_BAG[sample] || SAMPLES_BAG.simple;
                SET .source = fn ? fn() : null;
            } else {
                SET .source = SAMPLES_HTML.getItem(sample);
            }
        """, sample='^.config.sample', format='^.config.format',
            SAMPLES_HTML=SAMPLES_HTML,
            SAMPLES_BAG={k: v() for k, v in SAMPLES_BAG.items()},
            _onStart=False)

        # ---- Center: the editor ----
        editor_pane = bc.contentPane(region='center', overflow='hidden',
                                     padding='4px')
        editor_pane.proseMirrorEditor(
            nodeId='pmplay_editor',
            value='^.source',
            schema='basicWithLists',  # initial; rebuild will switch it
            setup='full',
            format='html',
            menubar=True,
            readOnly=False,
            height='100%', width='100%',
            border='1px solid silver', padding='8px')

        # ---- Bottom: live mirror ----
        mirror = bc.contentPane(region='bottom', height='220px',
                                splitter=True, padding='6px',
                                border_top='1px solid silver',
                                background='#fafbfc')
        mirror.div('Mirror — live view of the document in the current format',
                   font_weight='bold', font_size='0.9em',
                   padding_bottom='4px', color='#555')
        # Two views over the same datapath: textarea (good for html/json) and
        # tree (good for bag). The user can resize the split to look at both.
        mbc = mirror.borderContainer(height='180px', width='100%')
        ta_pane = mbc.contentPane(region='left', width='60%', splitter=True,
                                  padding='2px')
        ta_pane.div('Text view (HTML / JSON / serialized Bag XML):',
                    font_size='0.85em', color='#777')
        ta_pane.simpleTextarea(value='^.source', width='100%', height='150px',
                               font_family='monospace', font_size='12px')
        tree_pane = mbc.contentPane(region='center', padding='2px')
        tree_pane.div('Tree view (only meaningful when format=bag):',
                      font_size='0.85em', color='#777')
        tree_pane.div(height='150px', width='100%',
                      border='1px solid #ddd',
                      overflow='auto').tree(storepath='.source',
                                            hideValues=False, inspect='shift',
                                            autoCollapse=False,
                                            _class='branchtree noIcon')
