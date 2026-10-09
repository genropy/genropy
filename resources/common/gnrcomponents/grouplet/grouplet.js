var gnr_grouplet = {
    wizardNext: function(sourceNode, frameCode) {
        var formId = frameCode + '_step_form';
        var form = genro.formById(formId);
        var that = this;
        if (!form) {
            this.wizardStepForward(frameCode);
            return;
        }
        if (!form.isValid()) {
            genro.publish('floating_message', {
                message: _T('!!Please complete required fields'),
                messageType: 'warning'
            });
            return;
        }
        if (!form.changed) {
            this.wizardStepForward(frameCode);
            return;
        }
        form.save({onReload: function() {
            that.wizardStepForward(frameCode);
        }});
    },

    // a groupletChoice inside a wizard step: the step form is <frameCode>_step_form
    choiceNext: function(sourceNode) {
        var match = /^(.+)_step_form$/.exec(sourceNode.form ? sourceNode.form.formId : '');
        if (match) {
            setTimeout(function() { gnr_grouplet.wizardNext(sourceNode, match[1]); }, 1);
        }
    },

    wizardStepForward: function(frameCode) {
        var frameNode = genro.getFrameNode(frameCode);
        var idx = frameNode.getRelativeData('.step_index');
        var steps = frameNode.getRelativeData('.wizard_steps');
        var nodes = steps.getNodes();
        var currentNode = nodes[idx];
        var isLast = idx >= nodes.length - 1;
        if (!isLast) {
            this._wizardSetStepName(frameNode, idx + 1, true);
        }
        // lazySave: a silent save, no 'saved' toast on every page. On a saved
        // record it reloads nothing, so no load consumes wizard_saved_pkey.
        var mainForm = frameNode.form;
        var inserting = false;
        if (!isLast && mainForm && currentNode && this._wizardSavesOn(frameNode, currentNode.label)) {
            var isNew = mainForm.isNewRecord();
            var clearMark = isNew ? null : function() {
                frameNode.setRelativeData('.wizard_saved_pkey', null);
            };
            // An insert reloads the form with its pkey, and that load aborts the
            // step form (genro_frm.js, parentForm onLoaded): the screen stays
            // locked until the reload, which enters the next step itself.
            var saving = mainForm.lazySave(clearMark, isNew ? {waitingStatus: true} : null);
            inserting = isNew && saving instanceof dojo.Deferred;
        }
        if (currentNode) {
            genro.publish(frameCode + '_step_complete',
                {step_code: currentNode.attr.code});
        }
        if (isLast) {
            genro.publish(frameCode + '_complete');
        } else if (inserting) {
            frameNode.setRelativeData('.wizard_pending_index', idx + 1);
        } else {
            frameNode.setRelativeData('.step_index', idx + 1);
        }
    },

    wizardRegisterStep: function(stepForm) {
        var parentForm = stepForm && stepForm.getParentForm();
        if (parentForm) {
            parentForm.childForms[stepForm.formId] = stepForm;
            // the step edits the parent's record: its dialogs name that record
            stepForm.table_name = parentForm.table_name;
        }
    },

    wizardConfirm: function(frameCode) {
        var mainForm = genro.getFrameNode(frameCode).form;
        var stepForm = genro.formById(frameCode + '_step_form');
        var confirm = function() {
            if (mainForm.opStatus) { return; }
            var node = mainForm.sourceNode;
            mainForm.setDraft(false);
            node.setRelativeData('.wizard_confirming', true);
            mainForm.save({always: true});
            // a save under way ends in onSaved or onSaveFailed: any other
            // outcome saved nothing, so the record is still a draft
            if (mainForm.opStatus != 'saving' && node.getRelativeData('.wizard_confirming')) {
                node.setRelativeData('.wizard_confirming', false);
                mainForm.setDraft(true);
            }
        };
        if (stepForm && !stepForm.isValid()) {
            genro.publish('floating_message', {
                message: _T('!!Please complete required fields'),
                messageType: 'warning'
            });
            return;
        }
        if (stepForm && stepForm.changed) {
            stepForm.save({onReload: confirm});
        } else {
            confirm();
        }
    },

    wizardGoTo: function(sourceNode, targetIdx, frameCode) {
        var frameNode = genro.getFrameNode(frameCode);
        if (frameNode.getRelativeData('.wizard_readonly')) { return; }
        var idx = frameNode.getRelativeData('.step_index');
        var showingSummary = frameNode.getRelativeData('.wizard_showing_summary');
        if (showingSummary) {
            var editable = frameNode.getRelativeData('.summary_editable');
            if (!editable) { return; }
            frameNode.setRelativeData('.wizard_page', 'steps');
            frameNode.setRelativeData('.wizard_showing_summary', false);
        }
        if (targetIdx > idx) {
            if (targetIdx == idx + 1) {
                this.wizardNext(sourceNode, frameCode);
            }
            return;
        }
        if (targetIdx < idx) {
            var formId = frameCode + '_step_form';
            var form = genro.formById(formId);
            if (form && form.changed) {
                form.save();
            }
            this._wizardSetStepName(frameNode, targetIdx);
            frameNode.setRelativeData('.step_index', targetIdx);
        }
    },

    // saveOnNext: true on every step, or the comma-separated names of the steps that save
    _wizardSavesOn: function(sourceNode, stepLabel) {
        var saveOn = sourceNode.getRelativeData('.wizard_save_on_next');
        if (!saveOn) { return false; }
        return saveOn === true || saveOn.split(',').indexOf(stepLabel) >= 0;
    },

    _wizardSetStepName: function(frameNode, idx, advancing) {
        var nodes = frameNode.getRelativeData('.wizard_steps').getNodes();
        var node = nodes[idx];
        frameNode.setRelativeData('.wizard_step_name', node ? node.label : null);
        var field = frameNode.getRelativeData('.wizard_step_field');
        if (!(advancing && field && node && frameNode.form)) { return; }
        var record = frameNode.form.getFormData();
        var stored = record.getItem(field);
        var storedIdx = nodes.findIndex(function(n) { return n.label == stored; });
        if (idx > storedIdx) {
            record.setItem(field, node.label);
        }
    },

    wizardResolveRemote: function(sourceNode, stepLabel) {
        var specs = sourceNode.getRelativeData('.wizard_remote_specs');
        if (!specs) { return; }
        var chosen = {};
        specs.getNodes().forEach(function(n) {
            var a = n.attr;
            if (!(a.name in chosen)) { chosen[a.name] = null; }
            if (!a.step && !chosen[a.name]) { chosen[a.name] = a; }
        });
        specs.getNodes().forEach(function(n) {
            if (n.attr.step && n.attr.step == stepLabel) { chosen[n.attr.name] = n.attr; }
        });
        for (var name in chosen) {
            var a = chosen[name];
            var value = a ? (a.path ? sourceNode.getRelativeData(a.path) : a.value) : null;
            // a copy: setting the Bag itself would move it out of its place
            if (value instanceof gnr.GnrBag) { value = value.deepCopy(); }
            sourceNode.setRelativeData('.wizard_remote.' + name, value);
        }
    },

    wizardUpdateStep: function(sourceNode, idx, completeLabel, frameCode, saveLabel) {
        var steps = sourceNode.getRelativeData('.wizard_steps');
        var nodes = steps.getNodes();
        var node = nodes[idx];
        if (!node) { return; }
        this.wizardResolveRemote(sourceNode, node.label);
        sourceNode.setRelativeData('.current_resource', node.attr.resource);
        sourceNode.setRelativeData('.step_auto_next', !!node.attr.autoNext);
        var isLast = (idx >= nodes.length - 1);
        var nextLabel = isLast ? completeLabel : nodes[idx + 1].attr.grouplet_caption;
        if (!isLast && saveLabel && this._wizardSavesOn(sourceNode, node.label)) {
            nextLabel = saveLabel;
        }
        sourceNode.setRelativeData('.next_label', nextLabel);
        this._updateStepperUI(nodes, idx, frameCode);
    },

    _updateStepperUI: function(nodes, activeIdx, frameCode) {
        for (var i = 0; i < nodes.length; i++) {
            var stepNode = genro.nodeById(frameCode + '_step_' + i);
            if (!stepNode) { continue; }
            var el = stepNode.domNode;
            el.classList.remove('completed', 'active', 'pending');
            var circle = el.querySelector('.wizard_circle');
            if (i < activeIdx) {
                el.classList.add('completed');
                circle.innerHTML = '&#10003;';
            } else if (i === activeIdx) {
                el.classList.add('active');
                circle.textContent = String(i + 1);
            } else {
                el.classList.add('pending');
                circle.textContent = String(i + 1);
            }
            if (i > 0) {
                var connNode = genro.nodeById(frameCode + '_conn_' + i);
                if (connNode) {
                    connNode.domNode.classList.toggle('completed', i <= activeIdx);
                }
            }
        }
    },

    panelCheckMandatory: function(sourceNode, basePath, innerFormId) {
        var menu = sourceNode.getRelativeData('.grouplet_menu');
        var innerForm = innerFormId ? genro.formById(innerFormId) : null;
        var readData = function(location) {
            var path = basePath + '.' + location;
            // the open grouplet's pending edits: an invalid inner form is not flushed into its location
            if (innerForm && innerForm.store && innerForm.status != 'noItem'
                    && innerForm.store.locationpath == sourceNode.absDatapath(path)) {
                return innerForm.getFormData();
            }
            return sourceNode.getRelativeData(path);
        };
        var mandatoryNodes = [];
        var setStatus = function(node, status) {
            if ((node.attr.mandatory_status || null) != status) {
                // _class is what the multibutton reads, mandatory_status the tree's getLabelClass
                node.setAttr({mandatory_status: status, _class: status ? 'grouplet_mandatory_' + status : null},
                             true, true);
            }
        };
        var markBag = function(bag) {
            var anyMissing = false;
            bag.forEach(function(node) {
                var value = node.getValue('static');
                var missing = false;
                if (value instanceof gnr.GnrBag) {
                    missing = markBag(value);
                    setStatus(node, missing ? 'branch' : null);
                } else if (node.attr.mandatory) {
                    var data = readData(node.attr.mandatory_path);
                    missing = node.attr.mandatory.split(',').some(function(field) {
                        return isNullOrBlank(data instanceof gnr.GnrBag ? data.getItem(field.trim()) : null);
                    });
                    setStatus(node, missing ? 'missing' : null);
                    mandatoryNodes.push(node);
                }
                anyMissing = anyMissing || missing;
            }, 'static');
            return anyMissing;
        };
        markBag(menu);
        var form = sourceNode.form;
        // a draft record only signals what is still to complete: it blocks once confirmed.
        // The record value first: setDraft writes it before the _draft attribute isDraft reads
        var draftNode = form ? form.getFormData().getNode('__is_draft') : null;
        var enforced = !(draftNode ? draftNode.getValue() : (form && form.isDraft()));
        sourceNode.setRelativeData('.mandatory_enforced', enforced);
        var rootNode = sourceNode.getParentNode();
        if (rootNode) {
            genro.dom.setClass(rootNode, 'grouplet_mandatory_draft', !enforced);
        }
        if (!form) {
            return;
        }
        var applyErrors = function() {
            mandatoryNodes.forEach(function(node) {
                var missing = enforced && node.attr.mandatory_status == 'missing';
                form.setFormError('grouplet_mandatory_' + node.attr.resource.replace(/\W/g, '_'),
                                  missing ? _T('Incomplete group') + ': ' + (node.attr.grouplet_caption || node.label) : false,
                                  false);
            });
        };
        // now, for a save right after setDraft(false); again after the running load, whose reset() clears them
        applyErrors();
        setTimeout(applyErrors, 1);
    },

    panelLeaveGroup: function(sourceNode, resource, formId, onLeave, onStay) {
        var form = formId ? genro.formById(formId) : null;
        if (resource == sourceNode.getRelativeData('.selected_resource') || !form) {
            onLeave();
            return;
        }
        var pendingEditor = form.checkPendingGridEditor();
        if (pendingEditor) {
            // the edited cell reaches the form only when its editor closes, as in form.save
            var that = this;
            sourceNode.watch('grouplet_leave', function() { return !pendingEditor.grid.gnrediting; },
                             function() { that.panelLeaveGroup(sourceNode, resource, formId, onLeave, onStay); });
            return;
        }
        if (!form.changed) {
            onLeave();
            return;
        }
        if (form.isValid()) {
            // saved now, with the current grouplet's locationpath and hooks: the switch replaces them
            form.save();
            onLeave();
            return;
        }
        onStay();
        genro.dlg.ask(_T('Invalid changes'), 'The current group has invalid changes.',
                      {discard: _T('Discard and continue'), cancel: _T('Cancel')},
                      {discard: function() {
                          form.reload({discardChanges: true});
                          onLeave(true);
                      }});
    },

    panelTreeClick: function(sourceNode, treeNode, formId) {
        var item = treeNode.item;
        var itemInfo = item.attr;
        if (!itemInfo.resource || !itemInfo.grouplet_caption) {
            return;
        }
        var tree = sourceNode.widget;
        var currentNode = tree.currentSelectedNode;
        this.panelLeaveGroup(sourceNode, itemInfo.resource, formId, function(discarded) {
            if (discarded) {
                tree.setSelected(treeNode);
            }
            sourceNode.setRelativeData('.grouplet_info', new gnr.GnrBag(itemInfo), null, false, false);
            sourceNode.setRelativeData('.selected_resource', itemInfo.resource, null, false, false);
            sourceNode.setRelativeData('.selected_caption', itemInfo.grouplet_caption);
            sourceNode.setRelativeData('.selected_fullpath', item.getFullpath());
        }, function() {
            // the tree selects the clicked node after its onClick handlers
            setTimeout(function() { tree.setSelected(currentNode); }, 1);
        });
    },

    panelStart: function(sourceNode, startResource, mode) {
        // the group the panel opens on: true for the first leaf, or a resource path
        var menu = sourceNode.getRelativeData('.grouplet_menu');
        if (!menu || sourceNode.getRelativeData('.selected_resource')) {
            return;
        }
        var node = null;
        if (startResource === true) {
            menu.walk(function(n) {
                if (!node && n.attr.grouplet_caption) {
                    node = n;
                }
            }, 'static');
        } else {
            node = menu.getNodeByAttr('resource', startResource);
        }
        if (!node) {
            return;
        }
        if (mode == 'topic') {
            sourceNode.setRelativeData('.selected_code', node.label);
            return;
        }
        sourceNode.setRelativeData('.grouplet_info', new gnr.GnrBag(node.attr), null, false, false);
        sourceNode.setRelativeData('.selected_resource', node.attr.resource, null, false, false);
        sourceNode.setRelativeData('.selected_caption', node.attr.grouplet_caption);
        sourceNode.setRelativeData('.selected_fullpath', node.getFullpath());
        sourceNode.setRelativeData('.selected_treepath', node.getFullpath(null, menu));
    },

    panelSelectFromCode: function(sourceNode, code, formId) {
        var menu = sourceNode.getRelativeData('.grouplet_menu');
        var node = code ? menu.getNode(code) : null;
        if (!node) {
            return;
        }
        var currentResource = sourceNode.getRelativeData('.selected_resource');
        this.panelLeaveGroup(sourceNode, node.attr.resource, formId, function(discarded) {
            sourceNode.setRelativeData('.grouplet_info', new gnr.GnrBag(node.attr));
            sourceNode.setRelativeData('.selected_resource', node.attr.resource);
            if (discarded) {
                sourceNode.setRelativeData('.selected_code', code);
            }
        }, function() {
            var currentNode = menu.getNodeByAttr('resource', currentResource);
            setTimeout(function() {
                sourceNode.setRelativeData('.selected_code', currentNode ? currentNode.label : null);
            }, 1);
        });
    }
};
