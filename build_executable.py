"""
Build script for creating standalone executables with PyInstaller.
Run: python build_executable.py
"""

import PyInstaller.__main__
import sys
import os

# PyInstaller options
options = [
    'dbsample/cli.py',  # Main script
    '--name=dbsample',  # Executable name
    '--onefile',  # Create single executable file
    '--console',  # Console application
    '--clean',  # Clean PyInstaller cache before building
    
    # Include hidden imports (if PyInstaller misses them)
    '--hidden-import=psycopg',
    '--hidden-import=psycopg.binary',
    '--hidden-import=click',
    '--hidden-import=yaml',
    '--hidden-import=gzip',
    
    # Collect all submodules
    '--collect-all=psycopg',
    '--collect-all=click',
    
    # Add data files if needed (example configs)
    # Note: Use ';' separator on Windows, ':' on Linux/Mac
    f'--add-data=example_config.json{os.pathsep}.',
    f'--add-data=example_config.yaml{os.pathsep}.',
    
    # Icon (optional - create an .ico file for Windows)
    # '--icon=icon.ico',
    
    # Version info (optional - create version.txt)
    # '--version-file=version.txt',
    
    # Exclude unnecessary modules to reduce size
    '--exclude-module=tkinter',
    '--exclude-module=matplotlib',
    '--exclude-module=numpy',
    '--exclude-module=pandas',
    '--exclude-module=PIL',
    
    # Additional options
    '--noconfirm',  # Overwrite output directory without asking
]

if __name__ == '__main__':
    print("Building standalone executable with PyInstaller...")
    print("This may take a few minutes...")
    PyInstaller.__main__.run(options)

