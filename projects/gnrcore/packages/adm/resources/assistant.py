from gnr.core.gnrdecorator import customizable,metadata
from gnr.core.gnrlang import objectExtract
from gnr.core.gnrbag import Bag
from gnr.web.gnrbaseclasses import BaseComponent

class Assistant(BaseComponent):
    py_requires = 'iframegallery/iframegallery:IframeGallery'

    def configuration(self):
        handlers = objectExtract(self,'assistant_')
        result = []
        for key in sorted(handlers.keys()):
            kw = dict(handlers[key]())
            kw.setdefault('pageName',key)
            result.append(kw)
        return result
