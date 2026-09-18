/*
 *-*- coding: UTF-8 -*-
 *--------------------------------------------------------------------------
 * package       : Genro js - see LICENSE for details
 * module gnrwebsocket_wsx : the WSX transport of page RPC calls
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

/*
 * The client a provider names in its handler's `client_module` when the server
 * that hosts the site terminates the WebSocket itself. It takes the place of
 * `gnrwebsocket` in the frontend imports, so a page loads one
 * gnr.GnrWebSocketHandler and the classic one is not on the page at all.
 *
 * The wire format is WSX: the text `WSX://` followed by a JSON object with
 * `id`, `method`, `path`, `page_id` and `data`, where `data` is the payload
 * serialized as a TYTX json string. An answer carries `id`, `status` and
 * `data`; a status of 400 and over makes `data` the reason in plain text.
 *
 * What travels here:
 *   - the channel of the page, on `/_wsx/openchannel`, sent at every opening
 *     of the socket and answered before any call of the page is written;
 *   - the ping, on `/_wsx/ping`, which the server answers with `pong`;
 *   - a page RPC sent with dataRpc(httpMethod='WSK'): the same form the HTTP
 *     branch posts, urlencoded into the `form` field, answered with the site's
 *     own response body and its content-type.
 *
 * What does not: shared objects, `user_event`, `route`, and anything the
 * server sends on its own. `send` logs what it is given and drops it; the
 * datachanges of a call arrive in its own answer, as they do over HTTP.
 */

