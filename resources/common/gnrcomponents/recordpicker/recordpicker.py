from gnr.core.gnrdecorator import extract_kwargs
from gnr.core.gnrlang import getUuid
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrwebstruct import struct_method


class RecordPicker(BaseComponent):
    js_requires = 'gnrcomponents/recordpicker/recordpicker'
    css_requires = 'gnrcomponents/recordpicker/recordpicker'

    @extract_kwargs(condition=True)
    @struct_method
    def rp_recordPicker(self, pane, checkedId=None, table=None, storepath=None,
                        columns=None, auxColumns=None, hiddenColumns=None,
                        rowcaption=None, condition=None, condition_kwargs=None,
                        template=None, template_resource=None, layout='cards', cols=None,
                        boxHeight=None, emptyMessage='!!No items',
                        preview=False, preview_template=None, preview_resource=None,
                        multiSelect=False, showRadio=False, showSelected=None, maxSelect=None,
                        selectedRecord=None, selectedCaption=None,
                        identifier='_pkey', captionField='caption',
                        limit=30, delay=250, disabled=False, nodeId=None,
                        **kwargs):
        """Search template records and write checked identifiers to a reactive data path."""
        if not isinstance(checkedId, str) or not checkedId.startswith('^'):
            raise ValueError('recordPicker requires a reactive checkedId path')
        if bool(table) == bool(storepath):
            raise ValueError('Specify exactly one of table and storepath')
        if layout not in ('cards', 'list'):
            raise ValueError('Invalid recordPicker layout')
        if cols is not None and (not isinstance(cols, int) or cols < 1):
            raise ValueError('cols must be a positive integer')
        if isinstance(boxHeight, (int, float)) and boxHeight <= 0:
            raise ValueError('boxHeight must be positive')
        if limit < 1 or delay < 0:
            raise ValueError('Invalid recordPicker limit or delay')
        if maxSelect is not None and maxSelect < 1:
            raise ValueError('maxSelect must be positive')
        nodeId = nodeId or 'record_picker_%s' % getUuid()
        config = dict(checkedId=checkedId, table=table, columns=columns,
                      auxColumns=auxColumns, hiddenColumns=hiddenColumns,
                      rowcaption=rowcaption, template=self._rp_template(template, template_resource),
                      previewTemplate=self._rp_template(preview_template, preview_resource),
                      layout=layout, cols=cols, boxHeight=boxHeight, emptyMessage=emptyMessage,
                      preview=preview, multiSelect=multiSelect,
                      showRadio=showRadio, showSelected=multiSelect if showSelected is None else showSelected,
                      maxSelect=maxSelect, identifier=identifier,
                      captionField=captionField,
                      limit=limit, delay=delay, selectedRecord=selectedRecord,
                      selectedCaption=selectedCaption)
        kwargs['_class'] = 'record_picker %s' % kwargs.pop('_class', '')
        root = pane.div(nodeId=nodeId, picker_config=config,
                        onCreated='this.recordPicker = new gnr.RecordPicker(this, widget);',
                        selfsubscribe_reload='this.recordPicker.reload();',
                        **kwargs)
        root.dataController('genro.nodeById(pickerId).recordPicker.setValue(checkedId);',
                            pickerId=nodeId, checkedId=checkedId, _onBuilt=True)
        root.dataController('genro.nodeById(pickerId).recordPicker.setDisabled(disabled);',
                            pickerId=nodeId, disabled=disabled, _onBuilt=True)
        if storepath:
            root.dataController('genro.nodeById(pickerId).recordPicker.setStore(store);',
                                pickerId=nodeId, store='^%s' % storepath.lstrip('^='),
                                _onBuilt=True)
        else:
            root.dataController("""
                genro.nodeById(pickerId).recordPicker.setQuery(
                    objectUpdate({condition:condition}, objectExtract(_kwargs,'condition_*')));
            """, pickerId=nodeId, condition=condition, _onBuilt=True,
                                **{'condition_%s' % k: v for k, v in condition_kwargs.items()})
        return root

    def _rp_template(self, template, resource):
        if template is not None and resource:
            raise ValueError('Specify either an inline template or a template resource')
        if not resource:
            return template
        source, _ = self.loadTemplate(resource, asSource=True)
        if not source:
            raise ValueError('Missing recordPicker template: %s' % resource)
        return source['compiled'] or source['content']

    @struct_method
    def rp_recordPickerButton(self, pane, record=None, placeholder='!!Select a record',
                              template=None, template_resource=None, action=None,
                              disabled=False, nodeId=None, **kwargs):
        """Render a record or placeholder in a button owned by the host page."""
        nodeId = nodeId or 'record_picker_button_%s' % getUuid()
        kwargs['_class'] = 'record_picker_button %s' % kwargs.pop('_class', '')
        root = pane.button(nodeId=nodeId, disabled=disabled, action=action,
                           iconClass='rpb_icon', iconRight=True, showLabel=True, focusOnTab=True,
                           **kwargs)
        root.dataController("""
            var widget = genro.nodeById(buttonId).widget;
            var empty = !record || (record instanceof gnr.GnrBag && !record.len());
            widget.domNode.classList.toggle('rpb_empty', empty);
            widget.setLabel(empty ? dataTemplate('$placeholder', new gnr.GnrBag({placeholder:placeholder || ''})) :
                dataTemplate(template, record));
        """, buttonId=nodeId, record=record, placeholder=placeholder,
                            template=self._rp_template(template, template_resource) or '$caption',
                            _onBuilt=True)
        return root
