# -*- coding: utf-8 -*-

"""Downloading what an RPC returns, without writing a file anywhere

The method returns the file CONTENT as a string and sets `self.download_name`;
the framework turns the pair into a `Content-Disposition: attachment` response,
so the browser saves a file the server never stored. The extension of
`download_name` is what decides the mime type the response declares. The two
cases download the same `hello.txt` and differ only in how the call is started:
the first builds the name in its action, `downloadButton` passes each `rpc_`
value as it is, so its field carries the extension itself.
"""

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_1_download_text(self, pane):
        """Start the download by hand: a button action calling genro.rpcDownload()"""
        fb = pane.formbuilder(cols=1, border_spacing='3px')
        fb.textbox(value='^.name', lbl='Name')
        fb.data('.name', "hello")
        fb.button('Download file', action='genro.rpcDownload(rpcmethod,{name:name+".txt"})',
                  rpcmethod=self.testDownloadFile,
                  name='=.name')

    def test_2_download_button(self, pane):
        """The same download through downloadButton, which wires that call itself"""
        fb = pane.formbuilder(cols=1, border_spacing='3px')
        fb.textbox(value='^.name', lbl='Name')
        fb.data('.name', "hello.txt")
        fb.downloadButton(label='Download file',
                          cursor='pointer',
                          text_decoration='underline',
                          rpc_method=self.testDownloadFile,
                          rpc_name='=.name')

    @public_method
    def testDownloadFile(self, name=None, **kwargs):
        self.download_name = name or 'pippo.txt'
        return 'Hello to everybody \n paraponzi'
