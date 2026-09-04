import json
import os
import tempfile

import pytest

from gnr.app.esmbuilder import (
    EsmBuilder,
    _npm_url,
    _safe_pkg_name,
    _semver_tuple,
    NPM_REGISTRY,
)
from common import BaseGnrAppTest


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

    def _make_output_dir(self, items, results, create_files=True):
        d = tempfile.mkdtemp()
        self.builder._save_manifest(d, items, results)
        if create_files:
            open(os.path.join(d, 'gnr_ext_bundle.js'), 'w').close()
            for _, _, _, f in results:
                open(f, 'w').close()
        return d

    def test_up_to_date_when_manifest_and_files_match(self):
        items = [('react', 'react@18.2.0')]
        with tempfile.TemporaryDirectory() as d:
            results = [('react', 'react', '18.2.0', os.path.join(d, 'react.js'))]
            open(os.path.join(d, 'gnr_ext_bundle.js'), 'w').close()
            open(os.path.join(d, 'react.js'), 'w').close()
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
            open(os.path.join(d, 'gnr_ext_bundle.js'), 'w').close()
            open(os.path.join(d, 'react.js'), 'w').close()
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

    def test_not_up_to_date_when_alias_set_differs(self):
        items_old = [('react', 'react@18.2.0')]
        items_new = [('react', 'react@18.2.0'), ('vue', 'vue@3.0.0')]
        with tempfile.TemporaryDirectory() as d:
            results = [('react', 'react', '18.2.0', os.path.join(d, 'react.js'))]
            open(os.path.join(d, 'gnr_ext_bundle.js'), 'w').close()
            open(os.path.join(d, 'react.js'), 'w').close()
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
