# -*- coding: utf-8 -*-
import pypandoc
import re
from gnr.web.batch.btcbase import BaseResourceBatch
from gnr.app import pkglog as logger

caption = '!!Convert content format'
description = 'Convert documentation content between RST and Markdown'
tags = '_DEV_'

class Main(BaseResourceBatch):
    batch_prefix = 'CCF'
    batch_title = caption
    batch_delay = 0.3
    batch_steps = 'convertContents'

    def pre_process(self):
        self.conversion_direction = self.batch_parameters.get('conversion_direction', 'rst_to_markdown')
        self.source_field = 'rst' if self.conversion_direction == 'rst_to_markdown' else 'markdown'
        self.target_field = 'markdown' if self.conversion_direction == 'rst_to_markdown' else 'rst'
        self.overwrite_existing = self.batch_parameters.get('overwrite_existing', False)

        self.converted_count = 0
        self.skipped_count = 0
        self.error_count = 0

    def fix_admonitions(self, text):
        """Convert pypandoc admonition format to MyST format.

        Converts from:
            :::: hint
            ::: title
            Hint
            :::

            Content here
            ::::

        To:
            :::{hint}
            Content here
            :::
        """
        # List of admonition types supported by MyST
        admonition_types = [
            'attention', 'caution', 'danger', 'error', 'hint',
            'important', 'note', 'seealso', 'tip', 'warning'
        ]

        for adm_type in admonition_types:
            # Pattern to match pypandoc admonition format
            # :::: TYPE\n::: title\nTITLE\n:::\n\nCONTENT\n::::
            pattern = rf'::::\s*{adm_type}\s*\n::: title\n.*?\n:::\s*\n\n(.*?)\n::::'
            replacement = rf':::{{{adm_type}}}\n\1\n:::'
            text = re.sub(pattern, replacement, text, flags=re.DOTALL)

        return text

    def fix_iframes(self, text):
        """Convert RST raw HTML iframe blocks to MyST iframe directive.

        Converts from:
            .. raw:: html

                <iframe src="URL" width="100%" height="315" ...></iframe><hr>

        To:
            :::{iframe} URL
            :width: 100%
            :::
        """
        # Pattern to match RST raw html blocks with iframe
        # Matches: .. raw:: html\n\n    <iframe src="URL" ... ></iframe>
        pattern = r'\.\.\s+raw::\s+html\s*\n\s*\n\s+<iframe\s+src="([^"]+)"[^>]*>.*?</iframe>(?:<hr>)?'

        def replace_iframe(match):
            url = match.group(1)
            # Extract width if present in the original iframe
            width_match = re.search(r'width="([^"]+)"', match.group(0))
            width = width_match.group(1) if width_match else '100%'

            return f':::{{iframe}} {url}\n:width: {width}\n:::'

        text = re.sub(pattern, replace_iframe, text, flags=re.DOTALL)
        return text

    def convert_myst_iframe_to_rst(self, text):
        """Convert MyST iframe directive to RST raw HTML.

        Converts from:
            :::{iframe} URL
            :width: 100%
            Caption text
            :::

        To:
            .. raw:: html

                <iframe src="URL" width="100%" height="315" frameborder="0" allow="autoplay; fullscreen" allowfullscreen></iframe><hr>
        """
        # Pattern to match MyST iframe blocks
        # Matches: :::{iframe} URL\n:width: WIDTH\nCAPTION\n:::
        pattern = r':::\{iframe\}\s+([^\s\n]+)(?:\s*\n:width:\s+([^\n]+))?(?:\s*\n([^\n]*))?\s*\n:::'

        def replace_myst_iframe(match):
            url = match.group(1)
            width = match.group(2) if match.group(2) else '100%'
            # caption = match.group(3) if match.group(3) else ''

            return f'.. raw:: html\n\n    <iframe src="{url}" width="{width}" height="315" frameborder="0" allow="autoplay; fullscreen" allowfullscreen></iframe><hr>'

        text = re.sub(pattern, replace_myst_iframe, text, flags=re.MULTILINE)
        return text

    def step_convertContents(self):
        """Convert content format for all selected documentation records"""
        content_table = self.db.table('docu.content')
        doc_content_table = self.db.table('docu.documentation_content')

        for doc_pkey in self.get_selection_pkeys():

            # Get all documentation_content records for this documentation
            doc_contents = doc_content_table.query(
                where='$documentation_id=:doc_id',
                doc_id=doc_pkey
            ).fetch()

            for doc_content in doc_contents:
                content_id = doc_content['content_id']
                language = doc_content['language_code']
                try:
                    with content_table.recordToUpdate(content_id) as content_rec:
                        source_text = content_rec.get(self.source_field)
                        target_text = content_rec.get(self.target_field)

                        # Skip if source is empty
                        if not source_text:
                            logger.warning(f"  - Content {content_id} ({language}): No source text, skipping")
                            self.skipped_count += 1
                            continue

                        # Skip if target already exists and overwrite is False
                        if target_text and not self.overwrite_existing:
                            logger.warning(f"  - Content {content_id} ({language}): Target already exists, skipping")
                            self.skipped_count += 1
                            continue

                        # Convert content
                        if self.conversion_direction == 'rst_to_markdown':
                            # Use pandoc options:
                            # --wrap=none: don't wrap lines
                            # --markdown-headings=atx: use # for headers
                            # Disable extensions that add attributes: -link_attributes-fenced_code_attributes-inline_code_attributes
                            converted_text = pypandoc.convert_text(
                                source_text,
                                'markdown-smart-simple_tables-multiline_tables-grid_tables-link_attributes-fenced_code_attributes-inline_code_attributes',
                                format='rst',
                                extra_args=['--wrap=none', '--markdown-headings=atx']
                            )
                            # Fix admonitions to MyST format
                            converted_text = self.fix_admonitions(converted_text)
                            # Fix iframes to MyST format
                            converted_text = self.fix_iframes(converted_text)
                        else:
                            # Convert MyST iframe to RST before pypandoc conversion
                            source_text = self.convert_myst_iframe_to_rst(source_text)
                            converted_text = pypandoc.convert_text(source_text, 'rst', format='markdown')

                        # Save converted text
                        content_rec[self.target_field] = converted_text
                        logger.debug(f"  - Content {content_id} ({language}): Converted successfully")
                        self.converted_count += 1

                except Exception as e:
                    logger.error(f"  - Content {content_id} ({language}): ERROR - {str(e)}")
                    self.error_count += 1

            self.db.commit()

    def result_handler(self):
        result_msg = f"Conversion completed: {self.converted_count} converted, {self.skipped_count} skipped, {self.error_count} errors"
        return result_msg, {}

    def table_script_parameters_pane(self, pane, **kwargs):
        fb = pane.formbuilder(cols=1, border_spacing='5px')
        fb.filteringSelect('^.conversion_direction', lbl='!![en]Conversion direction',
                          values='rst_to_markdown:RST → Markdown,markdown_to_rst:Markdown → RST',
                          default='rst_to_markdown', validate_notnull=True,
                          tooltip='!![en]Choose the conversion direction')
        fb.checkbox('^.overwrite_existing', label='!![en]Overwrite existing target field',
                   default=False,
                   tooltip='!![en]If checked, will overwrite target field even if it already contains text')
