import math
from gnr.core.gnrdecorator import extract_kwargs, public_method
from gnr.core.gnrbag import Bag
from gnr.core.gnrdict import dictExtract
from gnr.core.gnrlang import gnrImport
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrwebstruct import struct_method


class GroupletHandler(BaseComponent):
    css_requires = 'gnrcomponents/grouplet'
    js_requires = 'gnrcomponents/grouplet'

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
                           valuepath=None, grouplets_root=None, **kwargs):
        grid_kwargs = dictExtract(kwargs, 'grid_', pop=True)
        columns = int(grid_kwargs.pop('columns', 1))
        template_columns = grid_kwargs.pop('template_columns', None)
        collapsible = grid_kwargs.pop('collapsible', False)
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
        start_closed = (collapsible == 'closed')
        for node in topic_menu:
            attr = node.attr
            cell_class = 'grouplet_topic_cell'
            if start_closed:
                cell_class += ' collapsed'
            cell = grid.div(_class=cell_class)
            caption_text = attr.get('grouplet_caption') or attr.get('caption', '')
            if collapsible:
                caption = cell.lightButton(
                    _class='grouplet_topic_cell_caption',
                    action='gnr_grouplet.toggleGroupletCell(this.domNode.parentNode);')
                caption.span(_class='grouplet_topic_toggle')
                caption.span(caption_text)
            else:
                cell.div(caption_text, _class='grouplet_topic_cell_caption')
            content_kw = {}
            if start_closed:
                content_kw['max_height'] = '0'
            content = cell.div(_class='grouplet_topic_cell_content', **content_kw)
            if node.value:
                self._loadGroupletTopic(content, node.value,
                                        table=table,
                                        valuepath=f'.{attr.get("topic", node.label)}',
                                        grouplets_root=grouplets_root,
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
        root = pane.div(position='relative', **kwargs)
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
                         grouplet_kwargs=None, **kwargs):
        frameCode = frameCode or 'grplt_panel'
        formId = f'{frameCode}_grpform'
        grouplet_kwargs.update(resource='^#ANCHOR.selected_resource',
                               value=value,
                               panelMode=True, formId=formId,
                               store_autoSave=1)
        if table:
            grouplet_kwargs['table'] = table
        if grouplets_root:
            grouplet_kwargs['grouplets_root'] = grouplets_root
        grouplet_kwargs['rootTag'] = 'contentPane'
        menu = self.gr_getGroupletMenu(table=table, topic=topic,
                                       grouplets_root=grouplets_root)
        if topic:
            grouplet_kwargs['grouplet_remote_topic'] = topic
            return self._groupletPanel_topic(
                pane, menu, frameCode=frameCode, formId=formId,
                grouplet_kwargs=grouplet_kwargs, **kwargs)
        return self._groupletPanel_tree(
            pane, menu, frameCode=frameCode, formId=formId,
            grouplet_kwargs=grouplet_kwargs, **kwargs)

    def _groupletPanel_topic(self, pane, menu, frameCode=None,
                             formId=None, grouplet_kwargs=None, **kwargs):
        frame = pane.framePane(frameCode=frameCode, _anchor=True, **kwargs)
        frame.data('.grouplet_menu', menu)
        bar_id = f'{frameCode}_bar'
        frame.dataController("""
            var barNode = genro.nodeById(barId);
            if(barNode){
                ['ok','changed','error'].forEach(function(s){
                    genro.dom.setClass(barNode, 'grplt_status_' + s, s == status);
                });
            }
        """, barId=bar_id,
            **{f'subscribe_form_{formId}_onStatusChange': True})
        bar = frame.top.slotBar('*,mb,*', _class='mobile_bar',
                                nodeId=bar_id)
        bar.mb.multibutton(value='^.selected_code',
                           storepath='.grouplet_menu')
        bar.dataController(
            "gnr_grouplet.panelSelectFromCode(this, code);",
            code='^.selected_code', _onBuilt=1)
        bar.dataController("genro.formById(innerFormId).reload()",innerFormId=formId,formsubscribe_onLoaded=True)

        frame.center.contentPane(
            overflow='auto').GroupletForm(**grouplet_kwargs)
        return frame

    def _groupletPanel_tree(self, pane, menu, frameCode=None,
                            formId=None, grouplet_kwargs=None, **kwargs):
        bc = pane.borderContainer(_anchor=True, **kwargs)
        bc.data('.grouplet_menu', menu)
        semaphore_id = f'{frameCode}_semaphore'
        bc.dataController("""
            var semNode = genro.nodeById(semId);
            if(semNode){
                ['ok','changed','error'].forEach(function(s){
                    genro.dom.setClass(semNode, 'semaphore_' + s,
                        selectedResource && s == status);
                });
            }
        """, semId=semaphore_id, selectedResource='=.selected_resource',
            **{f'subscribe_form_{formId}_onStatusChange': True})
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
            _class='branchtree noIcon grouplet_tree',
            selectedLabelClass='selectedTreeNode',
            openOnClick=True,
            nodeId=f'{frameCode}_tree',
            getLabelClass="""
                if(!node.attr.grouplet_caption){ return 'grouplet_topic'; }
            """,
            connect_onClick="""
                if($2.item.attr.resource && $2.item.attr.grouplet_caption){
                    SET .selected_resource = $2.item.attr.resource;
                    SET .selected_caption = $2.item.attr.grouplet_caption;
                }
            """)
        right = bc.borderContainer(region='center')
        top = right.contentPane(region='top',
                                _class='grouplet_panel_title_bar')
        top.div('^.selected_caption',
                _class='grouplet_panel_title')
        top.div(_class='grouplet_panel_semaphore',
                nodeId=semaphore_id)
        right.dataController("genro.formById(innerFormId).reload()",innerFormId=formId,formsubscribe_onLoaded=True)
        right.contentPane(
            region='center', overflow='auto').GroupletForm(
                **grouplet_kwargs)
        return bc

    @extract_kwargs(grouplet=dict(slice_prefix=False, pop=True))
    @struct_method
    def gr_groupletWizard(self, pane, table=None, topic=None, value=None,
                          frameCode=None, completeLabel=None,
                          saveMainFormOnComplete=None,
                          grouplets_root=None,grouplet_kwargs=True, **kwargs):
        frameCode = frameCode or 'grplt_wizard'
        completeLabel = completeLabel or 'Confirm'
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
        menu_nodes = menu.getNodes()
        first_node = menu_nodes[0] if menu_nodes else None
        if first_node:
            frame.data('.current_resource', first_node.attr.get('resource'))
            frame.data('.next_label',
                       menu_nodes[1].attr.get('grouplet_caption')
                       if total_steps > 1 else completeLabel)
        stepper = frame.top.contentPane(_class='wizard_stepper_bar').div(
            _class='wizard_stepper')
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
        grouplet_kwargs.update(resource='^#ANCHOR.current_resource',
                           value=value,
                           loadOnBuilt=True, formId=step_form_id,
                           form_modalForm=True)
        grouplet_kwargs['rootTag'] = 'contentPane'
        if table:
            grouplet_kwargs['table'] = table
        if grouplets_root:
            grouplet_kwargs['grouplets_root'] = grouplets_root
        frame.center.contentPane(overflow='auto').GroupletForm(**grouplet_kwargs)
        bottom = frame.bottom.contentPane(_class='wizard_bottom_bar')
        bottom.lightButton('^.next_label',
                           _class='wizard_next_btn',
                           action="gnr_grouplet.wizardNext(this, _frameCode);",
                           _frameCode=frameCode)
        frame.dataController(
            "gnr_grouplet.wizardUpdateStep(this, idx, _completeLabel, _frameCode);",
            idx='^.step_index',
            _completeLabel=completeLabel, _frameCode=frameCode, _onBuilt=True)
        if saveMainFormOnComplete:
            frame.dataController("""
                this.form.save({destPkey:'*dismiss*'});
            """, **{f'subscribe_{frameCode}_complete': True})
        return frame

    @public_method
    def gr_getGroupletMenu(self, table=None, topic=None,
                           grouplets_root=None, **kwargs):
        result = Bag()
        resources = Bag()
        grouplets_root = grouplets_root or 'grouplets'
        grouplets_path = grouplets_root
        if topic:
            grouplets_path = f'{grouplets_path}/{topic}'
        if table:
            pkg, tblname = table.split('.')
            resources_pkg = self.site.resource_loader.resourcesAtPath(
                page=self, pkg=pkg, path=f'tables/{tblname}/{grouplets_path}')
            resources_custom = self.site.resource_loader.resourcesAtPath(
                page=self, path=f'tables/_packages/{pkg}/{tblname}/{grouplets_path}')
            resources.update(resources_pkg)
            resources.update(resources_custom)
        else:
            resources.update(self.site.resource_loader.resourcesAtPath(
                page=self, path=grouplets_path))
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
