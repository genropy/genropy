import pytest
import yaml

from gnr.core.gnryaml import GnrYamlBuilder, GnrYamlNode


def test_mapping_scalars():
    b = GnrYamlBuilder()
    b.set('name', 'genro').set('version', 1)
    out = b.toYaml()
    assert yaml.safe_load(out) == {'name': 'genro', 'version': 1}


def test_sequence_scalars():
    b = GnrYamlBuilder(kind='sequence')
    b.append('a').append('b').append(3)
    assert yaml.safe_load(b.toYaml()) == ['a', 'b', 3]


def test_nested_mapping_in_sequence():
    b = GnrYamlBuilder()
    services = b.child('services')
    items = services.child('items', kind='sequence')
    item = items.child(kind='mapping')
    item.set('name', 'first')
    assert yaml.safe_load(b.toYaml()) == {
        'services': {'items': [{'name': 'first'}]}
    }


def test_nested_sequence_in_mapping():
    b = GnrYamlBuilder(kind='sequence')
    item = b.child(kind='mapping')
    tags = item.child('tags', kind='sequence')
    tags.append('x').append('y')
    assert yaml.safe_load(b.toYaml()) == [{'tags': ['x', 'y']}]


def test_set_on_sequence_raises():
    n = GnrYamlNode(kind='sequence')
    with pytest.raises(TypeError):
        n.set('k', 'v')


def test_append_on_mapping_raises():
    n = GnrYamlNode(kind='mapping')
    with pytest.raises(TypeError):
        n.append('v')


def test_child_invalid_kind():
    with pytest.raises(ValueError):
        GnrYamlNode(kind='scalar')


def test_child_missing_key_on_mapping():
    n = GnrYamlNode(kind='mapping')
    with pytest.raises(TypeError):
        n.child()


def test_child_with_key_on_sequence():
    n = GnrYamlNode(kind='sequence')
    with pytest.raises(TypeError):
        n.child(key='nope')


def test_dollar_var_literal():
    b = GnrYamlBuilder()
    val = '${GNR_DB_HOST:-myinstance_db}'
    b.set('host', val)
    raw = b.toYaml()
    assert val in raw
    assert yaml.safe_load(raw) == {'host': val}


def test_docker_compose_shape():
    b = GnrYamlBuilder()
    services = b.child('services')
    db = services.child('myinstance_db')
    db.set('image', 'postgres:latest')
    env = db.child('environment', kind='sequence')
    env.append('POSTGRES_PASSWORD=S3cret')
    env.append('POSTGRES_USER=genro')
    hc = db.child('healthcheck')
    hc.set('test', ['CMD-SHELL', 'pg_isready -U genro -d myinstance'])
    hc.set('interval', '10s')
    app = services.child('myinstance')
    app.set('image', 'myinstance:1.0')
    ports = app.child('ports', kind='sequence')
    ports.append('8888:8888')
    deps = app.child('depends_on')
    db_dep = deps.child('myinstance_db')
    db_dep.set('condition', 'service_healthy')

    parsed = yaml.safe_load(b.toYaml())
    assert parsed == {
        'services': {
            'myinstance_db': {
                'image': 'postgres:latest',
                'environment': [
                    'POSTGRES_PASSWORD=S3cret',
                    'POSTGRES_USER=genro',
                ],
                'healthcheck': {
                    'test': ['CMD-SHELL', 'pg_isready -U genro -d myinstance'],
                    'interval': '10s',
                },
            },
            'myinstance': {
                'image': 'myinstance:1.0',
                'ports': ['8888:8888'],
                'depends_on': {
                    'myinstance_db': {'condition': 'service_healthy'},
                },
            },
        }
    }


def test_empty_mapping():
    b = GnrYamlBuilder()
    assert yaml.safe_load(b.toYaml()) == {}


def test_empty_sequence():
    b = GnrYamlBuilder(kind='sequence')
    assert yaml.safe_load(b.toYaml()) == []


def test_chainable_set_append():
    m = GnrYamlNode(kind='mapping')
    assert m.set('a', 1) is m
    s = GnrYamlNode(kind='sequence')
    assert s.append('x') is s


def test_explicit_start_opt_in():
    b = GnrYamlBuilder()
    b.set('k', 'v')
    out = b.toYaml(explicit_start=True)
    assert out.startswith('---\n')


def test_mapping_helper():
    b = GnrYamlBuilder()
    services = b.mapping('services')
    services.set('name', 'genro')
    assert yaml.safe_load(b.toYaml()) == {'services': {'name': 'genro'}}


def test_sequence_helper():
    b = GnrYamlBuilder()
    items = b.sequence('items')
    items.append('a').append('b')
    assert yaml.safe_load(b.toYaml()) == {'items': ['a', 'b']}


def test_mapping_sequence_inside_sequence():
    b = GnrYamlBuilder(kind='sequence')
    inner_map = b.mapping()
    inner_map.set('k', 'v')
    inner_seq = b.sequence()
    inner_seq.append(1).append(2)
    assert yaml.safe_load(b.toYaml()) == [{'k': 'v'}, [1, 2]]
