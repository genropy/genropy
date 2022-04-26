#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-


from gnr.lib.services import GnrBaseService

#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.lib.services import GnrBaseService,BaseServiceType


class ServiceType(BaseServiceType):
    def conf_ldaps(self):
        return dict(implementation='ldaps')

class LdapsService(GnrBaseService):
    def __init__(self,parent,**kwargs):
        self.parent = parent
