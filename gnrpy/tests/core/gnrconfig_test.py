"""
Tests for gnr.core.gnrconfig package
"""
import os
import subprocess
import sys
import venv

import pytest
import gnr.core.gnrconfig as gnrc
from .common import BaseGnrTest

class TestGnrConfig(BaseGnrTest):
    """
    unit tests for gnr.core.gnrconfig module
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
        assert not b
        gnrc.setRmsOptions(a=1)
        b = gnrc.getRmsOptions()
        assert b is not None
        assert 'a' in b


class TestVirtualEnvDetection:
    """
    gnrConfigPath must find $VENV/etc/gnr also when the venv is not activated
    """
    def test_activated_venv(self, monkeypatch, tmp_path):
        monkeypatch.setenv('VIRTUAL_ENV', str(tmp_path))
        assert gnrc.virtualEnvPrefix() == str(tmp_path)

    def test_stdlib_venv_not_activated(self, monkeypatch, tmp_path):
        monkeypatch.delenv('VIRTUAL_ENV', raising=False)
        monkeypatch.delenv('GENRO_GNRFOLDER', raising=False)
        monkeypatch.delattr(sys, 'real_prefix', raising=False)
        monkeypatch.setattr(sys, 'prefix', str(tmp_path))
        monkeypatch.setattr(sys, 'base_prefix', '/usr')
        assert gnrc.virtualEnvPrefix() == str(tmp_path)
        assert gnrc.gnrConfigPath() == os.path.join(str(tmp_path), 'etc', 'gnr')

    def test_no_venv(self, monkeypatch):
        monkeypatch.delenv('VIRTUAL_ENV', raising=False)
        monkeypatch.delattr(sys, 'real_prefix', raising=False)
        monkeypatch.setattr(sys, 'base_prefix', sys.prefix)
        assert gnrc.virtualEnvPrefix() is None

    def test_no_virtualenv_flag(self, monkeypatch, tmp_path):
        monkeypatch.delenv('GENRO_GNRFOLDER', raising=False)
        monkeypatch.setenv('VIRTUAL_ENV', str(tmp_path))
        monkeypatch.setenv('HOME', str(tmp_path / 'home'))
        assert gnrc.gnrConfigPath(force_return=True, no_virtualenv=True) == \
            os.path.join(str(tmp_path), 'home', '.gnr')

    def test_real_venv_called_without_activation(self, tmp_path):
        venv_dir = tmp_path / 'venv'
        venv.create(str(venv_dir), with_pip=False)
        python = venv_dir / ('Scripts' if sys.platform == 'win32' else 'bin') / 'python'
        env = {k: v for k, v in os.environ.items()
               if k not in ('VIRTUAL_ENV', 'GENRO_GNRFOLDER')}
        env['PYTHONPATH'] = os.pathsep.join(p for p in sys.path if p)
        result = subprocess.run(
            [str(python), '-c', 'from gnr.core.gnrconfig import gnrConfigPath; print(gnrConfigPath())'],
            env=env, capture_output=True, text=True, check=True)
        assert os.path.realpath(result.stdout.strip()) == \
            os.path.realpath(os.path.join(str(venv_dir), 'etc', 'gnr'))
