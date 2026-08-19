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
        bc = pane.borderContainer(height='520px')

        top = bc.contentPane(region='top', height='60px')
        top.div('Comparison: Formbuilder vs Formlet',
               font_size='20px',
               font_weight='bold',
               margin='10px')

        center = bc.contentPane(region='center')
        comparison = center.gridbox(columns=2, gap='20px',
                                   margin='10px')

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
            gap='10px')
            #item_lbl_side='top',
            #item_border='1px solid #e0e0e0',
            #item_rounded=4) # Styling can be added as needed

        fl.textbox(value='^.fl_name', lbl='Name')
        fl.textbox(value='^.fl_surname', lbl='Surname')
        fl.dateTextBox(value='^.fl_date', lbl='Date')
        fl.textbox(value='^.fl_city', lbl='City')
        fl.textbox(value='^.fl_email', lbl='Email', colspan=2)
        fl.simpleTextArea(value='^.fl_notes', lbl='Notes',
                        colspan=2, height='60px')

        # Comparison notes
        bottom = bc.contentPane(region='bottom', height='150px')
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

    def test_6_wrap(self, pane):
        """Wrapping formlet: responsive single-strip mode (wrap=True)

        This example demonstrates the wrap=True mode: the formlet lays out as a
        wrapping flexbox instead of a fixed-columns grid. Items keep their
        intrinsic width and flow onto new rows when the container narrows —
        no horizontal scrollbar, no breakpoints to maintain.

        Use it for toolbar-like "headline" strips: a single row of
        heterogeneous controls that reads like a sentence. For classic
        multi-row record forms keep the grid mode (columns/cols): wrap loses
        the cross-row column alignment and ignores colspan/rowspan.

        Tips:
        - box_flex on a field lands on its labledBox wrapper: the notes field
          absorbs the leftover width on the one-row layout and is the first
          item to wrap when space runs out.
        - inside a borderContainer, pair wrap=True with a top region WITHOUT
          a fixed height: BorderContainer re-measures top panes at every
          layout, so the region grows when the strip wraps.

        Drag the splitter to resize the center pane and watch the strip reflow
        to fit its width — no horizontal scroll.
        """
        pane.div('Wrapping Formlet (wrap=True)',
                font_size='20px',
                font_weight='bold',
                margin='10px')

        pane.div('Drag the splitter to resize the center pane: the strip reflows '
                'onto new rows as the pane narrows — the notes field stretches on '
                'wide layouts and is the first to wrap on narrow ones. The pane '
                'resizes instead of growing a horizontal scrollbar.',
                margin='10px',
                margin_bottom='15px',
                color='#666')

        # a real resizable pane (drag the splitter) instead of a slider: the
        # center contentPane holds the strip and reflows live as dijit resizes
        # it — the same path the tmsh rule dialog exercises.
        bc = pane.borderContainer(height='200px', margin='10px',
                                 border='1px solid #ccc', border_radius='8px')
        side = bc.contentPane(region='right', width='240px', splitter=True,
                             background='#f7f7f7', padding='12px',
                             border_left='1px solid #ddd')
        side.div('◀ Drag the splitter', font_weight='bold', color='#555',
                margin_bottom='6px')
        side.div('The center pane shrinks/grows; the wrap=True strip reflows to '
                'fit its width instead of scrolling.', color='#888',
                font_size='12px')

        center = bc.contentPane(region='center', padding='12px', overflow='auto')
        fl = center.formlet(wrap=True,
                            item_lbl_side='left',
                            align_items='center')

        # one flex item holding the whole weekday cluster (wraps as a unit,
        # then internally on extreme widths)
        days = fl.div(display='flex', gap='10px', align_items='center',
                     flex_wrap='wrap')
        for day in ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'):
            days.checkbox(value='^.day_%s' % day.lower(), label=day)

        fl.filteringSelect(value='^.freq', lbl='Freq', width='10em',
                          values='w1:Every week,w2:Every 2 weeks,w3:Every 3 weeks')
        fl.dateTextBox(value='^.valid_from', lbl='Valid from', width='7em')
        fl.dateTextBox(value='^.valid_to', lbl='to', width='7em')

        # box_flex lands on the labledBox wrapper: grow on wide, wrap first
        fl.textbox(value='^.notes', lbl='Notes', width='100%',
                  box_flex='1 0 12em')
        fl.checkbox(value='^.deny', label='Deny rule', label_color='red')

    def test_7_responsive_grid(self, pane):
        """Responsive grid formlet: reduce columns below col_min_width

        This example demonstrates the col_min_width mode: the formlet becomes a
        responsive CSS grid whose columns reduce in count as the container
        narrows — as many as fit down to 1 — each column never thinner than
        col_min_width. This is the "min column width below which it reflows"
        behaviour, and uses the same CSS auto-fit/minmax trick as the
        groupletGrid min_width parameter (the formlet name is spelled out as
        col_min_width so it never shadows the element's CSS min-width style).

        Use it for uniform record forms that must stay usable on mobile:
        unlike wrap=True (heterogeneous items flowing as a sentence), here
        every field sits in an equal-width column, so the grid reads as a
        clean table at every width.

        Note: auto-fit never creates more columns than there are items. To
        cap the column count on very wide screens, either use a fixed
        columns=N grid instead, or put a max_width on the formlet.

        Drag the splitter to resize the center pane and watch the column count
        step down.
        """
        pane.div('Responsive Grid Formlet (col_min_width=)',
                font_size='20px',
                font_weight='bold',
                margin='10px')

        pane.div('Drag the splitter to resize the center pane: the column count '
                'steps down (as many as fit → 1) as the pane narrows, each column '
                'at least 14em wide. Every field keeps an equal-width column — a '
                'clean table at any size.',
                margin='10px',
                margin_bottom='15px',
                color='#666')

        # same resizable-pane setup as the wrap demo: drag the splitter and the
        # grid recomputes its column count purely in CSS (auto-fit/minmax)
        bc = pane.borderContainer(height='340px', margin='10px',
                                 border='1px solid #ccc', border_radius='8px')
        side = bc.contentPane(region='right', width='240px', splitter=True,
                             background='#f7f7f7', padding='12px',
                             border_left='1px solid #ddd')
        side.div('◀ Drag the splitter', font_weight='bold', color='#555',
                margin_bottom='6px')
        side.div('The grid reduces its column count as the center pane narrows, '
                'each column at least 14em wide.', color='#888', font_size='12px')

        center = bc.contentPane(region='center', padding='12px', overflow='auto')
        fl = center.formlet(col_min_width='14em',
                            item_lbl_side='top')

        fl.textbox(value='^.g_firstname', lbl='First Name')
        fl.textbox(value='^.g_lastname', lbl='Last Name')
        fl.dateTextBox(value='^.g_birthdate', lbl='Birth Date')
        fl.textbox(value='^.g_city', lbl='City')
        fl.textbox(value='^.g_email', lbl='Email')
        fl.textbox(value='^.g_phone', lbl='Phone')
        fl.textbox(value='^.g_taxcode', lbl='Tax Code')
        fl.textbox(value='^.g_zip', lbl='ZIP')

    def test_8_button_alignment(self, pane):
        """Buttons inside formlet: vertical alignment with labeled fields

        A button (or any widget without lbl) placed next to labeled fields
        does not get the labledBox wrapper, so it aligns to the top of its
        grid cell while the field inputs sit below their label. This test
        collects the relevant cases to verify the framework-level alignment.
        """
        pane.div('Button alignment inside formlet',
                font_size='20px', font_weight='bold', margin='10px')

        # Case A: top labels, plain style — button lands next to two textboxes
        pane.div('A. item_lbl_side="top": button should align with the inputs, not float above',
                margin='10px', color='#666')
        fl = pane.formlet(cols=3, gap='10px', margin='10px',
                          item_lbl_side='top', width='700px')
        fl.textbox(value='^.a_code', lbl='Code')
        fl.textbox(value='^.a_description', lbl='Description')
        fl.button('Check', action='alert("checked")')

        # Case B: top labels, card style (item_border) — same with styled items
        pane.div('B. Same with card-styled items (item_border / item_padding)',
                margin='10px', color='#666')
        fl = pane.formlet(cols=3, gap='10px', margin='10px',
                          item_lbl_side='top', width='700px',
                          item_border='1px solid #ddd',
                          item_rounded=6, item_padding='8px')
        fl.textbox(value='^.b_code', lbl='Code')
        fl.textbox(value='^.b_description', lbl='Description')
        fl.button('Check', action='alert("checked")')

        # Case C: left labels — button next to fields on the same row
        pane.div('C. item_lbl_side="left": button on the same row as the fields',
                margin='10px', color='#666')
        fl = pane.formlet(cols=3, gap='10px', margin='10px',
                          item_lbl_side='left', width='700px')
        fl.textbox(value='^.c_code', lbl='Code')
        fl.textbox(value='^.c_description', lbl='Description')
        fl.button('Check', action='alert("checked")')

        # Case D: checkbox with both lbl and label next to labeled fields
        pane.div('D. checkbox with lbl and label next to labeled fields',
                margin='10px', color='#666')
        fl = pane.formlet(cols=3, gap='10px', margin='10px',
                          item_lbl_side='top', width='700px')
        fl.textbox(value='^.d_code', lbl='Code')
        fl.checkbox(value='^.d_active', label='Active', lbl='Status')
        fl.button('Check', action='alert("checked")')

        # Case E: several unlabeled widgets — buttons only, must not gain
        # spurious extra height
        pane.div('E. Buttons only: no labeled siblings, no extra height expected',
                margin='10px', color='#666')
        fl = pane.formlet(cols=3, gap='10px', margin='10px',
                          item_lbl_side='top', width='700px')
        fl.button('One', action='alert(1)')
        fl.button('Two', action='alert(2)')
        fl.button('Three', action='alert(3)')

        # Case F: checkbox variants — lbl only (text moved beside the box)
        # and label only (button-like placeholder): both must align with the
        # inputs; with both lbl and label see case D (label on top, box below)
        pane.div('F. checkbox with lbl only / label only: aligned with the inputs',
                margin='10px', color='#666')
        fl = pane.formlet(cols=3, gap='10px', margin='10px',
                          item_lbl_side='top', width='700px')
        fl.textbox(value='^.f_code', lbl='Code')
        fl.checkbox(value='^.f_privacy', lbl='Privacy')
        fl.checkbox(value='^.f_active', label='Active')
