.. _flexbox:

=======
Flexbox
=======

    *Last page update*: |today|

    .. note:: Flexbox features:

              * **Type**: Layout container
              * **Common attributes**: check the :ref:`attributes_index` section

    * :ref:`flexbox_def`
    * :ref:`flexbox_params`
    * :ref:`flexbox_examples`:

        * :ref:`flexbox_ex_basic`
        * :ref:`flexbox_ex_alignment`
        * :ref:`flexbox_ex_nested`
        * :ref:`flexbox_ex_multiline`
        * :ref:`flexbox_ex_practical`

.. _flexbox_def:

Definition
==========

    .. method:: pane.flexbox([direction=None, wrap=None, align_content=None, justify_content=None, align_items=None, justify_items=None, **kwargs])

                Create a flexbox container for flexible layout of child elements.

                The flexbox container uses CSS Flexbox layout to arrange child elements in a flexible,
                responsive manner. It provides powerful alignment and distribution capabilities for
                one-dimensional layouts (either horizontal or vertical).

.. _flexbox_params:

Parameters
==========

    **direction** (str): Main axis direction for flex items.

        * ``'row'``: Left to right (default)
        * ``'column'``: Top to bottom
        * ``'row-reverse'``: Right to left
        * ``'column-reverse'``: Bottom to top

    **wrap** (bool or str): Whether flex items should wrap to next line.

        * ``True`` or ``'wrap'``: Items wrap onto multiple lines
        * ``False`` or ``'nowrap'``: Items stay on single line (default)
        * ``'wrap-reverse'``: Items wrap in reverse order

    **align_content** (str): Aligns lines when there is extra space on cross axis (works with wrap=True).

        * ``'flex-start'``: Lines packed to start
        * ``'flex-end'``: Lines packed to end
        * ``'center'``: Lines centered
        * ``'space-between'``: Lines evenly distributed
        * ``'space-around'``: Lines with equal space around
        * ``'stretch'``: Lines stretch to fill container (default)

    **justify_content** (str): Aligns items along main axis.

        * ``'flex-start'``: Items packed to start (default)
        * ``'flex-end'``: Items packed to end
        * ``'center'``: Items centered
        * ``'space-between'``: Items evenly distributed
        * ``'space-around'``: Items with equal space around
        * ``'space-evenly'``: Items with equal space between

    **align_items** (str): Aligns items along cross axis.

        * ``'flex-start'``: Items aligned to start
        * ``'flex-end'``: Items aligned to end
        * ``'center'``: Items centered
        * ``'baseline'``: Items aligned to baseline
        * ``'stretch'``: Items stretch to fill (default)

    **justify_items** (str): Justifies items within their area (grid-specific property).

    ****kwargs**: Additional HTML/CSS attributes (e.g., height, width, border, padding)

.. _flexbox_examples:

Examples
========

.. _flexbox_ex_basic:

Basic Direction and Wrap
-------------------------

This example demonstrates the fundamental flexbox properties: **direction** and **wrap**.

    * **Code**::

        def test_0_basic(self, pane):
            """Basic flexbox: direction and wrap"""
            bc = pane.borderContainer(height='500px', width='600px')

            # Control panel
            fb = bc.contentPane(region='top').formbuilder(cols=2)
            fb.filteringSelect(value='^.direction',
                             values='row,column,row-reverse,column-reverse',
                             lbl='Direction', default='row')
            fb.checkbox(value='^.wrap', label='Wrap')

            # Flexbox with limited size to show wrapping
            fc = bc.contentPane(region='center').flexbox(
                direction='^.direction',
                wrap='^.wrap',
                width='300px', height='400px',
                border='1px solid silver',
                padding='5px')

            # Add multiple items
            for k in range(20):
                fc.div(f'Item {k}',
                      border='1px solid red',
                      height='40px', width='40px',
                      margin='5px', text_align='center')

.. _flexbox_ex_alignment:

Justify and Align Properties
-----------------------------

