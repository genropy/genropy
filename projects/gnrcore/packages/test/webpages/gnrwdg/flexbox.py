# -*- coding: utf-8 -*-

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/source_viewer/source_viewer:SourceViewer"

    def test_0_basic_direction_wrap(self,pane):
        """Basic flexbox: direction and wrap

        This example demonstrates the fundamental flexbox properties:
        - direction: Controls the main axis (row, column, row-reverse, column-reverse)
        - wrap: Controls whether items wrap to next line when they overflow

        Try changing direction and enabling wrap to see how items flow.
        """
        bc = pane.borderContainer(height='500px',width='600px',border='1px solid lime')
        fb = bc.contentPane(region='top').formbuilder(cols=2)
        fb.filteringSelect(value='^.direction',values='row,column,row-reverse,column-reverse',
                          lbl='Direction',default='row')
        fb.checkbox(value='^.wrap',label='Wrap')

        # Create flexbox with limited size to show wrapping behavior
        fc = bc.contentPane(region='center').flexbox(direction='^.direction',wrap='^.wrap',
                                                     width='300px',height='400px',
                                                     border='1px solid silver',padding='5px',
                                                     margin='5px')
        # Add multiple items to demonstrate wrapping
        for k in range(20):
            fc.div(f'Item {k}',border='1px solid red',height='40px',width='40px',
                  margin='5px',padding='5px',text_align='center')


    def test_1_justify_align(self,pane):
        """Flexbox alignment: justify_content and align_items

        This example demonstrates alignment properties:
        - justify_content: Aligns items along the main axis
        - align_items: Aligns items along the cross axis

        These properties control how items are positioned and spaced within the container.
        """
        bc = pane.borderContainer(height='500px',width='700px',border='1px solid lime')
        fb = bc.contentPane(region='top').formbuilder(cols=2,border_spacing='5px')
        fb.filteringSelect(value='^.justify_content',
                          values='flex-start,flex-end,center,space-between,space-around,space-evenly',
                          lbl='Justify Content',default='flex-start')
        fb.filteringSelect(value='^.align_items',
                          values='flex-start,flex-end,center,baseline,stretch',
                          lbl='Align Items',default='stretch')

        # Create flexbox demonstrating alignment
        fc = bc.contentPane(region='center').flexbox(
            direction='row',
            justify_content='^.justify_content',
            align_items='^.align_items',
            height='400px',width='600px',
            border='1px solid silver',padding='10px',
            margin='10px',background='#f5f5f5')

        # Add items with varying sizes to show alignment
        fc.div('Small',border='2px solid blue',height='40px',width='60px',
              margin='5px',padding='5px',background='lightblue')
        fc.div('Medium',border='2px solid green',height='80px',width='80px',
              margin='5px',padding='5px',background='lightgreen')
        fc.div('Large',border='2px solid red',height='120px',width='100px',
              margin='5px',padding='5px',background='lightcoral')
        fc.div('Tall',border='2px solid purple',height='150px',width='60px',
              margin='5px',padding='5px',background='plum')

    def test_2_nested_flexbox(self,pane):
        """Nested flexbox: Creating 2D layouts

        This example shows how to nest flexboxes to create complex 2D layouts.
        The outer flexbox controls one direction, inner flexboxes control another.

        This is useful for creating grid-like layouts with flexible sizing.
        """
        bc = pane.borderContainer(height='500px',width='600px',border='1px solid lime')
        fb = bc.contentPane(region='top').formbuilder(cols=2)
        fb.filteringSelect(value='^.direction',values='row,column,row-reverse,column-reverse',
                          lbl='Outer Direction',default='row')
        fb.filteringSelect(value='^.inner_direction',values='row,column,row-reverse,column-reverse',
                          lbl='Inner Direction',default='column')
        fb.checkbox(value='^.wrap',label='Wrap')

        # Outer flexbox
        fc = bc.contentPane(region='center').flexbox(direction='^.direction',wrap='^.wrap',
                                                     width='500px',height='400px',
                                                     border='1px solid silver',padding='5px',
                                                     margin='10px')
        # Create nested flexboxes
        for j in range(5):
            innerFc = fc.flexbox(direction='^.inner_direction',
                                flex_basis='100px',margin='5px',
                                border='1px solid pink',padding='3px',
                                background='#fff0f5')
            for k in range(5):
                innerFc.div(f'{j}-{k}',border='1px solid red',flex_basis='10px',
                           margin='2px',padding='2px',text_align='center',
                           font_size='10px')


    def test_3_align_content(self,pane):
        """Flexbox align_content: Multi-line alignment

        This example demonstrates align_content property:
        - align_content: Controls spacing between wrapped lines (only works with wrap=True)

        This is particularly useful when you have multiple rows/columns and want to control
        how they are distributed in the container.
        """
        bc = pane.borderContainer(height='500px',width='700px',border='1px solid lime')
        fb = bc.contentPane(region='top').formbuilder(cols=2,border_spacing='5px')
        fb.filteringSelect(value='^.align_content',
                          values='flex-start,flex-end,center,space-between,space-around,stretch',
                          lbl='Align Content',default='stretch')
        fb.checkbox(value='^.wrap',label='Wrap',default=True)

        # Create flexbox with wrap to demonstrate align_content
        fc = bc.contentPane(region='center').flexbox(
            direction='row',
            wrap='^.wrap',
            align_content='^.align_content',
            height='400px',width='600px',
            border='1px solid silver',padding='10px',
            margin='10px',background='#f5f5f5')

        # Add many items to force wrapping
        for k in range(15):
            fc.div(f'Item {k}',border='1px solid red',height='60px',width='80px',
                  margin='5px',padding='5px',text_align='center',
                  background='lightyellow')

    def test_4_practical_layouts(self,pane):
        """Practical flexbox layouts: Common UI patterns

        This example shows practical use cases:
        - Centered content (login forms, dialogs)
        - Header with navigation
        - Card layouts with equal spacing

        These are common patterns you'll use in real applications.
        """
        bc = pane.borderContainer(height='600px',width='800px',border='1px solid lime')

        # Example 1: Centered content (typical for login/dialog)
        section1 = bc.contentPane(region='top',height='200px',
                                 border_bottom='2px solid #ccc')
        section1.div('Example 1: Centered Content',font_weight='bold',
                    padding='5px',background='#eee')
        centered = section1.flexbox(justify_content='center',align_items='center',
                                    height='150px',background='#f9f9f9')
        loginBox = centered.div(border='2px solid #333',padding='20px',
                               background='white',border_radius='8px')
        loginBox.div('Login Form',font_size='18px',font_weight='bold',margin_bottom='10px')
        loginBox.div('Username: ______',margin='5px')
        loginBox.div('Password: ______',margin='5px')

        # Example 2: Header with navigation (typical nav bar)
        section2 = bc.contentPane(region='center',height='200px',
                                 border_bottom='2px solid #ccc')
        section2.div('Example 2: Navigation Bar',font_weight='bold',
                    padding='5px',background='#eee')
        navbar = section2.flexbox(direction='row',justify_content='space-between',
                                 align_items='center',padding='10px',
                                 background='#2c3e50',color='white')
        navbar.div('Logo',font_size='20px',font_weight='bold')
        navItems = navbar.flexbox(direction='row')
        for item in ['Home','About','Services','Contact']:
            navItems.div(item,margin='0 10px',cursor='pointer')

        # Example 3: Card layout with equal spacing
        section3 = bc.contentPane(region='bottom',overflow='auto')
        section3.div('Example 3: Card Layout',font_weight='bold',
                    padding='5px',background='#eee')
        cards = section3.flexbox(direction='row',wrap=True,
                                justify_content='space-around',
                                padding='10px',background='#f9f9f9')
        for i in range(6):
            card = cards.div(border='1px solid #ddd',border_radius='8px',
                           padding='15px',margin='10px',width='150px',
                           background='white',box_shadow='0 2px 4px rgba(0,0,0,0.1)')
            card.div(f'Card {i+1}',font_weight='bold',margin_bottom='5px')
            card.div('Description text here',font_size='12px',color='#666')
