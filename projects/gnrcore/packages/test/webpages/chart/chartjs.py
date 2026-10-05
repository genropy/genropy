# -*- coding: utf-8 -*-

"""Chart.js: charts from literal data, from a Bag and from a grid

The `chartjs` element draws a Chart.js chart from a literal `data` dict. On a
grid, the `chartjs` toolbar slot opens a chart of the grid's rows; a
`chartPane` draws its datasets either from a Bag (`value`) or from the store
of the grid it is `connectedTo`, and `paletteChart` does the same in a
floating palette. Edits in the grid redraw the chart.
"""

from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,js_plugins/chartjs/chartjs:ChartManager"

    def source_viewer_open(self):
        return False
    def test_0_simple(self, pane):
        """A line chart of two datasets given as a literal Chart.js `data` dict"""
        pane.chartjs(nodeId='testchart_2',chartType='line',data={
                'labels': ["Red", "Blue", "Yellow", "Green", "Purple", "Orange"],
                'datasets': [{
                    'label': '# of Votes',
                    'data': [12, 19, 3, 5, 2, 3],
                    'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                    'borderColor': 'rgba(255,99,132,1)',
                    'borderWidth': 1
                },{
                    'label': '# of Votes last year',
                    'data': [10, 16, 8, 9, 6, 3],
                    'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                    'borderColor': 'rgba(54, 162, 235, 1)',
                    'borderWidth': 1
                }]
            },options={'scales': {'y': {'beginAtZero': True}}},
            height='300px',width='600px',border='1px solid silver')

    def test_2_bagDataValue(self, pane):
        """The `chartjs` slot in a bagGrid's toolbar: its menu opens a chart of the rows"""
        pane.data('.databag',self.getTestData())
        pane.dataFormula('.data','databag',databag='=.databag',_onStart=True)
        bc = pane.borderContainer(height='600px',width='800px',_anchor=True)
        frame = bc.bagGrid(storepath='#ANCHOR.data',region='center',
                        struct=self.bmiStruct,export=True)
        frame.top.bar.replaceSlots('delrow','chartjs,delrow,duprow')

    def test_22_bagDataValue(self, pane):
        """A quickGrid on attribute rows, with add, delete and export tools"""
        pane.data('.databag',self.getTestData2())
        pane.dataFormula('.data','databag',databag='=.databag',_onStart=True)
        bc = pane.borderContainer(height='600px',width='800px',_anchor=True)
        grid = bc.contentPane(region='center').quickGrid(value='^.data',datamode='attr')
        grid.tools('addrow,delrow,export')

    def bmiStruct(self,struct):
        r = struct.view().rows()
        r.cell('nome',edit=True,name='Name')
        r.cell('eta',edit=True,name='Age',dtype='L')
        r.cell('peso',edit=True,name='Weight',dtype='L')
        r.cell('altezza',edit=True,name='Height',dtype='L')#(peso||0)/((altezza||1)*(altezza||1))
        r.cell('bmi',formula='(peso||0)/((altezza/100||1)*(altezza/100||1))',name='BMI',dtype='N',calculated=True)

    def getTestData(self):
        result = Bag()
        result.setItem('r_0',Bag(dict(nome='Mario Rossi',eta=30,peso=80,altezza=190,
                                     chart_backgroundColor='red')))
        result.setItem('r_1',Bag(dict(nome='Luigi Bianchi',eta=38,peso=90,altezza=180,
                                    chart_backgroundColor='green')))
        result.setItem('r_2',Bag(dict(nome='Rossella Albini',eta=22,peso=60,altezza=170,
                                    chart_backgroundColor='navy')))
        return result

    def getTestData2(self):
        result = Bag()
        result.setItem('r_0',None,nome='Mario Rossi',eta=30,peso=80,altezza=190,
                                     chart_backgroundColor='red')
        result.setItem('r_1',None,nome='Luigi Bianchi',eta=38,peso=90,altezza=180,
                                    chart_backgroundColor='green')
        result.setItem('r_2',None,nome='Rossella Albini',eta=22,peso=60,altezza=170,
                                    chart_backgroundColor='navy')
        return result



    def test_9_chartPane(self,pane):
        """A chartPane on a Bag value, its configurator opened by a button"""
        bc = pane.borderContainer(height='800px',_anchor=True)
        bc.data('.testData',self.getTestData())
        fb = bc.contentPane(region='top').formbuilder()
        fb.button('Configurations',action="PUBLISH myconfigurator_open")
        #pane = fb.palettePane(title='Params',paletteCode='params',dockButton=True)
        bc.chartPane(value='^.testData',
                    region='center',
                    captionField='nome',
                    datasetFields="peso,altezza",
                    chartType='bar',
                    _workspace_path='aux.myconfigurations',
                    configurator=dict(palette='myconfigurator',userObject=False),
                    datamode='bag')
        


    def test_3_chartpane_value(self,pane):
        """A chartPane whose `value` is the store of a bagGrid: editing a weight redraws the line"""
        bc = pane.borderContainer(height='700px',_anchor=True)
        bc.data('.store',self.getTestData())
        bc.contentPane(region='center').bagGrid(frameCode='chartValueGrid',storepath='#ANCHOR.store',
                                                struct=self.bmiStruct)
        bc.chartPane(value='^.store',
                    region='bottom',height='400px',
                    captionField='nome',
                    datasetFields='peso,altezza',
                    configurator=True,
                    chartType='line',
                    datamode='bag')

    def test_4_chartpane_connected(self,pane):
        """A chartPane `connectedTo` a bagGrid: it reads the grid's own store"""
        bc = pane.borderContainer(height='700px',_anchor=True)
        bc.data('.store',self.getTestData())
        frame = bc.contentPane(region='center').bagGrid(frameCode='chartConnectedGrid',
                                                        storepath='#ANCHOR.store',
                                                        struct=self.bmiStruct)
        bc.chartPane(connectedTo=frame.grid,
                    region='bottom',height='400px',
                    captionField='nome',
                    datasetFields='peso,altezza',
                    configurator=True,
                    chartType='bar')

    def test_5_palette_chart(self,pane):
        """A paletteChart docked in a bagGrid's toolbar, connected to that grid"""
        bc = pane.borderContainer(height='400px',_anchor=True)
        bc.data('.store',self.getTestData())
        frame = bc.contentPane(region='center').bagGrid(frameCode='chartPaletteGrid',
                                                        storepath='#ANCHOR.store',
                                                        struct=self.bmiStruct)
        bar = frame.top.bar.replaceSlots('#','#,chartPalette,5')
        bar.chartPalette.paletteChart(connectedTo=frame.grid,
                    title='Chart',
                    height='500px',width='700px',dockButton=True,
                    captionField='nome',
                    datasetFields='peso,altezza',
                    configurator=True,
                    chartType='bar')
