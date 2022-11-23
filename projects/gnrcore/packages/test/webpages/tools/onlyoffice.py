# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull"""

    def test_0_onlyoffice(self, pane):
        """OnlyOffice testing. Please set OnlyOffice integration secret and server address in DEV preferences"""
        config = self.config()
        token = self.token(config)

        pane.div(id='placeholder', height='800px').dataController("""
                            var config = config;
                            var token = token;
                            var conf = Object.assign({}, config, token);
                            console.log(conf);
                            var docEditor = new DocsAPI.DocEditor("placeholder", conf);
                            docEditor.createConnector();""", config=config, token=token, _onStart=True)

    def config(self):
        return {
                "document": {
                    "fileType": "docx",
                    "key": "apiwh0d3d560a-f766-4532-a6cb-e4ac583267e7",
                    "title": "Example Document Title.docx",
                    "url": "https://d2nlctn12v279m.cloudfront.net/assets/docs/samples/demo.docx",        
                },
                "documentType": "word",
                "height":"600px",
                "width":"100%"
                }
    
    @public_method
    def token(self, config):
        secret = self.getPreference('dev.onlyoffice_secret', pkg='adm')
        if not secret:
            return
        import jwt
        return dict(token=jwt.encode(config, secret, algorithm='HS256'))