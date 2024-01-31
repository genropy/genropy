import pytest
import gnr.app.gnrlocalization as gl
import gnr.app.gnrapp as ga
from common import BaseGnrAppTest

class TestGnrLocalization(BaseGnrAppTest):
    app_name = 'gnr_it'
    app = ga.GnrApp(app_name, forTesting=True)

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
        with pytest.raises(AttributeError):
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
