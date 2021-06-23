# -*- coding: utf-8 -*-

"""Html iframe tester"""
from gnr.web.gnrwebstruct import struct_method

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    def test_0_external(self, pane):
        """Basic test for an external iframe with no attributes"""
        bc = pane.borderContainer(height='800px',width='800px')
        center = bc.contentPane(region='center',overflow='hidden')
        center.htmliframe(src='http://mappe.comune.genova.it/mapstore/?public=yes&mapId=805',height='100%',width='100%',border='0px')

    def test_1_iframe(self,pane):
        "Iframe with tabContainer: frame to insert city and second frame with page where you find data"
        sc = pane.tabContainer(selectedPage='^currentPage', nodeId='maintab', height='400px')
        frame = sc.framepane(frameCode='test', datapath='test', pageName='selector', title='Insert Data')
        top = frame.top.slotBar(slots='foo')
        fb = top.foo.formbuilder()
        fb.dbselect(value='^.prov',dbtable='glbl.provincia',lbl='Provincia')
        fb.dataController("SET currentPage=pageName;genro.publish({'topic':'load','iframe':'*','form':'baseform'},{destPkey:pkey});",
                           pkey="^.prov", pageName='iframe_inside')
        sc.createFrameTab(pageName='iframe_inside',title='Read Data')
        
    @struct_method
    def createFrameTab(self,sc,pageName='',**kwargs):
        pane = sc.contentPane(pageName=pageName,overflow='hidden',**kwargs).contentPane(_lazyBuild=True,overflow='hidden')
        pane.iframe(height='100%',width='100%',border='0', nodeId=pageName,src=f'/test/{pageName}',
                        onCreated='console.log("created");')