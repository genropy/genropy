#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

from werkzeug.wrappers import Response

from gnr.web.gnrbaseclasses import BaseWebtool
from gnr.web.gnrgenroapp import ConnectorError, connector_config

TOOLS_SEGMENT = '_tools'


class Connector(BaseWebtool):
    """Give the logged user the personal site connector that opens this site in GenroApp.

    The connector is signed on request by the Softwell signing service named in the
    ``<genroapp>`` tag of the instance configuration; this tool never signs anything.
    A browser downloads it as a file; GenroApp reads it from its login window.

    - 404: the site has no ``<genroapp>`` tag;
    - 401: no logged user;
    - 409: the user holds no connector and the site already has ``max_users`` users;
    - 502: the signing service gave no signed connector.

    The connector names the public URL the request came through: the path of the site
    and the domain or the store the router resolved. The answer is personal: it is
    never cached."""

    content_type = 'application/vnd.softwell.connection+json'

    def refusal(self, message, status):
        return Response(message, status=status, mimetype='text/plain')

    def public_url(self):
        """The URL GenroApp opens: host, path of the site and the segment of the request
        path the router resolved before ``_tools`` (a store or a domain), if any. Only
        the path of the request is read: a ``base_dbstore`` among the request
        parameters never changes the signed URL."""
        site = self.site
        request = site.currentRequest
        route = site.get_path_list(request.path)
        prefix = route[:route.index(TOOLS_SEGMENT)]
        return request.host_url.rstrip('/') + site.default_uri + ''.join(f'{segment}/' for segment in prefix)

    def __call__(self, **kwargs):
        site = self.site
        config = connector_config(site.gnrapp)
        if config is None:
            return self.refusal('No GenroApp site connector for this site', 404)
        connection = site.get_logged_connection()
        if connection is None:
            return self.refusal('Log in to get the GenroApp site connector', 401)
        try:
            connector = site.db.table('adm.user_connector').newConnector(
                config, user_id=connection['user_id'], user=connection['user'],
                url=self.public_url())
        except ConnectorError as e:
            return self.refusal(str(e), e.status)
        site.db.commit()
        self.download_name = f'{site.site_name}.site'
        self.headers = [('Cache-Control', 'private, no-store')]
        return json.dumps(connector)
