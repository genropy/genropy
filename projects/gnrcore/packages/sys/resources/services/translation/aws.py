#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

#  Created by Davide Paci on 2021-12-21
#  Service documentation available here: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/translate.html

import boto3
from gnrpkg.sys.services.translation import TranslationService
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrlang import GnrException
import re

SAFETRANSLATE = re.compile(r"""(?:\[tr-off\])(.*?)(?:\[tr-on\])""",flags=re.DOTALL)

class Main(TranslationService):
    def __init__(self, parent=None,
                 api_key=None, region_name="eu-central-1",
                 aws_access_key_id=None, aws_secret_access_key=None,
                 **kwargs):
        self.parent = parent
        self.enabled = boto3 is not False
        if not self.enabled:
            return
        self.client = boto3.client('translate', region_name=region_name,
                                   aws_access_key_id=aws_access_key_id,
                                   aws_secret_access_key=aws_secret_access_key)

    def translate(self, what=None, to_language=None, from_language=None, **kwargs):
        if not self.enabled:
            raise GnrException('Service not enabled')
        if not what or not to_language:
            raise GnrException('Missing content or target language code')
        if not from_language:
            from_language = 'auto'
        safedict = dict()

        def cb(m):
            safekey = '[NO_TR_%i]' %len(safedict)
            safedict[safekey] = m.group(1)
            return safekey

        base_to_translate = SAFETRANSLATE.sub(cb,what)
        response = self.client.translate_text(Text=base_to_translate,
              SourceLanguageCode=from_language, TargetLanguageCode=to_language, **kwargs)
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
            raise GnrException('Error in translation')
        else:
            txt = response['TranslatedText']
            for k,v in list(safedict.items()):
                txt = txt.replace(k,'[tr-off]%s[tr-on]' %v)
            return txt
            
class ServiceParameters(BaseComponent):
    def service_parameters(self, pane, datapath=None, **kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.textbox(value='^.region_name', lbl='Region name')
        fb.textbox(value='^.aws_access_key_id',lbl='Aws Access Key Id')
        fb.textbox(value='^.aws_secret_access_key',lbl='Aws Secret Access Key')
