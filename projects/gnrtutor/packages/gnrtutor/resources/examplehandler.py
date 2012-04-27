# -*- coding: UTF-8 -*-

"""
examplehandler.py
Created by Giovanni Porcari on 2010-08-09.
Copyright (c) 2011 Softwell. All rights reserved.
"""

from gnr.web.gnrbaseclasses import BaseComponent
import sys
import inspect
from pygments import highlight
from pygments.lexers import PythonLexer,XmlLexer
from pygments.formatters import HtmlFormatter
from gnr.core.gnrbag import Bag
import xml.dom.minidom

class ExampleHandler(BaseComponent):
    exampleOnly=False
    dojo_source=True
    css_requires = 'pygmentcss/friendly,example'


    def isDeveloper(self):
        return True
        
    def exampleHandler(self, pane):
        
        self.exampleHandler_headers(pane)
        
        title = pane.div(width='1000px', text_align='center', color='#ACACAC', font_size='20pt')
        moduledoc=sys.modules[self.__module__].__doc__ or '...missing docline in module...'
        title.span(moduledoc)
        pane = pane.div(width='1000px')
        self.exampleHandler_loop(pane)
        
    def exampleHandler_headers(self, pane):
        pane.div(width='1000px', margin='5px')


    def exampleHandler_loop(self, pane):
        example_to_do = [(n,getattr(self,n)) for n in dir(self) if hasattr(getattr(self,n),'isExample')]
        
        example_to_do = sorted(example_to_do,key=lambda x:int(x[1].example_code)) #
        # 
        for example_name,example_handler in example_to_do:
            example_code = int(example_handler.example_code)
            if self.exampleOnly and not example_code in self.exampleOnly:
                continue
            example_doc_handler=getattr(self,'doc_%s'%example_name,None)
            example_doc= example_doc_handler.__doc__ or '...missing example doc...' if example_doc_handler else '...missing example doc...'
            
            self.exampleBody(pane,example_name=example_name,example_handler=example_handler,example_doc=example_doc)

    def exampleBody(self,pane,example_name=None,example_handler=None,example_doc=None):
        datapath = 'example.%s.data' % example_name
        storepath = 'example.%s' % example_name
        pane.data(datapath,Bag())
        bc=pane.borderContainer(border='1px solid gray', margin='2em',height='%spx' %example_handler.example_height,background_color='white',
                           rounded=5, shadow='3px 3px 5px gray',
                           datapath=datapath)
        top=bc.contentPane(region='top',border_bottom='1px solid silver')

        top.div('%(example_code)s - %(example_description)s' %example_handler.__dict__,_class='exm_roundedGroupLabel')

        center=bc.tabContainer(region='center')
        p1=center.framePane(title='Example')
        p2=center.contentPane(title='Source Code',padding='6px')
        p3=center.contentPane(title='Documentation',padding='6px')
        examplePane = p1.center.contentPane(padding='6px')
        p4 = center.contentPane(title='XML Source',padding='6px')

        bar = p1.right.slotBar('2,datatree,2',width='200px',splitter=True,closable='close')
        datatreeslot = bar.datatree
        datatreeslot.attributes.update(height='100%',position='relative')
        treebox = datatreeslot.div(position='absolute',top='2px',right='4px',bottom='2px',
                                left='2px',overflow='auto',text_align='left',_class='pbl_roundedGroup',padding='2px',background='white')
        treebox.tree(storepath=storepath)
        example_handler(examplePane)
        source=inspect.getsource(example_handler).split('\n')
        source.pop(0)
        source='\n'.join(source)
        source=highlight(source, PythonLexer(), HtmlFormatter(linenos='table'))
        p2.div(source,_class='codehilite',padding='4px',rounded=6,detachable=True)
        p3.div(example_doc,white_space='pre',overflow='auto', margin='10px')
        
        xmlsource = examplePane.toXml(docHeader=False)
        xmlsource = xmlsource.replace('>\n','>')

        xmlsource = xml.dom.minidom.parseString(xmlsource) # or xml.dom.minidom.parseString(xml_string)
        pretty_xml_as_string = xmlsource.toprettyxml()
        xmlsource = highlight(pretty_xml_as_string, XmlLexer(), HtmlFormatter())
        p4.div(innerHTML=xmlsource,zoom='.7',_class='codehilite')

        
class ExampleHandlerBase(ExampleHandler):
    def main_root(self, root, **kwargs):
        if self._call_args:
            if '*' in self._call_args:
                self.exampleOnly = False
            else:
                self.exampleOnly = [int(a) for a in self._call_args]
        self.exampleHandler(root)
        
class ExampleHandlerFull(ExampleHandler):
    def main(self, root, **kwargs):
        print kwargs
        if self._call_args:
            if '*' in self._call_args:
                self.exampleOnly = False
            else:
                self.exampleOnly = [int(a) for a in self._call_args]
        self.exampleHandler(root)
