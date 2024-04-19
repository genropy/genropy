
import os
from datetime import datetime

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrlang import getUuid

class WebApplicationCache(object):
    def __init__(self,application=None):
        self.application = application
        self.site = application.site
        self.cache = {}

    def getItem(self,key):
        item,ts = self.cache.get(key,(None,None))
        if item is not None:
            last_change_ts = self.site.register.globalStore().getItem('CACHE_TS.%s' %key)
            if last_change_ts and ts<last_change_ts:
                item = None 
        return item

    def setItem(self,key,value):
        now = datetime.now()
        self.cache[key] = (value,now)

    def updatedItem(self,key):
        with self.site.register.globalStore() as gs:
            gs.setItem('CACHE_TS.%s' %key,datetime.now())
    
    def expiredItem(self,key):
        item,ts = self.cache.get(key,(None,None))
        if item is None:
            return True
        last_cache_ts = self.site.register.globalStore().getItem('CACHE_TS.%s' %key)
        return last_cache_ts and ts<last_cache_ts

class GnrWsgiWebApp(GnrApp):
    def __init__(self, *args, **kwargs):
        if 'site' in kwargs:
            self.site = kwargs.get('site')
            kwargs.pop('site')
        else:
            self.site = None
        self._siteMenuDict = dict()
        super(GnrWsgiWebApp, self).__init__(*args, **kwargs)
        self.cache = WebApplicationCache(self)
    
    def createAuxInstance(self,instance_name):
        return GnrWsgiWebApp(instance_name,site=self.site)

    def notifyDbUpdate(self,tblobj,recordOrPkey=None,**kwargs):
        if isinstance(recordOrPkey,list):
            records = recordOrPkey
        elif not recordOrPkey and kwargs:
            records = tblobj.query(**kwargs).fetch()
        else:
            broadcast = tblobj.attributes.get('broadcast')
            if broadcast is False:
                return
            if isinstance(recordOrPkey, str):
                if isinstance(broadcast, str):
                    records = [tblobj.record(pkey=recordOrPkey).output('dict')]
                else:
                    records = [{tblobj.pkey:recordOrPkey}]
            else:
                records = [recordOrPkey]
        for record in records:
            self.notifyDbEvent(tblobj, record, 'U')
    
    def notifyDbEvent(self, tblobj, record, event, old_record=None,**kwargs):
        """TODO
        
        :param tblobj: the :ref:`database table <table>` object
        :param record: TODO
        :param event: TODO
        :param old_record: TODO. """
        currentEnv = self.db.currentEnv
        if currentEnv.get('hidden_transaction'):
            return
        dbeventKey = 'dbevents_%s' %self.db.connectionKey()
        if not currentEnv.get('env_transaction_id'):
            self.db.updateEnv(env_transaction_id= getUuid())
        broadcast = tblobj.attributes.get('broadcast')
        if broadcast is not False and broadcast != '*old*':
            dbevents=currentEnv.setdefault(dbeventKey,{})
            r=dict(dbevent=event,pkey=record.get(tblobj.pkey),old_pkey=old_record.get(tblobj.pkey) if old_record else None)
            if broadcast and broadcast is not True:
                for field in broadcast.split(','):
                    newvalue = record.get(field)
                    r[field] = self.catalog.asTypedText(newvalue) #2011/01/01::D
                    if old_record:
                        oldvalue = old_record.get(field)
                        if newvalue!=oldvalue:
                            r['old_%s' %field] = self.catalog.asTypedText(old_record.get(field))
            r['autoCommit'] = self.db.currentEnv.get('autoCommit')
            dbevents.setdefault(tblobj.fullname,[]).append(r)
        audit_mode = tblobj.attributes.get('audit')
        if audit_mode:
            self.db.table('adm.audit').audit(tblobj,event,audit_mode=audit_mode,record=record, old_record=old_record)
                

    def onDbCommitted(self):
        super(GnrWsgiWebApp, self).onDbCommitted()
        dbeventKey = 'dbevents_%s' %self.db.connectionKey()
        dbeventsDict= self.db.currentEnv.pop(dbeventKey,None)
        dbevent_reason = self.db.currentEnv.pop('dbevent_reason',None)
        if dbeventsDict:
            page = self.site.currentPage
            tables = [k for k,v in list(dbeventsDict.items()) if v]
            subscribed_tables = self.site.getSubscribedTables(tables)
            if subscribed_tables:
                for table in set(tables).difference(subscribed_tables):
                    dbeventsDict.pop(table)         
                for table,dbevents in list(dbeventsDict.items()):
                    dbeventsDict[table] = self._compress_dbevents(dbevents)
                page_id = None
                pagename = None
                if page:
                    page_id = page.page_id
                    pagename = page.pagename
                self.site.register.notifyDbEvents(dbeventsDict,register_name='page',
                                                 origin_page_id=page_id,
                                                 dbevent_reason=dbevent_reason or pagename)
            self.db.updateEnv(env_transaction_id= None,dbevents=None)

    def _compress_dbevents(self,dbevents):
        event_index = dict()
        result = list()
        filter_ignored = False
        for event in dbevents:
            pkey = event['pkey']
            eventype = event['dbevent']
            if not pkey in event_index:
                event_index[pkey] = len(result)
                result.append(event)
            else:
                event_to_update = result[event_index[pkey]]
                if eventype=='U':
                    event.pop('dbevent')
                elif eventype=='D' and event_to_update['dbevent'] == 'I':
                    event['dbevent'] = 'X'
                    filter_ignored = True
                event_to_update.update(event)
        return [r for r in result if r['dbevent']!='X'] if filter_ignored else result

    def _get_pagePackageId(self, filename):
        _packageId = None
        fpath, last = os.path.split(os.path.realpath(filename))
        while last and last != 'webpages':
            fpath, last = os.path.split(fpath)
        if last == 'webpages':
            _packageId = self.packagesIdByPath[fpath]
        if not _packageId:
            _packageId = self.config.getAttr('packages', 'default')
        return _packageId

    def newUserUrl(self):
        if self.config['authentication?canRegister']:
            authpkg = self.authPackage()
            if authpkg and hasattr(authpkg, 'newUserUrl'):
                return authpkg.newUserUrl()

    def modifyUserUrl(self):
        authpkg = self.authPackage()
        if authpkg and hasattr(authpkg, 'modifyUserUrl'):
            return authpkg.modifyUserUrl()


    def checkAllowedIp(self,allowed_ip):
        if allowed_ip is None:
            return True
        if isinstance(allowed_ip,bool):
            return allowed_ip
        currentPage = self.site.currentPage
        iplist = currentPage.connection.ip.split('.')
        for ip in allowed_ip.split(','):
            ipcheck = ip.split('.') 
            if iplist[0:len(ipcheck)] == ipcheck:
                return True
        return False

    def loginUrl(self):
        authpkg = self.authPackage()
        loginUrl = ''
        if authpkg and hasattr(authpkg, 'loginUrl'):
            loginUrl = authpkg.loginUrl()
        return loginUrl

    def sqlDebugger(self, **kwargs):
        self.site.sqlDebugger(**kwargs)

    def clearSiteMenu(self):
        self._siteMenuDict = dict()


    def getAvatar(self, user, password=None, authenticate=False, page=None, **kwargs):
        """TODO

        :param user: MANDATORY. The guest username
        :param password: the username's password
        :param authenticate: boolean. If ``True``, to enter in the application a password is required
        :param page: TODO"""
        if user:
            page = page or self.site.currentPage
            if page and page.connectionStore().getItem('external_verified_user') == user:
                authenticate = False
            authmethods = self.config['authentication']
            if user=='gnrtoken':
                user = self.db.table('sys.external_token').authenticatedUser(password)
                if not user:
                    return
                authenticate = False
            if authmethods:
                for node in self.config['authentication'].nodes:
                    nodeattr = node.attr
                    authmode = nodeattr.get('mode') or node.label.replace('_auth', '')
                    avatar = getattr(self, 'auth_%s' % authmode)(node, user, password=password,
                                                                 authenticate=authenticate,
                                                                 **kwargs)
                    if not (avatar is None):
                        avatar.page = page
                        avatar.authmode = authmode
                        errors = self.pkgBroadcast('onAuthentication',avatar)
                        return avatar