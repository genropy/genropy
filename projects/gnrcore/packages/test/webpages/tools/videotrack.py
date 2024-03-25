# -*- coding: utf-8 -*-

# tpleditor.py
# Created by Francesco Porcari on 2011-06-22.
# Copyright (c) 2011 Softwell. All rights reserved.

"Test page description"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerBase"
    
    def test_0_videotrack_dynamic(self,pane):
        "Widget video shows a video from its url. You can indicate video path dinamically"
        pane.formbuilder(width='100%', colswidth='100%').textbox('^.video_url', lbl='Video url', width='100%')
        pane.data('.video_url', 'https://community.genropy.net/_storage/social/video/YGvmpOe7Nfea_L08ojbcoQ.mp4')
        pane.video(src='^.video_url',
                    height='100%',width='100%',
                    border=0,controls=True,nodeId='preview_video')
                    #tracks=[dict(src='/_site/screencasts/pippo.vtt?zzz',
                    #            kind='subtitles',srclang='it')])
                    #In this case I have no subtitles available

    def test_1_videotrack_semistatic(self,pane):
        "Widget VideoPlayer is an alternative way. It supports timerange and resizing"
        bc = pane.borderContainer(height='500px')
        top = bc.contentPane(region='top',height='50px',background='red',splitter=True)
        fb = top.formbuilder(cols=1,border_spacing='3px')
        fb.data('.myvideo.range','12,30')
        fb.data('.myvideo.playerTime',0)

        fb.textbox('^.myvideo.range',lbl='Range')

        bc.contentPane(region='left',width='50px',splitter=True,background='lime')
        bc.contentPane(region='right',width='50px',splitter=True,background='navy')
        bc.contentPane(region='bottom',height='50px',splitter=True,background='silver')

        pane = bc.VideoPlayer(url='https://community.genropy.net/_storage/social/video/YGvmpOe7Nfea_L08ojbcoQ.mp4',
                    datapath='.myvideo',
                    region='center',
                    manageCue=True,
                    timerange='^.range',
                    selfsubscribe_addCue='console.log("fffff",$1);',
                    border=0,nodeId='preview_videoplayer',
                    subtitlePane=True)
                   #tracks=[dict(src='/video/index/vtt/KMq3Rzs6MMW3so_vWdYFXg/subtitles/it.vtt',
                   #           kind='subtitles',srclang='it',label='Subtitle',
                   #           cue_path='.mainsub',hidden=True)
                   #])
                   #In this case I have no subtitles available
        