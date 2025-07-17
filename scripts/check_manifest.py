#!/usr/bin/env python3
"""
Manifest check script for Agent Data Langroid project.
Verifies that key files and directories exist and are properly structured.
"""

import os
import sys
from pathlib import Path

def check_manifest():
    """Check that all required files and directories exist."""
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    required_files = [
        "pyproject.toml",
        "README.md",
        "requirements.txt",
        ".pre-commit-config.yaml",
        "agent_data/__init__.py",
    ]
    
    required_directories = [
        "agent_data",
        "tests",
        "tools",
        "vector_store",
    ]
    
    missing_files = []
    missing_dirs = []
    
    print("Checking manifest...")
    
    # Check required files
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
            print(f"❌ Missing file: {file_path}")
        else:
            print(f"✅ Found: {file_path}")
    
    # Check required directories
    for dir_path in required_directories:
        if not Path(dir_path).is_dir():
            missing_dirs.append(dir_path)
            print(f"❌ Missing directory: {dir_path}")
        else:
            print(f"✅ Found: {dir_path}/")
    
    # Check pyproject.toml structure
    try:
        import tomllib
        with open("pyproject.toml", "rb") as f:
            pyproject_data = tomllib.load(f)
        
        required_sections = ["project", "build-system", "tool.pytest.ini_options"]
        for section_path in required_sections:
            keys = section_path.split('.')
            current = pyproject_data
            try:
                for key in keys:
                    current = current[key]
                print(f"✅ Found pyproject.toml section: {section_path}")
            except KeyError:
                print(f"❌ Missing pyproject.toml section: {section_path}")
                missing_files.append(f"pyproject.toml[{section_path}]")
    except Exception as e:
        print(f"❌ Error reading pyproject.toml: {e}")
        missing_files.append("pyproject.toml (readable)")
    
    # Summary
    print("\n" + "="*50)
    if missing_files or missing_dirs:
        print(f"❌ Manifest check FAILED")
        print(f"Missing files: {len(missing_files)}")
        print(f"Missing directories: {len(missing_dirs)}")
        return False
    else:
        print("✅ Manifest check PASSED")
        print("All required files and directories found.")
        return True

if __name__ == "__main__":
    success = check_manifest()
    sys.exit(0 if success else 1) 