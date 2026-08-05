"""
command_builder.py - SQL migration command generation
=======================================================

This module contains the :class:`CommandBuilderMixin`, responsible for
translating change events (added, changed, removed) into concrete
SQL commands.

Handler architecture
---------------------

The mixin provides handler methods with the naming convention ``{event}_{entity}``:

- ``added_db``, ``added_schema``, ``added_table``, ``added_column``, ...
- ``changed_table``, ``changed_column``, ``changed_index``, ...
- ``removed_table``, ``removed_column``, ``removed_index``, ...

These handlers are called by ``prepareMigrationCommands()`` (in the migrator)
via dynamic dispatch::

    handler = getattr(self, f'{evt}_{entity}', self.missing_handler_cb)
    handler(**kw)

Each handler generates a SQL fragment and stores it in the
``self.commands`` structure, a nested defaultdict with this hierarchy::

    commands['db']
    +-- 'command': CREATE DATABASE SQL (if DB doesn't exist)
    +-- 'extensions': {ext_name: {'command': CREATE EXTENSION SQL}}
    +-- 'schemas': {schema_name: {
            'command': CREATE SCHEMA SQL,
            'tables': {table_name: {
                'command': CREATE TABLE SQL (for new tables),
                'pre_commands': [...],  (column backups for conversions)
                'columns': {col_name: {'command': ADD/ALTER COLUMN SQL}},
                'indexes': {idx_name: {'command': CREATE INDEX SQL}},
                'relations': {rel_name: {'command': ADD FK SQL}},
                'constraints': {cst_name: {'command': ADD/DROP CONSTRAINT SQL}}
            }}
        }}

Type conversions
-----------------

The most complex handling is in ``changed_column`` for dtype changes.
Conversions follow this logic:

1. **Any type -> text**: always possible (PostgreSQL does implicit cast).
   Exception: bytea -> text uses ``encode(col, 'hex')``.

2. **Supported conversion** (present in ``adapter.TYPE_CONVERSIONS``):
   - ``None`` or ``True``: simple conversion with ALTER TYPE
   - ``str``: complex conversion with USING clause
     - Without ``--force``: raises exception if column is not empty
     - With ``--force``: converts (incompatible values -> NULL)
     - With ``--backup``: creates backup column before conversion

3. **Unsupported conversion**:
   - If column is empty: DROP + ADD (rebuild)
   - If column has data: raises exception

Removal operations
-------------------

Most removals are disabled (no-op with ``pass``) for safety. Only
``removed_column`` actually generates a DROP COLUMN.
Removals are further controlled by the ``removeDisabled`` flag
in the migrator.

Name handling
--------------

Constraint, FK and index names are compared via hash.
The ``ignore_constraint_name`` flag (default True) prevents generating
RENAME when the only difference is the constraint name (which
may differ between ORM and DB but be semantically equivalent).
"""

import re

from gnr.sql.gnrsql_exceptions import GnrSqlException

from gnr.sql._typing import SqlMigratorBaseMixin
from .structures import hashed_name


