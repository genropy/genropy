"""Verifier classes for GnrWebPage public method authentication.

Each verifier is instantiated with a page reference and called by
getPublicMethod before dispatching the handler. The __call__ contract is:

- Return None on success (verification passed).
- Return an exception instance on failure (caller will raise it).

Verifiers can be attached to handlers via the ``verifier`` attribute
on the @public_method decorator, or applied automatically when the
handler declares ``tags`` (falls back to AuthorizationBaseTagsVerifier).
"""

from base64 import b64decode


class GnrVerifier():
    """Base verifier. Subclasses must override __call__ to implement
    their authentication logic."""

    def __init__(self,page):
        self.page = page

    def __call__(self,**kwargs):
        pass

    verify = __call__


class AuthorizationBearerVerifier(GnrVerifier):
    """Verifier for Bearer token authentication.

    Extracts the token from the Authorization header and compares it
    against the value returned by get_token_to_verify().
    Subclasses must override get_token_to_verify() to provide the
    expected token."""

    def __call__(self,**kwargs):
        bearer = self.get_bearer()
        if not bearer:
            return self.page.exception('user_not_allowed', method='bearer_auth')
        token_to_verify = self.get_token_to_verify()
        if bearer != token_to_verify:
            return self.page.exception('user_not_allowed', method='bearer_auth')

    def get_bearer(self):
        """Extract the bearer token from the Authorization header.
        Returns the token string or None if missing/invalid."""
        auth_header = self.page.request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None
        return auth_header[7:]

    def get_token_to_verify(self):
        """Return the expected token. Must be overridden by subclasses."""
        return


class AuthorizationBaseTagsVerifier(GnrVerifier):
    """Verifier for HTTP Basic Authentication with tag-based authorization.

    Decodes Basic Auth credentials, authenticates the user via getAvatar,
    and checks resource permissions against the handler's required tags."""

    def __call__(self,tags=None,**kwargs):
        authorization = self.page.request.headers.get('Authorization')
        if not authorization:
            return self.page.exception('basic_authentication',msg='Missing Basic Authorization')
        parts = authorization.split(' ', 1)
        if len(parts) != 2 or parts[0] != 'Basic':
            return self.page.exception('basic_authentication', msg='Wrong Authorization Mode')
        try:
            user, pwd = b64decode(parts[1]).decode().split(':', 1)
        except Exception:
            return self.page.exception('basic_authentication', msg='Invalid Authorization Header')
        self.page.avatar = self.page.application.getAvatar(user, pwd, authenticate=True)
        if not self.page.avatar:
            return self.page.exception('basic_authentication', msg='Wrong Authorization Login')
        userTags = self.page.userTags or self.page.avatar.user_tags
        if not self.page.application.checkResourcePermission(tags, userTags):
            return self.page.exception('basic_authentication', msg='User not allowed')
