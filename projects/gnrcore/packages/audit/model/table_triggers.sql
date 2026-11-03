-- External audit of one table: the two triggers and its row in
-- audit.members. Declared by sysFields for audit='external'.
CREATE OR REPLACE TRIGGER gnr_audit_before
    BEFORE INSERT OR UPDATE ON {sqlfullname}
    FOR EACH ROW EXECUTE FUNCTION {audit_schema}.version_before('{excluded}');
CREATE OR REPLACE TRIGGER gnr_audit_after
    AFTER INSERT OR UPDATE OR DELETE ON {sqlfullname}
    FOR EACH ROW EXECUTE FUNCTION {audit_schema}.capture_after('{fullname}', '{pkey}', '{excluded}');
INSERT INTO {audit_schema}.audit_members (sqltable, tbl, pkey_column, excluded_cols, activated_ts)
VALUES ('{sqlschema}.{sqlname}', '{fullname}', '{pkey}', '{excluded}', now())
ON CONFLICT (sqltable) DO UPDATE SET excluded_cols = EXCLUDED.excluded_cols;
