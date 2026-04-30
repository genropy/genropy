/*-*- coding: utf-8 -*-
 *--------------------------------------------------------------------------
 * package            : Genropy clientside
 * module genro_cmd   : Unified client-side command catalog
 *
 * Exposes a single namespace `genro.cmd` collecting the framework's
 * core client-side capabilities (open page, run batch, show dialog,
 * save form, ...). Every command is a thin wrapper over an existing
 * primitive and carries an explicit machine-readable schema, so that
 * the catalog is introspectable at runtime via:
 *
 *     genro.cmd.list()           -> array of {name, category, description, params, returns}
 *     genro.cmd.toolsManifest()  -> Anthropic tool-use compatible array
 *
 * Three equivalent invocation channels are supported:
 *   1. Direct JS:   genro.cmd.openPageInTab({pageName, file})
 *   2. Pub/sub:     genro.publish('gnrcmd', {command: 'openPageInTab', pageName, file})
 *   3. Datachange:  genro.setData('gnr.gnrcmd', {command: 'openPageInTab', pageName, file})
 *--------------------------------------------------------------------------
 */

dojo.declare('gnr.GnrCmd', null, {

    constructor: function(genro) {
        this.genro = genro;
        this._registerDispatchers();
    },

    _registerDispatchers: function() {
        var self = this;
        dojo.subscribe('gnrcmd', function(kw) {
            self._dispatch(kw || {});
        });
        this.genro.dataSubscribe('gnr.gnrcmd', 'gnrcmd_dispatcher', {
            any: function() {
                var payload = self.genro.getData('gnr.gnrcmd');
                if (payload) self._dispatch(payload);
            }
        });
    },

    _dispatch: function(payload) {
        var command = payload.command;
        if (!command) {
            console.error('[gnrcmd] missing "command" key in payload', payload);
            return;
        }
        var fn = this[command];
        if (typeof fn !== 'function' || !fn.schema) {
            console.error('[gnrcmd] unknown command:', command);
            return;
        }
        var params = {};
        for (var k in payload) {
            if (k !== 'command') params[k] = payload[k];
        }
        try {
            this._validateParams(command, params);
        } catch (e) {
            console.error('[gnrcmd] validation error for ' + command + ':', e.message);
            throw e;
        }
        return fn.call(this, params);
    },

    _validateParams: function(cmdName, params) {
        var schema = this[cmdName].schema;
        var spec = schema.params || {};
        for (var pname in spec) {
            var pdef = spec[pname];
            var hasIt = (params[pname] !== undefined && params[pname] !== null);
            if (pdef.required && !hasIt) {
                throw new Error('missing required param "' + pname + '"');
            }
            if (hasIt && pdef.type) {
                var actual = (params[pname] instanceof Array) ? 'array' : typeof params[pname];
                var expected = pdef.type;
                if (expected === 'array' && actual !== 'array') {
                    throw new Error('param "' + pname + '" expected array, got ' + actual);
                }
                if (expected !== 'array' && expected !== 'object' && actual !== expected) {
                    throw new Error('param "' + pname + '" expected ' + expected + ', got ' + actual);
                }
            }
        }
    },

    list: function() {
        var out = [];
        for (var k in this) {
            var fn = this[k];
            if (typeof fn === 'function' && fn.schema) {
                out.push({
                    name: fn.schema.name,
                    category: fn.schema.category,
                    description: fn.schema.description,
                    params: fn.schema.params,
                    returns: fn.schema.returns
                });
            }
        }
        return out;
    },

    toolsManifest: function() {
        var tools = [];
        var entries = this.list();
        for (var i = 0; i < entries.length; i++) {
            var e = entries[i];
            var properties = {};
            var required = [];
            for (var pname in (e.params || {})) {
                var pdef = e.params[pname];
                properties[pname] = {
                    type: pdef.type || 'string',
                    description: pdef.description || ''
                };
                if (pdef.required) required.push(pname);
            }
            tools.push({
                name: e.name,
                description: e.description + (e.returns ? ' Returns: ' + (e.returns.description || e.returns.type) : ''),
                input_schema: {
                    type: 'object',
                    properties: properties,
                    required: required
                }
            });
        }
        return tools;
    },

    /* ============================================================
     * helpers (private)
     * ============================================================ */

    _requireForm: function(formId) {
        var form = this.genro.getForm(formId);
        if (!form) throw new Error('form not found: ' + formId);
        return form;
    },

    _requireWidget: function(widgetId) {
        var w = this.genro.wdgById(widgetId);
        if (!w) throw new Error('widget not found: ' + widgetId);
        return w;
    },

    _requireNode: function(nodeId) {
        var n = this.genro.nodeById(nodeId);
        if (!n) throw new Error('node not found: ' + nodeId);
        return n;
    },

    /* ============================================================
     * Navigation
     * ============================================================ */

    openPageInTab: function(p) {
        return this.genro.framedIndexManager.newBrowserWindowPage({
            pageName: p.pageName, file: p.file, label: p.label
        });
    },

    openPageInWindow: function(p) {
        return this.genro.openWindow(p.url, p.target || '_blank', p.features);
    },

    openPageInDialog: function(p) {
        return this.genro.dlg.iframeDialog({
            url: p.url, title: p.title, width: p.width, height: p.height
        });
    },

    gotoURL: function(p) {
        return this.genro.gotoURL(p.url, p.target);
    },

    pageReload: function() {
        return this.genro.pageReload();
    },

    pageBack: function() {
        if (window.history && window.history.back) window.history.back();
    },

    /* ============================================================
     * Dialogs / Messages
     * ============================================================ */

    alert: function(p) {
        return this.genro.dlg.alert(p.message, p.title);
    },

    ask: function(p) {
        return this.genro.dlg.ask(p.message, p.title, p['default']);
    },

    prompt: function(p) {
        return this.genro.dlg.prompt(p.message, p.title, p['default']);
    },

    confirm: function(p) {
        return this.genro.dlg.ask(p.message, p.title);
    },

    notify: function(p) {
        this.genro.publish('floating_message', {
            message: p.message,
            messageType: p.type || 'info',
            duration: p.duration
        });
    },

    lockScreen: function(p) {
        return this.genro.lockScreen(p.message, p.timeout);
    },

    unlockScreen: function() {
        return this.genro.unlockScreen ? this.genro.unlockScreen() : null;
    },

    /* ============================================================
     * Forms
     * ============================================================ */

    formNewRecord: function(p) {
        var form = this._requireForm(p.formId);
        return form.newrecord ? form.newrecord(p.defaults) : form.handlers.newrecord(p.defaults);
    },

    formLoadRecord: function(p) {
        var form = this._requireForm(p.formId);
        return form.load ? form.load(p.pkey) : form.handlers.load(p.pkey);
    },

    formSave: function(p) {
        var form = this._requireForm(p.formId);
        return form.save ? form.save() : form.handlers.save();
    },

    formDelete: function(p) {
        var form = this._requireForm(p.formId);
        return form.deleteItem ? form.deleteItem(p.pkey) : form.handlers.del(p.pkey);
    },

    formAbort: function(p) {
        var form = this._requireForm(p.formId);
        return form.abort ? form.abort() : null;
    },

    formReload: function(p) {
        var form = this._requireForm(p.formId);
        return form.reload ? form.reload() : null;
    },

    formGetData: function(p) {
        this._requireForm(p.formId);
        return this.genro.getFormData(p.formId);
    },

    /* ============================================================
     * Grids
     * ============================================================ */

    gridRefresh: function(p) {
        var w = this._requireWidget(p.gridId);
        if (w.reload) return w.reload();
        if (w.refresh) return w.refresh();
        throw new Error('grid does not support refresh: ' + p.gridId);
    },

    gridGetSelected: function(p) {
        var w = this._requireWidget(p.gridId);
        if (w.getSelectedPkeys) return w.getSelectedPkeys();
        if (w.getSelected) return w.getSelected();
        throw new Error('grid does not support selection read: ' + p.gridId);
    },

    gridSelectRow: function(p) {
        var w = this._requireWidget(p.gridId);
        if (!w.selectRow) throw new Error('grid does not support row selection: ' + p.gridId);
        return w.selectRow(p.rowIndex);
    },

    gridExport: function(p) {
        var w = this._requireWidget(p.gridId);
        if (!w.exportGrid) throw new Error('grid does not support export: ' + p.gridId);
        return w.exportGrid(p.format || 'xls');
    },

    /* ============================================================
     * Records (table-level)
     * ============================================================ */

    openRecord: function(p) {
        this.genro.publish('open_record', {
            table: p.table, pkey: p.pkey, mode: p.mode || 'dialog'
        });
    },

    newRecord: function(p) {
        this.genro.publish('new_record', {
            table: p.table, defaults: p.defaults, mode: p.mode || 'dialog'
        });
    },

    deleteRecord: function(p) {
        return this.genro.serverCall('app.deleteDbRow', {
            table: p.table, pkey: p.pkey
        });
    },

    /* ============================================================
     * Batch / Resources
     * ============================================================ */

    runBatch: function(p) {
        this.genro.publish('table_script_run', {
            res_type: p.res_type || 'action',
            resource: p.resource,
            table: p.table,
            selectedPkeys: p.selectedPkeys,
            parameters: p.parameters
        });
    },

    runPrint: function(p) {
        this.genro.publish('table_script_run', {
            res_type: 'print',
            resource: p.resource,
            table: p.table,
            selectedPkeys: p.selectedPkeys,
            parameters: p.parameters
        });
    },

    runExport: function(p) {
        this.genro.publish('table_script_run', {
            res_type: 'export',
            resource: p.resource,
            table: p.table,
            selectedPkeys: p.selectedPkeys,
            parameters: p.parameters
        });
    },

    /* ============================================================
     * RPC
     * ============================================================ */

    serverCall: function(p) {
        return this.genro.serverCall(p.method, p.params || {}, p.callback, p.async);
    },

    /* ============================================================
     * Data store
     * ============================================================ */

    setData: function(p) {
        return this.genro.setData(p.path, p.value);
    },

    getData: function(p) {
        return this.genro.getData(p.path);
    },

    resetData: function(p) {
        return this.genro.resetData(p.path);
    },

    /* ============================================================
     * Storage / Preferences
     * ============================================================ */

    setUserPreference: function(p) {
        return this.genro.setUserPreference(p.path, p.value, p.pkg);
    },

    getUserPreference: function(p) {
        return this.genro.userPreference(p.path, p.pkg);
    },

    setAppPreference: function(p) {
        return this.genro.setAppPreference(p.path, p.value, p.pkg);
    },

    getAppPreference: function(p) {
        return this.genro.appPreference(p.path, p.pkg);
    },

    setInStorage: function(p) {
        return this.genro.setInStorage(p.key, p.value, p.scope);
    },

    getFromStorage: function(p) {
        return this.genro.getFromStorage(p.key, p.scope);
    },

    /* ============================================================
     * Files
     * ============================================================ */

    download: function(p) {
        return this.genro.download ? this.genro.download(p.url, p.filename) : this.genro.triggerDownload(p.url, p.filename);
    },

    viewPDF: function(p) {
        return this.genro.viewPDF ? this.genro.viewPDF(p.url, p.title) : this.genro.openWindow(p.url);
    },

    recordToPDF: function(p) {
        return this.genro.recordToPDF ? this.genro.recordToPDF(p.table, p.pkey, p.template) : null;
    },

    /* ============================================================
     * Misc
     * ============================================================ */

    copyToClipboard: function(p) {
        if (this.genro.textToClipboard) return this.genro.textToClipboard(p.text);
        if (navigator.clipboard) return navigator.clipboard.writeText(p.text);
        throw new Error('clipboard not available');
    },

    focusWidget: function(p) {
        var w = this._requireWidget(p.widgetId);
        if (!w.focus) throw new Error('widget does not support focus: ' + p.widgetId);
        return w.focus();
    },

    refreshBadge: function(p) {
        this.genro.publish('refreshBadge', {code: p.code});
    }

});


