import pytest

from gnr.web.gnrwebstruct import GnrDomSrc_dojo_11

from grouplet_panel_test import panel_page  # noqa: F401


class WizardPane:
    def groupletWizard(self, **kwargs):
        return kwargs


@pytest.mark.parametrize('keep_toolbar, kept', [(False, []), (True, ['bar'])])
def test_wizard_form_keeps_the_top_bar_only_when_asked(panel_page, keep_toolbar, kept):  # noqa: F811
    root = GnrDomSrc_dojo_11.makeRoot(panel_page)
    form = root.frameForm(frameCode='ticket', formId='ticket', table='test.myticket')
    form.top.slotBar('dismissTitle,*,prevUp,nextDown')
    panel_page.gr_groupletWizardForm(form, pane=WizardPane(), keepToolbar=keep_toolbar)
    assert list(form.getNode('top').value.keys()) == kept
