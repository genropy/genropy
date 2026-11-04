# -*- coding: utf-8 -*-

"""htmlToCanvas: a screenshot of a page node, uploaded to a storage path

`genro.dom.htmlToCanvas` renders a DOM node into a canvas. Given an
`uploadPath` - a storage path such as `site:testcanvas` - it asks for a file
name with a preview of the image, uploads it as a PNG into that folder and
calls `onResult` with the upload's response, whose text is the url of the
stored file, or with a failed upload whose status is shown instead. Cancel
calls `onResult` too, with no response to read.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_1_basic(self, pane):
        """Capture the coloured panes below, name the file and upload it: its url appears in the top bar"""
        bc = pane.borderContainer(height='500px')
        top = bc.contentPane(region='top', height='50px', background='lime')
        top.button('Capture', action="""
            var sourceNode = this;
            genro.dom.htmlToCanvas(d, {uploadPath: p, onResult: function(evt){
                if(!(evt && evt.currentTarget)){
                    return;
                }
                var xhr = evt.currentTarget;
                sourceNode.setRelativeData('.uploaded_url',
                                           xhr.status == 200 ? xhr.responseText : 'Upload failed: ' + xhr.status);
            }});
            """, d=bc.js_domNode, p='site:testcanvas')
        top.div('^.uploaded_url', display='inline-block', margin_left='1em')
        bc.contentPane(region='left', width='50px', background='red')
        bc.contentPane(region='center', background='pink')
