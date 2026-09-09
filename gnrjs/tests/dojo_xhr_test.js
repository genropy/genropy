/* Browser contract tests: real Dojo, native fetch/XHR and a local HTTP server. */
(async function(){
    const output = document.getElementById('results');
    const lines = [];
    function assert(value, message){
        if(!value){ throw new Error(message); }
    }
    function report(message){
        lines.push(message);
        output.textContent = lines.join('\n');
    }
    function wait(dfd){
        return new Promise(function(resolve, reject){
            dfd.addCallbacks(function(value){ resolve(value); return value; },
                             function(error){ reject(error); return error; });
        });
    }
    const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
    const endpoint = '/transport-test/echo';
    async function test(name, run){
        await run();
        report('PASS ' + name);
    }
    async function contract(transport){
        await test(transport + ': methods, encoding, raw bodies and headers', async function(){
            for(const name of ['xhrGet', 'xhrPost', 'xhrPut', 'xhrDelete', 'rawXhrPost', 'rawXhrPut']){
                const args = {url: endpoint, handleAs: 'json',
                    content: {text: 'caffè & tea', multi: ['a', 'b']},
                    headers: {'X-Test': 'transport'}, preventCache: true,
                    postData: 'raw=post&untouched', putData: 'raw=put&untouched'};
                const dfd = dojo[name](args);
                assert(dfd instanceof dojo.Deferred, 'Real Deferred required');
                const result = await wait(dfd);
                const expected = name.includes('Get') ? 'GET' : name.includes('Delete') ? 'DELETE' :
                                 name.includes('Put') ? 'PUT' : 'POST';
                assert(result.method === expected, name + ' method');
                const headers = Object.fromEntries(Object.entries(result.headers).map(([k, v]) => [k.toLowerCase(), v]));
                assert(headers['x-test'] === 'transport', 'Custom header');
                assert(headers['x-requested-with'] === 'XMLHttpRequest', 'Legacy request header');
                if(name.startsWith('raw')){
                    assert(result.body === (name === 'rawXhrPost' ? 'raw=post&untouched' : 'raw=put&untouched'), 'Raw body');
                }else{
                    const params = ['GET', 'DELETE'].includes(expected) ? result.query :
                        Object.fromEntries(new URLSearchParams(result.body));
                    assert(String(params.text) === 'caffè & tea', 'Parameter encoding');
                    assert(params['dojo.preventCache'], 'Cache prevention');
                }
                assert(dfd.ioArgs.xhr.getResponseHeader('X-GnrTime') !== null, 'Timing header');
                assert(dfd.ioArgs.xhr.getAllResponseHeaders().toLowerCase().includes('x-gnrtime:'), 'All headers');
            }
        });
        await test(transport + ': XML and callback transformation', async function(){
            const order = [];
            const args = {url: '/transport-test/xml', handleAs: 'xml',
                load: function(xml, io){
                    assert(this === args && io.args === args, 'Callback context');
                    assert(xml.documentElement.nodeName === 'GenRoBag', 'XML document');
                    assert(xml.getElementsByTagName('result')[0].getAttribute('answer') === 'yes', 'XML attributes');
                    order.push('load');
                    return 40;
                }, handle: function(value){ order.push('handle'); return value + 1; }};
            const dfd = dojo.xhrGet(args);
            dfd.addCallback(function(value){ order.push('callback'); return value + 1; });
            assert(await wait(dfd) === 42, 'Transformed result');
            assert(order.join(',') === 'load,handle,callback', 'Callback ordering');
        });
        await test(transport + ': empty raw PUT retains legacy content and Deferred chaining', async function(){
            const dfd = dojo.rawXhrPut({url: endpoint, handleAs: 'json', putData: '',
                content: {value: 'preserved'}});
            dfd.addCallback(function(result){
                assert(result.body === 'value=preserved', 'Empty raw PUT body');
                return dojo.xhrGet({url: endpoint, handleAs: 'text'});
            });
            assert(JSON.parse(await wait(dfd)).method === 'GET', 'Returned Deferred is awaited');
        });
        await test(transport + ': HTTP error, parser error and recovery', async function(){
            let recovered = false;
            const dfd = dojo.xhrGet({url: endpoint + '?status=500', handleAs: 'json',
                error: function(error, io){
                    assert(error.status === 500 && io.xhr.status === 500, 'HTTP status');
                    assert(error.responseText.includes('GET'), 'Error response');
                    recovered = true;
                    return 'recovered';
                }});
            assert(await wait(dfd) === 'recovered' && recovered, 'Errback recovery');
            try{
                await wait(dojo.xhrGet({url: '/transport-test/invalid-json', handleAs: 'json'}));
                throw new Error('Parser must reject');
            }catch(error){ assert(error instanceof SyntaxError, 'JSON parse error'); }
            assert((await wait(dojo.xhrGet({url: endpoint, handleAs: 'json'}))).method === 'GET', 'Recovery request');
        });
        await test(transport + ': timeout and cancellation complete once', async function(){
            for(const mode of ['timeout', 'cancel', 'abort', 'all']){
                let completions = 0;
                const dfd = dojo.xhrGet({url: endpoint + '?delay=0.12', handleAs: 'json',
                    timeout: mode === 'timeout' ? 15 : 0,
                    handle: function(value){ completions++; return value; }});
                const result = wait(dfd).catch(error => error);
                if(mode === 'cancel'){ dfd.cancel(); }
                if(mode === 'abort'){ dfd.ioArgs.xhr.abort(); }
                if(mode === 'all'){ dojo._ioCancelAll(); }
                // Direct native XHR.abort() does not complete the legacy Deferred.
                if(mode === 'abort' && transport === 'legacy'){ dfd.cancel(); }
                const error = await result;
                assert(error.dojoType === (mode === 'timeout' ? 'timeout' : 'cancel'), mode + ' classification');
                await pause(150);
                assert(completions === 1, mode + ' completed once');
            }
        });
        await test(transport + ': synchronous calls retain native XHR', function(){
            let value;
            const dfd = dojo.xhrGet({url: endpoint, sync: true, handleAs: 'json',
                load: function(result){ value = result; }});
            assert(value.method === 'GET', 'Synchronous callback');
            assert(dfd.ioArgs.xhr instanceof XMLHttpRequest, 'Native synchronous XHR');
        });
        await test(transport + ': timeout while reading response body', async function(){
            const dfd = dojo.xhrGet({url: '/transport-test/slow-body', timeout: 30});
            const error = await wait(dfd).catch(error => error);
            assert(error.dojoType === 'timeout', 'Timeout covers body consumption');
        });
        await test(transport + ': form fields and same-origin cookies', async function(){
            document.cookie = 'dojo_transport_test=present; path=/; SameSite=Lax';
            const form = document.createElement('form');
            form.action = endpoint;
            form.innerHTML = '<input name="field" value="from form">';
            document.body.appendChild(form);
            try{
                const result = await wait(dojo.xhrPost({form: form, handleAs: 'json'}));
                assert(new URLSearchParams(result.body).get('field') === 'from form', 'Form serialization');
                const headers = Object.fromEntries(Object.entries(result.headers).map(([k, v]) => [k.toLowerCase(), v]));
                assert(headers.cookie.includes('dojo_transport_test=present'), 'Session cookie');
            }finally{
                form.remove();
                document.cookie = 'dojo_transport_test=; Max-Age=0; path=/';
            }
        });
    }
    async function benchmark(){
        for(let i = 0; i < 12; i++){
            await wait(dojo.xhrGet({url: endpoint, handleAs: 'json', preventCache: true}));
        }
        const client = [], server = [];
        for(let i = 0; i < 50; i++){
            const start = performance.now();
            const dfd = dojo.xhrGet({url: endpoint, handleAs: 'json', preventCache: true});
            await wait(dfd);
            client.push(performance.now() - start);
            server.push(Number(dfd.ioArgs.xhr.getResponseHeader('X-GnrTime')) * 1000);
        }
        const percentile = (values, p) => values.sort((a, b) => a - b)[Math.ceil(values.length * p) - 1].toFixed(2);
        return {calls: 50, client_p50_ms: percentile(client, 0.5), client_p95_ms: percentile(client, 0.95),
                server_p50_ms: percentile(server, 0.5)};
    }
    try{
        const original = dojo.xhr;
        genropatches.dojoXhr();
        genropatches.dojoXhr('disabled');
        assert(dojo.xhr === original, 'Disabled configuration leaves Dojo unchanged');
        await contract('legacy');
        const legacy = await benchmark();
        genropatches.dojoXhr('fetch');
        assert(dojo.xhr !== original, 'Patch installed');
        const patched = dojo.xhr;
        genropatches.dojoXhr('fetch');
        assert(dojo.xhr === patched, 'Idempotent installation');
        await contract('fetch');
        await test('fetch: async completion bypasses polling', async function(){
            const watch = dojo._ioWatch;
            let watched = 0;
            dojo._ioWatch = function(){ watched++; return watch.apply(dojo, arguments); };
            try{
                await wait(dojo.xhrGet({url: endpoint, handleAs: 'json'}));
                assert(watched === 0, 'No polling for fetch');
                await wait(dojo.xhrGet({url: endpoint, handleAs: 'json', onprogress: function(){}}));
                assert(watched === 1, 'Unsupported options use original transport');
            }finally{ dojo._ioWatch = watch; }
        });
        await test('fetch: network failure completes the Deferred', async function(){
            const error = await wait(dojo.xhrGet({url: '/transport-test/close'})).catch(error => error);
            assert(error instanceof Error, 'Network failure');
        });
        const fetched = await benchmark();
        report('BENCHMARK ' + JSON.stringify({legacy: legacy, fetch: fetched}, null, 2));
        report('ALL TESTS PASSED');
    }catch(error){
        report('FAIL ' + error.stack);
    }
})();
