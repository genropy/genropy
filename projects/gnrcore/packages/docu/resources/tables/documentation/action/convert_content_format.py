# -*- coding: utf-8 -*-

from gnr.web.batch.btcbase import BaseResourceBatch

caption = 'Convert content format'
description = 'Convert documentation content between RST and Markdown'
tags = '_DEV_'

class Main(BaseResourceBatch):
    dialog_height = '350px'
    dialog_width = '550px'
    batch_prefix = 'CCF'
    batch_title = 'Convert content format'
    batch_cancellable = True
    batch_delay = 0.3
    batch_steps = 'convertContents'

    def pre_process(self):
        self.conversion_direction = self.batch_parameters.get('conversion_direction', 'rst_to_markdown')
        self.source_field = 'rst' if self.conversion_direction == 'rst_to_markdown' else 'markdown'
        self.target_field = 'markdown' if self.conversion_direction == 'rst_to_markdown' else 'rst'
        self.overwrite_existing = self.batch_parameters.get('overwrite_existing', False)

        # Check if pypandoc is available
        try:
            import pypandoc
            self.pypandoc = pypandoc
        except ImportError:
            raise Exception("pypandoc library is not installed. Please install it with: pip install pypandoc")

        # Get selected documentation records
        self.selection_pkeys = self.batch_parameters.get('_pkeys', [])
        if not self.selection_pkeys:
            raise Exception("No documentation records selected")

        self.converted_count = 0
        self.skipped_count = 0
        self.error_count = 0

    def step_convertContents(self):
        """Convert content format for all selected documentation records"""
        content_table = self.db.table('docu.content')
        doc_content_table = self.db.table('docu.documentation_content')

        for doc_pkey in self.selection_pkeys:
            self.batch_log_write(f"Processing documentation: {doc_pkey}")

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
                            self.batch_log_write(f"  - Content {content_id} ({language}): No source text, skipping")
                            self.skipped_count += 1
                            continue

                        # Skip if target already exists and overwrite is False
                        if target_text and not self.overwrite_existing:
                            self.batch_log_write(f"  - Content {content_id} ({language}): Target already exists, skipping")
                            self.skipped_count += 1
                            continue

                        # Convert content
                        if self.conversion_direction == 'rst_to_markdown':
                            converted_text = self.pypandoc.convert_text(source_text, 'markdown', format='rst')
                        else:
                            converted_text = self.pypandoc.convert_text(source_text, 'rst', format='markdown')

                        # Save converted text
                        content_rec[self.target_field] = converted_text
                        self.batch_log_write(f"  - Content {content_id} ({language}): Converted successfully")
                        self.converted_count += 1

                except Exception as e:
                    self.batch_log_write(f"  - Content {content_id} ({language}): ERROR - {str(e)}")
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
