import glob
import os

import pytest
import gnr.app.gnrlocalization as gl
from gnr.core.gnrbag import Bag
from gnr.core.gnrconfig import getGenroRoot
from gnr.core.gnrstring import flatten
from gnr.sql.gnrsql_exceptions import GnrSqlMissingTable
from common import BaseGnrAppTest

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


        tr = al.translate("goober", "en")

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

    def test_marker_inside_T_is_collected_under_the_runtime_key(self):
        """
        ``_T('!!Toggle')`` and a bare ``'!!Toggle'`` must land on the same
        lockey the runtime asks for. The scanner used to keep the marker inside
        the key of the ``_T(...)`` form (``en__toggle``, base ``!!Toggle``), so
        the entry it wrote was never found again and the caption stayed English.
        """
        for source, lockey, base in (
                ("bar._('lightbutton',{tip:_T('!!Toggle')});", 'en_toggle', 'Toggle'),
                ("bar._('lightbutton',{tip:_T('Toggle')});", 'en_toggle', 'Toggle'),
                ("var defaultTip = '!!Toggle';", 'en_toggle', 'Toggle'),
                ("let title = _T('!![it]Nazione');", 'it_nazione', 'Nazione'),
                ("let title = _T('!!{custom_key}Some caption');", 'en_custom_key',
                 'Some caption')):
            m = gl.LOCREGEXP.search(source)
            assert m, source
            text = m.group('text_emb') or m.group('text') or m.group('text_func')
            key = (m.group('key_emb') or m.group('key') or m.group('key_func')
                   or flatten(text))
            lang = (m.group('lang_emb') or m.group('lang') or m.group('lang_func')
                    or 'en')
            assert text == base, source
            assert '%s_%s' % (lang, key) == lockey, source

    def test_marked_literals_in_expressions_are_localized(self):
        """
        Captions written as a default inside an expression (``_T(kw.label ||
        '!!...')``) or passed along as a plain argument reach the dictionary
        only through their ``!!`` marker: without it they never get an entry
        and the widget shows the English text on every locale.
        """
        al = gl.AppLocalizer(self.app)
        expected = {'!!Drop the file to import here':
                        'Trascina qui il file da importare',
                    '!!Press to open the file explorer':
                        'Premi per aprire la finestra di selezione',
                    '!!Fill parameters': 'Compila i parametri',
                    '!!Grouping Pars': 'Parametri di raggruppamento',
                    '!!Toggle': 'Mostra/Nascondi',
                    '!!Read Only': 'Sola lettura',
                    '!!Invalid fields': 'Campi non validi',
                    '!!Row actions': 'Azioni riga',
                    '!!Template not yet created': 'Template non ancora creato'}
        for txt, translation in expected.items():
            r = al.getTranslation(txt, 'it')
            assert r['status'] == 'OK', txt
            assert r['translation'] == translation, txt

    def test_no_marker_leaks_into_a_collected_base(self):
        """
        A ``base`` starting with ``!!`` is a caption filed under a key nobody
        ever looks up, and it is what an Italian user ends up reading when the
        fallback kicks in. The marker belongs to the source, never to the
        collected text.
        """
        genroroot = getGenroRoot()
        paths = [os.path.join(genroroot, 'localization.xml')]
        paths += glob.glob(os.path.join(genroroot, 'projects', 'gnrcore',
                                        'packages', '*', 'localization.xml'))
        polluted = []
        for path in paths:
            if not os.path.exists(path):
                continue

            def cb(node, path=path):
                base = node.attr.get('base')
                if base and base.startswith('!!'):
                    polluted.append('%s: %s' % (path, node.label))
            Bag(path).walk(cb)
        assert not polluted, polluted
