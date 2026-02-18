"""Tests for confirmed bugs in the migration package (now fixed).

Bug inventory (from migration/README.md):

1. structures.py  — new_relation_item() mutates caller's attributes dict
2. structures.py  — new_index_item()    mutates caller's attributes dict
3. db_extractor.py — stale loop variable ``v`` in process_constraints
4. command_builder.py — reads constraint_name from command dict instead of
   entity attributes
5. migrator.py — falsy check on ``{}`` causes unnecessary re-extraction
"""

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Bug 1 — new_relation_item mutates caller's attributes dict
# ---------------------------------------------------------------------------

class TestBug1_RelationItemMutatesCallerDict:

    def test_caller_dict_unchanged_after_new_relation_item(self):
        from gnr.sql.migration.structures import new_relation_item

        caller_attrs = {
            'related_table': 'other_table',
            'related_schema': 'public',
            'related_columns': 'id',
        }
        original_keys = set(caller_attrs.keys())

        new_relation_item(
            schema_name='public',
            table_name='my_table',
            columns=['fk_id'],
            attributes=caller_attrs,
        )

        assert set(caller_attrs.keys()) == original_keys, (
            "new_relation_item() should not add keys to the caller's dict; "
            f"found extra keys: {set(caller_attrs.keys()) - original_keys}"
        )


# ---------------------------------------------------------------------------
# Bug 2 — new_index_item mutates caller's attributes dict
# ---------------------------------------------------------------------------

class TestBug2_IndexItemMutatesCallerDict:

    def test_caller_dict_unchanged_after_new_index_item(self):
        from gnr.sql.migration.structures import new_index_item

        caller_attrs = {
            'unique': True,
            'method': 'btree',
        }
        original_keys = set(caller_attrs.keys())

        new_index_item(
            schema_name='public',
            table_name='my_table',
            columns=['col_a', 'col_b'],
            attributes=caller_attrs,
        )

        assert set(caller_attrs.keys()) == original_keys, (
            "new_index_item() should not add keys to the caller's dict; "
            f"found extra keys: {set(caller_attrs.keys()) - original_keys}"
        )


# ---------------------------------------------------------------------------
# Bug 3 — stale loop variable v in process_constraints
# ---------------------------------------------------------------------------

class TestBug3_StaleLoopVariableInProcessConstraints:

    def test_multi_unique_constraint_uses_own_constraint_name(self):
        """When two multi-column UNIQUE constraints exist, each should use
        its own constraint_name — not the last value of ``v`` from the
        previous loop."""
        from gnr.sql.migration.db_extractor import DbExtractor

        extractor = DbExtractor.__new__(DbExtractor)

        extractor.json_schemas = {
            'myschema': {
                'tables': {
                    'mytable': {
                        'attributes': {'pkeys': 'id'},
                        'columns': {
                            'id': {'attributes': {}},
                            'a': {'attributes': {}},
                            'b': {'attributes': {}},
                            'c': {'attributes': {}},
                            'd': {'attributes': {}},
                        },
                        'constraints': {},
                        'indexes': {},
                        'relations': {},
                    }
                }
            }
        }

        constraints_dict = {
            ('myschema', 'mytable'): {
                'UNIQUE': {
                    'uq_ab': {
                        'columns': ['a', 'b'],
                        'constraint_name': 'uq_ab',
                    },
                    'uq_cd': {
                        'columns': ['c', 'd'],
                        'constraint_name': 'uq_cd',
                    },
                },
            }
        }

        extractor.process_constraints(constraints_dict, schemas=['myschema'])

        table_constraints = extractor.json_schemas['myschema']['tables']['mytable']['constraints']

        constraint_names = [
            c['attributes']['constraint_name']
            for c in table_constraints.values()
        ]
        assert 'uq_ab' in constraint_names, (
            f"Expected 'uq_ab' in constraint names, got {constraint_names}. "
            "Bug: stale loop variable 'v' overwrites constraint_name."
        )
        assert 'uq_cd' in constraint_names, (
            f"Expected 'uq_cd' in constraint names, got {constraint_names}."
        )


# ---------------------------------------------------------------------------
# Bug 4 — changed_constraint reads from command dict instead of entity attrs
# ---------------------------------------------------------------------------

class TestBug4_ChangedConstraintReadsWrongDict:

    def test_changed_constraint_uses_entity_attributes(self):
        """changed_constraint() should read constraint_name from
        item['attributes'], not from the commands nested_defaultdict
        (which auto-creates empty entries on access)."""
        from gnr.sql.migration.command_builder import CommandBuilderMixin
        from gnr.sql.migration.structures import nested_defaultdict

        builder = CommandBuilderMixin.__new__(CommandBuilderMixin)

        mock_db = MagicMock()
        mock_db.adapter.struct_constraint_sql.return_value = (
            'CONSTRAINT uq_real UNIQUE("a", "b")'
        )
        builder.db = mock_db
        builder.ignore_constraint_name = False

        commands = nested_defaultdict()
        commands['db']['schemas']['myschema']['tables']['mytable'] = {
            'constraints': nested_defaultdict(),
        }

        builder.commands = commands

        item = {
            'entity_name': 'cst_hash_abc',
            'schema_name': 'myschema',
            'table_name': 'mytable',
            'attributes': {
                'constraint_name': 'uq_real',
                'constraint_type': 'UNIQUE',
                'columns': ['a', 'b'],
            },
        }

        builder.changed_constraint(
            item=item,
            entity_name='cst_hash_abc',
            changed_attribute='columns',
            oldvalue=['a'],
            newvalue=['a', 'b'],
        )

        call_kwargs = mock_db.adapter.struct_constraint_sql.call_args
        passed_name = call_kwargs.kwargs.get(
            'constraint_name',
            call_kwargs[1].get('constraint_name') if len(call_kwargs) > 1 else None
        )
        assert passed_name == 'uq_real', (
            f"Expected constraint_name='uq_real' from entity attributes, "
            f"got '{passed_name}'. Bug: reads from commands dict instead."
        )


# ---------------------------------------------------------------------------
# Bug 5 — falsy check on {} causes unnecessary re-extraction
# ---------------------------------------------------------------------------

class TestBug5_FalsyCheckCausesReextraction:

    def test_empty_dict_structures_not_reextracted(self):
        """After prepareStructures() sets sqlStructure={} (empty DB) and
        ormStructure={} (empty model), jsonModelWithoutMeta() should NOT
        call prepareStructures() again — but the falsy check ``not ({} or {})``
        evaluates to True, triggering a redundant extraction."""
        from gnr.sql.migration.migrator import SqlMigrator

        migrator = SqlMigrator.__new__(SqlMigrator)
        migrator.sqlStructure = {}
        migrator.ormStructure = {}

        prepare_called = False
        original_prepare = SqlMigrator.prepareStructures

        def tracking_prepare(self_inner):
            nonlocal prepare_called
            prepare_called = True
            original_prepare(self_inner)

        with patch.object(SqlMigrator, 'prepareStructures', tracking_prepare):
            try:
                migrator.jsonModelWithoutMeta()
            except Exception:
                pass

        assert not prepare_called, (
            "prepareStructures() was called again even though structures "
            "were already set (to {}). Bug: 'not ({} or {})' is True."
        )
