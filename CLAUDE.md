## Language

All project outputs (issues, PRs, commit messages, code comments, documentation) MUST be written in English.

## No LLM References (CRITICAL)

**NEVER include any reference to LLM, AI, Claude, or any AI assistant in ANY output.**

This applies to:
- Commit messages (NO `Co-Authored-By: Claude`, NO mentions of AI)
- Pull request descriptions
- Code comments
- Documentation
- Any other text that will be persisted or shared

This is a contractual obligation. Violations can cause serious problems.

## Pre-PR / Pre-Push Quality Checks (CRITICAL)

**ALWAYS run quality checks BEFORE proposing a commit, PR or push.**

Before any commit/PR/push, verify MANDATORY:

1. **flake8** (or the linter configured in the project) — zero errors
   - Unused imports
   - Unused variables
   - Syntax errors
   - Style violations
2. **Full test suite** — all tests must pass (excluding documented pre-existing failures)
3. **No imports from CLI modules** — CLI files are interface only, NEVER import logic from them
4. **Separation of concerns** — logic goes in library modules, CLI is just wiring
5. **Clean imports** — no unused imports, no unnecessary runtime imports

**Pre-PR checklist**:
```
- [ ] flake8 passes with zero errors on modified files
- [ ] All tests pass
- [ ] No unused imports
- [ ] Logic in the right place (library, not CLI)
- [ ] Obsolete files removed
```

**NEVER** create a PR with:
- Unused imports (e.g. `import pytest` not used)
- Logic in CLI files that should be in library
- Tests that import from CLI modules
- Duplicate files not removed

**This rule exists because trivial errors like these waste reviewer time and show lack of care. The reviewer should not find errors that a linter would have caught.**

## Real Tests, Not Cosmetic Mocks (CRITICAL)

**NEVER create tests that mock the entire stack when the suite provides infrastructure for real database tests.**

Mocks should be used **only** to isolate external dependencies (network APIs, remote filesystem, third-party services). If the project has test infrastructure with temporary databases (sqlite, postgres), tests MUST use it.

**NEVER**:
- Mock `insert()`, `query()`, `commit()` and then declare "48 tests pass"
- Create MagicMock of tables, columns, records that hide real errors
- Test only internal logic without ever touching the database
- Consider a test "passed" if it doesn't exercise the real code

**ALWAYS**:
- Use the project's test infrastructure (fixture `db`, temporary databases)
- Test end-to-end flow: data generation -> insert -> verify in DB
- If a table has required fields, triggers, counters — the test MUST go through them
- If a test passes with MagicMock but fails on a real instance, the test is **useless**

**Why**: A test on MagicMock that passes while real code throws `KeyError: 'data'` is not a test — it's an illusion. The reviewer wastes time discovering nothing actually works. Cosmetic mocks are worse than no tests, because they give false confidence.
