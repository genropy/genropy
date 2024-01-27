import os, os.path
import pytest
import gnr.app.gnrconfig as gnrc
from common import BaseGnrTest

class TestGnrConfig(BaseGnrTest):
    def test_gnrConfigPath(self):
        r = gnrc.gnrConfigPath()
        assert r == self.local_dir

    def test_getGnrConfig(self):
        r = gnrc.getGnrConfig()

        # ask for a non existing path
        with pytest.raises(Exception) as excinfo:
            r = gnrc.getGnrConfig("/k3ipiojfij3ojesjkhflsij3")
        assert "Missing" in str(excinfo)

        # set enviroment
        r = gnrc.getGnrConfig(set_environment=True)

    def test_getGenroRoot(self):
        r = gnrc.getGenroRoot()
        assert r == self.test_genro_root
    
    def test_ConfigStruct(self):
        a = gnrc.ConfigStruct()

    def test_RmsOptions(self):
        b = gnrc.getRmsOptions()
        assert b is None
        gnrc.setRmsOptions(a=1)
        b = gnrc.getRmsOptions()
        assert b is not None
        assert 'a' in b
    
