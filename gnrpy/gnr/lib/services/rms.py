
# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrmail : gnr mail controller
# Copyright (c) : 2004 - 2007 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import os

from future import standard_library
standard_library.install_aliases()

import urllib.parse
from gnr.app.gnrconfig import gnrConfigPath

from gnr.core.gnrbag import Bag,NetBag
from gnr.app.gnrapp import GnrApp
from gnr.app.gnrdeploy import PathResolver
from gnr.app.gnrconfig import getRmsOptions,setRmsOptions

class RMS(object):
    def __init__(self):
        self.options = getRmsOptions() or {}
        self.code = self.options.get('code')
        self.token = self.options.get('token')
        self.url = self.options.get('url')
        self.customer_code = self.options.get('customer_code')

    
    def __getattr__(self,attr):
        return self.options.get(attr)

    def registerPod(self):
        if self.url and not self.token:
            result =  NetBag(self.url,'register_pod',code=self.code,
                                customer_code=self.customer_code)()
            if result and result.get('client_token'):
                setRmsOptions(token=result['client_token'])
            else:
                print(result)
    

    @property
    def authenticatedUrl(self):
        sp = urllib.parse.urlsplit(self.url)
        return '%s://%s:%s@%s%s' %(sp.scheme,'gnrtoken',self.token,sp.netloc,sp.path)

    def buildRmsService(self,instancename,domain=None,customer_code=None):
        rmsfolder = os.path.join(gnrConfigPath(),'rms')
        if not os.path.isdir(rmsfolder):
            os.mkdir(rmsfolder)
        rmspath = os.path.join(rmsfolder,'{name}.xml'.format(name=instancename))
        app = GnrApp(instancename,enabled_packages=['gnrcore:sys','gnrcore:adm'])
        db = app.db
        usertbl = db.table('adm.user')
        service_tbl = db.table('sys.service')
        if not usertbl.checkDuplicate(username='DEPLOY_SERVER'):
            user_rec = usertbl.newrecord(username='DEPLOY_SERVER',md5pwd=usertbl.newPkeyValue())
            usertbl.insert(user_rec)
            htagtbl = db.table('adm.htag')
            tag_id = htagtbl.sysRecord('_SYSTEM_')['id']
            db.table('adm.user_tag').insert({'tag_id':tag_id,'user_id':user_rec['id']})
        service_record = service_tbl.record(service_name=instancename,service_type='rms',ignoreMissing=True).output('record')
        if not service_record:
            deploy_token = db.table('sys.external_token').create_token(exec_user='DEPLOY_SERVER')
            service_tbl.addService(service_type='rms',service_name=instancename,
                                                            token=deploy_token,
                                                            domain=domain)
            rmsbag = Bag()
            rmsbag.setItem('rms',None,token=deploy_token,domain=domain,instance_name=instancename,customer_code=customer_code)
            rmsbag.toXml(rmspath)
            db.commit()
        else:
            if os.path.isfile(rmspath):
                rmsbag = Bag(rmspath)
            else:
                rmsbag = Bag()
            rmsbag.setAttr('rms',domain=domain,instance_name=instancename,
                                token=service_record['parameters.token'],
                                customer_code=customer_code)
            rmsbag.toXml(rmspath)
        return rmsbag

    def ping(self):
        result =  NetBag(self.url,'ping')()
        print(result)
    
    def authping(self):
        result =  NetBag(self.authenticatedUrl,'authping')()
        print(result)

    def ping(self):
        result =  NetBag(self.url,'ping')()
        print(result)
    
    def authping(self):
        result =  NetBag(self.authenticatedUrl,'authping')()
        print(result)

    def registerInstance(self,name,customer_code=None,domain=None):
        if not (self.url and self.token):
            return
        p = PathResolver()
        instance_config = p.get_instanceconfig(name)
        site_rms = dict(instance_config.getAttr('rms')) if instance_config.getAttr('rms') else dict()
        customer_code = customer_code or site_rms.get('customer_code')
        domain = domain or  site_rms.get('domain')
        if not domain:
            return
        rmsbag = self.buildRmsService(name,domain=domain,customer_code=customer_code)
        rms_instance_attr = rmsbag.getAttr('rms')
        customer_code = rms_instance_attr.get('customer_code') or self.customer_code
        result = NetBag(self.authenticatedUrl,'register_instance',code=name,
                            domain=domain,
                            pod_token=self.token,
                            instance_token= rms_instance_attr['token'],
                            customer_code=customer_code)()
        print(result)
        return result

