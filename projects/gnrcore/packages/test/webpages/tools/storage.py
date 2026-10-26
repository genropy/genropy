# -*- coding: utf-8 -*-

"""Storage nodes: writing, addressing and copying files by storage path

`site.storageNode(path)` turns a storage path - `site:...`, `pkg:<package>/...`
and the other services of the instance - into a node that opens, copies and
answers the url of the file it points to, wherever the service keeps it. Every
write and every copy, source and destination alike, is confined to
`site:storage_test/`: any other path - another service, a path with no scheme
(the raw filesystem) or one with a `..` segment - is refused without touching
storage. The tree of `test_1` lists the `test` package read-only, the tree of
`test_2` lists `site:storage_test` itself, read-only too, to pick the file the
copy starts from; browsing storage with drag-and-drop is shown by
`sys/webpages/test/test_storageTree.py`.
"""

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.lib.services.storage import StorageResolver

STORAGE_TEST = 'site:storage_test/'


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_1_write(self, root, **kwargs):
        """Write the content into the storage path and read its url back

        The path must be under `site:storage_test/`. The url follows the path as
        it is typed; the tree lists the `.txt` files of the `test` package,
        read-only, through a `StorageResolver`.
        """
        fb = root.formbuilder()
        fb.data('.path', 'site:storage_test/sample.txt')
        fb.data('.content', 'Hello storage')
        fb.textbox(value='^.path', lbl='Path', width='40em')
        fb.simpleTextArea(value='^.content', lbl='Content')
        fb.button('Write', fire='.write')
        fb.div('^.write_result', lbl='Result')
        fb.dataRpc('.write_result', self.writeContent, _fired='^.write',
                   filepath='=.path', filecontent='=.content')

        fb.textbox(value='^.url', lbl='Url', width='40em', readOnly=True)
        fb.dataRpc('.url', self.url, filepath='^.path', _onStart=True)
        root.data('.store', StorageResolver(self.site.storageNode('pkg:test'), cacheTime=10,
                                            include='*.txt', exclude='_*,.*', dropext=True,
                                            readOnly=True, _page=self)())
        root.tree(storepath='.store', hideValues=True, inspect='shift', draggable=True, dragClass='draggedItem')

    @public_method
    def writeContent(self, filepath=None, filecontent=None):
        if not filepath:
            return 'Type a storage path first'
        if self.outsideStorageTest(filepath):
            return 'Refused: %s is not under %s' % (filepath, STORAGE_TEST)
        storageNode = self.site.storageNode(filepath)
        with storageNode.open(mode='w') as f:
            f.write(filecontent or '')
        return 'Written %s' % storageNode.fullpath

    @public_method
    def url(self, filepath=None, **kwargs):
        if not filepath:
            return
        return self.site.storageNode(filepath).url(**kwargs)

    def test_2_copy(self, root, **kwargs):
        """Pick a file of `site:storage_test` in the tree and copy it to another path of it

        Source and destination must both be under `site:storage_test/`: the file
        `test_1` wrote is there to pick, and the read-only tree reloads to show the
        copy. Browsing storage with drag-and-drop is shown by
        `sys/webpages/test/test_storageTree.py`.
        """
        bc = root.borderContainer(_anchor=True, height='400px')
        bc.data('#ANCHOR.destpath', 'site:storage_test/copied_file')
        bc.contentPane(region='center', border='1px solid silver', margin='2px', rounded=4,
                       overflow='auto').tree(storepath='#ANCHOR.store', hideValues=True,
                                             selected_abs_path='#ANCHOR.sourcepath')
        bc.dataRpc('#ANCHOR.store', self.getStorageTestTree, _onStart=True,
                   _fired='^#ANCHOR.reloadstore')

        fb = bc.contentPane(region='bottom').formbuilder()

        fb.textbox(value='^#ANCHOR.sourcepath', lbl='Source')
        fb.textbox(value='^#ANCHOR.destpath', lbl='Dest')
        fb.button('Copy', fire='.copy')
        fb.div('^#ANCHOR.copy_result', lbl='Result')
        fb.dataRpc('#ANCHOR.copy_result', self.copyFileTest, sourcepath='=#ANCHOR.sourcepath',
                   destpath='=#ANCHOR.destpath', _fired='^.copy', _onResult='FIRE #ANCHOR.reloadstore',
                   _lockScreen=True)

    @public_method
    def getStorageTestTree(self):
        result = Bag()
        result.setItem('root', StorageResolver(STORAGE_TEST.rstrip('/'), cacheTime=2,
                                               dropext=True, readOnly=True, _page=self)())
        return result

    @public_method
    def copyFileTest(self, sourcepath=None, destpath=None, **kwargs):
        if not (sourcepath and destpath):
            return 'Pick a source file and type a destination path first'
        for path in (sourcepath, destpath):
            if self.outsideStorageTest(path):
                return 'Refused: %s is not under %s' % (path, STORAGE_TEST)
        source = self.site.storageNode(sourcepath)
        dest = self.site.storageNode(destpath)
        source.copy(dest)
        return 'Copied to %s' % dest.fullpath

    def outsideStorageTest(self, path):
        return not path.startswith(STORAGE_TEST) or '..' in path.split('/')
