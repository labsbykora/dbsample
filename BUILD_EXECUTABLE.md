# Building Standalone Executable

This guide explains how to create a standalone executable that doesn't require Python to be installed.

## Prerequisites

1. Install PyInstaller:
```bash
pip install pyinstaller
```

2. Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

## Quick Build

### Option 1: Using the build script (Recommended)
```bash
python build_executable.py
```

### Option 2: Using PyInstaller directly
```bash
pyinstaller --onefile --name=dbsample --console dbsample/cli.py
```

### Option 3: Using the spec file (Advanced)
```bash
pyinstaller pyinstaller.spec
```

## Build Options Explained

### `--onefile`
Creates a single executable file. All dependencies are bundled inside.

**Pros:**
- Single file to distribute
- Easy to use

**Cons:**
- Slower startup (extracts to temp directory)
- Larger file size

### `--onedir` (Alternative)
Creates a directory with the executable and dependencies.

**Pros:**
- Faster startup
- Smaller individual files

**Cons:**
- Multiple files to distribute
- More complex distribution

## Output Location

After building, the executable will be in:
- **Windows**: `dist/dbsample.exe`
- **Linux/Mac**: `dist/dbsample`

## Testing the Executable

1. Navigate to the `dist` directory:
```bash
cd dist
```

2. Test the executable:
```bash
# Windows
dbsample.exe --help

# Linux/Mac
./dbsample --help
```

3. Test with a real database:
```bash
dbsample.exe --host localhost --username myuser --dbname mydb --limit "*=10" --file test.sql
```

## Platform-Specific Notes

### Windows
- Creates `dbsample.exe`
- May require Visual C++ Redistributable for psycopg
- File size: ~15-30 MB

### Linux
- Creates `dbsample` (no extension)
- May need to set executable permissions: `chmod +x dbsample`
- File size: ~15-30 MB

### macOS
- Creates `dbsample`
- May need to sign the executable for distribution
- File size: ~15-30 MB

## Troubleshooting

### Issue: "Module not found" errors
**Solution:** Add missing modules to `hiddenimports` in the spec file or build script.

### Issue: Large file size
**Solution:** 
- Use `--exclude-module` to exclude unused modules
- Use `--onedir` instead of `--onefile`
- Use UPX compression (if available)

### Issue: Slow startup
**Solution:** Use `--onedir` instead of `--onefile` for faster startup.

### Issue: psycopg binary issues
**Solution:** Ensure `psycopg[binary]` is installed. PyInstaller should automatically include the binary libraries.

## Advanced Configuration

### Custom Icon
Add to build options:
```bash
--icon=icon.ico  # Windows
--icon=icon.icns  # macOS
```

### Version Information (Windows)
Create a `version.txt` file and add:
```bash
--version-file=version.txt
```

### UPX Compression
Install UPX and PyInstaller will use it automatically if available:
- Download: https://upx.github.io/
- Add to PATH

## Distribution

### Single Executable (--onefile)
- Distribute: `dist/dbsample.exe` (or `dbsample` on Linux/Mac)
- Users just run the executable directly

### Directory Distribution (--onedir)
- Distribute: entire `dist/dbsample/` directory
- Users run: `dbsample/dbsample.exe` (or `dbsample/dbsample`)

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Build executable
  run: |
    pip install pyinstaller
    pyinstaller --onefile --name=dbsample --console dbsample/cli.py
    
- name: Upload artifact
  uses: actions/upload-artifact@v2
  with:
    name: dbsample-${{ runner.os }}
    path: dist/dbsample*
```

## File Size Optimization

The executable will be ~15-30 MB due to:
- Python interpreter (~8-10 MB)
- psycopg binary libraries (~5-10 MB)
- Click and other dependencies (~2-5 MB)

To reduce size:
1. Exclude unused modules
2. Use UPX compression
3. Consider Nuitka for smaller binaries (more complex setup)

## Alternative: Nuitka

For smaller executables and faster startup, consider Nuitka:

```bash
pip install nuitka
python -m nuitka --standalone --onefile dbsample/cli.py
```

**Pros:**
- Smaller executables
- Faster startup
- True compilation to C++

**Cons:**
- More complex setup
- Longer build times
- May require C++ compiler

