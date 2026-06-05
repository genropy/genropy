# -*- coding: utf-8 -*-

"""Test page for the expandbox widget and HTML details/summary elements"""

class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                 gnrcomponents/source_viewer/source_viewer:SourceViewer"""

    def test_0_basic(self, pane):
        """Basic expandbox: simple expand/collapse

        The expandbox widget wraps content in a native HTML5 <details>/<summary>
        element. Click the header to toggle visibility of the content area.
        """
        container = pane.div(width='500px', padding='10px')

        box = container.expandbox(title='Click to expand')
        box.div('This content is hidden by default. '
                'Click the header above to show or hide it.',
                padding='10px')

        container.div(height='10px')

        box2 = container.expandbox(title='This one starts open', open=True)
        box2.div('This content is visible on load because open=True.',
                 padding='10px')

    def test_1_animated(self, pane):
        """Animated expandbox: smooth CSS transitions

        Setting animate=True enables smooth height and opacity transitions
        using the CSS ::details-content pseudo-element and interpolate-size.
        Requires a modern browser (Chrome 131+, Safari 18.2+, Firefox 132+).
        """
        container = pane.div(width='500px', padding='10px')

        box = container.expandbox(title='Animated (closed)', animate=True)
        box.div('Notice the smooth transition when opening and closing. '
                'The content fades in and the height animates.',
                padding='10px')

        container.div(height='10px')

        box2 = container.expandbox(title='Animated (open)',
                                   open=True, animate=True)
        for i in range(5):
            box2.div(f'Line {i + 1}: some content to show the animation effect',
                     padding='4px')

    def test_2_with_form(self, pane):
        """Expandbox with form widgets inside

        The expandbox is designed to contain active form elements.
        All standard GenroPy widgets work inside the content area.
        """
        container = pane.div(width='600px', padding='10px')

        box = container.expandbox(title='Personal Data', open=True, animate=True)
        fb = box.formbuilder(cols=2, border_spacing='4px')
        fb.textbox(value='^.name', lbl='Name')
        fb.textbox(value='^.surname', lbl='Surname')
        fb.textbox(value='^.email', lbl='Email')
        fb.textbox(value='^.phone', lbl='Phone')

        container.div(height='10px')

        box2 = container.expandbox(title='Address', animate=True)
        fb2 = box2.formbuilder(cols=2, border_spacing='4px')
        fb2.textbox(value='^.street', lbl='Street')
        fb2.textbox(value='^.city', lbl='City')
        fb2.textbox(value='^.zip', lbl='ZIP Code')
        fb2.filteringSelect(value='^.country', lbl='Country',
                            values='IT:Italy,US:United States,UK:United Kingdom,DE:Germany')

    def test_3_reactive_binding(self, pane):
        """Reactive open/close: data-bound open, title and locked attributes

        All main attributes support GenroPy data binding. Toggle the
        checkboxes and change the title to control the expandbox
        programmatically. When locked, the toggle is disabled and the
        marker is hidden.
        """
        container = pane.div(width='500px', padding='10px')

        fb = container.formbuilder(cols=3)
        fb.checkbox(value='^.is_open', label='Open', default=True)
        fb.checkbox(value='^.is_locked', label='Locked')
        fb.textbox(value='^.box_title', lbl='Title', default='Dynamic title')

        container.div(height='10px')

        box = container.expandbox(title='^.box_title',
                                  open='^.is_open', animate=True,
                                  locked='^.is_locked')
        box.div('This box is controlled by the controls above. '
                'Enable Locked to freeze the current state.',
                padding='10px')

    def test_4_locked(self, pane):
        """Locked expandbox: disabled toggle

        Setting locked=True prevents the user from toggling the box.
        The marker is hidden and the header is not clickable.
        Useful for always-visible sections that still need a header.
        """
        container = pane.div(width='600px', padding='10px')

        box1 = container.expandbox(title='Always open (locked)',
                                   open=True, locked=True,
                                   margin_bottom='10px')
        fb1 = box1.formbuilder(cols=2, border_spacing='4px')
        fb1.textbox(value='^.lock_name', lbl='Name')
        fb1.textbox(value='^.lock_email', lbl='Email')

        box2 = container.expandbox(title='Always closed (locked)',
                                   locked=True, margin_bottom='10px')
        box2.div('You cannot see this content because the box is '
                 'locked in closed state.', padding='10px')

        container.div('Locked + minimal:', font_weight='bold',
                      margin_bottom='6px', color='var(--text-muted)')
        box3 = container.expandbox(title='Locked minimal section',
                                   open=True, locked=True, minimal=True)
        fb3 = box3.formbuilder(cols=2, border_spacing='4px')
        fb3.textbox(value='^.lm_name', lbl='Name')
        fb3.textbox(value='^.lm_city', lbl='City')

    def test_5_multiple_sections(self, pane):
        """Multiple expandboxes: accordion-like layout

        Stack multiple expandboxes to create an accordion-like UI.
        Unlike a true accordion, multiple sections can be open simultaneously.
        """
        container = pane.div(width='600px', padding='10px')
        sections = [
            ('General Settings', [
                ('Application Name', '.app_name'),
                ('Version', '.version'),
            ]),
            ('Database Configuration', [
                ('Host', '.db_host'),
                ('Port', '.db_port'),
                ('Database', '.db_name'),
            ]),
            ('Email Settings', [
                ('SMTP Server', '.smtp_server'),
                ('SMTP Port', '.smtp_port'),
                ('From Address', '.from_email'),
            ]),
            ('Advanced Options', [
                ('Debug Mode', '.debug'),
                ('Log Level', '.log_level'),
                ('Cache TTL', '.cache_ttl'),
            ]),
        ]
        for i, (title, fields) in enumerate(sections):
            box = container.expandbox(title=title, open=(i == 0),
                                      animate=True, margin_bottom='4px')
            fb = box.formbuilder(cols=1, border_spacing='4px', width='100%')
            for lbl, path in fields:
                fb.textbox(value=f'^{path}', lbl=lbl)

    def test_6_nested(self, pane):
        """Nested expandboxes: hierarchical disclosure

        Expandboxes can be nested inside each other to create a tree-like
        disclosure hierarchy. The inner boxes use minimal=True for a cleaner
        look — the outer box provides the framing, the inner ones just need
        the toggle without extra borders and backgrounds.
        """
        container = pane.div(width='600px', padding='10px')

        outer = container.expandbox(title='Project Configuration',
                                    open=True, animate=True)
        inner1 = outer.expandbox(title='Frontend', animate=True,
                                 minimal=True)
        fb1 = inner1.formbuilder(cols=2, border_spacing='4px')
        fb1.textbox(value='^.fe_framework', lbl='Framework')
        fb1.textbox(value='^.fe_port', lbl='Dev Port')

        inner2 = outer.expandbox(title='Backend', animate=True,
                                 minimal=True)
        fb2 = inner2.formbuilder(cols=2, border_spacing='4px')
        fb2.textbox(value='^.be_language', lbl='Language')
        fb2.textbox(value='^.be_port', lbl='Port')

        inner3 = outer.expandbox(title='Deployment', animate=True,
                                 minimal=True)
        fb3 = inner3.formbuilder(cols=1, border_spacing='4px')
        fb3.filteringSelect(value='^.deploy_target', lbl='Target',
                            values='dev:Development,staging:Staging,prod:Production')
        fb3.textbox(value='^.deploy_url', lbl='URL')

    def test_7_html_details(self, pane):
        """Native HTML details/summary: lightweight disclosure

        For simple text content (no active widgets), you can use the native
        HTML <details> and <summary> tags directly. No JavaScript needed.
        """
        container = pane.div(width='500px', padding='10px')

        container.div('These use raw HTML details/summary tags:',
                      font_weight='bold', margin_bottom='10px')

        det1 = container.details(margin_bottom='8px')
        det1.summary('What is GenroPy?', font_weight='bold', cursor='pointer')
        det1.div('GenroPy is a full-stack Python web framework for building '
                 'enterprise applications with rich browser-based interfaces.',
                 padding='8px', color='#555')

        det2 = container.details(margin_bottom='8px')
        det2.summary('How does data binding work?', font_weight='bold',
                     cursor='pointer')
        det2.div('GenroPy uses a reactive data model. Prefix a path with ^ '
                 'for two-way binding or = for one-way. Changes propagate '
                 'automatically through the UI.', padding='8px', color='#555')

        det3 = container.details(open=True, margin_bottom='8px')
        det3.summary('Can I nest details elements?', font_weight='bold',
                     cursor='pointer')
        inner_det = det3.details(margin='8px')
        inner_det.summary('Yes, you can!', cursor='pointer', color='#666')
        inner_det.div('Details elements nest naturally in HTML.',
                      padding='8px', color='#888')

    def test_8_minimal_variant(self, pane):
        """Minimal expandbox: clean, borderless style

        Setting minimal=True removes the border and header background,
        leaving just the text with a subtle bottom separator. Ideal for
        lightweight disclosure in content-heavy layouts.
        """
        container = pane.div(width='600px', padding='10px')

        container.div('Default (with border and header background):',
                      font_weight='bold', margin_bottom='6px',
                      color='var(--text-muted)')
        box1 = container.expandbox(title='Default style', open=True,
                                   animate=True, margin_bottom='16px')
        fb1 = box1.formbuilder(cols=2, border_spacing='4px')
        fb1.textbox(value='^.d_name', lbl='Name')
        fb1.textbox(value='^.d_email', lbl='Email')

        container.div('Minimal (no border, no background):',
                      font_weight='bold', margin_bottom='6px',
                      color='var(--text-muted)')
        box2 = container.expandbox(title='Minimal style', open=True,
                                   animate=True, minimal=True,
                                   margin_bottom='16px')
        fb2 = box2.formbuilder(cols=2, border_spacing='4px')
        fb2.textbox(value='^.m_name', lbl='Name')
        fb2.textbox(value='^.m_email', lbl='Email')

        container.div('Minimal stacked:',
                      font_weight='bold', margin_bottom='6px',
                      color='var(--text-muted)')
        for title in ['Section A', 'Section B', 'Section C']:
            box = container.expandbox(title=title, animate=True,
                                      minimal=True)
            box.div(f'Content for {title}. This variant works well '
                    'when stacking multiple sections in a clean layout.',
                    padding='8px 0', color='var(--text-secondary)')

    def test_9_styled_variants(self, pane):
        """Styled expandboxes: custom appearance

        Use standard GenroPy CSS attributes and title_* prefix
        to customize the look of expandboxes.
        """
        container = pane.div(width='600px', padding='10px')

        box1 = container.expandbox(title='Default style', open=True,
                                   animate=True, margin_bottom='10px')
        box1.div('Standard expandbox with default styling.', padding='10px')

        box2 = container.expandbox(title='Custom border', open=True,
                                   animate=True, margin_bottom='10px',
                                   border='2px solid #3498db',
                                   border_radius='8px')
        box2.div('Blue bordered expandbox with rounded corners.',
                 padding='10px')

        box3 = container.expandbox(title='Compact', open=True,
                                   animate=True, margin_bottom='10px',
                                   border='1px solid #ccc')
        box3.div('A more compact variant.', padding='4px', font_size='.85em')
