# -*- coding: utf-8 -*-
from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    def test_1_plain(self, pane):
        """TinyMCE plain: placeholders and removeToolbarItems"""
        pane.tinymce(value='^.text', placeholders='name,surname,email',
                     removeToolbarItems=['image', 'code'], height='200px')
        
    def test_2_image(self, pane):
        """Image upload: uploadPath and onUploadedMethod"""
        pane.tinymce(value='^.text', uploadPath='site:test_uploads',
                     onUploadedMethod=self.onImageUploaded)
        
    def test_3_imageData(self, pane):
        """Image upload: uploadPath and imageData"""
        pane.tinymce(value='^.text', imageData=True)
       
    @public_method 
    def onImageUploaded(self, pane, **kwargs):
        print(x)