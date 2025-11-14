# DBStores Storetable Feature Branch Setup

## Branch Status

**Branch:** `feature/refactor-dbstores-storetable`
**Base:** `develop`
**Status:** Created, awaiting commit cherry-picks

## Commits to Include

The following commits from `feature/remove-dbstores-config` should be cherry-picked into this branch:

```
df0d8a7f2 - dbstores handler changes (Sept 9, 2025)
982c0fb18 - auxdbstores in instance (Sept 10, 2025)
8bc38e8e0 - Improves cache and store handling; adds union dict (Sept 10, 2025)
d38ea9561 - Refactors DB adapter to use unified raw_fetch API (Sept 10, 2025)
adbb26e00 - Refactors storetable handling for multidb package (Sept 15, 2025)
0d999c1af - Improves dbstore activation logic and selector access (Sept 15, 2025)
1da4073f5 - Improves multi-db store activation and migration sync (Sept 16, 2025)
bbb0fe483 - pref handler multidb_pref (Sept 16, 2025)
9b0d2c011 - storetable (Sept 25, 2025)
```

## Cherry-Pick Commands

Due to conflicts between develop and the feature branch, cherry-picking needs to be done with conflict resolution:

```bash
git checkout feature/refactor-dbstores-storetable

# Cherry-pick commits one at a time, resolving conflicts
git cherry-pick df0d8a7f2
# If conflicts: resolve, then: git cherry-pick --continue

git cherry-pick 982c0fb18
# If conflicts: resolve, then: git cherry-pick --continue

git cherry-pick 8bc38e8e0
# If conflicts: resolve, then: git cherry-pick --continue

git cherry-pick d38ea9561
# If conflicts: resolve, then: git cherry-pick --continue

git cherry-pick adbb26e00
# If conflicts: resolve, then: git cherry-pick --continue

git cherry-pick 0d999c1af
# If conflicts: resolve, then: git cherry-pick --continue

git cherry-pick 1da4073f5
# If conflicts: resolve, then: git cherry-pick --continue

git cherry-pick bbb0fe483
# If conflicts: resolve, then: git cherry-pick --continue

git cherry-pick 9b0d2c011
# If conflicts: resolve, then: git cherry-pick --continue
```

## Alternative: Interactive Rebase

If cherry-picking becomes too complex, consider:

```bash
# Create branch from the original feature branch at the last dbstores commit
git checkout -b feature/refactor-dbstores-storetable 9b0d2c011

# Interactive rebase to remove multidomain commits
git rebase -i develop

# In the editor, remove (delete lines for) all commits that are not dbstores-related
# Save and close
```

## Files Modified by DBStores Refactoring

Primary files changed:
- `gnrpy/gnr/sql/gnrsql.py` - Store initialization and management
- `gnrpy/gnr/sql/adapters/_gnrbaseadapter.py` - Adapter improvements
- `gnrpy/gnr/app/gnrapp.py` - Application-level store loading
- `gnrpy/gnr/core/gnrdict.py` - UnionDict utility
- `gnrpy/gnr/web/gnrwebapp.py` - Web app integration
- `gnrpy/gnr/web/gnrwsgisite.py` - Site-level changes
- `projects/gnrcore/packages/multidb/lib/storetable.py` - New module
- `projects/gnrcore/packages/multidb/main.py` - Package updates
- `gnrpy/tests/sql/test_gnrsql.py` - Test updates

## Documentation

Documentation for this feature is in:
- `DBSTORES_STORETABLE_REFACTOR.md` - Technical documentation
- `DBSTORES_STORETABLE_REFACTOR_TICKET.md` - Implementation ticket

These should be added to this branch after cherry-picking code commits.

## Next Steps

1. Cherry-pick the commits listed above (with conflict resolution)
2. Add documentation files to the branch
3. Test that all dbstores functionality works
4. Create PR to merge into develop
5. After merge, rebase multidomain-workspace branch on updated develop

## Testing Checklist

After cherry-picking, verify:
- [ ] Application starts without errors
- [ ] Storetable loads from database
- [ ] Store connections work correctly
- [ ] Multidb package initializes properly
- [ ] All tests pass: `pytest gnrpy/tests/sql/test_gnrsql.py`
- [ ] No multidomain-specific code included

## Notes

- This branch contains ONLY the dbstores storetable refactoring
- Multidomain functionality is in separate branch: `feature/multidomain-workspace`
- The multidomain branch depends on this one being merged first
- Cherry-pick conflicts are expected due to develop's evolution
- Take care to preserve commit messages and authorship
