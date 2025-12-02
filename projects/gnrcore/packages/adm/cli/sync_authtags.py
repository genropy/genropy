#!/usr/bin/env python3
"""
sync_authtags.py - Manual synchronization of auth tags from code to database

WHY THIS SCRIPT EXISTS
======================

The createSysRecords method (called during db setup/upgrade) only INSERTS new
auth tags - it never updates existing ones. This is a deliberate design choice:

1. PRODUCTION SAFETY: A running production instance may have customized tag
   descriptions, notes, or other attributes directly in the database to match
   specific customer requirements.

2. NO SILENT OVERWRITES: Framework upgrades should never silently overwrite
   database customizations made by administrators.

3. EXPLICIT CONTROL: When you want to realign database tags with new code
   definitions (e.g., after updating packageTags in a package), you must
   explicitly run this script.

WHEN TO USE THIS SCRIPT
=======================

- After modifying packageTags() definitions in package main.py files
- After adding new auth tags that need to update existing records
- When you want to reset tag descriptions/attributes to code defaults
- During controlled migration/upgrade procedures

USAGE
=====

    # Preview changes without applying them (recommended first step)
    gnr adm sync_authtags instance_name --dry-run

    # Apply changes to database
    gnr adm sync_authtags instance_name

The script will:
- Update existing records (matched by __syscode) with current code definitions
- Create new records for newly defined tags
- Use for_update locking for safe concurrent access
- Show a summary of created/updated records
"""

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import AuthTagStruct

DESCRIPTION = "Synchronize auth tags from code definitions to database"

def main(instance):
    """Update existing auth tag records with current code definitions.

    This script synchronizes the htag table with the packageTags definitions
    in code, updating descriptions, notes, and other attributes for existing tags
    with the same __syscode.

    Usage:
        gnr adm sync_authtags [instance_name] [--dry-run]
    """

    parser = GnrCliArgParse(description=DESCRIPTION)
    parser.add_argument('--dry-run', action='store_true',
                       help='Show changes without applying them')
    args = parser.parse_args()

    htag_table = instance.db.table('adm.htag')
    permissions = AuthTagStruct.makeRoot()

    # Populate the structure for all packages
    for pkg in instance.db.packages.keys():
        htag_table.fillPermissions(pkg, permissions)

    updated_count = 0
    created_count = 0

    # Now iterate and update/create records
    code_to_id = {}
    for tag_info in permissions.iterFlattenedTags():
        code = tag_info.pop('code')
        tag_description = tag_info.pop('description')
        parent_code = tag_info.pop('parent_code')
        tag_info.pop('tag_type')  # Remove tag_type, not needed for DB

        # Resolve parent_id from parent_code
        parent_id = code_to_id.get(parent_code) if parent_code else None

        # Get existing record with for_update lock
        record = htag_table.record(__syscode=code, for_update=True, ignoreMissing=True).output('dict')

        if record:
            # Update only if code matches (code change means different tag)
            # Check if update is needed
            needs_update = False
            update_fields = {}

            if record.get('description') != tag_description:
                update_fields['description'] = tag_description
                needs_update = True

            if parent_id != record.get('parent_id'):
                update_fields['parent_id'] = parent_id
                needs_update = True

            # Check additional attributes (note, isreserved, require_2fa, linked_table, etc.)
            for key, value in tag_info.items():
                if record.get(key) != value:
                    update_fields[key] = value
                    needs_update = True

            if needs_update:
                if args.dry_run:
                    print(f"Would update tag '{code}': {update_fields}")
                else:
                    for key, value in update_fields.items():
                        record[key] = value
                    htag_table.update(record)
                    print(f"Updated tag '{code}'")
                updated_count += 1

            code_to_id[code] = record['id']
        else:
            # Create new record
            if args.dry_run:
                print(f"Would create tag '{code}': {tag_description}")
            else:
                new_record = htag_table.newrecord(
                    __syscode=code,
                    code=code,
                    description=tag_description,
                    parent_id=parent_id,
                    **tag_info
                )
                htag_table.insert(new_record)
                code_to_id[code] = new_record['id']
                print(f"Created tag '{code}'")
            created_count += 1

    if not args.dry_run:
        instance.db.commit()
        print("\nChanges committed successfully.")

    print("\nSummary:")
    print(f"  Created: {created_count}")
    print(f"  Updated: {updated_count}")
    if args.dry_run:
        print("  (dry-run mode - no changes applied)")