dojo.declare("gnr.GnrWebSocketHandler", null, {
    constructor: function(application, wsroot, options) {
        this.application = application;
        this.wsroot = wsroot;
        this.options = objectUpdate({debug: false, reconnectInterval: 4000, ping_time: 1000,
                                     replyTimeout: 60000}, options);
        var protocol = window.location.protocol == 'https:' ? 'wss://' : 'ws://';
        this.url = protocol + window.location.host + (wsroot || '');
        this.waitingCalls = {};
        this.counter = 0;
        this.socket = null;
        this.channelReady = null;
        this._interval = null;
        this._reconnect = null;
    },

    create: function() {
        if (!this.wsroot || this.channelReady) {
            return;
        }
        var that = this;
        this.channelReady = new Promise(function(resolve, reject) {
            that.socket = new WebSocket(that.url);
            that.socket.onmessage = function(event) {
                that.onmessage(event);
            };
            that.socket.onopen = function() {
                that.onopen().then(resolve, reject);
            };
            that.socket.onerror = function(error) {
                that.onerror(error);
                reject(new Error('websocket connection failed'));
            };
            that.socket.onclose = function() {
                that.onclose();
                reject(new Error('websocket connection closed'));
            };
        });
        this.channelReady.catch(function(error) {
            console.error(error);
        });
    },

    onopen: function() {
        // The page says it speaks on this socket, at every opening of it: the
        // server binds page to socket only on the answer, and a reconnection
        // needs the binding again.
        var that = this;
        return this.request('/_wsx/openchannel', {parameters: {sequential: true}}).then(function(answer) {
            that._interval = setInterval(function() {
                that.ping();
            }, that.options.ping_time);
            return answer;
        });
    },

    onclose: function() {
        clearInterval(this._interval);
        this._interval = null;
        this.channelReady = null;
        var closed = new Error('websocket connection closed');
        var that = this;
        Object.keys(this.waitingCalls).forEach(function(id) {
            var waiting = objectPop(that.waitingCalls, id);
            clearTimeout(waiting.timer);
            waiting.reject(closed);
        });
        if (this.wsroot && !this._reconnect) {
            this._reconnect = setTimeout(function() {
                that._reconnect = null;
                that.create();
            }, this.options.reconnectInterval);
        }
    },

    onerror: function(error) {
        console.error('WebSocket Error ' + error);
    },

    ping: function() {
        this.request('/_wsx/ping').catch(function(error) {
            console.debug('ping unanswered:', error);
        });
    },

    request: function(path, payload) {
        // One message with an id, and the promise of its answer. The payload
        // travels as a TYTX json string: the outer quotes are the format, and
        // a JSON object inside them is what it reads back as an object.
        var that = this;
        return new Promise(function(resolve, reject) {
            if (!that.socket || that.socket.readyState !== 1) {
                reject(new Error('websocket is not open'));
                return;
            }
            var id = 'wstk_' + (++that.counter);
            var timer = setTimeout(function() {
                objectPop(that.waitingCalls, id);
                reject(new Error('no answer to the websocket message ' + id));
            }, that.options.replyTimeout);
            that.waitingCalls[id] = {resolve: resolve, reject: reject, timer: timer};
            var envelope = {id: id, method: 'WSK', path: path,
                            page_id: that.application.page_id};
            if (payload !== undefined) {
                envelope.data = '"' + JSON.stringify(payload) + '"';
            }
            try {
                that.socket.send('WSX://' + JSON.stringify(envelope));
            } catch (error) {
                clearTimeout(timer);
                objectPop(that.waitingCalls, id);
                reject(error);
            }
        });
    },

    onmessage: function(event) {
        var text = event.data;
        if (typeof text !== 'string' || text.indexOf('WSX://') !== 0) {
            genro.publish('websocketMessage', text);
            return;
        }
        var envelope;
        try {
            envelope = JSON.parse(text.slice(6));
        } catch (error) {
            console.error('unreadable WSX message', error);
            return;
        }
        if (envelope.id == null) {
            // Nothing sends these yet: the server-to-page road is the pull one.
            console.debug('unsolicited WSX message on', envelope.path);
            return;
        }
        var waiting = objectPop(this.waitingCalls, envelope.id);
        if (!waiting) {
            return;
        }
        clearTimeout(waiting.timer);
        var data = this.decode(envelope.data);
        if (envelope.status >= 400) {
            waiting.reject(new Error('websocket message ' + envelope.id + ' refused (' +
                                     envelope.status + '): ' + data));
            return;
        }
        waiting.resolve(data);
    },

    decode: function(text) {
        // A TYTX json payload: the value, JSON, inside one pair of quotes.
        if (text == null) {
            return null;
        }
        var inner = text.slice(1, -1);
        try {
            return JSON.parse(inner);
        } catch (error) {
            return inner;
        }
    },

    call: function(kw, omitSerialize, cb) {
        var deferred = new dojo.Deferred();
        var that = this;
        this.create();
        if (!this.channelReady) {
            deferred.errback(new Error('the websocket transport is not enabled'));
            return deferred;
        }
        var rpc = this.application.rpc;
        var parameters = objectUpdate({}, kw);
        objectPop(parameters, '_onResult');
        objectPop(parameters, '_onError');
        objectPop(parameters, '_sourceNode');
        parameters.mode = parameters.mode || 'bag';
        parameters.page_id = this.application.page_id;
        if (this.application._serverstore_changes) {
            parameters._serverstore_changes = this.application._serverstore_changes;
            this.application._serverstore_changes = null;
        }
        var call = {content: parameters};
        rpc.register_call(call);
        var registered = true;
        function unregister() {
            if (registered) {
                registered = false;
                rpc.unregister_call({args: call});
            }
        }
        this.channelReady.then(function() {
            var serialized = omitSerialize ? parameters :
                rpc.serializeParameters(that.application.src.dynamicParameters(parameters));
            var form = Object.keys(serialized).map(function(key) {
                return encodeURIComponent(key) + '=' + encodeURIComponent(serialized[key]);
            }).join('&');
            return that.request(rpc.pageIndexUrl(), {form: form});
        }).then(function(reply) {
            var result;
            if (parameters.mode === 'json') {
                unregister();
                result = JSON.parse(reply.body);
            } else {
                var xml = new DOMParser().parseFromString(reply.body, 'text/xml');
                var ioArgs = {args: call, url: rpc.pageIndexUrl(), xhr: {
                    getResponseHeader: function(name) {
                        return reply.headers[name.toLowerCase()] || null;
                    }
                }};
                registered = false; // resultHandler unregisters the call itself.
                result = rpc.resultHandler(xml, ioArgs);
            }
            deferred.callback(result);
        }).catch(function(error) {
            unregister();
            deferred.errback(error);
        });
        if (kw._onResult) {
            deferred.addCallback(kw._onResult);
        }
        if (kw._onError) {
            deferred.addErrback(kw._onError);
        }
        return deferred;
    },

    errorHandler: function(error) {
        console.error(error);
        return error;
    },

    send: function(command, parameters) {
        // Shared objects, user events and routes are not carried here.
        console.debug('websocket command not carried by this transport:', command);
    }
});
