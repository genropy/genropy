.. _formlet:

=======
Formlet
=======

    *Last page update*: |today|

    .. note:: Formlet features:

              * **Type**: Form layout container
              * **Based on**: :ref:`gridbox` with form-specific features
              * **Common attributes**: check the :ref:`attributes_index` section

    * :ref:`formlet_def`
    * :ref:`formlet_params`
    * :ref:`formlet_vs_formbuilder`
    * :ref:`formlet_examples`:

        * :ref:`formlet_ex_basic`
        * :ref:`formlet_ex_spanning`
        * :ref:`formlet_ex_styling`
        * :ref:`formlet_ex_responsive`
        * :ref:`formlet_ex_complex`

.. _formlet_def:

Definition
==========

    .. method:: pane.formlet([columns=None, cols=None, table=None, formletCode=None, **kwargs])

                Create a formlet container for flexible form layouts.

                Formlet is a modern form layout container that combines the power of :ref:`gridbox`
                with the ease of use of :ref:`formbuilder`. It uses CSS Grid layout internally,
                providing more flexible control over form field positioning, spanning, and styling
                compared to traditional table-based formbuilder.

                **Key advantages over formbuilder:**

                * Grid-based layout instead of HTML tables
                * Easy column and row spanning with ``colspan`` and ``rowspan``
                * Responsive design with dynamic column count
                * Consistent styling with ``item_*`` parameters
                * Better control over individual field positioning

.. _formlet_params:

Parameters
==========

    **columns** or **cols** (int or str): Number of columns or explicit column definition.

        * int: Number of equal-width columns (e.g., ``2``, ``3``)
        * str: CSS grid-template-columns value (e.g., ``'1fr 2fr'``)
        * Default: 1

    **table** (str): Database table name for form fields. Defaults to page.maintable if not specified.

    **formletCode** (str): Optional identifier for the formlet instance.

    **formletclass** (str): CSS class for formlet styling. Default: ``'formlet'``

    **gap** (str): Spacing between form fields (e.g., ``'10px'``, ``'1em'``).

    **column_gap** (str): Horizontal spacing between columns.

    **row_gap** (str): Vertical spacing between rows.

    **Item Styling Parameters** - Apply to all form fields:

        * **item_side** (str): Label position for all fields (``'top'``, ``'left'``, ``'right'``, ``'bottom'``)
        * **item_border** (str): Border for all field containers
        * **item_rounded** (int): Border radius for field containers
        * **item_padding** (str): Padding for field containers
        * **item_background** (str): Background color for field containers
        * **item_box_l_background** (str): Background color for labels
        * **item_box_c_padding** (str): Padding for field content
        * **item_fld_border** (str): Border for input fields
        * **item_fld_background** (str): Background color for input fields

    **Field Attributes** - Can be set on individual fields:

        * **colspan** (int): Number of columns to span
        * **rowspan** (int): Number of rows to span
        * **lbl_side** (str): Override label position for this field

.. _formlet_vs_formbuilder:

Formlet vs Formbuilder
======================

    **Use formlet when:**

    * You need responsive layouts with changing column counts
    * You want fields to span multiple columns or rows
    * You need fine control over field positioning
    * You want modern CSS Grid-based layout

    **Use formbuilder when:**

    * You need maximum browser compatibility (old browsers)
    * You're working with legacy code
    * You need the traditional table-based layout structure

    **Syntax comparison:**

    .. code-block:: python

        # Formbuilder (traditional)
        fb = pane.formbuilder(cols=2)
        fb.textbox(value='^.name', lbl='Name')
        fb.textbox(value='^.email', lbl='Email')

        # Formlet (modern)
        fl = pane.formlet(cols=2)
        fl.textbox(value='^.name', lbl='Name')
        fl.textbox(value='^.email', lbl='Email', colspan=2)  # Can span!

.. _formlet_examples:

Examples
========

.. _formlet_ex_basic:

Basic Formlet Layout
--------------------

Simple form with two columns and standard fields.

    * **Code**::

        def test_0_basic(self, pane):
            """Basic formlet with 2 columns"""
            fl = pane.formlet(cols=2, gap='10px', margin='20px')

            fl.textbox(value='^.firstname', lbl='First Name',
                      validate_notnull=True)
            fl.textbox(value='^.lastname', lbl='Last Name',
                      validate_notnull=True)
            fl.dateTextBox(value='^.birthdate', lbl='Birth Date')
            fl.textbox(value='^.city', lbl='City')

            # Email spans both columns
            fl.textbox(value='^.email', lbl='Email',
                      colspan=2, validate_notnull=True)

            # Comments span both columns
            fl.simpleTextArea(value='^.notes', lbl='Notes',
                            colspan=2, height='80px')

