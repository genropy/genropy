import pytest

from gnr.app.gnrdeploy import NGINX_TEMPLATE, GunicornDeployBuilder

MAINTENANCE_LOCATION = 'location @gnr_maintenance'


def _make_builder(supervisord_monitor_parameters=None):
    """Build the object without __init__: the real one resolves paths,
    reads the siteconfig and creates directories on disk."""
    b = GunicornDeployBuilder.__new__(GunicornDeployBuilder)
    b.site_name = 'mysite'
    b.site_path = '/home/genro/sites/mysite'
    b.logs_path = '/home/genro/sites/mysite/logs'
    b.gnrasync_socket_path = '/tmp/mysite_gnrasync.sock'
    b.gunicorn_socket_path = '/tmp/mysite_gunicorn.sock'
    b.supervisord_socket_path = '/tmp/mysite_supervisord.sock'
    b.supervisord_monitor_parameters = supervisord_monitor_parameters
    return b


def _render(builder, domain='mysite.local'):
    """Render NGINX_TEMPLATE the way write_nginx_conf does, without
    writing the conf file to the current working directory."""
    pars = dict(
        domain=domain,
        site_path=builder.site_path,
        logs_path=builder.logs_path,
        gnrasync_socket_path=builder.gnrasync_socket_path,
        gunicorn_socket_path=builder.gunicorn_socket_path,
        supervisord_location=builder.supervisord_monitor_location(),
    )
    return NGINX_TEMPLATE % pars


# ---------- rendering ----------

def test_nginx_template_renders_without_placeholder_error():
    # Guards against a stray unescaped '%' in the template, which would
    # raise at `NGINX_TEMPLATE % pars` time in write_nginx_conf.
    conf = _render(_make_builder())
    assert 'mysite.local' in conf
    assert '%(' not in conf


def test_nginx_template_renders_with_supervisord_location():
    builder = _make_builder(supervisord_monitor_parameters={'username': 'admin'})
    conf = _render(builder)
    assert 'location /supervisord' in conf
    assert '/tmp/mysite_supervisord.sock' in conf


def test_supervisord_location_empty_without_parameters():
    assert _make_builder().supervisord_monitor_location() == ''
    assert _make_builder(
        supervisord_monitor_parameters={'port': 9001}
    ).supervisord_monitor_location() == ''


# ---------- maintenance 503 ----------

@pytest.mark.parametrize('supervisord', [None, {'username': 'admin'}])
def test_maintenance_location_present(supervisord):
    conf = _render(_make_builder(supervisord_monitor_parameters=supervisord))
    assert 'proxy_intercept_errors on;' in conf
    assert 'error_page 502 503 504 = @gnr_maintenance;' in conf
    assert MAINTENANCE_LOCATION in conf
    assert 'add_header Retry-After 5 always;' in conf
    assert '"code":"MAINTENANCE"' in conf
    assert 'default_type application/json;' in conf


def test_maintenance_location_defined_once():
    conf = _render(_make_builder())
    assert conf.count(MAINTENANCE_LOCATION) == 1
    assert conf.count('proxy_intercept_errors') == 1
    assert conf.count('error_page') == 1


def test_intercept_lives_in_root_location_not_websocket():
    conf = _render(_make_builder())
    websocket_at = conf.index('location /websocket')
    root_at = conf.index('location / {')
    intercept_at = conf.index('proxy_intercept_errors')
    maintenance_at = conf.index(MAINTENANCE_LOCATION)
    # a JSON 503 is meaningless on a websocket upgrade: the intercept must
    # sit in `location /`, which is served after /websocket in the template
    assert websocket_at < root_at < intercept_at < maintenance_at


def test_maintenance_returns_503():
    conf = _render(_make_builder())
    return_line = next(
        line.strip() for line in conf.splitlines() if 'return 503' in line
    )
    assert return_line.startswith('return 503 ')
    assert return_line.endswith("please retry\"}';")


def test_500_is_not_intercepted():
    # application tracebacks come back as HTTP 200 with an error payload,
    # so a real 500 is a worker crash and must not read as retriable
    conf = _render(_make_builder())
    error_page_line = next(
        line for line in conf.splitlines() if 'error_page' in line
    )
    assert '500' not in error_page_line


# ---------- structure ----------

@pytest.mark.parametrize('supervisord', [None, {'username': 'admin'}])
def test_rendered_conf_braces_balance(supervisord):
    conf = _render(_make_builder(supervisord_monitor_parameters=supervisord))
    assert conf.count('{') == conf.count('}')
    depth = 0
    for char in conf:
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            assert depth >= 0, 'unbalanced closing brace in rendered conf'
    assert depth == 0
