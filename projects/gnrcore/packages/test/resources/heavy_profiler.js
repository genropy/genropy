/* Sampling-free instrumentation profiler for the genro client build.
 *
 * Loaded by test_heavy_build.py via js_requires. It wraps the hot methods of
 * the genro engine with self/total time accounting. Activate by adding
 * ?_profile=1 to the page url (wrapping slows everything down, so it is
 * opt-in), or call gnrProfiler.install() from the console.
 *
 * gnrProfiler.report(n)  -> top n rows sorted by self time
 * gnrProfiler.reset()    -> clear counters
 */

window.gnrProfiler = (function() {
    const stats = {};
    const stack = [];
    const stacks = {};
    let installed = false;

    function wrap(obj, name, label) {
        const orig = obj[name];
        if (typeof orig != 'function') {
            console.warn('gnrProfiler: missing', label);
            return;
        }
        const stat = stats[label] = {calls: 0, self: 0, total: 0};
        obj[name] = function() {
            const frame = {child: 0};
            stack.push(frame);
            const t0 = performance.now();
            try {
                return orig.apply(this, arguments);
            } finally {
                const dt = performance.now() - t0;
                stack.pop();
                stat.calls += 1;
                stat.total += dt;
                stat.self += dt - frame.child;
                if (stack.length) {
                    stack[stack.length - 1].child += dt;
                }
            }
        };
        obj[name]._gnrProfiled = orig;
    }

    function wrapGlobal(name) {
        wrap(window, name, 'global.' + name);
    }

    function install() {
        if (installed) {
            return;
        }
        installed = true;
        const bagP = gnr.GnrBag.prototype;
        ['index', 'htraverse', 'setItem', 'set', '_insertNode', 'getNode',
         '_getNode', 'getItem', 'get', 'onNodeTrigger', 'runTrigger', 'walk',
         'fromXmlDoc', 'setBackRef', 'findNodeById', 'getNodeByAttr'].forEach(function(m) {
            wrap(bagP, m, 'Bag.' + m);
        });
        const nodeP = gnr.GnrBagNode.prototype;
        ['setValue', 'setAttr', 'getValue', 'getFullpath'].forEach(function(m) {
            wrap(nodeP, m, 'BagNode.' + m);
        });
        const srcNodeP = gnr.GnrDomSourceNode.prototype;
        ['build', '_doBuildNode', '_buildChildren', 'registerNodeDynAttr',
         '_setDynAttributes', '_resetDynAttributes', 'absDatapath',
         'getAttributeFromDatasource', 'currentFromDatasource',
         'buildLblWrapper', '_registerInForm', 'getFormHandler',
         'trigger_data', 'getTriggerReason', 'updateAttrBuiltObj',
         'checkOnChildBuilding'].forEach(function(m) {
            wrap(srcNodeP, m, 'SrcNode.' + m);
        });
        const srcP = gnr.GnrSrcHandler.prototype;
        ['stripData', 'stripDataNode', 'moveData', 'buildNode',
         'refreshSourceIndexAndSubscribers', 'nodeTrigger'].forEach(function(m) {
            wrap(srcP, m, 'Src.' + m);
        });
        const wdgP = gnr.GnrWdgHandler.prototype;
        ['create', 'getHandler', 'createDojoWidget', 'createHtmlElement',
         'doMixin', 'makeDomNode', 'getWidgetFactory'].forEach(function(m) {
            wrap(wdgP, m, 'Wdg.' + m);
        });
        ['objectUpdate', 'objectExtract', 'objectPop', 'funcCreate',
         'funcApply', 'smartsplit', 'convertFromText', 'isEqual',
         'dataTemplate', 'objectAsStyle'].forEach(wrapGlobal);
        const origGNBA = gnr.GnrBag.prototype.getNodeByAttr;
        gnr.GnrBag.prototype.getNodeByAttr = function() {
            const st = new Error().stack.split('\n').slice(2, 6).join(' | ');
            stacks[st] = (stacks[st] || 0) + 1;
            return origGNBA.apply(this, arguments);
        };
        wrap(dojo, 'subscribe', 'dojo.subscribe');
        wrap(dojo, 'publish', 'dojo.publish');
        wrap(dojo, 'require', 'dojo.require');
        if (gnr.GnrTriggerIndex) {
            ['add', 'remove', 'publish'].forEach(function(m) {
                wrap(gnr.GnrTriggerIndex.prototype, m, 'TriggerIndex.' + m);
            });
        }
        console.log('gnrProfiler installed');
    }

    function report(topN) {
        const rows = Object.keys(stats).map(function(k) {
            const s = stats[k];
            return {name: k, calls: s.calls,
                    self_ms: Math.round(s.self * 10) / 10,
                    total_ms: Math.round(s.total * 10) / 10};
        }).filter(function(r) {
            return r.calls > 0;
        }).sort(function(a, b) {
            return b.self_ms - a.self_ms;
        });
        return rows.slice(0, topN || 30);
    }

    function reset() {
        Object.keys(stats).forEach(function(k) {
            stats[k].calls = 0;
            stats[k].self = 0;
            stats[k].total = 0;
        });
    }

    if (window.location.search.indexOf('_profile') >= 0) {
        install();
    }

    //?_walkcallers -> record the direct caller of every top-level Bag.walk
    const walkCallers = {};
    if (window.location.search.indexOf('_walkcallers') >= 0) {
        let walkDepth = 0;
        const origWalk = gnr.GnrBag.prototype.walk;
        gnr.GnrBag.prototype.walk = function() {
            if (walkDepth === 0) {
                const st = new Error().stack.split('\n').slice(2, 4).join('|');
                walkCallers[st] = (walkCallers[st] || 0) + 1;
            }
            walkDepth += 1;
            try {
                return origWalk.apply(this, arguments);
            } finally {
                walkDepth -= 1;
            }
        };
    }

    const api = {install: install, report: report, reset: reset, stats: stats,
                 stacks: stacks, walkCallers: walkCallers, buildTime: null};

    //?_sample -> run the native JS sampling profiler across the build (needs
    //the Document-Policy: js-profiling response header); aggregated self-hit
    //counts accumulate in localStorage across reloads: gnrProfiler.sampleReport()
    let sampler = null;
    if (window.location.search.indexOf('_sample') >= 0 && window.Profiler) {
        try {
            sampler = new Profiler({sampleInterval: 10, maxBufferSize: 1000000});
        } catch (e) {
            console.warn('gnrProfiler: sampler unavailable', e);
        }
    }

    function frameKey(trace, frameId) {
        const frame = trace.frames[frameId];
        const res = trace.resources[frame.resourceId] || '';
        return (frame.name || '(anon)') + '@' +
               res.split('/').pop().split('?')[0] + ':' + (frame.line || '');
    }

    function aggregateTrace(trace) {
        const agg = JSON.parse(localStorage.getItem('gnr_prof_agg') || '{}');
        const totals = JSON.parse(localStorage.getItem('gnr_prof_tot') || '{}');
        for (const s of trace.samples) {
            let key = '(idle)';
            if (s.stackId !== undefined) {
                key = frameKey(trace, trace.stacks[s.stackId].frameId);
                //every distinct frame on the stack gets one total-hit
                const seen = {};
                let stackId = s.stackId;
                while (stackId !== undefined) {
                    const stackNode = trace.stacks[stackId];
                    const k = frameKey(trace, stackNode.frameId);
                    if (!(k in seen)) {
                        seen[k] = true;
                        totals[k] = (totals[k] || 0) + 1;
                    }
                    stackId = stackNode.parentId;
                }
            }
            agg[key] = (agg[key] || 0) + 1;
        }
        localStorage.setItem('gnr_prof_agg', JSON.stringify(agg));
        localStorage.setItem('gnr_prof_tot', JSON.stringify(totals));
    }

    (function() {
        const origStartUp = gnr.GnrSrcHandler.prototype.startUp;
        gnr.GnrSrcHandler.prototype.startUp = function() {
            const t0 = performance.now();
            const result = origStartUp.apply(this, arguments);
            api.buildTime = performance.now() - t0;
            console.log('gnrProfiler startUp build time:', api.buildTime.toFixed(0), 'ms');
            const done = sampler ? sampler.stop().then(aggregateTrace)
                                 : Promise.resolve();
            done.then(function() {
                //?_bt_sample=N -> collect N build times in localStorage,
                //reloading between samples; read them with gnrProfiler.samples()
                const m = window.location.search.match(/_bt_sample=(\d+)/);
                if (m) {
                    const samples = JSON.parse(localStorage.getItem('gnr_bt') || '[]');
                    samples.push(Math.round(api.buildTime));
                    localStorage.setItem('gnr_bt', JSON.stringify(samples));
                    if (samples.length < parseInt(m[1], 10)) {
                        setTimeout(function() { window.location.reload(); }, 500);
                    }
                }
            });
            return result;
        };
    })();

    api.sampleReport = function(topN, clear) {
        const agg = JSON.parse(localStorage.getItem('gnr_prof_agg') || '{}');
        if (clear) {
            localStorage.removeItem('gnr_prof_agg');
        }
        return Object.entries(agg).sort(function(a, b) { return b[1] - a[1]; })
                     .slice(0, topN || 40);
    };

    api.totalReport = function(topN, clear) {
        const totals = JSON.parse(localStorage.getItem('gnr_prof_tot') || '{}');
        if (clear) {
            localStorage.removeItem('gnr_prof_tot');
        }
        return Object.entries(totals).sort(function(a, b) { return b[1] - a[1]; })
                     .slice(0, topN || 40);
    };

    api.samples = function(clear) {
        const samples = JSON.parse(localStorage.getItem('gnr_bt') || '[]');
        if (clear) {
            localStorage.removeItem('gnr_bt');
        }
        return samples;
    };

    return api;
})();
