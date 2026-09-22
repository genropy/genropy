import base64
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock

from gnr.app import logger

NPM_REGISTRY = 'https://registry.npmjs.org'

# Exact version of esbuild to download and run. Pinned deliberately: esbuild
# is executed as a binary on the build machine, so an unpinned 'latest' would
# let a future upstream release run unreviewed. Bump this by hand.
_ESBUILD_VERSION = '0.28.2'

# Maps (system, machine) -> (npm-package-name, path-to-binary-inside-tarball)
_ESBUILD_PACKAGES = {
    ('linux', 'x86_64'):  ('@esbuild/linux-x64',   'package/bin/esbuild'),
    ('linux', 'aarch64'): ('@esbuild/linux-arm64',  'package/bin/esbuild'),
    ('linux', 'armv7l'):  ('@esbuild/linux-arm',    'package/bin/esbuild'),
    ('darwin', 'x86_64'): ('@esbuild/darwin-x64',   'package/bin/esbuild'),
    ('darwin', 'arm64'):  ('@esbuild/darwin-arm64',  'package/bin/esbuild'),
    ('windows', 'amd64'): ('@esbuild/win32-x64',    'package/esbuild.exe'),
}

# An alias becomes both a filesystem entry (<alias>.js) and a JS binding
# name (export * as <alias> from ...), so it must be a plain identifier:
# no path separators, no quotes, nothing that needs escaping either way.
_ALIAS_RE = re.compile(r'^[A-Za-z_$][A-Za-z0-9_$]*$')

# Reserved because they collide with fixed output filenames written by bundle().
_RESERVED_ALIASES = {'gnr_ext_bundle', 'manifest', 'dependencies'}

_LICENSE_PREFIXES = ('license', 'licence')

# A package name flows into a filesystem path (node_modules/<name>), an npm
# registry URL, and a JS string literal. This mirrors npm's own naming rules
# (letters, digits, '.', '_', '-', at most one leading '@scope/') and rejects
# everything else up front, rather than trying to escape arbitrary text at
# each of those use sites individually.
_PKG_NAME_RE = re.compile(r'^(?:@[A-Za-z0-9][\w.-]*/)?[A-Za-z0-9][\w.-]*$')


def _npm_url(name, version=None):
    encoded = urllib.parse.quote(name, safe='')
    base = f'{NPM_REGISTRY}/{encoded}'
    return f'{base}/{version}' if version else base


def _safe_pkg_name(name):
    """Convert npm package name to a filesystem-safe string."""
    return name.lstrip('@').replace('/', '__')


def _default_alias(name):
    """Derive a default alias from an npm package name: must be a valid JS
    identifier since it is used as `export * as <alias> from ...`, so
    characters npm allows but JS doesn't (like '-') are folded to '_'."""
    base = re.sub(r'[^A-Za-z0-9_$]', '_', _safe_pkg_name(name))
    if not base or base[0].isdigit():
        base = '_' + base
    return base


def _validate_alias(alias):
    """Raise ValueError unless alias is safe to use as both a filename and a JS binding."""
    if not _ALIAS_RE.match(alias):
        raise ValueError(
            f'Invalid alias {alias!r}: must be a plain identifier '
            '(letters, digits, "_", "$", not starting with a digit)'
        )
    if alias in _RESERVED_ALIASES:
        raise ValueError(f'Alias {alias!r} is reserved for internal build output')


def _validate_pkg_name(name):
    """Raise ValueError unless name is safe to use as a path segment, a
    registry URL component, and a JS string literal."""
    if not _PKG_NAME_RE.match(name):
        raise ValueError(f'Invalid npm package name {name!r}')


def _semver_tuple(version_str):
    """Parse '18.2.0' -> (18, 2, 0). Returns None if unparseable."""
    base = re.split(r'[-+]', version_str)[0]
    parts = base.split('.')
    try:
        return tuple(int(p) for p in parts[:3])
    except ValueError:
        return None


