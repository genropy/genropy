import math
from gnr.core.gnrdecorator import extract_kwargs, public_method
from gnr.core.gnrbag import Bag
from gnr.core.gnrdict import dictExtract
from gnr.core.gnrlang import gnrImport
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrwebstruct import struct_method

class GroupletHandler(BaseComponent):
    css_requires = 'gnrcomponents/grouplet/grouplet'
    js_requires = 'gnrcomponents/grouplet/grouplet'

    @public_method
    def gr_loadGrouplet(self, pane, resource=None, table=None,
                        handlername=None, valuepath=None,
                        grouplets_root=None,rootTag='div', **kwargs):
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
        if info_method:
            grouplet_code = info_method().get('code')
            if grouplet_code:
                box_kw['grouplet_code'] = grouplet_code
        box = pane.child(rootTag,_class='grouplet_box', **box_kw)
        return handler(box, **kwargs)

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
            return {}
        if node.value:
            children = Bag(node.value)
            info_node = children.getNode('__info__')
            if not info_node:
                return {}
            node = info_node
        resmodule = gnrImport(node.attr['abs_path'], avoid_module_cache=True)
        info = self._get_raw_info(resmodule)
        result = {}
        if info.get('template'):
            result['template'] = info['template']
        if info.get('template_virtual_columns'):
            result['virtual_columns'] = info['template_virtual_columns']
        return result

    @extract_kwargs(grouplet=dict(slice_prefix=False, pop=True), template=True, btn=True)
    @struct_method
    def gr_groupletChunk(self, pane, value=None, template=None, name=None,
                         handler=None, resource=None, table=None,
                         title=None,
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
        kwargs.setdefault('_class', 'grouplet_chunk_box')
        grid_kw = dictExtract(kwargs, 'grid_', pop=True)
        root = pane.div(**kwargs)
        template_kwargs['template'] = template
        template_kwargs['datasource'] = value
        root.div(**template_kwargs)  # templatechunk
        btn = root.lightButton(**btn_kwargs)
        grouplet_kwargs['value'] = value.replace('^', '')
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
        btn.dataController("""
            let editor_kw = {..._kwargs};
            genro.dlg.memoryDataEditor(name,editor_kw,this);
        """, name=name, **grouplet_kwargs)
        return root

    @extract_kwargs(grouplet=dict(slice_prefix=False, pop=True))
    @struct_method
    def gr_groupletPanel(self, pane, table=None, topic=None, value=None,
                         frameCode=None, grouplets_root=None,
                         useForm=True, useRecordPath=False,
                         menuCallback=None,
                         grouplet_kwargs=None, **kwargs):
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
        if topic:
            grouplet_kwargs['grouplet_remote_topic'] = topic
            return self._groupletPanel_topic(
                pane, menu, frameCode=frameCode, formId=formId,
                useForm=useForm,
                grouplet_kwargs=grouplet_kwargs, **kwargs)
        return self._groupletPanel_tree(
            pane, menu, frameCode=frameCode, formId=formId,
            useForm=useForm,
            grouplet_kwargs=grouplet_kwargs, **kwargs)

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
            "gnr_grouplet.panelSelectFromCode(this, code);",
            code='^.selected_code', _onBuilt=1)
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
            bar.dataController("""
                                 if(genro.formById(innerFormId).status!='noItem'){
                                    genro.formById(innerFormId).reload()
                                 }
                                 """,
                                 innerFormId=formId,
                                 formsubscribe_onLoaded=True)
            center.GroupletForm(**grouplet_kwargs)
        else:
            center.grouplet(**grouplet_kwargs)
        return frame

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
            nodeId=f'{frameCode}_tree',
            getLabelClass="""
                if(!node.attr.grouplet_caption){ return 'grouplet_topic'; }
            """,
            connect_onClick="""
                if($2.item.attr.resource && $2.item.attr.grouplet_caption){
                    let itemInfo = $2.item.attr;
                    PUT .grouplet_info = new gnr.GnrBag(itemInfo);
                    PUT .selected_resource = itemInfo.resource;
                    SET .selected_caption = itemInfo.grouplet_caption;
                    SET .selected_fullpath = $2.item.getFullpath()
                }
            """)
        grouplet_kwargs['grouplet_remote__reloader'] = '^#ANCHOR.selected_fullpath'
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
            right.dataController("""
                                 if(genro.formById(innerFormId).status!='noItem'){
                                    genro.formById(innerFormId).reload()
                                 }
                                 """,
                                 innerFormId=formId,
                                 formsubscribe_onLoaded=True)
            center.GroupletForm(**grouplet_kwargs)
        else:
            center.grouplet(**grouplet_kwargs)
        return bc

    @extract_kwargs(grouplet=dict(slice_prefix=False, pop=True))
    @struct_method
    def gr_groupletWizard(self, pane, table=None, topic=None, value=None,
                          frameCode=None, completeLabel=None,
                          closeLabel=None,
                          saveMainFormOnComplete=None,
                          grouplets_root=None,grouplet_kwargs=True, **kwargs):
        frameCode = frameCode or 'grplt_wizard'
        completeLabel = completeLabel or 'Confirm'
        closeLabel = closeLabel or 'Close'
        root_info = self._getGroupletsRootInfo(table=table, topic=topic,
                                               grouplets_root=grouplets_root)
        summary_template = root_info.get('summary_template')
        summary_editable = root_info.get('summary_editable', False)
        has_summary = bool(summary_template)
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
        if has_summary:
            frame.data('.summary_editable', summary_editable)
        menu_nodes = menu.getNodes()
        first_node = menu_nodes[0] if menu_nodes else None
        if first_node:
            frame.data('.current_resource', first_node.attr.get('resource'))
            frame.data('.next_label',
                       menu_nodes[1].attr.get('grouplet_caption')
                       if total_steps > 1 else completeLabel)
        stepper_bar = frame.top.contentPane(_class='wizard_stepper_bar')
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
        step_form_id = f'{frameCode}_step_form'
        on_loaded_js = "gnr_grouplet.wizardGoTo(this, 0, frameCode);"
        if has_summary:
            on_loaded_js = """
                SET .wizard_showing_summary = false;
                SET .wizard_page = 'steps';
                if(this.form.isNewRecord()){
                    FIRE .step_index = 0;
                }else{
                    genro.publish(frameCode + '_show_summary');
                }
            """
        pane.dataController(on_loaded_js,
                            innerFormId=step_form_id,
                            frameCode=frameCode,
                            formsubscribe_onLoaded=True)
        grouplet_kwargs.update(resource='^#ANCHOR.current_resource',
                           value=value,
                           loadOnBuilt=True, formId=step_form_id,
                           form_modalForm=True)
        grouplet_kwargs['rootTag'] = 'contentPane'
        if table:
            grouplet_kwargs['table'] = table
        if grouplets_root:
            grouplet_kwargs['grouplets_root'] = grouplets_root

        if has_summary:
            frame.data('.wizard_page', 'steps')
            frame.data('.wizard_showing_summary', False)
            sc = frame.center.stackContainer(selectedPage='^.wizard_page')
            sc.contentPane(pageName='steps', overflow='auto').GroupletForm(
                **grouplet_kwargs)
            sc.contentPane(pageName='summary', overflow='auto',
                           _class='wizard_summary').div(
                template=summary_template, datasource=value)
        else:
            frame.center.contentPane(overflow='auto').GroupletForm(
                **grouplet_kwargs)
        bottom = frame.bottom.contentPane(_class='wizard_bottom_bar')
        if has_summary:
            bottom.lightButton('^.next_label',
                               _class='wizard_next_btn',
                               action="gnr_grouplet.wizardNext(this, _frameCode);",
                               _frameCode=frameCode,
                               hidden='==_showing',
                               _showing='^.wizard_showing_summary')
            bottom.lightButton(closeLabel,
                               _class='wizard_close_btn',
                               action="this.form.dismiss();",
                               hidden='==!_showing',
                               _showing='^.wizard_showing_summary')
        else:
            bottom.lightButton('^.next_label',
                               _class='wizard_next_btn',
                               action="gnr_grouplet.wizardNext(this, _frameCode);",
                               _frameCode=frameCode)
        frame.dataController(
            "gnr_grouplet.wizardUpdateStep(this, idx, _completeLabel, _frameCode);",
            idx='^.step_index',
            _completeLabel=completeLabel, _frameCode=frameCode, _onBuilt=True)
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


