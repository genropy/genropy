"""
orm_extractor.py - ORM model structure extraction
===================================================

This module contains the :class:`OrmExtractor` class, responsible for
reading table definitions from the **Genropy ORM model** and producing
a normalized JSON structure.

Extraction flow
----------------

The extraction proceeds in this order::

    OrmExtractor.get_json_struct()
        |
        +-- For each package (= SQL schema):
        |   +-- fill_json_package(pkgobj)
        |       +-- For each table in the package:
        |           +-- fill_json_table(tblobj)
        |               +-- fill_json_column(colobj)
        |               |   +-- convert_colattr()  -> normalizes dtype/size
        |               +-- fill_json_relations_and_indexes(colobj)
        |                   +-- fill_json_relation()  -> foreign key
        |                   +-- fill_json_column_index()  -> index
        |
        +-- add_tenant_schemas()  -> replicate multi-tenant tables
        |
        +-- Deferred indexes (deferred_indexes)
        |   +-- fill_json_column_index() for related columns not in pkey
        |
        +-- Auto-detected extensions from columns

Key concepts
-------------

- **Package -> Schema**: each Genropy package corresponds to a PostgreSQL schema.
  The package's ``sqlname`` becomes the schema name.

- **Multi-tenant**: tables with ``multi_tenant=True`` are replicated in
  additional tenant schemas. The list of tenant schemas comes from the migrator.

- **Deferred indexes**: when a column has a FK relation to a column that is not
  part of the related table's primary key, the index on the related column is
  created at the end (after processing all packages), because the target table
  might not have been processed yet.

- **Composite columns**: columns defined with ``composed_of`` that group
  multiple physical columns (e.g. for composite FK or multi-column UNIQUE).

Dtype and size normalization
-----------------------------

The ``convert_colattr()`` function normalizes Genropy types::

    ORM dtype  -> Normalized dtype
    X, Z, P    -> T (text)
    size "10"  -> dtype C (char), size "10"
    size "5:20"-> dtype A (varchar range), size "0:20" (min normalized)
    size "10,2"-> dtype N (numeric), size "10,2"
    A/C without size -> T (text, char without length is impossible)
"""

from gnr.core.gnrdict import dictExtract
from gnr.core.gnrstring import boolean

from .structures import (
    COL_JSON_KEYS, GNR_DTYPE_CONVERTER, DTYPE_INDEX_CONFIG,
    new_structure_root, new_schema_item, new_table_item,
    new_column_item, new_constraint_item, new_relation_item,
    new_index_item, new_extension_item,
    nested_defaultdict, camel_to_snake, hashed_name
)


