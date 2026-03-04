import os
from io import BytesIO
import pytest
from unittest.mock import MagicMock

from gnr.core.gnrlang import GnrException
from gnr.dev.packagetester import PackageTester


SIMPLE_XSL = b"""<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/root">
    <html><body><p><xsl:value-of select="message"/></p></body></html>
  </xsl:template>
</xsl:stylesheet>"""

SIMPLE_XML = "<root><message>hello xmltransform</message></root>"




class TestXmlTransform(PackageTester):
    
    def get_service(self, xsl_bytes=None):
        """Build a service instance with a mocked parent that serves the given XSL bytes."""
        parent = MagicMock()
        if xsl_bytes:
            storage_node = MagicMock()
            storage_node.__enter__ = MagicMock(return_value=BytesIO(xsl_bytes))
            storage_node.__exit__ = MagicMock(return_value=False)
            parent.storageNode.return_value.open.return_value = storage_node
            service =  self._get_base_service(service_type="xmltransform",
                                              xsl_path='fake/path.xsl')
        else:
            service =  self._get_base_service(service_type="xmltransform")
        service.parent = parent
        #service = Service(parent, xsl_path='fake/path.xsl')
        return service

        
    def test_service_type_not_in_framework_lib(self):
        """Confirm the file was removed from the framework lib path."""
        with pytest.raises(ImportError):
            from gnr.lib.services import xmltransform

    def test_xml_to_html_returns_bytes(self):
        main = self.get_service(SIMPLE_XSL)
        result = main.xml_to_html(SIMPLE_XML)
        assert isinstance(result, bytes)

    def test_xml_to_html_contains_expected_content(self):
        main = self.get_service(SIMPLE_XSL)
        result = main.xml_to_html(SIMPLE_XML)
        assert b'hello xmltransform' in result

    def test_xml_to_html_raises_without_xsl_path(self):
        main = self.get_service()
        main.xsl_path = None
        with pytest.raises(GnrException):
            main.xml_to_html(SIMPLE_XML)
