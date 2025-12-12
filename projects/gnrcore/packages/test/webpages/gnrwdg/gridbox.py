# -*- coding: utf-8 -*-

"""Gridbox Component Tests

This module demonstrates the gridbox component, which uses CSS Grid Layout
for creating two-dimensional layouts with rows and columns.
"""

class GnrCustomWebPage(object):
    py_requires="""gnrcomponents/testhandler:TestHandlerBase,
                    th/th:TableHandler"""

    def test_0_basic_gridbox(self,pane):
        """Basic gridbox: Fixed grid with CSS template

        This example demonstrates a simple gridbox using explicit CSS grid-template-columns.
        The grid has 4 equal-width columns (1fr each) and auto-generates rows as needed.

        This is the most basic way to create a grid layout.
        """
        bc = pane.borderContainer(height='500px',width='600px',border='1px solid lime')

        # Create gridbox with explicit CSS grid template
        fc = bc.contentPane(region='center').gridbox(
            width='400px', height='400px',
            style='grid-template-columns:repeat(4,1fr)',  # 4 equal columns
            border='1px solid silver', padding='5px',
            margin='5px')

        # Add items - they'll flow into the grid automatically
        for k in range(20):
            fc.div(f'Item {k}', border='1px solid red', margin='5px',
                  padding='5px', text_align='center')

    def test_1_columns_colspan_rowspan(self,pane):
        """Gridbox with colspan and rowspan

        This example demonstrates:
        - Setting columns dynamically with the 'columns' parameter (simpler than CSS)
        - Using colspan to make items span multiple columns
        - Using rowspan to make items span multiple rows
        - Using column_gap and row_gap for spacing

        Try changing the number of columns to see how the grid adapts.
        """
        bc = pane.borderContainer(height='500px',width='600px',border='1px solid lime')
        bc.contentPane(region='right',width='100px',splitter=True,background='pink')

        # Control panel for dynamic column count
        fb = bc.contentPane(region='top').formbuilder(cols=2)
        fb.textBox(value='^.columns',default='4',lbl='Columns')

        # Create gridbox with dynamic columns and gap spacing
        fc = bc.contentPane(region='center').gridbox(
            width='90%',
            item_height='100px',
            columns='^.columns',  # Dynamic number of columns
            column_gap='10px',    # Horizontal spacing
            row_gap='5px',        # Vertical spacing
            border='1px solid silver',
            padding='5px',
            item_border='1px solid red',  # Default border for all items
            margin='5px')

        # Items with different spans
        fc.div('Item 1')
        fc.div('Item 2 (colspan=2)', colspan=2, border='1px solid green')  # Spans 2 columns
        fc.div('Item 3 (rowspan=2)', rowspan=2, height='100%')  # Spans 2 rows
        fc.div('Item 4')
        fc.div('Item 5')
        fc.div('Item 6')


    def test_2_positioned_item(self,pane):
        """Gridbox with precisely positioned item

        This example shows how to place an item at a specific grid position
        using CSS grid-column-start, grid-column-span, grid-row-start, and grid-row-span.

        The item is positioned at column 2, row 2, and spans 2 columns and 2 rows,
        creating a centered element in the grid.
        """
        bc = pane.borderContainer(height='500px',width='600px',border='1px solid lime')
        bc.contentPane(region='right',width='100px',splitter=True,background='pink')

        # Create 4-column grid
        fc = bc.contentPane(region='center').gridbox(
            width='90%', height='400px',
            style='grid-template-columns:repeat(4,1fr);column-gap:10px;row-gap:5px;',
            border='1px solid silver',
            padding='5px',
            margin='5px')

        # Single item positioned and sized explicitly
        # Starts at column 2, row 2 and spans 2x2 cells
        fc.div('Centered Item (2x2)',
              style='grid-column-start: 2;grid-column-span: 2;grid-row-start: 2; grid-row-span:2;',
              border='1px solid green',
              padding='20px',
              text_align='center')


    def test_3_gridbox_as_form(self,pane):
        """Gridbox as form layout: Alternative to formbuilder

        This example demonstrates using gridbox instead of formbuilder for form layouts.
        Gridbox offers more flexible control over field positioning and spanning.

        Key features:
        - Dynamic column count
        - Fields can span multiple columns (see email field)
        - Consistent spacing with gap parameter
        - Label positioning with lbl_side parameter

        Gridbox is ideal when you need more control than formbuilder provides.
        """
        bc = pane.borderContainer(height='200px',border='1px solid lime')

        # Control panel for dynamic columns
        fb = bc.contentPane(region='top').formbuilder(cols=2)
        fb.textBox(value='^.columns',default='3',lbl='Columns')

        # Gridbox with dynamic columns used as form layout
        gb = bc.contentPane(region='center').gridbox(columns='^.columns',gap='10px',
                                                     margin='10px')
        side = 'top'

        # Form fields in grid layout
        gb.textbox(value='^.nome',lbl='Nome',lbl_side=side)
        gb.textbox(value='^.cognome',lbl='Cognome',lbl_side=side)
        gb.dateTextBox(value='^.nato_il',lbl='Nato il',lbl_side=side)

        # Email field spans 2 columns
        gb.textbox(value='^.email',lbl='Email',lbl_side=side,
                  colspan=2)

        gb.radioButtonText(value='^.genere',values='M:Maschi,F:Femmina,N:Neutro',
                          lbl='Genere',lbl_side=side)
        gb.checkbox(value='^.privacy',label='Accetto privacy',
                   lbl='Privacy',lbl_side=side)

    def test_4_gridbox_with_labledbox(self,pane):
        """Gridbox with labledBox items: Styled form containers

        This example shows gridbox combined with labledBox for creating
        visually appealing forms with labeled sections.

        Features demonstrated:
        - Dynamic styling with item_* parameters
        - labledBox for labeled containers
        - rowspan for spanning multiple rows
        - Conditional visibility (email field)
        - Live preview of styling changes

        Try adjusting the styling parameters to see the effects.
        """
        bc = pane.borderContainer(height='400px')
        top = bc.contentPane(region='top')

        # Control panel for styling parameters
        gb = top.gridbox(columns=4,gap='10px',margin='5px',
                        nodeId='boxControllers',datapath='.controllers')
        gb.h3('Box Styling Controls',colspan=4)
        gb.textBox(value='^.columns',default='3',lbl='Columns')
        gb.filteringSelect(value='^.item_side',lbl='Label Side',values='top,left,bottom,right')
        gb.textbox(value='^.item_border',lbl='Item border')
        gb.numberTextBox(value='^.item_rounded',lbl='Rounded')
        gb.input(value='^.item_box_l_background',lbl='Label background',type='color')
        gb.textbox(value='^.item_box_c_padding',lbl='Content Padding')
        gb.textbox(value='^.item_fld_border',lbl='Field border')
        gb.textbox(value='^.item_fld_background',lbl='Field background')

        # Form with labledBox items and dynamic styling
        prevbox = bc.contentPane(region='center').div(padding='10px')
        prevbox.h3('Preview Area')
        fl = prevbox.formlet(
            columns='^#boxControllers.columns',
            gap='10px',
            item_border='^#boxControllers.item_border',
            item_side='^#boxControllers.item_side',
            item_rounded='^#boxControllers.item_rounded',
            item_fld_border='^#boxControllers.item_fld_border',
            item_fld_background='^#boxControllers.item_fld_background',
            item_box_l_background='^#boxControllers.item_box_l_background',
            item_box_c_padding='^#boxControllers.item_box_c_padding')

        # Form fields with labledBox
        
        fl.labledBox('Nome',tip='bbb').textbox(value='^.nome',validate_notnull=True)
        fl.labledBox('Cognome',tip='aaa').textbox(value='^.cognome',validate_notnull=True)
        fl.labledBox('Genere',rowspan=2).radioButtonText(
            value='^.genere',values='M:Maschi,F:Femmina,N:Neutro',cols=1)
        fl.labledBox('Essendo Nato il').dateTextBox(value='^.nato_il')
        fl.labledBox('Pr.Nascita').dbSelect(value='^.provincia_nascita',
                                            table='glbl.provincia',hasDownArrow=True)
        fl.labledBox('Privacy acceptance').checkbox(value='^.privacy',label='Accept')
        fl.br()
        # Conditional field - only visible if privacy is accepted
        fl.textbox(value='^.email',lbl='Email',colspan=2,hidden='^.privacy?=!#v')

    def test_5_flexbox_vs_gridbox(self,pane):
        """Comparison: Flexbox with labledBox

        This example shows how labledBox can be used within a flexbox layout
        (vertical column) for creating complex interfaces. Compare with test_8
        to see the difference between flexbox and gridbox approaches.

        Flexbox is better for one-dimensional layouts where items should
        flow and adapt their size dynamically.
        """
        mainbc = pane.borderContainer(height='800px',width='500px')
        mainbc.contentPane(region='bottom',height='30%',splitter=True,background='#fee')

        # Vertical flexbox with labeled sections
        fbox = mainbc.contentPane(region='center').flexbox(
            height='100%',width='100%',flex_direction='column')

        # Table section
        fbox.labledBox('Table Section',height='30%',
                      border='1px solid silver',margin='5px',rounded=6
                      ).borderContainer().plainTableHandler(
                          region='center',table='glbl.provincia',condition_onStart=True)

        # Form section
        fl = fbox.labledBox('Form Section',height='20%',
                           border='1px solid silver',margin='5px',rounded=6
                           ).formlet(cols=2)
        fl.textbox(value='^.nome',lbl='Nome')
        fl.textbox(value='^.cognome',lbl='Cognome')
        fl.textbox(value='^.indirizzo',lbl='Indirizzo',colspan=2)

        # Mixed layout section
        bc = fbox.labledBox('Mixed Layout',height='15%',
                           border='1px solid silver',margin='5px',rounded=6
                           ).borderContainer()
        bc.contentPane(region='top',height='20%',background='lime',splitter=True)
        bc.contentPane(region='right',width='20%',background='salmon',splitter=True)
        bc.contentPane(region='center',background='pink')

        # Flexible section (fills remaining space)
        fbox.labledBox('Flexible Section',
                      border='1px solid silver',margin='5px',flex=1,rounded=6)