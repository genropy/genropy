# -*- coding: utf-8 -*-

# test_special_action.py
# Created by Francesco Porcari on 2010-07-02.
# Copyright (c) 2011 Softwell. All rights reserved.

from json import dumps
from datetime import datetime
import re, sys, time

if sys.version_info[0] == 3:
    from urllib.request import urlopen
else:
    # Not Python 3 - today, it is most likely to be Python 2
    # But note that this might need an update when Python 4
    # might be around one day
    from urllib import urlopen

from sphinx.cmd.build import main as sphinx_build_main
import boto3

from gnr.web.batch.btcbase import BaseResourceBatch
from gnr.app.gnrlocalization import AppLocalizer
from gnr.core.gnrbag import Bag
from gnr.app import pkglog as logger

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
    batch_steps = 'prepareConfFile,prepareRstDocs,buildHtmlDocs'

    def pre_process(self):
        self.handbook_id = self.batch_parameters['extra_parameters']['handbook_id']
        self.handbook_record = self.tblobj.record(self.handbook_id, virtual_columns='$sphinx_path').output('bag')
        self.doctable =self.db.table('docu.documentation')
        self.doc_data = self.doctable.getHierarchicalData(root_id=self.handbook_record['docroot_id'], condition='$is_published IS TRUE')['root']['#0']
        #DP202208 Temporary node to build files, moved after creation to definitive folder
        self.handbookNode = self.page.site.storageNode('site:handbooks', self.handbook_record['name'])
        self.sphinxNode = self.handbookNode.child('sphinx') 
        self.sourceDirNode = self.sphinxNode.child('source')
        #DP202208 publishedDocNode node is where the final documentation will be published, at beginning of the process we erase former docs
        self.publishedDocNode = self.page.site.storageNode(self.handbook_record['sphinx_path'])
        self.publishedDocNode.delete()
        self.html_baseurl = self.db.application.getPreference('.sphinx_baseurl',pkg='docu') or self.page.site.externalUrl('/_documentation/')
        self.handbook_url = f"{self.html_baseurl}{self.handbook_record['name']}/"
        self.enable_sitemap = self.db.application.getPreference('.enable_sitemap',pkg='docu')
        self.imagesDict = dict()
        self.imagesPath='_static/images'
        self.examplesPath='_static/_webpages'
        self.examples_root = None 
        self.examples_pars = Bag(self.handbook_record['examples_pars'])
        self.examples_mode = self.examples_pars['mode'] or 'iframe'
        self.examples_root_local = ''
        self.examplesDict = {}
        if self.handbook_record['examples_site']:
            self.examples_root = '%(examples_site)s/webpages/%(examples_directory)s' %self.handbook_record
        if self.handbook_record['examples_local_site']:
            self.examples_root_local = '%(examples_local_site)s/webpages/%(examples_directory)s' %self.handbook_record
        self.imagesDirNode = self.sourceDirNode.child(self.imagesPath)
        self.examplesDirNode = self.sourceDirNode.child(self.examplesPath)
        #DP202112 Check if there are active redirects
        if self.db.application.getPreference('.manage_redirects',pkg='docu'):
            self.redirect_pkeys = self.db.table('docu.redirect').query(where='$old_handbook_id=:h_id AND $is_active IS TRUE', 
                        h_id=self.handbook_id).selection().output('pkeylist')   
            
    def step_prepareConfFile(self):
        "Prepare conf file"
        confSn = self.sourceDirNode.child('conf.py')
        self.page.site.storageNode('rsrc:pkg_docu','sphinx_env','default_conf.py').copy(self.page.site.storageNode(confSn))

        # Check if theme exists, fallback to sphinx_rtd_theme if not
        theme = self.handbook_record['theme'] or 'sphinx_rtd_theme'
        theme_path = self.page.site.storageNode('rsrc:pkg_docu','sphinx_env','themes').internal_path
        theme_node = self.page.site.storageNode('rsrc:pkg_docu','sphinx_env','themes', theme)

        if not theme_node.exists:
            logger.warning(f"Theme '{theme}' not found, falling back to 'sphinx_rtd_theme'")
            theme = 'sphinx_rtd_theme'
        handbooks_theme_pref = self.db.application.getPreference('.handbooks_theme',pkg='docu') or {}
        conf_lines = [
            f"html_theme = '{theme}'",
            f"html_theme_path = ['{theme_path}/']",
            f"html_baseurl='{self.html_baseurl}'",
        ]
        if handbooks_theme_pref.get('logo'):
            conf_lines.append(f"html_logo = '{self.page.site.externalUrl(handbooks_theme_pref['logo'])}'")
            conf_lines.append("html_short_title = 'Handbook'")
        if handbooks_theme_pref.get('copyright'):
            conf_lines.append("show_copyright = True")
            conf_lines.append("html_show_sphinx = False")
            conf_lines.append(f"copyright = '{self.db.workdate.year} {handbooks_theme_pref['copyright']}'")
        if handbooks_theme_pref.get('display_version'):
            conf_lines.append("theme_display_version = True")
            conf_lines.append(f"version = release = '{self.handbook_record['version']}'")
        if handbooks_theme_pref.get('last_update'):
            conf_lines.append("html_last_updated_fmt = '%d-%m-%Y'")
        if handbooks_theme_pref.get('show_authors'):
            conf_lines.append("show_authors = True")
        if self.enable_sitemap: #DP Enabled extensions = ['sphinx_sitemap','sphinxext.opengraph']
            conf_lines.append(f"sitemap_url_scheme = '{self.handbook_record['name']}/{{link}}'")
        extra_conf = '\n'.join(conf_lines)
        with confSn.open('a') as confFile:
            confFile.write(extra_conf)
            logger.info("Extra conf lines added to conf.py: %s" % extra_conf)
            
    def step_prepareRstDocs(self):
        "Prepare Rst docs"
        if self.handbook_record['toc_roots']:
            toc_roots = self.handbook_record['toc_roots'].split(',')
            toc_trees = []
            regular_pages = []

            # Process all direct children of docroot
            for node in self.doc_data:
                doc_id = node.label
                record = self.doctable.record(doc_id).output('dict')

                # Skip if no publish_date
                if not record.get('publish_date'):
                    continue

                if doc_id in toc_roots:
                    # Process as toc_root with caption
                    subtree = Bag()
                    subtree.setItem(node.label, node.value, **node.attr)
                    title = Bag(record['docbag'])['%s.title' % self.handbook_record['language']]
                    toc_elements = self.prepare(subtree, [], skip_first=True)
                    toc_trees.append(self.createToc(elements=toc_elements, includehidden=True, titlesonly=True, caption=title))
                else:
                    # Process as regular page (not in toc_roots but has publish_date)
                    subtree = Bag()
                    subtree.setItem(node.label, node.value, **node.attr)
                    page_elements = self.prepare(subtree, [])
                    regular_pages.extend(page_elements)

            # Build main TOC: regular pages first, then toc_root sections
            main_toc_parts = []
            if regular_pages:
                main_toc_parts.append(self.createToc(elements=regular_pages, includehidden=True, titlesonly=True))
            main_toc_parts.extend(toc_trees)
            tocstring = '\n\n'.join(main_toc_parts)
        else:
            toc_elements = self.prepare(self.doc_data,[])
            tocstring = self.createToc(elements=toc_elements, includehidden=True, titlesonly=True)

        self.createFile(pathlist=[], name='index', title=self.handbook_record['title'], rst='', tocstring=tocstring)
        for k,v in self.imagesDict.items():
            #DP202112 Useful for local debugging
            source_url = self.page.site.externalUrl(v) if v.startswith('/') else v
            child = self.sourceDirNode.child(k)
            with child.open('wb') as f:
                try:
                    f.write(urlopen(source_url).read())
                except:
                    logger.debug("Missing file", source_url)
                    continue
                    
        for relpath,source in self.examplesDict.items():
            if not source:
                continue
            with self.examplesDirNode.child(relpath).open('wb') as f:
                f.write(source.encode())

    def step_buildHtmlDocs(self):
        "Build HTML docs"
        self.resultNode = self.sphinxNode.child('build')
        ogp_image = self.page.site.externalUrl(self.handbook_record['ogp_image']) if self.handbook_record['ogp_image'] else None
        build_args = dict(project=self.handbook_record['title'],
                          version=self.handbook_record['version'],
                          author=self.handbook_record['author'],
                          ogp_image=ogp_image,
                          release=self.handbook_record['release'],
                          language=self.handbook_record['language'])
        template_variables = dict()
        args = []
        for k,v in build_args.items():
            if v:
                args.extend(['-D', '%s=%s' % (k,v)])
        for k,v in template_variables.items():
            if v:
                args.extend(['-A', '%s=%s' % (k,v)])
        
        self.processCssCustomizations()
        self.processJsCustomizations()
        self.processHtmlCustomizations()

        args = [self.sourceDirNode.internal_path, self.resultNode.internal_path] + args
        sphinx_build_main(args)

    def post_process(self):     
        with self.tblobj.recordToUpdate(self.handbook_id) as record:
            record['last_exp_ts'] = datetime.now()
            if record['is_local_handbook']:
                self.zipNode = self.handbookNode.child('%s.zip' % self.handbook_record['name'])
                self.page.site.zipFiles([self.resultNode.fullpath], self.zipNode.internal_path)
                #DP202208 Zip file will be moved to published Doc node after creation. Building folders will be deleted
                destNode = self.publishedDocNode.child(self.zipNode.basename)
                self.zipNode.move(destNode)
                self.result_url = self.zipNode.internal_url().split('?')[0] #Remove ?download=True if present
                record['local_handbook_zip'] = self.result_url
            else:
                #DP202208 Html files will be moved to published Doc node after creation. Building folders will be deleted
                logger.info(f"Moving HTML build from {self.resultNode.fullpath} to {self.publishedDocNode.fullpath}")
                self.resultNode.move(self.publishedDocNode)
                logger.info(f"Move completed. Published doc available at: {self.publishedDocNode.fullpath}")
                record['handbook_url'] = self.handbook_url
                self.result_url = None
        if not self.db.application.getPreference('.save_src_debug',pkg='docu'):
            self.sphinxNode.delete()
        self.db.commit()

        if self.db.application.getPreference('.manage_redirects',pkg='docu'):
            if self.redirect_pkeys or not self.batch_parameters.get('skip_redirects'):
            #DP202112 Make redirect files
                redirect_recs = self.db.table('docu.redirect').query(columns='*,$old_handbook_path,$old_handbook_url').fetchAsDict('id')
                for redirect_pkey in self.redirect_pkeys:
                    redirect_rec = redirect_recs[redirect_pkey]
                    self.db.table('docu.redirect').makeRedirect(redirect_rec)

        if self.batch_parameters.get('invalidate_cache'):
            self.invalidateCloudfrontCache()

        if self.db.package('genrobot'):
            if self.batch_parameters.get('send_notification'):
                #DP202101 Send notification message via Telegram (gnrextra genrobot required)
                notification_message = self.batch_parameters['notification_message'].format(handbook_title=self.handbook_record['title'], 
                                            timestamp=datetime.now(), handbook_url=self.handbook_url)
                notification_bot = self.batch_parameters['bot_token']
                self.sendNotification(notification_message=notification_message, notification_bot=notification_bot)

    def result_handler(self):
        resultAttr = dict() 
        if self.result_url:
            resultAttr['url'] = self.result_url
        return 'Export done', resultAttr

    def prepare(self, data, pathlist, skip_first=False):
        IMAGEFINDER = re.compile(r"\.\. image:: ([\w./:-]+)")
        LINKFINDER = re.compile(r"`([^`]*) <([\w./]+)>`_\b")
        #LINKFINDER = re.compile(r"`([^`]*) <([\w./-]+)(?:/(#[\w-]+))?>`_\b") version with group 3 after /#
        TOCFINDER = re.compile(r"_TOC?(\w*)")
        EXAMPLE_FINDER = re.compile(r"`([^`]*)<javascript:localIframe\('version:([\w_]+)'\)>`_")
        result=[]
        if not data:
            return result
        for idx, n in enumerate(data):
            v = n.value
            record = self.doctable.record(n.label,
                                          virtual_columns='$full_external_url,$root_handbook_url').output('dict')
            
            name=record['name']
            docbag = Bag(record['docbag'])
            self.curr_sourcebag = Bag(record['sourcebag'])
            self.hierarchical_name = record['hierarchical_name']
            lbag=docbag[self.handbook_record['language']] or Bag()
            rst = lbag['rst'] or ''
            df_rst = self.doctable.dfAsRstTable(record['id'], language=self.handbook_record['language'])
            translator = AppLocalizer(self.db.application) 
            if df_rst:
                params = translator.getTranslation('!!Parameters', language=self.handbook_record['language']).get('translation') or 'Parameters'
                rst = f'{rst}\n\n' + '.. raw:: html\n\n <hr>' + f'\n\n**{params}:**\n\n{df_rst}'
            atc_rst = self.doctable.atcAsRstTable(record['id'], host=self.page.external_host)
            if atc_rst:
                atcs = translator.getTranslation('!!Attachments', language=self.handbook_record['language']).get('translation') or 'Attachments'
                rst = f'{rst}\n\n' + '.. raw:: html\n\n <hr>' + f'\n\n**{atcs}:**\n\n{atc_rst}'
            
            if self.examples_root and self.curr_sourcebag:
                        rst = EXAMPLE_FINDER.sub(self.fixExamples, rst)

            has_children = bool(n.attr['child_count'])
            branch_pathlist = pathlist+[name] if has_children else pathlist
            child_toc_elements = []
            if has_children and v:
                child_toc_elements = self.prepare(v, branch_pathlist)
            self.curr_pathlist = branch_pathlist if has_children else pathlist

            skip_current = skip_first and idx == 0
            if skip_current:
                tocstring = ''
                if child_toc_elements:
                    tocstring = self.createToc(elements=child_toc_elements,
                                               titlesonly=True,
                                               includehidden=True,
                                               maxdepth=1)
                self.createFile(pathlist=branch_pathlist,
                                name='index',
                                title=lbag['title'] or name,
                                rst='',
                                tocstring=tocstring,
                                hname=record['hierarchical_name'])
                prefixed_entries = [f'{name}/{entry}' for entry in child_toc_elements if entry]
                result.extend(prefixed_entries)
                continue

            rst = IMAGEFINDER.sub(self.fixImages,rst)
            rst = LINKFINDER.sub(self.fixLinks, rst)

            rst=rst.replace('[tr-off]','').replace('[tr-on]','')
            footer= ''
            if record['author']:
                footer = '\n.. sectionauthor:: %s\n' % (record['author'] or self.handbook_record['author'])
            if self.db.application.getPreference('.handbooks_theme.last_update',pkg='docu'):
                last_upd = translator.getTranslation('!!Publish date', language=self.handbook_record['language']).get('translation') or 'Publish date'
                date_format = '%Y-%m-%d'if self.handbook_record['language'] == 'en' else '%d-%m-%Y' 
                publish_date_str = record['publish_date'].strftime(date_format) if record['publish_date'] else ''
                footer += f"""\n.. raw:: html\n\n   <p style="font-size:0.8em;">{last_upd} {publish_date_str}</p>"""

            url = record.get('full_external_url') or record.get('root_handbook_url')
            if url:
                self.batch_log_write(f"{record.get('hierarchical_name') or record.get('name')}: {url}")

            tocstring = ''
            if has_children:
                result.append('%s/%s.rst' % (name,name))
                if child_toc_elements:
                    tocstring = self.createToc(elements=child_toc_elements,
                                                    hidden=not record['sphinx_toc'],
                                                    titlesonly=True,
                                                    maxdepth=1)
            else:
                result.append(name)
                
            self.createFile(pathlist=self.curr_pathlist, name=name,
                            title=lbag['title'], 
                            rst=rst,
                            tocstring=tocstring,
                            hname=record['hierarchical_name'], footer=footer)
            
        return result

    def fixExamples(self, m):
        example_label = m.group(1)
        example_name = m.group(2)
        logger.debug(f'**EXAMPLE** {example_name}')
        sourcedata = self.curr_sourcebag[example_name] or Bag()
        logger.debug(sourcedata)
        return '.. raw:: html\n\n %s' %self.exampleHTMLChunk(sourcedata,example_label=example_label,example_name=example_name)
        
    def exampleHTMLChunk(self,sourcedata,example_label=None,example_name=None):
        height = sourcedata['iframe_height'] or self.examples_pars['default_height'] or  100
        width = sourcedata['iframe_width'] or self.examples_pars['default_width']
        source_theme = self.examples_pars['source_theme']
        source_region = sourcedata['source_region'] or self.examples_pars['source_region']
        parsstring = ''
        if source_region:
            source_region_inspector = sourcedata['source_inspector']
            if source_region_inspector and not sourcedata['iframe_height']:
                height = max(300,height)
            source_region_inspector = 'f' if not source_region_inspector else 't'
            parsstring = '?_source_viewer=%s&_source_toolbar=%s' %(source_region,source_region_inspector)
            if source_theme:
                parsstring = '%s&cm_theme=%s' %(parsstring,source_theme)
        
        iframekw = dict(height=height,width=width or '100%',examples_root = self.examples_root,
                        examples_root_local = self.examples_root_local,
                        example_folder = self.hierarchical_name,parsstring=parsstring,
                        example_label=example_label or example_name,example_name=example_name)
        self.examplesDict['%(example_folder)s/%(example_name)s.py' %iframekw] = sourcedata['source']

        return """<div class="gnrexamplebox">
            <a class="gnrexamplebox_title" onclick='gnrExampleIframe(this.nextElementSibling,%s );'>
                %s
            </a>
            <div></div>
        </div> 
        """  %(dumps(iframekw),iframekw['example_label'])

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
        ref = path.replace(prefix,'')
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

    def invalidateCloudfrontCache(self):
        client = boto3.client('cloudfront')
        response = client.create_invalidation(
                    DistributionId=self.db.application.getPreference('.cloudfront_distribution_id',pkg='docu'),
                    InvalidationBatch={
                        'Paths': {
                            'Quantity': 1,
                            'Items': [
                                '/{handbook_name}/*'.format(handbook_name=self.handbook_record['name'])
                                ],
                            },
                            'CallerReference': str(time.time()).replace(".", "")
                        }
                    )
        return response

    def sendNotification(self, notification_bot=None, notification_message=None):
        notification_recipients = self.db.table('genrobot.bot_contact').query(columns='@contact_id.username AS username', 
                        where='@bot_id.bot_token=:bot_token', bot_token=notification_bot).fetchAsDict('username')
        socialservice = self.page.site.getService(service_type='telegram', service_name='telegram')
        assert socialservice,'set in siteconfig the service social/telegram'
        for recipient in notification_recipients:
            result = socialservice.publishPost(message=notification_message, 
                                            bot_token=notification_bot, page_id_code=recipient)
             
    def createFile(self, pathlist=None, name=None, title=None, rst=None, hname=None, tocstring=None, footer=''):
        reference_label='.. _%s:\n' % hname if hname else ''
        title = title or name
        content = '\n'.join([reference_label, title, '='*len(title), tocstring, '\n\n', rst, footer])
        storageNode = self.page.site.storageNode('/'.join([self.sourceDirNode.internal_path]+pathlist))
        with storageNode.child('%s.rst' % name).open('wb') as f:
            f.write(content.encode())

    
    def table_script_parameters_pane(self,pane,**kwargs):   
        fb = pane.formbuilder(cols=1, border_spacing='5px')
        if self.db.application.getPreference('.manage_redirects',pkg='docu'):
            fb.checkbox(label='!![en]Skip redirects', value='^.skip_redirects')
        if self.db.application.getPreference('.cloudfront_distribution_id',pkg='docu'):
            fb.checkbox(label='!![en]Force Cloudfront cache invalidation', value='^.invalidate_cache')
        #DP202101 Ask for Telegram notification option if enabled in docu settings
        if self.db.application.getPreference('.telegram_notification',pkg='docu'):
            fb.checkbox(label='!![en]Send notification via Telegram', value='^.send_notification', default=True)
            fb.dbselect('^.bot_token', lbl='BOT', table='genrobot.bot', columns='$bot_name', alternatePkey='bot_token',
                        colspan=3, hasDownArrow=True, default=self.db.application.getPreference('.bot_token',pkg='docu'),
                        hidden='^.send_notification?=!#v')                
            fb.simpleTextArea(lbl='!![en]Notification content', value='^.notification_message', hidden='^.send_notification?=!#v',
                    default="!![en]Genropy Documentation updated: {handbook_title} was modified @ {timestamp}. Check out what's new on {handbook_url}", 
                    height='60px', width='200px')
            #pane.inlineTableHandler(table='genrobot.bot_contact', datapath='.notification_recipients',
            #                title='!![en]Notification recipients', 
            #                margin='2px', pbl_classes=True, addrow=False, delrow=False, height='200px')

    def processCssCustomizations(self):
        customCssPath='_static/custom.css' #DP Customizable?
        cssStyles = [
            s for s in [
                self.db.application.getPreference('.base_css', pkg='docu'),
                self.handbook_record.get('custom_styles'),
                self.defaultCssCustomization()
            ] if s
        ]
        with self.sourceDirNode.child(customCssPath).open('wb') as cssfile:
            cssfile.write('\n'.join(cssStyles).encode())
    
    def processJsCustomizations(self):
        customJSPath='_static/custom.js'    
        jsStyles = [
            s for s in [
                self.db.application.getPreference('.base_js',pkg='docu'),
                self.defaultJSCustomization()
            ] if s
        ]
        with self.sourceDirNode.child(customJSPath).open('wb') as jsfile:
            jsfile.write('\n'.join(jsStyles).encode())
            
    def processHtmlCustomizations(self):
        extra_head = self.db.application.getPreference('.html_extra_head', pkg='docu')
        if not extra_head:
            return
        layout_html = f"""
            {{% extends "!layout.html" %}}

            {{% block extrahead %}}
              {{% raw %}}{{{{ super() }}}}{{% endraw %}}
              {extra_head}
            {{% endblock %}}
            """
        template_file = self.sourceDirNode.child('_templates', 'layout.html')
        template_file.ensureParent()
        with template_file.open('w') as f:
            f.write(layout_html)
            
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
                    var gnrExampleIframe = function(box,kw){
                        var src_root = window.location.port?window.location.origin+'/webpages/docu_examples':kw.examples_root;
                        var src = [src_root,kw.example_folder,kw.example_name].join('/');
                        src+=kw.parsstring;
                        var height = kw.height || '200px';
                        var width = kw.width || '100%'
                        box.innerHTML = '<div class="gnrexamplebox_iframecont"><iframe style="padding-bottom:3px; padding-right:3px; resize:vertical;" src="'+src+'" frameborder="0" height="'+height+'" width="'+width+'"></iframe></div>';
                    }
                """
