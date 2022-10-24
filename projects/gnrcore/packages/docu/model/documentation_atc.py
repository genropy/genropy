# encoding: utf-8

from gnr.app.gnrdbo import AttachmentTable
from gnr.core.gnrdecorator import metadata
class Table(AttachmentTable):
    pass

    def atc_download(self):
        return True