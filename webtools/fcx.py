from gnr.web.gnrbaseclasses import BaseWebtool
from gnr.core.gnrdecorator import metadata
import fitz, urllib


class FieldContentExtension(BaseWebtool):
    
    #@metadata(alias_url="/document_generation")
    def __call__(self, pkey=None, rebuild=None, history=None, url=None, **kwargs):
        """Url can be https://mywebsite.ext/_tools/fcx/pkg/tbl/fld?pkey=pkey&rebuild=True|keep&history=n|date
            - pkg/tbl/fld or just pkg/tbl (fld can be omitted in attachment tables)
            - pkey is record's pkey
            - rebuild can be True (in this case document is rebuilt every time) or equal to 'keep' (in this case versions are saved in history bag)
            - history can be a number ('n' version) or a date (version valid on 2025-03-18)"""
        print(x)
        #Se c'è doc cached restituisco quello
        #Se c'è metodo per costruirlo, costruisco e rendo
        
        
#All'interno della pagina metto il tool
#Specifico table, campo

#tbl.campo1_path
#tbl.campo1_externalurl

#tbl.campo2_path
#tbl.campo2_externalurl
#tbl.campo2_history (X)

#ESEMPIO CHIAMANTE
#http://app.anaci.it/_tools/fcx/fatt/fattura/doc_fattura?pkey=XYZ12345FGRPS&rebuild=True|keep&history=n|date
#http://app.anaci.it/_tools/fcx/fatt/fattura/doc_fattura?pkey=XYZ12345FGRPS
#http://app.anaci.it/_tools/fcx/fatt/fattura_atc?pkey=XYZ12345FGRPS

#tbl.doc_fattura_path
#tbl.doc_fattura_provider (solo nella tabella atc_type)
        #1: https://apple.com
        #2: fatt.fattura
    
#def provider_doc_fattura(self, *args, **kwargs):
#    pass
#
##Atc Table
##@atc_type.provider
#
##table primaria soci
#@metadata(documento_tipo_codice='ATT')
#def atc_ATT_provider(self, *args, **kwargs):
#    pass
#
#Se documento c'è rendo quello che avevo, altrimenti lo costruisco
#