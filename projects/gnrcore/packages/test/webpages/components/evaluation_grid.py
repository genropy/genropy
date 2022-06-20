# -*- coding: utf-8 -*-

# Created by Davide Paci on 2022-06.

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/framegrid:EvaluationGrid"

    def test_0_radioButton_table(self, pane):
        "evaluationGrid permits items evaluation through radioButtons. Items can be table records."
        pane.evaluationGrid(value='^.evaluation', 
                            title="Visited/Not visited regions",
                            table='glbl.regione',
                            field_values="1:Yes,2:No",
                            field_name="visited", field_caption="Ever been there?",
                            height='250px', width='100%')
    
    def test_1_radioButton_items(self, pane):
        "evaluationGrid permits items evaluation through radioButtons. Items can be a string of comma separated items."
        pane.evaluationGrid(value='^.evaluation', 
                            title="Italian pizza restaurants evaluation",
                            items="Luciano's, Domino's, Pizza Hut", 
                            field_values="1:Bad,2:Good,3:Awesome",
                            field_name="level", field_caption="Level",
                            height='250px', width='100%')

    def test_2_checkbox_items(self, pane):
        """If an aggregator is present, checkbox is used instead of radioButton. 
        Aggregator can basically be a ',' or '+' to sum and '*'"""
        pane.evaluationGrid(value='.features', 
                            title="Which features did you appreciate at most in these Italian pizza restaurants",
                            items="Luciano's, Domino's, Pizza Hut", 
                            field_values="1:Location,2:Menu,3:Service,4:Price",
                            field_aggr=',',
                            field_name="features", field_caption="Appreciated features",
                            height='250px', width='100%')
        
    def test_3_checkbox_sum(self, pane):
        "evaluationGrid can be used as quiz system as well to sum votes and totalize global evaluation."
        pane.evaluationGrid(value='.evaluation', 
                            title="How do you rate Genropy's evaluationGrid? (max 2 options)",
                            items="It is useful for  ", 
                            field_values="1:Bad,2:Adequate,3:Good,4:Excellent",
                            field_aggr='+',
                            field_totalize=True,
                            field_name="features", field_caption="Appreciated features",
                            height='250px', width='100%')