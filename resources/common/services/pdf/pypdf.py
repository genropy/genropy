#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-


from gnr.lib.services.pdf import PdfService
import os
from io import BytesIO
from gnr.core.gnrdecorator import extract_kwargs

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

    @extract_kwargs(watermark=True)
    def watermarkedPDF(self,input_pdf,watermark=None,mode='TextBox',watermark_kwargs=None):
        with self.parent.storageNode(input_pdf).open('rb') as f:
            doc = fitz.open('pdf',f.read())
        m = fitz.Matrix
        color = watermark_kwargs.pop('color',None)
        align = watermark_kwargs.pop('align','left')
        pars = dict(fontsize=24, fontname='helv', 
                    align = getattr(fitz,f'TEXT_ALIGN_{align.upper()}'),
                    color=fitz.utils.getColor(color) if color else (0, 0, 0),
                    fill_opacity=.1)
        pars.update(watermark_kwargs)
        
        for page in doc:  
            page.clean_contents()
            getattr(self,f'_insert{mode}')(page,watermark,**pars)

        output_pdf_bytes = BytesIO()
        doc.save(output_pdf_bytes)
        output_pdf_bytes.seek(0)  
        doc.close() 
        result = output_pdf_bytes.read()
        return result
    
    def _finishWatermark(self,shape,**kwargs):
        """
        width=1, color=(0,), 
        fill=None, lineCap=0, 
        lineJoin=0, dashes=None, 
        closePath=True, even_odd=False, 
        morph=(fixpoint, matrix),
          stroke_opacity=1, fill_opacity=1, oc=0
        """
        shape.finish(

        )
    
    def _insertText(self,page,watermark,**kwargs):
        """point, text, fontsize=11, fontname='helv', 
        fontfile=None, set_simple=False, 
        encoding=TEXT_ENCODING_LATIN, color=None,
          lineheight=None, fill=None, render_mode=0,
            border_width=1, rotate=0, morph=None, 
            stroke_opacity=1, fill_opacity=1, oc=0"""
        rect = page.rect  
        x_center = rect.width / 2
        y_center = rect.height / 2
        shape = page.new_shape()
        shape.insert_text((x_center,y_center), watermark,**kwargs)

        shape.commit()  

    

    def _insertTextBox(self,page,watermark,**kwargs):
        """
        rect, buffer, fontsize=11, fontname='helv', 
        fontfile=None, set_simple=False,
          encoding=TEXT_ENCODING_LATIN, color=None, 
          fill=None, render_mode=0, border_width=1, 
          expandtabs=8, align=TEXT_ALIGN_LEFT, rotate=0, 
          lineheight=None, morph=None, stroke_opacity=1, fill_opacity=1, oc=0
        """
        rect = page.rect  
        x_center = rect.width / 2
        y_center = rect.height / 2
        text_rect = fitz.Rect(x_center - 200, y_center - 100, x_center + 200, y_center + 100)
        shape = page.new_shape()
        rotate_matrix = fitz.Matrix(45)
        shape.insert_textbox(text_rect, watermark,morph=(fitz.Point(x_center,y_center),rotate_matrix),**kwargs)
        #rect = fitz.Rect(0, 0, len(watermark)*5, 50).transform(rotate_matrix)
        #rect = rect + (x_center, y_center)
        #shape.finish(morph=rotate_matrix)
        shape.commit()  
