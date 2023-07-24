#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gnr.core.gnrdecorator import public_method

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('push_subscription', pkey='id',
                    name_long='Subscription', name_plural='Subscriptions',caption_field='user_id')
        self.sysFields(tbl)
        tbl.column('user_id', size='22', name_long='User').relation('adm.user.id', mode='foreign_key')
        tbl.column('subscription_token',dtype='jsonb',name_long='Token')

    @public_method
    def store_new_subscription(self, subscription_token=None):
        user_id = self.db.currentPage.avatar.user_id
        self.insert(dict(user_id=user_id, subscription_token=subscription_token))
        self.db.commit()

    @public_method
    def notify_all(self, message_body=None):
        all_sub = self.query().fetch()
        for one in all_sub:
            self.notify_one(one, message_body=message_body)

    @public_method
    def notify_one(self, subscription_record, message_body=None):
        from pywebpush import webpush,WebPushException
        VAPID_CLAIMS = {
        "sub": "mailto:info@genropy.org"
        }
        vapid_private_key = self.db.application.site.getPreference('.vapid_private',pkg='sys')
        try:
            return webpush(
                subscription_info=subscription_record["subscription_token"],
                data=message_body,
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
    
    @public_method
    def get_vapid_public_key(self):
        site = self.db.application.site
        page = self.db.currentPage
        if page and site.getPreference('.notifications_enabled',pkg='sys'):
            vapid_private_key = site.getPreference('.vapid_private',pkg='sys')
            vapid_public_key = site.getPreference('.vapid_public',pkg='sys')
            if not (vapid_private_key and vapid_public_key) or type(vapid_private_key)==bytes or "b'" in vapid_private_key:
                vapid_private_key,vapid_public_key = self.generate_vapid_keypair()
                vapid_private_key = vapid_private_key.decode()
                vapid_public_key = vapid_public_key.decode()
                site.setPreference('.vapid_private', vapid_private_key,pkg='sys')
                site.setPreference('.vapid_public', vapid_public_key,pkg='sys')
            return vapid_public_key

