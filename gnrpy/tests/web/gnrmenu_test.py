import gnr.web.gnrmenu  # noqa: F401

from gnr.web.gnrmenu import DirectoryMenuResolver


class FakeStorageNode(object):
    def __init__(self, path, isdir=False, children=None):
        self.path = path
        self.isdir = isdir
        self.isfile = not isdir
        self._children = children

    @property
    def basename(self):
        return self.path.rsplit('/', 1)[-1]

    @property
    def cleanbasename(self):
        return self.basename.rsplit('.', 1)[0]

    @property
    def ext(self):
        if self.isdir or '.' not in self.basename:
            return ''
        return self.basename.rsplit('.', 1)[-1]

    def children(self):
        return self._children


class FakeSite(object):
    def __init__(self, node):
        self.node = node
        self.calls = []

    def storageNode(self, *args):
        self.calls.append(args)
        return self.node


class FakePage(object):
    def __init__(self, node):
        self.site = FakeSite(node)


def makeResolver(node, **kwargs):
    return DirectoryMenuResolver(_page=FakePage(node), **kwargs)


def test_missing_folder_defaults_to_webpages_root():
    """A directoryBranch with no folder must ask for the webpages root, not None.

    `_adapt_path` joins its args with '/', so a None folder raises TypeError.
    """
    node = FakeStorageNode('test/webpages', isdir=True, children=[])
    resolver = makeResolver(node, pkg='test')
    resolver.sourceBag
    assert resolver._page.site.calls == [('pkg:test/webpages', '')]


def test_missing_folder_defaults_to_webpages_root_without_pkg():
    node = FakeStorageNode('webpages', isdir=True, children=[])
    resolver = makeResolver(node)
    resolver.sourceBag
    assert resolver._page.site.calls == [('site:webpages', '')]


def test_non_directory_folder_yields_empty_menu():
    """StorageNode.children() returns None when the path is not a directory."""
    node = FakeStorageNode('test/webpages/nowhere', isdir=True, children=None)
    result = makeResolver(node, pkg='test', folder='nowhere').sourceBag
    assert len(result) == 0


def test_underscore_folders_are_skipped():
    children = [
        FakeStorageNode('test/webpages/_resources', isdir=True),
        FakeStorageNode('test/webpages/__pycache__', isdir=True),
        FakeStorageNode('test/webpages/ui_builder', isdir=True),
        FakeStorageNode('test/webpages/iframe_inside.py'),
        FakeStorageNode('test/webpages/readme.txt'),
    ]
    node = FakeStorageNode('test/webpages', isdir=True, children=children)
    result = makeResolver(node, pkg='test', folder='').sourceBag
    labels = [n.attr.get('label') for n in result]
    assert labels == ['Ui Builder', 'Iframe Inside']
    assert result.getNode('#1').attr['filepath'] == '/test/iframe_inside'
