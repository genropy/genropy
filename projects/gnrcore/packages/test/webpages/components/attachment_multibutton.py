# -*- coding: utf-8 -*-

"""attachmentMultiButtonFrame: one button per attachment over a viewer

The attachments are the items of a minimal multibutton; the bar next to them
holds the description editor, the copy url button and the external url editor.
Images get the same zoom bar as the attachmentChips viewer. The record is an adm.htmltemplate, whose attachments
live in adm.htmltemplate_atc: pick one in the select above each test.
"""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler,
                        gnrcomponents/attachmanager/attachmanager:AttachManager"""

    def _templateForm(self, pane, frameCode):
        bc = pane.borderContainer(height='500px')
        top = bc.contentPane(region='top')
        top.formlet(cols=1).dbSelect(value='^.template_id', dbtable='adm.htmltemplate',
                                     lbl='Template', hasDownArrow=True)
        form = bc.frameForm(frameCode=frameCode, datapath='.form', region='center',
                            table='adm.htmltemplate')
        form.top.slotToolbar('*,semaphore,locker,2')
        form.formStore(table='adm.htmltemplate', storeType='Item',
                       handler='recordCluster', startKey='*norecord*')
        bc.dataController("frm.load({destPkey:pkey || '*norecord*'});",
                          pkey='^.template_id', frm=form.js_form)
        return form

    def test_0_multiButtonInForm(self, pane):
        """Attachments of the loaded record: pick a button to view it, the pencil to rename it,
        the link icon to copy its url, the globe (no file uploaded) to set an external url,
        − Fit + over an image to zoom it."""
        form = self._templateForm(pane, 'atcMultiButtonForm')
        form.center.contentPane().attachmentMultiButtonFrame()

    def test_1_toolbarBottom(self, pane):
        """toolbarPosition='bottom': the same bar under the viewer"""
        form = self._templateForm(pane, 'atcMultiButtonBottom')
        form.center.contentPane().attachmentMultiButtonFrame(toolbarPosition='bottom')
