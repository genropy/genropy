import io
import os
import tempfile

import pytest
import yaml

from gnr.web.gnrk8s import GnrK8SGenerator


def _make_generator(fqdns=None, image='myregistry/myapp:1.0', **kwargs):
    return GnrK8SGenerator(
        instance_name='myapp',
        image=image,
        fqdns=fqdns if fqdns is not None else [],
        **kwargs,
    )


def _generate_docs(generator):
    buf = io.StringIO()
    generator.generate_conf(fp=buf)
    return [d for d in yaml.safe_load_all(buf.getvalue()) if d]


def _collect_kinds(generator):
    return [d['kind'] for d in _generate_docs(generator)]


# ---------- no-FQDN (internal-only) ----------

def test_no_fqdns_omits_ingress():
    assert 'Ingress' not in _collect_kinds(_make_generator(fqdns=[]))


def test_no_fqdns_omits_ingress_split_mode():
    assert 'Ingress' not in _collect_kinds(_make_generator(fqdns=[], split=True))


def test_no_fqdns_omits_externalhost_env():
    g = _make_generator(fqdns=[])
    assert 'GNR_EXTERNALHOST' not in [e['name'] for e in g.env]


# ---------- with FQDNs ----------

def test_with_fqdns_includes_ingress():
    assert 'Ingress' in _collect_kinds(_make_generator(fqdns=['myapp.example.com']))


def test_with_fqdns_ingress_rules_match():
    fqdns = ['a.example.com', 'b.example.com']
    docs = _generate_docs(_make_generator(fqdns=fqdns))
    ingress = next(d for d in docs if d['kind'] == 'Ingress')
    assert [r['host'] for r in ingress['spec']['rules']] == fqdns


def test_with_fqdns_tls_hosts_match():
    fqdns = ['secure.example.com']
    docs = _generate_docs(_make_generator(fqdns=fqdns))
    ingress = next(d for d in docs if d['kind'] == 'Ingress')
    assert ingress['spec']['tls'][0]['hosts'] == fqdns


# ---------- image tag ----------

def test_image_without_tag_gets_latest():
    g = _make_generator(image='myregistry/myapp')
    assert g.image == 'myregistry/myapp:latest'


def test_image_with_tag_unchanged():
    g = _make_generator()
    assert g.image == 'myregistry/myapp:1.0'


# ---------- env_file ----------

def test_env_file_missing_does_not_raise():
    g = _make_generator(env_file='/nonexistent/path/env.file')
    assert all(e['name'] != 'MYVAR' for e in g.env)


def test_env_file_loaded_into_env():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write('MYVAR=myvalue\n')
        f.write('OTHER=123\n')
        f.write('NOEQUAL\n')
        fname = f.name
    try:
        g = _make_generator(env_file=fname)
        env_map = {e['name']: e['value'] for e in g.env}
        assert env_map['MYVAR'] == 'myvalue'
        assert env_map['OTHER'] == '123'
        assert 'NOEQUAL' not in env_map
    finally:
        os.unlink(fname)


# ---------- extra_initContainers validation ----------

def test_extra_initcontainers_are_included():
    extra = [{'name': 'my-init', 'image': 'busybox', 'command': ['sh', '-c', 'echo hi']}]
    g = _make_generator(extra_initContainers=extra)
    assert 'my-init' in [c['name'] for c in g.extra_initContainers]


def test_extra_initcontainers_non_dict_raises():
    with pytest.raises(TypeError, match="must be a dict"):
        _make_generator(extra_initContainers=["not-a-dict"])


def test_extra_initcontainers_missing_key_raises():
    with pytest.raises(ValueError, match="Missing required"):
        _make_generator(extra_initContainers=[{'name': 'x', 'image': 'busybox'}])


def test_extra_initcontainers_duplicate_name_raises():
    dup = {'name': 'volume-permissions', 'image': 'busybox', 'command': ['sh']}
    with pytest.raises(ValueError, match="duplicates"):
        _make_generator(extra_initContainers=[dup])


# ---------- namespace ----------

def test_namespace_applied_to_all_resources():
    docs = _generate_docs(_make_generator(fqdns=['x.example.com'], namespace='mynamespace'))
    for doc in docs:
        assert doc['metadata'].get('namespace') == 'mynamespace', \
            f"{doc['kind']} is missing namespace"


# ---------- extra_labels ----------

def test_extra_labels_in_pv_and_pvc():
    labels = {'env': 'prod', 'team': 'ops'}
    docs = _generate_docs(_make_generator(extra_labels=labels))
    for kind in ('PersistentVolume', 'PersistentVolumeClaim'):
        doc = next(d for d in docs if d['kind'] == kind)
        assert doc['metadata']['labels'] == labels


def test_extra_labels_in_ingress():
    labels = {'env': 'prod'}
    docs = _generate_docs(_make_generator(fqdns=['x.example.com'], extra_labels=labels))
    ingress = next(d for d in docs if d['kind'] == 'Ingress')
    assert ingress['metadata']['labels'] == labels


# ---------- no_tls ----------

def test_no_tls_ingress_has_web_entrypoint():
    docs = _generate_docs(_make_generator(fqdns=['x.example.com'], no_tls=True))
    ingress = next(d for d in docs if d['kind'] == 'Ingress')
    assert ingress['metadata']['annotations'][
        'traefik.ingress.kubernetes.io/router.entrypoints'
    ] == 'web'
    assert 'tls' not in ingress['spec']


# ---------- split mode ----------

def test_split_resource_profile():
    profile = {'requests': {'cpu': '100m', 'memory': '256Mi'}}
    docs = _generate_docs(_make_generator(fqdns=[], split=True, resource_profile=profile))
    for dep in (d for d in docs if d['kind'] == 'Deployment'):
        container = dep['spec']['template']['spec']['containers'][0]
        assert container['resources'] == profile


def test_split_env_secrets():
    docs = _generate_docs(_make_generator(fqdns=[], split=True, env_secrets=['my-secret']))
    for dep in (d for d in docs if d['kind'] == 'Deployment'):
        container = dep['spec']['template']['spec']['containers'][0]
        assert container['envFrom'] == [{'secretRef': {'name': 'my-secret'}}]


def test_split_secret_name():
    docs = _generate_docs(_make_generator(fqdns=[], split=True, secret_name='registry-secret'))
    for dep in (d for d in docs if d['kind'] == 'Deployment'):
        assert dep['spec']['template']['spec']['imagePullSecrets'] == [{'name': 'registry-secret'}]


# ---------- monolithic mode ----------

def test_monolithic_resource_profile():
    profile = {'requests': {'cpu': '200m'}}
    docs = _generate_docs(_make_generator(fqdns=[], resource_profile=profile))
    dep = next(d for d in docs if d['kind'] == 'Deployment')
    assert dep['spec']['template']['spec']['containers'][0]['resources'] == profile


def test_monolithic_env_secrets():
    docs = _generate_docs(_make_generator(fqdns=[], env_secrets=['db-secret']))
    dep = next(d for d in docs if d['kind'] == 'Deployment')
    assert dep['spec']['template']['spec']['containers'][0]['envFrom'] == [
        {'secretRef': {'name': 'db-secret'}}
    ]


def test_monolithic_secret_name():
    docs = _generate_docs(_make_generator(fqdns=[], secret_name='registry-secret'))
    dep = next(d for d in docs if d['kind'] == 'Deployment')
    assert dep['spec']['template']['spec']['imagePullSecrets'] == [{'name': 'registry-secret'}]
