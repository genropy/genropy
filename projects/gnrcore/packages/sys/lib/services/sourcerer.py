import os
import urllib.request
import urllib.error
import json

import secrets

DEFAULT_SOURCERER_URL = 'https://sourcerer.genropy.net'


class SourcererClient:
    """HTTP client for Sourcerer API communication."""

    def __init__(self, url=None, sourcerer_token=None):
        self.url = (url or os.environ.get('GNR_SOURCERER_URL', DEFAULT_SOURCERER_URL)).rstrip('/')
        self.sourcerer_token = sourcerer_token

    def _request(self, endpoint, payload=None, method='POST',
                 authenticated=True, timeout=10):
        headers = {}
        if authenticated and self.sourcerer_token:
            headers['Authorization'] = f'Bearer {self.sourcerer_token}'
        if payload:
            headers['Content-Type'] = 'application/json'
        data = json.dumps(payload).encode('utf-8') if payload else None
        req = urllib.request.Request(
            f'{self.url}/api/{endpoint}',
            data=data,
            headers=headers,
            method=method
        )
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            raise Exception(f'Sourcerer API error {e.code}: {e.reason}') from e
        return json.loads(resp.read().decode('utf-8'))

    def request_registration(self, host, name, callback_url):
        callback_token = secrets.token_urlsafe()
        data = self._request('srv/request_server_registration',
                             payload={'host': host, 'name': name,
                                      'callback_url': callback_url,
                                      'callback_token': callback_token},
                             authenticated=False)
        return {
            'token': callback_token,
            'sourcerer_token': data.get('token', '')
        }

    def check_status(self):
        if not self.sourcerer_token:
            return 'idle'
        try:
            self._request('srv/status', method='GET', timeout=5)
            return 'enabled'
        except urllib.error.HTTPError as e:
            if e.code == 403:
                return 'pending'
            return 'idle'
        except Exception:
            return 'idle'

    def api_request(self, endpoint, payload=None, method='POST'):
        return self._request(endpoint, payload=payload, method=method)
