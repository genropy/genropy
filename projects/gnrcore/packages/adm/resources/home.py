from gnr.web.gnrbaseclasses import BaseComponent

def HomePage(BaseComponent):
    auth_main = 'user'
    
    def main(self,root,**kwargs):
        root.templateChunk(position='absolute',
                            top='0',bottom='0',
                            left='0',right='0',
                            template='homepage',
                            table='adm.user')