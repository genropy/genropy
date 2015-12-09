#!/usr/bin/env pythonw
# -*- coding: UTF-8 -*-
#
#  Created by Saverio Porcari on 2013-04-06.
#  Copyright (c) 2013 Softwell. All rights reserved.


from gnr.core.gnrbaseservice import GnrBaseService
from gnr.core.gnrlang import GnrException
import re
SAFETRANSLATE = re.compile(r"""(?:\[tr-off\])(.*?)(?:\[tr-on\])""",flags=re.DOTALL)

try:
    from yandex_translate import YandexTranslate
except:
    YandexTranslate = False

class Main(GnrBaseService):
    def __init__(self, parent=None,api_key=None):
        self.parent = parent
        self.api_key = api_key
        if not YandexTranslate:
            raise GnrException('Missing YandexTranslate. hint: pip install yandex.translate')
        self.translator = YandexTranslate(self.api_key)

    def translate(self,what=None, to_language=None,from_language=None,format=None):
        if not what:
            return
        direction = [to_language] if not from_language else [from_language,to_language]
        safedict = dict()
        def cb(m):
            safekey = '[NO_TR_%i]' %len(safedict)
            safedict[safekey] = m.group(1)
            return safekey
        base_to_translate = SAFETRANSLATE.sub(cb,what)
        print 'safedict',safedict
        print 'base_to_translate',base_to_translate
        result = self.translator.translate(base_to_translate, '-'.join(direction),format=format)
        if result['code'] == 200:
            txt = result['text'][0]
            for k,v in safedict.items():
                txt = txt.replace(k,'[tr-off]%s[tr-on]' %v)
            return txt
        else:
            raise GnrException('Error in translation')
        

