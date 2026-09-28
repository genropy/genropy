"""Structural checks on the two field groups of the notification form.

The panes are built through the resource of this working tree, on a real
site and against the real adm.notification model, so the struct here is the
one the browser is served: no struct object is faked.

What is pinned down is the readability of the group, not its decoration.
The captions are long enough ("If empty the cancel button is hidden") that a
label beside the input would squeeze it to nothing, hence the formlet with
labels on top; and the two audience criteria are meant to be compared side
by side, hence a single column each.
"""
import os

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import gnrImport
from gnr.web.gnrdummysite import GnrDummySite
from gnr.web.gnrwebstruct import GnrDomSrc_dojo_11

from core.common import BaseGnrTest


def struct_nodes(struct):
    """Depth first walk of a built struct, yielding every node in it."""
    for node in struct.nodes:
        yield node
        if isinstance(node.value, Bag):
            yield from struct_nodes(node.value)


class TestNotificationFormPanes(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        bootstrap_app = GnrApp(cls.test_instance_name)
        bootstrap_app.db.model.check(applyChanges=True)
        bootstrap_app.db.commit()
        bootstrap_app.db.closeConnection()
        cls.site = GnrDummySite(cls.test_instance_name,
                                site_name=cls.test_instance_name)
        module_path = os.path.join(
            cls.site.db.application.packages['adm'].packageFolder,
            'resources', 'tables', 'notification', 'th_notification.py',
        )
        cls.th_notification = gnrImport(module_path, avoidDup=True)

    @classmethod
    def teardown_class(cls):
        if getattr(cls, 'site', None):
            cls.site.db.closeConnection()
        super().teardown_class()

    # --- fixtures ----------------------------------------------------------

    def _build(self, panename):
        """Build one pane of the form on a fresh struct root. The table is
        declared on the container the way the form's own datapath pane does,
        so field() resolves the real columns."""
        component = self.th_notification.Form()
        component.page = self.site.dummyPage
        root = GnrDomSrc_dojo_11.makeRoot(self.site.dummyPage)
        pane = root.child('div', childname='rec', table='adm.notification')
        getattr(component, panename)(pane)
        return root.getNode('rec').value.getNode('#0')

    def _fields(self, formlet):
        """The dbfield of every item of a formlet, in layout order, with the
        colspan it was given."""
        return [(node.attr['dbfield'].split('.')[-1], node.attr.get('colspan'))
                for node in struct_nodes(formlet.value) if node.attr.get('dbfield')]

    # --- both groups -------------------------------------------------------

    def test_groups_are_formlets_with_labels_on_top(self):
        for panename in ('confirmationSettingsPane', 'generalSettingsPane'):
            formlet = self._build(panename)
            assert 'formlet' in formlet.attr['_class'], panename
            assert formlet.attr['lbl_side'] == 'top', panename

    # --- confirmation settings ---------------------------------------------

    def test_confirmation_group_is_a_single_column(self):
        formlet = self._build('confirmationSettingsPane')
        assert formlet.attr['cols'] == 1
        assert [f for f, _ in self._fields(formlet)] == [
            'confirm_label', 'confirm_button_label', 'cancel_button_label']

    def test_every_caption_says_what_leaving_it_empty_does(self):
        formlet = self._build('confirmationSettingsPane')
        placeholders = {node.attr['dbfield'].split('.')[-1]: node.attr.get('placeholder')
                        for node in struct_nodes(formlet.value)
                        if node.attr.get('dbfield')}
        assert placeholders['confirm_label'] == '!!If empty no confirmation checkbox is shown'
        assert placeholders['cancel_button_label'] == '!!If empty the cancel button is hidden'
        # the confirm button always exists: its placeholder is the default caption
        assert placeholders['confirm_button_label'] == '!!Confirm'

    # --- general settings --------------------------------------------------

    def test_audience_criteria_share_a_row(self):
        formlet = self._build('generalSettingsPane')
        assert formlet.attr['cols'] == 2
        fields = dict(self._fields(formlet))
        assert fields['title'] == 2, "the title is the one field spanning the group"
        assert not fields['tag_rule'], "tag rule and group code must sit side by side"
        assert not fields['group_code']

    def test_general_group_holds_everything_but_the_captions(self):
        formlet = self._build('generalSettingsPane')
        fields = [f for f, _ in self._fields(formlet)]
        assert fields == ['title', 'tag_rule', 'group_code', 'letterhead_id',
                          'dynamic_list', 'start_date', 'end_date']

    def test_audience_criteria_keep_their_popup_layout(self):
        """`cols` on a checkboxtext is the popup's own column count: the
        formlet must not swallow it as its own grid width."""
        formlet = self._build('generalSettingsPane')
        popups = {node.attr['dbfield'].split('.')[-1]: node.attr
                  for node in struct_nodes(formlet.value)
                  if node.attr.get('tag') == 'CheckBoxText'}
        for field in ('tag_rule', 'group_code'):
            assert popups[field]['popup']
            assert popups[field]['cols'] == 4
