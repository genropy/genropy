import pytest
from unittest.mock import MagicMock

from gnr.utils.awsmanager import Route53Manager


ZONE_ID = '/hostedzone/Z1234567890'

_HOSTED_ZONES_RESPONSE = {
    'HostedZones': [{'Name': 'example.com.', 'Id': ZONE_ID}]
}


def _make_record(name, rtype, *values):
    return {
        'Name': name,
        'Type': rtype,
        'TTL': 300,
        'ResourceRecords': [{'Value': v} for v in values],
    }


def _make_client(records=None, zones_response=None):
    client = MagicMock()
    client.list_hosted_zones.return_value = zones_response or _HOSTED_ZONES_RESPONSE
    client.list_resource_record_sets.return_value = {
        'ResourceRecordSets': records or []
    }
    return client


def _make_manager(client=None):
    mgr = Route53Manager(region_name='eu-south-1')
    mgr.get_client = MagicMock(return_value=client or _make_client())
    return mgr


# ---------- find_managed_zone ----------

def test_find_managed_zone_direct_match():
    mgr = _make_manager()
    zone_name, zone_id = mgr.find_managed_zone('example.com')
    assert zone_name == 'example.com'
    assert zone_id == ZONE_ID


def test_find_managed_zone_subdomain():
    mgr = _make_manager()
    zone_name, zone_id = mgr.find_managed_zone('foo.example.com')
    assert zone_name == 'example.com'
    assert zone_id == ZONE_ID


def test_find_managed_zone_deep_subdomain():
    mgr = _make_manager()
    zone_name, _ = mgr.find_managed_zone('a.b.example.com')
    assert zone_name == 'example.com'


def test_find_managed_zone_strips_trailing_dot():
    mgr = _make_manager()
    zone_name, zone_id = mgr.find_managed_zone('foo.example.com.')
    assert zone_name == 'example.com'
    assert zone_id == ZONE_ID


def test_find_managed_zone_not_found():
    mgr = _make_manager()
    zone_name, zone_id = mgr.find_managed_zone('other.org')
    assert zone_name is None
    assert zone_id is None


# ---------- record_exists ----------

def test_record_exists_found():
    record = _make_record('foo.example.com.', 'CNAME', 'bar.example.com')
    mgr = _make_manager(_make_client(records=[record]))
    result = mgr.record_exists('foo.example.com', hosted_zone_id=ZONE_ID)
    assert result['status'] == 'ok'
    assert result['value']['type'] == 'CNAME'
    assert result['value']['resource_records'] == ['bar.example.com']


def test_record_exists_not_found():
    mgr = _make_manager()
    result = mgr.record_exists('missing.example.com', hosted_zone_id=ZONE_ID)
    assert result['status'] == 'error'
    assert result['value'] is None


def test_record_exists_auto_discovers_zone():
    record = _make_record('foo.example.com.', 'CNAME', 'bar.example.com')
    mgr = _make_manager(_make_client(records=[record]))
    assert mgr.record_exists('foo.example.com')['status'] == 'ok'


def test_record_exists_returns_none_when_no_managed_zone():
    mgr = _make_manager()
    result = mgr.record_exists('foo.other.org')
    assert result['status'] == 'error'


# ---------- verify_record ----------

def test_verify_record_correct_type_and_value():
    record = _make_record('foo.example.com.', 'CNAME', 'bar.example.com')
    mgr = _make_manager(_make_client(records=[record]))
    result = mgr.verify_record('foo.example.com', 'CNAME', 'bar.example.com',
                               hosted_zone_id=ZONE_ID)
    assert result['status'] == 'ok'
    assert result['value'] is True


def test_verify_record_wrong_type():
    record = _make_record('foo.example.com.', 'A', '1.2.3.4')
    mgr = _make_manager(_make_client(records=[record]))
    result = mgr.verify_record('foo.example.com', 'CNAME', '1.2.3.4',
                               hosted_zone_id=ZONE_ID)
    assert result['status'] == 'error'
    assert result['value'] is False


def test_verify_record_wrong_value():
    record = _make_record('foo.example.com.', 'CNAME', 'bar.example.com')
    mgr = _make_manager(_make_client(records=[record]))
    result = mgr.verify_record('foo.example.com', 'CNAME', 'other.example.com',
                               hosted_zone_id=ZONE_ID)
    assert result['status'] == 'error'
    assert result['value'] is False


def test_verify_record_missing():
    mgr = _make_manager()
    result = mgr.verify_record('missing.example.com', 'CNAME', 'x',
                               hosted_zone_id=ZONE_ID)
    assert result['status'] == 'error'


# ---------- ensure_cname_record ----------

def test_ensure_cname_no_managed_zone():
    mgr = _make_manager()
    with pytest.raises(ValueError, match='No managed Route53 zone'):
        mgr.ensure_cname_record('foo.other.org', 'bar.example.com')


def test_ensure_cname_record_exists_correct_value():
    record = _make_record('foo.example.com.', 'CNAME', 'bar.example.com')
    client = _make_client(records=[record])
    mgr = _make_manager(client)
    assert mgr.ensure_cname_record('foo.example.com', 'bar.example.com') is False
    client.change_resource_record_sets.assert_not_called()


def test_ensure_cname_record_exists_wrong_value():
    record = _make_record('foo.example.com.', 'CNAME', 'other.example.com')
    mgr = _make_manager(_make_client(records=[record]))
    with pytest.raises(ValueError, match='already exists with a different value'):
        mgr.ensure_cname_record('foo.example.com', 'bar.example.com')


def test_ensure_cname_absent_dryrun_skips_write():
    client = _make_client()
    mgr = _make_manager(client)
    result = mgr.ensure_cname_record('foo.example.com', 'bar.example.com', dryrun=True)
    assert result is True
    client.change_resource_record_sets.assert_not_called()


def test_ensure_cname_absent_creates_record():
    client = _make_client()
    mgr = _make_manager(client)
    result = mgr.ensure_cname_record('foo.example.com', 'bar.example.com', ttl=300)
    assert result is True
    client.change_resource_record_sets.assert_called_once_with(
        HostedZoneId=ZONE_ID,
        ChangeBatch={
            'Comment': 'add foo.example.com. -> bar.example.com',
            'Changes': [{
                'Action': 'UPSERT',
                'ResourceRecordSet': {
                    'Name': 'foo.example.com.',
                    'Type': 'CNAME',
                    'TTL': 300,
                    'ResourceRecords': [{'Value': 'bar.example.com'}]
                }
            }]
        }
    )
