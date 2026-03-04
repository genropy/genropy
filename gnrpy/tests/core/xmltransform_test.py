import pytest
from io import BytesIO
from unittest.mock import MagicMock


SIMPLE_XSL = b"""<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:template match="/root">
    <html><body><p><xsl:value-of select="message"/></p></body></html>
  </xsl:template>
</xsl:stylesheet>"""

SIMPLE_XML = "<root><message>hello xmltransform</message></root>"


def make_main(xsl_bytes):
    """Build a Main instance with a mocked parent that serves the given XSL bytes."""
    from projects.gnrcore.packages.sys.resources.services.xmltransform.service import Main

    parent = MagicMock()
    storage_node = MagicMock()
    storage_node.__enter__ = MagicMock(return_value=BytesIO(xsl_bytes))
    storage_node.__exit__ = MagicMock(return_value=False)
    parent.storageNode.return_value.open.return_value = storage_node
    return Main(parent=parent, xsl_path='fake/path.xsl')


class TestXmlTransformServiceLocation:
    def test_service_type_importable_from_sys_lib(self):
        """ServiceType must be in sys/lib/services, NOT in gnrpy/gnr/lib/services."""
        from projects.gnrcore.packages.sys.lib.services.xmltransform import ServiceType
        assert ServiceType is not None

    def test_service_type_not_in_framework_lib(self):
        """Confirm the file was removed from the framework lib path."""
        import importlib.util
        import os
        framework_path = os.path.join(
            'gnrpy', 'gnr', 'lib', 'services', 'xmltransform.py'
        )
        assert not os.path.exists(framework_path), (
            "xmltransform.py still exists in gnrpy/gnr/lib/services/ — it should have been moved"
        )

    def test_service_type_has_conf_method(self):
        from projects.gnrcore.packages.sys.lib.services.xmltransform import ServiceType
        instance = ServiceType.__new__(ServiceType)
        conf = instance.conf_xmltransform()
        assert conf == {'implementation': 'xmltransform'}


class TestXmlTransformFunctionality:
    def test_xml_to_html_returns_bytes(self):
        main = make_main(SIMPLE_XSL)
        result = main.xml_to_html(SIMPLE_XML)
        assert isinstance(result, bytes)

    def test_xml_to_html_contains_expected_content(self):
        main = make_main(SIMPLE_XSL)
        result = main.xml_to_html(SIMPLE_XML)
        assert b'hello xmltransform' in result

    def test_xml_to_html_raises_without_xsl_path(self):
        from projects.gnrcore.packages.sys.resources.services.xmltransform.service import Main
        from gnr.core.gnrlang import GnrException

        parent = MagicMock()
        main = Main.__new__(Main)
        main.parent = parent
        main.xsl_path = None
        main.xsl_content = None

        with pytest.raises(GnrException):
            main.xml_to_html(SIMPLE_XML)
