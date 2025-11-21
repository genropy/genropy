# -*- coding: utf-8 -*-
"""
Sphinx documentation formatters for RST and Markdown/MyST modes.

This module contains all the formatting logic for generating Sphinx documentation
in both RST and Markdown formats, keeping export_to_sphinx.py focused on the
export workflow.
"""

from gnr.app.gnrlocalization import AppLocalizer


class SphinxFormatter:
    """Handles format-specific rendering for Sphinx documentation export"""

    def __init__(self, editing_mode, handbook_record, doctable, page,
                 images_path, curr_pathlist=None, images_dict=None, show_last_update=False):
        """
        Initialize formatter

        Args:
            editing_mode: 'rst' or 'markdown'
            handbook_record: Current handbook record dict
            doctable: Documentation table instance
            page: Page instance for external_host
            images_path: Path for images (_static/images)
            curr_pathlist: Current path list for nested content
            images_dict: Dictionary to track image paths
            show_last_update: Whether to show last update date in footer
        """
        self.editing_mode = editing_mode
        self.handbook_record = handbook_record
        self.doctable = doctable
        self.page = page
        self.images_path = images_path
        self.curr_pathlist = curr_pathlist or []
        self.images_dict = images_dict or {}
        self.show_last_update = show_last_update

    # ========== RAW HTML FORMATTING ==========

    def format_raw_html(self, html_content):
        """Format raw HTML block according to editing mode"""
        if self.editing_mode == 'markdown':
            return self._format_raw_html_md(html_content)
        else:
            return self._format_raw_html_rst(html_content)

    def _format_raw_html_rst(self, html_content):
        """Format raw HTML block in RST syntax"""
        return f'.. raw:: html\n\n {html_content}'

    def _format_raw_html_md(self, html_content):
        """Format raw HTML block in Markdown/MyST syntax"""
        return f'```{{raw}} html\n{html_content}\n```'

    # ========== INTERNAL LINKS FORMATTING ==========

    def format_internal_link(self, title, ref):
        """Format internal cross-reference link according to editing mode"""
        if self.editing_mode == 'markdown':
            return self._format_internal_link_md(title, ref)
        else:
            return self._format_internal_link_rst(title, ref)

    def _format_internal_link_rst(self, title, ref):
        """Format internal cross-reference link in RST syntax"""
        return ' :ref:`%s<%s>` ' % (title, ref)

    def _format_internal_link_md(self, title, ref):
        """Format internal cross-reference link in Markdown syntax"""
        return f'[{title}]({ref})'

    # ========== IMAGE FORMATTING ==========

    def fix_images(self, match):
        """Fix image paths and format according to editing mode"""
        if self.editing_mode == 'markdown':
            return self._fix_images_md(match)
        else:
            return self._fix_images_rst(match)

    def _fix_images_rst(self, match):
        """Fix RST image: .. image:: url"""
        old_filepath = match.group(1)
        filename = old_filepath.split('/')[-1]
        new_filepath = '%s/%s' % (self.images_path, '/'.join(self.curr_pathlist + [filename]))
        self.images_dict[new_filepath] = old_filepath
        return ".. image:: /%s" % new_filepath

    def _fix_images_md(self, match):
        """Fix Markdown image: ![alt](url)"""
        alt_text = match.group(1)
        old_filepath = match.group(2)
        filename = old_filepath.split('/')[-1]
        new_filepath = '%s/%s' % (self.images_path, '/'.join(self.curr_pathlist + [filename]))
        self.images_dict[new_filepath] = old_filepath
        return "![%s](/%s)" % (alt_text, new_filepath)

    # ========== TOCTREE FORMATTING ==========

    def create_toc(self, elements=None, maxdepth=None, hidden=None,
                   titlesonly=None, caption=None, includehidden=None):
        """Create a toctree directive with proper formatting for the editing mode"""
        if self.editing_mode == 'markdown':
            return self._create_toc_md(elements, maxdepth, hidden, titlesonly, caption, includehidden)
        else:
            return self._create_toc_rst(elements, maxdepth, hidden, titlesonly, caption, includehidden)

    def _create_toc_rst(self, elements=None, maxdepth=None, hidden=None,
                        titlesonly=None, caption=None, includehidden=None):
        """Create RST toctree with 3-space indentation"""
        toc_options = []
        if includehidden:
            toc_options.append('   :includehidden:')
        if maxdepth:
            toc_options.append(f'   :maxdepth: {maxdepth}')
        if hidden:
            toc_options.append('   :hidden:')
        if titlesonly:
            toc_options.append('   :titlesonly:')
        if caption:
            toc_options.append(f'   :caption: {caption}')

        return '\n%s\n%s\n\n\n   %s' % (".. toctree::", '\n'.join(toc_options), '\n   '.join(elements))

    def _create_toc_md(self, elements=None, maxdepth=None, hidden=None,
                       titlesonly=None, caption=None, includehidden=None):
        """Create Markdown/MyST toctree with no indentation"""
        toc_options = []
        if includehidden:
            toc_options.append(':includehidden:')
        if maxdepth:
            toc_options.append(f':maxdepth: {maxdepth}')
        if hidden:
            toc_options.append(':hidden:')
        if titlesonly:
            toc_options.append(':titlesonly:')
        if caption:
            toc_options.append(f':caption: {caption}')

        elements_str = '\n'.join(elements) if elements else ''
        options_str = '\n'.join(toc_options) if toc_options else ''
        separator = '\n\n' if options_str else '\n'
        return f'\n```{{toctree}}\n{options_str}{separator}{elements_str}\n```'

    # ========== FILE CONTENT FORMATTING ==========

    def format_file_content(self, title, hname, tocstring, content, footer):
        """Format complete file content according to editing mode"""
        if self.editing_mode == 'markdown':
            return self._format_file_content_md(title, hname, tocstring, content, footer)
        else:
            return self._format_file_content_rst(title, hname, tocstring, content, footer)

    def _format_file_content_rst(self, title, hname, tocstring, content, footer):
        """Format file content in RST syntax"""
        reference_label = f'.. _{hname}:\n' if hname else ''
        title_line = f'{title}\n{"="*len(title)}'
        return '\n'.join([reference_label, title_line, tocstring, '\n\n', content, footer])

    def _format_file_content_md(self, title, hname, tocstring, content, footer):
        """Format file content in Markdown syntax"""
        reference_label = f'(#{hname})=\n' if hname else ''
        title_line = f'# {title}'
        return '\n'.join([reference_label, title_line, tocstring, '\n\n', content, footer])

    # ========== FOOTER FORMATTING ==========

    def create_footer(self, record, translator):
        """Create page footer with author and publish date"""
        if self.editing_mode == 'markdown':
            return self._create_footer_md(record, translator)
        else:
            return self._create_footer_rst(record, translator)

    def _create_footer_rst(self, record, translator):
        """Create RST footer with sectionauthor and publish date"""
        footer = ''
        if record['author']:
            footer = '\n.. sectionauthor:: %s\n' % (record['author'] or self.handbook_record['author'])
        if self.show_last_update:
            last_upd = translator.getTranslation('!!Publish date',
                                                language=self.handbook_record['language']).get('translation') or 'Publish date'
            date_format = '%Y-%m-%d' if self.handbook_record['language'] == 'en' else '%d-%m-%Y'
            publish_date_str = record['publish_date'].strftime(date_format) if record['publish_date'] else ''
            footer += f"""\n.. raw:: html\n\n   <p style="font-size:0.8em;">{last_upd} {publish_date_str}</p>"""
        return footer

    def _create_footer_md(self, record, translator):
        """Create Markdown footer with author and publish date as HTML"""
        footer_parts = []
        if record['author']:
            author = record['author'] or self.handbook_record['author']
            footer_parts.append(f'<p style="font-size:0.9em;"><em>Author: {author}</em></p>')
        if self.show_last_update:
            last_upd = translator.getTranslation('!!Publish date',
                                                language=self.handbook_record['language']).get('translation') or 'Publish date'
            date_format = '%Y-%m-%d' if self.handbook_record['language'] == 'en' else '%d-%m-%Y'
            publish_date_str = record['publish_date'].strftime(date_format) if record['publish_date'] else ''
            footer_parts.append(f'<p style="font-size:0.8em;">{last_upd} {publish_date_str}</p>')
        return '\n\n' + '\n'.join(footer_parts) if footer_parts else ''

    # ========== PARAMETERS & ATTACHMENTS TABLES ==========

    def append_parameters_table(self, content, doc_id):
        """Append parameters table to content in appropriate format"""
        translator = AppLocalizer(self.doctable.db.application)
        params_label = translator.getTranslation('!!Parameters',
                                                language=self.handbook_record['language']).get('translation') or 'Parameters'

        if self.editing_mode == 'markdown':
            params_table = self.doctable.dfAsHtmlTable(doc_id, language=self.handbook_record['language'])
            if params_table:
                return f'{content}\n\n<hr>\n\n**{params_label}:**\n\n{params_table}'
        else:
            params_table = self.doctable.dfAsRstTable(doc_id, language=self.handbook_record['language'])
            if params_table:
                return f'{content}\n\n.. raw:: html\n\n <hr>\n\n**{params_label}:**\n\n{params_table}'
        return content

    def append_attachments_table(self, content, doc_id):
        """Append attachments list to content in appropriate format"""
        translator = AppLocalizer(self.doctable.db.application)
        atcs_label = translator.getTranslation('!!Attachments',
                                              language=self.handbook_record['language']).get('translation') or 'Attachments'

        if self.editing_mode == 'markdown':
            atc_table = self.doctable.atcAsHtmlTable(doc_id, host=self.page.external_host)
            if atc_table:
                return f'{content}\n\n<hr>\n\n**{atcs_label}:**\n\n{atc_table}'
        else:
            atc_table = self.doctable.atcAsRstTable(doc_id, host=self.page.external_host)
            if atc_table:
                return f'{content}\n\n.. raw:: html\n\n <hr>\n\n**{atcs_label}:**\n\n{atc_table}'
        return content
