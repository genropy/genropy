# -*- coding: utf-8 -*-

import json
import urllib


from gnr.lib.services import GnrBaseService
from gnr.core.gnrdecorator import extract_kwargs,public_method
from gnr.web.gnrbaseclasses import BaseComponent

class Main(GnrBaseService):
    def __init__(self, parent=None,vapid_private=None,vapid_public=None,**kwargs):
        self.parent = parent
        self.subscribtion_tbl = self.db.table('sys.push_subscription')
        self.vapid_private = vapid_private
        self.vapid_public = vapid_public


    def subscribe(self,user_id=None, subscription_token=None):
        self.subscribtion_tbl.addNewSubscription(user_id=user_id,
                                                 subscription_token=subscription_token)

    @extract_kwargs(condition=True)
    def notify(self,user=None,condition=None,title=None,message=None,url=None,condition_kwargs=None,**kwargs):
        notification_claim_email = self.parent.getPreference('.notification_claim_email',pkg='sys')
        vapid_private_key = self.parent.getPreference('.vapid_private',pkg='sys')
        where = []
        if user:
            where.append('($user_id=:user OR @user_id.username=:user)')
        if condition:
            where.append(condition)
        subscriptions = self.subscribtion_tbl.query(where = ' AND '.join(where),**condition_kwargs)
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
            print('fail', subscription_record)
            status_code = e.response.status_code
            if status_code==410:
                self.delete(subscription_record)
                self.db.commit()

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

    def activate(self):
        vapid_private_key,vapid_public_key = self.generate_vapid_keypair()
        self.updateServiceParameters(vapid_private=vapid_private_key.decode(),
                                     vapid_public=vapid_public_key.decode())
    


class ServiceParameters(BaseComponent):
    def service_parameters(self,pane,datapath=None,**kwargs):
        service = self.getService('webpush')
        fb = pane.formbuilder()
        if service.vapid_private and service.vapid_public:
            fb.textbox(value='^.email',lbl='Email')
            fb.textbox(value='^.aud',lbl='Aud')
            fb.button('De-activate service')
        else:
            fb.button('Activate service').dataRpc(self.webpush_activate,
                        service_name='=#FORM.record.service_name',
                        _onResult="this.form.reload()")

    @public_method
    def webpush_activate(self,service_name=None):
        self.getService('webpush',service_name).activate()