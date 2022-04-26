# -*- coding: utf-8 -*-

"""Bag from external formats"""

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    def test_0_json(self, pane):
        self._formatTesterLayout(pane,'json')


    def test_1_yaml(self, pane):
        self._formatTesterLayout(pane,'yaml')


    def _formatTesterLayout(self,pane,ext):
        bc = pane.borderContainer(height='500px',width='600px')
        bc.contentPane(region='top').dropUploader(nodeId=f"{ext}_uploader",
                            height = '100px', width='400px',
                            label= f'Drop {ext} file here or double click',
                            rpc_storepath='==this.absDatapath(".store")')
        bc.contentPane(region='center').tree(
            storepath='.store'
        )
            

    @public_method
    def onUploaded_yaml_uploader(self, file_url=None, file_path=None, file_ext=None, storepath=None,
                                  action_results=None, **kwargs):
        result = Bag()
        with self.site.storageNode(file_path).open('rb') as f:
            result.fromYaml(f.read())
        self.setInClientData(storepath,result)


    @public_method
    def onUploaded_json_uploader(self, file_url=None, file_path=None, file_ext=None, storepath=None,
                                  action_results=None, **kwargs):
        result = Bag()
        with self.site.storageNode(file_path).open('r') as f:
            result.fromJson(f.read())
        self.setInClientData(storepath,result)
