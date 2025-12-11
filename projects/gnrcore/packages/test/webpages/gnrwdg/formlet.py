# -*- coding: utf-8 -*-

"""Formlet Component Tests

This module demonstrates the formlet component, a modern grid-based form layout
that combines the power of gridbox with the ease of formbuilder.

Formlet is the responsive, mobile-friendly alternative to formbuilder,
using CSS Grid instead of HTML tables for flexible, adaptive layouts.
"""

class GnrCustomWebPage(object):
    py_requires="""gnrcomponents/testhandler:TestHandlerFull,
                    gnrcomponents/source_viewer/source_viewer:SourceViewer"""

    def test_0_basic_formlet(self, pane):
        """Basic formlet: Simple two-column form

        This example demonstrates the basic usage of formlet as a modern
        replacement for formbuilder. Formlet uses CSS Grid internally,
        making it responsive and mobile-friendly.

        Key features:
        - Two-column layout with automatic field flow
        - Fields can span multiple columns with colspan
        - Grid-based spacing with gap parameter
        - Clean, modern styling
        """
        pane.div('Basic Formlet Example',
                font_size='20px',
                font_weight='bold',
                margin='10px')

        fl = pane.formlet(
            cols=2,
            gap='15px',
            margin='20px',
            width='600px')

        fl.textbox(value='^.firstname', lbl='First Name',
                  validate_notnull=True)
        fl.textbox(value='^.lastname', lbl='Last Name',
                  validate_notnull=True)
        fl.dateTextBox(value='^.birthdate', lbl='Birth Date')
        fl.textbox(value='^.city', lbl='City')

        # Email spans both columns
        fl.textbox(value='^.email', lbl='Email',
                  colspan=2,
                  validate_notnull=True)

        # Notes span both columns with larger height
        fl.simpleTextArea(value='^.notes', lbl='Notes',
                        colspan=2,
                        height='80px')

    def test_1_spanning_fields(self, pane):
        """Formlet spanning: colspan and rowspan

        This example demonstrates the powerful spanning capabilities of formlet.
        Unlike formbuilder, formlet allows fields to span multiple columns AND rows,
        enabling complex form layouts.

        Different column counts show how the form adapts.
        """
        pane.div('Formlet with Spanning Fields',
                font_size='18px',
                font_weight='bold',
                margin='20px',
                margin_bottom='10px')

        pane.div('This example shows a 3-column formlet with fields spanning multiple columns and rows.',
                margin='20px',
                margin_bottom='15px',
                color='#666')

        # Formlet with spanning - fixed 3 columns
        fl = pane.formlet(
            cols=3,
            gap='15px',
            margin='20px',
            width='90%',
            item_border='1px solid #ddd',
            item_rounded=6,
            item_padding='8px')

        # Regular single-column fields
        fl.textbox(value='^.field1', lbl='Field 1')
        fl.textbox(value='^.field2', lbl='Field 2')
        fl.textbox(value='^.field3', lbl='Field 3')

        # Wide field spanning 2 columns
        fl.textbox(value='^.wide_field', lbl='Wide Field (colspan=2)',
                  colspan=2,
                  item_border='1px solid #4CAF50')

        # Tall field spanning 2 rows
        fl.simpleTextArea(value='^.tall_field',
                        lbl='Tall Field (rowspan=2)',
                        rowspan=2,
                        height='100%',
                        item_border='1px solid #2196F3')

        fl.textbox(value='^.field4', lbl='Field 4')
        fl.textbox(value='^.field5', lbl='Field 5')

        # Full-width field spanning all 3 columns
        fl.textbox(value='^.full_width', lbl='Full Width (colspan=3)',
                  colspan=3,
                  item_border='1px solid #FF9800')

    def test_2_styling_options(self, pane):
        """Formlet styling: Global item_* parameters

        This example demonstrates formlet's powerful styling system using item_*
        parameters. These parameters apply consistent styling to ALL form fields
        at once, making it easy to create cohesive, professional forms.

        Three different styling examples are shown side by side.
        """
        pane.div('Formlet Styling Examples',
                font_size='18px',
                font_weight='bold',
                margin='20px',
                margin_bottom='10px')

        pane.div('The item_* parameters allow you to style all fields consistently.',
                margin='20px',
                margin_bottom='15px',
                color='#666')

        # Container for three styling examples
        container = pane.gridbox(columns=3, gap='15px', margin='20px')

        # Style 1: Labels on top
        section1 = container.div(border='1px solid #ddd',
                                border_radius='8px',
                                padding='15px')
        section1.div('Style 1: Top Labels',
                    font_weight='bold',
                    margin_bottom='10px')

        fl1 = section1.formlet(
            cols=1,
            gap='12px',
            item_lbl_side='top',
            item_border='1px solid #e0e0e0',
            item_rounded=6,
            item_padding='8px',
            item_box_l_background='#f5f5f5')

        fl1.textbox(value='^.s1_name', lbl='Name')
        fl1.textbox(value='^.s1_email', lbl='Email')
        fl1.checkbox(value='^.s1_privacy', label='Accept',
                    lbl='Privacy')

        # Style 2: Labels on left
        section2 = container.div(border='1px solid #ddd',
                                border_radius='8px',
                                padding='15px')
        section2.div('Style 2: Left Labels',
                    font_weight='bold',
                    margin_bottom='10px')

        fl2 = section2.formlet(
            cols=1,
            gap='12px',
            item_lbl_side='left',
            item_border='1px solid #cce5ff',
            item_rounded=4,
            item_padding='10px',
            item_box_l_background='#e3f2fd',
            item_box_c_padding='12px')

        fl2.textbox(value='^.s2_name', lbl='Name')
        fl2.textbox(value='^.s2_email', lbl='Email')
        fl2.checkbox(value='^.s2_privacy', label='Accept',
                    lbl='Privacy')

        # Style 3: Rounded with colors
        section3 = container.div(border='1px solid #ddd',
                                border_radius='8px',
                                padding='15px')
        section3.div('Style 3: Custom Colors',
                    font_weight='bold',
                    margin_bottom='10px')

        fl3 = section3.formlet(
            cols=1,
            gap='12px',
            item_lbl_side='top',
            item_border='1px solid #d4edda',
            item_rounded=12,
            item_padding='12px',
            item_box_l_background='#d4edda',
            item_box_c_padding='8px',
            item_fld_border='1px solid #28a745',
            item_fld_background='#f8fff9')

        fl3.textbox(value='^.s3_name', lbl='Name')
        fl3.textbox(value='^.s3_email', lbl='Email')
        fl3.checkbox(value='^.s3_privacy', label='Accept',
                    lbl='Privacy')

    def test_3_responsive_mobile(self, pane):
        """Responsive formlet: Mobile-friendly layouts

        This example demonstrates why formlet is perfect for mobile applications.
        Forms can be designed with different column counts for different devices.

        This is the KEY advantage over formbuilder - formlet's grid-based layout
        makes it naturally responsive and ideal for mobile devices.
        """
        pane.div('Responsive Formlet for Different Devices',
                font_size='18px',
                font_weight='bold',
                margin='20px',
                margin_bottom='10px')

        pane.div('The same form layout adapts to mobile, tablet, and desktop screen sizes.',
                margin='20px',
                margin_bottom='15px',
                color='#666')

        # Container with 3 columns: mobile (1/3), tablet (2/3), desktop (full width below)
        container = pane.gridbox(columns=3, gap='15px', margin='20px')

        # Mobile layout (1 column) - takes 1/3 width
        mobile = container.div(border='2px solid #4CAF50',
                              border_radius='8px',
                              padding='15px',
                              colspan=1)
        mobile.div('Mobile (1 column)',
                  font_weight='bold',
                  margin_bottom='10px',
                  color='#4CAF50')

        fl_mobile = mobile.formlet(
            cols=1,
            gap='10px',
            item_lbl_side='top',
            item_border='1px solid #e0e0e0',
            item_rounded=6,
            item_padding='8px')

        fl_mobile.textbox(value='^.m_firstname', lbl='First Name')
        fl_mobile.textbox(value='^.m_lastname', lbl='Last Name')
        fl_mobile.textbox(value='^.m_email', lbl='Email')
        fl_mobile.textbox(value='^.m_phone', lbl='Phone')

        # Tablet layout (2 columns) - takes 2/3 width
        tablet = container.div(border='2px solid #2196F3',
                              border_radius='8px',
                              padding='15px',
                              colspan=2)
        tablet.div('Tablet (2 columns)',
                  font_weight='bold',
                  margin_bottom='10px',
                  color='#2196F3')

        fl_tablet = tablet.formlet(
            cols=2,
            gap='10px',
            item_lbl_side='top',
            item_border='1px solid #e0e0e0',
            item_rounded=6,
            item_padding='8px')

        fl_tablet.textbox(value='^.t_firstname', lbl='First Name')
        fl_tablet.textbox(value='^.t_lastname', lbl='Last Name')
        fl_tablet.textbox(value='^.t_email', lbl='Email', colspan=2)
        fl_tablet.textbox(value='^.t_phone', lbl='Phone', colspan=2)

        # Desktop layout (3 columns) - takes full width below
        desktop = container.div(border='2px solid #FF9800',
                               border_radius='8px',
                               padding='15px',
                               colspan=3)
        desktop.div('Desktop (3 columns)',
                   font_weight='bold',
                   margin_bottom='10px',
                   color='#FF9800')

        fl_desktop = desktop.formlet(
            cols=3,
            gap='10px',
            item_lbl_side='top',
            item_border='1px solid #e0e0e0',
            item_rounded=6,
            item_padding='8px')

        fl_desktop.textbox(value='^.d_firstname', lbl='First Name')
        fl_desktop.textbox(value='^.d_lastname', lbl='Last Name')
        fl_desktop.textbox(value='^.d_phone', lbl='Phone')
        fl_desktop.textbox(value='^.d_email', lbl='Email', colspan=3)

    def test_4_complex_form(self, pane):
        """Complex multi-section form

        This example shows a complete form using formlet with multiple sections
        and different field types.

        This demonstrates how formlet can handle complex real-world forms
        while remaining responsive and mobile-friendly.
        """
        pane.div('Complex Multi-Section Form',
                font_size='18px',
                font_weight='bold',
                margin='20px',
                margin_bottom='10px')

        pane.div('Form with multiple sections, validation, and various field types.',
                margin='20px',
                margin_bottom='15px',
                color='#666')

        # Main container
        center = pane.div(overflow='auto', padding='10px')

        # Section 1: Personal Information
        self._formSection(
            center,
            title='Personal Information',
            icon='person',
            formCols=3,
            fields=[
                ('textbox', 'firstname', 'First Name', {'validate_notnull': True}),
                ('textbox', 'lastname', 'Last Name', {'validate_notnull': True}),
                ('dateTextBox', 'birthdate', 'Date of Birth', {}),
                ('radioButtonText', 'gender', 'Gender', {
                    'values': 'M:Male,F:Female,O:Other',
                    'cols': 3
                }),
                ('textbox', 'taxcode', 'Tax Code', {'colspan': 2}),
            ])

        # Section 2: Contact Information
        self._formSection(
            center,
            title='Contact Information',
            icon='mail',
            formCols=2,
            fields=[
                ('textbox', 'email', 'Email', {
                    'validate_notnull': True,
                    'colspan': 2
                }),
                ('textbox', 'phone', 'Phone Number', {}),
                ('textbox', 'mobile', 'Mobile Number', {}),
                ('textbox', 'address', 'Street Address', {'colspan': 2}),
                ('textbox', 'city', 'City', {}),
                ('textbox', 'zip', 'ZIP Code', {}),
            ])

        # Section 3: Preferences
        self._formSection(
            center,
            title='Preferences & Privacy',
            icon='settings',
            formCols=1,
            fields=[
                ('checkbox', 'newsletter', 'Subscribe to newsletter', {}),
                ('checkbox', 'sms_notifications', 'Receive SMS notifications', {}),
                ('checkbox', 'privacy', 'I accept the privacy policy', {
                    'validate_notnull': True
                }),
                ('simpleTextArea', 'notes', 'Additional Notes', {
                    'height': '100px'
                }),
            ])

    def _formSection(self, pane, title, icon, formCols, fields):
        """Helper to create a styled form section"""
        section = pane.div(
            margin='20px',
            margin_bottom='30px',
            border='1px solid #dee2e6',
            border_radius='8px',
            padding='20px',
            background='#ffffff',
            box_shadow='0 1px 3px rgba(0,0,0,0.1)')

        # Section header with icon
        header = section.div(
            margin_bottom='20px',
            padding_bottom='10px',
            border_bottom='2px solid #007bff',
            display='flex',
            align_items='center')

        # Icon
        if icon:
            header.div(iconClass=f'iconbox {icon}',
                      margin_right='10px',
                      font_size='18px')

        # Title
        header.div(
            title,
            font_size='18px',
            font_weight='bold',
            color='#333')

        # Formlet for this section
        fl = section.formlet(
            cols=formCols,
            gap='15px',
            item_lbl_side='top',
            item_border='1px solid #e9ecef',
            item_rounded=6,
            item_padding='8px',
            item_box_l_background='#f8f9fa',
            item_box_c_padding='8px')

        # Add fields
        for field_def in fields:
            field_type, field_name, field_label, field_kwargs = field_def
            method = getattr(fl, field_type)
            if field_label:
                field_kwargs['lbl'] = field_label
            field_kwargs['value'] = f'^.{field_name}'
            method(**field_kwargs)

    def test_5_formlet_vs_formbuilder(self, pane):
        """Formlet vs Formbuilder comparison

        This example shows the same form built with both formbuilder (table-based)
        and formlet (grid-based) side by side.

        Notice how formlet offers:
        - Cleaner HTML structure
        - Better responsiveness
        - Easier field spanning
        - Modern CSS Grid layout
        """
        bc = pane.borderContainer(height='600px')

        top = bc.contentPane(region='top', height='60px')
        top.div('Comparison: Formbuilder vs Formlet',
               font_size='20px',
               font_weight='bold',
               margin='15px')

        center = bc.contentPane(region='center')
        comparison = center.gridbox(columns=2, gap='20px',
                                   margin='20px')

        # Left: Traditional Formbuilder
        fbContainer = comparison.div(
            border='1px solid #ddd',
            border_radius='8px',
            padding='15px',
            background='#f9f9f9')
        fbContainer.div('Traditional Formbuilder',
                       font_weight='bold',
                       margin_bottom='10px',
                       color='#666')

        fb = fbContainer.formbuilder(
            cols=2,
            border_spacing='10px')

        fb.textbox(value='^.fb_name', lbl='Name')
        fb.textbox(value='^.fb_surname', lbl='Surname')
        fb.dateTextBox(value='^.fb_date', lbl='Date')
        fb.textbox(value='^.fb_city', lbl='City')
        fb.textbox(value='^.fb_email', lbl='Email', colspan=2)
        fb.simpleTextArea(value='^.fb_notes', lbl='Notes',
                        colspan=2, height='60px')

        # Right: Modern Formlet
        flContainer = comparison.div(
            border='2px solid #007bff',
            border_radius='8px',
            padding='15px',
            background='#f0f8ff')
        flContainer.div('Modern Formlet (Recommended)',
                       font_weight='bold',
                       margin_bottom='10px',
                       color='#007bff')

        fl = flContainer.formlet(
            cols=2,
            gap='10px',
            item_lbl_side='top',
            item_border='1px solid #e0e0e0',
            item_rounded=4)

        fl.textbox(value='^.fl_name', lbl='Name')
        fl.textbox(value='^.fl_surname', lbl='Surname')
        fl.dateTextBox(value='^.fl_date', lbl='Date')
        fl.textbox(value='^.fl_city', lbl='City')
        fl.textbox(value='^.fl_email', lbl='Email', colspan=2)
        fl.simpleTextArea(value='^.fl_notes', lbl='Notes',
                        colspan=2, height='60px')

        # Comparison notes
        bottom = bc.contentPane(region='bottom', height='100px')
        notes = bottom.div(margin='20px',
                          padding='15px',
                          background='#fffbea',
                          border='1px solid #ffc107',
                          border_radius='4px')
        notes.div('Key Differences:', font_weight='bold',
                 margin_bottom='5px')
        notes.div('• Formbuilder: Table-based, legacy, fixed layout')
        notes.div('• Formlet: Grid-based, modern, responsive, mobile-friendly')
        notes.div('• Use formlet for new projects and mobile applications')
