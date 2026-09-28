"""A minimal site facade for the htmltopdf tests.

The htmltopdf services are resolved from ``resources/common/services`` through
the real ``ResourceLoader`` and write through a real local storage service, so
the tests exercise the same resolution path production uses. What they do not
need is a site instance: no register daemon, no database, no config.
"""

import os
from types import SimpleNamespace

from gnr.lib.services.storage import StorageNode, BaseLocalService
from gnr.web.gnrwsgisite_proxy.gnrresourceloader import ResourceLoader

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
COMMON_RESOURCES = os.path.join(REPO_ROOT, 'resources', 'common')


def make_pdf_site(tmp_path):
    """A site facade backed by the repository resources and a temp storage root.

    :param tmp_path: the folder the storage service is rooted at
    :returns: an object exposing what the htmltopdf services use of a site"""
    site = SimpleNamespace(
        site_path=str(tmp_path),
        site_name='htmltopdftest',
        gnr_config=None,
        debug=False,
        getStatic=lambda name: None,
        default_page=None,
        gnrapp=SimpleNamespace(packages={}, experimentalFlag=lambda group, name: False),
    )
    site.resource_loader = ResourceLoader(site)
    site.resources_dirs = [COMMON_RESOURCES]
    storage = BaseLocalService(parent=site, base_path=str(tmp_path))
    storage.service_name = 'temp'
    site.storageNode = lambda path, **kwargs: path if isinstance(path, StorageNode) \
        else StorageNode(parent=site, path=str(path).split(':', 1)[-1], service=storage)
    return site
