# -*- coding: utf-8 -*-

"""borderContainer"""

class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerBase,th/th:TableHandler,
                        dashboard_component/dashboard_component:DashboardItem"""
    
    def windowTitle(self):
        return 'borderContainer'
        
    def test_0_bordercontainer_filled(self,pane):
        """borderContainer filled with a contentPane with red background and a textbox. 
        Set height to show colored cp."""
        bc = pane.borderContainer(height='200px',border='1px solid silver')
        bc.contentPane(region='top',background='red').div(height='^.height')
        bc.contentPane(region='center').textbox(value='^.height', lbl='Set height', placeholder='50px')

    def test_1_regions(self,pane):
        "borderContainers can include dynamic subregions"
        bc = pane.borderContainer(height='300px')
        fb = bc.contentPane(region='top',height='50px').formbuilder(cols=4,border_spacing='10px',
                                                                        datapath='.regions', fld_width='100%')
        fb.textBox(value='^.top',lbl='top', placeholder='100px')
        fb.textBox(value='^.left',lbl='left', placeholder='100px')
        fb.textBox(value='^.bottom',lbl='bottom', placeholder='100px')
        fb.textBox(value='^.right',lbl='right', placeholder='100px')

        bc = bc.borderContainer(regions='^.regions',region='center')
        bc.contentPane(region='top',background='red',splitter=True)
        bc.contentPane(region='bottom',background='yellow',splitter=True)
        bc.contentPane(region='left',background='blue',splitter=True)
        bc.contentPane(region='right',background='green',splitter=True)
        bc.contentPane(region='center',background='white')

    def test_2_bordercontainer_inside_cp(self, pane):
        """borderContainer with red background inside a contentPane with green background. 
        bc is invisible"""
        bc = pane.contentPane(height='200px',background='green').borderContainer(background='red')
    
    def test_3_bordercontainer_inside_cp2(self, pane):
        """borderContainer with red background inside a contentpane which is inside a tabContainer with green background. 
        bc is visible, cp is invisible"""
        bc = pane.tabContainer(height='200px',background='green')
        bc.contentPane(background='yellow',title='aa').borderContainer(background='red')
    
    def test_4_region(self,pane):
        """borderContainer with a closable contentPane inside. 
        Using closable='close' it starts closed on loading."""
        bc = pane.borderContainer(height='300px')
        bc.contentPane(region='right',width='400px',background='red',closable='close')
        bc.contentPane(region='center',background='green').div()
