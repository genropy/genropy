-- External audit: the two trigger functions shared by every table with
-- audit='external'. Both receive the comma-separated excluded columns as
-- their last trigger argument.

-- __version: 0 at insert; +1 when an audited column changes; unchanged
-- otherwise. A record without version (it existed before activation) gets
-- 1 at its first audited change, 0 when the statement sets it (touch).
CREATE OR REPLACE FUNCTION {sqlschema}.version_before() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_excluded text[] := string_to_array(TG_ARGV[0], ',');
    v_changed boolean;
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.__version := 0;
        RETURN NEW;
    END IF;
    v_changed := (to_jsonb(NEW) - v_excluded) IS DISTINCT FROM (to_jsonb(OLD) - v_excluded);
    IF OLD.__version IS NOT NULL THEN
        NEW.__version := OLD.__version + CASE WHEN v_changed THEN 1 ELSE 0 END;
    ELSIF v_changed THEN
        NEW.__version := 1;
    ELSIF NEW.__version IS DISTINCT FROM 0 THEN
        NEW.__version := NULL;
    END IF;
    RETURN NEW;
END $$;

-- One queue row per written record: insert and delete always, update only
-- when __version changed. Arguments: GenroPy fullname, pkey column,
-- excluded columns. User, caller and command come from the GNRCOMMENT line.
-- The pkey is read as text, so a character(n) pkey loses its padding.
CREATE OR REPLACE FUNCTION {sqlschema}.capture_after() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_excluded text[] := string_to_array(TG_ARGV[2], ',');
    v_first_line text := split_part(current_query(), E'\n', 1);
    v_gnr jsonb;
    v_new jsonb;
    v_old jsonb;
    v_pkey text;
    v_data jsonb;
    v_old_full jsonb;
    v_version bigint;
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.__version IS NOT DISTINCT FROM OLD.__version THEN
        RETURN NULL;
    END IF;
    IF v_first_line LIKE '-- GNRCOMMENT - %' THEN
        v_gnr := substr(v_first_line, 17)::jsonb;
    END IF;
    IF TG_OP <> 'DELETE' THEN
        EXECUTE format('SELECT ($1).%I::text', TG_ARGV[1]) INTO v_pkey USING NEW;
        v_new := to_jsonb(NEW) - v_excluded;
        v_version := NEW.__version;
    END IF;
    IF TG_OP <> 'INSERT' THEN
        IF v_pkey IS NULL THEN
            EXECUTE format('SELECT ($1).%I::text', TG_ARGV[1]) INTO v_pkey USING OLD;
        END IF;
        v_old := to_jsonb(OLD) - v_excluded;
        IF OLD.__version IS NULL THEN
            v_old_full := v_old;
        END IF;
    END IF;
    IF TG_OP = 'INSERT' THEN
        v_data := v_new;
    ELSIF TG_OP = 'DELETE' THEN
        v_data := v_old;
        v_version := COALESCE(OLD.__version, 0) + 1;
    ELSE
        SELECT COALESCE(jsonb_object_agg(n.key, n.value), '{}'::jsonb) INTO v_data
          FROM jsonb_each(v_new) n
         WHERE n.value IS DISTINCT FROM v_old -> n.key;
    END IF;
    INSERT INTO {sqlschema}.audit_queue
        (ts, txid, tbl, record_pkey, op, version, username, caller, sqlcommand, data, old_full)
    VALUES (now(), txid_current(), TG_ARGV[0], v_pkey, left(TG_OP, 1), v_version,
            v_gnr ->> 'user',
            CASE WHEN v_gnr IS NOT NULL THEN
                concat(v_gnr ->> 'module_name', '.', v_gnr ->> 'function_name', ':', v_gnr ->> 'line_number')
            END,
            v_gnr ->> 'sqlcommand', v_data, v_old_full);
    RETURN NULL;
END $$;
