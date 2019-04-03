# -*- coding: utf-8 -*-

# test_special_action.py
# Created by Francesco Porcari on 2010-07-02.
# Copyright (c) 2011 Softwell. All rights reserved.
from gnr.web.batch.btcbase import BaseResourceBatch
from gnr.core.gnrbag import Bag
import re
import urllib
import os

caption = 'Export to sphinx'
description = 'Export to sphinx'
tags = '_DEV_'


class Main(BaseResourceBatch):
    dialog_height = '450px'
    dialog_width = '650px'
    batch_prefix = 'ESW'
    batch_title =  'Export to sphinx'
    batch_cancellable = False
    batch_delay = 0.5
    batch_steps = 'prepareRstDocs,buildHtmlDocs'

    def pre_process(self):
        handbook_id = self.batch_parameters['extra_parameters']['handbook_id']
        self.handbook_record = self.tblobj.record(handbook_id).output('bag')
        self.doctable=self.db.table('docu.documentation')
        self.doc_data = self.doctable.getHierarchicalData(root_id=self.handbook_record['docroot_id'], condition='$is_published IS TRUE')['root']['#0']
        self.handbookNode= self.page.site.storageNode(self.handbook_record['sphinx_path']) #or default_path
        self.sphinxNode = self.handbookNode.child('sphinx')
        self.sourceDirNode = self.sphinxNode.child('source')
        self.page.site.storageNode('rsrc:pkg_docu','sphinx_env','default_conf.py').copy(self.page.site.storageNode(self.sourceDirNode.child('conf.py')))
        self.imagesDict = dict()
        self.imagesPath='_static/images'
        self.customCssPath='_static/custom.css'
        self.customJSPath='_static/custom.js'
        self.examples_root = None 
        self.examples_pars = Bag(self.handbook_record['examples_pars'])
        self.examples_mode = self.examples_pars['mode'] or 'iframe'
        if self.handbook_record['examples_site']:
            self.examples_root = '%(examples_site)s/webpages/%(examples_directory)s' %self.handbook_record
        self.imagesDirNode = self.sourceDirNode.child(self.imagesPath)

    def step_prepareRstDocs(self):
        "Prepare Rst docs"

        if self.handbook_record['toc_roots']:
            toc_roots = self.handbook_record['toc_roots'].split(',')
            toc_trees = []
            for doc_id in toc_roots:
                if doc_id in self.doc_data.keys():
                    toc_elements = self.prepare(self.doc_data[doc_id],[])
                    r = self.doctable.record(doc_id).output('dict')
                    title = Bag(r['docbag'])['%s.title' % self.handbook_record['language']] 
                    toctree = self.createToc(elements=toc_elements, includehidden=True, titlesonly=True, caption=title)
                    toc_trees.append(toctree)
            tocstring = '\n\n'.join(toc_trees)
        else:
            toc_elements = self.prepare(self.doc_data,[])
            tocstring = self.createToc(elements=toc_elements, includehidden=True, titlesonly=True)

        self.createFile(pathlist=[], name='index', title=self.handbook_record['title'], rst='', tocstring=tocstring)
        for k,v in self.imagesDict.items():
            source_url = self.page.externalUrl(v) if v.startswith('/') else v
            child = self.sourceDirNode.child(k)
            with child.open('wb') as f:
                f.write(urllib.urlopen(source_url).read())

    def step_buildHtmlDocs(self):
        "Build HTML docs"

        self.resultNode = self.sphinxNode.child('build')
        build_args = dict(project=self.handbook_record['title'],
                          version=self.handbook_record['version'],
                          author=self.handbook_record['author'],
                          release=self.handbook_record['release'],
                          lang=self.handbook_record['language'])
        args = []
        for k,v in build_args.items():
            if v:
                args.extend(['-D', '%s=%s' % (k,v)])
        customStyles = self.handbook_record['custom_styles'] or ''
        customStyles = '%s\n%s' %(customStyles,self.defaultCssCustomization())
        with self.sourceDirNode.child(self.customCssPath).open('wb') as cssfile:
            cssfile.write(customStyles)
        with self.sourceDirNode.child(self.customJSPath).open('wb') as jsfile:
            jsfile.write(self.defaultJSCustomization())
        self.page.site.shellCall('sphinx-build', self.sourceDirNode.internal_path , self.resultNode.internal_path, *args)


    def post_process(self):
        if self.batch_parameters['download_zip']:
            self.zipNode = self.handbookNode.child('%s.zip' % self.handbook_record['name'])
            self.page.site.zipFiles([self.resultNode.internal_path], self.zipNode.internal_path)
        
    def result_handler(self):
        r=dict()
        if self.batch_parameters['download_zip']:
            r=dict(url=self.zipNode.url())
        return 'Html Handbook created', r
        
    def prepare(self, data, pathlist):
        IMAGEFINDER = re.compile(r"\.\. image:: ([\w./:-]+)")
        LINKFINDER = re.compile(r"`([^`]*) <([\w./]+)>`_\b")
        TOCFINDER = re.compile(r"_TOC?(\w*)")
        EXAMPLE_FINDER = re.compile(r"`([^`]*)<javascript:localIframe\('version:([\w_]+)'\)>`_")

        result=[]
        for n in data:
            v = n.value
            record = self.doctable.record(n.label).output('dict')
            
            name=record['name']
            docbag = Bag(record['docbag'])
            self.curr_sourcebag = Bag(record['sourcebag'])
            toc_elements=[name]
            self.hierarchical_name = record['hierarchical_name']
            if n.attr['child_count']>0:
                result.append('%s/%s.rst' % (name,name))
                toc_elements=self.prepare(v, pathlist+toc_elements)
                self.curr_pathlist = pathlist+[name]
                tocstring = self.createToc(elements=toc_elements,
                            hidden=not record['sphinx_toc'],
                            titlesonly=True,
                            maxdepth=1)
            else:
                result.append(name)
                self.curr_pathlist=pathlist
                tocstring=''
            lbag=docbag[self.handbook_record['language']]
            if not lbag:
                continue
            rst = lbag['rst'] or ''
            rsttable = self.doctable.dfAsRstTable(record['id'])
            if rsttable:
                rst = '%s\n\n**Parameters:**\n\n%s' %(rst,rsttable) 
            if rst:
                rst = IMAGEFINDER.sub(self.fixImages,rst)
                rst = LINKFINDER.sub(self.fixLinks, rst)
                if self.examples_root and self.curr_sourcebag:
                    rst = EXAMPLE_FINDER.sub(self.fixExamples, rst)
                rst=rst.replace('[tr-off]','').replace('[tr-on]','')
                self.createFile(pathlist=self.curr_pathlist, name=name,
                                title=lbag['title'], 
                                rst=rst,
                                tocstring=tocstring,
                                hname=record['hierarchical_name'])
        return result

    def fixExamples(self, m):
        example_label = m.group(1)
        example_name = m.group(2)
        
        example_url = '%s/%s/%s.py' % (self.examples_root, self.hierarchical_name,example_name)
        sourcedata = self.curr_sourcebag[example_name] or Bag()
        
        return '.. raw:: html\n\n %s' %self.exampleHTMLChunk(example_url,sourcedata,example_label=example_label,example_name=example_name)
        
    def exampleHTMLChunk(self,example_url,sourcedata,example_label=None,example_name=None):
        height = sourcedata['iframe_height'] or self.examples_pars['default_height'] or  100
        width = sourcedata['iframe_width'] or self.examples_pars['default_width']
        source_theme = self.examples_pars['source_theme']
        source_region = sourcedata['source_region'] or self.examples_pars['source_region']
        if source_region:
            source_region_inspector = sourcedata['source_inspector']
            if source_region_inspector and not sourcedata['iframe_height']:
                height = max(300,height)
            source_region_inspector = 'f' if not source_region_inspector else 't'
            example_url = '%s?_source_viewer=%s&_source_toolbar=%s' %(example_url,source_region,source_region_inspector)
            if source_theme:
                example_url = '%s&cm_theme=%s' %(example_url,source_theme)
        iframekw = dict(example_url=example_url,height=height,width=width or '100%',
                        example_label=example_label or example_name,example_name=example_name)
        return """<div class="gnrexamplebox">
            <a class="gnrexamplebox_title" onclick="gnrExampleIframe(this.nextElementSibling,'%(example_url)s','%(height)s','%(width)s');">
                %(example_label)s
            </a>
            <div></div>
        </div>
        """  %iframekw


    def fixImages(self, m):
        old_filepath = m.group(1)
        filename = old_filepath.split('/')[-1]
        new_filepath = '%s/%s' % (self.imagesPath, '/'.join(self.curr_pathlist+[filename]))
        self.imagesDict[new_filepath]=old_filepath
        result = ".. image:: /%s" % new_filepath
        return result
        
    def fixLinks(self, m):
        prefix = '%s/' % self.db.package('docu').htmlProcessorName()
        title= m.group(1)
        path= m.group(2)
        ref = m.group(2).replace(prefix,'')
        valid_link=self.doctable.query(where='$hierarchical_name=:ref', ref= ref).fetch()
        if valid_link:
            result = ' :ref:`%s<%s>` ' % (title, ref)
            return result
        splitted_ref=ref.split('/')
        parent_name = '/'.join(splitted_ref[-2:])
        parent_name='%' + parent_name
        similar = self.doctable.query(where='$hierarchical_name LIKE :parent_name', parent_name=parent_name).fetch()
        if similar:
            result = ' :ref:`%s<%s>` ' % (title, similar[0]['hierarchical_name'])
            return result
        same_name=self.doctable.query(where='$name= :name', name=splitted_ref[-1] ).fetch()
        if same_name and len(same_name)==0:
            result = ' :ref:`%s<%s>` ' % (title, same_name[0]['hierarchical_name'])
            return result
        return '*MISSING LINK (%s)* %s' % (ref,title)

    def createToc(self, elements=None, maxdepth=None, hidden=None, titlesonly=None, caption=None, includehidden=None):
        toc_options=[]
        if includehidden:
            toc_options.append('   :includehidden:')
        if maxdepth:
            toc_options.append('   :maxdepth: %i' % maxdepth)
        if hidden:
            toc_options.append('   :hidden:')
        if titlesonly:
            toc_options.append('   :titlesonly:')
        if caption:
            toc_options.append('   :caption: %s' % caption)

        return '\n%s\n%s\n\n\n   %s' % (".. toctree::", '\n'.join(toc_options),'\n   '.join(elements))


             
    def createFile(self, pathlist=None, name=None, title=None, rst=None, hname=None, tocstring=None, footer=''):
        reference_label='.. _%s:\n' % hname if hname else ''
        title = title or name
        content = '\n'.join([reference_label, title, '='*len(title), tocstring, '\n\n', rst, footer])
        storageNode = self.page.site.storageNode('/'.join([self.sourceDirNode.internal_path]+pathlist))
        with storageNode.child('%s.rst' % name).open('wb') as f:
            f.write(content)


    def table_script_parameters_pane(self,pane,**kwargs):   
        fb = pane.formbuilder(cols=1, border_spacing='5px')
        fb.checkbox(lbl='Download Zip', value='^.download_zip')



    def defaultCssCustomization(self):
        return """/* override table width restrictions */
@media screen and (min-width: 767px) {

   .wy-table-responsive table td {
      /* !important prevents the common CSS stylesheets from overriding
         this as on RTD they are loaded after this stylesheet */
      white-space: normal !important;
   }

   .wy-table-responsive {
      overflow: visible !important;
   }
}

.gnrexamplebox{

}
.gnrexamplebox_title{
    color:#2980B9;
    cursor:pointer;
}
.gnrexamplebox_iframecont{
    border:1px solid silver;
    margin:5px;
}
"""

    def defaultJSCustomization(self):
        return """
          var gnrExampleIframe = function(box,src,height,width){

            height = height || '200px';
            width = width || '100%'
            box.innerHTML = '<div class="gnrexamplebox_iframecont"><iframe src="'+src+'" frameborder="0" height="'+height+'" width="'+width+'"></iframe></div>';
        }
    """