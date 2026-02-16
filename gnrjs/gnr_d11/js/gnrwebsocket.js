/*
 *-*- coding: UTF-8 -*-
 *--------------------------------------------------------------------------
 * package       : Genro js - see LICENSE for details
 * module genro_dlg : todo
 * Copyright (c) : 2004 - 2007 Softwell sas - Milano
 * Written by    : Giovanni Porcari, Michele Bertoldi
 *                 Saverio Porcari, Francesco Porcari
 *--------------------------------------------------------------------------
 *This library is free software; you can redistribute it and/or
 *modify it under the terms of the GNU Lesser General Public
 *License as published by the Free Software Foundation; either
 *version 2.1 of the License, or (at your option) any later version.

 *This library is distributed in the hope that it will be useful,
 *but WITHOUT ANY WARRANTY; without even the implied warranty of
 *MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 *Lesser General Public License for more details.

 *You should have received a copy of the GNU Lesser General Public
 *License along with this library; if not, write to the Free Software
 *Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
 */


//######################## genro  #########################

dojo.declare("gnr.GnrWebSocketHandler", null, {
    constructor: function(application, wsroot, options) {
        this.application = application;
        this.wsroot=wsroot;
        this.url=(window.location.protocol=='https:'?'wss://':'ws://')+window.location.host+wsroot;
        var wsOptions = objectUpdate({ debug: false, ping_time:1000,
                                       minReconnectionDelay: 4000 }, options);
        this.options = wsOptions;
        this.waitingCalls={};
        
    },
    create:function(){
        if (this.wsroot){
            this.socket=new ReconnectingWebSocket(this.url, null,this.options);
            var that=this;
            this.socket.onopen=function(){
                that.onopen();
            };
            this.socket.onclose=function(){
                that.onclose();
            };
            this.socket.onmessage=function(e){
                that.onmessage(e);
            };
            this.socket.onerror=function(error){
                that.onerror(error);
            };
        }
        
    },

    addhandler:function(name,cb){
        this[name] = cb;
    },

    onopen:function(){
        that=this;
        this.send('connected',{'page_id':genro.page_id});
        this._interval=setInterval(function(){
                                     genro.wsk.ping();
                                   },this.options.ping_time);
    },
    onclose:function(){
        clearInterval(this._interval);
        console.log('disconnected websocket');
    },
    onerror:function(error){
        console.error('WebSocket Error ' + error);
    },
    ping:function(){
        this.send('ping',{lastEventAge:(new Date()-genro._lastUserEventTs)});
    },

    onmessage:function(e){
        var data=e.data;
        if (data=='pong'){
            return;
        }
        
        if (data.indexOf('<?xml')==0){
            var result=this.parseResponse(e.data);
            var token=result.getItem('token') 
            if (token){
                this.receivedToken(token,result.getItem('envelope'))
            }else{
                this.receivedCommand(result.getItem('command'),result.getItem('data'))
            }
        }else{
            genro.publish('websocketMessage',data)
        }
    },
    receivedCommand:function(command,data){
        var handler;
        if (command){
            if (command.indexOf('.')>0){
                comlst=command.split('.')
                handler=genro[comlst[0]]['do_'+comlst.splice(1).join('.')]
            }
            else{
                handler=this['do_'+command] || this.do_publish
            }
        }else{
            handler=this.do_publish
        }
        handler.apply(this,[data])
    },
    receivedToken:function(token,envelope){
        var deferred=objectPop(this.waitingCalls,token);
        envelope = envelope || new gnr.GnrBag();
        var dataNode = envelope.getNode('data');
        var error = envelope.getItem('error');
        if (error){
            deferred.callback({'error':error,'dataNode':dataNode});
        }
        else{
            deferred.callback(dataNode);
        }
    
   },
    do_alert:function(data){
        alert(data)
    },
    do_set:function(data){
        var path=data.getItem('path')
        var valueNode=data.getNode('data')
        var fired=data.getItem('fired')
        genro.setData(path,valueNode._value,valueNode.attr, true)
        if (fired){
            genro.setData(path,null,null,false)
        }
        
    },

    do_setInClientData:function(data){
        var value = data.getItem('value');
        var attributes = data.getItem('attributes');
        if(attributes){
            attributes = attributes.asDict();
        }
        var path = data.getItem('path');
        var reason = data.getItem('reason');
        var fired = data.getItem('fired');
        var nodeId = data.getItem('nodeId');
        var noTrigger = data.getItem('noTrigger');
        var root = nodeId? genro.nodeById(nodeId):genro.src.getNode();
        root.setRelativeData(path,value,attributes,fired,reason,null,noTrigger?{doTrigger:false}:null)
    },

    do_datachanges:function(datachanges){
        genro.rpc.setDatachangesInData(datachanges)
    },

    do_sharedObjectChange:function(data){
        var shared_id = data.getItem('shared_id');
        var path = data.getItem('path');
        var value = data.getItem('value');
        var attr = data.getItem('attr');
        var evt = data.getItem('evt');
        var from_page_id = data.getItem('from_page_id');
        var so = genro._sharedObjects[shared_id];
        if(!so){
            return;
        }
        var sopath = so.path;
        var fullpath = path? sopath+ '.' +path: sopath;
        if(evt=='del'){
            genro._data.popNode(fullpath,'serverChange')
        }else{
            genro._data.setItem(fullpath, value, attr, objectUpdate({'doTrigger':'serverChange',lazySet:true}));
        }
    },

    do_publish:function(data){
        var topic=data.getItem('topic')
        var nodeId = data.pop('nodeId');
        var iframe = data.pop('iframe');
        var parent = data.pop('parent');
        if (!topic){
            topic='websocketMessage';
        }else{
            var data = data.getItem('data');
            if(data instanceof gnr.GnrBag){
                data = data.asDict();
            }
        }
        if(nodeId || iframe || parent){
            topic = {topic:topic,nodeId:nodeId,iframe:iframe,parent:parent};
        }
        genro.publish(topic,data)
    },
    call:function(kw,omitSerialize,cb){
        var deferred = new dojo.Deferred();
        var kw= objectUpdate({},kw);
        var _onResult = objectPop(kw,'_onResult');
        var _onError = objectPop(kw,'_onError');
        var token='wstk_'+genro.getCounter('wstk');
        kw['result_token']=token;
        kw['command']= kw['command'] || 'call';
        if (!omitSerialize){
            kw=genro.rpc.serializeParameters(genro.src.dynamicParameters(kw));
        }
        this.waitingCalls[token] = deferred;
        //console.log('sending',kw)
        this.socket.send(dojo.toJson(kw));
        deferred.addCallback(function(result){
            if(result && result.error){
                if(_onError){
                    funcApply(_onError,{result:result});
                }else{
                    console.error('WSK ERROR',result.error);
                    genro.setData('gnr.wsk.lastErrorTraceback',result.dataNode);
                    genro.dev.openBagInspector('gnr.wsk.lastErrorTraceback',{title:'WSK error'});
                    //console.log('ERROR TRACEBACK',result.dataNode.getValue());
                }
            }
            return result;
        });
        if(_onResult){
            deferred.addCallback(_onResult);
        }
        return deferred;
    },
    send:function(command,kw){
        var kw=kw || {};
        kw['command']=command
        kw=genro.rpc.serializeParameters(genro.src.dynamicParameters(kw));
        var msg = dojo.toJson(kw);
        this.socket.send(msg);
    },
    
    parseResponse:function(response){
        var result = new gnr.GnrBag();
        var parser=new window.DOMParser()
        result.fromXmlDoc(parser.parseFromString(response, "text/xml")
                                            ,genro.clsdict);
        return result
    },
    
    sendCommandToPage:function(page_id,command,data){
        var envelope=new gnr.GnrBag({'command':command,'data':data})
         this.send('route',{'target_page_id':page_id,'envelope':envelope.toXml()})
    },
    setInClientData:function(page_id,path,data){
        this.sendCommandToPage(page_id,'set',new gnr.GnrBag({'data':data,'path':path}))
    },
    fireInClientData:function(page_id,path,data){
        this.sendCommandToPage(page_id,'set',new gnr.GnrBag({'data':data,'path':path,'fired':true}))
    },
    publishToClient:function(page_id,topic,data){
        this.sendCommandToPage(page_id,'publish',new gnr.GnrBag({'data':data,'topic':topic}))
    },
    errorHandler:function(error){
        console.log('wsk errorHandler',error)
    }
});

