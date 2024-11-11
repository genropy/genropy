# -*- coding: utf-8 -*-

import json

from gnr.core.gnrbag import Bag

PWA_SIZES = ['72','96','128','144','152','192','384','512']


class PWAHandler(object):
    def __init__(self, site):
        self.site = site
        self.db = self.site.db

    def manifest(self):
        sitename = self.site.site_name.title()
        result = {"short_name":sitename,
                "name": sitename,
                "description":f"PWA {sitename}",
                "display":"minimal-ui",
                "start_url":"/"}
        custom_parameters = self.configuration() or {}
        result.update(custom_parameters)
        icons = []
        for size in PWA_SIZES:
            path = self.get_image_path(size)
            if path:
                icons.append({"src":path,"type":"image/png", "sizes": f"{size}x{size}"})
        result["icons"] =  icons
        return json.dumps(result).encode()
    
    def get_image_path(self,size,ext='png'):
        image_node = self.site.storageNode(f'site:pwa/images/logo_{size}.{ext}')
        if not image_node.exists:
            image_node = self.site.storageNode(f'rsrc:pkg_{self.site.mainpackage}','pwa','images',f'logo_{size}.{ext}')
        if image_node.exists:
            return image_node.url()
        
    
    def configuration(self):
        package_conf = self.site.storageNode(f'rsrc:pkg_{self.site.mainpackage}','pwa','conf.xml')
        if not package_conf.exists:
            return
        with package_conf.open('r') as f:
            confbag = Bag(f)
        pref_customizations = Bag(self.site.getPreference('pwa',pkg=self.site.mainpackage))
        pref_customizations = {k:v for k,v in pref_customizations.items() if v is not None and k!='icons'}
        if pref_customizations:
            confbag.update(pref_customizations)
        return {k:v.strip() for k,v in confbag.items() if v is not None}
