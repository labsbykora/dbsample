# Release Checklist for v1.2.0

## Pre-Release Verification

### Version Consistency
- [x] `setup.py` version: 1.2.0
- [x] `pg_sample/__init__.py` version: 1.2.0
- [x] `CHANGELOG.md` has v1.2.0 entry

### Code Quality
- [x] All Python files compile without syntax errors
- [x] No linter errors
- [x] All imports are correct

### Documentation
- [x] README.md updated with new features
- [x] USAGE_GUIDE.md comprehensive and up-to-date
- [x] CHANGELOG.md documents all changes
- [x] Example config files (JSON and YAML) included

### Features
- [x] Gzip compression implemented
- [x] Configuration file support (JSON/YAML)
- [x] Self-test handles compressed files
- [x] PyYAML added to requirements.txt

## Release Steps

### 1. Final Verification
```bash
# Verify all changes are committed
git status

# Review recent commits
git log --oneline -20

# Verify version numbers match
grep -r "version.*1.2.0" setup.py pg_sample/__init__.py
```

### 2. Create Release Commit (if needed)
```bash
# If there are uncommitted changes
git add .
git commit -m "Release v1.2.0: Add gzip compression and configuration file support"
```

### 3. Create Git Tag
```bash
# Create annotated tag
git tag -a v1.2.0 -m "Release v1.2.0

Features:
- Gzip compression support (--compress flag)
- Configuration file support (JSON/YAML)
- Enhanced exclusion documentation
- Self-test handles compressed files
- PyYAML added to requirements

See CHANGELOG.md for full details."

# Verify tag was created
git tag -l "v1.2.0"
git show v1.2.0
```

### 4. Push Tag to Remote
```bash
# Push tag to remote repository
git push origin v1.2.0

# If you also want to push commits
git push origin main  # or master, depending on your default branch
```

### 5. Create Release Notes

Create a release on GitHub/GitLab/etc. with the following:

**Title:** v1.2.0 - Gzip Compression and Configuration Files

**Description:**
```markdown
## 🎉 Release v1.2.0

### New Features

#### Gzip Compression
- `--compress` / `--gzip` flag to compress output files
- Auto-detection: files ending with `.gz` are automatically compressed
- Compressed files show "(compressed)" in verbose output
- Compatible with standard `gunzip` and `zcat` tools
- Self-test automatically handles compressed files

#### Configuration File Support
- `--config` / `-c` flag to specify configuration file
- Supports JSON format (built-in)
- Supports YAML format (PyYAML included in requirements)
- CLI arguments take precedence over config file values
- Key normalization (e.g., `database` → `dbname`, `output` → `file`)
- All CLI options can be specified in config file

### Improvements
- Enhanced exclusion documentation with comprehensive examples
- Self-test now handles compressed SQL files
- PyYAML added to requirements (no longer optional)

### Documentation
- Updated README.md with all exclusion options
- Comprehensive USAGE_GUIDE.md with exclusion examples
- Example configuration files (JSON and YAML)

### Installation

```bash
pip install -e .
```

### Upgrade from v1.1.0

No breaking changes. Simply upgrade:

```bash
pip install --upgrade -e .
```

### Full Changelog

See [CHANGELOG.md](CHANGELOG.md) for complete details.
```

### 6. Post-Release

- [ ] Verify tag is visible on remote
- [ ] Test installation from tag (if applicable)
- [ ] Update any CI/CD pipelines
- [ ] Announce release (if applicable)

## Files Changed in v1.2.0

- `pg_sample/cli.py` - Added compression and config file support
- `pg_sample/config.py` - New file for configuration parsing
- `pg_sample/self_test.py` - Added compressed file handling
- `pg_sample/__init__.py` - Version updated to 1.2.0
- `setup.py` - Version updated to 1.2.0
- `requirements.txt` - Added pyyaml>=6.0.0
- `README.md` - Updated with new features
- `USAGE_GUIDE.md` - Comprehensive exclusion documentation
- `CHANGELOG.md` - v1.2.0 entry added
- `example_config.json` - Example configuration file
- `example_config.yaml` - Example configuration file

## Testing Recommendations

Before releasing, consider testing:
- [ ] Compression with various file sizes
- [ ] Configuration file loading (JSON and YAML)
- [ ] Self-test with compressed files
- [ ] All exclusion options work correctly
- [ ] Installation from clean environment

