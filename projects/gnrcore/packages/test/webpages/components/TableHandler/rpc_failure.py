# -*- coding: utf-8 -*-

"""Form behaviour when the load/save/delete rpc fails at http level."""

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,th/th:TableHandler,public:Public"
    maintable = 'glbl.provincia'

    def test_0_dialog(self, pane):
        """dialogTableHandler on glbl.provincia: open a row, then use the switches below."""
        pane.borderContainer(height='400px').contentPane(region='center').dialogTableHandler(
            table='glbl.provincia', view_store_onStart=True,
            dialog_height='300px', dialog_width='450px')

    def test_1_switches(self, pane):
        """Route the next rpc of the chosen kind to an unreachable url (status 0), then load, edit or delete a row.
        A transport failure is reported by genro.rpc itself, so the form adds no message of its own:
        expected is a dismiss on load, the changes kept on save, nothing deleted on delete, and no
        callback of the operation running. The monitor shows opStatus / changed / pkey of every form."""
        bar = pane.div(margin_bottom='6px')
        for method in ('loadRecordCluster', 'saveRecordCluster', 'deleteDbRow'):
            bar.button('Fail next %s' % method, action="genro.rpc.failNext[method]=true;", method=method)
        bar.button('Reset', action="genro.rpc.failNext={};")
        pane.div(nodeId='rpc_failure_monitor', font_family='monospace', font_size='12px', white_space='pre')
        pane.dataController("""
            if(!genro.rpc._origServerCall){
                genro.rpc._origServerCall = genro.rpc._serverCall;
                genro.rpc.failNext = {};
                genro.rpc.failLog = [];
                genro.rpc._serverCall = function(callKwargs, xhrKwargs, httpMethod){
                    var m = callKwargs.method;
                    if(genro.rpc.failNext[m]){
                        delete genro.rpc.failNext[m];
                        genro.rpc.failLog.push(m);
                        xhrKwargs = objectUpdate({}, xhrKwargs);
                        xhrKwargs.url = 'http://localhost:1/unreachable';
                    }
                    return genro.rpc._origServerCall.call(genro.rpc, callKwargs, xhrKwargs, httpMethod);
                };
            }
            var render = function(){
                var lines = ['failNext: '+JSON.stringify(genro.rpc.failNext)+'   failed: '+genro.rpc.failLog.join(',')];
                var seen = {};
                for(var k in genro.src._index){
                    var n = genro.src._index[k];
                    var f = n.form;
                    if(!f || f.sourceNode!==n || seen[f.formId]){ continue; }
                    seen[f.formId] = true;
                    lines.push(f.formId+' | opStatus='+f.opStatus+' changed='+f.changed+' pkey='+f.getCurrentPkey()+' status='+f.status);
                }
                var mon = genro.nodeById('rpc_failure_monitor');
                if(mon && mon.domNode){ mon.domNode.innerHTML = lines.join('<br/>'); }
            };
            setInterval(render, 500);
        """, _onStart=True)
