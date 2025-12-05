# -*- coding: utf-8 -*-
#
# TagMatrixGrid component for contextual authorization management
# Created for feature request #336
#
# This component provides a reusable grid for managing authorization tags
# on homogeneous entities (users, groups, project members, etc.) with
# support for pluggable contexts via optional foreign keys on adm.user_tag.

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrwebstruct import struct_method
from gnr.core.gnrdecorator import extract_kwargs, public_method
from gnr.core.gnrbag import Bag


class TagMatrixGrid(BaseComponent):
    """
    Component for managing authorization tags in a matrix/pivot grid format.

    Each grid instance works with a single homogeneous entity type.
    The source column is NEVER mixed - it's either users OR groups OR
    memberships OR assignments, etc. - always one type per grid instance.

    Usage examples:

    # Users page - global tags (only users)
    pane.tagMatrixGrid(
        frameCode='userTags',
        source='user_id',
        tag_condition="$isreserved IS NOT TRUE"
    )

    # Groups page - group template tags (only groups)
    pane.tagMatrixGrid(
        frameCode='groupTags',
        source='group_code'
    )

    # Project page - contextual member tags (only members of this project)
    pane.tagMatrixGrid(
        frameCode='memberTags',
        source='member_id',
        source_condition='$project_id=:pr_id',
        condition_pr_id='^#FORM.pkey',
        tag_condition="$hierarchical_code LIKE 'proj.%'"
    )
    """

    py_requires = 'gnrcomponents/framegrid:FrameGrid'

    @extract_kwargs(condition=True)
    @struct_method
    def tmg_tagMatrixGrid(self, pane, frameCode=None, source=None,
                          source_condition=None, tag_condition=None,
                          condition_kwargs=None, title=None,
                          datapath=None, pbl_classes=None,
                          visible_columnsets=None, **kwargs):
        """
        Main entry point for TagMatrixGrid component.

        Parameters:
            frameCode: Unique identifier for the frame
            source: FK column name in user_tag (without $).
                   The related table and its caption_field are derived
                   automatically from the FK definition.
                   Examples: 'user_id', 'group_code', 'member_id'
            source_condition: Optional WHERE clause to filter source rows
                   Example: '$project_id=:pr_id'
            tag_condition: Optional WHERE clause to filter which tags to show
                   Example: "$hierarchical_code LIKE 'proj.%'"
            condition_*: Named parameters usable in both source_condition
                   and tag_condition
                   Example: condition_pr_id='^#FORM.pkey'
            title: Optional title for the grid frame
            datapath: Data path for the component (default: .{frameCode})
            pbl_classes: If True, apply pbl_roundedGroup styling
            visible_columnsets: Comma-separated list of columnset codes to show initially,
                   or '*' for all (default). Example: 'theme1,theme2'
        """
        frameCode = frameCode or f'tmg_{id(pane)}'
        datapath = datapath or f'.{frameCode}'
        condition_kwargs = condition_kwargs or {}

        # Get source table info from user_tag FK definition
        user_tag_tbl = self.db.table('adm.user_tag')
        source_col = user_tag_tbl.column(source)
        if source_col is None:
            raise ValueError(f"Column '{source}' not found in adm.user_tag. "
                           f"Available columns: {list(user_tag_tbl.columns.keys())}")

        # Get related table info
        relation = source_col.relatedTable()
        if relation is None:
            raise ValueError(f"Column '{source}' is not a foreign key in adm.user_tag")

        source_table = relation.fullname
        source_tblobj = relation.dbtable
        caption_field = source_tblobj.attributes.get('caption_field') or source_tblobj.pkey
        source_pkey = source_tblobj.pkey

        # Create bagGrid frame with AttributesBagRows datamode
        frame = pane.bagGrid(
            frameCode=frameCode,
            datapath=datapath,
            storepath='.store',
            datamode='attr',
            title=title,
            pbl_classes=pbl_classes,
            addrow=False,
            delrow=False,
            searchOn=True,
            _anchor=True,
            **kwargs
        )

        # Store configuration in data
        frame.data('.config', Bag(dict(
            source=source,
            source_table=source_table,
            source_pkey=source_pkey,
            caption_field=caption_field,
            source_condition=source_condition,
            tag_condition=tag_condition
        )))

        # Add toolbar buttons: columnset filter and reload
        bar = frame.top.bar.replaceSlots('#', '#,columnsetFilter,reloadBtn,5')
        bar.reloadBtn.slotButton('!!Reload', iconClass='iconbox reload',
                                  action='FIRE .reload;')

        # Columnset visibility filter (tooltipPane with checkboxText)
        filterBtn = bar.columnsetFilter.div( _class='iconbox filter',
                                                    tip='!!Show/hide tag groups')
        tp = filterBtn.tooltipPane()
        fb = tp.div(padding='10px').formbuilder(cols=1, border_spacing='3px')
        fb.checkboxText(value='^.visibleColumnsets',
                        values='^.columnsetOptions',
                        cols=1,
                        popup=False,
                        codeSeparator='|')

        # Setup data loading
        self._tmg_setupDataLoading(frame, source, source_table,
                                   source_pkey, caption_field,
                                   source_condition, tag_condition,
                                   condition_kwargs,
                                   visible_columnsets)

        # Setup save handling
        self._tmg_setupSaveHandler(frame, source)

        return frame

    def _tmg_setupDataLoading(self, frame, source, source_table,
                               source_pkey, caption_field, source_condition,
                               tag_condition, condition_kwargs,
                               visible_columnsets):
        """Setup data loading controllers for the matrix grid."""
        if not condition_kwargs:
            condition_kwargs['_onBuilt'] = True

        # Initialize visible columnsets ('*' means all, or specific comma-separated list)
        frame.dataRpc('.matrixData', self.tmg_loadData,
                      source=source,
                      source_table=source_table,
                      source_pkey=source_pkey,
                      caption_field=caption_field,
                      source_condition=source_condition,
                      tag_condition=tag_condition,
                      _default_visible_columnsets=visible_columnsets or '*',
                      _reload='^.reload',
                      _onResult="""
                                  const struct = result.getItem('struct');
                                   const store = result.getItem('store');
                                   const tagMap = result.getItem('tagMap');
                                   const columnsets = struct.getItem('info.columnsets');
                                   // Extract columnset options for visibility filter
                                   if(columnsets){
                                       let options = [];
                                       let codes = [];
                                       columnsets.forEach(function(n){
                                           let code = n.attr.code;
                                           options.push(code + '|' + n.attr.name);
                                           codes.push(code);
                                       });
                                       SET .columnsetOptions = options.join(',');
                                       // If visible_columnsets is '*', set all visible
                                       let currentVisible = GET .visibleColumnsets;
                                       if(!(this._loaded_once || currentVisible)){
                                           currentVisible = kwargs._default_visible_columnsets=='*'?codes.join(','):kwargs._default_visible_columnsets;
                                           SET .visibleColumnsets = currentVisible;
                                       }
                                   }

                                   SET .grid.struct = struct;
                                   SET .store = store;
                                   SET .tagMap = tagMap;
                                   this._loaded_once = true;
                                   """,
                      **condition_kwargs)

    def _tmg_setupSaveHandler(self, frame, source):
        """Setup save handler for checkbox changes with multi-selection support."""

        # Handle checkbox changes - apply to all selected rows
        frame.dataController("""
            if(!_triggerpars || !_triggerpars.kw){
                return;
            }
            const kw = _triggerpars.kw;
            if(kw.reason == 'tmg_multiselect' || !kw.changedAttr){
                return;
            }
            const changedAttr = kw.changedAttr;
            if(!changedAttr.startsWith('tag_')){
                return;
            }
            const tagId = changedAttr.substring(4);
            const clickedPkey = _node.attr._pkey;
            const checked = _node.attr[changedAttr];

            // Get selected pkeys from grid
            const selectedPkeys = grid.getSelectedPkeys() || [];
            let sourceIds = [];
            const storebag = grid.storebag();

            if(selectedPkeys.length > 1 && selectedPkeys.includes(clickedPkey)){
                // Multiple selection - apply to all selected rows
                sourceIds = selectedPkeys;
                const selectedRowsIdx = grid.getSelectedRowidx() || [];
                selectedRowsIdx.forEach(function(rowIdx){
                    const rowPath = '#' + grid.absIndex(rowIdx);
                    const sep = grid.datamode=='bag'? '.':'?';
                    // Update store for all selected rows with reason to avoid re-trigger
                    storebag.setItem(rowPath + sep + changedAttr, checked, null, {doTrigger:'tmg_multiselect'});
                });
            } else {
                // Single row
                sourceIds.push(clickedPkey);
            }

            // Save to server
            genro.serverCall(rpcmethod, {
                source: source,
                source_ids: sourceIds,
                tag_id: tagId,
                checked: checked
            });
        """, store='^.store', source=source, grid=frame.grid.js_widget,
            rpcmethod=self.tmg_saveChanges)

    @public_method
    def tmg_loadData(self, source=None, source_table=None, source_pkey=None,
                     caption_field=None, source_condition=None, tag_condition=None,
                     **kwargs):
        """
        Load pivot data for the matrix grid.

        Returns a Bag with:
        - struct: Grid structure with dynamic tag columns
        - store: Data rows with source entities and tag checkboxes
        - tagMap: Mapping of tag_id to tag info
        """
        # Extract condition values from kwargs (condition_* parameters)
        condition_values = {k.replace('condition_', ''): v
                           for k, v in kwargs.items()
                           if k.startswith('condition_')}

        # Load source entities (users, groups, members, etc.)
        source_tblobj = self.db.table(source_table)
        source_where = None
        source_params = {}

        if source_condition:
            # Convert :param to proper query parameters
            source_where = source_condition.replace('$', '')
            for param, value in condition_values.items():
                source_where = source_where.replace(f':{param}', f':{param}')
                source_params[param] = value

        source_query = source_tblobj.query(
            columns=f'${source_pkey},${caption_field}',
            where=source_where,
            order_by=f'${caption_field}',
            **source_params
        )
        source_rows = source_query.fetch()

        # Load tags (hierarchical)
        htag_tbl = self.db.table('adm.htag')
        tag_where = None
        tag_params = {}

        if tag_condition:
            tag_where = tag_condition.replace('$', '')
            for param, value in condition_values.items():
                tag_where = tag_where.replace(f':{param}', f':{param}')
                tag_params[param] = value

        tag_query = htag_tbl.query(
            columns='$id,$code,$description,$hierarchical_code,$parent_id',
            where=tag_where,
            order_by='$hierarchical_code',
            **tag_params
        )
        tag_rows = tag_query.fetch()

        # Load existing user_tag assignments
        user_tag_tbl = self.db.table('adm.user_tag')
        assignments_query = user_tag_tbl.query(
            columns=f'${source},$tag_id',
            where=f'${source} IS NOT NULL'
        )
        assignments = assignments_query.fetch()

        # Build assignment lookup: {source_id: set(tag_ids)}
        assignment_map = {}
        for assignment in assignments:
            source_id = assignment[source]
            tag_id = assignment['tag_id']
            if source_id not in assignment_map:
                assignment_map[source_id] = set()
            assignment_map[source_id].add(tag_id)

        # Build grid structure
        struct = self._tmg_buildStruct(tag_rows, caption_field)

        # Build store data
        store = Bag()
        for row in source_rows:
            row_id = row[source_pkey]
            row_data = {
                '_pkey': row_id,
                'caption': row[caption_field]
            }

            # Add tag checkbox values
            assigned_tags = assignment_map.get(row_id, set())
            for tag in tag_rows:
                tag_id = tag['id']
                row_data[f'tag_{tag_id}'] = tag_id in assigned_tags

            store.setItem(str(row_id), None, **row_data)

        # Build tag map for reference
        tagMap = Bag()
        for tag in tag_rows:
            tagMap.setItem(tag['id'], Bag(dict(
                code=tag['code'],
                description=tag['description'],
                hierarchical_code=tag['hierarchical_code'],
                parent_id=tag['parent_id']
            )))

        return Bag(dict(struct=struct, store=store, tagMap=tagMap))

    def _tmg_buildStruct(self, tag_rows, caption_field):
        """Build the grid structure with dynamic tag columns grouped by parent.

        Uses the newGridStruct API to properly build the struct with checkboxcell support.

        Logic: Only leaf nodes (tags without children) are shown as checkboxes.
        Columnsets are created for the immediate parents of leaf nodes (the nodes
        just before the leaves in the hierarchy).
        """
        struct = self.newGridStruct()
        r = struct.view().rows()

        # First column: entity caption
        r.cell('caption',
               name=caption_field.replace('_', ' ').title(),
               width='15em',
               sort='a')

        # Build lookup structures
        tag_by_id = {tag['id']: tag for tag in tag_rows}
        children_of = {}  # parent_id -> [child_tags]

        for tag in tag_rows:
            parent_id = tag.get('parent_id')
            if parent_id:
                if parent_id not in children_of:
                    children_of[parent_id] = []
                children_of[parent_id].append(tag)

        # Identify leaf nodes (tags that have no children)
        leaf_tags = [tag for tag in tag_rows if tag['id'] not in children_of]

        # Identify leaf parents (immediate parents of leaves)
        # These are the nodes that will become columnsets
        leaf_parent_ids = set()
        for leaf in leaf_tags:
            parent_id = leaf.get('parent_id')
            if parent_id:
                leaf_parent_ids.add(parent_id)

        # Group leaves by their parent
        leaves_by_parent = {}
        orphan_leaves = []  # Leaves without a parent (root-level leaves)

        for leaf in leaf_tags:
            parent_id = leaf.get('parent_id')
            if parent_id:
                if parent_id not in leaves_by_parent:
                    leaves_by_parent[parent_id] = []
                leaves_by_parent[parent_id].append(leaf)
            else:
                orphan_leaves.append(leaf)

        # Create columnsets for leaf parents, sorted by hierarchical_code
        sorted_parent_ids = sorted(
            leaf_parent_ids,
            key=lambda pid: tag_by_id[pid]['hierarchical_code'] if pid in tag_by_id else ''
        )

        for parent_id in sorted_parent_ids:
            parent_tag = tag_by_id.get(parent_id)
            if not parent_tag:
                continue

            columnset_code = parent_tag['code']
            # Use .#parent to go up from .grid to the frame datapath
            hidden = f"^.#parent.visibleColumnsets?=!(#v||'').split(',').includes('{columnset_code}')"
            cs = r.columnset(code=columnset_code, name=parent_tag['description'])

            # Add leaf children as checkboxes, sorted by hierarchical_code
            children = sorted(leaves_by_parent[parent_id],
                            key=lambda t: t['hierarchical_code'])
            for child_tag in children:
                cs.checkboxcell(
                    f"tag_{child_tag['id']}",
                    name=child_tag['description'],
                    width='5em',
                    hidden=hidden
                )

        # Add orphan leaves (root-level tags without children) directly
        orphan_leaves.sort(key=lambda t: t['hierarchical_code'])
        for leaf_tag in orphan_leaves:
            r.checkboxcell(
                f"tag_{leaf_tag['id']}",
                name=leaf_tag['description'],
                width='5em'
            )

        return struct

    @public_method
    def tmg_saveChanges(self, source=None, source_ids=None, tag_id=None, checked=None):
        """
        Save tag assignment changes for one or more source entities.

        Performs INSERT when checked=True, DELETE when checked=False.
        Supports batch operations on multiple selected rows.
        """
        user_tag_tbl = self.db.table('adm.user_tag')

        for source_id in source_ids:
            # Check if assignment exists
            existing = user_tag_tbl.query(
                where=f'${source}=:source_id AND $tag_id=:tag_id',
                source_id=source_id,
                tag_id=tag_id
            ).fetch()

            if checked and not existing:
                # INSERT new assignment
                new_record = user_tag_tbl.newrecord(**{
                    source: source_id,
                    'tag_id': tag_id
                })
                user_tag_tbl.insert(new_record)
            elif not checked and existing:
                # DELETE existing assignment
                user_tag_tbl.delete(existing[0])

        self.db.commit()
        return True
