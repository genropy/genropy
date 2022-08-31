# encoding: utf-8

from gnr.app.gnrdbo import AttachmentTable
from gnr.core.gnrdecorator import metadata
class Table(AttachmentTable):
    pass

    def atc_download(self):
        return True

    @metadata(doUpdate=True)
    def touch_updateAtcFilepath(self,record,old_record=None):
        "Update after S3 configuration"
        record['filepath'] = record['filepath'].replace('home:docu_documentation', 'documentation:attachments')