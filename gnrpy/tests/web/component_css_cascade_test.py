"""A component's ``css_requires`` loads every same-named css file (#148).

A page-level ``css_requires`` is resolved by ``get_css_path`` across all the
resource dirs, so each package shipping a ``<name>.css`` contributes its own.
A component mixed in at runtime (a table resource View, a ``mixinComponent``)
goes through the RPC envelope instead, which used to carry only the first file.

Runs on a real GnrDummySite over the isolated ``gnrtest`` instance: the two
same-named files live in two resource dirs of its throwaway site folder.
"""

import os

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.web.gnrdummysite import GnrDummySite
from gnr.web.gnrwsgisite_proxy import gnrresourceloader


CSS_NAME = 'cascade_probe'

_COMPONENT = '''
from gnr.web.gnrbaseclasses import BaseComponent

class Probe(BaseComponent):
    css_requires = '%s'

class MissingCss(BaseComponent):
    css_requires = 'cascade_probe_missing'
''' % CSS_NAME


class TestComponentCssCascade(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        app = GnrApp(cls.test_instance_name)
        app.db.model.check(applyChanges=True)
        app.db.commit()
        cls.site = GnrDummySite(cls.test_instance_name, site_name=cls.test_instance_name)
        site_path = cls.site.site_path
        cls.css_files = []
        for folder in ('resources', '_resources'):
            dirpath = os.path.join(site_path, folder)
            os.makedirs(dirpath, exist_ok=True)
            css_path = os.path.join(dirpath, '%s.css' % CSS_NAME)
            with open(css_path, 'w') as f:
                f.write('.from_%s{color:red;}\n' % folder.strip('_'))
            cls.css_files.append(css_path)
        with open(os.path.join(site_path, '_resources', 'cascade_probe_component.py'), 'w') as f:
            f.write(_COMPONENT)

    def test_module_under_test(self):
        checkout = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        assert gnrresourceloader.__file__.startswith(checkout + os.sep)

    def test_component_css_carries_every_file(self):
        page = self.site.dummyPage
        page.mixinComponent('cascade_probe_component:Probe')
        uris = page.envelope_css_requires[CSS_NAME]
        assert len(uris) == 2
        # same files, same order as a page-level css_requires
        expected, _ = page.get_css_path(requires=[CSS_NAME])
        assert uris == [u for u in expected if CSS_NAME in u]

    def test_page_level_css_is_not_sent_again(self):
        page = self.site.dummyPage
        page.css_requires.append(CSS_NAME)
        page.mixinComponent('cascade_probe_component:Probe')
        assert CSS_NAME not in page.envelope_css_requires

    def test_missing_css_sends_nothing(self):
        page = self.site.dummyPage
        page.mixinComponent('cascade_probe_component:MissingCss')
        assert page.envelope_css_requires['cascade_probe_missing'] is None
