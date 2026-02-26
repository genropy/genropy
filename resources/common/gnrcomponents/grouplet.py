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
                        handlername=None, valuepath=None, **kwargs):
        grouplet_module = None
        if not resource:
            if not handlername:
                raise self.exception('generic', msg='Missing resource or method for handling grouplet')
            handler = self.getPublicMethod('remote', handlername)
            box = pane.contentPane(datapath=valuepath)
            return handler(box, **kwargs)
        # Check if resource is a topic (folder with child grouplets)
        topic_menu = self.gr_getGroupletMenu(table=table, topic=resource)
        if topic_menu:
            return self._loadGroupletTopic(pane, topic_menu,
                                           table=table, valuepath=valuepath,
                                           **kwargs)
        # Single grouplet
        handlername = handlername or 'grouplet_main'
        if ':' not in resource:
            resource = f'{resource}:Grouplet'
        if table:
            mixinedClass = self.mixinTableResource(table, f'grouplets/{resource}', safeMode=True)
        else:
            mixinedClass = self.mixinComponent(f'grouplets/{resource}')
        grouplet_module = getattr(mixinedClass, '__top_mixined_module', None)
        handler = getattr(self, handlername)
        box = pane.contentPane(datapath=valuepath, grouplet_module=grouplet_module)
        return handler(box, **kwargs)

    def _loadGroupletTopic(self, pane, topic_menu, table=None,
                           valuepath=None, **kwargs):
        import math
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
            caption_text = attr.get('grouplet_caption', '')
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
            self.gr_loadGrouplet(content, resource=attr['resource'],
                                 table=table, **kwargs)

    def gr_getTemplatePars(self, resource=None, table=None):
        clean_resource = resource.split(':')[0] if ':' in resource else resource
        if '/' in clean_resource:
            parent, name = clean_resource.rsplit('/', 1)
            search_path = f'grouplets/{parent}'
        else:
            name = clean_resource
            search_path = 'grouplets'
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
        info = getattr(resmodule, 'info', {})
        result = {}
        if info.get('template'):
            result['template'] = info['template']
        if info.get('template_virtual_columns'):
            result['virtual_columns'] = info['template_virtual_columns']
        return result

    @extract_kwargs(grouplet=True,template=True,btn=True)
    @struct_method
    def gr_groupletChunk(self, pane, value=None, template=None, name=None,
                         handler=None, resource=None, table=None,
                         title=None,
                         virtual_columns=None,
                         grouplet_kwargs=None,template_kwargs=None,
                         btn_kwargs=None, **kwargs):
        if resource and not template:
            tpars = self.gr_getTemplatePars(resource=resource, table=table)
            template = tpars.get('template')
            virtual_columns = virtual_columns or tpars.get('virtual_columns')
        root_kw = {}
        if virtual_columns:
            root_kw['_virtual_columns'] = virtual_columns
        btn_kwargs.setdefault('_class','iconbox pencil')
        btn_kwargs.setdefault('height','14px')
        btn_kwargs.setdefault('position','absolute')
        btn_kwargs.setdefault('bottom','2px')
        btn_kwargs.setdefault('right','2px')
        kwargs.setdefault('_class', 'grouplet_chunk_box')

        grid_kw = dictExtract(kwargs, 'grid_', pop=True)
        root = pane.div(position='relative',**kwargs)
        template_kwargs['template'] = template
        template_kwargs['datasource'] = value
        root.div(**template_kwargs) #templatechunk
        btn = root.lightButton(**btn_kwargs)
        grouplet_kwargs['value'] = value.replace('^','')
        if resource:
            grouplet_kwargs['resource'] = resource
        if table:
            grouplet_kwargs['table'] = table
        if title:
            grouplet_kwargs['title'] = title
        if handler:
            grouplet_kwargs['handler'] = handler
        for k, v in grid_kw.items():
            grouplet_kwargs[f'grouplet_remote_grid_{k}'] = v
        btn.dataController("""
            let editor_kw = {..._kwargs};
            genro.dlg.memoryDataEditor(name,editor_kw,this);
        """,name=name, **grouplet_kwargs)
        return root
    
    @extract_kwargs(grouplet=True)
    @struct_method
    def gr_groupletPanel(self, pane, table=None, topic=None, value=None,
                         frameCode=None,grouplet_kwargs=None, **kwargs):
        frameCode = frameCode or 'grplt_panel'
        frame = pane.framePane(frameCode=frameCode, _anchor=True, **kwargs)
        frame.data('.grouplet_menu',
                   self.gr_getGroupletMenu(table=table, topic=topic))
        grouplet_kwargs.update(resource='^.selected_resource',value=value)
        if table:
            grouplet_kwargs['table'] = table
        if topic:
            bar = frame.top.slotBar('*,mb,*', _class='mobile_bar')
            bar.mb.multibutton(value='^.selected_code',
                               storepath='.grouplet_menu')
            bar.dataController(
                "gnr_grouplet.panelSelectFromCode(this, code);",
                code='^.selected_code', _onBuilt=1)
            frame.center.contentPane(overflow='auto').grouplet(**grouplet_kwargs)
        else:
            bc = frame.center.borderContainer()
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
                    if($2.item.attr.resource){
                        SET .selected_resource = $2.item.attr.resource;
                        SET .selected_caption = $2.item.attr.grouplet_caption;
                    }
                """)
            right = bc.borderContainer(region='center')
            top = right.contentPane(region='top',
                                    _class='grouplet_panel_title_bar')
            top.div('^.selected_caption',
                    _class='grouplet_panel_title')
            right.contentPane(region='center', overflow='auto').grouplet(
                **grouplet_kwargs)
        return frame

    @struct_method
    def gr_groupletWizard(self, pane, table=None, topic=None, value=None,
                          frameCode=None, completeLabel=None,
                          saveMainFormOnComplete=None, **kwargs):
        frameCode = frameCode or 'grplt_wizard'
        completeLabel = completeLabel or 'Confirm'
        frame = pane.framePane(frameCode=frameCode, _anchor=True, **kwargs)
        menu = self.gr_getGroupletMenu(table=table, topic=topic)
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
        grouplet_kw = dict(resource='^#ANCHOR.current_resource',
                           value=value,
                           loadOnBuilt=True, formId=step_form_id,
                           form_modalForm=True)
        if table:
            grouplet_kw['table'] = table
        frame.center.contentPane(overflow='auto').GroupletForm(**grouplet_kw)
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
    def gr_getGroupletMenu(self, table=None, topic=None, **kwargs):
        result = Bag()
        resources = Bag()
        grouplets_path = 'grouplets'
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
        for node in resources:
            if node.value:
                topic_content = Bag()
                children = Bag(node.value)
                info_node = children.popNode('__info__')
                topic_info = self._get_grouplet_info(info_node, table=table) if info_node else {}
                if topic_info is False:
                    continue
                if not isinstance(topic_info, dict):
                    topic_info = {}
                topic_info.setdefault('caption', node.attr.get('caption', node.label))
                topic_info.setdefault('topic', node.label)
                children.popNode('__pycache__')
                if not children:
                    continue
                result.addItem(node.label, topic_content, **topic_info)
                for child_node in children:
                    info = self._get_grouplet_info(child_node, table=table)
                    if info is False:
                        continue
                    info['grouplet_caption'] = info['caption']
                    resource_path = f'{node.label}/{child_node.label}'
                    if topic:
                        resource_path = f'{topic}/{resource_path}'
                    topic_content.setItem(info['code'], None,
                                          resource=resource_path,
                                          topic_caption=topic_info.get('caption'),
                                          topic=topic_info.get('topic'),
                                          **info)
                topic_content.sort('#a.priority,#a.caption')
            else:
                if node.label.startswith('__'):
                    continue
                info = self._get_grouplet_info(node, table=table)
                if info is False:
                    continue
                info['grouplet_caption'] = info['caption']
                resource_path = f'{topic}/{node.label}' if topic else node.label
                result.setItem(info['code'], None,
                               resource=resource_path,
                               **info)
        result.sort('#a.priority,#a.caption')
        return result

    def gr_groupletAddrowMenu(self, table=None, field=None):
        menu = self.gr_getGroupletMenu(table=table)
        result = Bag()
        for node in menu:
            if node.value:
                group_bag = Bag()
                for child in node.value:
                    group_bag.setItem(child.label, None,
                                      caption=child.attr.get('grouplet_caption'),
                                      default_kw={field: child.attr.get('resource')})
                result.setItem(node.label, group_bag,
                               caption=node.attr.get('caption'))
            else:
                result.setItem(node.label, None,
                               caption=node.attr.get('grouplet_caption'),
                               default_kw={field: node.attr.get('resource')})
        return result

    def _get_grouplet_info(self, node, table=None):
        resmodule = gnrImport(node.attr['abs_path'], avoid_module_cache=True)
        info = getattr(resmodule, 'info', {})
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
