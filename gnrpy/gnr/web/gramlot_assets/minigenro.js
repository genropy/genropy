// Copyright 2026 Softwell S.r.l. - SPDX-License-Identifier: LGPL-2.1-or-later
(function () {
    'use strict';
    document.addEventListener('gramlot:application-ready', function (event) {
        const application = event.detail.application;
        const miniGenro = {
            _pageStarted: false,
            publish(topic, ...args) {
                application.publish(typeof topic === 'string' ? topic : topic.topic, ...args);
            },
            resizeAll() { application.render(); },
            checkBeforeUnload() { return undefined; },
            hasPendingChanges() { return false; },
        };
        window.gramlot = application;
        window.genro = miniGenro;
        const receive = function (event) {
            if (event.source !== window.parent || event.origin !== window.location.origin) return;
            const message = event.data;
            if (!message || typeof message !== 'object' || Array.isArray(message)
                || typeof message.topic !== 'string' || !message.topic) return;
            const {topic, ...payload} = message;
            miniGenro.publish(topic, payload);
        };
        window.addEventListener('message', receive);
        window._windowMessageReady = true;
        const dispose = application.dispose.bind(application);
        application.dispose = function () {
            window.removeEventListener('message', receive);
            if (miniGenro.parentIframeSourceNode?._genro === miniGenro) {
                delete miniGenro.parentIframeSourceNode._genro;
            }
            if (window.genro === miniGenro) delete window.genro;
            if (window.gramlot === application) delete window.gramlot;
            window._windowMessageReady = false;
            dispose();
        };
    }, {once: true});
    document.addEventListener('gramlot:content-ready', function () {
        const miniGenro = window.genro;
        miniGenro._pageStarted = true;
        try {
            const sourceNode = window.frameElement?.sourceNode;
            if (!sourceNode || !window.parent.genro) return;
            miniGenro.parentIframeSourceNode = sourceNode;
            miniGenro.parentGenro = window.parent.genro;
            miniGenro.parent_page_id = miniGenro.parentGenro.page_id;
            miniGenro.mainGenroWindow = miniGenro.parentGenro.mainGenroWindow || window.parent;
            sourceNode._genro = miniGenro;
            sourceNode.publish('pageStarted');
        } catch (error) {
            // A page in a cross-origin frame has no legacy parent connection.
        }
    }, {once: true});
}());
