#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('push_subscription', pkey='id',
                    name_long='Subscription', name_plural='Subscriptions',caption_field='user_id')
        self.sysFields(tbl)
        tbl.column('user_id', size='22', name_long='User').relation('adm.user.id', mode='foreign_key')
        tbl.column('subscription_token',dtype='jsonb',name_long='Token')

    def addNewSubscription(self,user_id=None, subscription_token=None):
        newsub = self.newrecord(user_id=user_id,subscription_token=subscription_token)
        self.insert(newsub)
        self.db.commit()


