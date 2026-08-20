# -*- coding: utf-8 -*-

"""Raw browser WebSocket talking to an echo server, without the GenroPy channel

This page opens its own `WebSocket` object from client javascript instead of
using the framework channel, sends a Bag serialized to XML with an `echo`
command and displays whatever comes back. It documents the wire format the
async server expects; the connection is the hand-made one, so nothing here
goes through `httpMethod='WSK'`.

# todo the socket URL is hardcoded to ws://localhost:8888, the port of the
# standalone async server: the page only talks to a server listening there.
"""


class GnrCustomWebPage(object):
    def main(self,root,**kwargs):
        root.script("""genro.ws=new WebSocket('ws://localhost:8888/');
                        genro.ws.onopen = function () {
	                                genro.ws.send('connected');
	                                };
	
                        genro.ws.onerror = function (error) {
	                                console.log('WebSocket Error ' + error);
	                                };        
	
                        genro.ws.onmessage = function (e) {
	                        genro.setData('received', e.data);
	                    };""")
        root.div('test echo')
        fb=root.formbuilder(cols=1)
        fb.textbox(value='^dataToSend',lbl='Data To Send')
        fb.div(value='^received',lbl='Received Data')
        
        fb.dataController("""console.log('sending',data);
                       message=new gnr.GnrBag()
                       message.setItem('page_id',genro.page_id)
                       message.setItem('command','echo')
                       message.setItem('data',data)
                       genro.ws.send(message.toXml())""",data='^dataToSend')
