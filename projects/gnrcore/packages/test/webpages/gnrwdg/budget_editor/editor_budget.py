"""Quick Budget Editor — XML-backed Load/Save round-trip.

3 levels of nested groupletGrid (chapters → accounts → details) driven
by a Bag that is loaded from / saved to an on-disk XML file via two
@public_method RPCs. Demonstrates the realistic data-flow scenario: the
Bag is empty at page bootstrap and arrives later, after the user clicks
"Load".

XML file lives at:
    packages/test/resources/budget_editor/budget_sample.xml

generated once by /tmp/gen_budget_sample.py so the on-disk format
matches exactly what Bag.toXml(pretty=True) produces — no hand-XML
drift.
"""
import os

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):

    py_requires = ('gnrcomponents/grouplet/grouplet:GroupletHandler,'
                   'gnrcomponents/grouplet/grouplet:GroupletGridHandler')
    css_requires = 'budget_editor/editor_budget'

    def _xml_path(self):
        return os.path.join(self.package_folder, 'resources',
                            'budget_editor', 'budget_sample.xml')

    def main(self, root, **kwargs):
        # contentPane(datapath=...) workaround: gr_groupletGrid currently
        # needs an anchored ancestor to resolve relative storepaths.
        # Removed once Phase 13.5 lands.
        page = root.contentPane(datapath='budget')
        page.data('.chapters', Bag())

        bar = page.div(_class='budget_toolbar')
        # Load — ask for confirmation if there are unsaved edits.
        bar.lightButton(
            '!!Load',
            _class='budget_toolbar_btn',
            action=("var bag = GET .chapters;"
                    "if (bag && bag.len && bag.len() > 0) {"
                    "  if (!confirm('Discard current budget and reload "
                    "from disk?')) return;"
                    "}"
                    "FIRE .load_signal;"))
        bar.lightButton(
            '!!Save',
            _class='budget_toolbar_btn budget_toolbar_btn_success',
            action=("if (!confirm('Overwrite budget_sample.xml on disk "
                    "with the current budget?')) return;"
                    "FIRE .save_signal;"))
        bar.div('', _class='budget_toolbar_spacer')
        bar.div('^.status', _class='budget_toolbar_status')

        page.groupletGrid(
            storepath='.chapters',
            resource='budget/capitolo_card',
            _class='budget_capitoli_grid',
            dragCode='budget_capitoli',
            defaultRow=dict(codice='', descr=''))

        # Load: returns a Bag, dataRpc writes it to .chapters.
        page.dataRpc('.chapters', self.loadBudget,
                     _fired='^.load_signal')
        page.dataController(
            "SET .status = 'loaded ' + new Date().toLocaleTimeString();",
            _fired='^.chapters')
        # Save: send the current Bag to the server.
        page.dataRpc('.save_result', self.saveBudget,
                     payload='=.chapters',
                     _fired='^.save_signal')
        page.dataController(
            "if (result && result.getItem) {"
            "  SET .status = result.getItem('ok') ?"
            "    'saved ' + new Date().toLocaleTimeString() :"
            "    'save failed: ' + (result.getItem('error') || '?');"
            "}",
            result='=.save_result',
            _fired='^.save_result')

    @public_method
    def loadBudget(self, **kwargs):
        path = self._xml_path()
        return Bag(path) if os.path.exists(path) else Bag()

    @public_method
    def saveBudget(self, payload=None, **kwargs):
        if payload is None:
            return Bag(dict(ok=False, error='empty payload'))
        path = self._xml_path()
        payload.toXml(path, pretty=True)
        return Bag(dict(ok=True, path=path))
