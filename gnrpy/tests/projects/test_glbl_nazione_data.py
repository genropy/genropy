"""Guards for the country dataset shipped by the gnr_it:glbl package.

``glbl.nazione`` is a lookup that other packages point foreign keys at, so a
country code missing from the shipped data makes every row referencing it
impossible to migrate. The dataset lives in two places that must not drift
apart: ``startup_data.gz``, which ``Package.loadStartupData()`` reads, and the
``populate()`` seed list in the model.
"""

import gzip
import importlib.util
import pathlib
import shutil

import pytest

from gnr.core.gnrbag import Bag

GLBL = (pathlib.Path(__file__).parents[3]
        / 'projects' / 'gnr_it' / 'packages' / 'glbl')

# Codes assigned by ISO 3166-1 after the list originally shipped was compiled.
CODES_ADDED_SINCE_2006 = {
    'BL': 'BLM', 'BQ': 'BES', 'CW': 'CUW', 'GG': 'GGY', 'IM': 'IMN',
    'JE': 'JEY', 'ME': 'MNE', 'MF': 'MAF', 'RS': 'SRB', 'SS': 'SSD',
    'SX': 'SXM',
}

# Withdrawn codes kept on purpose: existing databases may still reference them
# and ISO 3166-3 records them as formerly used.
WITHDRAWN_CODES_KEPT = {'AN', 'CS'}


@pytest.fixture(scope='module')
def startup_data_countries(tmp_path_factory):
    """Countries as ``loadStartupData()`` would read them from the archive."""
    pik = tmp_path_factory.mktemp('glbl') / 'startup_data.pik'
    with gzip.open(GLBL / 'startup_data.gz', 'rb') as src:
        with open(pik, 'wb') as dest:
            shutil.copyfileobj(src, dest)
    return [dict(r) for r in Bag(str(pik))['nazione']]


@pytest.fixture(scope='module')
def populate_countries():
    """Countries as ``Table.populate()`` builds them from its seed list."""
    path = GLBL / 'model' / 'nazione.py'
    spec = importlib.util.spec_from_file_location('glbl_nazione_model', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Collector(module.Table):
        def __init__(self):
            self.records = []

        def insertOrUpdate(self, record):
            self.records.append(record)

    collector = Collector()
    collector.populate()
    return collector.records


def test_startup_data_and_populate_agree(startup_data_countries,
                                         populate_countries):
    """The archive and the seed list must describe the same countries."""
    from_archive = {r['code'] for r in startup_data_countries}
    from_populate = {r['code'] for r in populate_countries}
    assert from_archive == from_populate, (
        'startup_data.gz and populate() disagree. '
        f'Only in the archive: {sorted(from_archive - from_populate)}. '
        f'Only in populate(): {sorted(from_populate - from_archive)}.')


@pytest.mark.parametrize('source', ['startup_data_countries',
                                    'populate_countries'])
def test_codes_added_since_2006_are_present(source, request):
    """Countries whose code was assigned after the original list was compiled."""
    countries = {r['code']: r for r in request.getfixturevalue(source)}
    missing = sorted(set(CODES_ADDED_SINCE_2006) - set(countries))
    assert not missing, f'missing ISO 3166-1 alpha-2 codes: {missing}'
    for code, alpha3 in CODES_ADDED_SINCE_2006.items():
        assert countries[code]['code3'] == alpha3, (
            f'{code}: expected alpha-3 {alpha3}, '
            f"got {countries[code]['code3']}")


@pytest.mark.parametrize('source', ['startup_data_countries',
                                    'populate_countries'])
def test_withdrawn_codes_are_kept(source, request):
    """Removing them would break databases that already reference them."""
    codes = {r['code'] for r in request.getfixturevalue(source)}
    assert WITHDRAWN_CODES_KEPT <= codes, (
        f'withdrawn codes dropped: {sorted(WITHDRAWN_CODES_KEPT - codes)}')


@pytest.mark.parametrize('source', ['startup_data_countries',
                                    'populate_countries'])
def test_records_are_well_formed(source, request):
    """A malformed row silently produces an unusable lookup entry."""
    countries = request.getfixturevalue(source)
    codes = [r['code'] for r in countries]
    duplicates = sorted({c for c in codes if codes.count(c) > 1})
    assert not duplicates, f'duplicate country codes: {duplicates}'
    for r in countries:
        assert len(r['code']) == 2 and r['code'].isalpha() and r['code'].isupper(), r
        assert len(r['code3']) == 3 and r['code3'].isalpha(), r
        assert len(r['nmbr']) == 3 and r['nmbr'].isdigit(), r
        assert r['name'] and r['name'] == r['name'].strip(), r
