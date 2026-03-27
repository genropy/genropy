"""Tests for encrypted columns feature (issue #747).

Tests cover:
1. ColumnEncryptor — encrypt/decrypt/verify for all three modes (R, Q, X)
2. Column model — encrypted attribute and normalization
3. prepareRecordData — encryption on write
4. decrypt_row — decryption on read
5. Integration with test_invoice DB (customer table with encrypted columns)
"""

import os

import pytest

from gnr.sql.gnrsql.encryption import ColumnEncryptor

TEST_ENCRYPTION_KEY = 'gnr_test_encryption_key_747'


@pytest.fixture(scope='module')
def enc_db(db_sqlite):
    """Ensure the db_sqlite fixture has encryption enabled."""
    db_sqlite._encryption = ColumnEncryptor(TEST_ENCRYPTION_KEY)
    db_sqlite._encryption_initialized = True
    return db_sqlite


def setup_module(module):
    """Configure genro environment for GnrApp-based fixtures."""
    from core.common import BaseGnrTest
    BaseGnrTest.setup_class()


def teardown_module(module):
    from core.common import BaseGnrTest
    BaseGnrTest.teardown_class()


# ---------------------------------------------------------------------------
#  1. ColumnEncryptor unit tests
# ---------------------------------------------------------------------------

class TestColumnEncryptorModeR:
    """Mode R (Reversible): Fernet, non-deterministic."""

    def setup_method(self):
        self.enc = ColumnEncryptor('test_secret_key_747')

    def test_encrypt_returns_prefixed_string(self):
        result = self.enc.encrypt('hello', 'R')
        assert result.startswith('$R$')

    def test_decrypt_roundtrip(self):
        encrypted = self.enc.encrypt('my_api_token', 'R')
        assert self.enc.decrypt(encrypted) == 'my_api_token'

    def test_non_deterministic(self):
        e1 = self.enc.encrypt('same_value', 'R')
        e2 = self.enc.encrypt('same_value', 'R')
        assert e1 != e2

    def test_decrypt_different_values(self):
        e1 = self.enc.encrypt('value_a', 'R')
        e2 = self.enc.encrypt('value_b', 'R')
        assert self.enc.decrypt(e1) == 'value_a'
        assert self.enc.decrypt(e2) == 'value_b'

    def test_encrypt_none_returns_none(self):
        assert self.enc.encrypt(None, 'R') is None

    def test_decrypt_none_returns_none(self):
        assert self.enc.decrypt(None) is None

    def test_unicode_roundtrip(self):
        text = 'àèìòù €£¥ 日本語'
        encrypted = self.enc.encrypt(text, 'R')
        assert self.enc.decrypt(encrypted) == text


class TestColumnEncryptorModeQ:
    """Mode Q (Querable): AES-SIV, deterministic."""

    def setup_method(self):
        self.enc = ColumnEncryptor('test_secret_key_747')

    def test_encrypt_returns_prefixed_string(self):
        result = self.enc.encrypt('PRCGNN51P14F205K', 'Q')
        assert result.startswith('$Q$')

    def test_decrypt_roundtrip(self):
        encrypted = self.enc.encrypt('PRCGNN51P14F205K', 'Q')
        assert self.enc.decrypt(encrypted) == 'PRCGNN51P14F205K'

    def test_deterministic(self):
        e1 = self.enc.encrypt('PRCGNN51P14F205K', 'Q')
        e2 = self.enc.encrypt('PRCGNN51P14F205K', 'Q')
        assert e1 == e2

    def test_different_values_different_ciphertext(self):
        e1 = self.enc.encrypt('AAAA', 'Q')
        e2 = self.enc.encrypt('BBBB', 'Q')
        assert e1 != e2

    def test_different_keys_different_ciphertext(self):
        enc2 = ColumnEncryptor('different_key')
        e1 = self.enc.encrypt('same', 'Q')
        e2 = enc2.encrypt('same', 'Q')
        assert e1 != e2


class TestColumnEncryptorModeX:
    """Mode X (one-shot): SHA-256, irreversible."""

    def setup_method(self):
        self.enc = ColumnEncryptor('test_secret_key_747')

    def test_encrypt_returns_prefixed_string(self):
        result = self.enc.encrypt('auth_token_abc', 'X')
        assert result.startswith('$X$')

    def test_decrypt_returns_none(self):
        encrypted = self.enc.encrypt('auth_token_abc', 'X')
        assert self.enc.decrypt(encrypted) is None

    def test_verify_correct(self):
        encrypted = self.enc.encrypt('my_token', 'X')
        assert self.enc.verify('my_token', encrypted) is True

    def test_verify_wrong(self):
        encrypted = self.enc.encrypt('my_token', 'X')
        assert self.enc.verify('wrong_token', encrypted) is False

    def test_verify_empty_stored(self):
        assert self.enc.verify('value', None) is False
        assert self.enc.verify('value', '') is False

    def test_verify_non_x_prefix(self):
        assert self.enc.verify('value', '$R$something') is False

    def test_different_salts(self):
        e1 = self.enc.encrypt('same_token', 'X')
        e2 = self.enc.encrypt('same_token', 'X')
        assert e1 != e2
        assert self.enc.verify('same_token', e1) is True
        assert self.enc.verify('same_token', e2) is True


