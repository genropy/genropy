# -*- coding: utf-8 -*-

"""OData/GraphQL data API endpoint for GenroPy.

Temporary location in sys/webpages for testing.
Access via: /sys/apidata/<odata_path>

Examples:
    GET /sys/apidata/$metadata
    GET /sys/apidata/pkg.customer
    GET /sys/apidata/pkg.customer?$top=10&$filter=name eq 'Alice'
    GET /sys/apidata/pkg.customer(123)
    GET /sys/apidata/pkg.customer/$count
"""

import json
import logging

from gnr.core.gnrdecorator import public_method

logger = logging.getLogger('gnr.web.apidata')

try:
    from genro_data_api.odata import ODataRequestHandler
    from gnr.sql.gnrsql.data_api_adapter import GnrSqlDataApiAdapter
    HAS_DATA_API = True
except ImportError:
    HAS_DATA_API = False


class GnrCustomWebPage(object):
    py_requires = 'gnrcomponents/externalcall:BaseRpc'
    skip_connection = True
    convert_result = False

    def rootPage(self, *args, **kwargs):
        """Route all requests to the OData handler."""
        if 'pagetemplate' in kwargs:
            kwargs.pop('pagetemplate')
        if not HAS_DATA_API:
            self.response.content_type = 'application/json'
            self.response.status = '501 Not Implemented'
            return json.dumps({
                'error': {
                    'code': '501',
                    'message': 'genro-data-api is not installed. Run: pip install genro-data-api',
                }
            })

        adapter = GnrSqlDataApiAdapter(self.db)
        handler = ODataRequestHandler(adapter, service_root='')

        method = self.request.method
        odata_path = '/' + '/'.join(args) if args else '/'
        query_params = {}
        for k, v in self.request.args.items():
            query_params[k] = v

        try:
            status_code, headers, body = handler.handle(method, odata_path, query_params)
        except Exception as exc:
            import traceback
            self.response.content_type = 'application/json'
            self.response.status_code = 500
            return json.dumps({
                'error': {
                    'code': '500',
                    'message': str(exc),
                    'traceback': traceback.format_exc(),
                }
            })

        self.response.status_code = status_code
        for header_name, header_value in headers.items():
            self.response.headers[header_name] = header_value
        return body
