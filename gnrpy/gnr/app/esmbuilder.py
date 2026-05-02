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
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock

from gnr.app import logger

NPM_REGISTRY = 'https://registry.npmjs.org'

# Maps (system, machine) -> (npm-package-name, path-to-binary-inside-tarball)
_ESBUILD_PACKAGES = {
    ('linux', 'x86_64'):  ('@esbuild/linux-x64',   'package/bin/esbuild'),
    ('linux', 'aarch64'): ('@esbuild/linux-arm64',  'package/bin/esbuild'),
    ('linux', 'armv7l'):  ('@esbuild/linux-arm',    'package/bin/esbuild'),
    ('darwin', 'x86_64'): ('@esbuild/darwin-x64',   'package/bin/esbuild'),
    ('darwin', 'arm64'):  ('@esbuild/darwin-arm64',  'package/bin/esbuild'),
    ('windows', 'amd64'): ('@esbuild/win32-x64',    'package/esbuild.exe'),
}


def _npm_url(name, version=None):
    encoded = urllib.parse.quote(name, safe='')
    base = f'{NPM_REGISTRY}/{encoded}'
    return f'{base}/{version}' if version else base


def _safe_pkg_name(name):
    """Convert npm package name to a filesystem-safe string."""
    return name.lstrip('@').replace('/', '__')


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

    def _download(self, url, dest):
        self._log(f'Downloading: {url}')
        urllib.request.urlretrieve(url, dest)

    def _extractall(self, tf, dest):
        if sys.version_info >= (3, 12):
            tf.extractall(dest, filter='data')
        else:
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
        logger.info(f'Downloading esbuild for {system}/{machine}...')
        meta = self._fetch_json(_npm_url(pkg_name, 'latest'))
        tarball_url = meta['dist']['tarball']

        tmp_tgz = os.path.join(self.cache_dir, '_esbuild_pkg.tgz')
        self._download(tarball_url, tmp_tgz)

        with tarfile.open(tmp_tgz, 'r:gz') as tf:
            found = None
            for member in tf.getmembers():
                if member.name == inner_path:
                    found = member
                    break
            if not found:
                raise RuntimeError(f'Binary not found at {inner_path} in esbuild package')
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
                    items.append((_safe_pkg_name(name), f'{pkg}@{version.strip()}'))
                elif '=' in line:
                    # alias=package@version
                    alias, spec = line.split('=', 1)
                    items.append((alias.strip(), spec.strip()))
                else:
                    name, _ = self._parse_spec(line)
                    items.append((_safe_pkg_name(name), line))
        return items

    def _parse_spec(self, spec):
        """Parse 'name@version' into (name, version). Handles scoped packages."""
        if spec.startswith('@'):
            rest = spec[1:]
            if '@' in rest:
                pkg, version = rest.rsplit('@', 1)
                return '@' + pkg, version
            return spec, 'latest'
        if '@' in spec:
            name, version = spec.split('@', 1)
            return name, version
        return spec, 'latest'

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
        highest stable version that satisfies the spec.  Operator semantics:
          ^major.x.x  -> lock major
          ~major.minor.x -> lock major.minor
          bare digits  -> lock as many parts as given (18 -> major=18)
        """
        logger.info(f'Resolving {spec!r} for {name}')
        meta = self._fetch_json(_npm_url(name))

        dist_tags = meta.get('dist-tags', {})
        if spec in dist_tags:
            return dist_tags[spec]

        # Stable versions only (skip pre-releases like 18.0.0-rc.3)
        versions = [v for v in meta.get('versions', {})
                    if '-' not in v.split('+')[0]]

        m = re.match(r'^([~^><=]*)(.*)', spec)
        op = m.group(1) if m else ''
        clean = m.group(2) if m else spec

        nums = []
        for part in clean.split('.'):
            if part.isdigit():
                nums.append(int(part))
            else:
                break

        if '^' in op:
            lock = nums[:1]       # ^18.0.0 -> major must match
        elif '~' in op:
            lock = nums[:2]       # ~18.2.0 -> major.minor must match
        else:
            lock = nums           # 18 -> major; 18.2 -> major.minor; etc.

        def satisfies(v):
            t = _semver_tuple(v)
            if not t:
                return False
            return all(i < len(t) and t[i] == c for i, c in enumerate(lock))

        matching = [v for v in versions if satisfies(v)]
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
        tarball_url = meta['dist']['tarball']

        actual_dir = os.path.join(self.cache_dir, 'packages', f'{safe}@{actual_version}')
        if not force and self._cache_valid(actual_dir):
            logger.debug(f'Using cached: {name}@{actual_version}')
            return actual_dir, name, actual_version

        tgz_path = actual_dir + '.tgz'
        os.makedirs(os.path.dirname(tgz_path), exist_ok=True)
        self._download(tarball_url, tgz_path)

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

        for spec in specs:
            submit_if_new(spec)

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

    _MANIFEST = 'manifest.json'

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

        return (
            os.path.isfile(os.path.join(output_dir, 'gnr_ext_bundle.js'))
            and all(
                os.path.isfile(os.path.join(output_dir, manifest[a]['file']))
                for a in manifest
            )
        )

    def _results_from_manifest(self, items, output_dir):
        manifest = self._load_manifest(output_dir)
        return [
            (alias, manifest[alias]['name'], manifest[alias]['version'],
             os.path.join(output_dir, manifest[alias]['file']))
            for alias, _ in items
        ]

    def bundle(self, items, output_dir, force=False):
        """Download and bundle packages with esbuild into output_dir.

        items: list of (alias, spec) tuples as returned by parse_requirements().

        Always produces two outputs:
          - <alias>.js per package (others marked --external to avoid duplication)
          - gnr_ext_bundle.js with every package as a namespaced export

        Returns list of (alias, name, version, output_file) tuples for the
        per-package files.
        """
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
                [spec for _, spec in items], force=force
            )
            for name, info in downloaded.items():
                if info and info[0]:
                    self._symlink_package(node_modules_dir, info[0], name)

            top_level = []
            for alias, spec in items:
                name, _ = self._parse_spec(spec)
                pkg_dir, version = downloaded[name]
                top_level.append((alias, name, version))

            results = self._bundle_separate(esbuild, workspace, top_level, output_dir)
            self._bundle_single(esbuild, workspace, top_level, output_dir)

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
                ef.write(f"export * from '{name}';\n")

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
                ef.write(f"export * as {alias} from '{name}';\n")

        out_file = os.path.join(output_dir, 'gnr_ext_bundle.js')
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
    directory resolution, and requirement deduplication across packages.
    """

    def __init__(self, app, verbose=False):
        self.app = app
        self.builder = EsmBuilder(verbose=verbose)

    def collect_requirements(self):
        """Return {alias: {'spec': str, 'packages': [str]}} from all instance packages."""
        all_items = {}
        for package, _pkgattrs, _pkgcontent in self.app.config['packages'].digest('#k,#a,#v'):
            if ':' in package:
                project, package = package.split(':')
            else:
                project = None
            package_folder = self.app.pkg_name_to_path(package, project)
            esm_req = os.path.join(package_folder, package, 'esm_requirements.txt')
            if os.path.isfile(esm_req):
                for alias, spec in self.builder.parse_requirements(esm_req):
                    if alias not in all_items:
                        all_items[alias] = {'spec': spec, 'packages': []}
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
        results = self.builder.bundle(bundle_items, output_dir, force=force)
        return output_dir, results
