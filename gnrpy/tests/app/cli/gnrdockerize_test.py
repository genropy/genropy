from types import SimpleNamespace

import yaml

from gnr.app.cli.gnrdockerize import MultiStageDockerImageBuilder


def _make_builder(instance_name='myapp', mako=False, fqdns=None):
    b = MultiStageDockerImageBuilder.__new__(MultiStageDockerImageBuilder)
    b.instance_name = instance_name
    b.options = SimpleNamespace(
        mako=mako, fqdns=fqdns or [], router='traefik',
    )
    return b


# ---------- _compute_extra_labels ----------

def test_extra_labels_empty_when_no_fqdns():
    assert _make_builder()._compute_extra_labels() == []


def test_extra_labels_empty_when_router_not_traefik():
    b = _make_builder(fqdns=['myapp.local'])
    b.options.router = 'nginx'
    assert b._compute_extra_labels() == []


def test_extra_labels_traefik_when_fqdns():
    labels = _make_builder(fqdns=['myapp.local'])._compute_extra_labels()
    keys = [k for k, _ in labels]
    assert 'traefik.enable' in keys
    port_key = 'traefik.http.services.myapp_svc_web.loadbalancer.server.port'
    port_value = next(v for k, v in labels if k == port_key)
    assert port_value == 8888 and isinstance(port_value, int)


# ---------- builder path ----------

def test_compose_builder_minimal():
    parsed = yaml.safe_load(_make_builder()._generate_compose_yaml('1.0'))
    assert parsed['services']['myapp']['image'] == 'myapp:1.0'
    assert parsed['services']['myapp_db']['image'] == 'postgres:latest'
    assert 'labels' not in parsed['services']['myapp']


def test_compose_builder_with_traefik_labels():
    parsed = yaml.safe_load(
        _make_builder(fqdns=['myapp.local'])._generate_compose_yaml('1.0')
    )
    labels = parsed['services']['myapp']['labels']
    assert labels['traefik.enable'] == 'true'
    port_key = 'traefik.http.services.myapp_svc_web.loadbalancer.server.port'
    assert labels[port_key] == 8888


def test_compose_builder_dollar_var_preserved():
    raw = _make_builder()._generate_compose_yaml('1.0')
    assert '${GNR_DB_HOST:-myapp_db}' in raw
    assert '${GNR_ROOTPWD:-admin}' in raw
    assert '${GNR_DB_PASSWORD:-S3cret}' in raw


def test_compose_builder_healthcheck_test_is_list():
    parsed = yaml.safe_load(_make_builder()._generate_compose_yaml('1.0'))
    test = parsed['services']['myapp_db']['healthcheck']['test']
    assert test == ['CMD-SHELL', 'pg_isready -U genro -d myapp']


def test_compose_builder_db_environment_is_mapping():
    parsed = yaml.safe_load(_make_builder()._generate_compose_yaml('1.0'))
    env = parsed['services']['myapp_db']['environment']
    assert env == {
        'POSTGRES_PASSWORD': 'S3cret',
        'POSTGRES_USER': 'genro',
        'POSTGRES_DB': 'myapp',
    }


def test_compose_builder_app_volume_mount():
    parsed = yaml.safe_load(_make_builder()._generate_compose_yaml('1.0'))
    assert parsed['services']['myapp']['volumes'] == [
        'myapp_site:/home/genro/site/'
    ]


def test_compose_builder_explicit_start_marker():
    raw = _make_builder()._generate_compose_yaml('1.0')
    assert raw.startswith('---\n')


# ---------- mako legacy path ----------

def test_compose_legacy_mako_minimal():
    parsed = yaml.safe_load(
        _make_builder(mako=True)._generate_compose_yaml('1.0')
    )
    assert parsed['services']['myapp']['image'] == 'myapp:1.0'
    assert parsed['services']['myapp_db']['image'] == 'postgres:latest'


def test_compose_legacy_mako_dollar_var_preserved():
    raw = _make_builder(mako=True)._generate_compose_yaml('1.0')
    assert '${GNR_DB_HOST:-myapp_db}' in raw
    assert '${GNR_ROOTPWD:-admin}' in raw
