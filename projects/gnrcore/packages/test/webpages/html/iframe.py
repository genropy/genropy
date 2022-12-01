# -*- coding: utf-8 -*-

"""Html iframe tester"""
from gnr.web.gnrwebstruct import struct_method

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    def test_0_external(self, pane):
        """Basic test for an external iframe with no attributes"""
        bc = pane.borderContainer(height='800px',width='800px')
        center = bc.contentPane(region='center',overflow='hidden')
        center.htmliframe(src='http://mappe.comune.genova.it/mapstore/?public=yes&mapId=805',
                                                    height='100%',width='100%',border='0px')

    def test_1_iframe(self,pane):
        "Iframe with tabContainer: frame to insert city and second frame with page where you find data"
        bc = pane.borderContainer(height='400px')
        fb = bc.contentPane(region='top').formbuilder()
        fb.dbselect(value='^.prov', table='glbl.provincia', lbl='Provincia')
        fb.dataController("genro.publish({'topic':'load','iframe':'*','form':'baseform'},{destPkey:pkey});",
                           pkey="^.prov")
        bc.createFrameTab(title='Read Data')
        
    @struct_method
    def createFrameTab(self,bc,**kwargs):
        pane = bc.contentPane(region='center')
        pane.iframe(height='100%', width='100%', border='0', 
                        src=f'/test/iframe_inside', onCreated='console.log("created");')