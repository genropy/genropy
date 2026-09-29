import os

import pytest
import gnr
import gnr.app.gnrlocalization as gl
from gnr.core.gnrbag import Bag
from gnr.core.gnrconfig import getGenroRoot
from gnr.sql.gnrsql_exceptions import GnrSqlMissingTable
from common import BaseGnrAppTest

def catalogueModules(locbag):
    modules = set()
    locbag.walk(lambda n: modules.add(n.attr['path']) if n.attr.get('path') else None)
    return modules


def test_core_roots_source_checkout():
    """In a checkout gnrjs and resources are not under the gnr package:
    every core root must fall back to the repository layout and exist."""
    packageFolder = os.path.dirname(gnr.__file__)
    if os.path.isdir(os.path.join(packageFolder, 'gnrjs')):
        pytest.skip('running from an installed distribution')
    genroRoot = getGenroRoot()
    roots = gl.coreLocalizationRoots(packageFolder)
    assert roots == [(os.path.join(genroRoot, repoPath), repoPath)
                     for repoPath, packagePath in gl.CORE_LOCALIZATION_ROOTS]
    for folder, prefix in roots:
        assert os.path.isdir(folder), folder


def test_core_roots_installed_layout(tmp_path):
    """In a distribution the roots live inside the package and are preferred."""
    for repoPath, packagePath in gl.CORE_LOCALIZATION_ROOTS:
        (tmp_path / packagePath).mkdir(parents=True, exist_ok=True)
    roots = gl.coreLocalizationRoots(str(tmp_path))
    assert roots == [(os.path.normpath(os.path.join(str(tmp_path), packagePath)), repoPath)
                     for repoPath, packagePath in gl.CORE_LOCALIZATION_ROOTS]


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

    def test_core_scan_keeps_catalogue_modules(self):
        """Scanning the core slot must find the gnrjs and resources modules
        of the shipped catalogue, keyed in the repository layout."""
        al = gl.AppLocalizer(self.app)
        core = [s for s in al.slots if s['code'] == 'core'][0]
        scanned = catalogueModules(al.scanSlot(core))
        shipped = catalogueModules(Bag(os.path.join(core['destFolder'], 'localization.xml')))
        external = {m for m in shipped if m.startswith(('gnrjs/', 'resources/'))}
        assert external
        assert external <= scanned
        assert not [m for m in scanned if m.startswith('..')]
