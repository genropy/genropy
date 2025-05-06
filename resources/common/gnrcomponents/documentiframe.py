from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrwebstruct import struct_method

class DocumentIframe(BaseComponent):

    @struct_method
    def dc_tableEndpointIframe(self,parent,code=None,field=None,table=None,**kwargs):
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
        parent.attributes['_workspace'] = True
        if outdatedPath:
            kwargs['src_version'] = '^#WORKSPACE.selectedVersion'
        result = parent.iframe(src=src,height='100%',width='100%',border=0,documentClasses=True,**kwargs)
        if outdatedPath:
            parent.dataController("""SET #WORKSPACE.selectedVersion = null;""",_fired='^#FORM.controller.loaded')
            parent.div(_class='doc_version_menu_wrapper').menudiv('^#WORKSPACE.selectedVersion',
                        hidden=f'^{outdatedPath}?=!#v',
                        font_weight='bold',placeholder='!![en]Latest',
                        storepath=outdatedPath)
        return result