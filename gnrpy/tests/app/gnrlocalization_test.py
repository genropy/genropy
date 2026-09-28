import pathlib
import re
import xml.etree.ElementTree as ET

import pytest
import gnr.app.gnrlocalization as gl
from gnr.sql.gnrsql_exceptions import GnrSqlMissingTable
from common import BaseGnrAppTest

REPO = pathlib.Path(__file__).resolve().parents[3]
MASK = re.compile(r'\[\d+\]')

class TestGnrLocalization(BaseGnrAppTest):
    app_name = 'gnr_it'
    
    def test_gnrlocstring(self):
        """
        Tests for GnrLocString class
        """
        ls = gl.GnrLocString("goober")
        assert ls == "goober"
        ls2 = gl.GnrLocString("goober %s")
        ls2_f = ls2 % "foobar"
        assert ls2_f == "goober foobar"
        
    def test_applocalizer(self):
        """
        Tests for AppLocalizer class
        """
        al = gl.AppLocalizer(self.app)
        assert al.application is self.app

        # FIXME: apparently, the translator expect
        # an App with 'site' attribute, which usually don't
        # used also by languages
        with pytest.raises(AttributeError):
            assert al.translator is False
        with pytest.raises((AttributeError, GnrSqlMissingTable)):
            assert al.languages is False

        # forcing direct data injection to test properties
        FAKE_TRANSLATOR = "bubu"
        al._translator = FAKE_TRANSLATOR
        assert al.translator is FAKE_TRANSLATOR
        al._languages = dict(en="English", it="Italian")


        al.translate("goober", "en")

        # FIXME: won't work with a proper al.translator
        #al.autoTranslate("it")

        
        p = self.app.packages[0]['glbl']
        lbag = al.getLocalizationBag(p.packageFolder)
        assert lbag["menu"]["it_nazione?it"] == "Nazione"
        assert lbag["menu"]["it_nazione?en"] == "Nation"

        # simple txt
        r = al.getTranslation("Nazione", "en")
        assert r["status"] == "OK"
        assert r["translation"] == "Nazione"

        # GnrLocString
        r = al.getTranslation(gl.GnrLocString("it_nazione"), "en")
        assert r["status"] == "OK"
        assert r["translation"] == "Nation"

        r = al.getTranslation(gl.GnrLocString("bkasjklasjsd"), "en")
        assert r["status"] == "NOKEY"
        assert r["translation"] == "bkasjklasjsd"

        r = al.getTranslation(gl.GnrLocString("bkasjklasjsd", lockey="it"), None)
        assert r["status"] == "NOKEY"
        assert r["translation"] == "bkasjklasjsd"

        r = al.getTranslation(gl.GnrLocString("bkasjklasjsd", lockey="xk"), "it")
        assert r["status"] == "NOKEY"
        assert r["translation"] == "bkasjklasjsd"

    def test_missing_language_is_reported_as_nolang(self):
        """
        A fallback answer must stay distinguishable from a real translation:
        the client caches a translation only when the status is OK.
        """
        al = gl.AppLocalizer(self.app)
        al.localizationDict['en_records_to_delete'] = {'base': 'Records to delete'}
        al.localizationDict['en_condition_op'] = {'base': 'Condition op', 'it': 'Operatore condizione'}

        r = al.getTranslation('!!Records to delete', 'it')
        assert r['status'] == 'NOLANG'
        assert r['translation'] == 'Records to delete'

        r = al.getTranslation('!!Condition op', 'it')
        assert r['status'] == 'OK'
        assert r['translation'] == 'Operatore condizione'

        r = al.getTranslation(gl.GnrLocString('en_records_to_delete'), 'it')
        assert r['status'] == 'NOLANG'
        assert r['translation'] == 'Records to delete'

    def test_symbol_only_captions_not_translated(self):
        """
        Symbol-only captions ('=', '>=', '%', '#', whitespace, ...) all flatten
        to the same single '_' lockey: they must never resolve through whatever
        junk entry happens to occupy that '<lang>__' slot.
        """
        al = gl.AppLocalizer(self.app)
        al.localizationDict['en__'] = {'base': '%', 'it': ''}
        al.localizationDict['en_condition_op'] = {'base': 'Condition op', 'it': 'Operatore condizione'}

        for symbol in ('=', '>', '>=', '<', '<=', '!=', '#', '%'):
            r = al.getTranslation('!!%s' % symbol, 'it')
            assert r['translation'] == symbol

        # a real, non-symbol-only caption still resolves normally
        r = al.getTranslation('!!Condition op', 'it')
        assert r['translation'] == 'Operatore condizione'

        # digits survive flatten (flatten('100%') == '100_'), so this still
        # reaches the ordinary lookup instead of being short-circuited
        r = al.getTranslation('!!100%', 'it')
        assert r['translation'] == '100%'

    def test_markup_label_fragments_are_localized(self):
        """
        A drop uploader label is markup carrying embedded [!!...] fragments:
        each fragment needs its own core localization entry, otherwise the
        widget renders the marker itself instead of the translated text.
        """
        al = gl.AppLocalizer(self.app)
        label = ('<div class="atc_galleryDropArea">'
                 '<div>[!!Drop document here]</div>'
                 '<div>[!!or double click to upload]</div></div>')
        r = al.getTranslation(label, 'it')
        assert r['status'] == 'OK'
        assert r['translation'] == ('<div class="atc_galleryDropArea">'
                                    '<div>Trascina qui il documento</div>'
                                    '<div>o fai doppio click per caricare</div></div>')

    def test_attachmanager_captions_are_localized(self):
        """
        The attachment grid captions, the upload size alert and the preview
        fallback notices are marked for translation: a missing entry would
        silently fall back to English.
        """
        al = gl.AppLocalizer(self.app)
        expected = {'!!Type': 'Tipo',
                    '!!Open': 'Apri',
                    '!!DL': 'DL',
                    '!!Copy': 'Copia',
                    '!!File exceeds size limit': 'Il file supera la dimensione massima',
                    '!!Error': 'Errore',
                    '!!Open in a new tab': 'Apri in una nuova scheda',
                    '!!This video format cannot be played in the browser. Download it to watch it.':
                        'Questo formato video non può essere riprodotto nel browser. Scaricalo per vederlo.',
                    '!!This attachment links to an external site and cannot be previewed here.':
                        'Questo allegato rimanda a un sito esterno e non può essere visualizzato qui.'}
        for txt, translation in expected.items():
            r = al.getTranslation(txt, 'it')
            assert r['status'] == 'OK', txt
            assert r['translation'] == translation

    def test_same_basename_modules_keep_their_sections(self, tmp_path):
        (tmp_path / 'grouplet.js').write_text("var msg = '!!Please complete required fields';")
        (tmp_path / 'grouplet.py').write_text("caption = '!!Save draft'")
        (tmp_path / 'localization.xml').write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<GenRoBag>'
            '<grouplet path="grouplet.js" ext="js"><en_please_complete_required_fields'
            ' base="Please complete required fields" it="Completa i campi obbligatori">'
            '</en_please_complete_required_fields></grouplet>'
            '<grouplet path="grouplet.py" ext="py"><en_save_draft base="Save draft" it="Salva bozza">'
            '</en_save_draft></grouplet></GenRoBag>')
        al = gl.AppLocalizer(self.app)
        al.slots.append(dict(roots=[str(tmp_path)], destFolder=str(tmp_path),
                             code='samebasename', protected=False, language='en'))
        al.buildLocalizationDict()

        al.updateLocalizationFiles(localizationBlock='samebasename')

        lbag = al.getLocalizationBag(str(tmp_path))
        assert lbag.getNode('grouplet').attr['ext'] == 'js'
        assert lbag.getNode('grouplet_py').attr['ext'] == 'py'
        assert 'grouplet.en_please_complete_required_fields' in lbag
        assert 'grouplet_py.en_save_draft' in lbag
        assert al.translate('!!Please complete required fields', 'it') == 'Completa i campi obbligatori'
        assert al.translate('!!Save draft', 'it') == 'Salva bozza'

    def test_autotranslate_keeps_the_base_text_for_the_base_language(self):
        al = gl.AppLocalizer(self.app)
        al.localizationDict = {'en_counter_s': {'base': 'Counter %s'},
                               'en_fieldname_s_promised': {'base': '%(fieldname)s promised'}}
        al.autoTranslate('en')
        assert al.localizationDict['en_counter_s']['en'] == 'Counter %s'
        assert al.localizationDict['en_fieldname_s_promised']['en'] == '%(fieldname)s promised'


@pytest.mark.parametrize('catalog', [REPO / 'localization.xml'] + sorted((REPO / 'projects').rglob('localization.xml')),
                         ids=lambda p: str(p.relative_to(REPO)))
def test_catalog_base_language_carries_no_autotranslate_masks(catalog):
    masked = [el.tag for el in ET.parse(catalog).iter()
              if MASK.search(el.get('en', '')) and not MASK.search(el.get('base', ''))]
    assert not masked
