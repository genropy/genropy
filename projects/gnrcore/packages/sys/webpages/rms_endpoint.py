# -*- coding: utf-8 -*-

import logging
import re
import platform
import socket
import uuid
import json
import psutil

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag

def getSystemInfo():
    try:
        info=Bag()
        info['platform']=platform.system()
        info['platform-release']=platform.release()
        info['platform-version']=platform.version()
        info['architecture']=platform.machine()
        info['hostname']=socket.gethostname()
        info['ip-address']=socket.gethostbyname(socket.gethostname())
        info['mac-address']=':'.join(re.findall('..', '%012x' % uuid.getnode()))
        info['processor']=platform.processor()
        info['ram']=str(round(psutil.virtual_memory().total / (1024.0 **3)))
        disk_info = psutil.disk_usage('/')
        info['hdd_total'] = disk_info.total / (1024.0 **3)
        info['hdd_used'] = disk_info.used / (1024.0 **3)
        info['hdd_free'] = disk_info.free / (1024.0 **3)
        return json.dumps(info)
    except Exception as e:
        logging.exception(e)

class GnrCustomWebPage(object):
    py_requires='gnrcomponents/externalcall:NetBagRpc'



    @public_method #(tags='ext')
    def netbag_repositories(self,code=None,customer_code=None,**kwargs):
        pass



    @public_method(tags='_SYSTEM_',loglevel=1)
    def netbag_serverping(self,**kwargs):
        return Bag(message='OK')
