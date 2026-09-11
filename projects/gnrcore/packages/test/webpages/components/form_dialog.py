# -*- coding: utf-8 -*-

"""formDialog: a modal dialog that behaves like a form

The formDialog component builds a dialog with its own formId, so the content
inside it can use the standard form machinery — load, save, validation — while
living in a modal. The typical use is asking for a value that has to be
validated on the server before the caller may continue.
"""


class GnrCustomWebPage(object):
    py_requires = 'gnrcomponents/testhandler:TestHandlerFull,foundation/dialogs'

    def test_0_formDialog(self, pane):
        """Authorization code dialog: modal form with remote validation

        The button fires the dialog open. The textbox inside validates its
        content against rpc_validateAuthCode: the only accepted code is
        'pippo', anything else is refused without closing the dialog.
        """
        self.askAuthcodeDlg(pane)
        pane.button('test_0', action='FIRE #askAuthcode_dlg.open;')

    def askAuthcodeDlg(self, bc, onConfirmed='', request_txt=''):
        """Build the dialog: a single validated field plus its saver/loader controllers"""
        def cb_center(parentBC, **kwargs):
            dlg_body = parentBC.contentPane(margin='8px', **kwargs)
            dlg_body.div(request_txt)
            fb = dlg_body.formbuilder(cols=1)
            fb.textbox(lbl='Insert your authorization code',
                       value='^.authcode', width='8em',
                       validate_notnull=True,
                       validate_notnull_error='Insert code',
                       validate_remote='validateAuthCode',
                       validate_remote_error='Wrong or already used auth code.'
                       )

        dlg = self.formDialog(bc,
                              formId='askAuthcode',
                              title='Authorization required',
                              height='150px', width='350px',
                              datapath='aux.auth_dlg',
                              cb_center=cb_center, loadsync=True)
        dlg.dataController("""SET form.record.$authcode = GET .data.authcode;
                              FIRE .saved;
                              %s""" % onConfirmed,
                           nodeId='askAuthcode_saver')

        dlg.dataController("""SET .data.authcode = null;""",
                           nodeId='askAuthcode_loader')

    def rpc_validateAuthCode(self, value=None, **kwargs):
        """Server side of validate_remote: accept a single hardcoded code"""
        return value == 'pippo'
