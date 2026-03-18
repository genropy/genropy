var gnr_grouplet = {
    wizardNext: function(sourceNode, frameCode) {
        var formId = frameCode + '_step_form';
        var form = genro.formById(formId);
        if (form && !form.isValid()) {
            genro.publish('floating_message', {
                message: 'Please complete required fields',
                messageType: 'warning'
            });
            return;
        }
        if (form) {
            form.save();
        }
        var frameNode = genro.getFrameNode(frameCode);
        var idx = frameNode.getRelativeData('.step_index');
        var steps = frameNode.getRelativeData('.wizard_steps');
        var nodes = steps.getNodes();
        var currentNode = nodes[idx];
        if (currentNode) {
            genro.publish(frameCode + '_step_complete',
                {step_code: currentNode.attr.code});
        }
        if (idx >= nodes.length - 1) {
            genro.publish(frameCode + '_complete');
        } else {
            frameNode.setRelativeData('.step_index', idx + 1);
        }
    },

    wizardGoTo: function(sourceNode, targetIdx, frameCode) {
        var frameNode = genro.getFrameNode(frameCode);
        var idx = frameNode.getRelativeData('.step_index');
        if (targetIdx < idx) {
            var formId = frameCode + '_step_form';
            var form = genro.formById(formId);
            if (form) {
                form.save();
            }
            frameNode.setRelativeData('.step_index', targetIdx);
        }
    },

    wizardUpdateStep: function(sourceNode, idx, completeLabel, frameCode) {
        var steps = sourceNode.getRelativeData('.wizard_steps');
        var nodes = steps.getNodes();
        var node = nodes[idx];
        if (!node) { return; }
        sourceNode.setRelativeData('.current_resource', node.attr.resource);
        var isLast = (idx >= nodes.length - 1);
        sourceNode.setRelativeData('.next_label',
            isLast ? completeLabel : nodes[idx + 1].attr.grouplet_caption);
        for (var i = 0; i < nodes.length; i++) {
            var stepNode = genro.nodeById(frameCode + '_step_' + i);
            if (!stepNode) { continue; }
            var el = stepNode.domNode;
            el.classList.remove('completed', 'active', 'pending');
            var circle = el.querySelector('.wizard_circle');
            if (i < idx) {
                el.classList.add('completed');
                circle.innerHTML = '&#10003;';
            } else if (i === idx) {
                el.classList.add('active');
                circle.textContent = String(i + 1);
            } else {
                el.classList.add('pending');
                circle.textContent = String(i + 1);
            }
            if (i > 0) {
                var connNode = genro.nodeById(frameCode + '_conn_' + i);
                if (connNode) {
                    connNode.domNode.classList.toggle('completed', i <= idx);
                }
            }
        }
    },

    toggleGroupletCell: function(cellEl) {
        var content = cellEl.querySelector('.grouplet_topic_cell_content');
        if (!content) { return; }
        if (cellEl.classList.contains('collapsed')) {
            cellEl.classList.remove('collapsed');
            content.style.maxHeight = content.scrollHeight + 'px';
            var onExpanded = function() {
                content.style.maxHeight = '';
                content.removeEventListener('transitionend', onExpanded);
            };
            content.addEventListener('transitionend', onExpanded);
        } else {
            content.style.maxHeight = content.scrollHeight + 'px';
            content.offsetHeight; // force reflow
            content.style.maxHeight = '0';
            cellEl.classList.add('collapsed');
        }
    },

    panelSelectFromCode: function(sourceNode, code) {
        if (code) {
            var menu = sourceNode.getRelativeData('.grouplet_menu');
            var node = menu.getNode(code);
            if (node) {
                var meta = new gnr.GnrBag();
                meta.setItem('locationpath', node.attr.locationpath || null);
                meta.setItem('resource', node.attr.resource);
                sourceNode.setRelativeData('.grouplet_meta', meta);
                sourceNode.setRelativeData('.selected_resource', node.attr.resource);
            }
        }
    }
};
