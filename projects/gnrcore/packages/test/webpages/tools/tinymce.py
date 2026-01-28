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

    def test_4_maxLength(self, pane):
        """TinyMCE with maxLength: character limit and counter"""
        pane.tinymce(value='^.mycontent', maxLength=1024, height='400px',
                     removeToolbarItems=['image', 'code'])

    def test_5_insertToolbarItems_simple(self, pane):
        """TinyMCE with insertToolbarItems: add codesample button"""
        pane.data('.mycontent', 'This is a test with codesample plugin.')
        pane.tinymce(value='^.mycontent',
                     insertToolbarItems=['codesample'],
                     height='400px')

    def test_6_insertToolbarItems_custom(self, pane):
        """TinyMCE with insertToolbarItems: custom button with insertText"""
        pane.data('.mycontent', 'Test custom button insertion.')
        pane.tinymce(value='^.mycontent',
                     insertToolbarItems=[
                         {'name': 'myCustomBtn', 'text': 'Insert Hello',
                          'tooltip': 'Insert Hello World', 'insertText': '<p>Hello World!</p>'}
                     ],
                     height='400px')

    def test_7_insertToolbarItems_mixed(self, pane):
        """TinyMCE with insertToolbarItems: mix of plugin and custom button"""
        pane.data('.mycontent', 'Test mixed toolbar items.')
        pane.tinymce(value='^.mycontent',
                     insertToolbarItems=[
                         'codesample',
                         {'name': 'insertSignature', 'text': 'Signature',
                          'tooltip': 'Insert signature', 'insertText': '<p><em>Best regards</em></p>'}
                     ],
                     removeToolbarItems=['image'],
                     height='400px')