#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Tag Manager - Authorization tag management for users and groups
# Implements feature request #336

class GnrCustomWebPage(object):
    py_requires = """public:Public,
                     gnrcomponents/tag_matrix_grid:TagMatrixGrid"""

    auth_page = '_DEV_,admin,superadmin'
    auth_main = '_DEV_,admin,superadmin'
    pageOptions = {'openMenu': False}

    def main(self, root, **kwargs):
        frame = root.rootBorderContainer(
            datapath='main',
            design='sidebar',
            title='!![en]Authorization Tag Manager'
        )

        # Tabs to switch between Users and Groups
        tc = frame.tabContainer(region='center', margin='5px')

        # Users tab
        self._buildUsersTab(tc)

        # Groups tab
        self._buildGroupsTab(tc)

    def _buildUsersTab(self, tc):
        """Tab for managing user tags."""
        pane = tc.contentPane(title='!![en]User Tags', datapath='.users')

        pane.tagMatrixGrid(
            frameCode='userTagsMatrix',
            source='user_id',
            tag_condition='$isreserved IS NOT TRUE',
            title='!![en]Assign Tags to Users',
            pbl_classes=True,
            margin='10px'
        )

    def _buildGroupsTab(self, tc):
        """Tab for managing group tags."""
        pane = tc.contentPane(title='!![en]Group Tags', datapath='.groups')

        pane.tagMatrixGrid(
            frameCode='groupTagsMatrix',
            source='group_code',
            tag_condition='$isreserved IS NOT TRUE',
            title='!![en]Assign Tags to Groups',
            pbl_classes=True,
            margin='10px'
        )