.. _formlet_ex_spanning:

Column and Row Spanning
------------------------

Demonstrates using ``colspan`` and ``rowspan`` for complex layouts.

    * **Code**::

        def test_1_spanning(self, pane):
            """Formlet with colspan and rowspan"""
            bc = pane.borderContainer(height='500px', width='700px')

            # Control panel
            top = bc.contentPane(region='top')
            fb = top.formbuilder(cols=2)
            fb.numberTextBox(value='^.columns', default=3,
                           lbl='Columns', min=1, max=5)

            # Formlet with dynamic columns
            center = bc.contentPane(region='center')
            fl = center.formlet(
                cols='^.columns',
                gap='15px',
                margin='20px',
                item_border='1px solid #ddd',
                item_rounded=4)

            # Regular fields
            fl.textbox(value='^.field1', lbl='Field 1')
            fl.textbox(value='^.field2', lbl='Field 2')

            # Wide field (spans 2 columns)
            fl.textbox(value='^.field3', lbl='Wide Field',
                      colspan=2)

            # Tall field (spans 2 rows)
            fl.simpleTextArea(value='^.description',
                            lbl='Description',
                            rowspan=2, height='100%')

            fl.textbox(value='^.field4', lbl='Field 4')
            fl.textbox(value='^.field5', lbl='Field 5')

            # Full-width field
            fl.textbox(value='^.field6', lbl='Full Width',
                      colspan=3)

.. _formlet_ex_styling:

Global Styling with item_* Parameters
--------------------------------------

Shows how to apply consistent styling to all form fields.

    * **Code**::

        def test_2_styling(self, pane):
            """Formlet with global styling"""
            bc = pane.borderContainer(height='600px', width='800px')

            # Style controllers
            top = bc.contentPane(region='top')
            controllers = top.gridbox(
                columns=4, gap='10px', margin='10px',
                datapath='.style')

            controllers.filteringSelect(
                value='^.item_side',
                values='top,left,right',
                lbl='Label Position',
                default='top')

            controllers.numberTextBox(
                value='^.item_rounded',
                lbl='Rounded', default=4, min=0, max=20)

            controllers.input(
                value='^.item_box_l_background',
                lbl='Label BG',
                type='color',
                default='#f0f0f0')

            controllers.input(
                value='^.item_fld_background',
                lbl='Field BG',
                type='color',
                default='#ffffff')

            # Formlet with dynamic styling
            center = bc.contentPane(region='center')
            fl = center.formlet(
                cols=2,
                gap='15px',
                margin='20px',
                item_side='^.style.item_side',
                item_border='1px solid #ccc',
                item_rounded='^.style.item_rounded',
                item_padding='5px',
                item_box_l_background='^.style.item_box_l_background',
                item_box_c_padding='10px',
                item_fld_border='1px solid #ddd',
                item_fld_background='^.style.item_fld_background')

            fl.textbox(value='^.name', lbl='Name')
            fl.textbox(value='^.surname', lbl='Surname')
            fl.dateTextBox(value='^.birthdate', lbl='Birth Date')
            fl.textbox(value='^.city', lbl='City')
            fl.textbox(value='^.email', lbl='Email', colspan=2)
            fl.radioButtonText(
                value='^.gender',
                values='M:Male,F:Female,O:Other',
                lbl='Gender')
            fl.checkbox(value='^.newsletter',
                       label='Subscribe to newsletter',
                       lbl='Newsletter')

.. _formlet_ex_responsive:

Responsive Form Layout
----------------------

Form that adapts to different screen sizes with dynamic column count.

    * **Code**::

        def test_3_responsive(self, pane):
            """Responsive formlet layout"""
            bc = pane.borderContainer(height='600px', width='100%')

            # Viewport size controller
            top = bc.contentPane(region='top')
            fb = top.formbuilder(cols=3)
            fb.div('Simulate different screen sizes:',
                  colspan=3, font_weight='bold')
            fb.button('Mobile (1 col)',
                     action='SET .formCols = 1')
            fb.button('Tablet (2 cols)',
                     action='SET .formCols = 2')
            fb.button('Desktop (3 cols)',
                     action='SET .formCols = 3')

            # Initialize with desktop layout
            pane.dataController('SET .formCols = 3',
                              _onStart=True)

            # Responsive formlet
            center = bc.contentPane(region='center')
            fl = center.formlet(
                cols='^.formCols',
                gap='15px',
                margin='20px',
                item_side='top',
                item_border='1px solid #e0e0e0',
                item_rounded=6,
                item_padding='10px')

            # Personal info section
            fl.textbox(value='^.firstname', lbl='First Name')
            fl.textbox(value='^.lastname', lbl='Last Name')
            fl.dateTextBox(value='^.birthdate', lbl='Birth Date')

            # Contact info - email spans when multiple columns
            fl.textbox(value='^.phone', lbl='Phone')
            fl.textbox(value='^.email', lbl='Email',
                      colspan=2)

            # Address fields
            fl.textbox(value='^.address', lbl='Street Address',
                      colspan=3)
            fl.textbox(value='^.city', lbl='City')
            fl.textbox(value='^.zip', lbl='ZIP Code')
            fl.textbox(value='^.country', lbl='Country')

            # Comments - always full width
            fl.simpleTextArea(value='^.comments',
                            lbl='Comments',
                            colspan=3,
                            height='100px')

