# -*- coding: utf-8 -*-

"""Bag from external formats"""

from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    def test_0_json(self, pane):

        pane.button('Test').dataController("""
        var val_L = 2;
        var val_R = 2.3;
        var val_N = 5.6;
        val_L._gnrdtype = 'L';
        val_R._gnrdtype = 'R';
        val_N._gnrdtype = 'N';
        var val_D = new Date();
        val_D._gnrdtype = 'D';
        val_D.setHours(0, 0, 0, 0);
        var val_DH = new Date();
        val_DH._gnrdtype = 'DH';
        genro.serverCall('remoteTester',{
            val_L:val_L,
            val_R:val_R,
            val_N:val_N,
            val_D:val_D,
            val_DH:val_DH,
            val_LIST : [val_L,val_R,val_N,val_D,val_DH],
            val_DICT : {
                val_L:val_L,
                val_R:val_R,
                val_N:val_N,
                val_D:val_D,
                val_DH:val_DH,
                val_LIST: [val_L,val_R,val_N,val_D,val_DH]
            }
        },function(result){});
        
        """)



    @public_method
    def remoteTester(self,**kwargs):
        raise Exception("XXX exception")

    def test_1_rpcjson(self, pane):
        btn = pane.button('Test')
        btn.dataRpc(self.testResultJson,
                    _onResult="""
                    alert(result.message);
                    """)

    @public_method
    def testResultJson(self):
        return dict(message='Pippo',number=8)
