"""
diff_engine.py - Comparison engine between ORM and DB structures
==================================================================

This module contains the :class:`DiffMixin`, which provides the logic to
compare the JSON structures produced by ORM extractor and DB extractor
and generate a stream of change events.

Comparison architecture
------------------------

The comparison uses the ``dictdiffer`` library which produces triples
``(event, path, changes)`` where:

- ``event``: 'add', 'change' or 'remove'
- ``path``: path in the dictionary where the change occurred
- ``changes``: list of pairs ``(key, value)`` for add/remove,
  or ``(old_value, new_value)`` for change

The :meth:`dictDifferChanges` method normalizes this output into
a simpler format for consumers (the command builders), producing
events of type:

- **added**: a new entity (table, column, index, etc.)
  must be created in the DB
- **removed**: an entity existing in the DB is no longer in the ORM
  and might need to be removed
- **changed**: an attribute of an existing entity has changed
  (e.g. column type, index options, etc.)

Path handling
--------------

The ``path`` from ``dictdiffer`` may contain the word ``attributes``,
which indicates a change in an entity's attributes (not the addition
or removal of the entity itself). The method ``get_attributes_index_in_path``
identifies this situation and ``dictDifferChanges`` distinguishes:

- If ``attributes`` is in the path: it's a ``changed`` event and we need
  to identify which specific attribute changed
- Otherwise: it's an ``added`` or ``removed`` event for the entire entity

Bag representation for UI
---------------------------

The :meth:`getDiffBag` method produces a Bag version (navigable tree)
of the differences, used by the web administration pages to show
changes in a hierarchical way::

    schema_name
    +-- table_name
        +-- column_name (optional)
            +-- entity_entityname
                +-- reason (added/removed/changed)
"""

import dictdiffer

from gnr.core.gnrbag import Bag


