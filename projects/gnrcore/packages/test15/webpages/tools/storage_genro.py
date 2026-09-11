# -*- coding: utf-8 -*-

"""Storage: legacy services vs genro-storage (storage?use_genro_storage)"""

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.web.gnrwsgisite_proxy.gnrstoragehandler import (GenroStorageHandler,
                                                         LegacyStorageHandler)

TAKEN_OVER = ('local', 'raw', 'aws_s3')

# The node surface the two worlds must agree on, as (label, getter).
SURFACE = (
    ('exists', lambda n: n.exists),
    ('isfile', lambda n: n.isfile),
    ('isdir', lambda n: n.isdir),
    ('size', lambda n: n.size),
    ('mtime', lambda n: n.mtime),
    ('md5hash', lambda n: n.md5hash),
    ('basename', lambda n: n.basename),
    ('cleanbasename', lambda n: n.cleanbasename),
    ('ext', lambda n: n.ext),
    ('fullpath', lambda n: n.fullpath),
    ('internal_path', lambda n: n.internal_path),
    ('url', lambda n: n.url()),
    ('internal_url', lambda n: n.internal_url()),
    ('internal_url_nocache', lambda n: n.internal_url(nocache=True)),
    ('base64_bare', lambda n: (n.base64() or '')[:32]),
    ('base64_mime', lambda n: (n.base64(mime=True) or '')[:48]),
    ('listdir', lambda n: n.listdir()),
    ('children_count', lambda n: len(n.children() or [])),
    ('versions_count', lambda n: len(n.versions or [])),
    ('mimetype', lambda n: n.mimetype),
)


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/storagetree:StorageTree,
                     gnrcomponents/drop_uploader"""

    def windowTitle(self):
        return '!!Storage: legacy vs genro-storage'

    # ---- helpers

    @property
    def legacy_handler(self):
        """A legacy handler built on the side, to compare against whatever the
        site is currently using."""
        if not hasattr(self, '_legacy_handler'):
            self._legacy_handler = LegacyStorageHandler(self.site)
        return self._legacy_handler

    def _serviceLabel(self, service):
        if service is None:
            return 'none'
        module = service.__class__.__module__
        return 'genro-storage' if module.endswith('storage_genro') else 'legacy'

    def _readSurface(self, node):
        """Every member of the surface, with the failure kept as the value: an
        exception here is the interesting part, not something to hide."""
        result = Bag()
        for label, getter in SURFACE:
            try:
                value = getter(node)
            except Exception as exc:
                value = '%s: %s' % (exc.__class__.__name__, exc)
            result[label] = value if not isinstance(value, list) else ', '.join(
                str(item) for item in value[:6])
        return result

    # ---- tests

    def test_0_activeHandler(self, pane):
        """Which handler the site is using, and which mount each implementation
        is routed to. With the flag off everything is legacy: that is the
        default and it is correct."""
        handler = self.site.storage_handler
        is_genro = isinstance(handler, GenroStorageHandler)
        head = pane.div(padding='4px')
        head.div('handler: %s' % handler.__class__.__name__,
                 font_weight='bold', color='#2a6' if is_genro else '#a62')
        head.div('siteconfig storage?use_genro_storage: %r'
                 % self.site.config['storage?use_genro_storage'], color='#666')
        if not is_genro:
            head.div('The flag is off, so every row below says "legacy". '
                     'Set <storage use_genro_storage="True"/> in the siteconfig '
                     'to switch the mappable mounts over.',
                     color='#a62', padding_top='4px')

        table = pane.div(margin_top='6px').table(border_collapse='collapse',
                                                 font_family='monospace', font_size='.85em')
        header = table.tbody().tr(background='#eee')
        for title in ('mount', 'implementation', 'served by', 'note'):
            header.td(title, padding='2px 8px', border='1px solid #ccc', font_weight='bold')
        body = table.tbody()
        for mount_name in sorted(handler.storage_params):
            params = handler.storage_params[mount_name]
            implementation = params.get('implementation')
            service = handler.storage(mount_name)
            served_by = self._serviceLabel(service)
            note = ''
            if implementation not in TAKEN_OVER:
                note = 'not replaceable: stays legacy by design'
            elif served_by == 'legacy' and is_genro:
                note = 'mappable but skipped (check the site log for the reason)'
            row = body.tr()
            row.td(mount_name, padding='2px 8px', border='1px solid #ccc')
            row.td(implementation or '', padding='2px 8px', border='1px solid #ccc')
            row.td(served_by, padding='2px 8px', border='1px solid #ccc',
                   color='#2a6' if served_by == 'genro-storage' else '#888')
            row.td(note, padding='2px 8px', border='1px solid #ccc', color='#a62')

    def test_1_treeTakenOver(self, pane):
        """Tree on a mount genro-storage takes over when the flag is on
        (local). Everything the frame does goes through the storage layer:
        children, mkdir, drag-and-drop move, drop-to-upload, download,
        internal_url for the preview."""
        pane.data('.storagepath', 'site:')
        fb = pane.formbuilder(cols=4, border_spacing='3px')
        fb.textbox(value='^.storagepath', lbl='Path', width='24em')
        for quick in ('site:', 'home:', 'site:uploads'):
            fb.button(quick, action='SET .storagepath = %r;' % quick)
        pane.storageTreeFrame(frameCode='genroStorageTree', storagepath='^.storagepath',
                              border='1px solid silver', margin_top='4px', rounded=4,
                              height='340px', store__onBuilt=True,
                              preview_region='right', preview_width='50%',
                              preview_border_left='1px solid silver')

    def test_2_treeLegacyOnly(self, pane):
        """Tree on the mounts that stay legacy even with the flag on. These must
        behave exactly as they do today: symbolic resolves through the site
        (resources, packages, the temp dir), and no storage library can know
        about that."""
        pane.data('.storagepath', 'pkg:sys')
        fb = pane.formbuilder(cols=5, border_spacing='3px')
        fb.textbox(value='^.storagepath', lbl='Path', width='24em')
        for quick in ('pkg:sys', 'rsrc:', 'temp:', 'pages:'):
            fb.button(quick, action='SET .storagepath = %r;' % quick)
        pane.storageTreeFrame(frameCode='legacyStorageTree', storagepath='^.storagepath',
                              border='1px solid silver', margin_top='4px', rounded=4,
                              height='340px', store__onBuilt=True,
                              preview_region='right', preview_width='50%',
                              preview_border_left='1px solid silver')

    def test_3_nodeInspector(self, pane):
        """The whole legacy StorageNode surface on one path, with the service
        that answered it. Type any path: a failure is shown as the value."""
        pane.data('.storagepath', 'site:uploads')
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.textbox(value='^.storagepath', lbl='Path', width='40em', colspan=2)
        fb.button('Read', fire='.read')
        fb.div('^.served_by', lbl='Served by', font_weight='bold')
        box = pane.div(_class='selectable', margin_top='4px')
        box.dataRpc('.result', self.inspectNode, storagepath='=.storagepath',
                    _fired='^.read', served_by='.served_by')
        box.div('^.result?=#v?#v.getFormattedValue():""', white_space='pre',
                font_family='monospace', font_size='.85em')

    @public_method
    def inspectNode(self, storagepath=None, **kwargs):
        if not storagepath:
            return Bag()
        node = self.site.storageNode(storagepath)
        self.setInClientData(path='test.test_3_nodeInspector.served_by',
                             value='%s (%s)' % (self._serviceLabel(node.service),
                                                node.service.service_implementation))
        return self._readSurface(node)

    def test_4_sideBySide(self, pane):
        """The same path read twice: once through the handler the site is using,
        once through a legacy handler built on the side. Every row that differs
        is highlighted - this is the parity test, on screen."""
        pane.data('.storagepath', 'site:uploads')
        fb = pane.formbuilder()
        fb.textbox(value='^.storagepath', lbl='Path', width='40em')
        fb.button('Compare', fire='.compare')
        pane.dataRpc('.result', self.compareHandlers, storagepath='=.storagepath',
                     _fired='^.compare')
        grid = pane.div(margin_top='4px', overflow='auto')
        grid.tree(storepath='.result', hideValues=False, labelAttribute='caption',
                  font_family='monospace', font_size='.85em')

    @public_method
    def compareHandlers(self, storagepath=None, **kwargs):
        if not storagepath:
            return Bag()
        active_node = self.site.storageNode(storagepath)
        legacy_node = self.legacy_handler.storageNode(storagepath)
        active = self._readSurface(active_node)
        legacy = self._readSurface(legacy_node)
        result = Bag()
        result.setItem('_handlers', None, caption='active=%s | side=%s' % (
            self._serviceLabel(active_node.service), self._serviceLabel(legacy_node.service)))
        for label, _getter in SURFACE:
            active_value = active[label]
            legacy_value = legacy[label]
            same = active_value == legacy_value
            row = Bag()
            row['active'] = active_value
            row['legacy'] = legacy_value
            result.setItem(label, row, caption='%s %s' % ('=' if same else '≠', label))
        return result

    def test_5_uploader(self, pane):
        """Upload a file into a storage mount and read back what the storage
        layer says about it. Drop a file, or double click."""
        pane.data('.uploadpath', 'site:uploads')
        fb = pane.formbuilder(cols=1, colswidth='100%')
        fb.textbox(value='^.uploadpath', lbl='Destination', width='24em')
        fb.div(lbl='File').dropUploader(
            height='100px', width='340px', progressBar=True,
            label="<div style='padding:20px'>Drop a file here<br>or double click</div>",
            uploadPath='^.uploadpath',
            onUploadedMethod=self.onFileUploaded)
        fb.textbox('^.uploaded_path', lbl='Path', readOnly=True, width='100%',
                   hidden='^.uploaded_path?=!#v')
        fb.textbox('^.uploaded_served_by', lbl='Served by', readOnly=True,
                   hidden='^.uploaded_path?=!#v')
        fb.textbox('^.uploaded_size', lbl='Size (bytes)', readOnly=True,
                   hidden='^.uploaded_path?=!#v')
        fb.textbox('^.uploaded_md5', lbl='md5hash', readOnly=True, width='100%',
                   hidden='^.uploaded_path?=!#v')
        fb.textbox('^.uploaded_url', lbl='url()', readOnly=True, width='100%',
                   hidden='^.uploaded_path?=!#v')

    @public_method
    def onFileUploaded(self, file_path=None, **kwargs):
        node = self.site.storageNode(file_path)
        datapath = 'test.test_5_uploader'
        for name, value in (('uploaded_path', file_path),
                            ('uploaded_served_by', self._serviceLabel(node.service)),
                            ('uploaded_size', node.size),
                            ('uploaded_md5', node.md5hash),
                            ('uploaded_url', node.url())):
            self.setInClientData(path='%s.%s' % (datapath, name), value=value)
        self.clientPublish('floating_message',
                           message='Uploaded through the %s service'
                                   % self._serviceLabel(node.service))

    def test_6_crossWorld(self, pane):
        """Copy and move between a mount genro-storage serves and one the legacy
        service serves. StorageService bridges the two by content when the
        locations differ, so this must work in both directions."""
        pane.data('.source', 'site:uploads')
        pane.data('.dest', 'temp:gnr_crossworld_probe.txt')
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.textbox(value='^.source', lbl='Source', width='34em')
        fb.textbox(value='^.dest', lbl='Destination', width='34em')
        fb.button('Copy', fire='.copy')
        fb.button('Move', fire='.move')
        pane.dataRpc('.result', self.crossWorld, source='=.source', dest='=.dest',
                     action='copy', _fired='^.copy', _lockScreen=True)
        pane.dataRpc('.result', self.crossWorld, source='=.source', dest='=.dest',
                     action='move', _fired='^.move', _lockScreen=True)
        pane.div('^.result?=#v?#v.getFormattedValue():""', white_space='pre',
                 font_family='monospace', font_size='.85em', margin_top='4px')

    @public_method
    def crossWorld(self, source=None, dest=None, action=None, **kwargs):
        result = Bag()
        if not (source and dest):
            return result
        source_node = self.site.storageNode(source)
        dest_node = self.site.storageNode(dest)
        result['action'] = action
        result['source_served_by'] = self._serviceLabel(source_node.service)
        result['dest_served_by'] = self._serviceLabel(dest_node.service)
        result['same_location'] = (source_node.service.location_identifier
                                   == dest_node.service.location_identifier)
        if not source_node.exists:
            result['error'] = 'source does not exist'
            return result
        try:
            if action == 'move':
                source_node.move(dest_node)
                result['source_after_move'] = source_node.fullpath
            else:
                source_node.copy(dest_node)
            result['dest_exists'] = dest_node.exists
            result['dest_size'] = dest_node.size
        except Exception as exc:
            result['error'] = '%s: %s' % (exc.__class__.__name__, exc)
        return result

    def test_7_s3Mount(self, pane):
        """Tree on an S3 mount, to exercise the remote half. Needs a storage
        service of implementation aws_s3 - a local MinIO is enough - declared
        either in sys.service or in the siteconfig."""
        handler = self.site.storage_handler
        remote_mounts = [name for name, params in handler.storage_params.items()
                         if params.get('implementation') == 'aws_s3']
        if not remote_mounts:
            pane.div('No aws_s3 storage service is configured on this site: '
                     'declare one in sys.service or in the siteconfig, then reload.',
                     color='#a62', padding='4px')
            return
        pane.data('.storagepath', '%s:' % sorted(remote_mounts)[0])
        fb = pane.formbuilder(cols=1 + len(remote_mounts), border_spacing='3px')
        fb.textbox(value='^.storagepath', lbl='Path', width='24em')
        for name in sorted(remote_mounts):
            fb.button('%s:' % name, action='SET .storagepath = %r;' % ('%s:' % name))
        pane.storageTreeFrame(frameCode='s3StorageTree', storagepath='^.storagepath',
                              border='1px solid silver', margin_top='4px', rounded=4,
                              height='340px', store__onBuilt=True,
                              preview_region='right', preview_width='50%',
                              preview_border_left='1px solid silver')
