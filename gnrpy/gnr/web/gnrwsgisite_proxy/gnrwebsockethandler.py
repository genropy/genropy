#-*- coding: utf-8 -*-  
#--------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module gnrwebcore : core module for genropy web framework
# Copyright (c)     : 2004 - 2007 Softwell sas - Milano 
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import os
import http.client
import importlib.metadata
import socket
import urllib.request, urllib.parse, urllib.error
from time import sleep

from gnr.core.gnrbag import Bag
from gnr.web import logger

CONNECTION_REFUSED = 61
MAX_CONNECTION_ATTEMPT = 20 
CONNECTION_ATTEMPT_DELAY = 1

#: The variable that names an alternative provider. It is the one
#: ``gnr.web.daemon`` already reads: a provider is named once and replaces the
#: interfaces it declares an entry point for.
DAEMON_PROVIDER_ENV = 'GNR_DAEMON_PROVIDER'
WEBSOCKET_ENTRY_POINT_GROUP = 'gnr.web'
WEBSOCKET_ENTRY_POINT_NAME = 'websockethandler'
WEBSOCKET_HANDLER_INTERFACE = ('checkSocket', 'sendCommandToPage')

class WebSocketHandler(object):
    def sendCommandToPage(self,page_id,command,data):
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        envelope=Bag(dict(command=command,data=data))
        body=urllib.parse.urlencode(dict(page_id=page_id,remote_service=None,envelope=envelope.toXml(unresolved=True)))
        self.socketConnection.request('POST',self.proxyurl,headers=headers, body=body)
        self.close()

    def sendCommandToRemoteService(self,remote_service=None,command=None,data=None):
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        envelope=Bag(dict(command=command,data=data))
        body=urllib.parse.urlencode(dict(page_id=None,remote_service=remote_service,envelope=envelope.toXml(unresolved=True)))
        self.socketConnection.request('POST',self.proxyurl,headers=headers, body=body)
        self.close()

    def setInClientData(self,page_id,path=None,value=None,nodeId=None,
                    attributes=None,fired=None,reason=None,noTrigger=None):
        if not isinstance(page_id,list):
            page_id = [page_id]
        for p in page_id:
            self.sendCommandToPage(p,'setInClientData',Bag(dict(value=value,path=path,attributes=attributes,reason=reason,nodeId=nodeId,noTrigger=noTrigger)))
        
    def fireInClientData(self,page_id,path=None,data=None):
        self.sendCommandToPage(page_id,'set',Bag(data=data,path=path,fired=True))
        
    def publishToClient(self,page_id,topic=None,data=None,nodeId=None,iframe=None,parent=None):
        self.sendCommandToPage(page_id,'publish',Bag(data=data, topic=topic, nodeId=nodeId, iframe=iframe, parent=parent))

    #def sendDatachanges(self,datachanges):
    #    data=Bag()
    #    for j, change in enumerate(datachanges):
    #        data.setItem('sc_%i' % j, change.value, change_path=change.path, change_reason=change.reason,
    #                       change_fired=change.fired, change_attr=change.attributes,
    #                       change_ts=change.change_ts, change_delete=change.delete)
    #    self.sendCommandToPage(page_id,'datachanges',data)


class WsgiWebSocketHandler(WebSocketHandler):
    def __init__(self,site):
        self.site = site
        sockets_dir = os.path.join(site.site_path, 'sockets')
        if len(sockets_dir)>90:
            sockets_dir = os.path.join('/tmp', os.path.basename(site.instance_path), 'gnr_sock')
        os.makedirs(sockets_dir, exist_ok=True)
        self.socket_path = os.path.join(sockets_dir, 'async.sock')
        self.proxyurl='/wsproxy'
    
    def checkSocket(self):
        try:
            self.socketConnection
            self.close()
            return True
        except socket.error as e:
            if e.errno == CONNECTION_REFUSED:
                return False
        
    def close(self):
        if hasattr(self,'_socketConnection'):
            self.socketConnection.close()
            del self._socketConnection
    @property
    def socketConnection(self):
        if not hasattr(self,'_socketConnection'):
            _socketConnection = HTTPSocketConnection(self.socket_path,timeout=1000)
            _socketConnection.connect()
            self._socketConnection = _socketConnection
        return self._socketConnection
        
    def sendCommandToPage(self,page_id,command,data):
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        envelope=Bag(dict(command=command,data=data))

        body = urllib.parse.urlencode(dict(page_id=page_id,remote_service=None,envelope=envelope.toXml(unresolved=True)))
        #self.socketConnection.request('POST',self.proxyurl,headers=headers, body=body)

        n = MAX_CONNECTION_ATTEMPT
        error = CONNECTION_REFUSED
        while n>0 and error==CONNECTION_REFUSED:
            try:
                self.socketConnection.request('POST',self.proxyurl,headers=headers, body=body)
                error = False
                if n!=MAX_CONNECTION_ATTEMPT:
                    logger.debug("SUCCEED")
                self.close()
            except socket.error as e:
                error = e.errno
                if error == CONNECTION_REFUSED:
                    n -= 1
                    logger.debug('attempting %s',n)
                    sleep(CONNECTION_ATTEMPT_DELAY)
                else:
                    raise




