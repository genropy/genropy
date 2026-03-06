# -*- coding: utf-8 -*-

# testhandler.py
# Created by Giovanni Porcari on 2010-08-09.
# Copyright (c) 2011 Softwell. All rights reserved.

import sys

from gnr.web.gnrbaseclasses import BaseComponent


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
            doc = test_handler.__doc__ or ''
            if doc:
                card.div(doc, _class='test_handler_card_doc')
            body = card.div(_class='test_handler_card_body')
            test_handler(body)


class TestHandlerBase(TestHandler):
    def main_root(self, root, **kwargs):
        root.attributes['overflow'] = 'auto'
        root.attributes['onCreated'] = 'genro.fakeResize()'
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
