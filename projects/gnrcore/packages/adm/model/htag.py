#!/usr/bin/env python
# encoding: utf-8

from gnr.app.gnrapp import AuthTagStruct

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('htag', pkey='id', name_long='!!Tag',
                        rowcaption='$code,$description',caption_field='hierarchical_description',
                        newrecord_caption='!!New tag',hierarchical_caption_field='description',
                        sysRecord_masterfield='hierarchical_code')
        self.sysFields(tbl,hierarchical='code,description',counter=True,sysrecords=True)
        #self.htableFields(tbl)
        #tbl.column('parent_code').relation('htag.code',onDelete='cascade')

        tbl.column('code',name_long='!!Code', validate_notnull=True,
                   validate_nodup=True, unique=True)
        tbl.column('description',name_long='!!Description',validate_notnull=True)
        tbl.column('require_2fa', dtype='B', name_long='Require 2fa')

        tbl.column('isreserved', 'B', name_long='!!Reserved')
        tbl.column('note',name_long='!!Notes')
        tbl.column('linked_table', name_long='Linked table')
        tbl.formulaColumn('authorization_tag','COALESCE($__syscode,$hierarchical_code)')

    def createSysRecords(self,do_update=False):
        self.createSysRecords_(do_update=do_update)
        permissions = AuthTagStruct.makeRoot()

        # Populate the structure for all packages
        for pkg in self.db.packages.keys():
            self.fillPermissions(pkg, permissions)

        # Now iterate over the complete flattened structure and create records
        code_to_id = {}
        for tag_info in permissions.iterFlattenedTags():
            code = tag_info.pop('code')
            description = tag_info.pop('description')
            parent_code = tag_info.pop('parent_code')
            # Resolve parent_id from parent_code
            parent_id = code_to_id.get(parent_code) if parent_code else None

            # Create or get the tag record
            record = self.checkPackageTagRecord(code=code, description=description,
                                         parent_id=parent_id, **tag_info)

            # Store the mapping for children to reference
            code_to_id[code] = record['id']

    def fillPermissions(self, pkg, permissions):
        pkgobj = self.db.package(pkg)

        # Check for packageTags attribute (string format: legacy)
        packageTags_str = pkgobj.attributes.get('packageTags')

        # Check for packageTags method (new hierarchical format)
        has_method = hasattr(pkgobj, 'packageTags') and callable(getattr(pkgobj, 'packageTags'))

        if not packageTags_str and not has_method:
            return
        pkg_branch = permissions.branch(pkg, description=f'Package {pkg}')
        if packageTags_str:
            packageTags_list = packageTags_str.split(',')
            
            for tag_spec in packageTags_list:
                # Handle string format
                code, description = tag_spec.split(':')
                # Legacy format: code is the identifier, description is the human-readable label
                pkg_branch.authTag(label=code, description=description, identifier=code)

        # Handle method format
        if has_method:
            pkgobj.packageTags(pkg_branch)


    def checkPackageTagRecord(self, code=None, description=None, parent_id=None, **kwargs):
        record = self.record(__syscode=code, ignoreMissing=True).output('dict')
        if not record:
            record = self.newrecord(__syscode=code, code=code, description=description,
                                   parent_id=parent_id, **kwargs)
            self.insert(record)
        return record

