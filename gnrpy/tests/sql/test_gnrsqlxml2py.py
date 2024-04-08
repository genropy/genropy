import os, os.path
import tempfile
import pytest
from gnr.sql import gnrsqlxml2py as gx
from gnr.core.gnrbag import BagException

class TestGnrSqlXml2Py():
    def test_structToPyFull(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(AttributeError):
                gx.structToPyFull(None, tmpdir)
            with tempfile.NamedTemporaryFile(delete=True) as tmpdbfile:
                with pytest.raises(BagException):
                    gx.structToPyFull(tmpdbfile.name, tmpdir)
        
