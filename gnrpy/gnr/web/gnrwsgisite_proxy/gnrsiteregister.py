#-*- coding: utf-8 -*-
# Backward-compatibility shim. The actual implementation lives in
# gnr.web.daemon.siteregister_client

from gnr.web.daemon.siteregister_client import (  # noqa: F401
    RemoteStoreBag,
    SiteRegisterClient,
    ServerStore,
    RegisterResolver,
    GnrDaemonLocked,
)
from gnr.web.daemon.siteregister import (  # noqa: F401
    GnrDaemonException,
    DEFAULT_PAGE_MAX_AGE,
)
