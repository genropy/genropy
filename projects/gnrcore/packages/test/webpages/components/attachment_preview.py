# -*- coding: utf-8 -*-

"""attachmentPreviewViewer: which pane an attachment extension opens

The preview stack has four pages — image, video, unsupported and document —
and the extension of the source url decides which one is shown. The point of
this page is to make that routing visible without a stored attachment: the url
is typed or picked here and handed straight to the viewer.
"""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                        gnrcomponents/attachmanager/attachmanager:AttachManager"""

    sample_extensions = ('png:png (image)', 'jpg:jpg (image)', 'webp:webp (image)',
                         'mp4:mp4 (video)', 'webm:webm (video)', 'mov:mov (video)',
                         'm4v:m4v (video)', 'avi:avi (unsupported)', 'mpg:mpg (unsupported)',
                         'mpeg:mpeg (unsupported)', 'wmv:wmv (unsupported)',
                         'mkv:mkv (unsupported)', 'flv:flv (unsupported)',
                         'pdf:pdf (document)', 'txt:txt (document)')

    def test_0_previewRouting(self, pane):
        """Pick an extension and read back the pane the stack switched to

        The url does not need to exist: the routing runs on the extension
        alone, so this is the fastest way to check that no container the
        browser cannot decode reaches the player.
        """
        bc = pane.borderContainer(height='500px')
        fb = bc.contentPane(region='top').formbuilder(cols=2, border_spacing='4px')
        fb.filteringSelect(value='^.ext', lbl='Extension', default_value='avi',
                           values=','.join(self.sample_extensions))
        fb.textbox(value='^.pane', lbl='Selected pane', readOnly=True)
        fb.textbox(value='^.fileurl', lbl='Source url', readOnly=True, width='100%', colspan=2)
        bc.dataFormula('.fileurl', '"/sample_attachment."+ext', ext='^.ext')
        bc.attachmentPreviewViewer(src='^.fileurl', selectedPage='^.pane',
                                   region='center', margin='5px',
                                   border='1px solid silver', rounded=6)

    def test_1_previewRealFile(self, pane):
        """Paste the url of a real file and check the pane actually renders it

        Needed on top of test_0 because the routing being right is only half
        the fix: a container that reaches the player must play, and one that
        reaches the unsupported pane must offer the download instead.
        """
        bc = pane.borderContainer(height='500px')
        fb = bc.contentPane(region='top').formbuilder(cols=2, border_spacing='4px')
        fb.textbox(value='^.fileurl', lbl='Source url', width='100%')
        fb.textbox(value='^.pane', lbl='Selected pane', readOnly=True)
        bc.attachmentPreviewViewer(src='^.fileurl', selectedPage='^.pane',
                                   region='center', margin='5px',
                                   border='1px solid silver', rounded=6)
