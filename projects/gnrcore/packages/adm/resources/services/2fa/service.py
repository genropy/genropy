#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  Created by Saverio Porcari on 2013-04-06.
#  Copyright (c) 2013 Softwell. All rights reserved.


from gnr.lib.services import GnrBaseService
from gnr.web.gnrbaseclasses import BaseComponent
from base64 import b32encode
import time

class Main(GnrBaseService):
    def __init__(self, parent=None,secret=None,issuer_name=None,image=None,expiry_days=None,**kwargs):
        self.parent = parent
        self.secret = secret
        self.issuer_name = issuer_name or self.parent.gnrapp.instanceName
        self.image = image
        self.expiry_days = expiry_days or 30


    def get2faSecret(self,user_id):
        return b32encode(f'{self.secret}_{user_id}'.encode())

    def getTOTP(self,user_id):
        import pyotp
        return pyotp.totp.TOTP(self.get2faSecret(user_id))


    def verifyTOTP(self,user_id=None,otp=None):
        verifier = self.getTOTP(user_id)
        return verifier.verify(otp=otp,valid_window=1)
    
    def getPrevisioningUri(self,name=None,user_id=None,issuer_name=None,image=None):
        otp = self.getTOTP(user_id)
        return otp.provisioning_uri(name=name, 
                                  issuer_name=issuer_name or self.issuer_name,
                                  image=image or self.image)
    
    def remember2fa(self,user_id):
        page = self.parent.currentPage
        cookie = page.request.newCookie(f'{page.siteName}_{user_id}_otp', user_id)
        cookie.expires = time.time() + self.expiry_days*24
        page.add_cookie(cookie)

    def saved2fa(self,user_id):
        page = self.parent.currentPage
        result = page.get_cookie(f'{page.siteName}_{user_id}_otp', 'simple')
        return result


class ServiceParameters(BaseComponent):
    def service_parameters(self,pane,datapath=None,**kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.textbox(value='^.issuer_name',lbl='Issuer name')
        fb.textbox(value='^.secret',lbl='Secret',type='password')
        fb.textbox(value='^.image',lbl='Image')