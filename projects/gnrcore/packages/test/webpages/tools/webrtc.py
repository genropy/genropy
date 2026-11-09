# -*- coding: utf-8 -*-

"""WebRTC: camera capture into a video, a canvas and an image

A `video` node's `startCapture` streams the camera into it; a `canvas` node's
`takePhoto` copies the current frame of a video, once or in sync, and
`savePhoto` downloads the canvas or uploads it to a storage path. An `img`
with `edit=True` grabs a photo through the video picker palette, or straight
from the camera with `camera=True`. Every case needs a camera and the
browser's permission to use it.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_video(self, pane):
        """Press Start and allow the camera: the video shows its stream"""
        video = pane.div(height='310px').video(autoplay=True, height='300px', width='400px')
        fb = pane.formbuilder(cols=3, border_spacing='3px')
        fb.checkbox(value='^.video', label='Video', default_value=True)
        fb.checkbox(value='^.audio', label='Audio')
        fb.button('Start', action='video.startCapture({video:videoCapture,audio:audioCapture})',
                  video=video, videoCapture='=.video', audioCapture='=.audio')

    def test_1_video_canvas(self, pane):
        """Start the video, then Snapshot copies its current frame into the canvas; Save downloads it"""
        video = pane.div(height='310px', display='inline-block').video(autoplay=True, height='300px',
                                                                       width='400px')
        canvas = pane.div(height='310px', display='inline-block',
                          margin_left='10px').canvas(height='300px', width='400px',
                                                     border='1px solid silver')
        pane.br()
        fb = pane.formbuilder(cols=5, border_spacing='3px')
        fb.checkbox(value='^.video', label='Video', default_value=True)
        fb.checkbox(value='^.audio', label='Audio')
        fb.button('Start', action='video.startCapture({video:videoCapture,audio:audioCapture})',
                  video=video, videoCapture='=.video', audioCapture='=.audio')
        fb.button('Snapshot', action='canvas.takePhoto(video)', video=video, canvas=canvas)
        fb.button('Save', action='canvas.savePhoto()', canvas=canvas)

    def test_2_video_copytocanvas(self, pane):
        """Start the video, then Copy mirrors it into the canvas frame by frame, with an optional effect

        Save downloads the canvas; Save server uploads it as `supertest` into
        `site:test/myimage`.
        """
        video = pane.div(height='310px', display='inline-block').video(autoplay=True, height='300px',
                                                                       width='400px')
        canvas = pane.div(height='310px', display='inline-block',
                          margin_left='10px').canvas(height='300px', width='400px',
                                                     border='1px solid silver', effect='^.effect')
        pane.br()
        fb = pane.formbuilder(cols=6, border_spacing='3px')
        fb.checkbox(value='^.mirror', label='Mirror')
        fb.dataController('SET .effects = canvas.pixasticEffects.join(",")', _onStart=True,
                          canvas=canvas)
        fb.filteringSelect(value='^.effect', values='^.effects')
        fb.button('Start', action='video.startCapture({video:videoCapture,audio:audioCapture})',
                  video=video, videoCapture=True, audioCapture=False)
        fb.button('Copy', action='canvas.takePhoto(video,{"sync":sync,"mirror":mirror})',
                  video=video, canvas=canvas, sync=True, mirror='=.mirror')
        fb.button('Save', action='canvas.savePhoto()', canvas=canvas)
        fb.button('Save server', action='canvas.savePhoto({uploadPath:path,filename:"supertest"})',
                  canvas=canvas, path='site:test/myimage')

    def test_3_video_capture_palette(self, pane):
        """Open the picker in the toolbar to grab a photo from the camera into the image"""
        frame = pane.framePane(height='340px', width='420px', border='1px solid silver')
        top = frame.top.slotToolbar('*,pickerImage,5', height='20px')
        top.pickerImage.videoPickerPalette()
        center = frame.center.contentPane(overflow='hidden')
        center.img(src='^.currUrl', crop_width='400px', crop_height='300px',
                   placeholder=self.getResourceUri('images/missing_photo.png'),
                   upload_folder='site:test/photo', edit=True,
                   upload_filename='foto_test_grabber', crop_border='1px solid #ddd',
                   crop_rounded=8, crop_margin='9px', zoomWindow=True)

    def test_4_video_capture_nopalette(self, pane):
        """Edit the image to take a photo straight from the camera, with no palette"""
        pane.img(src='^.currUrl', width='400px', height='300px', border='2px solid gray',
                 placeholder=self.getResourceUri('images/missing_photo.png'),
                 upload_folder='*', edit=True, camera=True)
