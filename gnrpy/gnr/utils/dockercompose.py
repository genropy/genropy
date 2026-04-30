from gnr.core.gnryaml import GnrYamlBuilder


class DockerComposeBuilder(GnrYamlBuilder):
    """Domain builder for docker-compose YAML documents.

    Layers domain-aware methods on top of GnrYamlBuilder, modelling the
    five top-level sections of a compose document as first-class
    citizens: services, volumes, networks, configs, secrets.

    Each section has a getter (``services()``, ``volumes()``, ...) that
    returns the section's mapping node and an adder
    (``service(name, ...)``, ``volume(name)``, ...) that declares an
    item inside it. Sections are created lazily on first use, so an
    unused builder produces no spurious empty sections."""

    def __init__(self, kind='mapping'):
        super().__init__(kind=kind)
        self._services_node = None
        self._volumes_node = None
        self._networks_node = None
        self._configs_node = None
        self._secrets_node = None

    # ------------------------------------------------------------------
    # Top-level sections (first-class citizens of a compose document)
    # ------------------------------------------------------------------

    def services(self):
        """The top-level ``services`` mapping."""
        if self._services_node is None:
            self._services_node = self.mapping('services')
        return self._services_node

    def volumes(self):
        """The top-level ``volumes`` mapping."""
        if self._volumes_node is None:
            self._volumes_node = self.mapping('volumes')
        return self._volumes_node

    def networks(self):
        """The top-level ``networks`` mapping."""
        if self._networks_node is None:
            self._networks_node = self.mapping('networks')
        return self._networks_node

    def configs(self):
        """The top-level ``configs`` mapping."""
        if self._configs_node is None:
            self._configs_node = self.mapping('configs')
        return self._configs_node

    def secrets(self):
        """The top-level ``secrets`` mapping."""
        if self._secrets_node is None:
            self._secrets_node = self.mapping('secrets')
        return self._secrets_node

    # ------------------------------------------------------------------
    # Adders (declare one item inside a top-level section)
    # ------------------------------------------------------------------

    def volume(self, name):
        """Declare a named volume. Returns the volume mapping node."""
        return self.volumes().mapping(name)

    def network(self, name):
        """Declare a network. Returns the network mapping node."""
        return self.networks().mapping(name)

    def config(self, name):
        """Declare a config. Returns the config mapping node."""
        return self.configs().mapping(name)

    def secret(self, name):
        """Declare a secret. Returns the secret mapping node."""
        return self.secrets().mapping(name)

    def service(self, name, image, version_tag=None, *,
                environment=None, ports=None, depends_on=None,
                labels=None, volumes=None, healthcheck=None):
        """Declare a service. Returns the service node for further config.

        Common sections accepted as kwargs; for less common keys, mutate
        the returned service node directly via the inherited builder
        primitives (``set``, ``mapping``, ``sequence``)."""
        srv = self.services().mapping(name)
        srv.set('image', f'{image}:{version_tag}' if version_tag else image)
        if labels:
            self._fill_mapping(srv.mapping('labels'), labels)
        if ports:
            self._fill_sequence(srv.sequence('ports'), ports)
        if depends_on:
            self._fill_mapping(srv.mapping('depends_on'), depends_on)
        if environment:
            self._fill_mapping(srv.mapping('environment'), environment)
        if volumes:
            self._fill_sequence(srv.sequence('volumes'), volumes)
        if healthcheck:
            self._fill_mapping(srv.mapping('healthcheck'), healthcheck)
        return srv

    @staticmethod
    def _fill_mapping(node, items):
        for k, v in items.items():
            node.set(k, v)

    @staticmethod
    def _fill_sequence(node, items):
        for v in items:
            node.append(v)