/* ============================================================
 * Schemas — attached after class declaration
 * ============================================================ */

(function() {
    var P = gnr.GnrCmd.prototype;

    /* --- Navigation --- */

    P.openPageInTab.schema = {
        name: 'openPageInTab', category: 'navigation',
        description: 'Open a webpage as a new tab in the frameindex.',
        params: {
            pageName: {type: 'string', required: true, description: 'Logical page name (used as tab id).'},
            file:     {type: 'string', required: true, description: 'Resource file path (e.g. "myfolder/mypage").'},
            label:    {type: 'string', required: false, description: 'Visible tab label. Defaults to pageName.'}
        },
        returns: {type: 'string', description: 'The pageId assigned to the new tab.'}
    };

    P.openPageInWindow.schema = {
        name: 'openPageInWindow', category: 'navigation',
        description: 'Open a URL in a new browser window or named target.',
        params: {
            url:      {type: 'string', required: true,  description: 'URL to open.'},
            target:   {type: 'string', required: false, description: 'Browser target name. Defaults to "_blank".'},
            features: {type: 'string', required: false, description: 'window.open features string.'}
        },
        returns: {type: 'object', description: 'Reference to the opened window.'}
    };

    P.openPageInDialog.schema = {
        name: 'openPageInDialog', category: 'navigation',
        description: 'Open a webpage inside a modal iframe dialog.',
        params: {
            url:    {type: 'string', required: true,  description: 'URL of the page to embed.'},
            title:  {type: 'string', required: false, description: 'Dialog title.'},
            width:  {type: 'string', required: false, description: 'Dialog width (CSS value).'},
            height: {type: 'string', required: false, description: 'Dialog height (CSS value).'}
        }
    };

    P.gotoURL.schema = {
        name: 'gotoURL', category: 'navigation',
        description: 'Navigate the current window to a URL.',
        params: {
            url:    {type: 'string', required: true,  description: 'Target URL.'},
            target: {type: 'string', required: false, description: 'Optional target frame.'}
        }
    };

    P.pageReload.schema = {
        name: 'pageReload', category: 'navigation',
        description: 'Reload the current page.',
        params: {}
    };

    P.pageBack.schema = {
        name: 'pageBack', category: 'navigation',
        description: 'Navigate back in browser history.',
        params: {}
    };

    /* --- Dialogs / Messages --- */

    P.alert.schema = {
        name: 'alert', category: 'dialog',
        description: 'Show a modal alert dialog.',
        params: {
            message: {type: 'string', required: true,  description: 'Alert message.'},
            title:   {type: 'string', required: false, description: 'Dialog title.'}
        }
    };

    P.ask.schema = {
        name: 'ask', category: 'dialog',
        description: 'Show a yes/no question dialog.',
        params: {
            message:   {type: 'string', required: true,  description: 'Question text.'},
            title:     {type: 'string', required: false, description: 'Dialog title.'},
            'default': {type: 'string', required: false, description: 'Default button.'}
        },
        returns: {type: 'object', description: 'Deferred resolved with user choice.'}
    };

    P.prompt.schema = {
        name: 'prompt', category: 'dialog',
        description: 'Show a prompt dialog asking the user to type a value.',
        params: {
            message:   {type: 'string', required: true,  description: 'Prompt text.'},
            title:     {type: 'string', required: false, description: 'Dialog title.'},
            'default': {type: 'string', required: false, description: 'Default value.'}
        },
        returns: {type: 'object', description: 'Deferred resolved with the typed value.'}
    };

    P.confirm.schema = {
        name: 'confirm', category: 'dialog',
        description: 'Show a confirm dialog (alias of ask without default).',
        params: {
            message: {type: 'string', required: true,  description: 'Confirm text.'},
            title:   {type: 'string', required: false, description: 'Dialog title.'}
        },
        returns: {type: 'object', description: 'Deferred resolved with user choice.'}
    };

    P.notify.schema = {
        name: 'notify', category: 'dialog',
        description: 'Show a non-modal floating notification (toast).',
        params: {
            message:  {type: 'string', required: true,  description: 'Message to display.'},
            type:     {type: 'string', required: false, description: 'Type: info|warning|error|success. Defaults to info.'},
            duration: {type: 'number', required: false, description: 'Duration in milliseconds.'}
        }
    };

    P.lockScreen.schema = {
        name: 'lockScreen', category: 'dialog',
        description: 'Lock the screen showing a busy overlay.',
        params: {
            message: {type: 'string', required: false, description: 'Optional overlay message.'},
            timeout: {type: 'number', required: false, description: 'Auto-unlock timeout in seconds.'}
        }
    };

    P.unlockScreen.schema = {
        name: 'unlockScreen', category: 'dialog',
        description: 'Remove the busy overlay set by lockScreen.',
        params: {}
    };

    /* --- Forms --- */

    P.formNewRecord.schema = {
        name: 'formNewRecord', category: 'form',
        description: 'Start a new record on the given form.',
        params: {
            formId:   {type: 'string', required: true,  description: 'Form id.'},
            defaults: {type: 'object', required: false, description: 'Default values for the new record.'}
        }
    };

    P.formLoadRecord.schema = {
        name: 'formLoadRecord', category: 'form',
        description: 'Load an existing record into the form.',
        params: {
            formId: {type: 'string', required: true, description: 'Form id.'},
            pkey:   {type: 'string', required: true, description: 'Primary key of the record to load.'}
        }
    };

    P.formSave.schema = {
        name: 'formSave', category: 'form',
        description: 'Save the current record on the form.',
        params: {
            formId: {type: 'string', required: true, description: 'Form id.'}
        },
        returns: {type: 'object', description: 'Deferred resolved when save completes.'}
    };

    P.formDelete.schema = {
        name: 'formDelete', category: 'form',
        description: 'Delete the record currently loaded in the form.',
        params: {
            formId: {type: 'string', required: true,  description: 'Form id.'},
            pkey:   {type: 'string', required: false, description: 'Optional pkey override.'}
        }
    };

    P.formAbort.schema = {
        name: 'formAbort', category: 'form',
        description: 'Discard pending changes on the form.',
        params: {
            formId: {type: 'string', required: true, description: 'Form id.'}
        }
    };

    P.formReload.schema = {
        name: 'formReload', category: 'form',
        description: 'Reload the form from the server, dropping local edits.',
        params: {
            formId: {type: 'string', required: true, description: 'Form id.'}
        }
    };

    P.formGetData.schema = {
        name: 'formGetData', category: 'form',
        description: 'Read the current data of the form (record + extra panes).',
        params: {
            formId: {type: 'string', required: true, description: 'Form id.'}
        },
        returns: {type: 'object', description: 'Form data object.'}
    };

    /* --- Grids --- */

    P.gridRefresh.schema = {
        name: 'gridRefresh', category: 'grid',
        description: 'Refresh a grid by reloading its data.',
        params: {
            gridId: {type: 'string', required: true, description: 'Grid widget id.'}
        }
    };

    P.gridGetSelected.schema = {
        name: 'gridGetSelected', category: 'grid',
        description: 'Get the list of selected primary keys in a grid.',
        params: {
            gridId: {type: 'string', required: true, description: 'Grid widget id.'}
        },
        returns: {type: 'array', description: 'Array of pkeys currently selected.'}
    };

    P.gridSelectRow.schema = {
        name: 'gridSelectRow', category: 'grid',
        description: 'Select a row in a grid by index.',
        params: {
            gridId:   {type: 'string', required: true, description: 'Grid widget id.'},
            rowIndex: {type: 'number', required: true, description: 'Zero-based row index.'}
        }
    };

    P.gridExport.schema = {
        name: 'gridExport', category: 'grid',
        description: 'Export grid contents in the requested format.',
        params: {
            gridId: {type: 'string', required: true,  description: 'Grid widget id.'},
            format: {type: 'string', required: false, description: 'Export format (xls|csv|...). Default xls.'}
        }
    };

    /* --- Records --- */

    P.openRecord.schema = {
        name: 'openRecord', category: 'record',
        description: 'Open a record of the given table for view/edit.',
        params: {
            table: {type: 'string', required: true,  description: 'Fully qualified table name (pkg.tbl).'},
            pkey:  {type: 'string', required: true,  description: 'Primary key of the record.'},
            mode:  {type: 'string', required: false, description: 'Display mode: dialog|tab|palette. Default dialog.'}
        }
    };

    P.newRecord.schema = {
        name: 'newRecord', category: 'record',
        description: 'Open a new-record form for the given table.',
        params: {
            table:    {type: 'string', required: true,  description: 'Fully qualified table name (pkg.tbl).'},
            defaults: {type: 'object', required: false, description: 'Default field values.'},
            mode:     {type: 'string', required: false, description: 'Display mode: dialog|tab|palette. Default dialog.'}
        }
    };

    P.deleteRecord.schema = {
        name: 'deleteRecord', category: 'record',
        description: 'Delete a record from the database.',
        params: {
            table: {type: 'string', required: true, description: 'Fully qualified table name (pkg.tbl).'},
            pkey:  {type: 'string', required: true, description: 'Primary key of the record to delete.'}
        }
    };

    /* --- Batch / Resources --- */

    P.runBatch.schema = {
        name: 'runBatch', category: 'batch',
        description: 'Run a batch action resource on a set of records.',
        params: {
            resource:      {type: 'string', required: true,  description: 'Resource path (e.g. "myaction").'},
            table:         {type: 'string', required: true,  description: 'Target table.'},
            selectedPkeys: {type: 'array',  required: false, description: 'Pkeys to operate on. Empty = all.'},
            parameters:    {type: 'object', required: false, description: 'Action parameters.'},
            res_type:      {type: 'string', required: false, description: 'Resource type. Default "action".'}
        }
    };

    P.runPrint.schema = {
        name: 'runPrint', category: 'batch',
        description: 'Run a print resource on a set of records.',
        params: {
            resource:      {type: 'string', required: true,  description: 'Print resource path.'},
            table:         {type: 'string', required: true,  description: 'Target table.'},
            selectedPkeys: {type: 'array',  required: false, description: 'Pkeys to print.'},
            parameters:    {type: 'object', required: false, description: 'Print parameters.'}
        }
    };

    P.runExport.schema = {
        name: 'runExport', category: 'batch',
        description: 'Run an export resource on a set of records.',
        params: {
            resource:      {type: 'string', required: true,  description: 'Export resource path.'},
            table:         {type: 'string', required: true,  description: 'Target table.'},
            selectedPkeys: {type: 'array',  required: false, description: 'Pkeys to export.'},
            parameters:    {type: 'object', required: false, description: 'Export parameters.'}
        }
    };

    /* --- RPC --- */

    P.serverCall.schema = {
        name: 'serverCall', category: 'rpc',
        description: 'Invoke an RPC method on the server (rpc_*, _table.*, plugin.*).',
        params: {
            method:   {type: 'string',  required: true,  description: 'Method name (e.g. "rpc_doSomething" or "_table.foo.bar.method").'},
            params:   {type: 'object',  required: false, description: 'Method parameters.'},
            callback: {type: 'object',  required: false, description: 'Callback function (rarely used from outside JS).'},
            async:    {type: 'boolean', required: false, description: 'Async flag.'}
        },
        returns: {type: 'object', description: 'Deferred resolved with the RPC result.'}
    };

    /* --- Data store --- */

    P.setData.schema = {
        name: 'setData', category: 'data',
        description: 'Write a value into the client datastore at the given path.',
        params: {
            path:  {type: 'string', required: true, description: 'Datastore path (e.g. "gnr.foo.bar").'},
            value: {type: 'object', required: true, description: 'Value to set (any type).'}
        }
    };

    P.getData.schema = {
        name: 'getData', category: 'data',
        description: 'Read a value from the client datastore.',
        params: {
            path: {type: 'string', required: true, description: 'Datastore path.'}
        },
        returns: {type: 'object', description: 'Value at the given path.'}
    };

    P.resetData.schema = {
        name: 'resetData', category: 'data',
        description: 'Clear the value at a datastore path.',
        params: {
            path: {type: 'string', required: true, description: 'Datastore path.'}
        }
    };

    /* --- Storage / Preferences --- */

    P.setUserPreference.schema = {
        name: 'setUserPreference', category: 'preferences',
        description: 'Write a user-scoped preference value.',
        params: {
            path:  {type: 'string', required: true,  description: 'Preference path.'},
            value: {type: 'object', required: true,  description: 'Value to store.'},
            pkg:   {type: 'string', required: false, description: 'Owner package.'}
        }
    };

    P.getUserPreference.schema = {
        name: 'getUserPreference', category: 'preferences',
        description: 'Read a user-scoped preference value.',
        params: {
            path: {type: 'string', required: true,  description: 'Preference path.'},
            pkg:  {type: 'string', required: false, description: 'Owner package.'}
        },
        returns: {type: 'object', description: 'Preference value.'}
    };

    P.setAppPreference.schema = {
        name: 'setAppPreference', category: 'preferences',
        description: 'Write an app-scoped preference value (admin).',
        params: {
            path:  {type: 'string', required: true,  description: 'Preference path.'},
            value: {type: 'object', required: true,  description: 'Value to store.'},
            pkg:   {type: 'string', required: false, description: 'Owner package.'}
        }
    };

    P.getAppPreference.schema = {
        name: 'getAppPreference', category: 'preferences',
        description: 'Read an app-scoped preference value.',
        params: {
            path: {type: 'string', required: true,  description: 'Preference path.'},
            pkg:  {type: 'string', required: false, description: 'Owner package.'}
        },
        returns: {type: 'object', description: 'Preference value.'}
    };

    P.setInStorage.schema = {
        name: 'setInStorage', category: 'preferences',
        description: 'Write a value in the browser storage.',
        params: {
            key:   {type: 'string', required: true,  description: 'Storage key.'},
            value: {type: 'object', required: true,  description: 'Value to store.'},
            scope: {type: 'string', required: false, description: 'Storage scope: local|session.'}
        }
    };

    P.getFromStorage.schema = {
        name: 'getFromStorage', category: 'preferences',
        description: 'Read a value from the browser storage.',
        params: {
            key:   {type: 'string', required: true,  description: 'Storage key.'},
            scope: {type: 'string', required: false, description: 'Storage scope: local|session.'}
        },
        returns: {type: 'object', description: 'Stored value.'}
    };

    /* --- Files --- */

    P.download.schema = {
        name: 'download', category: 'file',
        description: 'Trigger a file download.',
        params: {
            url:      {type: 'string', required: true,  description: 'File URL.'},
            filename: {type: 'string', required: false, description: 'Suggested filename.'}
        }
    };

    P.viewPDF.schema = {
        name: 'viewPDF', category: 'file',
        description: 'Open a PDF in a viewer.',
        params: {
            url:   {type: 'string', required: true,  description: 'PDF URL.'},
            title: {type: 'string', required: false, description: 'Window title.'}
        }
    };

    P.recordToPDF.schema = {
        name: 'recordToPDF', category: 'file',
        description: 'Render a record using a print template and open the resulting PDF.',
        params: {
            table:    {type: 'string', required: true, description: 'Table name.'},
            pkey:     {type: 'string', required: true, description: 'Record pkey.'},
            template: {type: 'string', required: true, description: 'Print template name.'}
        }
    };

    /* --- Misc --- */

    P.copyToClipboard.schema = {
        name: 'copyToClipboard', category: 'misc',
        description: 'Copy a string to the system clipboard.',
        params: {
            text: {type: 'string', required: true, description: 'Text to copy.'}
        }
    };

    P.focusWidget.schema = {
        name: 'focusWidget', category: 'misc',
        description: 'Move keyboard focus to a widget.',
        params: {
            widgetId: {type: 'string', required: true, description: 'Widget id.'}
        }
    };

    P.refreshBadge.schema = {
        name: 'refreshBadge', category: 'misc',
        description: 'Force refresh of a badge counter.',
        params: {
            code: {type: 'string', required: true, description: 'Badge code.'}
        }
    };

})();
