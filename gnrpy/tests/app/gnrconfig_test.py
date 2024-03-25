"""
Tests for gnr.app.gnrconfig package
"""
import pytest
import gnr.app.gnrconfig as gnrc
from common import BaseGnrAppTest

class TestGnrConfig(BaseGnrAppTest):
    """
    unit tests for gnr.app.gnrconfig module
    """
    def test_gnrconfigpath(self):
        """
        Test gnrConfigPath function
        """
        r = gnrc.gnrConfigPath()
        assert r == self.conf_dir

    def test_getgnrconfig(self):
        """
        Test getGnrConfig function
        """
        gnrc.getGnrConfig()

        # ask for a non existing path
        with pytest.raises(Exception) as excinfo:
            gnrc.getGnrConfig("/k3ipiojfij3ojesjkhflsij3")
        assert "Missing" in str(excinfo)

        # set enviroment
        gnrc.getGnrConfig(set_environment=True)

    def test_getgenroroot(self):
        """
        Test for getGenroRoot function
        """
        r = gnrc.getGenroRoot()
        assert r == self.test_genro_root

    def test_configstruct(self):
        """
        test for gnrconfig.ConfigStruct class
        """
        gnrc.ConfigStruct()

    def test_rmsoptions(self):
        """
        Test for getRmsOptions function
        """
        b = gnrc.getRmsOptions()
        assert b is None
        gnrc.setRmsOptions(a=1)
        b = gnrc.getRmsOptions()
        assert b is not None
        assert 'a' in b