class GroupletGridHandler(BaseComponent):
    py_requires = 'gnrcomponents/grouplet/grouplet:GroupletHandler'
    css_requires = 'gnrcomponents/grouplet/grouplet'
    js_requires = ('gnrcomponents/grouplet/grouplet,'
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
            result.setItem(resource_path.replace('/', '_'), template,
                           resource=resource_path)
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
        additem=True, delitem=True, editmenu=True,
    )
    @struct_method
    def gr_groupletGrid(self, pane, datapath=None, storepath=None,
                        controllerPath=None,
                        resource=None, handler=None,
                        resourceField=None,
                        struct=None, structpath=None,
                        table=None, grouplets_root=None,
                        cols=1, min_width=None, gap='12px',
                        height=None, max_height=None, fillParent=False,
                        additem=True, delitem=True, editmenu=False,
                        layout='cards',
                        titleField=None,
                        emptyTitle='!!Untitled',
                        dragCode=None,
                        onSelfDropRows=None,
                        afterSelfDropRows=None,
                        minRows=0, maxRows=None,
                        defaultRow=None,
                        counterField=None,
                        grouplet_kwargs=None,
                        additem_kwargs=None,
                        delitem_kwargs=None,
                        editmenu_kwargs=None,
                        store_kwargs=None,
                        nodeId=None, **kwargs):
        # Author-supplied nodeIds inside the template must bake in `rowKey`
        # (or similar): the framework does NOT auto-rename them per row clone.
        nodeId = nodeId or kwargs.pop('gridId', None) or f'grpgrid_{id(pane)}'
        if editmenu is True:
            editmenu = {'addPrev': True, 'addNext': True}
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
        if framed:
            flavours.append('grouplet_grid--framed')
        if fillParent:
            flavours.append('grouplet_grid--fill')
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
        for side in ('top', 'bottom', 'left', 'right'):
            slot = container.div(
                _class=f'grouplet_grid_slot grouplet_grid_slot_{side}',
                childname=side, gg_side=side)
            # Pre-allocate placeholders: the JS adapter can only graft into
            # a leaf-empty sourceNode, never into a live one.
            if struct_mode and side == 'top':
                slot.div(_class='grouplet_grid__struct_header',
                         childname='struct_header')
            elif struct_mode and side == 'bottom':
                slot.div(_class='grouplet_grid__struct_footer',
                         childname='struct_footer')
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
            additem=additem, delitem=delitem, editmenu=editmenu,
            additem_kwargs=additem_kwargs,
            delitem_kwargs=delitem_kwargs,
            editmenu_kwargs=editmenu_kwargs,
            layout=layout, titleField=titleField, emptyTitle=emptyTitle,
            defaultRow=defaultRow, minRows=minRows, maxRows=maxRows,
            counterField=counterField,
            resolved_drag_code=resolved_drag_code,
            loaderrpc=self.gr_getGroupletGridTemplate,
            mapLoaderrpc=self.gr_getGroupletGridTemplateMap)
        return container

    def _gr_groupletGrid_emitController(
            self, container, *,
            resource, handler_name, resourceField, structpath, table,
            grouplets_root, grouplet_kwargs, store_kwargs,
            cols, min_width, gap,
            additem, delitem, editmenu,
            additem_kwargs, delitem_kwargs, editmenu_kwargs,
            layout, titleField, emptyTitle,
            defaultRow, minRows, maxRows, counterField,
            resolved_drag_code,
            loaderrpc, mapLoaderrpc):
        # Resolve the container via attributeOwnerNode at runtime: a fixed
        # containerNode kwarg would freeze on the template's sourceNode and
        # collide across row clones in nested groupletGrid.
        container.dataController("""
            var node = this.attributeOwnerNode('_gg_root');
            var bodyNode = node.getValue().walk(function(n){
                if (n.attr && n.attr._gg_body) return n;
            }, 'static');
            node.gridController = new gnr.GroupletGridController(node, {
                bodyNode: bodyNode,
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
                editmenu: editmenu,
                additem_kw: additem_kw,
                delitem_kw: delitem_kw,
                editmenu_kw: editmenu_kw,
                layout: layout,
                titleField: titleField,
                emptyTitle: emptyTitle,
                defaultRow: defaultRow,
                minRows: minRows,
                maxRows: maxRows,
                counterField: counterField,
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
            editmenu=editmenu,
            additem_kw=additem_kwargs or {},
            delitem_kw=delitem_kwargs or {},
            editmenu_kw=editmenu_kwargs or {},
            layout=layout,
            titleField=titleField,
            emptyTitle=emptyTitle,
            defaultRow=defaultRow,
            minRows=minRows,
            maxRows=maxRows,
            counterField=counterField,
            dragCode=resolved_drag_code,
            loaderrpc=loaderrpc,
            mapLoaderrpc=mapLoaderrpc)
