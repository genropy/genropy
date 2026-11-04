from email.utils import parsedate_to_datetime

from gnr.lib.services.mail import MailService


def build_message(**kwargs):
    mh = MailService()
    msg = mh.build_base_message(subject='Test', body='Test body')
    mh.set_address_headers(msg, **kwargs)
    return msg


def test_set_address_headers_complete():
    msg = build_message(from_address='sender@example.com', to_address='dest@example.org',
                        reply_to='reply@example.com')
    assert msg['From'] == 'sender@example.com'
    assert msg['To'] == 'dest@example.org'
    assert msg['reply-to'] == 'reply@example.com'
    assert msg['Subject'] == 'Test'
    assert parsedate_to_datetime(msg['Date']) is not None
    assert msg['Message-ID'].startswith('<')
    assert msg['Message-ID'].endswith('@example.com>')


def test_set_address_headers_display_name_sender():
    msg = build_message(from_address='Sender Name <sender@example.com>')
    assert msg['From'] == 'Sender Name <sender@example.com>'
    assert msg['Message-ID'].endswith('@example.com>')


def test_set_address_headers_without_addresses():
    msg = build_message()
    assert msg['From'] is None
    assert msg['To'] is None
    assert msg['reply-to'] is None
    assert msg['Date']
    assert msg['Message-ID']
