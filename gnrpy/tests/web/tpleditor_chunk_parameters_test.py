"""Structural checks on the templateChunk palette editor (issue #1283).

Every pane here is built through the same entry point the browser uses --
``remoteBuilder`` -> ``te_chunkEditorPane`` -- on a real site: the component
under test is the one in this working tree and no struct object is faked.
"""

import inspect
import os

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.web.gnrdummysite import GnrDummySite

CHUNK_COMPONENT = 'gnrcomponents/tpleditor:ChunkEditor'
CHUNK_TABLE = 'adm.htmltemplate'
GRID_DATAPATHS = ('.varsgrid', '.parametersgrid')


def struct_nodes(struct):
    """Depth first walk of a built struct, yielding every node in it."""
    for node in struct.nodes:
        yield node
        if isinstance(node.value, Bag):
            yield from struct_nodes(node.value)


class TestChunkEditorParameters(BaseGnrTest):
    """No daemon is started for this class: nothing here may need one."""

    @classmethod
    def setup_class(cls):
        super().setup_class()
        app = GnrApp(cls.test_instance_name)
        app.db.model.check(applyChanges=True)
        app.db.commit()
        cls.site = GnrDummySite(cls.test_instance_name, site_name=cls.test_instance_name)

    def chunk_editor_page(self):
        page = self.site.dummyPage
        page.mixinComponent(CHUNK_COMPONENT)
        return page

    def chunk_editor_pane(self, **kwargs):
        return self.site.dummyPage.remoteBuilder(handler='te_chunkEditorPane',
                                                 py_requires=CHUNK_COMPONENT,
                                                 table=CHUNK_TABLE,
                                                 paletteId='tpl_editor_floating',
                                                 **kwargs)

    def metadata_grids(self, pane):
        """Region and store of every bagGrid of the Metadata tab, by datapath."""
        result = {}
        for node in struct_nodes(pane):
            datapath = node.attr.get('datapath')
            if datapath in GRID_DATAPATHS:
                stores = [n.attr['storepath'] for n in struct_nodes(node.value)
                          if n.attr.get('tag') == 'BagStore']
                result[datapath] = dict(region=node.attr.get('region'),
                                        height=node.attr.get('height'),
                                        storepath=stores[0] if stores else None)
        return result

    def save_buttons(self, pane):
        """The save buttons of the palette bars, the ones compiling the chunk."""
        return [node for node in struct_nodes(pane)
                if node.attr.get('tag') == 'SlotButton'
                and 'te_compileTemplate' in (node.attr.get('action') or '')]

    def test_component_under_test(self):
        # the editable install resolves gnr.* to the main checkout, so make sure
        # the component being exercised is the one in this working tree
        mixined = self.site.dummyPage.mixinComponent(CHUNK_COMPONENT)
        component_file = inspect.getsourcefile(mixined._te_frameChunkInfo)
        assert component_file == os.path.join(self.test_genro_root, 'resources',
                                             'common', 'gnrcomponents', 'tpleditor.py')

    def test_parameters_hidden_by_default(self):
        grids = self.metadata_grids(self.chunk_editor_pane())
        assert '.parametersgrid' not in grids
        # the variables grid keeps the whole Metadata tab, as before #1283
        assert grids['.varsgrid']['region'] == 'center'
        assert grids['.varsgrid']['height'] is None

    def test_parameters_shown_on_request(self):
        grids = self.metadata_grids(self.chunk_editor_pane(showParameters=True))
        assert grids['.parametersgrid']['storepath'] == '#ANCHOR.data.parameters'
        assert grids['.parametersgrid']['region'] == 'center'
        # the variables grid makes room for it, as in the full template editor
        assert grids['.varsgrid']['region'] == 'bottom'
        assert grids['.varsgrid']['height'] == '60%'

    def test_save_button_forwards_the_parameters(self):
        for pane in (self.chunk_editor_pane(), self.chunk_editor_pane(showParameters=True)):
            buttons = self.save_buttons(pane)
            assert buttons
            for button in buttons:
                # .data.parametersbag was a dangling path: nothing ever wrote it
                assert button.attr['pb'] == '=.data.parameters'
                assert button.attr['vb'] == '=.data.varsbag'

    def test_parameter_formats_reach_the_compiled_template(self):
        parameters = Bag()
        parameters.setItem('r_0', Bag(dict(code='occurrences', format='#,##0')))
        parameters.setItem('r_1', Bag(dict(code='notification_url', mask='%s/detail')))
        compiled = self.chunk_editor_page().te_compileTemplate(
            table=CHUNK_TABLE,
            datacontent='<p>$occurrences</p><p>$notification_url</p>',
            varsbag=Bag(), parametersbag=parameters)['compiled']
        attributes = compiled.getAttr('main')
        assert attributes['formats']['occurrences'] == '#,##0'
        assert attributes['masks']['notification_url'] == '%s/detail'
        # parameters are not columns of the template table
        assert 'occurrences' not in attributes['columns']
