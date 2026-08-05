.. _gridbox:

=======
Gridbox
=======

    *Last page update*: |today|

    .. note:: Gridbox features:

              * **Type**: Layout container
              * **Common attributes**: check the :ref:`attributes_index` section

    * :ref:`gridbox_def`
    * :ref:`gridbox_params`
    * :ref:`gridbox_item_attrs`
    * :ref:`gridbox_examples`:

        * :ref:`gridbox_ex_basic`
        * :ref:`gridbox_ex_spanning`
        * :ref:`gridbox_ex_form`
        * :ref:`gridbox_ex_dashboard`
        * :ref:`gridbox_ex_comparison`

.. _gridbox_def:

Definition
==========

    .. method:: pane.gridbox([columns=None, align_content=None, justify_content=None, align_items=None, justify_items=None, table=None, **kwargs])

                Create a gridbox container for two-dimensional grid-based layouts.

                The gridbox container uses CSS Grid layout to arrange child elements in a two-dimensional
                grid system with rows and columns. It provides powerful control over item positioning,
                sizing, and alignment, making it ideal for complex layouts, forms, and dashboards.

.. _gridbox_params:

Parameters
==========

    **columns** (int or str): Number of columns or explicit column definition.

        * int: Number of equal-width columns (e.g., ``3``)
        * str: CSS grid-template-columns value (e.g., ``'1fr 2fr 1fr'``, ``'200px 1fr 2fr'``)
        * If not specified, uses auto-placement

    **align_content** (str): Aligns the grid within the container when there's extra space.

        * ``'start'``: Grid aligned to start
        * ``'end'``: Grid aligned to end
        * ``'center'``: Grid centered
        * ``'stretch'``: Grid stretches to fill (default)
        * ``'space-between'``: Space distributed between rows
        * ``'space-around'``: Space around each row
        * ``'space-evenly'``: Equal space between all rows

    **justify_content** (str): Aligns the grid horizontally within the container.

        * ``'start'``: Grid aligned to start
        * ``'end'``: Grid aligned to end
        * ``'center'``: Grid centered
        * ``'stretch'``: Grid stretches to fill (default)
        * ``'space-between'``: Space distributed between columns
        * ``'space-around'``: Space around each column
        * ``'space-evenly'``: Equal space between all columns

    **align_items** (str): Aligns items vertically within their grid cell.

        * ``'start'``: Items aligned to cell start
        * ``'end'``: Items aligned to cell end
        * ``'center'``: Items centered in cell
        * ``'stretch'``: Items stretch to fill cell (default)

    **justify_items** (str): Aligns items horizontally within their grid cell.

        * ``'start'``: Items aligned to cell start
        * ``'end'``: Items aligned to cell end
        * ``'center'``: Items centered in cell
        * ``'stretch'``: Items stretch to fill cell (default)

    **table** (str): Optional table name for integration with Genro data handling. Defaults to page.maintable if not specified.

    ****kwargs**: Additional attributes:

        * **gap** (str): Spacing between grid items (e.g., ``'10px'``, ``'1em'``)
        * **column_gap** (str): Horizontal spacing between columns
        * **row_gap** (str): Vertical spacing between rows
        * **item_height** (str): Default height for grid items
        * **item_border** (str): Border applied to all items
        * **item_side** (str): Label position for labledBox items (``'top'``, ``'left'``, etc.)

.. _gridbox_item_attrs:

Grid Item Attributes
====================

    Child elements can use these attributes for positioning and spanning:

    **colspan** (int): Number of columns the item spans

    **rowspan** (int): Number of rows the item spans

    **Example**::

        grid = pane.gridbox(columns=3)
        grid.div('Normal item')
        grid.div('Wide item', colspan=2)  # Spans 2 columns
        grid.div('Tall item', rowspan=2)  # Spans 2 rows

.. _gridbox_examples:

Examples
========

.. _gridbox_ex_basic:

Basic Grid Layout
-----------------

This example demonstrates a simple gridbox with dynamic column count.

    * **Code**::

        def test_0_basic(self, pane):
            """Basic gridbox with equal columns"""
            # Simple 3-column grid
            grid = pane.gridbox(columns=3, gap='10px',
                              border='1px solid silver',
                              padding='5px')

            # Items flow into grid automatically
            for k in range(12):
                grid.div(f'Item {k}',
                        border='1px solid red',
                        padding='5px',
                        text_align='center')

.. _gridbox_ex_spanning:

Column and Row Spanning
------------------------

This example demonstrates **colspan** and **rowspan** for creating items that span multiple cells.

    * **Code**::

        def test_1_spanning(self, pane):
            """Gridbox with colspan and rowspan"""
            bc = pane.borderContainer(height='500px', width='600px')

            # Control panel
            fb = bc.contentPane(region='top').formbuilder(cols=2)
            fb.textBox(value='^.columns', default='4', lbl='Columns')

            # Grid with dynamic columns
            fc = bc.contentPane(region='center').gridbox(
                columns='^.columns',
                column_gap='10px',
                row_gap='5px',
                item_height='100px',
                border='1px solid silver',
                padding='5px',
                item_border='1px solid red')

            # Items with different spans
            fc.div('Item 1')
            fc.div('Item 2 (colspan=2)',
                  colspan=2,
                  border='1px solid green')
            fc.div('Item 3 (rowspan=2)',
                  rowspan=2,
                  height='100%')
            fc.div('Item 4')
            fc.div('Item 5')
            fc.div('Item 6')