def has_timeout(timeout): # python 2.6
    if hasattr(socket, '_GLOBAL_DEFAULT_TIMEOUT'):
        return (timeout is not None and timeout is not socket._GLOBAL_DEFAULT_TIMEOUT)
    return (timeout is not None)


    
class HTTPSocketConnection(http.client.HTTPConnection):
 
    def __init__(self, socket_path, host='127.0.0.1', port=None,
                timeout=None):
        self.socket_path=socket_path
        super().__init__(host=host, port=port, timeout=timeout)

    def connect(self):
        """Connect to the host and port specified in __init__."""
        # Mostly verbatim from httplib.py.
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            if has_timeout(self.timeout):
                self.sock.settimeout(self.timeout)

            logger.debug("HTTPSocketConnection - connect: (%s)", self.socket_path)
            self.sock.connect(self.socket_path)
            
        except socket.error as msg:
            logger.debug("HTTPSocketConnection - connect fail: (%s)", self.socket_path)
            
            if self.sock:
                self.sock.close()
            self.sock = None
            if not self.sock:
                raise socket.error(msg)

    def close(self):
        if hasattr(self,'sock') and self.sock:
            self.sock.close()


def websocketHandlerClass():
    """Return the class a site builds as its ``wsk``.

    ``WsgiWebSocketHandler``, the handler that talks to the ``gnrasync``
    daemon over ``async.sock``, unless ``GNR_DAEMON_PROVIDER`` names a provider
    that also declares a ``gnr.web:websockethandler`` entry point.

    The WebSocket interface is optional for a provider: one that serves HTTP
    and the register but terminates no socket declares nothing, and the classic
    handler stays — with it the classic probe, which finds no ``async.sock``
    and turns the site's WebSockets off. Two entry points for one provider, or
    one that is not a class carrying ``checkSocket`` and ``sendCommandToPage``,
    is a configuration statement that cannot be honoured and raises
    ``ImportError``.
    """
    provider = os.environ.get(DAEMON_PROVIDER_ENV)
    if not provider:
        return WsgiWebSocketHandler
    eps = importlib.metadata.entry_points(group=WEBSOCKET_ENTRY_POINT_GROUP,
                                          name=WEBSOCKET_ENTRY_POINT_NAME)
    matching = [ep for ep in eps
                if provider in (ep.module, getattr(ep.dist, 'name', None))]
    if not matching:
        logger.info('%s=%r declares no %s:%s entry point: the classic WebSocket '
                    'handler stays', DAEMON_PROVIDER_ENV, provider,
                    WEBSOCKET_ENTRY_POINT_GROUP, WEBSOCKET_ENTRY_POINT_NAME)
        return WsgiWebSocketHandler
    if len(matching) > 1:
        declaring = ', '.join(sorted(
            f'{ep.module} ({getattr(ep.dist, "name", "unknown distribution")})'
            for ep in matching))
        raise ImportError(
            f'{DAEMON_PROVIDER_ENV}={provider!r} matches {len(matching)} '
            f'{WEBSOCKET_ENTRY_POINT_GROUP}:{WEBSOCKET_ENTRY_POINT_NAME} entry '
            f'points; declared by: {declaring}')
    handler = matching[0].load()
    missing = [name for name in WEBSOCKET_HANDLER_INTERFACE
               if not callable(getattr(handler, name, None))]
    if not isinstance(handler, type) or missing:
        raise ImportError(
            f'{DAEMON_PROVIDER_ENV}={provider!r} names {matching[0].value!r} as '
            f'its {WEBSOCKET_ENTRY_POINT_GROUP}:{WEBSOCKET_ENTRY_POINT_NAME}: a '
            f'handler class with {", ".join(WEBSOCKET_HANDLER_INTERFACE)} is '
            f'required, {", ".join(missing) or type(handler).__name__} is not there')
    logger.info('%s=%r resolved to the WebSocket handler %s', DAEMON_PROVIDER_ENV,
                provider, matching[0].value)
    return handler