This example demonstrates alignment properties: **justify_content** and **align_items**.

    * **Code**::

        def test_1_alignment(self, pane):
            """Flexbox alignment"""
            bc = pane.borderContainer(height='500px', width='700px')

            # Control panel
            fb = bc.contentPane(region='top').formbuilder(cols=2)
            fb.filteringSelect(value='^.justify_content',
                             values='flex-start,flex-end,center,space-between,space-around,space-evenly',
                             lbl='Justify Content', default='flex-start')
            fb.filteringSelect(value='^.align_items',
                             values='flex-start,flex-end,center,baseline,stretch',
                             lbl='Align Items', default='stretch')

            # Flexbox with alignment controls
            fc = bc.contentPane(region='center').flexbox(
                direction='row',
                justify_content='^.justify_content',
                align_items='^.align_items',
                height='400px',
                border='1px solid silver',
                padding='10px',
                background='#f5f5f5')

            # Items with varying sizes
            fc.div('Small', border='2px solid blue',
                  height='40px', width='60px',
                  background='lightblue')
            fc.div('Medium', border='2px solid green',
                  height='80px', width='80px',
                  background='lightgreen')
            fc.div('Large', border='2px solid red',
                  height='120px', width='100px',
                  background='lightcoral')

.. _flexbox_ex_nested:

Nested Flexbox for 2D Layouts
------------------------------

This example shows how to nest flexboxes to create complex two-dimensional layouts.

    * **Code**::

        def test_2_nested(self, pane):
            """Nested flexbox layouts"""
            # Outer flexbox (horizontal)
            fc = pane.flexbox(direction='row', wrap=True,
                            width='500px', height='400px',
                            border='1px solid silver')

            # Create nested flexboxes (vertical)
            for j in range(5):
                innerFc = fc.flexbox(direction='column',
                                   flex_basis='100px',
                                   margin='5px',
                                   border='1px solid pink')
                for k in range(5):
                    innerFc.div(f'{j}-{k}',
                              border='1px solid red',
                              flex_basis='10px',
                              margin='2px',
                              text_align='center')

.. _flexbox_ex_multiline:

Multi-line Alignment with align_content
----------------------------------------

This example demonstrates **align_content** for controlling spacing between wrapped lines.

    * **Code**::

        def test_3_multiline(self, pane):
            """Multi-line flexbox with align_content"""
            bc = pane.borderContainer(height='500px', width='700px')

            # Control panel
            fb = bc.contentPane(region='top').formbuilder(cols=2)
            fb.filteringSelect(value='^.align_content',
                             values='flex-start,flex-end,center,space-between,space-around,stretch',
                             lbl='Align Content', default='stretch')

            # Flexbox with wrapping enabled
            fc = bc.contentPane(region='center').flexbox(
                direction='row',
                wrap=True,
                align_content='^.align_content',
                height='400px',
                width='600px',
                border='1px solid silver',
                padding='10px')

            # Add many items to force wrapping
            for k in range(15):
                fc.div(f'Item {k}',
                      border='1px solid red',
                      height='60px', width='80px',
                      margin='5px',
                      background='lightyellow')

.. _flexbox_ex_practical:

Practical Layouts
-----------------

Common UI patterns using flexbox.

    * **Code**::

        def test_4_practical(self, pane):
            """Practical flexbox layouts"""
            bc = pane.borderContainer(height='600px', width='800px')

            # Example 1: Centered content (login form)
            section1 = bc.contentPane(region='top', height='200px')
            centered = section1.flexbox(
                justify_content='center',
                align_items='center',
                height='150px',
                background='#f9f9f9')
            loginBox = centered.div(
                border='2px solid #333',
                padding='20px',
                background='white',
                border_radius='8px')
            loginBox.div('Login Form', font_size='18px')

            # Example 2: Navigation bar
            section2 = bc.contentPane(region='center', height='200px')
            navbar = section2.flexbox(
                direction='row',
                justify_content='space-between',
                align_items='center',
                padding='10px',
                background='#2c3e50',
                color='white')
            navbar.div('Logo', font_size='20px', font_weight='bold')
            navItems = navbar.flexbox(direction='row')
            for item in ['Home', 'About', 'Services', 'Contact']:
                navItems.div(item, margin='0 10px')

            # Example 3: Card layout
            section3 = bc.contentPane(region='bottom')
            cards = section3.flexbox(
                direction='row',
                wrap=True,
                justify_content='space-around',
                padding='10px')
            for i in range(6):
                card = cards.div(
                    border='1px solid #ddd',
                    border_radius='8px',
                    padding='15px',
                    width='150px',
                    background='white')
                card.div(f'Card {i+1}', font_weight='bold')
                card.div('Description', font_size='12px')

See Also
========

    * :ref:`gridbox` - For two-dimensional grid-based layouts
    * :ref:`bordercontainer` - For region-based layouts
    * :ref:`formbuilder` - For form layouts