.. _gridbox_ex_form:

Gridbox as Form Layout
-----------------------

This example shows using gridbox as an alternative to formbuilder for flexible form layouts.

    * **Code**::

        def test_2_form(self, pane):
            """Gridbox for form layouts"""
            bc = pane.borderContainer(height='500px', width='700px')

            # Control panel
            fb = bc.contentPane(region='top').formbuilder(cols=2)
            fb.textBox(value='^.columns', default='3', lbl='Columns')

            # Gridbox form layout
            gb = bc.contentPane(region='center').gridbox(
                columns='^.columns',
                gap='10px',
                margin='10px')

            side = 'top'

            # Form fields
            gb.textbox(value='^.nome', lbl='Nome', lbl_side=side)
            gb.textbox(value='^.cognome', lbl='Cognome', lbl_side=side)
            gb.dateTextBox(value='^.nato_il', lbl='Nato il', lbl_side=side)

            # Email spans 2 columns
            gb.textbox(value='^.email', lbl='Email',
                      lbl_side=side, colspan=2)

            gb.radioButtonText(value='^.genere',
                             values='M:Maschi,F:Femmina,N:Neutro',
                             lbl='Genere', lbl_side=side)

            gb.checkbox(value='^.privacy',
                       label='Accetto privacy',
                       lbl='Privacy', lbl_side=side)

.. _gridbox_ex_dashboard:

Dashboard Layout
----------------

This example demonstrates creating a dashboard with different sized sections.

    * **Code**::

        def test_3_dashboard(self, pane):
            """Dashboard layout with gridbox"""
            # 3-column dashboard
            dashboard = pane.gridbox(columns=3,
                                   gap='20px',
                                   height='100%',
                                   padding='10px')

            # Stats section (spans 2 columns)
            stats = dashboard.labledBox('Statistics',
                                       colspan=2)
            stats.borderContainer().contentPane(region='center').div(
                'Stats content here',
                padding='10px')

            # Quick actions (1 column)
            actions = dashboard.labledBox('Quick Actions')
            actions.div('Action 1', padding='5px')
            actions.div('Action 2', padding='5px')

            # Recent activity (spans all 3 columns)
            activity = dashboard.labledBox('Recent Activity',
                                          colspan=3)
            activity.div('Activity feed here', padding='10px')

            # Additional cards
            dashboard.labledBox('Card 1').div('Content', padding='10px')
            dashboard.labledBox('Card 2').div('Content', padding='10px')
            dashboard.labledBox('Card 3').div('Content', padding='10px')

.. _gridbox_ex_comparison:

Explicit Column Widths
-----------------------

This example shows using explicit column width definitions with CSS syntax.

    * **Code**::

        def test_4_explicit_widths(self, pane):
            """Gridbox with explicit column widths"""
            # Grid with fixed and flexible columns
            # 200px fixed sidebar, remaining space split 1:2
            grid = pane.gridbox(columns='200px 1fr 2fr',
                              row_gap='15px',
                              column_gap='10px',
                              padding='10px')

            # Sidebar (fixed width)
            grid.div('Sidebar',
                    border='1px solid blue',
                    height='400px',
                    background='#e3f2fd')

            # Content area (1 fraction)
            grid.div('Content',
                    border='1px solid green',
                    height='400px',
                    background='#e8f5e9')

            # Main area (2 fractions - twice as wide)
            grid.div('Main Area',
                    border='1px solid red',
                    height='400px',
                    background='#ffebee')

Advanced Example: Mixed Units
------------------------------

Combining different CSS grid units for complex layouts.

    * **Code**::

        def test_5_mixed_units(self, pane):
            """Complex grid with mixed units"""
            # Columns: 50px fixed, auto-fit content, remaining space, 100px fixed
            grid = pane.gridbox(
                columns='50px auto 1fr 100px',
                gap='5px',
                padding='10px',
                height='300px')

            # Row 1
            grid.div('Icon', background='#ffcdd2', text_align='center')
            grid.div('Label', background='#f8bbd0')
            grid.div('Content area with flexible width', background='#e1bee7')
            grid.div('Action', background='#d1c4e9', text_align='center')

            # Row 2 with spanning
            grid.div('50px', background='#c5cae9')
            grid.div('Multi-column content', colspan=2, background='#bbdefb')
            grid.div('100px', background='#b3e5fc')

See Also
========

    * :ref:`flexbox` - For one-dimensional flexible layouts
    * :ref:`formbuilder` - For traditional form layouts
    * :ref:`bordercontainer` - For region-based layouts
