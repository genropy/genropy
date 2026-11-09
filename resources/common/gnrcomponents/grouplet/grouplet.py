import math
import os
import re
from gnr.core.gnrdecorator import extract_kwargs, public_method
from gnr.core.gnrbag import Bag
from gnr.core.gnrdict import dictExtract
from gnr.core.gnrlang import gnrImport
from gnr.core.gnrstring import templateReplace
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrdocumentation import doc_folder
from gnr.web.gnrwebstruct import struct_method

class GroupletHandler(BaseComponent):
    css_requires = 'gnrcomponents/grouplet/grouplet'
    js_requires = 'gnrcomponents/grouplet/grouplet'

    @public_method
    def gr_loadGrouplet(self, pane, resource=None, table=None,
                        handlername=None, valuepath=None,
                        grouplets_root=None,rootTag='div',
                        mandatory_enforced=None, **kwargs):
        grouplets_root = grouplets_root or 'grouplets'
        if not resource:
            if not handlername:
                raise self.exception('generic',
                                     msg='Missing resource or method for handling grouplet')
            handler = self.getPublicMethod('remote', handlername)
            box = pane.contentPane(datapath=valuepath)
            return handler(box, **kwargs)
        # Check if resource is a topic (folder with child grouplets)
        topic_menu = self.gr_getGroupletMenu(table=table, topic=resource,
                                             grouplets_root=grouplets_root)
        if topic_menu:
            return self._loadGroupletTopic(pane, topic_menu,
                                           table=table, valuepath=valuepath,
                                           grouplets_root=grouplets_root,
                                           **kwargs)
        # Single grouplet
        handlername = handlername or 'grouplet_main'
        if ':' not in resource:
            resource = f'{resource}:Grouplet'
        if table:
            mixinedClass = self.mixinTableResource(
                table, f'{grouplets_root}/{resource}', safeMode=True)
        else:
            mixinedClass = self.mixinComponent(f'{grouplets_root}/{resource}')
        grouplet_module = getattr(mixinedClass, '__top_mixined_module', None)
        handler = getattr(self, handlername)
        box_kw = dict(datapath=valuepath, grouplet_module=grouplet_module)
        info_method = getattr(self, '__info__', None)
        info = info_method() if info_method else {}
        grouplet_code = info.get('code')
        if grouplet_code:
            box_kw['grouplet_code'] = grouplet_code
        box = pane.child(rootTag,_class='grouplet_box', **box_kw)
        result = handler(box, **kwargs)
        if info.get('mandatory'):
            self._groupletRequireFields(box, info['mandatory'],
                                        enforced_path=mandatory_enforced)
        return result

    def _groupletRequireFields(self, box, mandatory, enforced_path=None):
        # the widgets bound to the mandatory fields, so the open grouplet shows what its menu entry asks for;
        # in a groupletPanel they are required only while the panel enforces them (not on a draft record)
        values = {f'^.{field.strip()}' for field in mandatory.split(',')}
        notnull = f'^{enforced_path}' if enforced_path else True

        def cb(node):
            if node.attr.get('value') in values and 'validate_notnull' not in node.attr:
                node.attr['validate_notnull'] = notnull
        box.walk(cb)

    def _loadGroupletTopic(self, pane, topic_menu, table=None,
                           valuepath=None, grouplets_root=None,
                           _depth=0, **kwargs):
        grid_kwargs = dictExtract(kwargs, 'grid_', pop=True)
        columns = int(grid_kwargs.pop('columns', 1))
        template_columns = grid_kwargs.pop('template_columns', None)
        collapsible = grid_kwargs.pop('collapsible', columns <= 1)
        locked = (collapsible is False)
        start_open = (collapsible != 'closed')
        direction = grid_kwargs.pop('direction', None)
        if direction is None:
            direction = 'columns' if columns > 1 else 'rows'
        if not template_columns:
            template_columns = f'repeat({columns}, 1fr)' if columns > 1 else '1fr'
        gap = grid_kwargs.pop('gap', '10px')
        grid_class = 'grouplet_topic_grid'
        grid_style = dict(display='grid',
                          grid_template_columns=template_columns,
                          gap=gap)
        if direction == 'columns':
            n_items = len(topic_menu)
            n_rows = math.ceil(n_items / columns) if columns > 1 else n_items
            grid_style['grid_template_rows'] = f'repeat({n_rows}, auto)'
            grid_class += ' grouplet_topic_grid_columns'
        grid = pane.div(
            datapath=valuepath,
            _class=grid_class,
            **grid_style,
            **grid_kwargs)
        minimal = (_depth > 0)
        for node in topic_menu:
            attr = node.attr
            caption_text = (attr.get('grouplet_caption')
                            or attr.get('caption', ''))
            cell = grid.expandbox(
                title=caption_text,
                open=start_open,
                animate=not locked,
                locked=locked or None,
                minimal=minimal or None)
            content = cell.div(_class='grouplet_topic_cell_content')
            if node.value:
                self._loadGroupletTopic(content, node.value,
                                        table=table,
                                        valuepath=f'.{attr.get("topic", node.label)}',
                                        grouplets_root=grouplets_root,
                                        _depth=_depth + 1,
                                        **kwargs)
            else:
                self.gr_loadGrouplet(content, resource=attr['resource'],
                                     table=table,
                                     valuepath=f'.{node.label}',
                                     grouplets_root=grouplets_root,
                                     **kwargs)

    def gr_getTemplatePars(self, resource=None, table=None,
                           grouplets_root=None):
        info = self._gr_resourceInfo(resource=resource, table=table,
                                     grouplets_root=grouplets_root)[0]
        result = {}
        if info.get('template'):
            result['template'] = info['template']
        if info.get('template_virtual_columns'):
            result['virtual_columns'] = info['template_virtual_columns']
        return result

    def _gr_resourceInfo(self, resource=None, table=None, grouplets_root=None):
        """The `__info__` of a grouplet resource (of its topic for a folder)
        and the path of the file declaring it"""
        grouplets_root = grouplets_root or 'grouplets'
        clean_resource = resource.split(':')[0] if ':' in resource else resource
        if '/' in clean_resource:
            parent, name = clean_resource.rsplit('/', 1)
            search_path = f'{grouplets_root}/{parent}'
        else:
            name = clean_resource
            search_path = grouplets_root
        resources = Bag()
        if table:
            pkg, tblname = table.split('.')
            resources.update(self.site.resource_loader.resourcesAtPath(
                page=self, pkg=pkg, path=f'tables/{tblname}/{search_path}'))
            resources.update(self.site.resource_loader.resourcesAtPath(
                page=self, path=f'tables/_packages/{pkg}/{tblname}/{search_path}'))
        else:
            resources.update(self.site.resource_loader.resourcesAtPath(
                page=self, path=search_path))
        node = resources.getNode(name)
        if not node:
            return {}, None
        if node.value:
            children = Bag(node.value)
            info_node = children.getNode('__info__')
            if not info_node:
                return {}, None
            node = info_node
        resmodule = gnrImport(node.attr['abs_path'], avoid_module_cache=True)
        return self._get_raw_info(resmodule), node.attr['abs_path']

    def _gr_cardInfo(self, resource=None, table=None, grouplets_root=None):
        """The card profile a grouplet resource declares: `card=dict(...)` in
        its `__info__`, its `template` as the title of last resort"""
        if not resource:
            return {}
        info, abs_path = self._gr_resourceInfo(resource=resource, table=table,
                                               grouplets_root=grouplets_root)
        card = dict(info.get('card') or {})
        if info.get('template'):
            card.setdefault('template', info['template'])
        if self.inlineDoc:
            card['doc'] = self._gr_cardDocAddress(card.get('doc'), resource=resource, table=table)
        elif card.get('doc'):
            card['doc'] = self._gr_cardDoc(card['doc'], abs_path=abs_path, table=table)
        return card

    def _gr_cardDocAddress(self, doc, resource=None, table=None):
        """With the inlinedoc experimental flag a card's doc is a documentation
        address (sys/ep_doc): the one given, else the resource's own
        `grouplet:<table or package>:<resource>`; False opts out"""
        if doc is False:
            return False
        try:
            doc_folder(doc)
            return doc
        except ValueError:
            if not resource:
                return None
            return f"grouplet:{table or self.package.name}:{resource.split(':')[0]}"

    def _gr_cardDoc(self, doc, abs_path=None, table=None):
        """A doc given as `file:name.html` is read next to the resource (among
        the resources without one), its relative image paths made urls; any
        other doc is the template itself"""
        if not (isinstance(doc, str) and doc.startswith('file:')):
            return doc
        filename = doc[len('file:'):]
        path = os.path.join(os.path.dirname(abs_path), filename) if abs_path \
            else self.getResource(filename)
        if not (path and os.path.isfile(path)):
            raise self.exception('generic', msg=f'grouplet card: doc file {filename} not found')
        with open(path, encoding='utf-8') as f:
            html = f.read()
        folder = os.path.dirname(path)
        pkg = table.split('.')[0] if table else None

        def url(match):
            src = os.path.normpath(os.path.join(folder, match.group(2)))
            return match.group(1) + (self.resolveResourceUri(src, pkg=pkg) or match.group(2))
        return re.sub(r'''(src=["'])(?![a-z]+:|/)([^"']+)''', url, html)

    def _gr_template(self, spec):
        """A row template (title, collapsed card, doc) in the shape the JS
        compiles: a string, or dict(template=, formats=, sums=) where `sums`
        maps a $name to 'path.field', the field summed under the row's path."""
        if not spec:
            return None
        spec = dict(template=spec) if isinstance(spec, str) else dict(spec)
        spec['template'] = self._(spec.get('template') or '')
        return spec

    def _gr_cardForJs(self, card):
        """The profile as the JS reads it: its templates translated, the
        resource `template` as groupletChunk and the entry rows take it"""
        card = dict(card)
        for key in ('titleTemplate',) if self.inlineDoc else ('titleTemplate', 'doc'):
            if card.get(key):
                card[key] = self._gr_template(card[key])
        return card

    @extract_kwargs(grouplet=dict(slice_prefix=False, pop=True), template=True, btn=True)
    @struct_method
    def gr_groupletChunk(self, pane, value=None, template=None, name=None,
                         handler=None, resource=None, table=None,
                         title=None,
                         record_id=None,
                         virtual_columns=None,
                         grouplets_root=None,
                         grouplet_kwargs=None, template_kwargs=None,
                         btn_kwargs=None, **kwargs):
        if resource and not template:
            tpars = self.gr_getTemplatePars(resource=resource, table=table,
                                            grouplets_root=grouplets_root)
            template = tpars.get('template')
            virtual_columns = virtual_columns or tpars.get('virtual_columns')
        root_kw = {}
        if virtual_columns:
            root_kw['_virtual_columns'] = virtual_columns
        btn_kwargs.setdefault('_class', 'iconbox pencil')
        btn_kwargs.setdefault('height', '14px')
        btn_kwargs.setdefault('position', 'absolute')
        btn_kwargs.setdefault('bottom', '2px')
        btn_kwargs.setdefault('right', '2px')
        # 'selectable' re-enables text selection on the summary template
        # (the global reset sets user-select:none on div/span), so read-only
        # content like an IBAN or code can be copied from the chunk.
        kwargs.setdefault('_class', 'grouplet_chunk_box selectable')
        grid_kw = dictExtract(kwargs, 'grid_', pop=True)
        if record_id is not None:
            # in record mode the chunk gets its own workspace, so the loaded record lives
            # in an isolated (gnr.workspace) scope, never in the caller datapath.
            kwargs['_workspace'] = f'grplt_{name}'
        root = pane.div(**kwargs)
        template_kwargs['template'] = template
        if record_id is not None:
            # RECORD MODE (no surrounding form): the record is loaded into the component's
            # own WORKSPACE (isolated from the caller datapath, so it can never pollute a
            # form record) which feeds the templatechunk. record_id (a pkey or a reactive
            # path) is resolved in the caller scope. The pencil opens recordDataEditor, which
            # loads by pkey and saves the record directly (store_handler='record');
            # onSavedCb bumps the reload trigger so the summary refreshes after save.
            root.dataRecord('#WORKSPACE.record', table=table, pkey=record_id,
                            _onBuilt=True, _fired='^#WORKSPACE.reload')
            template_kwargs['datasource'] = '^#WORKSPACE.record'
        else:
            template_kwargs['datasource'] = value
        root.div(**template_kwargs)  # templatechunk
        btn = root.lightButton(**btn_kwargs)
        if resource:
            grouplet_kwargs['resource'] = resource
        if table:
            grouplet_kwargs['table'] = table
        if title:
            grouplet_kwargs['title'] = title
        if handler:
            grouplet_kwargs['handler'] = handler
        if grouplets_root:
            grouplet_kwargs['grouplets_root'] = grouplets_root
        for k, v in grid_kw.items():
            grouplet_kwargs[f'grouplet_remote_grid_{k}'] = v
        if record_id is not None:
            # editor pkey read at click (= binding) when record_id is a reactive path, so
            # the button controller does not subscribe to it; a literal pkey passes through.
            grouplet_kwargs['pkey'] = (f'={record_id[1:]}'
                                       if isinstance(record_id, str) and record_id.startswith('^')
                                       else record_id)
            grouplet_kwargs['storeType'] = 'Item'
            btn.dataController("""
                var _bnode = this;
                let editor_kw = {..._kwargs};
                editor_kw.onSavedCb = function(){_bnode.setRelativeData('#WORKSPACE.reload', new Date().getTime());};
                genro.dlg.recordDataEditor(name, editor_kw, this);
            """, name=name, **grouplet_kwargs)
        else:
            grouplet_kwargs['value'] = value.replace('^', '')
            btn.dataController("""
                let editor_kw = {..._kwargs};
                genro.dlg.memoryDataEditor(name,editor_kw,this);
            """, name=name, **grouplet_kwargs)
        return root

    @struct_method
    def gr_groupletChoice(self, pane, field=None, table=None, columns=None, where=None,
                          order_by=None, rows=None, value_column='pkey', glyph=None,
                          title=None, note=None, caption_field=None, groups=None,
                          autoNext=True, validate_notnull=True, **kwargs):
        """Tiles that set `field` to one value of `rows` (or of a query on `table`,
        kwargs are its parameters). glyph, title and note: a column, a $template
        or a callable(row). groups: dicts of caption, condition(row), _class and
        tint (a CSS colour washed over the tiles' background).
        In a wizard step a click also advances it (autoNext). validate_notnull
        False leaves the choice optional."""
        if rows is None:
            rows = self.db.table(table).query(columns=columns or '*', where=where,
                                              order_by=order_by, **kwargs).fetch()

        def render(spec, row):
            if callable(spec):
                return spec(row)
            return templateReplace(spec, row) if '$' in spec else row.get(spec)

        action = f'SET .{field} = _choice;'
        if caption_field:
            action += f' SET .{caption_field} = _caption;'
        if autoNext:
            action += ' gnr_grouplet.choiceNext(this);'
        box = pane.div(_class='grouplet_choice')
        for group in groups or [{}]:
            condition = group.get('condition')
            if group.get('caption'):
                box.div(group['caption'], _class='grouplet_choice_separator')
            tiles_kw = dict(style=f"--grouplet-choice-tint: {group['tint']}") if group.get('tint') else {}
            tiles = box.div(_class='grouplet_choice_tiles', **tiles_kw)
            for row in rows:
                if condition and not condition(row):
                    continue
                value = row[value_column]
                caption = render(title, row) if title else value
                tile = tiles.lightButton(action=action, _choice=value, _caption=caption,
                                         _class=' '.join(filter(None, ['grouplet_choice_tile',
                                                                       group.get('_class')])))
                tile.dataController("genro.dom.setClass(this.getParentNode(), 'grouplet_choice_selected', current == _choice);",
                                    current=f'^.{field}', _choice=value, _onBuilt=True)
                if glyph:
                    tile.div(render(glyph, row), _class='grouplet_choice_glyph')
                text = tile.div(_class='grouplet_choice_text')
                text.div(caption, _class='grouplet_choice_title')
                if note:
                    text.div(render(note, row), _class='grouplet_choice_note')
        # without the attribute a grouplet's __info__ mandatory can still require it
        notnull_kw = dict(validate_notnull=validate_notnull) if validate_notnull else {}
        box.textbox(value=f'^.{field}', hidden=True, **notnull_kw)
        return box

    @extract_kwargs(grouplet=dict(slice_prefix=False, pop=True))
    @struct_method
    def gr_groupletPanel(self, pane, table=None, topic=None, value=None,
                         frameCode=None, grouplets_root=None,
                         useForm=True, useRecordPath=False,
                         menuCallback=None, startResource=None,
                         grouplet_kwargs=None, **kwargs):
        # startResource: the group the panel opens on instead of an empty pane — True for the
        # first leaf of the menu, or a resource path ('topic/grouplet')
        frameCode = frameCode or 'grplt_panel'
        if useRecordPath:
            grouplet_kwargs['formDatapath'] = '.record'
        if useForm:
            formId = f'{frameCode}_grpform'
            grouplet_kwargs.update(resource='^#ANCHOR.selected_resource',
                                   value=value,
                                   dynamicLocationPath=True,
                                   loadingGrouplet_locationpath='=#ANCHOR.grouplet_info.locationpath',
                                   loadingGrouplet_onSaving='=#ANCHOR.grouplet_info.onSaving',
                                   loadingGrouplet_onLoading='=#ANCHOR.grouplet_info.onLoading',
                                   formId=formId,
                                   store_autoSave=1)
        else:
            formId = None
            grouplet_kwargs.update(resource='^#ANCHOR.selected_resource',
                                   value=value)
        if table:
            grouplet_kwargs['table'] = table
        if grouplets_root:
            grouplet_kwargs['grouplets_root'] = grouplets_root
        grouplet_kwargs['rootTag'] = 'contentPane'
        if menuCallback:
            menu = menuCallback(table=table, topic=topic,
                                grouplets_root=grouplets_root)
        else:
            menu = self.gr_getGroupletMenu(table=table, topic=topic,
                                           grouplets_root=grouplets_root)
        remote_prefix = 'grouplet_remote_' if useForm else 'remote_'
        mandatory_locations = self._groupletPanel_mandatoryPaths(menu, topic=topic)
        if mandatory_locations:
            grouplet_kwargs[f'{remote_prefix}mandatory_enforced'] = '#ANCHOR.mandatory_enforced'
        if topic:
            grouplet_kwargs[f'{remote_prefix}topic'] = topic
            root = self._groupletPanel_topic(
                pane, menu, frameCode=frameCode, formId=formId,
                useForm=useForm,
                grouplet_kwargs=grouplet_kwargs, **kwargs)
        else:
            root = self._groupletPanel_tree(
                pane, menu, frameCode=frameCode, formId=formId,
                useForm=useForm,
                grouplet_kwargs=grouplet_kwargs, **kwargs)
        if startResource:
            root.dataController("gnr_grouplet.panelStart(this, startResource, mode);",
                                startResource=startResource,
                                mode='topic' if topic else 'tree', _onBuilt=100)
        if mandatory_locations and value:
            base = value.lstrip('^=')
            triggers = {f'mandatory_{i}': f'^{base}.{location}'
                        for i, location in enumerate(sorted(mandatory_locations))}
            if formId:
                # the open grouplet's edits, also those an invalid inner form keeps from its location
                inner_datapath = (grouplet_kwargs.get('grouplet_datapath') or grouplet_kwargs.get('datapath')
                                  or f'gnr.grouplet_{formId}')
                inner_record = (grouplet_kwargs.get('grouplet_formDatapath') or grouplet_kwargs.get('formDatapath')
                                or '.record')
                triggers['inner_record'] = f'^{inner_datapath}{inner_record}'
            root.dataController(
                "gnr_grouplet.panelCheckMandatory(this, basePath, innerFormId);",
                basePath=base, innerFormId=formId, formsubscribe_onLoaded=True,
                _onBuilt=1, **triggers)
        return root

    def _groupletPanel_mandatoryPaths(self, menu, topic=None):
        # the data location of a grouplet, as GroupletForm.updateFormFromGroupletMeta computes it
        locations = set()

        def cb(node):
            if not node.attr.get('mandatory'):
                return
            resource = node.attr['resource']
            if topic and resource.startswith(f'{topic}/'):
                resource = resource[len(topic) + 1:]
            location = node.attr.get('locationpath') or resource.replace('/', '.')
            node.attr['mandatory_path'] = location
            locations.add(location)
        menu.walk(cb)
        return locations

    def _groupletPanel_topic(self, pane, menu, frameCode=None,
                             formId=None, useForm=True,
                             grouplet_kwargs=None, **kwargs):
        frame = pane.framePane(frameCode=frameCode, _anchor=True, **kwargs)
        frame.data('.grouplet_menu', menu)
        bar_id = f'{frameCode}_bar'
        bar = frame.top.slotBar('*,mb,*', _class='mobile_bar',
                                nodeId=bar_id)
        bar.mb.multibutton(value='^.selected_code',
                           storepath='.grouplet_menu')
        bar.dataController(
            "gnr_grouplet.panelSelectFromCode(this, code, innerFormId);",
            code='^.selected_code', innerFormId=formId, _onBuilt=1)
        center = frame.center.contentPane(overflow='auto')
        if useForm:
            frame.dataController("""
                var barNode = genro.nodeById(barId);
                if(barNode){
                    ['ok','changed','error'].forEach(function(s){
                        genro.dom.setClass(barNode, 'grplt_status_' + s, s == status);
                    });
                }
            """, barId=bar_id,
                **{f'subscribe_form_{formId}_onStatusChange': True})
            self._groupletPanel_innerReload(bar, formId)
            center.GroupletForm(**grouplet_kwargs)
        else:
            center.grouplet(**grouplet_kwargs)
        return frame

    def _groupletPanel_innerReload(self, node, formId, flagPath='#ANCHOR.after_save'):
        # the open group follows the outer record on every load, except right after the outer
        # form's own save: an invalid edit the group still holds was not flushed and must stay
        node.dataController(f"this.setRelativeData('{flagPath}', true);",
                            formsubscribe_onSaved=True)
        node.dataController(f"""
            var inner = genro.formById(innerFormId);
            var keep = afterSave && inner.changed;
            this.setRelativeData('{flagPath}', false);
            if(inner.status!='noItem' && !keep){{
                inner.reload();
            }}
            """, innerFormId=formId, afterSave=f'={flagPath}',
            formsubscribe_onLoaded=True)

    def _groupletPanel_tree(self, pane, menu, frameCode=None,
                            formId=None, useForm=True,
                            grouplet_kwargs=None, **kwargs):
        bc = pane.borderContainer(_anchor=True, **kwargs)
        bc.data('.grouplet_menu', menu)
        tree_frame = bc.framePane(region='left', width='220px',
                                  splitter=True,
                                  _class='grouplet_panel_tree',
                                  frameCode=f'{frameCode}_tree')
        tree_frame.top.slotBar('5,searchOn,*,5',
                               _class='grouplet_panel_searchbar')
        tree_frame.center.contentPane().div(padding='10px').tree(
            storepath='.grouplet_menu',
            hideValues=True,
            labelAttribute='caption',
            _class='grouplet_tree',
            selectedLabelClass='selectedTreeNode',
            openOnClick=True,
            selectedPath='^.selected_treepath',
            nodeId=f'{frameCode}_tree',
            getLabelClass="""
                var labelClass = node.attr.grouplet_caption ? '' : 'grouplet_topic';
                if(node.attr.mandatory_status){
                    labelClass += ' grouplet_mandatory_' + node.attr.mandatory_status;
                }
                return labelClass;
            """,
            connect_onClick=f"gnr_grouplet.panelTreeClick(this, $2, '{formId or ''}');")
        reloader = 'grouplet_remote__reloader' if useForm else 'remote__reloader'
        grouplet_kwargs[reloader] = '^#ANCHOR.selected_fullpath'
        right = bc.borderContainer(region='center')
        top = right.contentPane(region='top',
                                _class='grouplet_panel_title_bar')
        title_id = f'{frameCode}_title'
        top.div('^.selected_caption',
                _class='grouplet_panel_title',
                nodeId=title_id)
        center = right.contentPane(region='center', overflow='auto')
        if useForm:
            bc.dataController("""
                var titleNode = genro.nodeById(titleId);
                if(titleNode){
                    genro.dom.setClass(titleNode, 'grplt_status_error',
                        selectedResource && status == 'error');
                }
            """, titleId=title_id,
                selectedResource='=.selected_resource',
                **{f'subscribe_form_{formId}_onStatusChange': True})
            self._groupletPanel_innerReload(right, formId)
            center.GroupletForm(**grouplet_kwargs)
        else:
            center.grouplet(**grouplet_kwargs)
        return bc

    @extract_kwargs(grouplet=dict(slice_prefix=False, pop=True), remote=True)
    @struct_method
    def gr_groupletWizard(self, pane, table=None, topic=None, value=None,
                          frameCode=None, completeLabel=None,
                          closeLabel=None, backLabel=None,
                          saveMainFormOnComplete=None, saveOnNext=None, resumeStepField=None,
                          grouplets_root=None, grouplet_kwargs=True, remote_kwargs=None,
                          stepperPosition=None, stepSummary=False, saveLabel=None,
                          _confirmedReadOnly=False, _bottomCb=None,
                          _confirmOnLast=False, **kwargs):
        frameCode = frameCode or 'grplt_wizard'
        completeLabel = completeLabel or '!![en]Confirm'
        closeLabel = closeLabel or '!![en]Close'
        backLabel = backLabel or '!![en]Back'
        root_info = self._getGroupletsRootInfo(table=table, topic=topic,
                                               grouplets_root=grouplets_root)
        summary_template = root_info.get('summary_template')
        summary_editable = root_info.get('summary_editable', False)
        has_summary = bool(summary_template)
        step_remote = {}
        for key in [k for k in kwargs if '_remote_' in k]:
            step_remote[tuple(key.split('_remote_', 1))] = kwargs.pop(key)
        vertical = stepperPosition == 'left'
        if vertical:
            # the rail runs the full height, the footer sits under the step only
            kwargs.setdefault('design', 'sidebar')
            kwargs['_class'] = ' '.join(filter(None, [kwargs.get('_class'), 'wizard_vertical']))
        frame = pane.framePane(frameCode=frameCode, _anchor=True, **kwargs)
        menu = self.gr_getGroupletMenu(table=table, topic=topic,
                                       grouplets_root=grouplets_root)
        wizard_steps = Bag()
        for node in menu:
            attrs = dict(node.attr)
            attrs.setdefault('grouplet_caption', attrs.get('caption', node.label))
            wizard_steps.setItem(node.label, None, **attrs)
        menu = wizard_steps
        total_steps = len(menu)
        frame.data('.wizard_steps', menu)
        frame.data('.step_index', 0)
        frame.data('.wizard_last_index', total_steps - 1)
        if has_summary:
            frame.data('.summary_editable', summary_editable)
        menu_nodes = menu.getNodes()
        step_labels = [n.label for n in menu_nodes]
        first_node = menu_nodes[0] if menu_nodes else None
        if first_node:
            frame.data('.current_resource', first_node.attr.get('resource'))
            frame.data('.step_auto_next', bool(first_node.attr.get('autoNext')))
            frame.data('.next_label',
                       menu_nodes[1].attr.get('grouplet_caption')
                       if total_steps > 1 else completeLabel)
        if vertical:
            stepper_bar = frame.left.div(_class='wizard_stepper_bar wizard_stepper_vertical')
        else:
            stepper_bar = frame.top.div(_class='wizard_stepper_bar')
        if has_summary:
            summary_caption = root_info.get('summary_caption', 'Summary')
            stepper_bar.div(summary_caption,
                            _class='wizard_summary_title',
                            hidden='==!_showing',
                            _showing='^.wizard_showing_summary')
        stepper_kw = dict(_class='wizard_stepper')
        if has_summary:
            stepper_kw['hidden'] = '^.wizard_showing_summary'
        stepper = stepper_bar.div(**stepper_kw)
        for i, mnode in enumerate(menu_nodes):
            if i > 0:
                stepper.div(_class='wizard_connector',
                            nodeId=f'{frameCode}_conn_{i}')
            step_cls = 'wizard_step active' if i == 0 else 'wizard_step pending'
            item = stepper.lightButton(
                _class=step_cls,
                nodeId=f'{frameCode}_step_{i}',
                action=f"gnr_grouplet.wizardGoTo(this, {i}, '{frameCode}');")
            item.div(str(i + 1), _class='wizard_circle')
            item.div(mnode.attr.get('grouplet_caption'),
                     _class='wizard_caption')
            # the top stepper has no room for a summary
            step_template = mnode.attr.get('template') if stepSummary and vertical else None
            if step_template:
                item.div(template=step_template, datasource=value,
                         _class='wizard_step_summary')
        step_form_id = f'{frameCode}_step_form'
        # The reload that follows the wizard's own save (onSaved sets
        # wizard_saved_pkey before it, this load consumes it) stays on the step,
        # unless it switched read-only (a confirm). After the insert of an
        # advance it enters the step the advance left pending: that step is
        # built on the saved record (wizardStepForward).
        # Another load of the same record (a reload after an rpc) stays on the
        # step and rebuilds it, unless it switched read-only.
        # A different or new record repositions: first step, the step stored in
        # resumeStepField, or the last one when read-only. SET, not FIRE: FIRE
        # leaves step_index null and the next advance would restart from 0.
        # Already on the target step, wizard_build rebuilds it: its content
        # still shows the record as it was.
        on_loaded_js = """
            var pkey = this.form.getCurrentPkey();
            var isNew = this.form.isNewRecord();
            var ownSave = !isNew && pkey == _saved_pkey;
            SET .wizard_saved_pkey = null;
            SET .wizard_pending_index = null;
            var confirmed = !isNew && !this.form.isDraft();
            var readOnly = confirmed_ro && !isNew && pkey != _reopened
                           && (confirmed || this.form.isProtectWrite());
            var sameMode = !readOnly == !_was_readonly;
            var sameRecord = !isNew && pkey == _loaded_pkey && sameMode;
            SET .wizard_readonly = readOnly;
            SET .wizard_confirmed = confirmed;
            SET .wizard_loaded_pkey = pkey;
            if(ownSave && sameMode){
                if(_pending_index != null){
                    SET .step_index = _pending_index;
                }
                return;
            }
            if(sameRecord){
                var current = _steps.getNodes()[_step_index];
                gnr_grouplet.wizardResolveRemote(this, current ? current.label : null);
                FIRE .wizard_build;
            }else{
                var nodes = _steps.getNodes();
                var target = 0;
                if(readOnly){
                    target = nodes.length - 1;
                }else if(!isNew && step_field){
                    var stored = this.form.getFormData().getItem(step_field);
                    target = Math.max(nodes.findIndex(function(n){return n.label == stored;}), 0);
                }
                if(nodes[target] && _current_resource == nodes[target].attr.resource){
                    gnr_grouplet.wizardResolveRemote(this, nodes[target].label);
                    FIRE .wizard_build;
                }
                SET .step_index = target;
                SET .wizard_step_name = nodes[target] ? nodes[target].label : null;
            }
        """
        # True saves on every advance, step names only on leaving those steps
        if saveOnNext and saveOnNext is not True:
            save_steps = saveOnNext.split(',') if isinstance(saveOnNext, str) else list(saveOnNext)
            unknown = [s for s in save_steps if s not in step_labels]
            if unknown:
                raise ValueError(f'groupletWizard: no step {", ".join(unknown)} for saveOnNext')
            saveOnNext = ','.join(save_steps)
        if saveOnNext:
            frame.data('.wizard_save_on_next', saveOnNext)
        # The current step lives in the wizard's own data and reaches the
        # record inside a save the form is already making. The one move that
        # writes it on its own is an advance past the stored step: progress is
        # a change, looking back is not (_wizardSetStepName).
        if resumeStepField and not has_summary:
            frame.data('.wizard_step_field', resumeStepField)
            pane.dataController("""
                var record = this.form.getFormData();
                if(step_name && record.getItem(step_field) != step_name){
                    record.setItem(step_field, step_name);
                }
            """, _fired='^#FORM.controller.saving', step_name='=.wizard_step_name',
                step_field=resumeStepField)
        if not has_summary:
            pane.dataController("SET .wizard_saved_pkey = $1.pkey;",
                                formsubscribe_onSaved=True)
            # a save followed by no load (a dismiss) must not mark the next one
            pane.dataController("SET .wizard_saved_pkey = null; SET .wizard_loaded_pkey = null;",
                                formsubscribe_onDismissed=True)
        # a refused insert brings no reload to enter the pending step
        pane.dataController("SET .wizard_pending_index = null;",
                            formsubscribe_onSaveFailed=True)
        if has_summary:
            on_loaded_js = """
                SET .wizard_pending_index = null;
                SET .wizard_showing_summary = false;
                SET .wizard_page = 'steps';
                if(this.form.isNewRecord()){
                    FIRE .step_index = 0;
                }else{
                    genro.publish(frameCode + '_show_summary');
                }
            """
        pane.dataController(on_loaded_js,
                            frameCode=frameCode,
                            _saved_pkey='=.wizard_saved_pkey',
                            _pending_index='=.wizard_pending_index',
                            _loaded_pkey='=.wizard_loaded_pkey',
                            _was_readonly='=.wizard_readonly',
                            _step_index='=.step_index',
                            _current_resource='=.current_resource',
                            _steps='=.wizard_steps',
                            _reopened='=#FORM.wizard_reopened',
                            step_field=resumeStepField,
                            confirmed_ro=_confirmedReadOnly,
                            formsubscribe_onLoaded=True)
        if _confirmedReadOnly:
            # <frameCode>_reopen {step}: a confirmed record opens for editing
            # on that step, until it is saved or the form is dismissed
            pane.dataController("""
                SET #FORM.wizard_reopened = this.form.getCurrentPkey();
                this.form.setLocked(false);
                SET .wizard_readonly = false;
                var nodes = _steps.getNodes();
                var target = Math.max(nodes.findIndex(function(n){return n.label == step;}), 0);
                if(nodes[target] && _current_resource == nodes[target].attr.resource){
                    gnr_grouplet.wizardResolveRemote(this, nodes[target].label);
                    FIRE .wizard_build;
                }
                SET .step_index = target;
                SET .wizard_step_name = nodes[target] ? nodes[target].label : null;
            """, _steps='=.wizard_steps', _current_resource='=.current_resource',
                **{f'subscribe_{frameCode}_reopen': True})
            # an advance saves a stored record without reloading it: reload it,
            # to lock it again and build the next step on what was saved
            pane.dataController("""if(!reopened || $1.pkey != reopened){ return; }
                                   SET #FORM.wizard_reopened = null;
                                   this.form.reload();""",
                                reopened='=#FORM.wizard_reopened',
                                formsubscribe_onSaved=True)
            # an advance with nothing to save reloads nothing: reaching the last
            # step locks the record again all the same
            pane.dataController("""if(!reopened || idx != last || this.form.lazySaving){ return; }
                                   SET #FORM.wizard_reopened = null;
                                   SET .wizard_readonly = true;
                                   this.form.setLocked(true);""",
                                idx='^.step_index', last='=.wizard_last_index',
                                reopened='=#FORM.wizard_reopened')
            pane.dataController("SET #FORM.wizard_reopened = null;",
                                formsubscribe_onDismissed=True)
        # the step form saves even when incomplete, so Back keeps what was
        # typed: validity is checked by the wizard on Next and on Confirm.
        # As a child of the surrounding form, its pending changes are asked
        # about when that form is dismissed or navigated away, unless that
        # form has form_avoidPendingChangesDialog (wizardRegisterStep).
        grouplet_kwargs.update(resource='^#ANCHOR.current_resource',
                           value=value,
                           loadOnBuilt=True, formId=step_form_id,
                           form_modalForm=True, form_allowSaveInvalid=True,
                           form_pendingChangesSaveSlot=False,
                           _onRemote="gnr_grouplet.wizardRegisterStep(this.form);",
                           grouplet_remote__wizard_build='^#ANCHOR.wizard_build')
        grouplet_kwargs['rootTag'] = 'contentPane'
        # remote_<name> reaches every step, <step>_remote_<name> only that one.
        # Both resolve where they are written, not inside the step (where #FORM
        # and relative paths would mean the step form): the wizard reads them
        # in its own context before each build (wizardResolveRemote).
        remote_specs = Bag()
        specs = [(None, name, v) for name, v in (remote_kwargs or {}).items()]
        for (step, name), v in step_remote.items():
            if step not in step_labels:
                raise ValueError(f'groupletWizard: no step {step!r} for {step}_remote_{name}')
            specs.append((step, name, v))
        for step, name, remote_value in specs:
            spec = dict(name=name, step=step)
            if isinstance(remote_value, str) and remote_value[:1] in ('=', '^'):
                spec['path'] = remote_value[1:]
            else:
                spec['value'] = remote_value
            remote_specs.setItem(f'r_{len(remote_specs)}', None, **spec)
            grouplet_kwargs[f'grouplet_remote_{name}'] = f'=#ANCHOR.wizard_remote.{name}'
        if remote_specs:
            frame.data('.wizard_remote_specs', remote_specs)
        if table:
            grouplet_kwargs['table'] = table
        if grouplets_root:
            grouplet_kwargs['grouplets_root'] = grouplets_root

        if has_summary:
            frame.data('.wizard_page', 'steps')
            frame.data('.wizard_showing_summary', False)
            sc = frame.center.stackContainer(selectedPage='^.wizard_page')
            sc.contentPane(pageName='steps', overflow='auto',
                           _class='wizard_step_pane').GroupletForm(
                **grouplet_kwargs)
            sc.contentPane(pageName='summary', overflow='auto',
                           _class='wizard_summary').div(
                template=summary_template, datasource=value)
        else:
            frame.center.contentPane(overflow='auto',
                                     _class='wizard_step_pane').GroupletForm(
                **grouplet_kwargs)
        bottom = frame.bottom.div(_class='wizard_bottom_bar')
        back_kwargs = dict(_class='wizard_back_btn',
                           action="gnr_grouplet.wizardGoTo(this, _idx-1, _frameCode);",
                           _idx='^.step_index', _frameCode=frameCode)
        if has_summary:
            back_kwargs['hidden'] = '==_idx==0 || _showing'
            back_kwargs['_showing'] = '^.wizard_showing_summary'
        else:
            back_kwargs['hidden'] = '==_idx==0 || _readonly'
            back_kwargs['_readonly'] = '^.wizard_readonly'
        bottom.lightButton(backLabel, **back_kwargs)
        if _bottomCb:
            _bottomCb(bottom)
        if has_summary:
            bottom.lightButton('^.next_label',
                               _class='wizard_next_btn',
                               action="gnr_grouplet.wizardNext(this, _frameCode);",
                               _frameCode=frameCode,
                               hidden='==_showing || _auto',
                               _showing='^.wizard_showing_summary',
                               _auto='^.step_auto_next')
            bottom.lightButton(closeLabel,
                               _class='wizard_close_btn',
                               action="this.form.dismiss();",
                               hidden='==!_showing',
                               _showing='^.wizard_showing_summary')
        else:
            # with _confirmOnLast the last step's buttons come from _bottomCb
            bottom.lightButton('^.next_label',
                               _class='wizard_next_btn',
                               action="gnr_grouplet.wizardNext(this, _frameCode);",
                               _frameCode=frameCode,
                               hidden='==_ro || (_col && _idx==_last) || _auto',
                               _ro='^.wizard_readonly', _col=_confirmOnLast,
                               _auto='^.step_auto_next',
                               _idx='^.step_index', _last='^.wizard_last_index')
        frame.dataController(
            "gnr_grouplet.wizardUpdateStep(this, idx, _completeLabel, _frameCode, _saveLabel);",
            idx='^.step_index',
            _completeLabel=completeLabel, _frameCode=frameCode,
            _saveLabel=saveLabel, _onBuilt=True)
        if saveMainFormOnComplete:
            if has_summary:
                frame.data('.wizard_pending_summary', False)
                frame.dataController("""
                    SET .wizard_pending_summary = true;
                    this.form.save();
                """, **{f'subscribe_{frameCode}_complete': True})
                frame.dataController("""
                    if(pending){
                        SET .wizard_pending_summary = false;
                        genro.publish(_frameCode + '_show_summary');
                    }
                """, formsubscribe_onSaved=True,
                     pending='=.wizard_pending_summary',
                     _frameCode=frameCode)
            else:
                frame.dataController("""
                    this.form.save({destPkey:'*dismiss*'});
                """, **{f'subscribe_{frameCode}_complete': True})
        elif has_summary:
            frame.dataController("""
                genro.publish(_frameCode + '_show_summary');
            """, **{f'subscribe_{frameCode}_complete': True},
                 _frameCode=frameCode)
        if has_summary:
            frame.dataController("""
                SET .wizard_page = 'summary';
                SET .wizard_showing_summary = true;
            """, **{f'subscribe_{frameCode}_show_summary': True})
        return frame

    @struct_method
    def gr_groupletWizardForm(self, form, pane=None, frameCode=None,
                              saveOnNext=True, confirmedReadOnly=False,
                              draftConfirm=False, backToDraft=None,
                              saveDraftLabel=None, backToDraftLabel=None,
                              confirmAsk=None, backToDraftAsk=None,
                              keepToolbar=False, **kwargs):
        """The wizard as the mode of a th form, called from th_form: no toolbar,
        no padlock, a save on every advance, and the last step saves and closes.
        saveOnNext may name the steps (comma-separated) whose advance saves,
        the others save nothing; saveLabel is the Next label of those steps.
        confirmedReadOnly opens a confirmed (or protect_write) record on the
        last step, locked and without navigation, the record saved by an
        advance included. On a draftField table confirmed means not a draft,
        so new records must start as drafts; on any other table every saved
        record is confirmed. draftConfirm (implies
        confirmedReadOnly) splits a draft's last step into Save draft (saves
        and closes) and completeLabel (confirms, saves and reloads read-only);
        a confirmed record gets Back to draft in place of Back, if backToDraft
        allows it (True: everyone, a string: the user tags). On a table with no
        drafts, publishing <frameCode>_reopen with {step} opens a confirmed
        record for editing on that step, locked again once saved.
        keepToolbar leaves the top bar th already built: with the th option
        modal='navigation' a dialog form keeps Back and, on a list, Prev/Next.
        Any other bar is kept too, the standard save/delete toolbar included."""
        confirmedReadOnly = confirmedReadOnly or draftConfirm
        # Emptied, not removed: later builds still insert into the slot.
        top = form.getNode('top')
        if top is not None and not keepToolbar:
            for label in list(top.value.keys()):
                top.value.popNode(label)
        form.attributes['form_parentLock'] = False
        # the record is saved by the wizard only, never from Pending changes
        form.attributes['form_pendingChangesSaveSlot'] = False
        form.dataController("""
            var readOnly = confirmed_ro && !this.form.isNewRecord()
                           && this.form.getCurrentPkey() != reopened
                           && (!this.form.isDraft() || this.form.isProtectWrite());
            if(!!this.form.locked != readOnly){ this.form.setLocked(readOnly); }
        """, confirmed_ro=confirmedReadOnly, reopened='=#FORM.wizard_reopened',
            formsubscribe_onLoaded=True)
        frameCode = frameCode or f"{form.attributes['formId']}_wizard"
        form.dataController("this.form.save({destPkey:'*dismiss*', always:true});",
                            **{f'subscribe_{frameCode}_complete': True})
        bottomCb = None
        if draftConfirm:
            bottomCb = self._wizardDraftButtons(form, frameCode=frameCode,
                                                backToDraft=backToDraft,
                                                completeLabel=kwargs.get('completeLabel'),
                                                saveDraftLabel=saveDraftLabel,
                                                backToDraftLabel=backToDraftLabel,
                                                confirmAsk=confirmAsk,
                                                backToDraftAsk=backToDraftAsk)
        if pane is None:
            # a border region: a plain contentPane does not pass a dialog's
            # resize down to the wizard's frame, which then stays 0 high
            pane = form.center.borderContainer().contentPane(region='center')
        return pane.groupletWizard(table=form.attributes.get('table'),
                                   value='^.record', frameCode=frameCode,
                                   saveOnNext=saveOnNext,
                                   _confirmedReadOnly=confirmedReadOnly,
                                   _confirmOnLast=draftConfirm,
                                   _bottomCb=bottomCb, **kwargs)

    def _wizardDraftButtons(self, form, frameCode=None, backToDraft=None,
                            completeLabel=None, saveDraftLabel=None,
                            backToDraftLabel=None, confirmAsk=None,
                            backToDraftAsk=None):
        completeLabel = completeLabel or '!![en]Confirm'
        backToDraftLabel = backToDraftLabel or '!![en]Back to draft'
        back_tags = None if backToDraft is True else backToDraft
        can_back = bool(backToDraft) and self.application.checkResourcePermission(
            back_tags, self.userTags)
        if backToDraft:
            # the rpc reads its permission from here, never from the client
            with self.pageStore() as store:
                store.setItem(f'grouplet_wizard.{frameCode}.back_to_draft_table',
                              form.attributes.get('table'))
                store.setItem(f'grouplet_wizard.{frameCode}.back_to_draft_tags', back_tags)
        form.dataController(f"gnr_grouplet.wizardConfirm('{frameCode}');",
                            _ask=confirmAsk or '!![en]Once confirmed, the record can no longer be edited.',
                            _ask_title=completeLabel,
                            **{f'subscribe_{frameCode}_confirm': True})
        form.dataController("SET .wizard_confirming = false;", formsubscribe_onSaved=True)
        # a refused confirm must not leave the record flagged for the next save
        form.dataController("""
            if(!confirming){ return; }
            SET .wizard_confirming = false;
            this.form.setDraft(true);
        """, confirming='=.wizard_confirming', formsubscribe_onSaveFailed=True)
        if can_back:
            # the method object, not its name: it carries the mixin path, so the
            # rpc finds it also on a page that got the component through a th resource
            form.dataRpc(None, self.grouplet_wizardBackToDraft,
                         frameCode=frameCode, pkey='=#FORM.pkey',
                         _onResult='this.form.reload();',
                         _ask=backToDraftAsk or '!![en]The record goes back to draft and can be edited again.',
                         _ask_title=backToDraftLabel,
                         **{f'subscribe_{frameCode}_back_to_draft': True})

        def bottomCb(bottom):
            if can_back:
                bottom.lightButton(backToDraftLabel, _class='wizard_back_btn',
                                   action="genro.publish(_fc + '_back_to_draft');",
                                   _fc=frameCode,
                                   hidden='==!(_ro && _c)', _ro='^.wizard_readonly',
                                   _c='^.wizard_confirmed')
            last_kw = dict(hidden='==_ro || _idx!=_last', _ro='^.wizard_readonly',
                           _idx='^.step_index', _last='^.wizard_last_index',
                           _fc=frameCode)
            bottom.lightButton(saveDraftLabel or '!![en]Save draft',
                               _class='wizard_save_draft_btn',
                               action="gnr_grouplet.wizardNext(this, _fc);", **last_kw)
            bottom.lightButton(completeLabel, _class='wizard_next_btn',
                               action="genro.publish(_fc + '_confirm');", **last_kw)
        return bottomCb

    @public_method
    def grouplet_wizardBackToDraft(self, frameCode=None, pkey=None):
        store = self.pageStore()
        table = store.getItem(f'grouplet_wizard.{frameCode}.back_to_draft_table')
        tags = store.getItem(f'grouplet_wizard.{frameCode}.back_to_draft_tags')
        if not (table and pkey) or not self.application.checkResourcePermission(tags, self.userTags):
            raise self.exception('generic', msg='!![en]Not allowed to take this record back to draft')
        with self.db.table(table).recordToUpdate(pkey) as record:
            record['__is_draft'] = True
        self.db.commit()

    def _getGroupletResources(self, table=None, topic=None,
                              grouplets_root=None):
        grouplets_root = grouplets_root or 'grouplets'
        grouplets_path = grouplets_root
        if topic:
            grouplets_path = f'{grouplets_path}/{topic}'
        resources = Bag()
        if table:
            pkg, tblname = table.split('.')
            resources.update(
                self.site.resource_loader.resourcesAtPath(
                    page=self, pkg=pkg,
                    path=f'tables/{tblname}/{grouplets_path}'))
            resources.update(
                self.site.resource_loader.resourcesAtPath(
                    page=self,
                    path=f'tables/_packages/{pkg}/{tblname}/{grouplets_path}'))
        else:
            resources.update(
                self.site.resource_loader.resourcesAtPath(
                    page=self, path=grouplets_path))
        return resources

    @public_method
    def gr_getGroupletMenu(self, table=None, topic=None,
                           grouplets_root=None, **kwargs):
        result = Bag()
        resources = self._getGroupletResources(table=table, topic=topic,
                                               grouplets_root=grouplets_root)
        self._buildGroupletMenu(result, resources, table=table,
                                parent_path=topic)
        result.sort('#a.priority,#a.caption')
        return result

    def _buildGroupletMenu(self, result, resources, table=None,
                           parent_path=None):
        for node in resources:
            if node.value:
                self._processTopicNode(result, node, table=table,
                                       parent_path=parent_path)
            else:
                if node.label.startswith('__'):
                    continue
                info = self._get_grouplet_info(node, table=table)
                if info is False:
                    continue
                info['grouplet_caption'] = info['caption']
                resource_path = (f'{parent_path}/{node.label}'
                                 if parent_path else node.label)
                result.setItem(node.label, None,
                               resource=resource_path,
                               **info)

    def _processTopicNode(self, result, node, table=None,
                          parent_path=None):
        topic_content = Bag()
        children = Bag(node.value)
        info_node = children.popNode('__info__')
        topic_info = (self._get_grouplet_info(info_node, table=table)
                      if info_node else {})
        if topic_info is False:
            return
        if not isinstance(topic_info, dict):
            topic_info = {}
        topic_info.setdefault('caption',
                              node.attr.get('caption', node.label))
        topic_info.setdefault('topic', node.label)
        children.popNode('__pycache__')
        if not children:
            return
        current_path = (f'{parent_path}/{node.label}'
                        if parent_path else node.label)
        topic_info['resource'] = current_path
        result.addItem(node.label, topic_content, **topic_info)
        self._buildGroupletMenu(topic_content, children, table=table,
                                parent_path=current_path)
        topic_content.sort('#a.priority,#a.caption')

    def gr_groupletAddrowMenu(self, table=None, field=None,
                              grouplets_root=None):
        menu = self.gr_getGroupletMenu(table=table,
                                       grouplets_root=grouplets_root)
        result = Bag()
        self._buildAddrowMenu(result, menu, field=field)
        return result

    def _buildAddrowMenu(self, result, menu, field=None):
        for node in menu:
            if node.value:
                group_bag = Bag()
                self._buildAddrowMenu(group_bag, node.value, field=field)
                result.setItem(node.label, group_bag,
                               caption=node.attr.get('caption'))
            else:
                result.setItem(node.label, None,
                               caption=node.attr.get('grouplet_caption'),
                               default_kw={field: node.attr.get('resource')})

    def _get_raw_info(self, resmodule):
        for cls_name in ('Grouplet', 'GroupletTopic'):
            cls = getattr(resmodule, cls_name, None)
            if cls and hasattr(cls, '__info__'):
                return dict(cls.__info__(self))
        return dict(getattr(resmodule, 'info', {}))

    def _get_grouplet_info(self, node, table=None):
        resmodule = gnrImport(node.attr['abs_path'], avoid_module_cache=True)
        info = self._get_raw_info(resmodule)
        tags = info.get('tags')
        permissions = info.get('permissions')
        info['caption'] = info.get('caption') or node.attr.get('caption')
        info['code'] = info.get('code') or node.label
        info['priority'] = info.get('priority') or 0
        if (tags and not self.application.checkResourcePermission(tags, self.userTags)) or \
                (table and permissions and not self.checkTablePermission(table=table, permissions=permissions)):
            return False
        is_enabled_cb = getattr(resmodule, 'is_enabled', None)
        if is_enabled_cb and is_enabled_cb(self) is False:
            return False
        return info

    def _getGroupletsRootInfo(self, table=None, topic=None,
                              grouplets_root=None):
        resources = self._getGroupletResources(table=table, topic=topic,
                                               grouplets_root=grouplets_root)
        info_node = resources.getNode('__info__')
        if not info_node:
            return {}
        resmodule = gnrImport(info_node.attr['abs_path'],
                              avoid_module_cache=True)
        return self._get_raw_info(resmodule)


