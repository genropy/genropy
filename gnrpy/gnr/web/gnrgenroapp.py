# -*- coding: utf-8 -*-
"""Personal GenroApp site connectors, signed on request by the Softwell signing service.

The instance configuration holds the GenroApp data of the site::

    <genroapp name="My site"
              signing_url="https://host/signing/genroapp/connectors/sign"
              signing_token="..."
              capabilities="signature,printers"
              lock_minutes_max="30"
              duration_days="30"
              max_users="10"/>

``name``, ``signing_url`` and ``duration_days`` are mandatory. Without ``signing_token``
the token is asked to the package ``keycloak``, when the instance loads it. Without
``max_users`` the number of users is not limited. A site without the tag gives no connector.

The site never signs: it sends the fields of the tag, its own URL and the user to
``signing_url``; the signing service adds ``connector_id`` and ``expires`` and answers
the signed connector ``{payload, signature}``.
"""

import base64
import binascii
import json
from datetime import datetime, timezone

import requests

CONFIG_TAG = 'genroapp'
MANDATORY_ATTRIBUTES = ('name', 'signing_url', 'duration_days')
KEYCLOAK_PACKAGE = 'keycloak'
SIGNING_TIMEOUT = 20
EXPIRES_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class ConnectorError(Exception):
    """A connector that cannot be given; ``status`` is the HTTP status of the answer."""
    status = 500


class ConnectorUsersExceeded(ConnectorError):
    """The user holds no connector and the site already has ``max_users`` users."""
    status = 409


class ConnectorSigningError(ConnectorError):
    """The signing service did not answer a signed connector."""
    status = 502


def connector_config(application):
    """The ``<genroapp>`` tag of the instance configuration as a dict, None without the tag."""
    node = application.config.getNode(CONFIG_TAG)
    if node is None:
        return None
    attributes = node.attr
    for name in MANDATORY_ATTRIBUTES:
        if not attributes.get(name):
            raise ValueError(f'<{CONFIG_TAG}> in instanceconfig has no {name}')
    config = dict(name=attributes['name'],
                  signing_url=attributes['signing_url'],
                  signing_token=attributes.get('signing_token'),
                  duration_days=int(attributes['duration_days']),
                  capabilities=[c.strip() for c in (attributes.get('capabilities') or '').split(',') if c.strip()],
                  lock_minutes_max=None,
                  max_users=None)
    for name in ('lock_minutes_max', 'max_users'):
        if attributes.get(name):
            config[name] = int(attributes[name])
    return config


def signing_token(application, config):
    """The Bearer token for the signing service: the one of the tag, else an access
    token of the package ``keycloak`` of the instance."""
    if config['signing_token']:
        return config['signing_token']
    keycloak = application.packages[KEYCLOAK_PACKAGE]
    if keycloak is None:
        raise ValueError(f'<{CONFIG_TAG}> has no signing_token and the instance has no package {KEYCLOAK_PACKAGE}')
    return keycloak.getToken()


def signing_request(config, url, user):
    """The JSON body sent to the signing service for the connector of ``user`` on ``url``."""
    body = dict(name=config['name'], url=url, user=user, duration_days=config['duration_days'])
    if config['capabilities']:
        body['capabilities'] = config['capabilities']
    if config['lock_minutes_max']:
        body['lock_minutes_max'] = config['lock_minutes_max']
    return body


def sign_connector(config, token, url, user):
    """Ask the signing service the connector of ``user`` on ``url``.

    Returns ``(connector, connector_id, expires)``: the signed ``{payload, signature}``
    and the two fields the signing service wrote in the payload."""
    try:
        response = requests.post(config['signing_url'], json=signing_request(config, url, user),
                                 headers={'Authorization': f'Bearer {token}'}, timeout=SIGNING_TIMEOUT)
    except requests.RequestException as e:
        raise ConnectorSigningError(f'The signing service is not reachable: {type(e).__name__}')
    if response.status_code != 200:
        raise ConnectorSigningError(f'The signing service answered {response.status_code}')
    try:
        answer = response.json()
        connector = dict(payload=answer['payload'], signature=answer['signature'])
        if not all(isinstance(value, str) and value for value in connector.values()):
            raise ValueError('empty payload or signature')
        payload = json.loads(base64.b64decode(connector['payload'], validate=True))
        connector_id = payload['connector_id']
        expires = datetime.strptime(payload['expires'], EXPIRES_FORMAT).replace(tzinfo=timezone.utc)
    except (ValueError, KeyError, TypeError, binascii.Error):
        raise ConnectorSigningError('The signing service did not answer a signed connector')
    return connector, connector_id, expires
