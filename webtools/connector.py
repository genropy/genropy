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
    - 502: the signing service gave no signed connector."""

    content_type = 'application/vnd.softwell.connection+json'

    def refusal(self, message, status):
        return Response(message, status=status, mimetype='text/plain')

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
                url=site.currentRequest.host_url)
        except ConnectorError as e:
            return self.refusal(str(e), e.status)
        site.db.commit()
        self.download_name = f'{site.site_name}.site'
        return json.dumps(connector)
