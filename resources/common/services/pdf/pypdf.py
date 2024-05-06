#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-


from gnr.lib.services.pdf import PdfService
import os
from io import BytesIO

try:
    from PyPDF2 import PdfWriter, PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


class Service(PdfService):

    def joinPdf(self, pdf_list, output_filepath):
        """TODO
        :param pdf_list: TODO
        :param output_filepath: TODO"""
        
        if HAS_PYPDF:
            return self.joinPdf_PYPDF(pdf_list, output_filepath)
        
        if HAS_FITZ:
            return self.joinPdf_FITZ(pdf_list, output_filepath)
        raise self.parent.exception('Missing pyPdf in this installation')
    
    def joinPdf_PYPDF(self,pdf_list, output_filepath):
        output_pdf = PdfWriter()
        open_files = []
        out_sn = self.parent.storageNode(output_filepath)
        if len(pdf_list)==1:
            input_node = self.parent.storageNode(pdf_list[0])
            input_node.copy(out_sn)
            return
        for input_path in pdf_list:
            input_node = self.parent.storageNode(input_path)
            with input_node.open() as input_file:
                memory_file = BytesIO(input_file.read())
                open_files.append(memory_file)
            input_pdf = PdfReader(memory_file)
            for page in input_pdf.pages:
                output_pdf.add_page(page)
        with out_sn.open(mode='wb') as output_file:
            output_pdf.write(output_file)
        for open_file in open_files:
            open_file.close()


    def joinPdf_FITZ(self,pdf_list, output_filepath):
        out_sn = self.parent.storageNode(output_filepath)
        if len(pdf_list)==1:
            input_node = self.parent.storageNode(pdf_list[0])
            input_node.copy(out_sn)
            return
        doc = None
        for input_path in pdf_list:
            input_node = self.parent.storageNode(input_path)
            with input_node.open('rb') as input_file:
                op = fitz.open('pdf',input_file.read())
                if doc:
                    doc.insert(op)
                else:
                    doc= op
        with out_sn.open('rb') as f:
            doc.save(f.read())
        doc.save()


    def watermarkedPDF(self,input_pdf,watermark=None):
        with self.parent.storageNode(input_pdf).open('rb') as f:
            doc = fitz.open('pdf',f.read())
        for page in doc:  
            rect = page.rect  # Ottiene il rettangolo della pagina
            x0 = rect.x0
            x1 = rect.x1
            y0 = rect.y0
            y1 = rect.y1
            print('x0',x0,'y0',y0)
            print('x1',x1,'y1',y1)

            rc = fitz.Rect(x0+50, y1-50, x1-50, y1)  # Definisce il rettangolo per il testo
            shape = page.new_shape()  # Crea una nuova "forma" per disegnare
            shape.insert_text(rc.bottom_left,  # Posizione del testo
                            watermark,  # Testo del watermark
                            fontsize=11,  # Dimensione del font
                            color=(0, 0, 1),  # Colore del testo (blu)
                            rotate=0)  # Angolazione del testo
            shape.finish(width=1, color=(0, 0, 1), fill=(0, 0, 1, 0.3))  # Colora e imposta la trasparenza
            shape.commit()  # Applica la forma alla pagina
        output_pdf_bytes = BytesIO()
        doc.save(output_pdf_bytes)
        output_pdf_bytes.seek(0)  # Riposiziona il cursore all'inizio del buffer
        doc.close()  # Chiudi il documento
        result = output_pdf_bytes.read()
        return result