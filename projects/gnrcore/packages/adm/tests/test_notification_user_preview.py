"""The Users tab of the notification form previews the notification.

An ``adm.user_notification`` row is a delivery, not something an
administrator edits: what is worth opening on one is the notification as its
recipient will receive it. The grid is therefore wired to build the very
dialog the login shows -- the one in ``adm_notification.js`` -- in preview
mode, and the point of these tests is that it stays the *same* dialog:
a second implementation would be free to drift from what the user sees,
which is exactly what the tab is meant to show.

The struct is built through the resource of this working tree, on a real
site and against the real adm model, so the handler asserted here is the one
the browser is served.
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


class TestNotificationUserPreview(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        bootstrap_app = GnrApp(cls.test_instance_name)
        bootstrap_app.db.model.check(applyChanges=True)
        bootstrap_app.db.commit()
        bootstrap_app.db.closeConnection()
        cls.site = GnrDummySite(cls.test_instance_name,
                                site_name=cls.test_instance_name)
        cls.adm_resources = os.path.join(
            cls.site.db.application.packages['adm'].packageFolder, 'resources')
        cls.th_notification = gnrImport(
            os.path.join(cls.adm_resources, 'tables', 'notification',
                         'th_notification.py'), avoidDup=True)

    @classmethod
    def teardown_class(cls):
        if getattr(cls, 'site', None):
            cls.site.db.closeConnection()
        super().teardown_class()

    # --- fixtures ----------------------------------------------------------

    @classmethod
    def _users_tab(cls):
        """The Users tab of the form, built as a real table handler. The page
        is the one the site hands to headless callers, with the table handler
        component mixed in the way a webpage using the form has it, and set as
        the current page for the build alone -- the grid struct reads the saved
        views of the user asking for it, and the site is shared."""
        page = cls.site.dummyPage
        page.mixinComponent('th/th:TableHandler')
        component = cls.th_notification.Form()
        component.page = page
        root = GnrDomSrc_dojo_11.makeRoot(page)
        page._root = root
        pane = root.child('div', childname='tab', table='adm.notification')
        previous_page = cls.site.currentPage
        cls.site.currentPage = page
        try:
            component.connectedUser(pane)
        finally:
            cls.site.currentPage = previous_page
        return root

    @classmethod
    def _resource_source(cls, name):
        with open(os.path.join(cls.adm_resources, name), encoding='utf-8') as f:
            return f.read()

    # --- the wiring --------------------------------------------------------

    def test_a_row_opens_the_notification_dialog_in_preview_mode(self):
        handlers = [node.attr for node in struct_nodes(self._users_tab())
                    if node.attr.get('connect_onRowDblClick')]
        assert len(handlers) == 1, "only the recipients grid reacts to a double click"
        assert handlers[0]['table'] == 'adm.user_notification'
        action = handlers[0]['connect_onRowDblClick']
        assert 'notificationDialog.open' in action
        assert 'rowIdByIndex' in action, "the dialog is opened on the row clicked"
        assert 'true' in action.split('notificationDialog.open')[1], \
            "the preview flag is what keeps the buttons from acting"

    def test_the_rows_still_have_no_form_to_open(self):
        """The preview replaces nothing: there was no form on these rows, and
        adding one is not what the tab is for."""
        tags = [node.attr.get('tag') for node in struct_nodes(self._users_tab())]
        assert 'FormHandler' not in tags

    def test_the_dialog_resource_is_served_with_the_form(self):
        """The handler calls a global, so the resource holding it has to reach
        the browser with the form: mixing the form resource into a page is
        what puts it among the files the page is told to load, and a double
        click on a page without it would raise instead of previewing."""
        for resource in ('tables/notification/th_notification:Form',
                         'tables/notification/th_notification:FormEmbed'):
            page = self.site.dummyPage
            self.site.resource_loader.mixinPageComponent(page, resource, pkg='adm')
            assert page.envelope_js_requires.get('adm_notification'), resource

    # --- one dialog, not two -----------------------------------------------

    def test_the_login_builds_the_previewed_dialog(self):
        """frameindex.js is where this dialog used to be built inline. It has
        to stay delegated: the day it builds one of its own again, the tab
        would be previewing something the user never sees."""
        frameindex = self._resource_source('frameindex.js')
        assert 'notificationDialog.open' in frameindex
        assert 'quickDialog' not in frameindex
        assert 'quickDialog' in self._resource_source('adm_notification.js')
