from gnr.web.gnrbaseclasses import BaseComponent

class HomePage(BaseComponent):
    py_requires = 'gnrcomponents/tpleditor'
    auth_main = 'user'

    def main(self,root,**kwargs):
        tplname = f'homepage_{self.user}'
        tpl = self.loadTemplate(f'adm.user:{tplname}',missingMessage='_')
        if tpl=='_':
            tplname = f"homempage_{self.rootenv['user_group_code']}"
            tpl = self.loadTemplate(f'adm.user:{tplname}',missingMessage='_')
        if tpl == '_':
            tplname = 'homepage'
        root.dataFormula('main.user_id','user_id',user_id=self.rootenv['user_id'],_onBuilt=1)
        root.templateChunk(position='absolute',datapath='main',
                            top='0',bottom='0',
                            left='0',right='0',
                            template='homepage',
                            table='adm.user',
                            record_id='^.user_id')