#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

import requests
import json
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
from gnr.lib.services.shortener import ShortenerService
from gnr.web.gnrbaseclasses import BaseComponent



class Service(ShortenerService):
    def __init__(self, parent,api_key=None,customDomain=None,defaultAutoTrack=False, **kwargs):
        super().__init__(parent, **kwargs)
        self.api_key = api_key
        self.db = self.parent.db
        self.tblshorturl= self.db.table('sys.shorturl')
        self.customDomain = customDomain
        self.defaultAutoTrack = defaultAutoTrack
        self.headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        }

    @property
    def service_identifier(self):
        return f'shortener_{self.service_name}'
    
    def shorten(self, longUrl=None,expireHours=None,
                customDomain=None,customKey=None,autoTrack=False,
                 **kwargs):
        autoTrack = autoTrack or self.defaultAutoTrack
        customDomain = customDomain or self.customDomain
        bodypars = {"longUrl": longUrl}
        if expireHours is not None:
            bodypars['expireHours'] = expireHours
        if customDomain is not None:
            bodypars['customDomain'] = customDomain
        if customKey is not None:
            bodypars['customKey'] = customDomain
        body = json.dumps(bodypars)
        response = requests.post('https://api.aws3.link/shorten', headers=self.headers, data=body)
        result = response.json()
        shortUrl = result['shortUrl']
        metadata = result['metadata']
        if not autoTrack:
            return result
        if autoTrack:
            with self.db.tempEnv(connectionName='system',storename=self.db.rootstore):
                newrecord = self.tblshorturl.newrecord(key=metadata['key'],
                                                    domain=metadata['domain'],shorturl=shortUrl,
                                                    longurl=metadata['longUrl'],
                                                    expiration=metadata['expiration'],
                                                    service_identifier=self.service_identifier)
                self.tblshorturl.insert(newrecord)
                self.db.commit()
        return shortUrl
        
    def remove(self, key=None,customDomain=None, **kwargs):
        bodypars = {"key": key}
        customDomain = customDomain or self.customDomain
        if customDomain:
            bodypars['customDomain'] = customDomain
        body = json.dumps(bodypars)
        response = requests.post('https://api.aws3.link/remove', headers=self.headers, data=body)
        response = response.json()
        return response['body']

    def track(self, key=None,customDomain=None,autoTrack=False, **kwargs):
        bodypars = {"key": key}
        customDomain = customDomain or self.customDomain
        autoTrack = autoTrack or self.defaultAutoTrack
        if customDomain:
            bodypars['customDomain'] = customDomain
        body = json.dumps(bodypars)
        response = requests.post('https://api.aws3.link/track', headers=self.headers, data=body)
        response = response.json()
        result = response['body']
        if not autoTrack:
            return result
        tracking_kw = dict(result)
        metadata = tracking_kw.pop('metadata')
        tracking = Bag()
        tracking.fromJson(tracking_kw)
        with self.db.tempEnv(connectionName='system',storename=self.db.rootstore):
            with self.tblshorturl.recordToUpdate(service_identifier=self.service_identifier,
                                                key=key,domain=metadata['domain'],insertMissing=True) as rec:
                rec['traking'] = tracking
        return result


class ServiceParameters(BaseComponent):
    def service_parameters(self,pane,datapath=None,**kwargs):
        bc = pane.borderContainer()
        bc.contentPane(region='center')
        fb = bc.contentPane(region='top').formbuilder(datapath=datapath)
        fb.textbox(value='^.api_key',lbl='Api key',width='40em')
        fb.textbox(value='^.customDomain',lbl='Default Custom domain',width='40em')
        fb.checkbox(value='^.defaultAutoTrack',label='Default autotrack')
        fb.button('Test shorten').dataRpc(self.testShorten,
            customDomain='=.customDomain',
            service_name='=#FORM.record.service_name',
            _ask=dict(title='Get shortlink',
                        fields=[
                            dict(name='longUrl',lbl='longUrl'),
                            dict(name='expireHours',tag='NumberTextBox',lbl='expireHours'),
                            dict(name='customDomain',lbl='customDomain'),
                            dict(name='customKey',lbl='customKey')
                        ])
        ).addCallback('genro.dlg.alert(result,"testlink")')
        fb.button('Test Remove')
        fb.button('Test Track')

    @public_method
    def testShorten(self,service_name=None,longUrl=None,expireHours=None,customDomain=None,customKey=None):
        service = self.getService('shortener',service_name)
        result = service.shorten(longUrl=longUrl,expireHours=expireHours,customDomain=customDomain,customKey=customKey)
        print(x)