class CommandBuilderMixin(SqlMigratorBaseMixin):
    """Mixin providing handlers for generating SQL migration commands.

    This mixin is composed into the :class:`SqlMigrator` class and
    requires the host to have these attributes:
    - ``db``: database object with ``db.adapter``
    - ``commands``: nested defaultdict for storing commands
    - ``force``: flag for forcing type conversions
    - ``backup``: flag for creating backups before conversions
    - ``ignore_constraint_name``: flag for ignoring name differences
    - ``removeDisabled``: flag for disabling removals
    """

    def missing_handler_cb(self, **kwargs):
        """Fallback handler for events without a specific handler.

        Used when dynamic dispatch in ``prepareMigrationCommands``
        doesn't find a handler for the event+entity combination.

        Returns:
            str: Message with kwargs for debugging.
        """
        return f'missing {kwargs}'

    # -------------------------------------------------------------------
    # Helpers for navigating the command structure
    # -------------------------------------------------------------------

    def schema_tables(self, schema_name):
        """Access the tables dictionary of a schema in the commands.

        Shortcut for navigating ``self.commands['db']['schemas'][schema]['tables']``.

        Args:
            schema_name: Name of the schema.

        Returns:
            defaultdict: Dictionary of tables with their commands.
        """
        return self.commands['db']['schemas'][schema_name]['tables']

    # -------------------------------------------------------------------
    # ADDED handlers: creation of new entities
    # -------------------------------------------------------------------

    def added_db(self, item=None, **kwargs):
        """Generate the CREATE DATABASE command and delegate schema creation.

        When the database doesn't exist, all ORM content is emitted as
        "added". This handler creates the DB and iterates over schemas.

        Args:
            item: DB entity dictionary with ``entity_name`` and ``schemas``.
        """
        self.commands['db']['command'] = self.db.adapter.createDbSql(
            item['entity_name'], 'UNICODE'
        )
        for schema in item['schemas'].values():
            self.added_schema(item=schema)

    def added_schema(self, item=None, **kwargs):
        """Generate the CREATE SCHEMA command and delegate table creation.

        Args:
            item: Schema entity dictionary with ``entity_name`` and ``tables``.
        """
        schema_name = item['entity_name']
        self.commands['db']['schemas'][schema_name]['command'] = (
            self.db.adapter.createSchemaSql(schema_name)
        )
        for table in item['tables'].values():
            self.added_table(item=table)

    def added_table(self, item=None, **kwargs):
        """Generate the complete CREATE TABLE command with columns, PK and constraints.

        The command includes:
        1. Column definitions (via ``columnSql``)
        2. PRIMARY KEY clause
        3. Inline constraints (e.g. multi-column UNIQUE)
        4. After CREATE TABLE: indexes and FK relations

        If the table has no columns, creation is skipped.

        Args:
            item: Table entity dictionary with ``columns``, ``attributes``,
                ``constraints``, ``indexes``, ``relations``.
        """
        sqltablename = self.tableSqlName(item)
        substatements = []
        if not item['columns']:
            # Table cannot be created without columns
            return
        for col in item['columns'].values():
            substatements.append(self.columnSql(col).strip())
        if item["attributes"]["pkeys"]:
            substatements.append(f'PRIMARY KEY ({item["attributes"]["pkeys"]})')

        # Inline constraints in CREATE TABLE (e.g. multi-column UNIQUE)
        for const_item in item['constraints'].values():
            constattr = const_item['attributes']
            const_sql = self.db.adapter.struct_constraint_sql(
                const_item['entity_name'], constattr['constraint_type'],
                columns=constattr.get('columns'),
                check_clause=constattr.get('check_clause')
            )
            substatements.append(const_sql)

        joined_substatements = ',\n '.join(substatements)
        sql = f"CREATE TABLE {sqltablename}(\n {joined_substatements}\n);"
        self.schema_tables(item['schema_name'])[item['table_name']]['command'] = sql

        # Indexes and relations are created after CREATE TABLE
        for index_item in item['indexes'].values():
            self.added_index(item=index_item)
        for rel_item in item['relations'].values():
            self.added_relation(item=rel_item)

    def added_column(self, item=None, **kwargs):
        """Generate the ADD COLUMN command for a new column.

        The command is a SQL fragment to be used with ALTER TABLE.

        Args:
            item: Column entity dictionary.
        """
        sql = f'ADD COLUMN {self.columnSql(item)}'
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        columns_dict = table_dict['columns']
        columns_dict[item['entity_name']]['command'] = sql

    def added_index(self, item=None, **kwargs):
        """Generate the CREATE INDEX command.

        Args:
            item: Index entity dictionary with attributes
                (columns, method, with_options, etc.).
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        indexes_dict = table_dict['indexes']
        indexes_dict[item['entity_name']]['command'] = self.createIndexSql(item)

    def added_relation(self, item=None, **kwargs):
        """Generate the ADD CONSTRAINT ... FOREIGN KEY command.

        The SQL fragment includes ON DELETE, ON UPDATE,
        DEFERRABLE and INITIALLY DEFERRED clauses if specified.

        Args:
            item: Relation entity dictionary with FK attributes.
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        relations_dict = table_dict['relations']
        relattr = item['attributes']
        sql = self.db.adapter.struct_foreign_key_sql(
            fk_name=item['entity_name'],
            columns=item['attributes']['columns'],
            related_table=relattr['related_table'],
            related_schema=relattr['related_schema'],
            related_columns=relattr['related_columns'],
            on_delete=relattr.get('on_delete'),
            on_update=relattr.get('on_update'),
            deferrable=relattr.get('deferrable'),
            initially_deferred=relattr.get('initially_deferred')
        )
        relations_dict[item['entity_name']] = {
            "command": f'ADD {sql}'
        }

    def added_constraint(self, item=None, **kwargs):
        """Generate the ADD CONSTRAINT command (e.g. multi-column UNIQUE).

        Args:
            item: Constraint entity dictionary with type and columns.
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        constraints_dict = table_dict['constraints']
        sql = self.db.adapter.struct_constraint_sql(  # REVIEW: passes schema_name/table_name which may not be expected by adapter
            schema_name=item['schema_name'],
            table_name=item['table_name'],
            constraint_name=item['entity_name'],
            constraint_type=item['attributes']['constraint_type'],
            columns=item['attributes']['columns']
        )
        constraints_dict[item['entity_name']] = {
            "command": f'ADD {sql};'
        }

    def added_extension(self, item=None, **kwargs):
        """Generate the CREATE EXTENSION command.

        Args:
            item: Extension entity dictionary.
        """
        self.commands['db']['extensions'][item['entity_name']]['command'] = (
            self.db.adapter.struct_create_extension_sql(
                extension_name=item['entity_name']
            )
        )

    def added_event_trigger(self, item=None, **kwargs):
        """Handler for added event triggers. Currently no-op."""
        pass

    # -------------------------------------------------------------------
    # CHANGED handlers: modification of existing entities
    # -------------------------------------------------------------------

    def changed_table(self, item=None, changed_attribute=None,
                      oldvalue=None, newvalue=None, **kwargs):
        """Handle changes in table attributes.

        Currently only handles primary key changes:
        generates DROP of the old PK + ADD of the new PK.

        Args:
            item: Table dictionary.
            changed_attribute: Name of the changed attribute.
            oldvalue: Previous value.
            newvalue: New value.
        """
        schema_name = item['schema_name']
        table_name = item['table_name']
        if changed_attribute == 'pkeys':
            drop_pk_sql = self.db.adapter.struct_drop_table_pkey_sql(
                schema_name, table_name
            )
            add_pk_sql = self.db.adapter.struct_add_table_pkey_sql(
                schema_name, table_name, newvalue
            )
            self.schema_tables(schema_name)[table_name]['command'] = (
                f"{drop_pk_sql}\n{add_pk_sql}"
            )

    def is_empty_column(self, item):
        """Check if a database column is empty (all NULL).

        Used before type conversions to determine if it is safe
        to proceed without risk of data loss.

        Args:
            item: Column dictionary with schema_name, table_name,
                column_name.

        Returns:
            bool: True if the column contains no non-NULL values.
        """
        return self.db.adapter.struct_is_empty_column(
            schema_name=item['schema_name'],
            table_name=item['table_name'],
            column_name=item['column_name']
        )

    def changed_column(self, item=None, changed_attribute=None,
                       oldvalue=None, newvalue=None, **kwargs):
        """Handle changes in column attributes.

        This is the most complex handler. It handles four types of changes:

        **size**: Change in column size.
        If there is no existing command with USING (from dtype conversion),
        generates a simple ALTER TYPE. If there is a USING, only updates
        the type in the existing command.

        **dtype**: Change in data type. Logic follows a priority cascade:

        1. Any type -> text: always possible
           (bytea -> text uses encode(col, 'hex'))
        2. Conversion in TYPE_CONVERSIONS:
           - None/True: simple ALTER TYPE
           - str (USING expression):
             - without --force: exception if column not empty
             - with --force: forced conversion (incompatible -> NULL)
             - with --backup: creates backup column, then converts
        3. Unsupported conversion:
           - empty column: DROP + ADD (complete rebuild)
           - non-empty column: exception

        **notnull**: Addition or removal of NOT NULL constraint.

        **unique**: Addition or removal of UNIQUE constraint.

        **generated_expression, extra_sql**: Ignored (not auto-migratable).

        Args:
            item: Column dictionary with all updated attributes.
            changed_attribute: Name of the changed attribute.
            oldvalue: Previous value in the DB.
            newvalue: New value from the ORM.
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        columns_dict = table_dict['columns']
        column_name = item['entity_name']

        if changed_attribute == 'size' and not item.get('_rebuilt'):
            self._handle_size_change(item, columns_dict, column_name)

        elif changed_attribute == 'dtype':
            self._handle_dtype_change(
                item, table_dict, columns_dict, column_name,
                oldvalue, newvalue
            )

        elif changed_attribute == 'notnull':
            if newvalue:
                columns_dict[column_name]['command'] = (
                    self.db.adapter.struct_add_not_null_sql(
                        column_name=column_name,
                        schema_name=item['schema_name'],
                        table_name=item['table_name']
                    )
                )
            else:
                columns_dict[column_name]['command'] = (
                    self.db.adapter.struct_drop_not_null_sql(
                        column_name=column_name,
                        schema_name=item['schema_name'],
                        table_name=item['table_name'],
                    )
                )

        elif changed_attribute == 'unique':
            if newvalue:
                self.addColumnUniqueConstraint(item)
            else:
                columns = [column_name]
                constraints_dict = table_dict['constraints']
                constraint_name = hashed_name(
                    schema=item['schema_name'],
                    table=item['table_name'],
                    columns=columns, obj_type='cst'
                )
                sql = self.db.adapter.struct_drop_constraint_sql(
                    constraint_name=constraint_name,
                    schema_name=item['schema_name'],
                    table_name=item['table_name'],
                )
                constraints_dict[constraint_name] = {"command": sql}

        elif changed_attribute in ('generated_expression', 'extra_sql'):
            # These attributes are not automatically migratable
            return

    def _handle_size_change(self, item, columns_dict, column_name):
        """Handle column size change.

        If an existing command with USING clause already exists (from a previous
        dtype conversion), only updates the SQL type in the existing command.
        Otherwise generates a new ALTER TYPE.

        Args:
            item: Column dictionary.
            columns_dict: Table columns command dictionary.
            column_name: Name of the column.
        """
        existing_command = columns_dict[column_name].get('command', '')
        if 'USING' not in existing_command:
            new_sql_type = self.db.adapter.columnSqlType(
                dtype=item['attributes']['dtype'],
                size=item['attributes'].get('size')
            )
            columns_dict[column_name]['command'] = (
                self.db.adapter.struct_alter_column_sql(
                    column_name=column_name,
                    new_sql_type=new_sql_type,
                    schema_name=item['schema_name'],
                    table_name=item['table_name']
                )
            )
        else:
            # Update the SQL type in the existing USING command
            new_sql_type = self.db.adapter.columnSqlType(
                dtype=item['attributes']['dtype'],
                size=item['attributes'].get('size')
            )
            existing_command = columns_dict[column_name]['command']
            columns_dict[column_name]['command'] = re.sub(
                r'TYPE\s+\S+(\s+USING)',
                f'TYPE {new_sql_type}\\1',
                existing_command
            )

    def _handle_dtype_change(self, item, table_dict, columns_dict,
                             column_name, oldvalue, newvalue):
        """Handle column dtype change.

        Implements the priority cascade for type conversions:
        text -> always ok, TYPE_CONVERSIONS -> various strategies,
        unsupported -> DROP+ADD or exception.

        Args:
            item: Column dictionary.
            table_dict: Table command dictionary.
            columns_dict: Columns command dictionary.
            column_name: Name of the column.
            oldvalue: Previous dtype in the DB.
            newvalue: New dtype from the ORM.
        """
        TEXT_TYPES = ('T', 'A', 'C', 'X', 'Z', 'P')

        # Generic rule: any type -> text is always possible
        if newvalue in TEXT_TYPES and oldvalue not in TEXT_TYPES:
            new_sql_type = self.db.adapter.columnSqlType(
                dtype=item['attributes']['dtype'],
                size=item['attributes'].get('size')
            )
            if oldvalue == 'O':
                # Bytea requires special encoding
                conversion_expression = f'encode("{column_name}", \'hex\')'
                columns_dict[column_name]['command'] = (
                    self.db.adapter.struct_alter_column_with_conversion_sql(
                        column_name=column_name,
                        new_sql_type=new_sql_type,
                        conversion_expression=conversion_expression,
                        schema_name=item['schema_name'],
                        table_name=item['table_name']
                    )
                )
            else:
                # Simple conversion (PostgreSQL does implicit cast)
                columns_dict[column_name]['command'] = (
                    self.db.adapter.struct_alter_column_sql(
                        column_name=column_name,
                        new_sql_type=new_sql_type,
                        schema_name=item['schema_name'],
                        table_name=item['table_name']
                    )
                )
            return

        conversion_key = (oldvalue, newvalue)
        if conversion_key in self.db.adapter.TYPE_CONVERSIONS:
            self._apply_type_conversion(
                item, table_dict, columns_dict, column_name,
                oldvalue, newvalue
            )
        else:
            # Unsupported conversion
            if self.is_empty_column(item):
                # Empty column: DROP + ADD (complete rebuild)
                entity_name = item['entity_name']
                table_dict['columns'][f'rem_{entity_name}']['command'] = (
                    f'DROP COLUMN "{entity_name}"'
                )
                self.added_column(item)
                item['_rebuilt'] = True
            else:
                raise GnrSqlException(
                    f'Incompatible data type change in a non-empty column. '
                    f'Column {item["table_name"]}.{item["column_name"]} '
                    f'{oldvalue} {newvalue}'
                )

    def _apply_type_conversion(self, item, table_dict, columns_dict,
                               column_name, oldvalue, newvalue):
        """Apply a type conversion supported by TYPE_CONVERSIONS.

        Handles three modes:
        - Simple conversion (None/True): direct ALTER TYPE
        - Conversion with USING (str): with force/backup control
        - With --backup: creates backup column + pre_commands

        Args:
            item: Column dictionary.
            table_dict: Table command dictionary.
            columns_dict: Columns command dictionary.
            column_name: Name of the column.
            oldvalue: Previous dtype.
            newvalue: New dtype.
        """
        conversion_def = self.db.adapter.TYPE_CONVERSIONS[(oldvalue, newvalue)]
        new_sql_type = self.db.adapter.columnSqlType(
            dtype=item['attributes']['dtype'],
            size=item['attributes'].get('size')
        )

        # Simple conversion (None or True): direct ALTER TYPE
        if conversion_def in (None, True):
            columns_dict[column_name]['command'] = (
                self.db.adapter.struct_alter_column_sql(
                    column_name=column_name,
                    new_sql_type=new_sql_type,
                    schema_name=item['schema_name'],
                    table_name=item['table_name']
                )
            )
            return

        # Complex conversion with USING clause
        if isinstance(conversion_def, str):
            schema_name = item['schema_name']
            table_name = item['table_name']
            full_table = f'"{schema_name}"."{table_name}"'
            conversion_expression = conversion_def.format(
                column_name=f'"{column_name}"'
            )

            # Without --force: exception if column is not empty
            if not self.force:
                if not self.is_empty_column(item):
                    raise GnrSqlException(
                        f'Incompatible type conversion {oldvalue}\u2192{newvalue} '
                        f'on non-empty column {table_name}.{column_name}. '
                        f'Use --force to convert (non-matching values become NULL) '
                        f'or --backup to create backup columns first.'
                    )

            # With --backup: create backup column before conversion
            if self.backup:
                backup_column_name = f'{column_name}__{oldvalue}'

                # Register backup info for post-migration verification
                if not hasattr(self, '_conversion_backups'):  # REVIEW: should be initialized in __init__ instead of hasattr check
                    self._conversion_backups = []
                self._conversion_backups.append({
                    'schema': schema_name,
                    'table': table_name,
                    'column': column_name,
                    'backup_column': backup_column_name,
                    'old_dtype': oldvalue,
                    'new_dtype': newvalue
                })

                # Pre-commands: create backup column + copy data
                if 'pre_commands' not in table_dict:
                    table_dict['pre_commands'] = []
                table_dict['pre_commands'].append(
                    f'ALTER TABLE {full_table} ADD COLUMN '
                    f'"{backup_column_name}" text'
                )
                table_dict['pre_commands'].append(
                    f'UPDATE {full_table} SET '
                    f'"{backup_column_name}" = "{column_name}"::text'
                )

            # Conversion command (with --force or --backup)
            columns_dict[column_name]['command'] = (
                self.db.adapter.struct_alter_column_with_conversion_sql(
                    column_name=column_name,
                    new_sql_type=new_sql_type,
                    conversion_expression=conversion_expression,
                    schema_name=schema_name,
                    table_name=table_name
                )
            )

    def changed_index(self, item=None, changed_attribute=None,
                      oldvalue=None, newvalue=None, **kwargs):
        """Handle changes in an index.

        Two cases:
        - Index name changed: if ``ignore_constraint_name`` is True,
          keeps the old name. Otherwise generates RENAME.
        - Index attributes changed: DROP + CREATE with new attributes.

        Args:
            item: Index dictionary.
            changed_attribute: Changed attribute.
            oldvalue: Previous value.
            newvalue: New value.
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        indexes_dict = table_dict['indexes']
        entity_name = item['entity_name']
        index_attributes = item['attributes']
        if changed_attribute == 'index_name':
            if self.ignore_constraint_name:
                index_attributes['index_name'] = oldvalue
                return
            else:
                sql = f"ALTER INDEX {oldvalue} RENAME TO {newvalue};"
        else:
            new_command = self.createIndexSql(item)
            sql = f'DROP INDEX IF EXISTS {index_attributes["index_name"]};\n{new_command}'
        indexes_dict[entity_name]['command'] = sql

    def changed_relation(self, item=None, changed_attribute=None,
                         oldvalue=None, newvalue=None, **kwargs):
        """Handle changes in a relation (foreign key).

        If only the constraint name changed and ``ignore_constraint_name``
        is True, the change is ignored. Otherwise the FK is recreated
        (DROP + ADD) with new attributes.

        Args:
            item: Relation dictionary.
            changed_attribute: Changed attribute.
            oldvalue: Previous value.
            newvalue: New value.
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        relations_dict = table_dict['relations']
        entity_name = item['entity_name']
        relattr = item['attributes']
        if changed_attribute == 'constraint_name':
            if self.ignore_constraint_name:
                relattr['constraint_name'] = oldvalue
            else:
                relations_dict[f'rem_{entity_name}']['command'] = (
                    f"RENAME CONSTRAINT {oldvalue} TO {newvalue};"
                )
            return

        # Rebuild: DROP old FK + ADD new FK
        add_sql = self.db.adapter.struct_foreign_key_sql(
            fk_name=relattr['constraint_name'],
            columns=relattr['columns'],
            related_table=relattr['related_table'],
            related_schema=relattr['related_schema'],
            related_columns=relattr['related_columns'],
            on_delete=relattr.get('on_delete'),
            on_update=relattr.get('on_update'),
            deferrable=relattr.get('deferrable'),
            initially_deferred=relattr.get('initially_deferred')
        )
        relations_dict[f'rem_{entity_name}']['command'] = (
            self.db.adapter.struct_drop_constraint_sql(
                constraint_name=relattr['constraint_name'],
                schema_name=item['schema_name'],
                table_name=item['table_name'],
            )
        )
        relations_dict[f'add_{entity_name}']['command'] = f"ADD {add_sql}"

    def changed_constraint(self, item=None, changed_attribute=None,
                           oldvalue=None, newvalue=None, **kwargs):
        """Handle changes in a constraint.

        Logic similar to ``changed_relation``: if only the name changed
        and ``ignore_constraint_name`` is True, it is ignored.
        Otherwise: DROP + ADD with new attributes.

        Args:
            item: Constraint dictionary.
            changed_attribute: Changed attribute.
            oldvalue: Previous value.
            newvalue: New value.
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        constraints_dict = table_dict['constraints']
        entity_name = item['entity_name']
        constraint_attr = item['attributes']

        if changed_attribute == 'constraint_name':
            if self.ignore_constraint_name:
                constraint_attr['constraint_name'] = oldvalue
            else:
                constraints_dict[f'rem_{entity_name}']['command'] = (
                    f"RENAME CONSTRAINT {oldvalue} TO {newvalue};"
                )
            return

        add_sql = self.db.adapter.struct_constraint_sql(
            schema_name=item['schema_name'],
            table_name=item['table_name'],
            constraint_name=constraint_attr['constraint_name'],  
            constraint_type=item['attributes']['constraint_type'],
            columns=item['attributes']['columns']
        )
        constraints_dict[f'drop_{entity_name}']['command'] = (
            f"DROP CONSTRAINT {constraint_attr['constraint_name']};"
        )
        constraints_dict[f'add_{entity_name}']['command'] = f"ADD {add_sql}"

    # -------------------------------------------------------------------
    # REMOVED handlers: entity removal
    # -------------------------------------------------------------------
    # Most removals are disabled for safety.
    # Only removed_column actually generates SQL.
    # The removeDisabled flag in the migrator further controls
    # whether removed handlers are called.

    def removed_table(self, item=None, **kwargs):
        """Handler for removed tables. No-op for safety."""
        pass

    def removed_column(self, item=None, **kwargs):
        """Generate the DROP COLUMN command for a removed column.

        This is the only removal handler that generates actual SQL.
        Only called if ``removeDisabled`` is False in the migrator.

        Args:
            item: Column dictionary to remove.
        """
        table_dict = self.schema_tables(item['schema_name'])[item['table_name']]
        entity_name = item['entity_name']
        table_dict['columns'][entity_name]['command'] = f'DROP COLUMN "{entity_name}"'

    def removed_index(self, item=None, **kwargs):
        """Handler for removed indexes. No-op for safety."""
        pass

    def removed_relation(self, item=None, **kwargs):
        """Handler for removed relations. No-op for safety."""
        pass

    def removed_constraint(self, item=None, **kwargs):
        """Handler for removed constraints. No-op for safety."""
        pass

    def removed_extension(self, item=None, **kwargs):
        """Handler for removed extensions. No-op for safety."""
        pass

    def removed_event_trigger(self, item=None, **kwargs):
        """Handler for removed event triggers. No-op for safety."""
        pass

    # -------------------------------------------------------------------
    # SQL generation helpers
    # -------------------------------------------------------------------

    def addColumnUniqueConstraint(self, col):
        """Generate the ADD CONSTRAINT UNIQUE command for a column.

        Creates a UNIQUE constraint with hashed name and adds it
        to the table commands.

        Args:
            col: Column dictionary with schema_name, table_name,
                entity_name.
        """
        table_dict = self.schema_tables(col['schema_name'])[col['table_name']]
        columns = [col['entity_name']]
        constraint_name = hashed_name(
            schema=col['schema_name'], table=col['table_name'],
            columns=columns, obj_type='cst'
        )
        sql = self.db.adapter.struct_constraint_sql(
            constraint_type='UNIQUE',
            constraint_name=constraint_name,
            columns=columns,
            schema_name=col['schema_name'],
            table_name=col['table_name']
        )
        constraints_dict = table_dict['constraints']
        constraints_dict[constraint_name] = {
            "command": f'ADD {sql}'
        }

    def columnSql(self, col):
        """Generate the SQL definition of a column for a CREATE TABLE.

        If the column has a UNIQUE constraint, also calls
        ``addColumnUniqueConstraint`` to add the separate constraint.

        Args:
            col: Column dictionary with entity_name and attributes.

        Returns:
            str: SQL column definition (e.g. ``"name" varchar(100) NOT NULL``).
        """
        colattr = col['attributes']
        if colattr.get('unique'):
            self.addColumnUniqueConstraint(col)
        return self.db.adapter.columnSqlDefinition(
            col['entity_name'],
            dtype=colattr['dtype'],
            size=colattr.get('size'),
            notnull=colattr.get('notnull', False),
            default=colattr.get('sqldefault'),
            extra_sql=colattr.get('extra_sql'),
            generated_expression=colattr.get('generated_expression')
        )

    def createIndexSql(self, index_item):
        """Generate the CREATE INDEX command for an index.

        Delegates to the adapter which generates database-specific SQL,
        including options such as method (btree, gin, gist), WITH options,
        tablespace, UNIQUE and WHERE.

        Args:
            index_item: Index dictionary with schema_name, table_name,
                entity_name and attributes.

        Returns:
            str: Complete CREATE INDEX command.
        """
        attributes = index_item.get("attributes", {})
        return self.db.adapter.struct_create_index_sql(
            schema_name=index_item['schema_name'],
            table_name=index_item['table_name'],
            columns=attributes.get("columns"),
            index_name=index_item['entity_name'],
            method=attributes.get("method"),
            with_options=attributes.get("with_options"),
            tablespace=attributes.get("tablespace"),
            unique=attributes.get('unique'),
            where=attributes.get('where')
        )

    def tableSqlName(self, item=None):
        """Generate the fully qualified SQL name of a table (schema.table).

        Uses the adapter's ``adaptSqlName`` to properly quote
        names (e.g. with double quotes for PostgreSQL).

        Args:
            item: Dictionary with schema_name and table_name.

        Returns:
            str: Qualified table name (e.g. ``"myschema"."mytable"``).
        """
        schema_name = item['schema_name']
        table_name = item['table_name']
        return (
            f'{self.db.adapter.adaptSqlName(schema_name)}'
            f'.{self.db.adapter.adaptSqlName(table_name)}'
        )