class EsmBuilder:
    """Download npm packages and bundle them as ESM modules using esbuild."""

    _MANIFEST = 'manifest.json'
    _DEPENDENCIES_FILE = 'dependencies.json'
    _ATTRIBUTION_FILE = 'THIRD-PARTY-LICENSES.txt'
    _BUNDLE_FILE = 'gnr_ext_bundle.js'

    def __init__(self, cache_dir=None, verbose=False):
        self.verbose = verbose
        self.cache_dir = cache_dir or os.path.join(
            os.path.expanduser('~'), '.gnr', 'esm_cache'
        )
        os.makedirs(self.cache_dir, exist_ok=True)
        self._esbuild = None

    def _log(self, msg):
        logger.debug(msg)

    def _fetch_json(self, url):
        self._log(f'Fetching: {url}')
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise RuntimeError(f'npm package not found: {url}') from e
            raise

    def _download(self, url, dest, dist):
        """Download url to dest and verify it against npm's dist.integrity/shasum."""
        self._log(f'Downloading: {url}')
        urllib.request.urlretrieve(url, dest)
        self._verify_integrity(dest, dist)

    def _verify_integrity(self, path, dist):
        integrity = (dist or {}).get('integrity')
        if integrity:
            algo, _, b64digest = integrity.partition('-')
            algo = algo.lower()
            if algo not in ('sha512', 'sha384', 'sha256'):
                raise RuntimeError(f'Unsupported integrity algorithm {algo!r} for {path}')
            digest = hashlib.new(algo)
            expected = base64.b64decode(b64digest)
        else:
            shasum = (dist or {}).get('shasum')
            if not shasum:
                raise RuntimeError(f'No integrity metadata available to verify {path}')
            digest = hashlib.sha1()
            expected = bytes.fromhex(shasum)

        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 16), b''):
                digest.update(chunk)

        if digest.digest() != expected:
            raise RuntimeError(f'Integrity check failed for {path}: {digest.name} mismatch')

    def _extractall(self, tf, dest):
        """Extract tf into dest, rejecting members that would land outside dest
        or that are symlinks/hardlinks (matches tarfile's 'data' filter)."""
        data_filter = getattr(tarfile, 'data_filter', None)
        if data_filter is not None:
            tf.extractall(dest, filter=data_filter)
            return
        self._extractall_manual_filter(tf, dest)

    def _extractall_manual_filter(self, tf, dest):
        """Same safety guarantee as _extractall's 'data' filter, applied by
        hand for interpreters old enough to lack tarfile's filter support
        entirely (so the trailing extractall() call below must not pass a
        filter= argument: that parameter doesn't exist there)."""
        abs_dest = os.path.abspath(dest)
        for member in tf.getmembers():
            if member.issym() or member.islnk():
                raise RuntimeError(f'Refusing to extract link member: {member.name}')
            member_path = os.path.abspath(os.path.join(abs_dest, member.name))
            if member_path != abs_dest and not member_path.startswith(abs_dest + os.sep):
                raise RuntimeError(f'Refusing to extract member outside destination: {member.name}')
        tf.extractall(dest)

    def get_esbuild(self):
        """Return path to esbuild binary, downloading it from npm if needed."""
        if self._esbuild and os.path.isfile(self._esbuild):
            return self._esbuild

        bin_name = 'esbuild.exe' if sys.platform == 'win32' else 'esbuild'
        cached = os.path.join(self.cache_dir, bin_name)
        if os.path.isfile(cached) and os.access(cached, os.X_OK):
            self._esbuild = cached
            return cached

        system = platform.system().lower()
        machine = platform.machine()
        key = (system, machine)
        if key not in _ESBUILD_PACKAGES:
            raise RuntimeError(f'esbuild not available for platform {system}/{machine}')

        pkg_name, inner_path = _ESBUILD_PACKAGES[key]
        logger.info(f'Downloading esbuild {_ESBUILD_VERSION} for {system}/{machine}...')
        meta = self._fetch_json(_npm_url(pkg_name, _ESBUILD_VERSION))
        dist = meta['dist']
        tarball_url = dist['tarball']

        tmp_tgz = os.path.join(self.cache_dir, '_esbuild_pkg.tgz')
        self._download(tarball_url, tmp_tgz, dist)

        with tarfile.open(tmp_tgz, 'r:gz') as tf:
            found = None
            for member in tf.getmembers():
                if member.name == inner_path:
                    found = member
                    break
            if not found:
                raise RuntimeError(f'Binary not found at {inner_path} in esbuild package')
            if not found.isfile():
                raise RuntimeError(f'{inner_path} in esbuild package is not a regular file')
            src = tf.extractfile(found)
            with open(cached, 'wb') as dst:
                dst.write(src.read())

        os.chmod(cached, 0o755)
        self._esbuild = cached
        return cached

    def parse_requirements(self, filepath):
        """Parse esm_requirements.txt and return list of (alias, spec) tuples.

        Supported formats per line:
            alias=package@version   ->  ('alias', 'package@version')
            package@version         ->  ('package', 'package@version')
            package                 ->  ('package', 'package')
        Lines starting with '#' are ignored.
        """
        items = []
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '==' in line:
                    # pip-style: package==version  (alias = safe package name)
                    pkg, version = line.split('==', 1)
                    pkg = pkg.strip()
                    name, _ = self._parse_spec(pkg)
                    alias = _default_alias(name)
                    items.append((alias, f'{pkg}@{version.strip()}'))
                elif '=' in line:
                    # alias=package@version
                    alias, spec = line.split('=', 1)
                    alias = alias.strip()
                    items.append((alias, spec.strip()))
                else:
                    name, _ = self._parse_spec(line)
                    alias = _default_alias(name)
                    items.append((alias, line))
                _validate_alias(items[-1][0])
        return items

    def _parse_spec(self, spec):
        """Parse 'name@version' into (name, version). Handles scoped packages.

        This is the single chokepoint every spec string passes through
        (declared requirements, transitive dependencies read back from a
        downloaded package.json), so the name is validated here: it later
        becomes a filesystem path segment, a registry URL component, and a
        JS string literal.
        """
        if spec.startswith('@'):
            rest = spec[1:]
            if '@' in rest:
                pkg, version = rest.rsplit('@', 1)
                name = '@' + pkg
            else:
                name, version = spec, 'latest'
        elif '@' in spec:
            name, version = spec.split('@', 1)
        else:
            name, version = spec, 'latest'
        _validate_pkg_name(name)
        return name, version

    def _needs_resolution(self, version):
        """Return True when version is a semver range rather than an exact version or dist-tag."""
        if re.match(r'^\d+\.\d+\.\d+', version):
            return False  # exact: 18.2.0 or 18.2.0-rc.0
        if re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', version):
            return False  # dist-tag: latest, next, beta
        return True  # partial or range: 18, ^18.0.0, ~18.2, >=18

    def _resolve_version(self, name, spec):
        """Resolve a partial/range version spec to an exact version string.

        Fetches the full package manifest from the npm registry and picks the
        highest stable version that satisfies the spec.  Operator semantics
        follow node-semver:
          ^major.minor.patch -> >=major.minor.patch, <(major+1).0.0
                                 (or narrower once major is 0, per semver)
          ~major.minor.patch -> >=major.minor.patch, <major.(minor+1).0
          >=, >, <=, <, =     -> ordinary numeric comparison
          bare digits         -> lock as many parts as given (18 -> major=18)
        """
        logger.info(f'Resolving {spec!r} for {name}')
        meta = self._fetch_json(_npm_url(name))

        dist_tags = meta.get('dist-tags', {})
        if spec in dist_tags:
            return dist_tags[spec]

        # Stable versions only (skip pre-releases like 18.0.0-rc.3)
        versions = [v for v in meta.get('versions', {})
                    if '-' not in v.split('+')[0]]

        m = re.match(r'^(\^|~|>=|<=|>|<|=)?\s*(.*)$', spec)
        op = m.group(1) or ''
        clean = m.group(2)

        nums = _semver_tuple(clean)
        if nums is None or not nums:
            raise RuntimeError(f'Unparseable version spec {spec!r} for {name}')

        floor = nums + (0,) * (3 - len(nums))

        def _bump(t, index):
            return tuple(list(t[:index]) + [t[index] + 1] + [0] * (2 - index))

        if op == '^':
            if floor[0] > 0:
                ceiling = _bump(floor, 0)
            elif floor[1] > 0:
                ceiling = _bump(floor, 1)
            else:
                ceiling = _bump(floor, 2)
            satisfies = lambda t: floor <= t < ceiling  # noqa: E731
        elif op == '~':
            ceiling = _bump(floor, 1) if len(nums) >= 2 else _bump(floor, 0)
            satisfies = lambda t: floor <= t < ceiling  # noqa: E731
        elif op == '>=':
            satisfies = lambda t: t >= floor  # noqa: E731
        elif op == '>':
            satisfies = lambda t: t > floor  # noqa: E731
        elif op == '<=':
            satisfies = lambda t: t <= floor  # noqa: E731
        elif op == '<':
            satisfies = lambda t: t < floor  # noqa: E731
        elif op == '=':
            satisfies = lambda t: t == floor  # noqa: E731
        else:
            # bare X-range: lock exactly the components given (18 -> major=18)
            satisfies = lambda t: t[:len(nums)] == nums  # noqa: E731

        matching = [v for v in versions
                    if (_semver_tuple(v) is not None and satisfies(_semver_tuple(v)))]
        if not matching:
            raise RuntimeError(f'No stable version matching {spec!r} found for {name}')

        return max(matching, key=lambda v: _semver_tuple(v) or (0, 0, 0))

    def download_package(self, spec, force=False):
        """Download and extract an npm package tarball.

        Returns (pkg_dir, name, resolved_version).
        """
        name, version = self._parse_spec(spec)

        if self._needs_resolution(version):
            version = self._resolve_version(name, version)

        safe = _safe_pkg_name(name)
        pkg_dir = os.path.join(self.cache_dir, 'packages', f'{safe}@{version}')

        if not force and self._cache_valid(pkg_dir):
            logger.debug(f'Using cached: {name}@{version}')
            return pkg_dir, name, version

        logger.info(f'Downloading: {name}@{version}')
        meta = self._fetch_json(_npm_url(name, version))
        actual_version = meta['version']
        dist = meta['dist']
        tarball_url = dist['tarball']

        actual_dir = os.path.join(self.cache_dir, 'packages', f'{safe}@{actual_version}')
        if not force and self._cache_valid(actual_dir):
            logger.debug(f'Using cached: {name}@{actual_version}')
            return actual_dir, name, actual_version

        tgz_path = actual_dir + '.tgz'
        os.makedirs(os.path.dirname(tgz_path), exist_ok=True)
        self._download(tarball_url, tgz_path, dist)

        # Remove any stale partial extraction before re-extracting
        if os.path.isdir(actual_dir):
            shutil.rmtree(actual_dir)
        os.makedirs(actual_dir)
        with tarfile.open(tgz_path, 'r:gz') as tf:
            self._extractall(tf, actual_dir)

        return actual_dir, name, actual_version

    def _cache_valid(self, pkg_dir):
        """Return True only when the cache directory contains a complete extraction."""
        return os.path.isfile(os.path.join(pkg_dir, 'package', 'package.json'))

    def _symlink_package(self, node_modules_dir, pkg_dir, name):
        """Symlink a package's extracted directory into a node_modules tree."""
        pkg_src = os.path.abspath(os.path.join(pkg_dir, 'package'))
        if name.startswith('@'):
            scope, pkg = name.split('/', 1)
            scope_dir = os.path.join(node_modules_dir, scope)
            os.makedirs(scope_dir, exist_ok=True)
            link_path = os.path.join(scope_dir, pkg)
        else:
            link_path = os.path.join(node_modules_dir, name)

        if os.path.islink(link_path):
            if os.path.realpath(link_path) == pkg_src:
                return
            os.unlink(link_path)

        if not os.path.exists(link_path):
            os.symlink(pkg_src, link_path)

    def _download_all(self, specs, force=False, max_workers=8):
        """Download all packages and their transitive dependencies in parallel.

        Returns {name: (pkg_dir, version)} for every package in the full tree.
        """
        downloaded = {}  # name -> (pkg_dir, version) | None (in-progress)
        lock = Lock()
        idle = Event()
        pending = [0]
        errors = []

        executor = ThreadPoolExecutor(max_workers=max_workers)

        def submit_if_new(spec):
            name, _ = self._parse_spec(spec)
            with lock:
                if name in downloaded:
                    return
                downloaded[name] = None
                pending[0] += 1
            executor.submit(do_download, spec)

        def do_download(spec):
            name, _ = self._parse_spec(spec)
            try:
                pkg_dir, name, version = self.download_package(spec, force=force)

                pkg_json_path = os.path.join(pkg_dir, 'package', 'package.json')
                with open(pkg_json_path) as f:
                    pkg_json = json.load(f)

                optional_peers = {
                    k for k, v in pkg_json.get('peerDependenciesMeta', {}).items()
                    if v.get('optional')
                }
                all_deps = {}
                for dep_name, dep_spec in pkg_json.get('dependencies', {}).items():
                    if not dep_name.startswith('@types/'):
                        all_deps[dep_name] = dep_spec
                for dep_name, dep_spec in pkg_json.get('peerDependencies', {}).items():
                    if dep_name.startswith('@types/') or dep_name in optional_peers:
                        continue
                    all_deps[dep_name] = dep_spec

                with lock:
                    downloaded[name] = (pkg_dir, version)

                for dep_name, dep_spec in all_deps.items():
                    submit_if_new(f'{dep_name}@{dep_spec}')

            except Exception as e:
                with lock:
                    errors.append((name, e))
                    downloaded[name] = (None, None)
            finally:
                with lock:
                    pending[0] -= 1
                    if pending[0] == 0:
                        idle.set()

        # Sentinel prevents idle firing before all initial specs are submitted
        with lock:
            pending[0] = 1

        try:
            for spec in specs:
                submit_if_new(spec)
        except Exception as e:
            # e.g. an invalid package name in one of the top-level specs:
            # record it like any other download failure so already-submitted
            # background downloads still get drained and the executor still
            # gets shut down below, instead of leaking its threads.
            with lock:
                errors.append((None, e))

        with lock:
            pending[0] -= 1
            if pending[0] == 0:
                idle.set()

        idle.wait()
        executor.shutdown(wait=True)

        if errors:
            _name, exc = errors[0]
            raise exc

        return downloaded

    def _load_manifest(self, output_dir):
        path = os.path.join(output_dir, self._MANIFEST)
        if not os.path.isfile(path):
            return None
        with open(path) as f:
            return json.load(f)

    def _save_manifest(self, output_dir, items, results):
        spec_map = {alias: spec for alias, spec in items}
        manifest = {
            alias: {
                'spec': spec_map[alias],
                'name': name,
                'version': version,
                'file': os.path.basename(out_file),
            }
            for alias, name, version, out_file in results
        }
        with open(os.path.join(output_dir, self._MANIFEST), 'w') as f:
            json.dump(manifest, f, indent=2)

    def _load_dependencies(self, output_dir):
        path = os.path.join(output_dir, self._DEPENDENCIES_FILE)
        if not os.path.isfile(path):
            return {}
        with open(path) as f:
            return json.load(f)

    def _save_dependencies(self, output_dir, downloaded):
        deps = {name: version for name, (pkg_dir, version) in downloaded.items() if pkg_dir}
        with open(os.path.join(output_dir, self._DEPENDENCIES_FILE), 'w') as f:
            json.dump(deps, f, indent=2, sort_keys=True)

    def load_lock(self, lock_path):
        """Read a package-level esm_requirements.lock file, or None if absent/unreadable."""
        if not os.path.isfile(lock_path):
            return None
        try:
            with open(lock_path) as f:
                return json.load(f)
        except (OSError, ValueError):
            logger.warning(f'Ignoring unreadable lock file: {lock_path}')
            return None

    def save_lock(self, lock_path, aliases_items, dependencies):
        """Write a package-level lock file if its content actually changed.

        aliases_items: list of (alias, name, spec, version) for the aliases
        that package declares. dependencies: {name: version} for every
        package resolved in the build that produced these aliases.
        """
        lock = {
            'aliases': {
                alias: {'spec': spec, 'name': name, 'version': version}
                for alias, name, spec, version in aliases_items
            },
            'dependencies': dict(sorted(dependencies.items())),
        }
        if self.load_lock(lock_path) == lock:
            return
        with open(lock_path, 'w') as f:
            json.dump(lock, f, indent=2, sort_keys=True)
            f.write('\n')

    def _package_license_id(self, pkg_dir):
        pkg_json_path = os.path.join(pkg_dir, 'package', 'package.json')
        try:
            with open(pkg_json_path) as f:
                pkg_json = json.load(f)
        except (OSError, ValueError):
            return None
        license_field = pkg_json.get('license')
        if isinstance(license_field, str):
            return license_field
        if isinstance(license_field, dict):
            return license_field.get('type')
        licenses = pkg_json.get('licenses')
        if isinstance(licenses, list) and licenses:
            names = [lic.get('type') for lic in licenses if isinstance(lic, dict) and lic.get('type')]
            if names:
                return ', '.join(names)
        return None

    def _package_license_text(self, pkg_dir):
        pkg_root = os.path.join(pkg_dir, 'package')
        if not os.path.isdir(pkg_root):
            return None
        for fname in sorted(os.listdir(pkg_root)):
            if fname.lower().split('.')[0] in _LICENSE_PREFIXES:
                path = os.path.join(pkg_root, fname)
                if os.path.isfile(path):
                    with open(path, encoding='utf-8', errors='replace') as f:
                        return f.read()
        return None

    def _write_attribution(self, output_dir, downloaded):
        """Write a THIRD-PARTY-LICENSES.txt covering every bundled npm package."""
        lines = [
            'Third-party JavaScript packages bundled into this instance.',
            'Generated automatically by EsmBuilder; do not edit by hand.',
            '',
        ]
        for name in sorted(downloaded):
            pkg_dir, version = downloaded[name]
            if not pkg_dir:
                continue
            license_id = self._package_license_id(pkg_dir) or 'UNKNOWN'
            header = f'{name}@{version} — {license_id}'
            lines.append('=' * len(header))
            lines.append(header)
            lines.append('=' * len(header))
            text = self._package_license_text(pkg_dir)
            lines.append(text.strip() if text else '(license text not included in package)')
            lines.append('')
        with open(os.path.join(output_dir, self._ATTRIBUTION_FILE), 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def _is_up_to_date(self, items, output_dir):
        """Return True when the manifest matches current specs and all output files exist."""
        manifest = self._load_manifest(output_dir)
        if manifest is None:
            return False

        current = {alias: spec for alias, spec in items}
        if set(manifest.keys()) != set(current.keys()):
            return False
        if any(manifest[a]['spec'] != s for a, s in current.items()):
            return False

        required = [self._BUNDLE_FILE, self._DEPENDENCIES_FILE, self._ATTRIBUTION_FILE]
        required += [manifest[a]['file'] for a in manifest]
        return all(os.path.isfile(os.path.join(output_dir, f)) for f in required)

    def _results_from_manifest(self, items, output_dir):
        manifest = self._load_manifest(output_dir)
        return [
            (alias, manifest[alias]['name'], manifest[alias]['version'],
             os.path.join(output_dir, manifest[alias]['file']))
            for alias, _ in items
        ]

    def bundle(self, items, output_dir, force=False, locked=None):
        """Download and bundle packages with esbuild into output_dir.

        items: list of (alias, spec) tuples as returned by parse_requirements().
        locked: optional {alias: 'name@exact_version'} overriding the spec used
            to actually resolve/download a given alias (e.g. from a lock file),
            while `items` keeps identifying cache validity by the declared spec.

        Always produces:
          - <alias>.js per package (others marked --external to avoid duplication)
          - gnr_ext_bundle.js with every package as a namespaced export
          - dependencies.json with the full resolved dependency tree
          - THIRD-PARTY-LICENSES.txt with license info for every bundled package

        Returns list of (alias, name, version, output_file) tuples for the
        per-package files.
        """
        for alias, _spec in items:
            _validate_alias(alias)
        locked = locked or {}

        if not force and self._is_up_to_date(items, output_dir):
            logger.info('All packages already up to date.')
            return self._results_from_manifest(items, output_dir)

        esbuild = self.get_esbuild()
        os.makedirs(output_dir, exist_ok=True)

        # Temporary workspace: esbuild finds node_modules via standard Node
        # resolution (searching parent directories from the entry file).
        with tempfile.TemporaryDirectory() as workspace:
            node_modules_dir = os.path.join(workspace, 'node_modules')
            os.makedirs(node_modules_dir)

            downloaded = self._download_all(
                [locked.get(alias, spec) for alias, spec in items], force=force
            )
            for name, info in downloaded.items():
                if info and info[0]:
                    self._symlink_package(node_modules_dir, info[0], name)

            top_level = []
            for alias, spec in items:
                name, _ = self._parse_spec(locked.get(alias, spec))
                pkg_dir, version = downloaded[name]
                top_level.append((alias, name, version))

            results = self._bundle_separate(esbuild, workspace, top_level, output_dir)
            self._bundle_single(esbuild, workspace, top_level, output_dir)

            self._save_dependencies(output_dir, downloaded)
            self._write_attribution(output_dir, downloaded)

        self._save_manifest(output_dir, items, results)
        return results

    def _esbuild_run(self, cmd, workspace, label):
        """Run an esbuild command and raise on failure."""
        logger.debug(f'Running: {" ".join(cmd)}')
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=workspace)
        if result.returncode != 0:
            raise RuntimeError(f'esbuild failed for {label}:\n{result.stderr}')

    def _bundle_separate(self, esbuild, workspace, top_level, output_dir):
        """One ESM file per package; peer packages are --external."""
        listed_names = {name for _, name, _ in top_level}
        results = []

        for alias, name, version in top_level:
            externals = listed_names - {name}

            entry_file = os.path.join(workspace, f'__{alias}.js')
            with open(entry_file, 'w') as ef:
                ef.write(f'export * from {json.dumps(name)};\n')

            out_file = os.path.join(output_dir, alias + '.js')
            cmd = [
                esbuild, entry_file,
                '--bundle', '--format=esm', '--platform=browser',
                '--preserve-symlinks', f'--outfile={out_file}',
            ]
            for ext in externals:
                cmd.append(f'--external:{ext}')

            self._esbuild_run(cmd, workspace, f'{name}@{version}')
            logger.info(f'Bundled: {alias} ({name}@{version}) -> {out_file}')
            results.append((alias, name, version, out_file))

        return results

    def _bundle_single(self, esbuild, workspace, top_level, output_dir):
        """Single gnr_ext_bundle.js with each package as a namespaced export."""
        entry_file = os.path.join(workspace, '__bundle.js')
        with open(entry_file, 'w') as ef:
            for alias, name, _version in top_level:
                ef.write(f'export * as {alias} from {json.dumps(name)};\n')

        out_file = os.path.join(output_dir, self._BUNDLE_FILE)
        cmd = [
            esbuild, entry_file,
            '--bundle', '--format=esm', '--platform=browser',
            '--preserve-symlinks', f'--outfile={out_file}',
        ]
        self._esbuild_run(cmd, workspace, 'bundle')

        results = []
        for alias, name, version in top_level:
            logger.info(f'  {alias} ({name}@{version})')
            results.append((alias, name, version, out_file))
        logger.info(f'Bundled all packages -> {out_file}')
        return results


