from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrwebstruct import struct_method

class DocumentIframe(BaseComponent):

    @struct_method
    def dc_tableDocumentIframe(self,parent,code=None,field=None,table=None,**kwargs):
        if not table:
            table = parent.getInheritedAttributes().get('table')
        if not table:
            raise self.exception('generic',msg='Missing table for tableEndpoint')
        tblobj = self.db.table(table)
        columnobj = tblobj.column(code)
        outdatedWatermark = None
        if columnobj is not None:
            outdatedWatermark = columnobj.attributes.get('outdatedWatermark')
            field = code
            if 'docurl' in columnobj.attributes.get('variant',''):
                field = f'{code}_docurl'
        kwargs['_virtual_column'] = f'{field}'
        endpoint_maker = getattr(tblobj,f'getDocument_{code}',None)
        if endpoint_maker and not outdatedWatermark:
            outdatedWatermark = getattr(endpoint_maker,'outdatedWatermark',None)
        return parent.documentIframe(src=f'^#FORM.record.{field}',
                                    outdatedPath=f'#FORM.record.${code}_versions',
                                        **kwargs)

            
    @struct_method
    def dc_documentIframe(self,parent,src=None,outdatedPath=None,**kwargs):
        frame = parent.framePane(nodeId='documentIframe_#',
                                datapath=f'#FORM.documentIframe_{id(parent)}')
 
        if outdatedPath:
            kwargs['src_version'] = '^.selectedVersion'
        result = frame.center.contentPane().iframe(src=src,height='100%',width='100%',border=0,
                                onLoad="console.log('fastpollig start');genro.setFastPolling(true);" if outdatedPath else None,
                                documentClasses=True,**kwargs)
        if outdatedPath:
            frame.data('.selectedVersion','_latest_')
            frame.dataController("""SET .selectedVersion = '_latest_';""",_fired='^#FORM.controller.loaded')
            frame.dataController("""console.log('fastpollig stop',outdatedMenu);
                                    console.log(this.getRelativeData(".selectedVersion"))
                                    genro.setFastPolling(false)
                                    const currentVersions = outdatedMenu?outdatedMenu.keys().join(','):'_noversions_';
                                    if(currentVersions!=latestVersions){
                                        SET .latestVersions = currentVersions;
                                        SET .outdatedMenu = outdatedMenu;
                                    }
                                    
                                    
                                    """,
                                    outdatedMenu=f'^{outdatedPath}',latestVersions='=.latestVersions')
            frame.dataFormula('.selectedVersion','version_key || "_latest_"',version_key='^.version_key',_delay=1)
            #frame.bottom.slotBar('*,versions,*',_class='mobile_bar',height='22px').versions.multiButton(value='^.version_key',
            #            items='^.outdatedMenu')

            frame.top.slotBar('*,versions,*',height='22px',background='#2A2A2E').versions.menudiv('^.selectedVersion',
                        font_weight='bold',placeholder='!![en]Latest',colorWhite=True,
                        storepath='.outdatedMenu')
        return result