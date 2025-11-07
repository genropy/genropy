# -*- coding: utf-8 -*-

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    def test_1_plain(self, pane):
        """TinyMCE plain: placeholders and removeToolbarItems"""
        pane.tinymce(value='^.mycontent', placeholders='name,surname,email',
                     removeToolbarItems=['image', 'code'], 
                     placeholder='Type here...',)
        
    def test_2_image(self, pane):
        """Image upload: uploadPath to specify image upload path"""
        pane.data('.mycontent', 'This is a test content with an image upload feature.')
        pane.tinymce(value='^.mycontent', uploadPath='site:test_uploads', height='400px')
        
    def test_3_imageData(self, pane):
        """Image upload: imageData to manage image as base64"""
        pane.tinymce(value='^.mycontent', imageData=True, height='400px')