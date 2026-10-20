# -*- coding: utf-8 -*-

"""Polling ownership: only the root page polls, an iframe delegates to it

Tick "Server down" to send every request of this page and of its iframe to a closed
port: the browser reports status 0, the same transport failure a stopped server gives.
Press "Server call" in the iframe twice, five seconds apart, then untick: the lock and
the "Connection restored" alert must come once, from the root page, and the iframe
ping counter must stay still afterwards.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_iframe(self, pane):
        """Simulate an outage seen by the iframe, then count the pings of each window"""
        fb = pane.formbuilder(cols=3)
        fb.checkbox(value='^.server_down', label='Server down')
        fb.div('^.root_pings', lbl='Root pings')
        fb.div('^.iframe_pings', lbl='Iframe pings')
        pane.dataController("window._simulateServerDown = server_down;", server_down='^.server_down')
        pane.dataController("""
            var sn = this;
            var patch = function(w){
                var proto = w.XMLHttpRequest.prototype;
                if(proto._pollingTest){
                    return;
                }
                proto._pollingTest = true;
                w._pingCount = 0;
                var open = proto.open;
                proto.open = function(method, url){
                    var args = Array.prototype.slice.call(arguments);
                    if(String(url).indexOf('/_ping') >= 0){
                        w._pingCount++;
                    }
                    if(window._simulateServerDown){
                        args[1] = 'http://127.0.0.1:65530/';
                    }
                    return open.apply(this, args);
                };
            };
            patch(window);
            setInterval(function(){
                var child = genro.domById('pollingChild').contentWindow;
                if(child && child.XMLHttpRequest){
                    patch(child);
                }
                sn.setRelativeData('.root_pings', window._pingCount);
                sn.setRelativeData('.iframe_pings', child ? child._pingCount : null);
            }, 500);
        """, _onStart=True)
        pane.iframe(src='/test/tools/polling_iframe_child', nodeId='pollingChild',
                    height='240px', width='100%', border='1px solid silver')