class OrmExtractor:
    """Extract the database structure from the Genropy ORM model.

    Navigates the tree of packages and tables defined in the ORM and
    produces a normalized JSON dictionary with the same structure
    used by :class:`DbExtractor`, so they can be compared
    by ``dictdiffer``.

    Args:
        migrator: SqlMigrator instance (optional). Provides the reference
            to the database and the ``excludeReadOnly`` flag.
        db: GnrSqlDb database object. If not provided, taken from the migrator.
        extensions: List of required PostgreSQL extensions (optional).

    Attributes:
        json_structure: The resulting JSON dictionary with the complete structure.
        tenant_schema_tables: Map fullname->tblobj of multi-tenant tables,
            used to replicate them in tenant schemas.
        deferred_indexes: List of indexes to create at the end of extraction,
            for related columns that are not part of the target table's pkey.
    """

    col_json_keys = COL_JSON_KEYS

    def __init__(self, migrator=None, db=None, extensions=None):
        self.migrator = migrator
        self.excludeReadOnly = migrator and migrator.excludeReadOnly
        self.db = db or self.migrator.db
        self.json_structure = new_structure_root(self.db.get_dbname())
        self.json_meta = nested_defaultdict()
        self.extensions = extensions or []
        self.schemas = self.json_structure['root']['schemas']
        self.tenant_schema_tables = {}
        self.deferred_indexes = []

    def fill_json_package(self, pkgobj):
        """Process an ORM package and its tables.

        Creates the schema corresponding to the package and iterates over
        all tables in the package, also detecting those marked as multi-tenant.

        Args:
            pkgobj: Genropy package object with ``sqlname`` attribute and
                ``tables`` dictionary.
        """
        schema_name = pkgobj.sqlname
        self.schemas[schema_name] = new_schema_item(schema_name)
        for tblobj in pkgobj.tables.values():
            self.fill_json_table(tblobj)
            if tblobj.multi_tenant:
                self.tenant_schema_tables[tblobj.fullname] = tblobj

    def fill_json_extension(self, extension_name):
        """Register a PostgreSQL extension in the JSON structure.

        Extensions are detected automatically during column processing:
        if a column has an attribute that corresponds to an extension
        (e.g. ``uuid-ossp``), it is added to the list.

        Args:
            extension_name: Name of the PostgreSQL extension.
        """
        self.json_structure['root']['extensions'][extension_name] = (
            new_extension_item(extension_name)
        )

    def fill_json_table(self, tblobj, tenant_schema=None):
        """Process an ORM table and all its columns.

        Creates the table item in the JSON structure, sets the primary key,
        then iterates over all columns (both simple and composite) to
        extract definitions, relations and indexes.

        Args:
            tblobj: Genropy table object.
            tenant_schema: If specified, the table is created in this
                schema (for multi-tenant support) instead of the package schema.
        """
        schema_name = tenant_schema or tblobj.pkg.sqlname
        table_name = tblobj.sqlname

        # Build the pkeys string by joining the sqlnames of the primary columns
        pkeys = (
            ','.join([tblobj.column(col).sqlname for col in tblobj.pkeys])
            if tblobj.pkeys else None
        )
        table_entity = new_table_item(schema_name, table_name)
        table_entity['attributes']['pkeys'] = pkeys
        self.schemas[schema_name]['tables'][table_name] = table_entity

        # Simple columns: definition + relations/indexes
        for colobj in tblobj.columns.values():
            self.fill_json_column(colobj, tenant_schema=tenant_schema)
            self.fill_json_relations_and_indexes(colobj, tenant_schema=tenant_schema)

        # Composite columns: only relations/indexes + multi-column UNIQUE constraint
        for compositecol in tblobj.composite_columns.values():
            self.fill_json_relations_and_indexes(compositecol, tenant_schema=tenant_schema)
            self.fill_multiple_unique_constraint(compositecol, tenant_schema=tenant_schema)

    def fill_json_column(self, colobj, tenant_schema=None):
        """Process a single ORM column and add it to the JSON structure.

        Handles:
        - Auto-detection of extensions from column attributes
        - Attribute normalization (dtype, size) via convert_colattr()
        - Size min:max normalization (min is zeroed to avoid spurious diffs)
        - notnull='_auto_' flag for primary key columns
        - Removal of unique/indexed for primary key columns (PK already creates an index)

        Args:
            colobj: Genropy column object.
            tenant_schema: Alternative tenant schema (for multi-tenant).
        """
        table_name = colobj.table.sqlname
        schema_name = tenant_schema or colobj.table.pkg.sqlname
        colattr = colobj.attributes

        # Detect required PostgreSQL extensions from column attributes
        for auto_ext_attribute in self.db.adapter.struct_auto_extension_attributes():
            if colattr.get(auto_ext_attribute) and auto_ext_attribute not in self.extensions:
                self.extensions.append(auto_ext_attribute)

        # Detect required PostgreSQL extensions from column dtype
        dtype_extensions = self.db.adapter.struct_dtype_required_extensions()
        col_dtype = colattr.get('dtype', '')
        if col_dtype in dtype_extensions:
            ext_name = dtype_extensions[col_dtype]
            if ext_name not in self.extensions:
                self.extensions.append(ext_name)

        attributes = self.convert_colattr(colattr)

        # Normalize size with min:max format.
        # When min is not 0, we force it to 0 to prevent the comparison
        # with the DB (which doesn't know the min) from always flagging a change.
        # We can't use just the max because that would convert varchar to char.
        if ":" in attributes.get('size', '') and not attributes.get('size').startswith('0'):
            attributes['size'] = f"0:{attributes['size'].split(':')[1]}"

        table_json = self.schemas[schema_name]['tables'][table_name]
        column_name = colobj.sqlname
        pkeys = table_json['attributes']['pkeys']

        # Primary key columns are automatically NOT NULL
        # and don't need a separate index (PK already creates one).
        # For single-column PKs, unique is also redundant (PK implies uniqueness).
        # For composite PKs, individual columns may still need their own
        # UNIQUE constraint (issue #576).
        if pkeys and (column_name in pkeys.split(',')):
            attributes['notnull'] = '_auto_'
            if ',' not in pkeys:
                attributes.pop('unique', None)
            attributes.pop('indexed', None)

        column_entity = new_column_item(
            schema_name, table_name, column_name, attributes=attributes
        )
        table_json['columns'][colobj.sqlname] = column_entity

    def fill_json_relations_and_indexes(self, colobj, tenant_schema=None):
        """Process FK relations and indexes for a column.

        For each column checks:
        1. If it has a joiner (FK relation) -> creates the relation and marks
           the column as indexed (FKs must have an index for performance)
        2. If the related column is not in primary key -> adds a deferred
           index on the related column
        3. If it has ``indexed`` or ``unique`` attribute -> creates the index

        Primary key columns don't receive additional indexes (PK already creates one).

        Args:
            colobj: Genropy column object.
            tenant_schema: Alternative tenant schema.
        """
        colattr = colobj.attributes
        joiner = colobj.relatedColumnJoiner()
        indexed = colattr.get('indexed') or colattr.get('unique')
        dtype_index_config = DTYPE_INDEX_CONFIG.get(colattr.get('dtype'))
        if not indexed and dtype_index_config and dtype_index_config.get('required'):
            indexed = True
        table_name = colobj.table.sqlname
        schema_name = tenant_schema or colobj.table.pkg.sqlname
        table_json = self.schemas[schema_name]['tables'][table_name]
        pkeys = table_json['attributes']['pkeys']
        is_in_pkeys = pkeys and (colobj.name in pkeys.split(','))

        if joiner:
            # FKs always have an index to optimize JOINs
            indexed = indexed or True  # REVIEW: always evaluates to True — original indexed value from colattr is discarded
            relation_info = self._relation_info_from_joiner(
                colobj, joiner, tenant_schema=tenant_schema
            )
            related_to_pkeys = relation_info.pop('related_to_pkeys')
            rel_colobj = relation_info.pop('rel_colobj')
            if joiner.get('foreignkey'):
                self.fill_json_relation(
                    colobj=colobj, attributes=relation_info,
                    tenant_schema=tenant_schema
                )
            # If the related column is not part of the target table's pkey,
            # an index on the related column is needed for JOIN performance.
            # It is deferred because the target table might not be processed yet.
            if not related_to_pkeys:
                self.deferred_indexes.append({
                    "colobj": rel_colobj,
                    "tenant_schema": tenant_schema
                })

        if indexed and not is_in_pkeys:
            self.fill_json_column_index(
                colobj=colobj, indexed=indexed, tenant_schema=tenant_schema
            )

    def fill_multiple_unique_constraint(self, compositecol, tenant_schema=None):
        """Create a multi-column UNIQUE constraint for a composite column.

        Composite columns with ``unique=True`` attribute generate a
        UNIQUE constraint involving all columns from ``composed_of``.

        Args:
            compositecol: Composite column object with ``composed_of`` attribute.
            tenant_schema: Alternative tenant schema.
        """
        colattr = compositecol.attributes
        if not colattr.get('unique'):
            return
        table_name = compositecol.table.sqlname
        schema_name = tenant_schema or compositecol.table.pkg.sqlname
        table_json = self.schemas[schema_name]['tables'][table_name]
        columns = colattr.get('composed_of').split(',')
        constraint_item = new_constraint_item(
            schema_name, table_name, columns, 'UNIQUE'
        )
        table_json['constraints'][constraint_item['entity_name']] = constraint_item

    def statement_converter(self, command):
        """Convert FK action abbreviations to standard SQL format.

        The Genropy ORM accepts abbreviations for ON DELETE/ON UPDATE
        actions of foreign keys. This function normalizes them to full SQL format.

        Mapping::

            'R' / 'RESTRICT'    -> 'RESTRICT'
            'C' / 'CASCADE'     -> 'CASCADE'
            'N' / 'NO ACTION'   -> 'NO ACTION'
            'SN' / 'SETNULL'    -> 'SET NULL'
            'SD' / 'SETDEFAULT' -> 'SET DEFAULT'

        Args:
            command: Abbreviation or full name of the FK action.

        Returns:
            str or None: FK action in standard SQL format, or None if empty.
        """
        if not command:
            return None
        command = command.upper()
        if command in ('R', 'RESTRICT'):
            return 'RESTRICT'
        elif command in ('C', 'CASCADE'):
            return 'CASCADE'
        elif command in ('N', 'NO ACTION'):
            return 'NO ACTION'
        elif command in ('SN', 'SETNULL', 'SET NULL'):
            return 'SET NULL'
        elif command in ('SD', 'SETDEFAULT', 'SET DEFAULT'):
            return 'SET DEFAULT'
        # REVIEW: returns None implicitly for unknown commands — silent data loss

    def _relation_info_from_joiner(self, colobj, joiner, tenant_schema=None):
        """Extract FK relation information from the ORM joiner.

        The joiner is a dictionary describing the relation between columns.
        It contains keys like ``onDeleteSql``, ``onUpdateSql`` (in camelCase)
        that are converted to snake_case (``on_delete``, ``on_update``).

        Also handles:
        - Resolution of the related table and column
        - Multi-tenant support (if the related table is multi-tenant,
          uses the tenant schema)
        - Detection of whether the related column is part of the pkey
          (for deferred indexes)
        - Support for deferrable/initially_deferred relations

        Args:
            colobj: Source column object of the relation.
            joiner: Joiner dictionary with relation information.
            tenant_schema: Alternative tenant schema.

        Returns:
            dict: Relation information with keys ``on_delete``,
            ``on_update``, ``related_columns``, ``related_table``,
            ``related_schema``, ``deferrable``, ``initially_deferred``,
            ``related_to_pkeys`` (bool), ``rel_colobj`` (related column object).
        """
        # Convert keys ending with _sql from camelCase to snake_case
        # e.g. onDeleteSql -> on_delete, with normalized value
        result = {
            camel_to_snake(k[0:-4]): self.statement_converter(v)
            for k, v in joiner.items() if k.endswith('_sql')
        }
        related_field = joiner['one_relation']
        related_table, related_column = related_field.rsplit('.', 1)
        rel_tblobj = colobj.db.table(related_table)
        rel_colobj = rel_tblobj.column(related_column)

        result['related_columns'] = (
            rel_colobj.attributes.get('composed_of') or rel_colobj.name
        ).split(',')
        result['related_table'] = rel_tblobj.model.sqlname

        related_schema = rel_tblobj.pkg.sqlname
        if tenant_schema and rel_tblobj.multi_tenant:
            related_schema = tenant_schema
        result['related_schema'] = related_schema
        result['deferrable'] = joiner.get('deferrable') or joiner.get('deferred')
        result['initially_deferred'] = (
            joiner.get('initially_deferred') or joiner.get('deferred')
        )
        result['related_to_pkeys'] = result['related_columns'] == rel_tblobj.pkeys
        result['rel_colobj'] = rel_colobj
        return result

    def fill_json_relation(self, colobj, attributes=None, tenant_schema=None):
        """Create a relation (foreign key) item in the JSON structure.

        Builds the hashed FK name, populates the necessary attributes
        and adds the relation to the table in the JSON structure.

        Args:
            colobj: Source column object of the FK.
            attributes: Dictionary with relation information
                (related_table, related_schema, on_delete, etc.).
            tenant_schema: Alternative tenant schema.
        """
        columns = (
            colobj.attributes.get('composed_of') or colobj.name
        ).split(',')
        table_name = colobj.table.sqlname
        schema_name = tenant_schema or colobj.table.pkg.sqlname
        hashed_entity_name = hashed_name(
            schema=schema_name, table=table_name,
            columns=columns, obj_type='fk'
        )
        attributes['constraint_name'] = hashed_entity_name
        attributes['columns'] = columns
        attributes['constraint_type'] = "FOREIGN KEY"
        relation_item = new_relation_item(
            schema_name, table_name, columns, attributes=attributes
        )
        table_json = self.schemas[schema_name]['tables'][table_name]
        table_json["relations"][relation_item["entity_name"]] = relation_item

    def fill_json_column_index(self, colobj, indexed=None, tenant_schema=None):
        """Create an index item for a column in the JSON structure.

        If the column has a UNIQUE constraint, the index is not created
        because PostgreSQL automatically creates an index for UNIQUE constraints.

        The ``indexed`` attribute can be:
        - ``True``: simple index without additional options
        - A dictionary with options: ``sorting``, ``with_*``, ``method``, etc.

        Args:
            colobj: Column object to index.
            indexed: True for simple index, or dictionary with options.
            tenant_schema: Alternative tenant schema.
        """
        indexed = {} if indexed is True else dict(indexed)
        dtype_index_config = DTYPE_INDEX_CONFIG.get(colobj.attributes.get('dtype'))
        if dtype_index_config:
            indexed.setdefault('method', dtype_index_config.get('method'))
        if colobj.attributes.get('unique'):
            # The DB automatically creates an index for UNIQUE columns
            return
        with_options = dictExtract(indexed, 'with_', pop=True)
        sorting = indexed.pop('sorting', None)
        columns = (
            colobj.attributes.get('composed_of') or colobj.name
        ).split(',')
        sorting = sorting.split(',') if sorting else [None] * len(columns)
        table_name = colobj.table.sqlname
        schema_name = colobj.table.pkg.sqlname
        if tenant_schema and colobj.table.multi_tenant:
            schema_name = tenant_schema
        attributes = dict(
            columns=dict(zip(columns, sorting)),
            with_options=with_options,
            **indexed
        )
        index_item = new_index_item(
            schema_name, table_name, columns, attributes=attributes
        )
        table_json = self.schemas[schema_name]['tables'][table_name]
        table_json["indexes"][index_item["entity_name"]] = index_item

    def convert_colattr(self, colattr):
        """Normalize ORM column attributes for comparison.

        Applies several normalization rules:

        1. Filters only the keys in ``COL_JSON_KEYS``
        2. Converts dtype via ``GNR_DTYPE_CONVERTER`` (X/Z/P -> T)
        3. Normalizes size with prefix `:` -> `0:`
        4. Determines dtype from size format:
           - `min:max` -> dtype A (varchar with range)
           - number only, text dtype -> dtype C (fixed char)
           - `num,dec` with dtype N -> normalized size
        5. dtype A or C without size -> T (text, char without length is impossible)

        Args:
            colattr: Attribute dictionary from the ORM column.

        Returns:
            dict: Normalized attributes with consistent dtype and size.
        """
        result = {
            k: v for k, v in colattr.items()
            if k in self.col_json_keys and v is not None
        }
        size = result.pop('size', None)
        dtype = result.pop('dtype', None)
        dtype = GNR_DTYPE_CONVERTER.get(dtype, dtype)

        if size:
            if size.startswith(':'):
                size = f'0{size}'
            if ':' in size:
                dtype = 'A'
            elif ',' not in size:
                # Text types with fixed size -> char
                if not dtype or dtype in ('A', 'T', 'X', 'Z', 'P'):
                    dtype = 'C'
                elif dtype == 'N':
                    size = f'{size},0'

        # char/varchar without size makes no sense -> fallback to text
        if dtype in ('A', 'C') and not size:
            dtype = 'T'

        result['dtype'] = dtype
        if size:
            result['size'] = size
        return result

    def get_json_struct(self):
        """Generate the complete JSON structure of the database from the ORM.

        This is the main method of the extractor. It executes in order:

        1. Iterates over all database packages, skipping readOnly ones
           if ``excludeReadOnly`` is active
        2. For each package, extracts tables, columns, relations and indexes
        3. Adds tenant schemas with replicated multi-tenant tables
        4. Processes deferred indexes (for related columns not in pkey)
        5. Registers detected PostgreSQL extensions

        Returns:
            dict: Complete JSON structure with the hierarchy
            root -> schemas -> tables -> columns/relations/indexes/constraints.
        """
        for pkg in self.db.packages.values():
            if self.excludeReadOnly and boolean(pkg.attributes.get('readOnly')):
                continue
            self.fill_json_package(pkg)
        self.add_tenant_schemas()
        for deferred_index_kw in self.deferred_indexes:
            colobj = deferred_index_kw['colobj']
            tenant_schema = deferred_index_kw['tenant_schema']
            self.fill_json_column_index(
                colobj=colobj, indexed=True, tenant_schema=tenant_schema
            )
        for extension_name in self.extensions:
            self.fill_json_extension(extension_name)
        return self.json_structure

    def add_tenant_schemas(self):
        """Add tenant schemas with replicated multi-tenant tables.

        For each tenant schema (obtained from the migrator), creates the
        schema and replicates all tables marked as ``multi_tenant`` from the ORM.
        This allows having identical tables in different schemas for
        per-tenant data isolation.
        """
        if not self.migrator:
            return
        for tenant_schema in self.migrator.tenant_schemas:
            self.schemas[tenant_schema] = new_schema_item(tenant_schema)
            for tblobj in self.tenant_schema_tables.values():
                self.fill_json_table(tblobj, tenant_schema=tenant_schema)
