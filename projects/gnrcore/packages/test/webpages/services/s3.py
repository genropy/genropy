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
        fb.dbSelect(value='^.s3_service',lbl='S3 Service', table='sys.service', 
                            condition='$service_type=:st AND $implementation=:im',
                            condition_st='storage',
                            condition_im='aws_s3',
                            hasDownArrow=True,
                            alternatePkey='service_name')
        fb.dataRpc('.s3_folders', self.connectS3Bucket, s3_service='^.s3_service')
        fb.div('^.s3_folders')

    @public_method
    def connectS3Bucket(self, s3_service=None):
        s3 = self.site.getService(service_name=s3_service, service_type='storage')
        s3_folders = s3.listdir()
        return s3_folders
