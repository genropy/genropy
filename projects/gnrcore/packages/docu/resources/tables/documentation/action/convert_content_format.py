# -*- coding: utf-8 -*-
import pypandoc
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
                        else:
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
