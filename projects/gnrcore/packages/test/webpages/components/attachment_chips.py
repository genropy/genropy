# -*- coding: utf-8 -*-

"""attachmentChips: the attachments of a record as a light line of chips

Each chip opens its file on click and removes it with the small x; the
dashed chip at the end, or a drop anywhere on the area, uploads new files.
The record is an adm.htmltemplate, whose attachments live in
adm.htmltemplate_atc: pick one in the select above each test.
"""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                        gnrcomponents/attachmanager/attachmanager:AttachManager"""

    def _templateForm(self, pane, frameCode):
        bc = pane.borderContainer(height='260px')
        top = bc.contentPane(region='top')
        top.formbuilder(cols=1, border_spacing='4px').dbSelect(value='^.template_id',
                                                               dbtable='adm.htmltemplate',
                                                               lbl='Template', hasDownArrow=True)
        form = bc.frameForm(frameCode=frameCode, datapath='.form', region='center',
                            table='adm.htmltemplate')
        form.top.slotToolbar('*,semaphore,locker,2')
        form.formStore(table='adm.htmltemplate', storeType='Item',
                       handler='recordCluster', startKey='*norecord*')
        bc.dataController("frm.load({destPkey:pkey || '*norecord*'});",
                          pkey='^.template_id', frm=form.js_form)
        return form

    def test_0_chipsInForm(self, pane):
        """Attachments of the loaded record: click a chip to open the viewer, x to delete it,
        the dashed chip or a drop on the area to upload. In the viewer, the tag icon next to
        the name renames it: it is saved when you move to another attachment or close the
        viewer. Lock the form: the x and the upload chip disappear."""
        form = self._templateForm(pane, 'atcChipsForm')
        form.center.contentPane().attachmentChips()

    def test_1_explicitTable(self, pane):
        """Outside a record form: table and maintable_id given explicitly, download=True
        adds the download button to the viewer, with a custom upload label and empty message.
        maintable_id is resolved inside the component datapath, like the other attachment
        components"""
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.dbSelect(value='^.attachments.template_id', dbtable='adm.htmltemplate',
                    lbl='Template', hasDownArrow=True)
        pane.attachmentChips(table='adm.htmltemplate_atc', maintable_id='^.template_id',
                             parentForm=False, download=True, addLabel='Add file',
                             emptyMessage='Nothing attached yet')
