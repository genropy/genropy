# -*- coding: utf-8 -*-

# iframerunner.py
# Created by Francesco Porcari on 2011-04-19.
# Copyright (c) 2011 Softwell. All rights reserved.

"iframerunner"

class GnrCustomWebPage(object):
    py_requires="""gnrcomponents/testhandler:TestHandlerFull,
                    test_proxy:Leonard AS leo
                """
    

    def test_0_simple(self,pane):
        self.leo.makeBox(pane)
        self.leo.fakeLaugh()

