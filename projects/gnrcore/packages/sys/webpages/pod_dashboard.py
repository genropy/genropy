# -*- coding: utf-8 -*-

class GnrCustomWebPage(object):
    py_requires = 'public:Public,gnrcomponents/framegrid:FrameGrid,gnrcomponents/gnride/gnride'

    auth_main = '_DEV_'

    def main(self,root,**kwargs):
        frame = root.framePane(datapath='main')
        bc = frame.center.borderContainer()
        bc.gnrIdeFrame(region='center',nodeId='podIDE',datapath='main.podIDE',
                                sourceFolders='/home')
