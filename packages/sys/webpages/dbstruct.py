from gnr.core.gnrstring import  concat, jsquote

class GnrCustomWebPage(object):   
    css_theme='textmate'

    def main_root(self,root,bpath='',**kwargs):
        self.createCss(root)
        root.data('gnr.windowTite','Dtatabase Structure')
        root.dataRemote('_dev.dbstruct','app.dbStructure')
        bc=root.borderContainer(height='100%')
        self.topPane(bc.contentPane(region='top',height='70px',_class='tm_top'))
        tc=bc.tabContainer(region='center',margin='10px',background_color='white')
        for pkg in self.db.packages.values():
            self.packagePane(tc.borderContainer(title=pkg.name,
                               datapath='packages.%s'%pkg.name),pkg)

    def topPane(self,pane):
        top=pane.div()
        top.div('Genropy',font_size='3em',color='white',margin='10px')
    
    def packagePane(self,bc,pkg):
        top=bc.contentPane(region='bottom',height='32px',background_color='silver',overflow='hidden')
        top.textBox(value='^.selpath',readOnly=True,width='80%',margin='8px')
        center=bc.contentPane(region='center',splitter=True,background_color='white')
        for table in pkg['tables'].values():
            center.dataRemote('.tree.%s' % table.name,'relationExplorer',table=table.fullname,dosort=False)
        
        center.tree(storepath='.tree',persist=False,
                     inspect='shift', labelAttribute='caption',
                     _class='fieldsTree',
                     hideValues=True,
                     margin='6px',
                     font_size='.9em',
                     selected_fieldpath='.selpath',
                     getLabelClass="""if (!node.attr.fieldpath && node.attr.table){return "tableTreeNode"}
                                        else if(node.attr.relation_path){return "aliasColumnTreeNode"}
                                        else if(node.attr.sql_formula){return "formulaColumnTreeNode"}""",
                     getIconClass="""if(node.attr.dtype){return "icnDtype_"+node.attr.dtype}
                                     else {return opened?'dijitFolderOpened':'dijitFolderClosed'}""")
        
        
        
        
    def createCss(self,pane):
        pane.css('.tm_top','background-color:#801f78;')
        pane.css('#mainWindow','background-color:white;')
        
    def rpc_relationExplorer(self, table, prevRelation='', prevCaption='', omit='',quickquery=False, **kwargs):
        def buildLinkResolver(node, prevRelation, prevCaption):
            nodeattr = node.getAttr()
            if not 'name_long' in nodeattr:
                raise Exception(nodeattr) # FIXME: use a specific exception class
            nodeattr['caption'] = nodeattr.pop('name_long')
            nodeattr['fullcaption'] = concat(prevCaption, self._(nodeattr['caption']), ':')
            if nodeattr.get('one_relation'):
                nodeattr['_T'] = 'JS'
                if nodeattr['mode']=='O':
                    relpkg, reltbl, relfld = nodeattr['one_relation'].split('.')
                else:
                    relpkg, reltbl, relfld = nodeattr['many_relation'].split('.')
                jsresolver = "genro.rpc.remoteResolver('relationExplorer',{table:%s, prevRelation:%s, prevCaption:%s, omit:%s})"
                node.setValue(jsresolver % (jsquote("%s.%s" % (relpkg, reltbl)), jsquote(concat(prevRelation, node.label)), jsquote(nodeattr['fullcaption']),jsquote(omit)))
        result = self.db.relationExplorer(table=table, 
                                         prevRelation=prevRelation,
                                         omit=omit,
                                        **kwargs)
        result.walk(buildLinkResolver, prevRelation=prevRelation, prevCaption=prevCaption)
        return result
    
  
  