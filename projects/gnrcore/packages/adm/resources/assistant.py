from gnr.core.gnrdecorator import customizable,metadata
from gnr.core.gnrlang import objectExtract
from gnr.core.gnrbag import Bag
from gnr.web.gnrbaseclasses import BaseComponent

class Assistant(BaseComponent):
    is_assistant_page = True
    py_requires = 'iframegallery/iframegallery:IframeGallery'
   
    def pbl_avatarTemplate(self):
        return '<div>$user</div>'

    def configuration(self):
        handlers = objectExtract(self,'assistant_')
        result = [{'url':'/adm/home','title':'Home'}]
        
        for key in sorted(handlers.keys()):
            kw = dict(handlers[key]())
            kw.setdefault('pageName',key)
            result.append(kw)

        menu = self.menu.getRoot().getItem('root')
        for n in menu:
            result.append(n)
        return result
