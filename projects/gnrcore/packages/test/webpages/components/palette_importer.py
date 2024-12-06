# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    
    def test_0_rpc(self, pane):
        "Use paletteImporter to import csv, xlsx, xml files via rpc method (and _ask)"
        bc = pane.borderContainer(height='80px')
        fb = bc.contentPane(region='top').formbuilder()
        fb.paletteImporter(paletteCode='testimporter',
                            dockButton_iconClass='iconbox inbox',
                            title='!!Table from csv/xls',
                            importButton_label='Import test',
                            previewLimit=50,
                            dropMessage='Please drop here your file',
                            importButton_action="genro.publish('import_file',{filepath:imported_file_path,name:name})",
                            importButton_ask=dict(title='!!Custom parameter',fields=[dict(name='name',lbl='Name')]),
                            matchColumns='*')

        fb.dataRpc(self.importFileTest, subscribe_import_file=True,
            _onResult="genro.publish('testimporter_onResult',result);",
            _onError="genro.publish('testimporter_onResult',{error:error});")

    def test_1_importer(self, pane):
        "Use paletteImporter to import csv, xlsx, xml files via importer_ hook method"
        bc = pane.borderContainer(height='80px')
        fb = bc.contentPane(region='top').formbuilder()
        fb.paletteImporter(paletteCode='testimporter',
                            dockButton_iconClass=False,
                            title='!!Import cities',
                            importButton_label='Import cities',
                            previewLimit=50,
                            dropMessage='Please drop here your file',
                            filetype='excel', 
                            table='test.prov_test',
                            importerMethod='find_regions_from_name',
                            matchColumns='$sigla,$nome,$codice_istat')
        
    def test_2_dropUploader(self,pane):
        "Alternatively, it is possible to upload files with dropUploader"
        fb = pane.formbuilder()
        fb.dropUploader(label='Drop the file to import here', width='300px', onUploadedMethod=self.testUpl,
                        onResult="console.log('finished',evt)", progressBar=True)
    
    @public_method
    def testUpl(*args,**kwargs):
        print('File uploaded')

    def test_3_fileinput(self,pane):
        "Another option is to use fileInputBlind"
        fb = pane.formbuilder()
        fb.fileInputBlind(value='^.fileInputBlind', lbl='Import file')

    @public_method
    def importFileTest(self,filepath=None,name=None):
        if not name:
            return dict(error='Name required')
        else:
            return dict(message='Import ok',closeImporter=True)

