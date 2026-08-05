import yaml

from gnr.utils.dockercompose import DockerComposeBuilder


def _parse(builder):
    return yaml.safe_load(builder.toYaml(explicit_start=True))


# ---------- empty / lazy sections ----------

def test_empty_builder_produces_no_sections():
    """Sections are lazy: an unused builder produces an empty document."""
    b = DockerComposeBuilder()
    assert _parse(b) == {}


def test_only_used_sections_appear():
    """Calling volume() must not produce an empty 'services' section."""
    b = DockerComposeBuilder()
    b.volume('site_data')
    parsed = _parse(b)
    assert 'volumes' in parsed
    assert 'services' not in parsed


# ---------- top-level getters ----------

def test_services_getter_is_top_level_node():
    b = DockerComposeBuilder()
    b.service('db', image='postgres')
    b.service('app', image='myapp')
    assert set(b.services().to_python().keys()) == {'db', 'app'}


def test_volumes_getter_is_top_level_node():
    b = DockerComposeBuilder()
    b.volume('a')
    b.volume('b')
    assert b.volumes().to_python() == {'a': {}, 'b': {}}


def test_networks_configs_secrets_getters():
    b = DockerComposeBuilder()
    b.network('frontend')
    b.config('app_cfg')
    b.secret('db_pwd')
    parsed = _parse(b)
    assert parsed['networks'] == {'frontend': {}}
    assert parsed['configs'] == {'app_cfg': {}}
    assert parsed['secrets'] == {'db_pwd': {}}


# ---------- volume ----------

def test_volume_default_is_empty_mapping():
    b = DockerComposeBuilder()
    b.volume('site_data')
    assert _parse(b) == {'volumes': {'site_data': {}}}


def test_volume_can_be_populated_with_attributes():
    """Less common keys (driver, external, ...) via the returned node."""
    b = DockerComposeBuilder()
    vol = b.volume('site_data')
    vol.set('driver', 'local')
    vol.set('external', True)
    parsed = _parse(b)
    assert parsed['volumes']['site_data'] == {'driver': 'local', 'external': True}


# ---------- service ----------

def test_minimal_service():
    b = DockerComposeBuilder()
    b.service('app', image='myapp')
    assert _parse(b) == {'services': {'app': {'image': 'myapp'}}}


def test_service_with_version_tag():
    b = DockerComposeBuilder()
    b.service('app', image='myapp', version_tag='1.0')
    assert _parse(b)['services']['app']['image'] == 'myapp:1.0'


def test_service_environment_as_mapping():
    b = DockerComposeBuilder()
    b.service('app', image='myapp', environment={'A': 'x', 'B': 42})
    assert _parse(b)['services']['app']['environment'] == {'A': 'x', 'B': 42}


def test_service_ports():
    b = DockerComposeBuilder()
    b.service('app', image='myapp', ports=['8888:8888', '9999:9999'])
    assert _parse(b)['services']['app']['ports'] == ['8888:8888', '9999:9999']


def test_service_depends_on():
    b = DockerComposeBuilder()
    b.service('app', image='myapp',
              depends_on={'db': {'condition': 'service_healthy'}})
    assert _parse(b)['services']['app']['depends_on'] == {
        'db': {'condition': 'service_healthy'}
    }


def test_service_labels():
    b = DockerComposeBuilder()
    b.service('app', image='myapp',
              labels={'traefik.enable': 'true', 'port': 8888})
    assert _parse(b)['services']['app']['labels'] == {
        'traefik.enable': 'true', 'port': 8888,
    }


def test_service_volumes():
    b = DockerComposeBuilder()
    b.service('app', image='myapp', volumes=['site_data:/home/site/'])
    assert _parse(b)['services']['app']['volumes'] == ['site_data:/home/site/']


def test_service_healthcheck():
    b = DockerComposeBuilder()
    b.service('db', image='postgres:latest',
              healthcheck={'test': ['CMD-SHELL', 'pg_isready'],
                           'interval': '10s',
                           'retries': 5})
    assert _parse(b)['services']['db']['healthcheck'] == {
        'test': ['CMD-SHELL', 'pg_isready'],
        'interval': '10s',
        'retries': 5,
    }


def test_service_returns_node_for_extension():
    """Less common keys can be added on the returned node directly."""
    b = DockerComposeBuilder()
    srv = b.service('app', image='myapp')
    srv.set('restart', 'unless-stopped')
    srv.set('user', 'genro')
    parsed = _parse(b)['services']['app']
    assert parsed['restart'] == 'unless-stopped'
    assert parsed['user'] == 'genro'


def test_dollar_var_preserved_in_environment():
    b = DockerComposeBuilder()
    b.service('app', image='myapp',
              environment={'DB_HOST': '${DB_HOST:-mydb}'})
    raw = b.toYaml()
    assert '${DB_HOST:-mydb}' in raw


# ---------- realistic scenario ----------

def test_full_compose_shape():
    """Two-service compose: db + app with healthcheck and dependency."""
    b = DockerComposeBuilder()
    b.volume('site')
    b.service('db', image='postgres:latest',
              environment={'POSTGRES_DB': 'app'},
              healthcheck={'test': ['CMD-SHELL', 'pg_isready'],
                           'interval': '10s'})
    b.service('app', image='myapp', version_tag='1.0',
              ports=['8888:8888'],
              depends_on={'db': {'condition': 'service_healthy'}},
              volumes=['site:/home/site/'])
    parsed = _parse(b)
    assert parsed['volumes'] == {'site': {}}
    assert parsed['services']['db']['image'] == 'postgres:latest'
    assert parsed['services']['app']['image'] == 'myapp:1.0'
    assert parsed['services']['app']['depends_on'] == {
        'db': {'condition': 'service_healthy'}
    }
