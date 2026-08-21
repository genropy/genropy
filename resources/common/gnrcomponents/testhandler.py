# -*- coding: utf-8 -*-

# testhandler.py
# Created by Giovanni Porcari on 2010-08-09.
# Copyright (c) 2011 Softwell. All rights reserved.

import os
import re
import sys

from gnr.web.gnrbaseclasses import BaseComponent

# the attributes through which a widget names the table it is built over
TABLE_ATTRIBUTES = ('table', 'dbtable')
TABLE_REFERENCE = re.compile(r'^\w+\.\w+$')


class TestHandler(BaseComponent):
    #py_requires='gnrcomponents/source_viewer/source_viewer:SourceViewer'
    css_requires = 'gnrcomponents/testhandler'
    testOnly = False
    dojo_source = True

    def isDeveloper(self):
        return True

    def testHandler(self, pane):
        container = pane.div(_class='test_handler_container')
        module_doc = getattr(sys.modules.get(self.__module__), '__doc__', None)
        title_text = module_doc.strip().split('\n')[0] if module_doc else 'Test'
        container.div(title_text, _class='test_handler_title')
        self.testHandler_loop(container)

    def testHandler_loop(self, pane):
        def skip_test(test_name):
            if not self.testOnly:
                return False
            if isinstance(self.testOnly, str):
                self.testOnly = [self.testOnly]
            for testOne in self.testOnly:
                if testOne in test_name:
                    return False
            return True
        test_to_do = [n for n in dir(self) if n.startswith('test_')]
        test_to_do.sort()
        for test_name in test_to_do:
            if skip_test(test_name):
                continue
            test_handler = getattr(self, test_name)
            card = pane.div(_class='test_handler_card',
                            datapath='test.%s' % test_name)
            card.div(test_name, _class='test_handler_card_header')
            docline = card.div(_class='test_handler_card_doc')
            doc = test_handler.__doc__ or ''
            if doc:
                docline.div(doc)
            body = card.div(_class='test_handler_card_body')
            test_handler(body)
            self.testHandler_dataWarning(docline, body)
            if not len(docline):
                card.pop(docline.parentNode.label)

    def testHandler_dataWarning(self, docline, body):
        """Warn on the case's docline when a table it addresses carries no data

        A case built over an empty selection renders an empty widget and reads
        as a broken page, while the cause is developer setup: the package ships
        startup data this instance has never loaded.
        """
        packages = sorted({tablename.split('.')[0]
                           for tablename in self.testHandler_caseTables(body)
                           if self.testHandler_dataToLoad(tablename)})
        if packages:
            docline.div('Load %s data first' % ', '.join(packages),
                        _class='test_handler_card_warning')

    def testHandler_caseTables(self, body):
        """Tables the case addresses, read from the structure it has just built"""
        tables = set()
        for node in body.traverse():
            for attribute in TABLE_ATTRIBUTES:
                value = node.attr.get(attribute)
                if isinstance(value, str) and TABLE_REFERENCE.match(value):
                    tables.add(value)
        return tables

    def testHandler_dataToLoad(self, tablename):
        """True when the table is empty and its package ships startup data

        An empty table of a package without startup data is not a missing setup:
        there is nothing to load, so there is nothing to warn about.
        """
        cache = getattr(self, '_testHandler_dataToLoad', None)
        if cache is None:
            cache = self._testHandler_dataToLoad = {}
        if tablename not in cache:
            cache[tablename] = self.testHandler_checkDataToLoad(tablename)
        return cache[tablename]

    def testHandler_checkDataToLoad(self, tablename):
        """The uncached check behind testHandler_dataToLoad"""
        pkgid, name = tablename.split('.')
        dbpkg = self.db.packages.get(pkgid)
        if dbpkg is None or name not in dbpkg.tables:
            return False
        pkgfolder = self.db.application.packages[pkgid].packageFolder
        if not any(os.path.isfile(os.path.join(pkgfolder, 'startup_data.%s' % ext))
                   for ext in ('pik', 'gz')):
            return False
        return not self.db.table(tablename).countRecords()


class TestHandlerBase(TestHandler):
    def main_root(self, root, **kwargs):
        root = root.div(position='absolute',top='0',bottom='0',left='0',right='0',overflow='auto')
        if self._call_args:
            if '*' in self._call_args:
                self.testOnly = False
            else:
                self.testOnly = ['_%s_' % str(a) for a in self._call_args]
        self.testHandler(root)


class TestHandlerFull(TestHandler):
    def main(self, root, **kwargs):
        if self._call_args:
            if '*' in self._call_args:
                self.testOnly = False
            else:
                self.testOnly = ['_%s_' % str(a) for a in self._call_args]
        root.attributes['overflow'] = 'auto'
        root.attributes['onCreated'] = 'genro.fakeResize()'
        self.testHandler(root)
