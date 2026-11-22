#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

from werkzeug.wrappers import Response

from gnr.web.gnrbaseclasses import BaseWebtool
from gnr.web.gnrgenroapp import ConnectorError, connector_config


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

    def public_url(self, base_dbstore=None):
        """The URL GenroApp opens: host, path of the site and, when the request named
        one, the store. On a multidomain site the store is the domain ``home_uri``
        already carries."""
        site = self.site
        url = site.currentRequest.host_url.rstrip('/') + site.home_uri
        if base_dbstore and not site.multidomain:
            url = f'{url}{base_dbstore}/'
        return url

    def __call__(self, base_dbstore=None, **kwargs):
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
                url=self.public_url(base_dbstore))
        except ConnectorError as e:
            return self.refusal(str(e), e.status)
        site.db.commit()
        self.download_name = f'{site.site_name}.site'
        self.headers = [('Cache-Control', 'private, no-store')]
        return json.dumps(connector)
