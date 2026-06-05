import json
import logging
from base64 import b64decode

from werkzeug.wrappers import Response
from werkzeug.exceptions import NotImplemented as NotImplementedHTTP

logger = logging.getLogger("gnr.web")

try:
    from genro_routes import RoutingClass, Router
    from genro_routes.exceptions import (NotFound as RouteNotFound,
                                         NotAuthenticated as RouteNotAuthenticated,
                                         NotAuthorized as RouteNotAuthorized)
    HAS_GENRO_ROUTES = True
except ImportError:
    HAS_GENRO_ROUTES = False


class ApiDispatcher(object):
    """Site proxy for REST API dispatching via genro-routes.

    If genro-routes is installed, creates a RoutingClass-based router
    and dispatches /_api requests through it. Otherwise returns 501.
    """

    def __init__(self, site):
        self.site = site
        if HAS_GENRO_ROUTES:
            self._owner = _ApiRouterOwner()
            self.router = self._owner.api
        else:
            self._owner = None
            self.router = None

    @property
    def available(self):
        return self.router is not None

    def dispatch(self, path_list, environ, start_response, **kwargs):
        response = Response()
        response.content_type = 'application/json'
        try:
            if not self.available:
                exc = NotImplementedHTTP(description='API dispatcher is not available')
                return exc(environ, start_response)
            api_path = '/'.join(path_list[1:])
            auth_header = environ.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Basic '):
                encoded = auth_header[6:]
                decoded = b64decode(encoded).decode('utf-8')
                username, _, password = decoded.partition(':')
                avatar = self.site.gnrapp.getAvatar(username, password=password,
                                                    authenticate=True)
                if avatar is None:
                    return self.site.unauthorized_exception(
                        environ, start_response,
                        debug_message='Invalid credentials')
            node = self.router.node(api_path)
            result = node(**kwargs)
            response.data = json.dumps(result)
        except RouteNotAuthenticated:
            return self.site.unauthorized_exception(
                environ, start_response,
                debug_message='Authentication required')
        except RouteNotAuthorized:
            return self.site.forbidden_exception(
                environ, start_response,
                debug_message='Access denied')
        except RouteNotFound:
            return self.site.not_found_exception(
                environ, start_response,
                debug_message='API route not found: %s' % '/'.join(path_list))
        except Exception:
            raise
        finally:
            self.site.cleanup()
        return response(environ, start_response)


if HAS_GENRO_ROUTES:
    class _ApiRouterOwner(RoutingClass):
        def __init__(self):
            self.api = Router(self, name='api', branch=True)
