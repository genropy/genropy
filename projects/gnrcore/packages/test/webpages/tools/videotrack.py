# -*- coding: utf-8 -*-

# tpleditor.py
# Created by Francesco Porcari on 2011-06-22.
# Copyright (c) 2011 Softwell. All rights reserved.

"Test page description"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"
    
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

    def test_2_clear_video_source(self, pane):
        "Clearing a bound source resets the video element"
        sample_url = 'https://community.genropy.net/_storage/social/video/YGvmpOe7Nfea_L08ojbcoQ.mp4'
        box = pane.div(datapath='.clear_video_source')
        box.data('.sample_url', sample_url)
        bar = box.div(margin_bottom='10px')
        bar.button('Load video', action='SET .video_url = sample_url;',
                   sample_url='=.sample_url')
        bar.button('Clear source', action='SET .video_url = null;', margin_left='5px')
        bar.button('Inspect', fire='.inspect', margin_left='5px')
        video = box.video(src='^.video_url', height='360px', width='640px',
                          controls=True, autoplay=True, muted=True, preload='auto')
        box.dataController(r"""
            const hasSrc = videoNode.hasAttribute('src');
            const currentSrc = videoNode.currentSrc || '';
            const readyState = videoNode.readyState;
            const nullRequests = performance.getEntriesByType('resource').filter(function(entry){
                return /\/null(?:$|[?#])/.test(entry.name);
            }).length;
            SET .has_src = hasSrc;
            SET .src_attribute = videoNode.getAttribute('src') || '';
            SET .current_src = currentSrc;
            SET .ready_state = readyState;
            SET .paused = videoNode.paused;
            SET .null_requests = nullRequests;
            SET .verdict = !hasSrc && readyState === 0 && videoNode.paused && nullRequests === 0 ? 'PASS' : 'FAIL';
        """, videoNode=video.js_domNode, source='^.video_url', inspect='^.inspect', _delay=500)
        result = box.formbuilder(cols=1, margin_top='10px')
        result.div('^.verdict', lbl='Verdict', font_weight='bold')
        result.div('^.has_src', lbl='Has src attribute')
        result.div('^.src_attribute', lbl='Src attribute')
        result.div('^.current_src', lbl='Current source')
        result.div('^.ready_state', lbl='Ready state')
        result.div('^.paused', lbl='Paused')
        result.div('^.null_requests', lbl='Null requests')