class GroupletCardHandler(BaseComponent):
    py_requires = 'gnrcomponents/grouplet/grouplet:GroupletHandler'
    css_requires = 'gnrcomponents/grouplet/grouplet'
    js_requires = 'gnrcomponents/grouplet/grouplet,gnrcomponents/grouplet/grouplet_card'

    @extract_kwargs(grouplet=dict(slice_prefix=False, pop=True), editmenu=True, form=True)
    @struct_method
    def gr_groupletCard(self, pane, datapath=None, resource=None, handler=None, table=None,
                        grouplets_root=None, chromeSide=None, collapsible=None, collapsed=None,
                        title=None, titleField=None, titleTemplate=None, emptyTitle=None,
                        tools=None, doc=None, doc_kw=None, delitem=None, editmenu=None,
                        checkbox=None, useForm=False, nodeId=None, grouplet_kwargs=None,
                        editmenu_kwargs=None, form_kwargs=None, **kwargs):
        """A grouplet bound to a datapath with its chrome band: a titled group
        that can take a roundedGroup's place in a form. Without resource or
        handler it returns its body, to be filled in place.

        The profile — chromeSide, collapsible, title, titleField, titleTemplate,
        emptyTitle, tools, doc, doc_kw, delitem, editmenu — is the resource's
        `card` (in its `__info__`), then what is given here. `collapsed` and
        `checkbox` take a path ('^.path') holding the state; delitem is True,
        False or a '^path' / '=path' / '==expr' read as the menu opens, and
        its entry clears the fields of the card. With the inlinedoc
        experimental flag `doc` is the documentation address of the ⓘ
        (sys/ep_doc), by default the resource's; `doc_kw` fills the doc's
        variables the card's data has not.

        useForm=True edits the grouplet in a GroupletForm of its own: a copy
        of the card's data, written back as it is saved (form_autoSave, 1 by
        default; the other form_* go to the GroupletForm). It needs resource
        or handler, and follows the loads of the form the card sits in."""
        nodeId = nodeId or f'grpcard_{id(pane)}_{len(pane)}'
        if useForm and not (resource or handler):
            raise self.exception('generic', msg='groupletCard: useForm needs resource or handler')
        card = self._gr_cardInfo(resource=resource, table=table, grouplets_root=grouplets_root)
        caller = dict(chromeSide=chromeSide, collapsible=collapsible, title=title,
                      titleField=titleField, titleTemplate=titleTemplate, emptyTitle=emptyTitle,
                      tools=tools, doc=doc, doc_kw=doc_kw, delitem=delitem, editmenu=editmenu)
        card.update({k: v for k, v in caller.items() if v is not None})
        if doc is not None:
            card['doc'] = self._gr_cardDocAddress(doc, resource=resource, table=table) \
                if self.inlineDoc else self._gr_cardDoc(doc, table=table)
        side = card.get('chromeSide') or 'top'
        if side not in ('top', 'left', 'right'):
            raise self.exception('generic', msg="groupletCard: chromeSide is 'top', 'left' or 'right'")
        collapsible = card.get('collapsible', False)
        # a '^path' state is the caller's, at a path relative to where the
        # card is placed; otherwise the card keeps it in its workspace
        bound_collapsed = isinstance(collapsed, str) and collapsed.startswith('^')
        bound_checkbox = isinstance(checkbox, str) and checkbox.startswith('^')
        flavours = ['grouplet_card', 'grouplet_card--box', f'grouplet_card--chrome-{side}']
        extra_class = kwargs.pop('_class', None)
        if extra_class:
            flavours.append(extra_class)
        root = pane.div(_class=' '.join(flavours), nodeId=nodeId, datapath=datapath,
                        _gc_root=True, _workspace=True, **kwargs)
        if not bound_collapsed:
            root.data('#WORKSPACE.collapsed', bool(collapsed) or collapsible == 'closed')
        body = root.div(_class='grouplet_card_body')
        form_id = f'{nodeId}_form' if useForm else None
        if useForm:
            form_kwargs = dict(form_kwargs or {})
            # a card follows its content: no dijit pane sizing it to a frame
            grouplet_kwargs.setdefault('grouplet_rootWidget', 'div')
            body.GroupletForm(resource=resource, handler=handler if isinstance(handler, str) or not handler
                              else handler.__name__,
                              table=table, grouplets_root=grouplets_root, value='^.', formId=form_id,
                              loadOnBuilt=True, rootTag='div',
                              store_autoSave=form_kwargs.pop('autoSave', 1),
                              **form_kwargs, **grouplet_kwargs)
            self._groupletPanel_innerReload(root, form_id, flagPath='#WORKSPACE.after_save')
            root.dataController("""
                var host = this.attributeOwnerNode('_gc_root').cardHost;
                if (host) { host.setFormStatus(status); }
            """, **{f'subscribe_form_{form_id}_onStatusChange': True})
        elif resource or isinstance(handler, str):
            body.grouplet(resource=resource, handler=handler, table=table,
                          grouplets_root=grouplets_root, value='^.', **grouplet_kwargs)
        elif handler:
            handler(body, **grouplet_kwargs)
        editmenu = card.get('editmenu') or {}
        root.dataController("""
            var node = this.attributeOwnerNode('_gc_root');
            node.cardHost = new gnr.GroupletCardHost(node, kw);
        """, _onBuilt=True,
            kw=dict(tools=card.get('tools'), collapsible=bool(collapsible),
                    collapsedPath=collapsed[1:] if bound_collapsed else None,
                    checkboxPath=checkbox[1:] if bound_checkbox else None,
                    title=self._(card['title']) if card.get('title') else None,
                    titleField=card.get('titleField'),
                    emptyTitle=self._(card.get('emptyTitle') or '!!Untitled'),
                    titleTemplate=self._gr_template(card.get('titleTemplate')),
                    template=card.get('template'),
                    doc=(card.get('doc') or None) if self.inlineDoc else self._gr_template(card.get('doc')),
                    doc_kw=card.get('doc_kw') or {},
                    delitem=card.get('delitem', False),
                    editmenu=editmenu if isinstance(editmenu, dict) else {},
                    editmenu_kw=editmenu_kwargs or {}, formId=form_id))
        if collapsible:
            (pane if bound_collapsed else root).dataController("""
                var node = genro.nodeById(cardId);
                if (node && node.cardHost) { node.cardHost.applyCollapsed(collapsed); }
            """, cardId=nodeId, collapsed=collapsed if bound_collapsed else '^#WORKSPACE.collapsed')
        if bound_checkbox:
            pane.dataController("""
                var node = genro.nodeById(cardId);
                if (node && node.cardHost) { node.cardHost.card.setChecked(checked); }
            """, cardId=nodeId, checked=checkbox)
        root.dataController("""
            var host = this.attributeOwnerNode('_gc_root').cardHost;
            if (host) { host.card.refreshTitle(); }
        """, data='^.', _delay=1)
        return body


