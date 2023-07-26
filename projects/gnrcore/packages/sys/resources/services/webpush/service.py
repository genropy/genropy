# -*- coding: utf-8 -*-

import json
import urllib


from gnr.lib.services import GnrBaseService
from gnr.core.gnrdecorator import extract_kwargs,public_method
from gnr.web.gnrbaseclasses import BaseComponent

class Main(GnrBaseService):
    def __init__(self, parent=None,vapid_private=None,vapid_public=None,email=None,aud=None,**kwargs):
        self.parent = parent
        self.subscribtion_tbl = self.parent.db.table('sys.push_subscription')
        self.vapid_private = vapid_private
        self.vapid_public = vapid_public
        self.email = email
        self.aud = aud


    def subscribe(self,user_id=None, subscription_token=None):
        self.subscribtion_tbl.addNewSubscription(user_id=user_id,
                                                 subscription_token=subscription_token)

    def unsubscribe(self,user_id=None, subscription_token=None):
        self.subscribtion_tbl.removeSubscription(user_id=user_id,
                                                 subscription_token=subscription_token)
        

    def isSubscribed(self,user_id=None, subscription_token=None):
        return self.subscribtion_tbl.checkDuplicate(user_id=user_id,subscription_token=subscription_token)
        
    @extract_kwargs(condition=True)
    def notify(self,user=None,condition=None,title=None,message=None,url=None,condition_kwargs=None,logged=False,**kwargs):
        notification_claim_email = self.email
        vapid_private_key = self.vapid_private
        where = []
        if user:
            where.append('($user_id=:_user OR @user_id.username=:_user)')
        if condition:
            where.append(condition)
        subscriptions = self.subscribtion_tbl.query(where = ' AND '.join(where),_user=user,**condition_kwargs).fetch()
        for subscription_record in subscriptions:
            self._notify_subscription(subscription_record,
                                      title=title,message=message,url=url,
                                      notification_claim_email=notification_claim_email,
                                      vapid_private_key=vapid_private_key,
                                      **kwargs)
    
    def _notify_subscription(self,subscription_record=None,
                             title=None,message=None,url=None,
                             notification_claim_email=None,vapid_private_key=None,**kwargs):
        from pywebpush import webpush,WebPushException
        VAPID_CLAIMS = {"sub": f"mailto:{notification_claim_email}"}
        if kwargs:
            url = f'{url}?{urllib.parse.urlencode(kwargs)}'
        data = dict(title=title,message=message,url=url)
        try:
            return webpush(
                subscription_info=subscription_record["subscription_token"],
                data=json.dumps(data),
                vapid_private_key=vapid_private_key,
                vapid_claims=VAPID_CLAIMS)
        except WebPushException as e:
            print(e)
            status_code = e.response.status_code
            if status_code==410:
                self.subscribtion_tbl.delete(subscription_record)
                self.parent.db.commit()

    def generate_vapid_keypair(self):
        """
        Generate a new set of encoded key-pair for VAPID
        """
        import base64
        import ecdsa
        pk = ecdsa.SigningKey.generate(curve=ecdsa.NIST256p)
        vk = pk.get_verifying_key()
        private_key = base64.urlsafe_b64encode(pk.to_string()).strip(b"=")
        public_key = base64.urlsafe_b64encode(b"\x04" + vk.to_string()).strip(b"=")
        return private_key, public_key

    def activate(self,**kwargs):
        vapid_private_key,vapid_public_key = self.generate_vapid_keypair()
        self.updateServiceParameters(vapid_private=vapid_private_key.decode(),
                                     vapid_public=vapid_public_key.decode(),
                                     **kwargs)
    


class ServiceParameters(BaseComponent):
    def service_parameters(self,pane,datapath=None,**kwargs):
        service = self.getService('webpush')
        fb = pane.formbuilder(datapath=datapath)
        if service.vapid_private and service.vapid_public:
            fb.textbox(value='^.email',lbl='ClaimEmail',width='20em')
            fb.textbox(value='^.aud',lbl='Aud',width='20em')
        else:
            fb.button('Activate service').dataRpc(self.webpush_activate,
                        service_name='=#FORM.record.service_name',
                        _onResult="this.form.reload()",
                        _ask=dict(title='Activate webpush notification',
                                  fields=[
                                      dict(name='email',lbl='ClaimEmail',width='20em'),
                                      dict(name='aud',lbl='Aud',width='20em')
                                  ]))

    @public_method
    def webpush_activate(self,service_name=None,**kwargs):
        self.getService('webpush',service_name).activate(**kwargs)