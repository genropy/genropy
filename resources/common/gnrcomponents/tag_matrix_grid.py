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
                          datapath=None, pbl_classes=None, **kwargs):
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
        """
        frameCode = frameCode or f'tmg_{id(pane)}'
        datapath = datapath or f'.{frameCode}'
        condition_kwargs = condition_kwargs or {}

        # Get source table info from user_tag FK definition
        user_tag_tbl = self.db.table('adm.user_tag')
        source_col = user_tag_tbl.column(source)
        if not source_col:
            raise ValueError(f"Column '{source}' not found in adm.user_tag")

        # Get related table info
        relation = source_col.relatedTable()
        if not relation:
            raise ValueError(f"Column '{source}' is not a foreign key in adm.user_tag")

        source_table = relation.fullname
        source_tblobj = self.db.table(source_table)
        caption_field = source_tblobj.attributes.get('caption_field') or source_tblobj.pkey
        source_pkey = source_tblobj.pkey

        # Apply pbl_classes styling if requested
        if pbl_classes:
            _custclass = kwargs.get('_class', '')
            kwargs['_class'] = f'pbl_roundedGroup {_custclass}'
            if pbl_classes == '*':
                kwargs['_class'] = f'pbl_roundedGroup noheader {_custclass}'

        # Create frame container
        frame = pane.framePane(frameCode=frameCode, datapath=datapath,
                               center_overflow='hidden', **kwargs)

        # Store configuration in data
        frame.data('.config', Bag(dict(
            source=source,
            source_table=source_table,
            source_pkey=source_pkey,
            caption_field=caption_field,
            source_condition=source_condition,
            tag_condition=tag_condition
        )))

        # Store condition parameters
        for k, v in condition_kwargs.items():
            frame.data(f'.condition_{k}', v)

        # Build the grid structure
        bc = frame.borderContainer(region='center')
        center = bc.contentPane(region='center')

        # Create the includedView grid with AttributesBagRows datamode
        grid = center.includedView(
            nodeId=f'{frameCode}_grid',
            datapath='.grid',
            storepath='.store',
            autoWidth=False,
            _newGrid=True,
            parentFrame=frameCode,
            datamode='attr'
        )
        frame.grid = grid

        # Setup bagStore with AttributesBagRows
        grid.bagStore(storepath='.store', storeType='AttributesBagRows')

        # Add toolbar
        if title:
            if pbl_classes:
                bar = frame.top.slotBar('5,vtitle,*,reloadBtn,5', _class='pbl_roundedGroupLabel')
            else:
                bar = frame.top.slotToolbar('5,vtitle,*,reloadBtn,5')
            bar.vtitle.div(title, _class='frameGridTitle')
        else:
            bar = frame.top.slotToolbar('5,*,reloadBtn,5')

        bar.reloadBtn.slotButton('!!Reload', iconClass='iconbox reload',
                                  action='FIRE .reload;')

        # Setup data loading
        self._tmg_setupDataLoading(frame, frameCode, source, source_table,
                                   source_pkey, caption_field,
                                   source_condition, tag_condition,
                                   condition_kwargs)

        # Setup save handling
        self._tmg_setupSaveHandler(frame, frameCode, source)

        return frame

    def _tmg_setupDataLoading(self, frame, frameCode, source, source_table,
                               source_pkey, caption_field, source_condition,
                               tag_condition, condition_kwargs):
        """Setup data loading controllers for the matrix grid."""

        # Build condition parameters for dataController
        condition_params = {}
        for k, v in condition_kwargs.items():
            if isinstance(v, str) and v.startswith('^'):
                condition_params[k] = v
            else:
                condition_params[f'condition_{k}'] = f'=.condition_{k}'

        # Controller to load data on build or reload
        load_triggers = {'_onBuilt': True, '_fired': '^.reload'}
        load_triggers.update(condition_params)

        frame.dataRpc('.matrixData', self.tmg_loadData,
                      source=source,
                      source_table=source_table,
                      source_pkey=source_pkey,
                      caption_field=caption_field,
                      source_condition=source_condition,
                      tag_condition=tag_condition,
                      **load_triggers,
                      **{f'condition_{k}': f'=.condition_{k}' for k in condition_kwargs})

        # When matrixData changes, update struct and store
        frame.dataController("""
            if(!matrixData){
                return;
            }
            var struct = matrixData.getItem('struct');
            var store = matrixData.getItem('store');
            var tagMap = matrixData.getItem('tagMap');

            SET .grid.struct = struct;
            SET .store = store;
            SET .tagMap = tagMap;
        """, matrixData='^.matrixData')

    def _tmg_setupSaveHandler(self, frame, frameCode, source):
        """Setup save handler for checkbox changes."""

        frame.dataController("""
            if(!_triggerpars || !_triggerpars.kw || !_triggerpars.kw.changedAttr){
                return;
            }
            var changedAttr = _triggerpars.kw.changedAttr;
            if(!changedAttr.startsWith('tag_')){
                return;
            }
            var tagId = changedAttr.substring(4);
            var sourceId = _node.attr._pkey;
            var checked = _node.attr[changedAttr];

            genro.serverCall('tmg_saveChange', {
                source: source,
                source_id: sourceId,
                tag_id: tagId,
                checked: checked
            });
        """, store='^.store', source=source)

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
        Tags are grouped by their parent (theme) creating columnsets.
        """
        struct = self.newGridStruct()
        r = struct.view().rows()

        # First column: entity caption
        r.cell('caption',
               name=caption_field.replace('_', ' ').title(),
               width='15em')

        # Group tags by parent for columnsets
        parent_groups = {}
        root_tags = []
        parent_map = {}  # To look up parent info by id

        for tag in tag_rows:
            parent_id = tag.get('parent_id')
            parent_map[tag['id']] = tag
            if parent_id:
                if parent_id not in parent_groups:
                    parent_groups[parent_id] = []
                parent_groups[parent_id].append(tag)
            else:
                root_tags.append(tag)

        # Process root tags and their children
        for parent_tag in root_tags:
            parent_id = parent_tag['id']
            children = parent_groups.get(parent_id, [])

            if children:
                # Create columnset for this parent theme
                columnset_id = f'cs_{parent_id}'
                cs = r.columnset(code=columnset_id, name=parent_tag['description'])

                # Add child tag columns under this columnset
                for child_tag in children:
                    cs.checkboxcell(
                        f"tag_{child_tag['id']}",
                        name=child_tag['description'],
                        width='5em'
                    )

                    # Also handle grandchildren (second level nesting)
                    grandchildren = parent_groups.get(child_tag['id'], [])
                    for grandchild_tag in grandchildren:
                        cs.checkboxcell(
                            f"tag_{grandchild_tag['id']}",
                            name=grandchild_tag['description'],
                            width='5em'
                        )
            else:
                # Root tag without children - add directly
                r.checkboxcell(
                    f"tag_{parent_tag['id']}",
                    name=parent_tag['description'],
                    width='5em'
                )

        return struct

    @public_method
    def tmg_saveChange(self, source=None, source_id=None, tag_id=None, checked=None):
        """
        Save a single tag assignment change.

        Performs INSERT when checked=True, DELETE when checked=False.
        """
        user_tag_tbl = self.db.table('adm.user_tag')

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
