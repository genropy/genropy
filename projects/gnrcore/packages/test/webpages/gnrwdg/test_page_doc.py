"""How the documentation works in GenroPy: the page's own doc and its parts.

A page in the public frame: the ⓘ next to its title opens the doc of the page
(page:test/test_page_doc:) in the help panel, a whole guide of the manual. Each
block of the page has a helpcode, page:test/test_page_doc:<helpcode>, and its
ⓘ opens that chapter in a popup at the icon.

Needs <experimental><gui inlinedoc="true"/></experimental> in the
instanceconfig, a logged user and the demo manual: build and link it once from
webpages/gnrwdg/demo_inline_docs.py (test_0_setup), its inline_docs page holds
these sections.
"""

BLOCKS = (('addresses', '!!Addresses',
           '!!Every field, card, table and part of a page has an address: the same doc wherever it appears.'),
          ('sources', '!!Two sources',
           '!!The published manual, by label, and the notes the customer writes on the page.'),
          ('visibility', '!!Who sees what',
           '!!The ⓘ only where something documents the address; documenters see the missing ones in red.'),
          ('editing', '!!Writing a note',
           '!!Markdown in place, images, the row\'s values as variables, one file per language.'),
          ('storage', '!!Where the notes live',
           '!!The private inlinedoc storage, behind an experimental flag.'),
          ('code', '!!In the code',
           '!!field(), helpcode=, roundedGroup, groupletCard(doc=), docHelpButton.'))


class GnrCustomWebPage(object):
    py_requires = 'public:Public'

    def main(self, root, **kwargs):
        """The guide's blocks, each with the ⓘ of its chapter"""
        frame = root.rootContentPane(title='!!How the documentation works', **kwargs)
        center = frame.center.contentPane(overflow='auto', padding='16px')
        grid = center.div(display='grid', grid_template_columns='repeat(auto-fill, minmax(22em, 1fr))',
                          gap='12px')
        for helpcode, title, summary in BLOCKS:
            box = grid.div(height='130px', position='relative')
            content = box.roundedGroup(title=title, helpcode=helpcode, height='100%')
            content.div(summary, padding='8px', line_height='1.4')