/*!
 * Reconnecting WebSocket v4.4.0
 * by Pedro Ladaria <pedro.ladaria@gmail.com>
 * https://github.com/pladaria/reconnecting-websocket
 * License MIT
 */
var ReconnectingWebSocket = (function () {
    'use strict';

    var extendStatics = function(d, b) {
        extendStatics = Object.setPrototypeOf ||
            ({ __proto__: [] } instanceof Array && function (d, b) { d.__proto__ = b; }) ||
            function (d, b) { for (var p in b) if (b.hasOwnProperty(p)) d[p] = b[p]; };
        return extendStatics(d, b);
    };

    function __extends(d, b) {
        extendStatics(d, b);
        function __() { this.constructor = d; }
        d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
    }

    function __values(o) {
        var m = typeof Symbol === "function" && o[Symbol.iterator], i = 0;
        if (m) return m.call(o);
        return {
            next: function () {
                if (o && i >= o.length) o = void 0;
                return { value: o && o[i++], done: !o };
            }
        };
    }

    function __read(o, n) {
        var m = typeof Symbol === "function" && o[Symbol.iterator];
        if (!m) return o;
        var i = m.call(o), r, ar = [], e;
        try {
            while ((n === void 0 || n-- > 0) && !(r = i.next()).done) ar.push(r.value);
        }
        catch (error) { e = { error: error }; }
        finally {
            try {
                if (r && !r.done && (m = i["return"])) m.call(i);
            }
            finally { if (e) throw e.error; }
        }
        return ar;
    }

    function __spread() {
        for (var ar = [], i = 0; i < arguments.length; i++)
            ar = ar.concat(__read(arguments[i]));
        return ar;
    }

    var Event = /** @class */ (function () {
        function Event(type, target) {
            this.target = target;
            this.type = type;
        }
        return Event;
    }());
    var ErrorEvent = /** @class */ (function (_super) {
        __extends(ErrorEvent, _super);
        function ErrorEvent(error, target) {
            var _this = _super.call(this, 'error', target) || this;
            _this.message = error.message;
            _this.error = error;
            return _this;
        }
        return ErrorEvent;
    }(Event));
    var CloseEvent = /** @class */ (function (_super) {
        __extends(CloseEvent, _super);
        function CloseEvent(code, reason, target) {
            if (code === void 0) { code = 1000; }
            if (reason === void 0) { reason = ''; }
            var _this = _super.call(this, 'close', target) || this;
            _this.wasClean = true;
            _this.code = code;
            _this.reason = reason;
            return _this;
        }
        return CloseEvent;
    }(Event));

    var getGlobalWebSocket = function () {
        if (typeof WebSocket !== 'undefined') {
            return WebSocket;
        }
    };
    var isWebSocket = function (w) { return typeof w !== 'undefined' && !!w && w.CLOSING === 2; };
    var DEFAULT = {
        maxReconnectionDelay: 10000,
        minReconnectionDelay: 1000 + Math.random() * 4000,
        minUptime: 5000,
        reconnectionDelayGrowFactor: 1.3,
        connectionTimeout: 4000,
        maxRetries: Infinity,
        maxEnqueuedMessages: Infinity,
        startClosed: false,
        debug: false,
    };
    var ReconnectingWebSocket = /** @class */ (function () {
        function ReconnectingWebSocket(url, protocols, options) {
            var _this = this;
            if (options === void 0) { options = {}; }
            this._listeners = {
                error: [],
                message: [],
                open: [],
                close: [],
            };
            this._retryCount = -1;
            this._shouldReconnect = true;
            this._connectLock = false;
            this._binaryType = 'blob';
            this._closeCalled = false;
            this._messageQueue = [];
            this.onclose = null;
            this.onerror = null;
            this.onmessage = null;
            this.onopen = null;
            this._handleOpen = function (event) {
                _this._debug('open event');
                var _a = _this._options.minUptime, minUptime = _a === void 0 ? DEFAULT.minUptime : _a;
                clearTimeout(_this._connectTimeout);
                _this._uptimeTimeout = setTimeout(function () { return _this._acceptOpen(); }, minUptime);
                _this._ws.binaryType = _this._binaryType;
                _this._messageQueue.forEach(function (message) { return _this._ws.send(message); });
                _this._messageQueue = [];
                if (_this.onopen) {
                    _this.onopen(event);
                }
                _this._listeners.open.forEach(function (listener) { return _this._callEventListener(event, listener); });
            };
            this._handleMessage = function (event) {
                _this._debug('message event');
                if (_this.onmessage) {
                    _this.onmessage(event);
                }
                _this._listeners.message.forEach(function (listener) { return _this._callEventListener(event, listener); });
            };
            this._handleError = function (event) {
                _this._debug('error event', event.message);
                _this._disconnect(undefined, event.message === 'TIMEOUT' ? 'timeout' : undefined);
                if (_this.onerror) {
                    _this.onerror(event);
                }
                _this._debug('exec error listeners');
                _this._listeners.error.forEach(function (listener) { return _this._callEventListener(event, listener); });
                _this._connect();
            };
            this._handleClose = function (event) {
                _this._debug('close event');
                _this._clearTimeouts();
                if (_this._shouldReconnect) {
                    _this._connect();
                }
                if (_this.onclose) {
                    _this.onclose(event);
                }
                _this._listeners.close.forEach(function (listener) { return _this._callEventListener(event, listener); });
            };
            this._url = url;
            this._protocols = protocols;
            this._options = options;
            if (this._options.startClosed) {
                this._shouldReconnect = false;
            }
            this._connect();
        }
        Object.defineProperty(ReconnectingWebSocket, "CONNECTING", {
            get: function () { return 0; },
            enumerable: true, configurable: true
        });
        Object.defineProperty(ReconnectingWebSocket, "OPEN", {
            get: function () { return 1; },
            enumerable: true, configurable: true
        });
        Object.defineProperty(ReconnectingWebSocket, "CLOSING", {
            get: function () { return 2; },
            enumerable: true, configurable: true
        });
        Object.defineProperty(ReconnectingWebSocket, "CLOSED", {
            get: function () { return 3; },
            enumerable: true, configurable: true
        });
        Object.defineProperty(ReconnectingWebSocket.prototype, "CONNECTING", {
            get: function () { return ReconnectingWebSocket.CONNECTING; },
            enumerable: true, configurable: true
        });
        Object.defineProperty(ReconnectingWebSocket.prototype, "OPEN", {
            get: function () { return ReconnectingWebSocket.OPEN; },
            enumerable: true, configurable: true
        });
        Object.defineProperty(ReconnectingWebSocket.prototype, "CLOSING", {
            get: function () { return ReconnectingWebSocket.CLOSING; },
            enumerable: true, configurable: true
        });
        Object.defineProperty(ReconnectingWebSocket.prototype, "CLOSED", {
            get: function () { return ReconnectingWebSocket.CLOSED; },
            enumerable: true, configurable: true
        });
        Object.defineProperty(ReconnectingWebSocket.prototype, "binaryType", {
            get: function () {
                return this._ws ? this._ws.binaryType : this._binaryType;
            },
            set: function (value) {
                this._binaryType = value;
                if (this._ws) { this._ws.binaryType = value; }
            },
            enumerable: true, configurable: true
        });
        Object.defineProperty(ReconnectingWebSocket.prototype, "retryCount", {
            get: function () { return Math.max(this._retryCount, 0); },
            enumerable: true, configurable: true
        });
        Object.defineProperty(ReconnectingWebSocket.prototype, "bufferedAmount", {
            get: function () {
                var bytes = this._messageQueue.reduce(function (acc, message) {
                    if (typeof message === 'string') { acc += message.length; }
                    else if (message instanceof Blob) { acc += message.size; }
                    else { acc += message.byteLength; }
                    return acc;
                }, 0);
                return bytes + (this._ws ? this._ws.bufferedAmount : 0);
            },
            enumerable: true, configurable: true
        });
        Object.defineProperty(ReconnectingWebSocket.prototype, "extensions", {
            get: function () { return this._ws ? this._ws.extensions : ''; },
            enumerable: true, configurable: true
        });
        Object.defineProperty(ReconnectingWebSocket.prototype, "protocol", {
            get: function () { return this._ws ? this._ws.protocol : ''; },
            enumerable: true, configurable: true
        });
        Object.defineProperty(ReconnectingWebSocket.prototype, "readyState", {
            get: function () {
                if (this._ws) { return this._ws.readyState; }
                return this._options.startClosed
                    ? ReconnectingWebSocket.CLOSED
                    : ReconnectingWebSocket.CONNECTING;
            },
            enumerable: true, configurable: true
        });
        Object.defineProperty(ReconnectingWebSocket.prototype, "url", {
            get: function () { return this._ws ? this._ws.url : ''; },
            enumerable: true, configurable: true
        });
        ReconnectingWebSocket.prototype.close = function (code, reason) {
            if (code === void 0) { code = 1000; }
            this._closeCalled = true;
            this._shouldReconnect = false;
            this._clearTimeouts();
            if (!this._ws) { this._debug('close enqueued: no ws instance'); return; }
            if (this._ws.readyState === this.CLOSED) { this._debug('close: already closed'); return; }
            this._ws.close(code, reason);
        };
        ReconnectingWebSocket.prototype.reconnect = function (code, reason) {
            this._shouldReconnect = true;
            this._closeCalled = false;
            this._retryCount = -1;
            if (!this._ws || this._ws.readyState === this.CLOSED) {
                this._connect();
            } else {
                this._disconnect(code, reason);
                this._connect();
            }
        };
        ReconnectingWebSocket.prototype.send = function (data) {
            if (this._ws && this._ws.readyState === this.OPEN) {
                this._debug('send', data);
                this._ws.send(data);
            } else {
                var _a = this._options.maxEnqueuedMessages, maxEnqueuedMessages = _a === void 0 ? DEFAULT.maxEnqueuedMessages : _a;
                if (this._messageQueue.length < maxEnqueuedMessages) {
                    this._debug('enqueue', data);
                    this._messageQueue.push(data);
                }
            }
        };
        ReconnectingWebSocket.prototype.addEventListener = function (type, listener) {
            if (this._listeners[type]) { this._listeners[type].push(listener); }
        };
        ReconnectingWebSocket.prototype.dispatchEvent = function (event) {
            var e_1, _a;
            var listeners = this._listeners[event.type];
            if (listeners) {
                try {
                    for (var listeners_1 = __values(listeners), listeners_1_1 = listeners_1.next(); !listeners_1_1.done; listeners_1_1 = listeners_1.next()) {
                        var listener = listeners_1_1.value;
                        this._callEventListener(event, listener);
                    }
                }
                catch (e_1_1) { e_1 = { error: e_1_1 }; }
                finally {
                    try { if (listeners_1_1 && !listeners_1_1.done && (_a = listeners_1.return)) _a.call(listeners_1); }
                    finally { if (e_1) throw e_1.error; }
                }
            }
            return true;
        };
        ReconnectingWebSocket.prototype.removeEventListener = function (type, listener) {
            if (this._listeners[type]) {
                this._listeners[type] = this._listeners[type].filter(function (l) { return l !== listener; });
            }
        };
        ReconnectingWebSocket.prototype._debug = function () {
            var args = [];
            for (var _i = 0; _i < arguments.length; _i++) { args[_i] = arguments[_i]; }
            if (this._options.debug) { console.log.apply(console, __spread(['RWS>'], args)); }
        };
        ReconnectingWebSocket.prototype._getNextDelay = function () {
            var _a = this._options, _b = _a.reconnectionDelayGrowFactor, reconnectionDelayGrowFactor = _b === void 0 ? DEFAULT.reconnectionDelayGrowFactor : _b, _c = _a.minReconnectionDelay, minReconnectionDelay = _c === void 0 ? DEFAULT.minReconnectionDelay : _c, _d = _a.maxReconnectionDelay, maxReconnectionDelay = _d === void 0 ? DEFAULT.maxReconnectionDelay : _d;
            var delay = 0;
            if (this._retryCount > 0) {
                delay = minReconnectionDelay * Math.pow(reconnectionDelayGrowFactor, this._retryCount - 1);
                if (delay > maxReconnectionDelay) { delay = maxReconnectionDelay; }
            }
            this._debug('next delay', delay);
            return delay;
        };
        ReconnectingWebSocket.prototype._wait = function () {
            var _this = this;
            return new Promise(function (resolve) { setTimeout(resolve, _this._getNextDelay()); });
        };
        ReconnectingWebSocket.prototype._getNextUrl = function (urlProvider) {
            if (typeof urlProvider === 'string') { return Promise.resolve(urlProvider); }
            if (typeof urlProvider === 'function') {
                var url = urlProvider();
                if (typeof url === 'string') { return Promise.resolve(url); }
                if (!!url.then) { return url; }
            }
            throw Error('Invalid URL');
        };
        ReconnectingWebSocket.prototype._connect = function () {
            var _this = this;
            if (this._connectLock || !this._shouldReconnect) { return; }
            this._connectLock = true;
            var _a = this._options, _b = _a.maxRetries, maxRetries = _b === void 0 ? DEFAULT.maxRetries : _b, _c = _a.connectionTimeout, connectionTimeout = _c === void 0 ? DEFAULT.connectionTimeout : _c, _d = _a.WebSocket, WebSocket = _d === void 0 ? getGlobalWebSocket() : _d;
            if (this._retryCount >= maxRetries) {
                this._debug('max retries reached', this._retryCount, '>=', maxRetries);
                return;
            }
            this._retryCount++;
            this._debug('connect', this._retryCount);
            this._removeListeners();
            if (!isWebSocket(WebSocket)) { throw Error('No valid WebSocket class provided'); }
            this._wait()
                .then(function () { return _this._getNextUrl(_this._url); })
                .then(function (url) {
                if (_this._closeCalled) { return; }
                _this._debug('connect', { url: url, protocols: _this._protocols });
                _this._ws = _this._protocols
                    ? new WebSocket(url, _this._protocols)
                    : new WebSocket(url);
                _this._ws.binaryType = _this._binaryType;
                _this._connectLock = false;
                _this._addListeners();
                _this._connectTimeout = setTimeout(function () { return _this._handleTimeout(); }, connectionTimeout);
            });
        };
        ReconnectingWebSocket.prototype._handleTimeout = function () {
            this._debug('timeout event');
            this._handleError(new ErrorEvent(Error('TIMEOUT'), this));
        };
        ReconnectingWebSocket.prototype._disconnect = function (code, reason) {
            if (code === void 0) { code = 1000; }
            this._clearTimeouts();
            if (!this._ws) { return; }
            this._removeListeners();
            try {
                this._ws.close(code, reason);
                this._handleClose(new CloseEvent(code, reason, this));
            } catch (error) { /* ignore */ }
        };
        ReconnectingWebSocket.prototype._acceptOpen = function () {
            this._debug('accept open');
            this._retryCount = 0;
        };
        ReconnectingWebSocket.prototype._callEventListener = function (event, listener) {
            if ('handleEvent' in listener) { listener.handleEvent(event); }
            else { listener(event); }
        };
        ReconnectingWebSocket.prototype._removeListeners = function () {
            if (!this._ws) { return; }
            this._debug('removeListeners');
            this._ws.removeEventListener('open', this._handleOpen);
            this._ws.removeEventListener('close', this._handleClose);
            this._ws.removeEventListener('message', this._handleMessage);
            this._ws.removeEventListener('error', this._handleError);
        };
        ReconnectingWebSocket.prototype._addListeners = function () {
            if (!this._ws) { return; }
            this._debug('addListeners');
            this._ws.addEventListener('open', this._handleOpen);
            this._ws.addEventListener('close', this._handleClose);
            this._ws.addEventListener('message', this._handleMessage);
            this._ws.addEventListener('error', this._handleError);
        };
        ReconnectingWebSocket.prototype._clearTimeouts = function () {
            clearTimeout(this._connectTimeout);
            clearTimeout(this._uptimeTimeout);
        };
        return ReconnectingWebSocket;
    }());

    return ReconnectingWebSocket;

}());