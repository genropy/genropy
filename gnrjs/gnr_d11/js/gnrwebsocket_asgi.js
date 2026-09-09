/* WSX transport for ordinary ephemeral-page RPC calls. */
dojo.declare('gnr.GnrWebSocketHandler', null, {
    constructor: function(application, wsroot, options) {
        this.application = application;
        this.wsroot = wsroot;
        this.pending = {};
        this.counter = 0;
        this.channelReady = null;
        this.url = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') +
                   window.location.host + (wsroot || '/websocket');
    },

    create: function() {
        if (!this.wsroot || this.channelReady) { return; }
        var that = this;
        this.channelReady = new Promise(function(resolve, reject) {
            that.socket = new WebSocket(that.url);
            that.socket.onmessage = function(event) { that.onmessage(event); };
            that.socket.onopen = function() {
                that.request('/_wsx/openchannel', {parameters: {sequential: true}})
                    .then(resolve, reject);
            };
            that.socket.onerror = function() { reject(new Error('WSX connection failed')); };
            that.socket.onclose = function() {
                var error = new Error('WSX connection closed');
                reject(error);
                Object.keys(that.pending).forEach(function(id) {
                    clearTimeout(that.pending[id].timer);
                    that.pending[id].reject(error);
                });
                that.pending = {};
            };
        });
        // Bootstrap can open the channel before the first application call.
        this.channelReady.catch(function(error) { console.error(error); });
    },

    request: function(path, payload) {
        var that = this;
        return new Promise(function(resolve, reject) {
            var id = 'wsx_' + (++that.counter);
            var timer = setTimeout(function() {
                delete that.pending[id];
                reject(new Error('WSX reply timeout'));
            }, 15000);
            that.pending[id] = {resolve: resolve, reject: reject, timer: timer};
            try {
                // Initial payloads use the JSON subset of TYTX transport.
                that.socket.send('WSX://' + JSON.stringify({
                    id: id, method: 'WSK', path: path,
                    page_id: that.application.page_id,
                    data: '"' + JSON.stringify(payload) + '"'
                }));
            } catch (error) {
                clearTimeout(timer);
                delete that.pending[id];
                reject(error);
            }
        });
    },

    onmessage: function(event) {
        if (typeof event.data !== 'string' || event.data.indexOf('WSX://') !== 0) { return; }
        var envelope;
        try { envelope = JSON.parse(event.data.slice(6)); }
        catch (error) { console.error('Invalid WSX envelope', error); return; }
        var pending = this.pending[envelope.id];
        if (!pending) { return; }
        clearTimeout(pending.timer);
        delete this.pending[envelope.id];
        try {
            var encoded = envelope.data;
            var result = encoded == null ? null : JSON.parse(encoded.slice(1, -1));
            if (envelope.status >= 400) {
                throw new Error('WSX request failed (' + envelope.status + ')');
            }
            pending.resolve(result);
        } catch (error) { pending.reject(error); }
    },

    call: function(kw, omitSerialize, cb) {
        var deferred = new dojo.Deferred();
        var that = this;
        this.create();
        if (!this.channelReady) {
            deferred.errback(new Error('WSX is disabled'));
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
                registered = false; // resultHandler performs unregister_call.
                result = rpc.resultHandler(xml, ioArgs);
            }
            deferred.callback(result);
        }).catch(function(error) {
            unregister();
            deferred.errback(error);
        });
        if (kw._onResult) { deferred.addCallback(kw._onResult); }
        if (kw._onError) { deferred.addErrback(kw._onError); }
        return deferred;
    },

    errorHandler: function(error) {
        console.error(error);
        return error;
    },

    send: function(command, parameters) {
        // Legacy events are deliberately not forwarded during reception-only work.
        console.debug('WSX event not enabled:', command);
    }
});
