# encoding: utf-8
class Menu(object):
    def config(self, root, **kwargs):
        root.directoryBranch('!!Tests', folder='', tags='_DEV_')
        documents = root.branch('!!Test documents', tags='_DEV_')
        documents.docpage('!!HTML document', source='pkg:test/resources/test.html')
        # Deliberately exercises click-time 404 behavior.
        documents.docpage('!!HTML document (missing file)',
                          source='pkg:test/resources/does_not_exist.html')
