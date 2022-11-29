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
                            field_name="visited", 
                            field_caption="Ever been there?",
                            height='250px', width='100%')
    
    def test_1_radioButton_items(self, pane):
        "evaluationGrid permits items evaluation through radioButtons. Items can be a string of \n separated items."
        pane.evaluationGrid(value='^.evaluation', 
                            title="Italian pizza restaurants evaluation",
                            items="Luciano's\n Domino's\n Pizza Hut", 
                            field_values="B:Bad,G:Good,A:Awesome",
                            field_name="level", 
                            field_caption="Level",
                            choice_width='6em',
                            height='250px', width='100%')

    def test_2_checkbox_items(self, pane):
        """If an aggregator is present, checkbox is used instead of radioButton. 
        Aggregator can basically be a ',' or '+' to sum and '*'"""
        pane.evaluationGrid(value='^.features', 
                            title="Which features did you appreciate at most in these Italian pizza restaurants",
                            items="LL:Luciano's,DD:Domino's,PH:Pizza Hut", 
                            field_values="L:Loc.,M:Menu,S:Service,P:Price",
                            #field_aggr=',',
                            field_name="features", 
                            field_caption="Appreciated features",
                            showValue=True,
                            height='250px', width='100%')

    def test_3_checkbox_sum(self, pane):
        "evaluationGrid can be used as quiz system as well to sum votes and totalize global evaluation."
        pane.evaluationGrid(value='^.evaluation', 
                            title="Which Genropy grids are more suitable for these situations? (max 2 options)",
                            items="Watch and edit table records,Evaluate items with specific values,Rapidly list items in a grid,List items in a grid with a custom and more elaborated struct", 
                            field_values="1:TableHandler,1:evaluationGrid,2:quickGrid,3:bagGrid",
                            field_dtype='L',
                            #field_aggr='+',
                            #field_totalize=True,
                            field_name='components',
                            field_caption="Gnr components",
                            showValue=True,
                            choice_width='8em',
                            value_width='2em',
                            height='250px', width='100%')