class TestColumnEncryptorPlainFallback:
    """Plain text values without prefix are returned as-is."""

    def setup_method(self):
        self.enc = ColumnEncryptor('test_secret_key_747')

    def test_plain_string(self):
        assert self.enc.decrypt('plain_value') == 'plain_value'

    def test_non_string(self):
        assert self.enc.decrypt(42) == 42

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError):
            self.enc.encrypt('value', 'Z')


class TestColumnEncryptorDecryptRow:
    """decrypt_row modifies a dict in place."""

    def setup_method(self):
        self.enc = ColumnEncryptor('test_secret_key_747')

    def test_dict_row(self):
        row = {
            'name': 'Mario',
            'tax_id': self.enc.encrypt('PRCGNN51P14F205K', 'Q'),
            'api_key': self.enc.encrypt('sk-12345', 'R'),
        }
        self.enc.decrypt_row(row, {'tax_id': 'Q', 'api_key': 'R'})
        assert row['name'] == 'Mario'
        assert row['tax_id'] == 'PRCGNN51P14F205K'
        assert row['api_key'] == 'sk-12345'

    def test_none_values_skipped(self):
        row = {'tax_id': None}
        self.enc.decrypt_row(row, {'tax_id': 'Q'})
        assert row['tax_id'] is None

    def test_empty_encrypted_columns(self):
        row = {'name': 'Mario'}
        self.enc.decrypt_row(row, {})
        assert row['name'] == 'Mario'

    def test_missing_field_skipped(self):
        row = {'name': 'Mario'}
        self.enc.decrypt_row(row, {'tax_id': 'Q'})
        assert 'tax_id' not in row


# ---------------------------------------------------------------------------
#  2. SqlCompiledQuery encryptedColumns
# ---------------------------------------------------------------------------

class TestCompiledQueryEncryptedColumns:
    """encryptedColumns dict on SqlCompiledQuery."""

    def test_initial_empty(self):
        from gnr.sql.gnrsqldata.compiler import SqlCompiledQuery
        cpl = SqlCompiledQuery('test_table')
        assert cpl.encryptedColumns == {}


# ---------------------------------------------------------------------------
#  3. db.encryption lazy property
# ---------------------------------------------------------------------------

class TestDbEncryptionProperty:
    """db.encryption lazy property."""

    def test_no_key_returns_none(self):
        from gnr.sql.gnrsql.db import GnrSqlDb
        saved = os.environ.pop('GENROPY_ENCRYPTION_KEY', None)
        try:
            db = GnrSqlDb(implementation='sqlite')
            assert db.encryption is None
        finally:
            if saved:
                os.environ['GENROPY_ENCRYPTION_KEY'] = saved

    def test_env_key_creates_encryptor(self):
        from gnr.sql.gnrsql.db import GnrSqlDb
        os.environ['GENROPY_ENCRYPTION_KEY'] = 'test_key_for_pytest'
        try:
            db = GnrSqlDb(implementation='sqlite')
            db._encryption_initialized = False
            assert db.encryption is not None
            assert isinstance(db.encryption, ColumnEncryptor)
        finally:
            del os.environ['GENROPY_ENCRYPTION_KEY']

    def test_lazy_initialized_once(self):
        from gnr.sql.gnrsql.db import GnrSqlDb
        os.environ['GENROPY_ENCRYPTION_KEY'] = 'test_key_for_pytest'
        try:
            db = GnrSqlDb(implementation='sqlite')
            db._encryption_initialized = False
            enc1 = db.encryption
            enc2 = db.encryption
            assert enc1 is enc2
        finally:
            del os.environ['GENROPY_ENCRYPTION_KEY']


# ---------------------------------------------------------------------------
#  4. Integration tests with test_invoice DB (SQLite)
# ---------------------------------------------------------------------------