.. _formlet_ex_complex:

Complex Form with Mixed Elements
---------------------------------

Advanced example combining formlet with other containers.

    * **Code**::

        def test_4_complex(self, pane):
            """Complex form with sections"""
            form = pane.frameForm(
                frameCode='TestForm',
                datapath='.formdata',
                store='memory',
                height='600px')

            bc = form.center.borderContainer(datapath='.record')

            # Main form area
            center = bc.contentPane(region='center',
                                   overflow='auto')

            # Personal Information section
            section1 = center.div(
                margin='20px',
                border='1px solid #ddd',
                border_radius='8px',
                padding='15px',
                background='#fafafa')

            section1.div('Personal Information',
                        font_size='18px',
                        font_weight='bold',
                        margin_bottom='15px',
                        color='#333')

            fl1 = section1.formlet(
                cols=3,
                gap='12px',
                item_side='top',
                item_border='1px solid #e0e0e0',
                item_rounded=4,
                item_box_l_background='#f5f5f5')

            fl1.textbox(value='^.firstname', lbl='First Name',
                       validate_notnull=True)
            fl1.textbox(value='^.lastname', lbl='Last Name',
                       validate_notnull=True)
            fl1.dateTextBox(value='^.birthdate',
                          lbl='Birth Date')
            fl1.radioButtonText(
                value='^.gender',
                values='M:Male,F:Female,O:Other',
                lbl='Gender')
            fl1.textbox(value='^.taxcode', lbl='Tax Code',
                       colspan=2)

            # Contact Information section
            section2 = center.div(
                margin='20px',
                border='1px solid #ddd',
                border_radius='8px',
                padding='15px',
                background='#fafafa')

            section2.div('Contact Information',
                        font_size='18px',
                        font_weight='bold',
                        margin_bottom='15px',
                        color='#333')

            fl2 = section2.formlet(
                cols=2,
                gap='12px',
                item_side='top',
                item_border='1px solid #e0e0e0',
                item_rounded=4,
                item_box_l_background='#f5f5f5')

            fl2.textbox(value='^.email', lbl='Email',
                       validate_notnull=True,
                       colspan=2)
            fl2.textbox(value='^.phone', lbl='Phone')
            fl2.textbox(value='^.mobile', lbl='Mobile')
            fl2.textbox(value='^.address', lbl='Address',
                       colspan=2)
            fl2.textbox(value='^.city', lbl='City')
            fl2.textbox(value='^.zip', lbl='ZIP')

            # Preferences section
            section3 = center.div(
                margin='20px',
                border='1px solid #ddd',
                border_radius='8px',
                padding='15px',
                background='#fafafa')

            section3.div('Preferences',
                        font_size='18px',
                        font_weight='bold',
                        margin_bottom='15px',
                        color='#333')

            fl3 = section3.formlet(
                cols=1,
                gap='12px',
                item_side='top',
                item_border='1px solid #e0e0e0',
                item_rounded=4)

            fl3.checkbox(value='^.newsletter',
                        label='Subscribe to newsletter',
                        lbl='Newsletter')
            fl3.checkbox(value='^.privacy',
                        label='I accept privacy policy',
                        lbl='Privacy')
            fl3.simpleTextArea(value='^.notes',
                             lbl='Notes',
                             height='80px')

            # Form buttons
            bar = form.bottom.slotBar('*,save,cancel,5')
            bar.save.button('Save',
                          action="""
                              var data = this.form.getFormData();
                              console.log('Form data:', data.toXml());
                              alert('Form saved!');
                          """)
            bar.cancel.button('Cancel',
                            action='this.form.abort();')

            # Initialize form with new record
            pane.dataController(
                'frm.newrecord();',
                frm=form.js_form,
                _onStart=True)

See Also
========

    * :ref:`formbuilder` - Traditional table-based form layout
    * :ref:`gridbox` - Underlying grid container
    * :ref:`field` - Field widget for forms
    * :ref:`frameform` - Form controller with data management
