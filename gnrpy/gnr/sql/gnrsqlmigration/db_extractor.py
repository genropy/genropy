"""
db_extractor.py - Database structure extraction from the actual database
=========================================================================

This module contains the :class:`DbExtractor` class, responsible for
reading the **actual** structure of the PostgreSQL database and producing
a normalized JSON structure identical in format to the one produced
by :class:`OrmExtractor`.

Extraction flow
----------------

The extraction proceeds in this order::

    DbExtractor.get_json_struct(schemas)
        |
        +-- prepare_json_struct(schemas)
            |
            +-- get_info_from_db(schemas)
            |   |  <- Opens DB connection
            |   +-- adapter.struct_get_schema_info()    -> columns and types
            |   +-- adapter.struct_get_constraints()    -> PK, UNIQUE, FK
            |   +-- adapter.struct_get_indexes()        -> indexes
            |   +-- adapter.struct_get_extensions()     -> installed extensions
            |   +-- adapter.struct_get_event_triggers() -> DDL event triggers
            |      <- Closes DB connection
            |
            +-- For each returned data block:
                +-- process_base_structure()   -> schemas/tables/columns
                +-- process_constraints()      -> PK, UNIQUE, FK
                +-- process_indexes()          -> indexes
                +-- process_extensions()       -> extensions
                +-- process_event_triggers()   -> event triggers

Adapter interaction
--------------------

The DbExtractor does not execute SQL directly. It delegates everything to the
**adapter** (``self.db.adapter``), which is the database-specific abstraction
(PostgreSQL, SQLite, etc.). The adapter provides ``struct_get_*`` methods
that query system tables (``information_schema``, ``pg_catalog``, etc.)
and return already normalized data.

Constraint handling
--------------------

Constraints are processed by type:

- **PRIMARY KEY**: sets ``pkeys`` on the table and marks PK columns
  with ``notnull='_auto_'`` (no explicit NOT NULL needed).

- **UNIQUE on single column**: converted to a ``unique=True`` attribute
  on the column (does not remain as a separate constraint). If the column
  coincides with the pkey, it is ignored.

- **Multi-column UNIQUE**: remains as a separate constraint in the JSON structure.

- **FOREIGN KEY**: processed via ``process_table_relations()``
  and inserted in the table's ``relations`` section.

- **CHECK**: currently not handled (silently ignored).

Index handling
---------------

Indexes are filtered: those with an associated ``constraint_type``
(e.g. indexes automatically created by PK or UNIQUE) are skipped,
because they are already represented by the corresponding constraint.

Non-existing database
----------------------

If the database does not exist yet (``GnrNonExistingDbException``),
``get_info_from_db()`` returns ``False`` and the resulting JSON structure
will be empty (``{}``). In this case the comparison with the ORM will
produce commands for the complete database creation.
"""

from gnr.dev.decorator import time_measure
from gnr.sql.gnrsql_exceptions import GnrNonExistingDbException, GnrSqlConnectionException

from .structures import (
    COL_JSON_KEYS,
    new_structure_root, new_schema_item, new_table_item,
    new_column_item, new_constraint_item, new_relation_item,
    new_index_item, new_extension_item, new_event_trigger_item,
    nested_defaultdict, clean_attributes
)


