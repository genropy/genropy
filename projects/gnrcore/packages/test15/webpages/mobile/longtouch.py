# -*- coding: utf-8 -*-

# bugsxml.py
# Created by Francesco Porcari on 2012-03-01.
# Copyright (c) 2012 Softwell. All rights reserved.

"Test page description"

from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"


    def test_1_longtouch(self,pane):
        pane.data('.color','red')
        pane.div(height='100px',width='100px',margin='30px',background='^.color',id='red',display='inline-block',
                connect_touchstart="""
                                    SET .color="blue";
                                    console.log('connect_touchstart',$1)
                                    """,
                connect_touchend="""SET .color="red";
                                    console.log('connect_touchend',$1)

                                    """)
        pane.div(height='100px',width='100px',margin='30px',background='green',id='green',display='inline-block')