class GnrInstanceEsmBundler:
    """Collect ESM requirements from a Genropy instance and bundle them.

    Wraps EsmBuilder with GnrApp awareness: package discovery, output
    directory resolution, requirement deduplication across packages, and
    per-package lock files (esm_requirements.lock, sitting next to
    esm_requirements.txt) so repeated builds resolve the same exact
    versions instead of re-resolving semver ranges against npm each time.
    """

    _LOCK_FILENAME = 'esm_requirements.lock'

    def __init__(self, app, verbose=False):
        self.app = app
        self.builder = EsmBuilder(verbose=verbose)
        self._package_locks = {}

    def collect_requirements(self):
        """Return {alias: {'spec': str, 'effective_spec': str, 'packages': [str]}}
        from all instance packages, substituting locked exact versions where
        a package's lock file is present and still matches its declared spec.
        """
        all_items = {}
        self._package_locks = {}
        for package, _pkgattrs, _pkgcontent in self.app.config['packages'].digest('#k,#a,#v'):
            if ':' in package:
                project, package = package.split(':')
            else:
                project = None
            package_folder = self.app.pkg_path_from_attrs(package, _pkgattrs, project)
            pkg_dir = os.path.join(package_folder, package)
            esm_req = os.path.join(pkg_dir, 'esm_requirements.txt')
            if not os.path.isfile(esm_req):
                continue

            lock_path = os.path.join(pkg_dir, self._LOCK_FILENAME)
            lock = self.builder.load_lock(lock_path)
            self._package_locks[package] = lock_path

            for alias, spec in self.builder.parse_requirements(esm_req):
                if alias in all_items and all_items[alias]['spec'] != spec:
                    raise RuntimeError(
                        f"Conflicting esm_requirements for alias '{alias}': "
                        f"{all_items[alias]['spec']!r} (from "
                        f"{', '.join(all_items[alias]['packages'])}) vs "
                        f"{spec!r} (from {package})"
                    )
                if alias not in all_items:
                    locked = (lock or {}).get('aliases', {}).get(alias)
                    effective_spec = spec
                    if locked and locked.get('spec') == spec and locked.get('version'):
                        effective_spec = f"{locked['name']}@{locked['version']}"
                    all_items[alias] = {
                        'spec': spec,
                        'effective_spec': effective_spec,
                        'packages': [],
                    }
                all_items[alias]['packages'].append(package)
        return all_items

    def resolve_output_dir(self, output=None):
        """Return the output directory: explicit override, site _static, or instance fallback."""
        if output:
            return output
        try:
            site_path = self.app.path_resolver.site_name_to_path(self.app.instanceName)
            return os.path.join(site_path, 'resources', 'esm')
        except Exception:
            return os.path.join(self.app.instanceFolder, 'esm_bundles')

    def _update_package_locks(self, all_items, results, dependencies):
        resolved = {alias: (name, version) for alias, name, version, _file in results}
        for package, lock_path in self._package_locks.items():
            aliases_items = []
            for alias, info in all_items.items():
                if package not in info['packages']:
                    continue
                name, version = resolved.get(alias, (None, None))
                if name is None:
                    continue
                aliases_items.append((alias, name, info['spec'], version))
            if aliases_items:
                self.builder.save_lock(lock_path, aliases_items, dependencies)

    def run(self, force=False, output=None):
        """Collect requirements from all packages and bundle them.

        Returns (output_dir, results) or (None, None) if no requirements found.
        results is a list of (alias, name, version, output_file) tuples.
        """
        all_items = self.collect_requirements()
        if not all_items:
            return None, None

        for alias, info in all_items.items():
            logger.info(f'{alias}={info["spec"]}  (from: {", ".join(info["packages"])})')

        output_dir = self.resolve_output_dir(output)
        bundle_items = [(alias, info['spec']) for alias, info in all_items.items()]
        locked = {
            alias: info['effective_spec']
            for alias, info in all_items.items()
            if info['effective_spec'] != info['spec']
        }
        results = self.builder.bundle(bundle_items, output_dir, force=force, locked=locked)

        dependencies = self.builder._load_dependencies(output_dir)
        self._update_package_locks(all_items, results, dependencies)

        return output_dir, results
