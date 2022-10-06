from gnr.core.gnrdecorator import customizable,metadata
from gnr.core.gnrlang import objectExtract
from gnr.core.gnrbag import Bag
from gnr.web.gnrbaseclasses import BaseComponent

class Assistant(BaseComponent):
    
    def getAssistantPages(self):
        assistant_handlers = objectExtract(self,'assistant_')
        result = Bag()
        for key in sorted(assistant_handlers.keys()):
            result.addItem(key,None,code=key,caption=assistant_handlers[key].__doc__)
        return result
