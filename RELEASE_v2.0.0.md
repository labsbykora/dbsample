# Release v2.0.0 - Project Rename

## Release Date
2025-11-17

## Version
2.0.0

## Type
**Major Release** - Breaking Changes

## Summary

This release renames the project from `pg-sample` to `dbsample` to better reflect its future direction of supporting multiple database systems beyond PostgreSQL.

## ⚠️ BREAKING CHANGES

### What Changed
- **Package name**: `pg-sample` → `dbsample`
- **Command name**: `pg-sample` → `dbsample`
- **Default staging schema**: `_pg_sample` → `_dbsample`
- **Python imports**: `pg_sample.*` → `dbsample.*`

### Migration Required

Users must:
1. Uninstall old package: `pip uninstall pg-sample`
2. Install new package: `pip install dbsample`
3. Update all scripts: Replace `pg-sample` with `dbsample`
4. Update Python imports: `from pg_sample.*` → `from dbsample.*`

See [MIGRATION_GUIDE_v2.0.0.md](MIGRATION_GUIDE_v2.0.0.md) for detailed migration instructions.

## What Stayed the Same

- All functionality remains identical
- Configuration file format unchanged
- Command-line options unchanged (except command name)
- Output format unchanged
- All features from v1.2.0 preserved

## Files Changed

- Package directory renamed: `pg_sample/` → `dbsample/`
- All imports updated throughout codebase
- All documentation updated
- Default staging schema updated
- Version numbers updated to 2.0.0

## Git Commands to Create Release

```bash
# 1. Verify all changes are committed
git status

# 2. Create release commit (if needed)
git add .
git commit -m "Release v2.0.0: Project rename from pg-sample to dbsample

BREAKING CHANGES:
- Package renamed: pg-sample → dbsample
- Command renamed: pg-sample → dbsample
- Default staging schema: _pg_sample → _dbsample
- All imports updated: pg_sample.* → dbsample.*

See CHANGELOG.md and MIGRATION_GUIDE_v2.0.0.md for details."

# 3. Create annotated tag
git tag -a v2.0.0 -m "Release v2.0.0 - Project Rename

BREAKING CHANGES:
- Package renamed: pg-sample → dbsample
- Command renamed: pg-sample → dbsample
- Default staging schema: _pg_sample → _dbsample

This is a major version release due to breaking changes.
Users must uninstall pg-sample and install dbsample.

See CHANGELOG.md for full migration guide."

# 4. Verify tag
git tag -l "v2.0.0"
git show v2.0.0

# 5. Push commits and tag
git push origin main  # or master, depending on your default branch
git push origin v2.0.0
```

## Release Notes for GitHub/GitLab

**Title:** v2.0.0 - Project Rename (Breaking Changes)

**Description:**
```markdown
## 🎉 Release v2.0.0 - Project Rename

### ⚠️ BREAKING CHANGES

This is a **major version release** with breaking changes due to project renaming.

#### What Changed
- **Package name**: `pg-sample` → `dbsample`
- **Command name**: `pg-sample` → `dbsample`
- **Default staging schema**: `_pg_sample` → `_dbsample`
- **Python imports**: `pg_sample.*` → `dbsample.*`

#### Migration Guide

**1. Uninstall old package:**
```bash
pip uninstall pg-sample
```

**2. Install new package:**
```bash
pip install dbsample
```

**3. Update scripts:**
- Replace all `pg-sample` commands with `dbsample`
- Update any Python code: `from pg_sample.*` → `from dbsample.*`

**4. Clean up old staging schemas (optional):**
```sql
DROP SCHEMA IF EXISTS _pg_sample CASCADE;
```

### Why the Rename?

The project has been renamed to `dbsample` to better reflect its future direction:
- Currently supports PostgreSQL
- Designed to support multiple database systems in the future
- More generic name aligns with multi-database vision

### What Stayed the Same

- All functionality remains identical
- Configuration file format unchanged
- Command-line options unchanged (except command name)
- Output format unchanged

### Full Changelog

See [CHANGELOG.md](CHANGELOG.md) for complete details and migration guide.
```

## Verification Checklist

- [x] Version numbers updated to 2.0.0
- [x] All code references updated
- [x] Documentation updated
- [x] CHANGELOG.md updated with breaking changes
- [x] Migration guide created
- [x] Release checklist updated
- [x] No linter errors
- [x] All imports working correctly

## Post-Release Tasks

- [ ] Verify tag is visible on remote
- [ ] Create GitHub/GitLab release with notes
- [ ] Update any CI/CD pipelines
- [ ] Announce release (if applicable)
- [ ] Update any external documentation

