#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('subscription', pkey='id',
                    name_long='Subscription', name_plural='Subscriptions',caption_field='user_id')
        self.sysFields(tbl,id=False)
        tbl.column('user_id', size='22', name_long='User').relation('adm.user.id', mode='foreign_key')
        





    def generate_vapid_keypair():
        """
        Generate a new set of encoded key-pair for VAPID
        """
        import base64
        import ecdsa
        pk = ecdsa.SigningKey.generate(curve=ecdsa.NIST256p)
        vk = pk.get_verifying_key()
        return {
        'private_key': base64.urlsafe_b64encode(pk.to_string()).strip("="),
        'public_key': base64.urlsafe_b64encode("\x04" + vk.to_string()).strip("=")
        }