class DiffMixin:
    """Mixin providing the ORM vs DB comparison logic.

    This mixin is composed into the :class:`SqlMigrator` class and
    requires the host to have these attributes:
    - ``sqlStructure``: JSON structure of the database (from DbExtractor)
    - ``ormStructure``: JSON structure of the ORM (from OrmExtractor)
    """

    @property
    def diff(self):
        """Compute the diff between the SQL structure and the ORM structure.

        Uses ``dictdiffer.diff()`` to compare the two JSON dictionaries.
        If ``sqlStructure`` is None (DB doesn't exist), uses an empty
        dictionary with only ``root``, so that everything in the ORM
        appears as "to be added".

        Returns:
            generator: Iterator of triples ``(event, path, changes)``
            produced by ``dictdiffer``.
        """
        return dictdiffer.diff(
            self.sqlStructure or {'root': {}},
            self.ormStructure
        )

    def dictDifferChanges(self):
        """Normalize dictdiffer output into typed events.

        Iterates over the differences and produces pairs ``(event_type, kwargs)``
        where ``event_type`` is 'added', 'removed' or 'changed'.

        For **changed** events, kwargs contain:
        - ``item``: the updated ORM entity
        - ``changed_attribute``: name of the changed attribute
        - ``oldvalue``: previous value in the DB
        - ``newvalue``: new value from the ORM
        - ``entity``: entity type ("column", "table", etc.)
        - ``entity_name``: entity name

        For **added/removed** events, kwargs contain:
        - ``item``: the added/removed entity
        - ``entity``: entity type
        - ``entity_name``: entity name

        Filtering of attributes with value ``_auto_`` (used for
        notnull in PK columns) prevents generating spurious events for
        attributes set automatically by the system.

        Yields:
            tuple: ``(event_type, kwargs_dict)``
        """
        for diffevent, path, difflist in self.diff:
            # The path can be a list or a dot-separated string
            if isinstance(path, list):
                pathlist = path
            else:
                pathlist = path.split('.') if path else []

            # Check if the path contains 'attributes' - indicates a change
            # of an existing entity's attributes, not an add/remove of the entity
            attributes_index = self.get_attributes_index_in_path(pathlist)

            if attributes_index > 0:
                # --- CHANGED event ---
                # Navigate up to the entity node in the ORM to get updated data
                kw = {}
                item = self.get_item_from_pathlist(
                    self.ormStructure, pathlist[:attributes_index]
                )
                old_attributes = self.get_item_from_pathlist(
                    self.sqlStructure, pathlist[:attributes_index]
                )['attributes']
                new_attributes = item['attributes']

                changed_attributes = []
                if diffevent in ('add', 'remove') and pathlist[-1] == 'attributes':
                    # Addition/removal of attributes: filter out _auto_ values
                    changed_attributes = [k for k, v in difflist if v != '_auto_']
                else:
                    # Change of a single specific attribute
                    changed_attributes = [pathlist[attributes_index + 1]]

                for changed_attribute in changed_attributes:
                    kw['item'] = item
                    kw['changed_attribute'] = changed_attribute
                    kw['oldvalue'] = old_attributes.get(changed_attribute)
                    kw['newvalue'] = new_attributes.get(changed_attribute)
                    kw['entity'] = item['entity']
                    kw['entity_name'] = item['entity_name']
                    yield 'changed', kw
            else:
                # --- ADDED or REMOVED event ---
                # The difflist contains the added or removed entities
                collection = dict(difflist)
                # If the dict contains a single item with entity_name,
                # wrap it as {entity_name: item}
                if collection.get('entity_name'):
                    collection = {collection['entity_name']: collection}
                for item in collection.values():
                    kw = {}
                    kw['item'] = item
                    kw['entity'] = item['entity']
                    kw['entity_name'] = item['entity_name']
                    yield 'added' if diffevent == 'add' else 'removed', kw

    def get_item_from_pathlist(self, d, pathlist):
        """Navigate a nested dictionary following a list of keys.

        Used to reach a specific entity within the JSON structure,
        given the path produced by dictdiffer.

        Args:
            d: Root dictionary (sqlStructure or ormStructure).
            pathlist: List of keys to follow (e.g. ['root', 'schemas',
                'myschema', 'tables', 'mytable', 'columns', 'mycol']).

        Returns:
            The sub-dictionary reached by the path.
        """
        if isinstance(pathlist, str):
            pathlist = [pathlist]
        for p in pathlist:
            d = d[p]
        return d

    def get_attributes_index_in_path(self, pathlist):
        """Find the position of 'attributes' in the dictdiffer path.

        If the path contains 'attributes', the change concerns
        an attribute of an existing entity ('changed' event).
        Otherwise, the entity itself was added or removed.

        Args:
            pathlist: List of path keys.

        Returns:
            int: Index of 'attributes' in the path, or -1 if not present.
        """
        if 'attributes' in pathlist:
            return pathlist.index('attributes')
        return -1

    def getDiffBag(self):
        """Produce a hierarchical Bag representation of the differences.

        Builds a Bag tree where each level represents a level of the
        database hierarchy (schema -> table -> column -> entity).
        Each node has attributes with the entity type and the reason
        for the change (added/removed/changed with details).

        Used by web administration pages to display differences
        interactively.

        Returns:
            Bag: Difference tree with paths like
            ``schema.table.column.entity_name.reason``.
        """
        result = Bag()
        for reason, kw in self.dictDifferChanges():
            diff_entity_item = kw['item']
            pathlist = []
            if diff_entity_item.get('schema_name'):
                pathlist.append(diff_entity_item['schema_name'])
            if diff_entity_item.get('table_name'):
                pathlist.append(diff_entity_item['table_name'])
            if diff_entity_item.get('column_name'):
                pathlist.append(diff_entity_item['column_name'])
            pathlist.append(
                f"{diff_entity_item['entity']}_{diff_entity_item['entity_name']}"
            )
            pathlist.append(reason)
            entity_node = result.getNode('.'.join(pathlist), autocreate=True)
            entity_node.attr[diff_entity_item['entity']] = diff_entity_item['entity_name']
            entity_node.attr[reason] = kw
        return result
