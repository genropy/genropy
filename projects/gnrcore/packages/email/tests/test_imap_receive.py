import base64
import os

from gnr.core.gnrlang import gnrImport

imap_module = gnrImport(os.path.join(os.path.dirname(__file__), '..', 'lib', 'imap.py'), silent=False)
ImapReceiver = imap_module.ImapReceiver

message_model = gnrImport(os.path.join(os.path.dirname(__file__), '..', 'model', 'message.py'), silent=False)
MessageTable = message_model.Table


class FakeMessagesTable:
    def __init__(self):
        self.inserted = []

    def checkDuplicate(self, account_id=None, uid=None):
        return False

    def insert(self, record):
        self.inserted.append(record)


class FakeAccountTable:
    def __init__(self):
        self.last_uid = None

    def update(self, record, oldrecord=None):
        self.last_uid = record['last_uid']


class FakeMailboxTable:
    def readColumns(self, **kwargs):
        return 'MBX'


class FakeSite:
    debug = False


class FakeApplication:
    site = FakeSite()


class FakeDb:
    def __init__(self, tables):
        self.tables = tables
        self.application = FakeApplication()
        self.commits = 0
        self.rollbacks = 0

    def table(self, name):
        return self.tables[name]

    def commit(self):
        self.commits += 1

    def rollbackAll(self):
        self.rollbacks += 1


class FakeImap:
    def login(self, username, password):
        pass

    def select(self, mailbox):
        pass

    def uid(self, command, *args):
        return 'OK', [b'1 2 3']


def build_receiver(poisoned_uid=None):
    """An ImapReceiver wired on fakes, bypassing __init__ (which opens a real socket)."""
    receiver = ImapReceiver.__new__(ImapReceiver)
    messages_table = FakeMessagesTable()
    account_table = FakeAccountTable()
    db = FakeDb({'email.message': messages_table,
                 'email.attachment': None,
                 'email.mailbox': FakeMailboxTable()})
    receiver.db = db
    receiver.messages_table = messages_table
    receiver.account_table = account_table
    receiver.attachments_table = None
    receiver.account_id = 'ACC'
    receiver.last_uid = None
    receiver.username = 'u'
    receiver.password = 'p'
    receiver.imap = FakeImap()

    def createMessageRecord(email_id, mailbox_id):
        if email_id == poisoned_uid:
            raise ValueError('unreadable attachment')
        return dict(id='msg_%s' % email_id.decode(), uid=email_id)

    receiver.createMessageRecord = createMessageRecord
    return receiver


def test_healthy_messages_are_committed_one_by_one():
    receiver = build_receiver()
    receiver.receive()
    assert [r['uid'] for r in receiver.messages_table.inserted] == [b'1', b'2', b'3']
    assert receiver.db.rollbacks == 0
    assert receiver.account_table.last_uid == b'3'


def test_a_failing_message_does_not_stop_the_others():
    receiver = build_receiver(poisoned_uid=b'2')
    receiver.receive()
    assert [r['uid'] for r in receiver.messages_table.inserted] == [b'1', b'3']
    assert receiver.db.rollbacks == 1
    # last_uid moves past the failing message, so the mailbox is not stuck on it forever
    assert receiver.account_table.last_uid == b'3'


def _decode(payload):
    return MessageTable.decodeAttachmentPayload(MessageTable.__new__(MessageTable), payload)


def _mime_lines(raw):
    """Base64 as it travels in a MIME part: wrapped at 76 columns."""
    b64 = base64.b64encode(raw).decode()
    return '\n'.join([b64[i:i + 76] for i in range(0, len(b64), 76)])


def test_wrapped_base64_decodes():
    raw = b'%PDF-1.4 ' + b'x' * 200
    assert _decode(_mime_lines(raw)) == raw


def test_base64_with_lost_padding_still_decodes():
    # a PEC arriving with the trailing '=' stripped raised binascii.Error and
    # took the whole message down with it
    raw = b'%PDF-1.4 contenuto'
    assert _decode(_mime_lines(raw).rstrip('=')) == raw


def test_payload_with_stray_characters_still_decodes():
    # b64decode drops these on its own, so the padding must be counted without them
    raw = b'%PDF-1.4 contenuto'
    assert _decode(_mime_lines(raw).replace('\n', '\n\t *** \n')) == raw


def test_undecodable_payload_returns_none():
    # a base64 alphabet length of 4n+1 cannot be padded into anything valid:
    # the caller stores the raw payload instead of losing the whole message
    assert _decode('QUJDRA' + 'Q' * 3) is None
