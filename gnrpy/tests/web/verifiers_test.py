from base64 import b64encode

from gnr.web.verifiers import AuthorizationBaseTagsVerifier


class _RequestStub(object):
    def __init__(self, headers=None):
        self.headers = headers or {}


class _AvatarStub(object):
    user_tags = 'pos'


class _ApplicationStub(object):
    def __init__(self, avatar=None):
        self.avatar = avatar

    def getAvatar(self, user, pwd, authenticate=None):
        return self.avatar

    def checkResourcePermission(self, tags, userTags):
        tags = set((tags or '').split(','))
        return bool(tags & set((userTags or '').split(',')))


class _PageStub(object):
    def __init__(self, userTags=None, headers=None, avatar=None):
        self.userTags = userTags
        self.request = _RequestStub(headers)
        self.application = _ApplicationStub(avatar)
        self.avatar = None
        self.raised = None

    def exception(self, exception, **kwargs):
        self.raised = (exception, kwargs)
        return Exception(exception)


def test_session_tags_need_no_basic_authorization():
    """A logged in user calling a tagged public method must not be asked
    for a Basic Authorization header."""
    page = _PageStub(userTags='pos,user')
    assert AuthorizationBaseTagsVerifier(page).verify(tags='pos,admin') is None
    assert page.raised is None


def test_session_tags_not_matching_gives_user_not_allowed():
    page = _PageStub(userTags='user')
    assert AuthorizationBaseTagsVerifier(page).verify(tags='pos,admin', method='doit')
    assert page.raised == ('user_not_allowed', dict(method='doit'))


def test_missing_session_still_requires_basic_authorization():
    page = _PageStub()
    assert AuthorizationBaseTagsVerifier(page).verify(tags='pos')
    assert page.raised[0] == 'basic_authentication'
    assert page.raised[1]['msg'] == 'Missing Basic Authorization'


def test_basic_authorization_tags_are_checked():
    credentials = b64encode(b'mario:secret').decode()
    page = _PageStub(headers={'Authorization': 'Basic %s' % credentials},
                     avatar=_AvatarStub())
    assert AuthorizationBaseTagsVerifier(page).verify(tags='pos') is None
    assert page.avatar is not None
    assert AuthorizationBaseTagsVerifier(page).verify(tags='admin', method='doit')
    assert page.raised == ('user_not_allowed', dict(method='doit'))
