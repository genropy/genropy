# -*- coding: utf-8 -*-
"""Personal GenroApp site connectors, signed on request by the Softwell signing service.

The instance configuration holds the GenroApp data of the site::

    <genroapp name="My site"
              signing_url="https://host/signing/genroapp/connectors/sign"
              signing_issuer="https://auth.example.org/realms/signer"
              signing_client_id="my-site"
              signing_client_secret="..."
              capabilities="signature,printers"
              lock_minutes_max="30"
              duration_days="30"
              max_users="10"/>

``name``, ``signing_url`` and ``duration_days`` are mandatory. The site proves itself to the
signing service with a Bearer token, taken in this order:

- ``signing_token``: a token written in the tag;
- ``signing_client_id`` and ``signing_client_secret``: the Keycloak client of the site in
  the realm ``signing_issuer``, mandatory with them (the URL of the realm, for example
  ``https://auth.example.org/realms/signer``); the site asks the token with the client
  credentials and asks it again before it expires, or when the signing service refuses it;
- the package ``keycloak`` of the instance, when the instance loads it.

Without ``max_users`` the number of users is not limited. A site without the tag gives no
connector.

The site never signs: it sends the fields of the tag, its own URL and the user to
``signing_url``; the signing service adds ``connector_id`` and ``expires`` and answers
the signed connector ``{payload, signature}``.
"""

import base64
import binascii
import json
import time
from datetime import datetime, timezone

import requests

CONFIG_TAG = 'genroapp'
MANDATORY_ATTRIBUTES = ('name', 'signing_url', 'duration_days')
KEYCLOAK_PACKAGE = 'keycloak'
TOKEN_PATH = '/protocol/openid-connect/token'
TOKEN_RENEW_MARGIN = 30
SIGNING_TIMEOUT = 20
EXPIRES_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class ConnectorError(Exception):
    """A connector that cannot be given; ``status`` is the HTTP status of the answer."""
    status = 500


class ConnectorUsersExceeded(ConnectorError):
    """The user holds no connector and the site already has ``max_users`` users."""
    status = 409


class ConnectorNotSiteUser(ConnectorError):
    """The user is not a user of the site database: GenroApp is not for it."""
    status = 403


class ConnectorSigningError(ConnectorError):
    """The signing service did not answer a signed connector."""
    status = 502


class ConnectorTokenRefused(ConnectorSigningError):
    """The signing service refused the token of the site (401): a kept token is dropped."""


def site_user(db, user_id):
    """True when ``user_id`` is a row of ``adm.user``. GenroApp is only for these users: a
    user of ``xml_auth`` has its username as ``user_id`` and no row, so connectors, devices
    and tickets, which refer to ``adm.user``, cannot be recorded for it."""
    return bool(user_id) and db.table('adm.user').existsRecord(user_id)


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
                  signing_client_id=attributes.get('signing_client_id'),
                  signing_client_secret=attributes.get('signing_client_secret'),
                  signing_issuer=(attributes.get('signing_issuer') or '').rstrip('/') or None,
                  duration_days=int(attributes['duration_days']),
                  capabilities=[c.strip() for c in (attributes.get('capabilities') or '').split(',') if c.strip()],
                  lock_minutes_max=None,
                  max_users=None)
    if config['signing_client_id'] and not config['signing_issuer']:
        raise ValueError(f'<{CONFIG_TAG}> in instanceconfig has signing_client_id and no signing_issuer')
    for name in ('lock_minutes_max', 'max_users'):
        if attributes.get(name):
            config[name] = int(attributes[name])
    return config


def signing_token(application, config):
    """The Bearer token for the signing service: the one of the tag, else the token of the
    Keycloak client of the site, else an access token of the package ``keycloak`` of the
    instance."""
    if config['signing_token']:
        return config['signing_token']
    if config['signing_client_id'] and config['signing_client_secret']:
        return client_token(application, config)
    keycloak = application.packages[KEYCLOAK_PACKAGE]
    if keycloak is None:
        raise ValueError(f'<{CONFIG_TAG}> has no signing_token, no signing_client_id and signing_client_secret, '
                         f'and the instance has no package {KEYCLOAK_PACKAGE}')
    return keycloak.getToken()


def client_token(application, config):
    """An access token of the Keycloak client ``signing_client_id``, asked with the client
    credentials to the realm ``signing_issuer``. It is kept on the application and asked
    again TOKEN_RENEW_MARGIN seconds before it expires."""
    tokens = application.__dict__.setdefault('genroapp_signing_tokens', {})
    key = (config['signing_issuer'], config['signing_client_id'])
    token, expiry = tokens.get(key, (None, 0))
    if token is None or time.time() > expiry - TOKEN_RENEW_MARGIN:
        try:
            response = requests.post(config['signing_issuer'] + TOKEN_PATH,
                                     data=dict(grant_type='client_credentials',
                                               client_id=config['signing_client_id'],
                                               client_secret=config['signing_client_secret']),
                                     timeout=SIGNING_TIMEOUT)
        except requests.RequestException as e:
            raise ConnectorSigningError(f'The token service is not reachable: {type(e).__name__}')
        if response.status_code != 200:
            raise ConnectorSigningError(f'The token service answered {response.status_code}')
        try:
            answer = response.json()
            token, expiry = answer['access_token'], time.time() + float(answer['expires_in'])
            if not isinstance(token, str) or not token:
                raise ValueError('empty access token')
        except (ValueError, KeyError, TypeError):
            raise ConnectorSigningError('The token service did not answer an access token')
        tokens[key] = (token, expiry)
    return token


def forget_client_token(application, config):
    """Drop the kept token of the Keycloak client of ``config``: the next request asks a new one."""
    tokens = application.__dict__.get('genroapp_signing_tokens') or {}
    tokens.pop((config['signing_issuer'], config['signing_client_id']), None)


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
    if response.status_code == 401:
        raise ConnectorTokenRefused('The signing service refused the token of the site')
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
