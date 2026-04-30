import yaml


_KINDS = ('mapping', 'sequence')


class GnrYamlNode(object):

    def __init__(self, kind='mapping'):
        if kind not in _KINDS:
            raise ValueError(f"invalid kind: {kind!r}")
        self._kind = kind
        self._data = {} if kind == 'mapping' else []

    def child(self, key=None, kind='mapping'):
        node = GnrYamlNode(kind=kind)
        if self._kind == 'mapping':
            if key is None:
                raise TypeError("child() on mapping requires key")
            self._data[key] = node
        else:
            if key is not None:
                raise TypeError("child() on sequence does not accept key")
            self._data.append(node)
        return node

    def set(self, key, value):
        if self._kind != 'mapping':
            raise TypeError("set() not allowed on sequence node")
        self._data[key] = value
        return self

    def append(self, value):
        if self._kind != 'sequence':
            raise TypeError("append() not allowed on mapping node")
        self._data.append(value)
        return self

    def to_python(self):
        if self._kind == 'mapping':
            return {k: v.to_python() if isinstance(v, GnrYamlNode) else v
                    for k, v in self._data.items()}
        return [v.to_python() if isinstance(v, GnrYamlNode) else v
                for v in self._data]


class GnrYamlBuilder(GnrYamlNode):

    def toYaml(self, **dump_kwargs):
        opts = dict(sort_keys=False, default_flow_style=False, allow_unicode=True)
        opts.update(dump_kwargs)
        return yaml.safe_dump(self.to_python(), **opts)
