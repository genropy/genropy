"""Structural checks on attachmentPreviewViewer (issue #1921).

The viewer stacks an iframe, an img and a video. A hidden img still fetches its
src, so the three elements must not share the url: each one is bound to the src
of its own page, which the routing controller fills only for the selected page
(the routing itself is exercised in gnrjs/tests/attachment_preview_hidden_src.test.js).
The component is built on a real site, from this working tree.
"""

import inspect
import os

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.web.gnrdummysite import GnrDummySite

COMPONENT = 'gnrcomponents/attachmanager/attachmanager:AttachManager'
PAGE_SOURCES = {'iframe': '^.$preview_src.document',
                'img': '^.$preview_src.image',
                'video': '^.$preview_src.video'}


def struct_nodes(struct):
    """Depth first walk of a built struct, yielding every node in it."""
    for node in struct.nodes:
        yield node
        if isinstance(node.value, Bag):
            yield from struct_nodes(node.value)


class TestAttachmentPreviewViewer(BaseGnrTest):
    """No daemon is started for this class: nothing here may need one."""

    @classmethod
    def setup_class(cls):
        super().setup_class()
        app = GnrApp(cls.test_instance_name)
        app.db.model.check(applyChanges=True)
        app.db.commit()
        cls.site = GnrDummySite(cls.test_instance_name, site_name=cls.test_instance_name)

    def viewer(self, src='^.fileurl'):
        page = self.site.dummyPage
        page.mixinComponent(COMPONENT)
        root = page.newSourceRoot()
        root.attachmentPreviewViewer(src=src, currentPreviewZoom='^.zoom')
        return list(struct_nodes(root))

    def test_component_under_test(self):
        mixined = self.site.dummyPage.mixinComponent(COMPONENT)
        component_file = inspect.getsourcefile(mixined.at_attachmentPreviewViewer)
        assert component_file == os.path.join(self.test_genro_root, 'resources', 'common', 'gnrcomponents',
                                             'attachmanager', 'attachmanager.py')

    def test_each_element_loads_only_its_page_src(self):
        nodes = self.viewer()
        for tag, page_src in PAGE_SOURCES.items():
            elements = [node for node in nodes if node.attr.get('tag') == tag]
            assert len(elements) == 1, tag
            assert elements[0].attr['src'] == page_src
        # no element that loads content is bound to the shared url any more
        assert not [node for node in nodes
                    if node.attr.get('tag') in PAGE_SOURCES and node.attr.get('src') == '^.fileurl']

    def test_the_controller_fills_every_page_src(self):
        controllers = [node for node in self.viewer()
                       if node.attr.get('tag') == 'dataController' and node.attr.get('src') == '^.fileurl']
        assert len(controllers) == 1
        controller = controllers[0].attr
        for page_src in PAGE_SOURCES.values():
            assert f'SET {page_src[1:]} =' in controller['script']
        # an empty src must reach the controller too, or the last url would stay on screen
        assert '_if' not in controller
        # a viewer built after the page start, with the src already there
        assert controller['_onBuilt'] is True
