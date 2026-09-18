"""Runtime configuration regression for the standalone Bag integration."""


def test_native_site_dojo_version_is_explicit_text(tmp_path):
    from genro_bag import Bag as NativeBag

    # Instance configuration must retain the version as text for URL joining.
    # Keep this fixture independent of private development instances.
    site_config = tmp_path / "siteconfig.xml"
    site_config.write_text('<GenRoBag><dojo version="11::T"/></GenRoBag>')
    config = NativeBag(str(site_config))
    version = config["dojo?version"]
    assert version == "11"
    assert '/'.join((version, 'dojo', 'dojo.js')) == '11/dojo/dojo.js'
