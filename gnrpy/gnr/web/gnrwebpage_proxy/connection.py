#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  connection.py
#
#  Created by Giovanni Porcari on 2007-03-24.
#  Copyright (c) 2007 Softwell. All rights reserved.

from gnr.core.gnrlang import getUuid
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from datetime import datetime
from gnr.web.gnrwebpage_proxy.gnrbaseproxy import GnrBaseProxy
import time
from gnr.core.gnrstring import boolean
from gnr.web import logger

CONNECTION_TIMEOUT = 3600
CONNECTION_REFRESH = 20

USER_AGENT_SNIFF = (('GnrCordova', 'GnrCordova'),
                    ('Chrome', 'Chrome'),
                    ('Safari', 'Safari'),
                    ('Firefox', 'Firefox'),
                    ('Opera', 'Opera'),
                    ('MSIE', 'InternetExplorer'))
DEVICE_AGENT_SNIFF = (('iPad','mobile:tablet'),('iPhone','mobile:phone'),
                    ('Android','mobile:phone'),('WindowsPhone','mobile:phone'),
                    ('Mac','mac:desktop'),('Win','windows:desktop'),('Linux','linux:desktop'))

class GnrWebConnection(GnrBaseProxy):
    def init(self, connection_id=None, user=None, electron_static=None,**kwargs):
        page = self.page
        self.user_agent = page.user_agent or ''
        self.browser_name = self.sniffUserAgent()
        self.user_device = self.sniffUserDevice()
        self.is_cordova = self.browser_name == "GnrCordova"
        self.ip = self.page.user_ip or '0.0.0.0'
        self.connection_name = '%s_%s' % (self.ip.replace('.', '_'), self.browser_name)
        self.secret = page.site.config['secret'] or self.page.siteName
        self.electron_static = electron_static
        self.connection_id = None
        self.user = None
        self.user_tags = None
        self.user_id = None
        self.user_name = None
        self._cookie_data = None
        self.connection_item = None
        self.avatar_extra = dict()
        if connection_id:
            self.validate_connection(connection_id=connection_id, user=user)
        elif self.cookie:
            cv = dict(self.cookie)
            self.validate_connection(connection_id=cv.get('connection_id'), user=cv.get('user'))

    @property
    def cookie(self):
        if not getattr(self,'_cookie',None):
            self._cookie = self.read_cookie()
        return self._cookie
        
    @cookie.setter
    def cookie(self,cookie):
        self._cookie=cookie

    def create(self):
        self.connection_id = getUuid()
        self.user = self.guestname
        self.register()
        self.write_cookie()
        self._log_debug('create', created_connection=True)

    def validate_page_id(self, page_id):
        if not self.connection_item:
            logger.warning(
                "Page id validation requested without connection_item | domain=%s | connection_id=%s | page_id=%s",
                getattr(self.page.site, 'currentDomain', None),
                self.connection_id,
                page_id,
            )
            return False
        pages = self.connection_item.get('pages') or self.page.site.register.pages(connection_id=self.connection_item['register_item_id'])
        exists = page_id in pages if pages else False
        if not exists:
            self._log_debug('validate_page_id.miss', page_id=page_id, available=list(pages.keys()) if isinstance(pages, dict) else pages)
            logger.warning(
                "Page id validation failed | domain=%s | connection_id=%s | user=%s | page_id=%s | available=%s",
                getattr(self.page.site, 'currentDomain', None),
                self.connection_id,
                self.user,
                page_id,
                list(pages.keys()) if isinstance(pages, dict) else pages,
            )
        return exists

    def validate_connection(self, connection_id=None, user=None):
        connection_item = self.page.site.register.connection(connection_id)
        if connection_item:
            if (connection_item['user'] == user):
                self.connection_id = connection_id
                self.user = user
                self.user_tags = connection_item['user_tags']
                self.user_id = connection_item['user_id']
                self.user_name = connection_item['user_name']
                self.avatar_extra = connection_item.get('avatar_extra')
                self.electron_static = connection_item.get('electron_static')
                self.connection_item = connection_item
                self._log_debug('validate_connection.success', connection_id=connection_id, user=user,
                                 register_item_id=connection_item.get('register_item_id'))
            else:
                logger.warning(
                    "Connection validation user mismatch | domain=%s | connection_id=%s | expected_user=%s | received_user=%s",
                    getattr(self.page.site, 'currentDomain', None),
                    connection_id,
                    connection_item.get('user'),
                    user,
                )
                self._log_debug('validate_connection.miss_user', connection_id=connection_id, user=user)
        else:
            logger.warning(
                "Connection validation failed | domain=%s | connection_id=%s | user=%s | path=%s",
                getattr(self.page.site, 'currentDomain', None),
                connection_id,
                user,
                self.page._environ.get('PATH_INFO') if hasattr(self.page, '_environ') else None,
            )
            self._log_debug('validate_connection.miss', connection_id=connection_id, user=user)

    @property
    def guestname(self):
        """TODO"""
        return 'guest_%s' % self.connection_id

    def register(self):
        return self.page.site.register.new_connection(self.connection_id, self)

    def unregister(self):
        self.page.site.register.drop_connection(self.connection_id)

    def upd_registration(self, user):
        pass

    @property
    def cookie_name(self):
        return self.page.site.currentDomainIdentifier
    
    def read_cookie(self):
        cookie = self.page.get_cookie(self.cookie_name, 'marshal', secret=self.secret)
        if cookie and self.debug_enabled:
            self._log_debug('read_cookie', cookie_present=True, cookie_keys=list(cookie.keys()))
        return cookie

    def write_cookie(self):
        expires = time.time() + CONNECTION_TIMEOUT*24
        site = self.page.site
        cookie_path = site.home_uri if site.multidomain else site.default_uri
        if site.multidomain:
            # keep the connection cookie visible on the actual entry path, even if the
            # incoming request did not include the domain slug (eg: /index instead of /<domain>/index)
            request_path = getattr(site.currentRequest, 'path', None) or ''
            cookie_prefix = cookie_path.rstrip('/') or '/'
            if request_path and not request_path.startswith(cookie_prefix):
                cookie_path = '/'
        self.cookie = self.page.newMarshalCookie(self.cookie_name, {'user': self.user,
                                                                    'connection_id': self.connection_id,
                                                                    'data': self.cookie_data,
                                                                    'locale': None}, 
                                                                    secret=self.secret)
        self.cookie.expires = expires
        self.cookie.path = cookie_path
        cookieattrs = self.page.site.config.getAttr('cookies') or {}
        self.page.add_cookie(self.cookie, **cookieattrs)
        self._log_debug('write_cookie', cookie_path=cookie_path, cookie_name=self.cookie_name,
                         cookie_attrs=list(cookieattrs.keys()), expires_at=expires)

    @property
    def loggedUser(self):
        """TODO"""
        return (self.user != self.guestname) and self.user

    @property
    def cookie_data(self):
        """TODO"""
        if self._cookie_data is None:
            if self.cookie:
                self._cookie_data = self.cookie.get('data') or {}
            else:
                self._cookie_data = {}
        return self._cookie_data


    def sniffUserAgent(self):
        user_agent = self.user_agent
        for k, v in USER_AGENT_SNIFF:
            if k in  user_agent:
                return v
        return 'unknown browser'

    def sniffUserDevice(self):
        user_agent = self.user_agent
        for k, v in DEVICE_AGENT_SNIFF:
            if k in  user_agent:
                return v
        return 'pc:desktop'

    def _get_locale(self):
        if self.cookie:
            return self.cookie.get('locale')

    def _set_locale(self, v):
        self.cookie['locale'] = v

    locale = property(_get_locale, _set_locale)

    def change_user(self, avatar=None):
        avatar_dict = avatar.as_dict() if avatar else dict()
        self.user = avatar_dict.get('user') or self.guestname
        self.user_tags = avatar_dict.get('user_tags')
        self.user_name = avatar_dict.get('user_name')
        self.user_id = avatar_dict.get('user_id')
        if avatar:
            self.avatar_extra = avatar.extra_kwargs
        self.page.site.register.change_connection_user(self.connection_id, user=self.user,
                                                       user_tags=self.user_tags, user_id=self.user_id,
                                                       user_name=self.user_name, avatar_extra=self.avatar_extra)
        self.write_cookie()
        self._log_debug('change_user', user=self.user, user_id=self.user_id, user_tags=self.user_tags)

    def rpc_logout(self):
        self.page.site.register.drop_connection(self.connection_id,cascade=True)
        self.page.site.connectionLog('close',connection_id=self.connection_id)
        self._log_debug('logout', connection_id=self.connection_id)

    @public_method
    def connected_users_bag(self, exclude=None, exclude_guest=True, max_age=600):
        users = self.page.site.register.users()
        result = Bag()
        exclude = exclude or []
        now = datetime.now()
        if isinstance(exclude, str):
            exclude = exclude.split(',')
        for user, arguments in list(users.items()):
            if user in exclude:
                continue
            row = dict()
            if exclude_guest and user.startswith('guest_') or user == self.page.user:
                continue
            _customClasses = []
            userkey = user.replace('.','_').replace('@','_')
            row['_pkey'] = userkey
            row['iconClass'] = 'greenLight'
            last_refresh_ts = arguments.get('last_refresh_ts') or arguments['start_ts']
            last_user_ts = arguments.get('last_user_ts') or arguments['start_ts']
            last_refresh_age = (now - last_refresh_ts).seconds
            last_event_age = (now - last_user_ts).seconds
            if last_refresh_age > 60:
                _customClasses.append('user_disconnected')
                row['iconClass'] = 'grayLight'
            elif last_event_age>300:
                _customClasses.append('user_away')
                row['iconClass'] = 'redLight'
            elif last_event_age > 60:
                _customClasses.append('user_idle')
                row['iconClass'] = 'yellowLight'
            row['_customClasses'] = _customClasses
            row['caption'] = arguments['user_name'] or user
            row.update(arguments)
            row.pop('datachanges', None)
            result.addItem(userkey, None, **row)
        return result

    @property
    def debug_enabled(self):
        return boolean(self.page.site.connectionDebugEnabled)

    def describe(self, include_cookie=False):
        cookie_obj = getattr(self, '_cookie', None)
        data = dict(connection_id=self.connection_id,
                    user=self.user,
                    domain=self.page.site.currentDomain,
                    cookie_name=self.cookie_name,
                    cookie_path=(cookie_obj.path if cookie_obj else None),
                    user_device=self.user_device,
                    ip=self.ip,
                    electron_static=self.electron_static,
                    base_dbstore=self.page.base_dbstore,
                    temp_dbstore=self.page.temp_dbstore,
                    aux_instance=self.page.aux_instance)
        if include_cookie and cookie_obj:
            data['cookie_payload'] = dict(cookie_obj)
        return data

    def _log_debug(self, message, **kwargs):
        if not self.debug_enabled:
            return
        payload = self.describe()
        payload.update(kwargs)
        self.page.site.log_connection_debug(message, payload)



        
