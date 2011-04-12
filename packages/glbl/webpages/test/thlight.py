# -*- coding: UTF-8 -*-

# thlight.py
# Created by Francesco Porcari on 2011-03-30.
# Copyright (c) 2011 Softwell. All rights reserved.

"Test page description"
class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,tablehandler/th_components:TableHandlerBase"
         
    def test_0_localita(self,pane):
        """First test description"""
        sc = pane.stackTableHandler(widget_height='400px',table='glbl.localita')
        sc.form.store.handler('load',default_provincia='MI')

    def test_1_provincia(self,pane):
        """First test description"""
        sc = pane.stackTableHandler(widget_height='400px',table='glbl.provincia')
        sc.form.store.handler('load',default_regione='LOM')
    
   #def test_2_provincia2(self,pane):
   #    """First test description"""
   #    sc = pane.stackTableHandler(widget_height='400px',nodeId='provinciali',table='glbl.provincia')
   #    sc.form.store.handler('load',default_regione='LOM')