class DbExtractor(object):  # REVIEW: old-style (object) base class — unnecessary in Python 3
    """Extract the database structure from the actual PostgreSQL instance.

    Queries the database via the adapter to obtain the actual definition
    of schemas, tables, columns, constraints, indexes, extensions
    and event triggers. Produces a JSON dictionary in the same format
    used by :class:`OrmExtractor`.

    Args:
        migrator: SqlMigrator instance (optional). Provides the reference
            to the database.
        db: GnrSqlDb database object. If not provided, taken from the migrator.

    Attributes:
        json_structure: The resulting JSON dictionary with the DB structure.
        conn: Database connection (opened during extraction, closed after).
    """

    col_json_keys = COL_JSON_KEYS

    def __init__(self, migrator=None, db=None):
        self.migrator = migrator
        self.db = db or self.migrator.db
        self.conn = None

    def connect(self):
        """Open a connection to the database via the adapter.

        The connection is used for introspection queries
        and closed afterwards via :meth:`close_connection`.
        """
        self.conn = self.db.adapter.connect()

    def close_connection(self):
        """Close the database connection if open."""
        if self.conn:
            self.conn.close()

    def get_json_struct(self, schemas=None):
        """Generate and return the JSON structure of the database.

        Main method of the extractor. Delegates to ``prepare_json_struct``
        and returns the result.

        Args:
            schemas: List of schemas to inspect. If None, the structure
                will be empty.

        Returns:
            dict: JSON structure of the database, or ``{}`` if the DB doesn't exist.
        """
        self.prepare_json_struct(schemas=schemas)
        return self.json_structure

    @time_measure
    def prepare_json_struct(self, schemas=None):
        """Prepare the JSON structure by querying the database.

        Executes introspection queries via the adapter and processes
        the results with the ``process_*`` methods. Uses the
        ``@time_measure`` decorator to measure execution time.

        If the database doesn't exist, sets ``json_structure`` to ``{}``.

        Args:
            schemas: List of schemas to inspect.
        """
        self.json_structure = new_structure_root(self.db.get_dbname())
        self.json_meta = nested_defaultdict()
        self.json_schemas = self.json_structure["root"]['schemas']
        infodict = self.get_info_from_db(schemas=schemas)
        if infodict is False:  # REVIEW: {} is also falsy — if get_info_from_db returns {} this path is skipped
            self.json_structure = {}
            return
        for k, v in infodict.items():
            getattr(self, f'process_{k}')(v, schemas=schemas)

    def get_info_from_db(self, schemas=None):
        """Query the database to obtain all structural information.

        Opens a connection, executes introspection queries via the
        adapter and closes the connection in the ``finally`` block.

        If the database doesn't exist (``GnrNonExistingDbException``),
        returns ``False``.

        The executed queries are:
        - ``struct_get_schema_info``: columns with types, nullable, defaults
        - ``struct_get_constraints``: PK, UNIQUE, FK, CHECK
        - ``struct_get_indexes``: all indexes
        - ``struct_get_extensions``: installed PostgreSQL extensions
        - ``struct_get_event_triggers``: DDL event triggers

        Args:
            schemas: List of schemas to inspect.

        Returns:
            dict: Dictionary with keys ``base_structure``, ``constraints``,
            ``indexes``, ``extensions``, ``event_triggers``.
            Or ``False`` if the database doesn't exist.
        """
        result = {}
        try:
            self.connect()
            if schemas:
                adapter = self.db.adapter
                result["base_structure"] = adapter.struct_get_schema_info(schemas=schemas)
                result["constraints"] = adapter.struct_get_constraints(schemas=schemas)
                result["indexes"] = adapter.struct_get_indexes(schemas=schemas)
                result['extensions'] = adapter.struct_get_extensions()
                result['event_triggers'] = adapter.struct_get_event_triggers()
        except GnrNonExistingDbException:
            result = False
        except GnrSqlConnectionException:
            raise
        finally:
            self.close_connection()
        return result

    def process_base_structure(self, base_structure, schemas=None):
        """Process base information: schemas, tables and columns.

        Each record in ``base_structure`` contains column metadata
        with special fields prefixed with ``_pg_``:
        - ``_pg_schema_name``: schema name
        - ``_pg_table_name``: table name
        - ``_pg_is_nullable``: 'YES' or 'NO'
        - ``name``: column name

        The remaining fields are column attributes (dtype, size, etc.)
        filtered via ``COL_JSON_KEYS``.

        Handles the case of schemas present in the ``schemas`` list but empty
        in the database: these are removed from the final structure.

        Args:
            base_structure: List of dictionaries, one per DB column.
            schemas: List of expected schemas.
        """
        # Pre-initialize all schemas to None to track empty ones
        for schema_name in schemas:
            self.json_schemas[schema_name] = None

        for c in base_structure:
            schema_name = c.pop('_pg_schema_name')
            table_name = c.pop('_pg_table_name')
            is_nullable = c.pop('_pg_is_nullable')
            column_name = c.pop('name')
            colattr = {
                k: v for k, v in c.items()
                if k in self.col_json_keys and v is not None
            }
            if not self.json_schemas[schema_name]:
                self.json_schemas[schema_name] = new_schema_item(schema_name)
            if table_name and table_name not in self.json_schemas[schema_name]["tables"]:
                self.json_schemas[schema_name]["tables"][table_name] = (
                    new_table_item(schema_name, table_name)
                )
            if column_name:
                if is_nullable == 'NO':
                    colattr['notnull'] = True
                col_item = new_column_item(
                    schema_name, table_name, column_name, attributes=colattr
                )
                self.json_schemas[schema_name]["tables"][table_name]["columns"][column_name] = col_item

        # Remove schemas that exist in the list but are empty in the DB
        for schema_name in schemas:
            if not self.json_schemas[schema_name]:
                self.json_schemas.pop(schema_name)

    def process_constraints(self, constraints_dict, schemas=None):
        """Process all constraints extracted from the database.

        The ``constraints_dict`` dictionary is organized by table:
        the key is a tuple ``(schema_name, table_name)`` and the value
        is a dictionary of constraints grouped by type.

        Processing happens in this order:

        1. **PRIMARY KEY**: sets ``pkeys`` on the table and marks
           PK columns with ``notnull='_auto_'``.
        2. **UNIQUE**: if on a single column, becomes a column attribute.
           If multi-column, remains as a separate constraint.
        3. **FOREIGN KEY**: delegated to ``process_table_relations()``.
        4. **CHECK**: currently ignored.

        Args:
            constraints_dict: Dictionary ``{(schema, table): {type: {...}}}``.
            schemas: List of schemas (not used directly here).
        """
        for tablepath, constraints_by_type in constraints_dict.items():
            schema_name, table_name = tablepath
            d = dict(constraints_by_type)
            table_json = self.json_schemas[schema_name]["tables"][table_name]

            # PRIMARY KEY: set pkeys and mark columns as auto-notnull
            primary_key_const = d.pop("PRIMARY KEY", {})
            if primary_key_const:
                pkeys = primary_key_const["columns"]
                table_json['attributes']['pkeys'] = ','.join(pkeys)
                for col in pkeys:
                    table_json['columns'][col]['attributes']['notnull'] = '_auto_'

            # UNIQUE: single column -> attribute, multi-column -> constraint
            unique = d.pop("UNIQUE", {})
            multiple_unique = dict(unique)
            for k, v in unique.items():
                columns = v['columns']
                if len(columns) == 1:
                    # UNIQUE on single column that coincides with pkey -> ignored
                    if columns[0] == table_json['attributes']['pkeys']:
                        continue
                    # UNIQUE on single column -> column attribute
                    multiple_unique.pop(k)
                    self.json_schemas[schema_name]["tables"][table_name][
                        'columns'][columns[0]]['attributes']['unique'] = True

            # FOREIGN KEY -> delegate to process_table_relations
            self.process_table_relations(
                schema_name, table_name, d.pop('FOREIGN KEY', {})
            )

            # Multi-column UNIQUE -> separate constraint
            for multiple_unique_const in multiple_unique.values():
                const_item = new_constraint_item(
                    schema_name, table_name,
                    multiple_unique_const['columns'],
                    constraint_type='UNIQUE',
                    constraint_name=multiple_unique_const['constraint_name']
                )
                table_json['constraints'][const_item['entity_name']] = const_item
            # CHECK constraints not handled at this time

    def process_table_relations(self, schema_name, table_name, foreign_keys_dict):
        """Process the foreign keys of a table.

        For each FK in the dictionary, creates a relation item with hashed
        name and adds it to the table's ``relations`` section.

        Args:
            schema_name: Name of the schema.
            table_name: Name of the table.
            foreign_keys_dict: Dictionary of FKs with their attributes
                (columns, related_table, related_schema, on_delete, etc.).
        """
        relations = self.json_schemas[schema_name]["tables"][table_name]['relations']
        for entity_attributes in foreign_keys_dict.values():
            constraint_name = entity_attributes.pop('constraint_name', None)
            relation_item = new_relation_item(
                schema_name, table_name,
                columns=entity_attributes['columns'],
                attributes=entity_attributes,
                constraint_name=constraint_name
            )
            relations[relation_item['entity_name']] = relation_item

    def process_indexes(self, indexes_dict, schemas=None):
        """Process indexes extracted from the database.

        Filters indexes that have an associated ``constraint_type``
        (automatically created by PK or UNIQUE) because they are already
        represented by the corresponding constraint.

        The ``indexes_dict`` dictionary is organized by table:
        ``{(schema, table): {index_name: {columns, method, ...}}}``.

        Args:
            indexes_dict: Dictionary of indexes by table.
            schemas: List of schemas (not used directly).
        """
        for tablepath, index_dict in indexes_dict.items():
            schema_name, table_name = tablepath
            d = dict(index_dict)
            table_json = self.json_schemas[schema_name]["tables"][table_name]
            for index_name, index_attributes in d.items():
                # Skip indexes automatically created by constraints (PK, UNIQUE)
                if index_attributes.get('constraint_type'):
                    continue
                indexed_columns = list(index_attributes['columns'].keys())
                index_item = new_index_item(
                    schema_name, table_name,
                    columns=indexed_columns,
                    attributes=index_attributes,
                    index_name=index_name
                )
                table_json['indexes'][index_item['entity_name']] = index_item

    def process_extensions(self, extensions, **kwargs):
        """Process installed PostgreSQL extensions.

        Filters out extensions from the ``pg_catalog`` schema which are
        always present and not relevant for migration.

        Args:
            extensions: Dictionary ``{extension_name: {schema_name, ...}}``.
        """
        for extension_name, extension_dict in extensions.items():
            if extension_dict.get('schema_name') == 'pg_catalog':
                continue
            extension_dict = clean_attributes(extension_dict)  # REVIEW: reassigns local var — original info lost before storing in json_meta
            extension_item = new_extension_item(extension_name)
            self.json_meta['root']['extension'] = extension_dict
            self.json_structure["root"]['extensions'][extension_name] = extension_item

    def process_event_triggers(self, event_triggers, **kwargs):
        """Process DDL event triggers of the database.

        Event triggers respond to events such as CREATE TABLE,
        ALTER TABLE, DROP TABLE at the database level (not table level).

        Args:
            event_triggers: Dictionary ``{trigger_name: {attributes}}``.
        """
        for event_trigger_name, event_trigger_dict in event_triggers.items():
            event_trigger_item = new_event_trigger_item(event_trigger_name)
            event_trigger_item['attributes'].update(event_trigger_dict)
            self.json_structure["root"]['event_triggers'][event_trigger_name] = event_trigger_item
