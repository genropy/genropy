# -*- coding: utf-8 -*-

from gnr.lib.services.imgtopdf import ImgToPdfService

class Service(ImgToPdfService):
    def writePdf(self,srcNode, destNode, **kwargs):
        from PIL import Image
        with srcNode.open('rb') as infile:
            with destNode.open('wb') as outfile:
                Image.open(infile).save(outfile, "PDF" ,resolution=100.0, save_all=True)
        return destNode