# -*- coding: utf-8 -*-

# translate_fields.py
# Created by Francesco Porcari on 2026-01-12
# Copyright (c) 2025 Softwell. All rights reserved.

from gnr.web.batch.btcaction import BaseResourceAction

caption = '!!Translate localized content'
tags = 'admin,superadmin,_DEV_'
description = '!!Localize fields'

class Main(BaseResourceAction):
    batch_prefix = 'acnt'
    batch_title = 'Translation'
    batch_cancellable = True
    batch_delay = 0.5
    batch_immediate = True

    def needs_translation(self, record, field, target_languages):
        """Check if a record needs translation for at least one language."""
        for lang in target_languages:
            loc_field = f'{field}_{lang}'
            value = record.get(loc_field)
            if value is None or value == '' or (isinstance(value, str) and value.startswith('~')):
                return True
        return False

    def do(self):
        self.localizer = self.db.application.localizer
        if not self.localizer.translator:
            raise self.tblobj.exception('business_logic', msg='No translator service configured')

        self.default_language = self.page.default_language.lower()

        fields = self.batch_parameters.get('fields')
        if not fields:
            return

        # Collect all translations: {pkey: {field_lang: translation}}
        all_translations = {}

        for field in fields.split(','):
            field_translations = self.get_field_translations(field)
            for pkey_value, lang_translations in field_translations.items():
                if pkey_value not in all_translations:
                    all_translations[pkey_value] = {}
                all_translations[pkey_value].update(lang_translations)

        # Apply all translations to records
        self.apply_translations(all_translations)

    def get_field_translations(self, field):
        """Get translations for a field, returns {pkey: {field_lang: translation}}."""
        colobj = self.tblobj.column(field)
        localized_languages = colobj.attributes.get('localized', '').split(',')
        target_languages = [lang for lang in localized_languages if lang != self.default_language]

        if not target_languages:
            return {}

        pkey = self.tblobj.pkey
        columns = [pkey, field] + [f'{field}_{lang}' for lang in target_languages]

        where_conditions = [f'${field} IS NOT NULL']
        selection_pkeys = self.get_selection_pkeys()
        if selection_pkeys:
            where_conditions.append(f'${pkey} IN :pkeys')
        else:
            # Filter records with empty or null translations
            null_conditions = [f"(${field}_{lang} IS NULL OR ${field}_{lang} = '' OR ${field}_{lang} = '~' || ${field})"
                               for lang in target_languages]
            where_conditions.append(f"({' OR '.join(null_conditions)})")

        query_kwargs = dict(
            where=' AND '.join(where_conditions),
            columns=','.join(columns),
            pkeys=selection_pkeys
        )
        if not selection_pkeys:
            query_kwargs['limit'] = 1000
        records = self.tblobj.query(**query_kwargs).fetch()

        records_to_translate = [r for r in records if self.needs_translation(r, field, target_languages)]
        if not records_to_translate:
            return {}

        return self.translate_records(field, records_to_translate, target_languages)

    def translate_records(self, field, records, target_languages):
        """Translate records using translation service, returns {pkey: {field_lang: translation}}."""
        pkey = self.tblobj.pkey
        result_translations = {}
        translator = self.localizer.translator

        for record in records:
            pkey_value = record[pkey]
            source_text = record[field]
            result_translations[pkey_value] = {}

            for lang in target_languages:
                loc_field = f'{field}_{lang}'
                current_value = record.get(loc_field)

                # Skip if already translated
                if current_value and not current_value.startswith('~'):
                    continue

                translated = translator.translate(
                    what=source_text,
                    from_language=self.default_language,
                    to_language=lang
                )
                if translated:
                    result_translations[pkey_value][loc_field] = translated

        return result_translations

    def apply_translations(self, all_translations):
        """Apply all translations to records using batchUpdate for efficiency."""
        if not all_translations:
            return
        pkeys = list(all_translations.keys())

        def update_callback(record):
            pkey_value = record[self.tblobj.pkey]
            field_translations = all_translations.get(pkey_value, {})
            for field_name, translated_text in field_translations.items():
                record[field_name] = translated_text

        self.tblobj.batchUpdate(update_callback,
                                where=f'${self.tblobj.pkey} IN :pkeys',
                                pkeys=pkeys)
        self.db.commit()

    def table_script_parameters_pane(self, pane, **kwargs):
        localized_fields = [
            f"{colobj.name}:{self.localize(colobj.attributes.get('name_long', colobj.name))}"
            for colobj in self.tblobj.columns.values()
            if colobj.attributes.get('localized') and not colobj.attributes.get('hierarchical_field_of')
        ]

        lfields = ','.join(localized_fields)
        fb = pane.formlet()
        fb.checkboxText(value='^.fields', values=lfields, lbl='!![en]Localize fields')
