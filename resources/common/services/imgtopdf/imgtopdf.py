# -*- coding: utf-8 -*-

from gnr.lib.gnrheif import HEIF_EXTENSIONS, read_heif_image
from gnr.lib.services.imgtopdf import ImgToPdfService

class Service(ImgToPdfService):
    def writePdf(self,srcNode, destNode, **kwargs):
        from PIL import Image
        if srcNode.ext.lower() in HEIF_EXTENSIONS:
            with read_heif_image(srcNode) as image, destNode.open('wb') as outfile:
                image.save(outfile, "PDF", resolution=100.0)
            return destNode
        with srcNode.open('rb') as infile:
            with destNode.open('wb') as outfile:
                Image.open(infile).save(outfile, "PDF" ,resolution=100.0, save_all=True)
        return destNode