class GroupletGridHandler(BaseComponent):
    py_requires = 'gnrcomponents/grouplet/grouplet:GroupletHandler'
    css_requires = 'gnrcomponents/grouplet/grouplet'
    js_requires = ('gnrcomponents/grouplet/grouplet,'
                   'gnrcomponents/grouplet/grouplet_card,'
                   'gnrcomponents/grouplet/grouplet_grid')

    @public_method
    def gr_getGroupletGridTemplate(self, resource=None, handler=None,
                                   table=None, grouplets_root=None,
                                   grouplet_kwargs=None,
                                   _inheritedAttributes=None, **kwargs):
        grouplets_root = grouplets_root or 'grouplets'
        cell_kw = dict(grouplet_kwargs or {})
        for k in list(cell_kw.keys()):
            if k.endswith('_path'):
                cell_kw[k[0:-5]] = cell_kw.pop(k)[1:]
        if resource:
            handlername = handler or 'grouplet_main'
            res = resource if ':' in resource else f'{resource}:Grouplet'
            if table:
                self.mixinTableResource(
                    table, f'{grouplets_root}/{res}', safeMode=True)
            else:
                self.mixinComponent(f'{grouplets_root}/{res}')
            handler_fn = getattr(self, handlername)
        elif handler:
            handler_fn = self.getPublicMethod('remote', handler)
        else:
            raise self.exception(
                'generic',
                msg='groupletGrid: missing resource or handler for template')
        pane = self.newSourceRoot(_inheritedAttributes)
        self._root = pane
        handler_fn(pane, **cell_kw)
        return pane

    @public_method
    def gr_getGroupletGridTemplateMap(self, table=None,
                                      grouplets_root=None,
                                      grouplet_kwargs=None,
                                      _inheritedAttributes=None, **kwargs):
        """Return a Bag {resource_path: template_source_root} for every
        grouplet found under `table`'s `grouplets_root` folder. Used by
        the controller in `resourceField=` mode to preload all candidate
        templates with a single RPC at boot.
        """
        if not table:
            raise self.exception(
                'generic',
                msg='groupletGrid: gr_getGroupletGridTemplateMap '
                    'requires table=')
        menu = self.gr_getGroupletMenu(table=table,
                                       grouplets_root=grouplets_root)
        result = Bag()
        for resource_path in self._walkGroupletMenu(menu):
            template = self.gr_getGroupletGridTemplate(
                resource=resource_path, table=table,
                grouplets_root=grouplets_root,
                grouplet_kwargs=grouplet_kwargs,
                _inheritedAttributes=_inheritedAttributes)
            card = self._gr_cardInfo(resource=resource_path, table=table,
                                     grouplets_root=grouplets_root)
            result.setItem(resource_path.replace('/', '_'), template,
                           resource=resource_path,
                           card=self._gr_cardForJs(card) if card else None)
        return result

    def _walkGroupletMenu(self, menu):
        """Yield every leaf resource_path from a grouplet menu Bag
        (returned by gr_getGroupletMenu). Topics are walked recursively;
        leaves carry attr['resource']."""
        for node in menu:
            if node.value:
                yield from self._walkGroupletMenu(node.value)
            elif node.attr.get('resource'):
                yield node.attr['resource']

    @extract_kwargs(
        grouplet=dict(slice_prefix=False, pop=True),
        store= dict(slice_prefix=False,pop=True),
        additem=True, delitem=True, copyitem=True, editmenu=True, totals=True, card=True,
    )
    @struct_method
    def gr_groupletGrid(self, pane, datapath=None, storepath=None,
                        controllerPath=None,
                        resource=None, handler=None,
                        resourceField=None,
                        struct=None, structpath=None,
                        table=None, grouplets_root=None,
                        cols=1, min_width=None, gap='12px', fillRow=False,
                        height=None, max_height=None, fillParent=False,
                        additem=True, delitem=None, copyitem=False, editmenu=None,
                        layout='cards',
                        lazyTabs=False,
                        titleField=None,
                        titleTemplate=None,
                        sortField=None, sortStore=False,
                        collapsible=None, collapsedTemplate=None,
                        chromeSide=None,
                        emptyTitle=None,
                        dragCode=None,
                        onSelfDropRows=None,
                        afterSelfDropRows=None,
                        minRows=0, maxRows=None,
                        defaultRow=None,
                        rowTemplate=None,
                        selectionmenu=None, rowCheckbox=False,
                        selectionGroup=None,
                        counterField=None,
                        formulas=None, totals=None,
                        grouplet_kwargs=None,
                        additem_kwargs=None,
                        delitem_kwargs=None,
                        copyitem_kwargs=None,
                        editmenu_kwargs=None,
                        totals_kwargs=None,
                        store_kwargs=None,
                        card_kwargs=None,
                        nodeId=None, **kwargs):
        # Author-supplied nodeIds inside the template must bake in `rowKey`
        # (or similar): the framework does NOT auto-rename them per row clone.
        nodeId = nodeId or kwargs.pop('gridId', None) or f'grpgrid_{id(pane)}'
        # the card profile: the resource's `card`, then what the caller sets
        # (card_tools, card_doc, ... and the grid's own profile parameters);
        # with resourceField each row's resource adds its own, client side
        card = self._gr_cardInfo(resource=resource, table=table, grouplets_root=grouplets_root)
        caller = dict(card_kwargs or {}, delitem=delitem, editmenu=editmenu, collapsible=collapsible,
                      chromeSide=chromeSide, emptyTitle=emptyTitle, titleTemplate=titleTemplate)
        card.update({k: v for k, v in caller.items() if v is not None})
        delitem = card.get('delitem', True)
        editmenu = card.get('editmenu', False)
        collapsible = card.get('collapsible', False)
        chromeSide = card.get('chromeSide', False)
        emptyTitle = card.get('emptyTitle', '!!Untitled')
        titleTemplate = card.get('titleTemplate')
        if editmenu is True:
            editmenu = {'addPrev': True, 'addNext': True}
            if not copyitem:
                editmenu['copy'] = True
            if not delitem:
                editmenu['delete'] = True
        elif not editmenu:
            editmenu = {}
        body_id = f'{nodeId}_body'
        if callable(struct):
            built = pane.page.newGridStruct(maintable=table)
            struct(built)
            struct = built
        struct_mode = struct is not None
        if not (resource or handler or resourceField or struct_mode):
            raise self.exception(
                'generic',
                msg='groupletGrid: missing resource, handler, '
                    'resourceField, or struct')
        handler_name = handler.__name__ if callable(handler) else handler
        # dragCode: None → isolated DnD (nodeId), False → off, str → shared.
        if dragCode is False:
            resolved_drag_code = None
        elif dragCode is None:
            resolved_drag_code = nodeId
        else:
            resolved_drag_code = dragCode
        # fillParent implies framed: pixel-accurate sizing comes from the
        # dijit ancestor, internal scrolling is delegated to .grouplet_grid_body.
        framed = bool(height or max_height or fillParent)
        flavours = ['grouplet_grid_container', 'grouplet_grid']
        if struct_mode:
            flavours.append('grouplet_grid--struct')
            row_tools = sum(1 for tool in (delitem, copyitem, editmenu) if tool)
            if row_tools > 1:
                flavours.append(f'grouplet_grid--tools-{row_tools}')
        if framed:
            flavours.append('grouplet_grid--framed')
        if fillParent:
            flavours.append('grouplet_grid--fill')
        if fillRow:
            flavours.append('grouplet_grid--fillrow')
        if additem == 'phantom' and not resourceField:
            flavours.append('grouplet_grid--phantom')
        entry_mode = additem == 'entry' and not resourceField
        if entry_mode:
            flavours.append('grouplet_grid--entry')
            if resource and not rowTemplate:
                rowTemplate = self.gr_getTemplatePars(
                    resource=resource, table=table,
                    grouplets_root=grouplets_root).get('template')
            if rowTemplate:
                flavours.append('grouplet_grid--templated')
        else:
            rowTemplate = None
        # actions on several selected rows: outside tabs every row is
        # selectable by Cmd/Ctrl/Shift-click, and by its checkbox given
        # rowCheckbox; copy is preset, delete whenever rows can be deleted;
        # exportXls and print are presets to ask for;
        # selectionmenu=False turns the selection off
        selectable = layout not in ('tabs', 'vtabs')
        if not selectable or selectionmenu is False:
            selectionmenu = {}
        elif selectionmenu is None:
            selectionmenu = {'copy': True, 'delete': True} if delitem else {'copy': True}
        rowCheckbox = bool(rowCheckbox and selectionmenu)
        if rowCheckbox:
            flavours.append('grouplet_grid--checkbox')
        # chromeSide='top'|'left'|'right': cards gather checkbox, chevron and
        # kebab in a band along that side, the band being the drag source;
        # False (default) keeps the corner chrome
        if chromeSide not in (None, False, 'top', 'left', 'right'):
            raise self.exception('generic',
                                 msg="groupletGrid: chromeSide is 'top', 'left', 'right' or False")
        if struct_mode or rowTemplate or layout in ('tabs', 'vtabs'):
            chromeSide = None
        totals_kwargs = dict(totals_kwargs or {})
        if totals_kwargs.pop('sticky', False):
            flavours.append('grouplet_grid--sticky-totals')
        totals = self._gr_groupletGrid_totals(
            totals, default_format=totals_kwargs.pop('format', None))
        extra_class = kwargs.pop('_class', None)
        if extra_class:
            flavours.append(extra_class)
        container_class = ' '.join(flavours)
        # controllerPath: explicit → use it; else fall back to datapath when
        # caller supplied one; else default to a per-instance workspace slot
        # (isolated, no global namespace pollution). The store widget node
        # lives at controllerPath; the rows Bag is unaffected.
        if not controllerPath:
            if datapath:
                controllerPath = datapath
            else:
                controllerPath = f'#WORKSPACE.{nodeId}'
                kwargs['_workspace'] = True
        if struct_mode and not structpath:
            structpath = f'{controllerPath}.struct'
        # Root is always a plain div. When fillParent is set, the
        # `.grouplet_grid--fill { height: 100% }` rule makes the grid
        # claim its parent's height — relying on standard CSS flow,
        # not on dijit sizing (a dijit contentPane buried inside a
        # non-layout container would not get resize callbacks anyway).
        container = pane.div(
            _class=container_class,
            nodeId=nodeId,
            datapath=datapath,
            storepath=storepath,
            controllerPath=controllerPath,
            _gg_root=True,
            height=height,
            max_height=max_height,
            onSelfDropRows=onSelfDropRows,
            afterSelfDropRows=afterSelfDropRows,
            **kwargs)
        store_kwargs.setdefault('store_storeType', 'ValuesBagRows')
        if struct_mode:
            container.data(structpath, struct)
        # the footer placeholder exists only when some column totalizes: the JS
        # adapter grafts the totals there (buildFooter returns null otherwise)
        # and an unconditional placeholder would paint an empty footer strip
        struct_has_totalize = struct_mode and any(
            n.attr.get('totalize') for n in struct.traverse())
        for side in ('top', 'bottom', 'left', 'right'):
            slot = container.div(
                _class=f'grouplet_grid_slot grouplet_grid_slot_{side}',
                childname=side, gg_side=side)
            # Pre-allocate placeholders: the JS adapter can only graft into
            # a leaf-empty sourceNode, never into a live one.
            if selectionmenu and side == 'bottom':
                slot.div(_class='grouplet_grid_selection',
                         childname='selection', _gg_selection=True)
            if struct_mode and side == 'top':
                slot.div(_class='grouplet_grid__struct_header',
                         childname='struct_header')
            elif struct_has_totalize and side == 'bottom':
                slot.div(_class='grouplet_grid__struct_footer',
                         childname='struct_footer')
            if entry_mode and side == 'top':
                slot.div(_class='grouplet_grid_entry', childname='entry',
                         _gg_entry=True)
            # the totals band carries the caller's totals_* attributes
            # (hidden, dynamic params): the JS grafts only its content
            if totals and side == 'bottom':
                slot.div(_class='grouplet_grid__totals', childname='totals',
                         **totals_kwargs)
        container.div(_class='grouplet_grid_body',
                      nodeId=body_id,
                      datapath=storepath,
                      _gg_body=True)
        self._gr_groupletGrid_emitController(
            container,
            resource=resource, handler_name=handler_name,
            resourceField=resourceField, structpath=structpath,
            table=table, grouplets_root=grouplets_root,
            grouplet_kwargs=grouplet_kwargs,
            store_kwargs=store_kwargs,
            cols=cols, min_width=min_width, gap=gap,
            additem=additem, delitem=delitem, copyitem=copyitem, editmenu=editmenu,
            additem_kwargs=additem_kwargs,
            delitem_kwargs=delitem_kwargs,
            copyitem_kwargs=copyitem_kwargs,
            editmenu_kwargs=editmenu_kwargs,
            layout=layout, lazyTabs=lazyTabs,
            titleField=titleField, emptyTitle=emptyTitle,
            titleTemplate=self._gr_template(titleTemplate),
            sortField=sortField, sortStore=sortStore,
            collapsible=collapsible,
            collapsedTemplate=self._gr_template(collapsedTemplate),
            chromeSide=chromeSide, card=self._gr_cardForJs(card),
            defaultRow=defaultRow, minRows=minRows, maxRows=maxRows,
            counterField=counterField,
            formulas=formulas, totals=totals,
            rowTemplate=rowTemplate, selectionmenu=selectionmenu,
            rowCheckbox=rowCheckbox, selectionGroup=selectionGroup,
            resolved_drag_code=resolved_drag_code,
            loaderrpc=self.gr_getGroupletGridTemplate,
            mapLoaderrpc=self.gr_getGroupletGridTemplateMap)
        return container

    def _gr_groupletGrid_totals(self, totals, default_format=None):
        """The `totals=` entries in the shape the JS band reads: `key` is
        where the value lives under `<controllerPath>.totalize`, a row
        field summed, or the `name` of a formula over the other totals or of
        a row count. Any other key (`hidden=` and its parameters) goes to
        the entry's cell as an attribute."""
        result = []
        for entry in totals or []:
            entry = dict(entry)
            field = entry.pop('field', None)
            formula = entry.pop('formula', None)
            count = bool(entry.pop('count', False))
            name = entry.pop('name', None)
            if not (field or formula or count) \
                    or (formula and not name) \
                    or (count and (field or formula or not name)):
                raise self.exception(
                    'generic',
                    msg='groupletGrid totals: each entry needs field=, '
                        'or name= with formula= or count=True')
            key = field or name
            label = entry.pop('label', None) or key
            # a row count is an integer: the band's money format is not its
            fmt = entry.pop('format', None) or (None if count else default_format)
            highlight = bool(entry.pop('highlight', False))
            result.append(dict(key=key, field=field, formula=formula,
                               count=count, label=label, format=fmt,
                               highlight=highlight, attrs=entry))
        return result

    def _gr_groupletGrid_emitController(
            self, container, *,
            resource, handler_name, resourceField, structpath, table,
            grouplets_root, grouplet_kwargs, store_kwargs,
            cols, min_width, gap,
            additem, delitem, copyitem, editmenu,
            additem_kwargs, delitem_kwargs, copyitem_kwargs, editmenu_kwargs,
            layout, lazyTabs, titleField, emptyTitle,
            titleTemplate, sortField, sortStore,
            collapsible, collapsedTemplate, chromeSide, card,
            defaultRow, minRows, maxRows, counterField,
            formulas, totals, rowTemplate, selectionmenu, rowCheckbox,
            selectionGroup, resolved_drag_code,
            loaderrpc, mapLoaderrpc):
        # Resolve the container via attributeOwnerNode at runtime: a fixed
        # containerNode kwarg would freeze on the template's sourceNode and
        # collide across row clones in nested groupletGrid.
        container.dataController("""
            var node = this.attributeOwnerNode('_gg_root');
            var bodyNode = node.getValue().walk(function(n){
                if (n.attr && n.attr._gg_body) return n;
            }, 'static');
            var entryNode = node.getValue().walk(function(n){
                if (n.attr && n.attr._gg_entry) return n;
            }, 'static');
            var selectionNode = node.getValue().walk(function(n){
                if (n.attr && n.attr._gg_selection) return n;
            }, 'static');
            node.gridController = new gnr.GroupletGridController(node, {
                bodyNode: bodyNode,
                entryNode: entryNode,
                selectionNode: selectionNode,
                rowTemplate: rowTemplate,
                selectionmenu: selectionmenu,
                rowCheckbox: rowCheckbox,
                selectionGroup: selectionGroup,
                resource: resource,
                handler: handler,
                resourceField: resourceField,
                structpath: structpath,
                table: table,
                grouplets_root: grouplets_root,
                grouplet_kw: grouplet_kw,
                store_kw: store_kw,
                cols: cols,
                min_width: min_width,
                gap: gap,
                additem: additem,
                delitem: delitem,
                copyitem: copyitem,
                editmenu: editmenu,
                additem_kw: additem_kw,
                delitem_kw: delitem_kw,
                copyitem_kw: copyitem_kw,
                editmenu_kw: editmenu_kw,
                layout: layout,
                lazyTabs: lazyTabs,
                titleField: titleField,
                titleTemplate: titleTemplate,
                sortField: sortField,
                sortStore: sortStore,
                collapsible: collapsible,
                collapsedTemplate: collapsedTemplate,
                chromeSide: chromeSide,
                card: card,
                emptyTitle: emptyTitle,
                defaultRow: defaultRow,
                minRows: minRows,
                maxRows: maxRows,
                counterField: counterField,
                formulas: formulas,
                totals: totals,
                dragCode: dragCode,
                loaderrpc: loaderrpc,
                mapLoaderrpc: mapLoaderrpc
            });
            node.externalWidget = node.gridController;
            node.registerDynAttr('storepath');
            node._setDynAttributes();
        """, _onBuilt=True,
            resource=resource,
            handler=handler_name,
            resourceField=resourceField,
            structpath=structpath,
            table=table,
            grouplets_root=grouplets_root,
            grouplet_kw=grouplet_kwargs or {},
            store_kw=store_kwargs or {},
            cols=int(cols),
            min_width=min_width,
            gap=gap,
            additem=additem,
            delitem=delitem,
            copyitem=copyitem,
            editmenu=editmenu,
            additem_kw=additem_kwargs or {},
            delitem_kw=delitem_kwargs or {},
            copyitem_kw=copyitem_kwargs or {},
            editmenu_kw=editmenu_kwargs or {},
            layout=layout,
            lazyTabs=lazyTabs,
            titleField=titleField,
            titleTemplate=titleTemplate,
            sortField=sortField,
            sortStore=sortStore,
            collapsible=collapsible,
            collapsedTemplate=collapsedTemplate,
            chromeSide=chromeSide or None,
            card=card,
            emptyTitle=emptyTitle,
            defaultRow=defaultRow,
            minRows=minRows,
            maxRows=maxRows,
            counterField=counterField,
            formulas=formulas or {},
            totals=totals,
            rowTemplate=rowTemplate,
            selectionmenu=selectionmenu,
            rowCheckbox=rowCheckbox,
            selectionGroup=selectionGroup,
            dragCode=resolved_drag_code,
            loaderrpc=loaderrpc,
            mapLoaderrpc=mapLoaderrpc)
