"""An instance that mounts ``gnrcore:uke`` is warned that the package is going away (#1097).

The warning is logged once the application is inited, so an instance that still
mounts the package finds it in its log before the removal date.
"""
import logging

from gnr.app.gnrapp import GnrApp
from core.common import BaseGnrTest

CONFIG = """<?xml version="1.0" ?>
<GenRoBag>
  <db filename="test.db" implementation="sqlite"/>
  <packages>
%s
  </packages>
</GenRoBag>"""


class TestUkeDeprecated(BaseGnrTest):

    def _boot(self, *pkgcodes):
        declared = ['    <gnrcore_%s pkgcode="gnrcore:%s"/>' % (code, code) for code in pkgcodes]
        with open(self.test_instance_config_path, 'w', encoding='utf-8') as fp:
            fp.write(CONFIG % '\n'.join(declared))
        return GnrApp(self.test_instance_name)

    def test_mounting_uke_logs_the_removal_date(self, caplog):
        with caplog.at_level(logging.WARNING, logger='gnr.pkg'):
            app = self._boot('sys', 'adm', 'uke')
        assert 'uke' in app.packages
        assert 'gnrcore:uke is deprecated and will be removed on 2026-12-31' in caplog.text

    def test_instance_without_uke_logs_nothing(self, caplog):
        with caplog.at_level(logging.WARNING, logger='gnr.pkg'):
            self._boot('sys', 'adm')
        assert 'gnrcore:uke' not in caplog.text