class TestEncryptedColumnsSqlite:
    """End-to-end encrypted columns on customer table (SQLite)."""

    def _insert_encrypted_customer(self, enc_db):
        """Insert a customer with encrypted fields and return the pkey."""
        tbl = enc_db.table('invc.customer')
        rec = dict(
            id=tbl.newPkeyValue(),
            account_name='Encrypted Test Customer',
            customer_type_code='RES',
            payment_type_code='BANK',
            state='NSW',
            bank_account='IT60X0542811101000000123456',
            registration_id='REG-2024-00042',
            access_token='tok_live_secret_9876',
        )
        tbl.insert(rec)
        enc_db.commit()
        return rec['id']

    def test_insert_and_fetch_decrypted(self, enc_db):
        pkey = self._insert_encrypted_customer(enc_db)
        tbl = enc_db.table('invc.customer')
        rows = tbl.query(
            columns='$account_name, $bank_account, $registration_id, $access_token',
            where='$id = :pk', pk=pkey,
        ).fetch()
        assert len(rows) == 1
        row = rows[0]
        assert row['account_name'] == 'Encrypted Test Customer'
        assert row['bank_account'] == 'IT60X0542811101000000123456'
        assert row['registration_id'] == 'REG-2024-00042'
        assert row['access_token'] is None  # mode X: not reversible

    def test_raw_db_stores_encrypted(self, enc_db):
        pkey = self._insert_encrypted_customer(enc_db)
        raw_conn = enc_db.adapter.connect()
        raw_conn.row_factory = None
        raw_cur = raw_conn.cursor()
        raw_cur.execute(
            'SELECT bank_account, registration_id, access_token '
            'FROM invc_customer WHERE id = ?',
            (pkey,),
        )
        row = raw_cur.fetchone()
        raw_cur.close()
        assert row[0].startswith('$R$')
        assert row[1].startswith('$Q$')
        assert row[2].startswith('$X$')

    def test_mode_q_searchable_with_encrypt(self, enc_db):
        pkey = self._insert_encrypted_customer(enc_db)
        tbl = enc_db.table('invc.customer')
        encryptor = enc_db.encryption
        encrypted_reg = encryptor.encrypt('REG-2024-00042', 'Q')
        rows = tbl.query(
            columns='$account_name',
            where='$registration_id = :reg', reg=encrypted_reg,
        ).fetch()
        assert len(rows) >= 1
        assert any(r['account_name'] == 'Encrypted Test Customer' for r in rows)

    def test_mode_x_verify(self, enc_db):
        pkey = self._insert_encrypted_customer(enc_db)
        raw_conn = enc_db.adapter.connect()
        raw_conn.row_factory = None
        raw_cur = raw_conn.cursor()
        raw_cur.execute(
            'SELECT access_token FROM invc_customer WHERE id = ?',
            (pkey,),
        )
        stored = raw_cur.fetchone()[0]
        raw_cur.close()
        assert enc_db.encryption.verify('tok_live_secret_9876', stored)
        assert not enc_db.encryption.verify('wrong', stored)

    def test_record_output_bag(self, enc_db):
        pkey = self._insert_encrypted_customer(enc_db)
        tbl = enc_db.table('invc.customer')
        record = tbl.record(pkey).output('bag')
        assert record['bank_account'] == 'IT60X0542811101000000123456'
        assert record['registration_id'] == 'REG-2024-00042'
        assert record['access_token'] is None

    def test_record_output_dict(self, enc_db):
        pkey = self._insert_encrypted_customer(enc_db)
        tbl = enc_db.table('invc.customer')
        record = tbl.record(pkey).output('dict')
        assert record['bank_account'] == 'IT60X0542811101000000123456'
        assert record['registration_id'] == 'REG-2024-00042'

    def test_update_preserves_encryption(self, enc_db):
        pkey = self._insert_encrypted_customer(enc_db)
        tbl = enc_db.table('invc.customer')
        rec = tbl.record(pkey).output('dict')
        rec['bank_account'] = 'DE89370400440532013000'
        tbl.update(rec)
        enc_db.commit()
        # Verify encrypted in raw DB
        raw_conn = enc_db.adapter.connect()
        raw_conn.row_factory = None
        raw_cur = raw_conn.cursor()
        raw_cur.execute(
            'SELECT bank_account FROM invc_customer WHERE id = ?',
            (pkey,),
        )
        raw = raw_cur.fetchone()[0]
        raw_cur.close()
        assert raw.startswith('$R$')
        # Verify decrypted on read
        reloaded = tbl.record(pkey).output('dict')
        assert reloaded['bank_account'] == 'DE89370400440532013000'

    def test_null_values_preserved(self, enc_db):
        tbl = enc_db.table('invc.customer')
        rec = dict(
            id=tbl.newPkeyValue(),
            account_name='Null Encrypted Test',
            customer_type_code='RES',
            payment_type_code='BANK',
            state='NSW',
            bank_account=None,
            registration_id=None,
            access_token=None,
        )
        tbl.insert(rec)
        enc_db.commit()
        reloaded = tbl.record(rec['id']).output('dict')
        assert reloaded['bank_account'] is None
        assert reloaded['registration_id'] is None
        assert reloaded['access_token'] is None

    def test_selection_output_decrypts(self, enc_db):
        pkey = self._insert_encrypted_customer(enc_db)
        tbl = enc_db.table('invc.customer')
        sel = tbl.query(
            columns='$account_name, $bank_account, $registration_id',
            where='$id = :pk', pk=pkey,
        ).selection()
        data = sel.output('dictlist')
        assert len(data) >= 1
        row = data[0]
        assert row['bank_account'] == 'IT60X0542811101000000123456'
        assert row['registration_id'] == 'REG-2024-00042'

    def test_column_model_attributes(self, enc_db):
        col_bank = enc_db.model.column('invc.customer.bank_account')
        col_reg = enc_db.model.column('invc.customer.registration_id')
        col_tok = enc_db.model.column('invc.customer.access_token')
        col_name = enc_db.model.column('invc.customer.account_name')
        assert col_bank.encrypted == 'R'
        assert col_reg.encrypted == 'Q'
        assert col_tok.encrypted == 'X'
        assert col_name.encrypted is None
