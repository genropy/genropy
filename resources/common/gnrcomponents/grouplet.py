from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import gnrImport
from gnr.web.gnrbaseclasses import BaseComponent


class GroupletHandler(BaseComponent):

    @public_method
    def gr_loadGrouplet(self, pane, resource=None, table=None,
                        handlername=None, valuepath=None, **kwargs):
        grouplet_module = None
        if resource:
            handlername = handlername or 'grouplet_main'
            if ':' not in resource:
                resource = f'{resource}:Grouplet'
            if table:
                mixinedClass = self.mixinTableResource(table, f'grouplets/{resource}', safeMode=True)
            else:
                mixinedClass = self.mixinComponent(resource)
            grouplet_module = getattr(mixinedClass, '__top_mixined_module', None)
        if not handlername:
            raise self.exception('generic', msg='Missing resource or method for handling grouplet')
        box = pane.contentPane(datapath=valuepath, grouplet_module=grouplet_module)
        return getattr(self, handlername)(box, **kwargs)

    @public_method
    def gr_getGroupletMenu(self, table=None, **kwargs):
        result = Bag()
        pkg, tblname = table.split('.')
        resources = Bag()
        resources_pkg = self.site.resource_loader.resourcesAtPath(
            page=self, pkg=pkg, path=f'tables/{tblname}/grouplets')
        resources_custom = self.site.resource_loader.resourcesAtPath(
            page=self, path=f'tables/_packages/{pkg}/{tblname}/grouplets')
        resources.update(resources_pkg)
        resources.update(resources_custom)
        for node in resources:
            if node.value:
                group_content = Bag()
                settings = Bag(node.value)
                info_node = settings.popNode('__info__')
                group_info = self._get_grouplet_info(info_node, table=table) if info_node else {}
                if group_info is False:
                    continue
                if not isinstance(group_info, dict):
                    group_info = {}
                group_info.setdefault('caption', node.attr.get('caption', node.label))
                group_info.setdefault('group', node.label)
                settings.popNode('__pycache__')
                if not settings:
                    continue
                result.addItem(node.label, group_content, **group_info)
                for child_node in settings:
                    info = self._get_grouplet_info(child_node, table=table)
                    if info is False:
                        continue
                    info['grouplet_caption'] = info['caption']
                    group_content.setItem(info['code'], None,
                                          resource=f'{node.label}/{child_node.label}',
                                          group_caption=group_info.get('caption'),
                                          group=group_info.get('group'),
                                          **info)
                group_content.sort('#a.priority,#a.caption')
            else:
                if node.label.startswith('__'):
                    continue
                info = self._get_grouplet_info(node, table=table)
                if info is False:
                    continue
                info['grouplet_caption'] = info['caption']
                result.setItem(info['code'], None,
                               resource=f'{node.label}',
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
                permissions and not self.checkTablePermission(table=table, permissions=permissions):
            return False
        is_enabled_cb = getattr(resmodule, 'is_enabled', None)
        if is_enabled_cb and is_enabled_cb(self) is False:
            return False
        return info
