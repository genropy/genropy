import subprocess
from types import SimpleNamespace

import pytest
import yaml

from gnr.app.cli.gnrdockerize import (
    MultiStageDockerImageBuilder,
    browsable_repo_url,
    strip_url_credentials,
)
from gnr.dev.builder import GnrProjectBuilder


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


# ---------- traefik rules ----------

def test_traefik_rules_have_balanced_parentheses():
    labels = dict(_make_builder(fqdns=['a.local', 'b.local'])._compute_extra_labels())
    assert labels['traefik.http.routers.myapp_web.rule'] == (
        '(Host(`a.local`) || Host(`b.local`)) && !Path(`/websocket`)'
    )
    assert labels['traefik.http.routers.myapp_wsk.rule'] == (
        '(Host(`a.local`) || Host(`b.local`)) && Path(`/websocket`)'
    )


def test_compose_legacy_mako_traefik_rule():
    parsed = yaml.safe_load(
        _make_builder(mako=True, fqdns=['a.local'])._generate_compose_yaml('1.0')
    )
    rule = parsed['services']['myapp']['labels']['traefik.http.routers.myapp_web.rule']
    assert rule == '(Host(`a.local`)) && !Path(`/websocket`)'


# ---------- repository URLs in image labels ----------

@pytest.mark.parametrize('url,expected', [
    ('https://x-access-token:abc@github.com/org/repo.git', 'https://github.com/org/repo.git'),
    ('https://gitlab-ci-token:abc@gitlab.com/org/repo', 'https://gitlab.com/org/repo'),
    ('ssh://git@github.com/org/repo.git', 'ssh://github.com/org/repo.git'),
    ('git@github.com:org/repo.git', 'git@github.com:org/repo.git'),
    ('https://github.com/org/repo.git', 'https://github.com/org/repo.git'),
])
def test_strip_url_credentials(url, expected):
    assert strip_url_credentials(url) == expected


@pytest.mark.parametrize('url', [
    'git@github.com:org/repo.git',
    'https://github.com/org/repo.git',
    'https://x-access-token:abc@github.com/org/repo.git',
    'ssh://git@github.com/org/repo.git',
])
def test_browsable_repo_url(url):
    assert browsable_repo_url(url) == 'https://github.com/org/repo'


def test_browsable_repo_url_other_hosts():
    assert browsable_repo_url('git@hub.genro.com:softwell/erpy.git') == (
        'https://hub.genro.com/softwell/erpy'
    )


def test_git_url_from_path_ignores_insteadof_rewrites(tmp_path, monkeypatch):
    """A token injected by url.*.insteadOf (common in CI) must not be read back."""
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    subprocess.run(['git', 'remote', 'add', 'origin', 'git@github.com:org/repo.git'],
                   cwd=tmp_path, check=True)
    monkeypatch.setenv('GIT_CONFIG_COUNT', '1')
    monkeypatch.setenv('GIT_CONFIG_KEY_0', 'url.https://x-access-token:abc@github.com/.insteadOf')
    monkeypatch.setenv('GIT_CONFIG_VALUE_0', 'git@github.com:')
    builder = GnrProjectBuilder.__new__(GnrProjectBuilder)
    assert builder.git_url_from_path(str(tmp_path)) == 'git@github.com:org/repo.git'
