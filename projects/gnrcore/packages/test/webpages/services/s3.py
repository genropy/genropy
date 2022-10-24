# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                        gnrcomponents/storagetree:StorageTree"""

    def test_0_s3(self, pane):
        """Configure AWS CLI, create AWS S3 bucket and create a service before testing.
        See documentation: https://www.genropy.org/docs/service/service_genropy/storage/aws_s3.html"""
        bc = pane.borderContainer(height='100px')
        fb = bc.contentPane(region='top').formbuilder(cols=1,border_spacing='3px')
        fb.dbSelect(value='^s3_service',lbl='S3 Service', table='sys.service', 
                            condition='$service_type=:st AND $implementation=:im',
                            condition_st='storage',
                            condition_im='aws_s3',
                            hasDownArrow=True,
                            alternatePkey='service_name')
        fb.dataRpc('.s3_folders', self.connectS3Bucket, s3_service='^s3_service')
        fb.div('^.s3_folders')

    @public_method
    def connectS3Bucket(self, s3_service=None):
        s3 = self.site.getService(service_name=s3_service, service_type='storage')
        s3_folders = s3.listdir()
        return s3_folders

    def test_1_writeS3(self, pane):
        """Write new file on S3 bucket"""
        bc = pane.borderContainer(height='120px')
        fb = bc.contentPane(region='top').formbuilder(cols=1,border_spacing='3px')
        fb.dbSelect(value='^s3_service',lbl='S3 Service', table='sys.service', 
                            condition='$service_type=:st AND $implementation=:im',
                            condition_st='storage',
                            condition_im='aws_s3',
                            hasDownArrow=True,
                            alternatePkey='service_name')
        fb.simpleTextArea('^.text', lbl='Text to write')
        fb.button('Create file').dataRpc('.download_file', self.writeFile, s3='=s3_service', text='=.text')
        fb.a('Download file', href='^.download_file', target='_blank', hidden='^.download_file?=!#v')

    @public_method
    def writeFile(self, s3=None, text=None):
        s3 = self.site.getService(service_name=s3, service_type='storage')
        filepath = '{s3name}:temp'.format(s3name=s3.service_name)
        storageNode = self.site.storageNode(filepath, 'test.py')
        with storageNode.open('w') as testFile:
            testFile.write(text)
        file_url = self.site.externalUrl(storageNode.fullpath)
        return file_url

    def test_2_openWriteS3(self, pane):
        """Open same file as before and write new string on S3 bucket"""
        bc = pane.borderContainer(height='120px')
        fb = bc.contentPane(region='top').formbuilder(cols=1,border_spacing='3px')
        fb.dbSelect(value='^s3_service',lbl='S3 Service', table='sys.service', 
                            condition='$service_type=:st AND $implementation=:im',
                            condition_st='storage',
                            condition_im='aws_s3',
                            hasDownArrow=True,
                            alternatePkey='service_name')
        fb.simpleTextArea('^.text', lbl='Text to write')
        fb.button('Update file').dataRpc('.download_file', self.updateFile, s3='=s3_service', text='=.text')
        fb.a('Download file', href='^.download_file', target='_blank', hidden='^.download_file?=!#v')

    @public_method
    def updateFile(self, s3=None, text=None):
        s3 = self.site.getService(service_name=s3, service_type='storage')
        filepath = '{s3name}:temp'.format(s3name=s3.service_name)
        storageNode = self.site.storageNode(filepath, 'test.py')
        with storageNode.open('r') as testFileToUpdate:
            existing_text = testFileToUpdate.read()
        new_text = "\n".join([existing_text, text])
        with storageNode.open('w') as testFile:
            testFile.write(new_text)
        file_url = self.site.externalUrl(storageNode.fullpath)
        return file_url
