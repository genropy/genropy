# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    def test_01_rpc(self, pane):
        "Insert your test here"
        fb = pane.formbuilder(cols=1)
        fb.button('Test xhr',
                action="""
                genro.serverCall(myrpc,{par:'using xhr'},
                                function(result){
                                    alert(result)
                                });
                """,myrpc=self.myrcp)
    
    def test_02_fetch(self, pane):
        "Insert your test here"
        fb = pane.formbuilder(cols=1)
        fb.button('Test fetch',
                action="""
                fetch('/sandbox/test_fetch', {
                    method: 'POST', // or 'PUT'
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({method:myrpc,par:'using fetch',
                                        'page_id': genro.page_id,'zzz':2}),
                }).then(result=>console.log('aaa',result));
                """,myrpc=self.myrcp)

    @public_method
    def myrcp(self,par=None,**kwargs):
        result = f'par {par}'
        print(result)
        return result