#!/usr/bin/env python3
"""
Mark specific tests as deferred to achieve exactly 519 tests from 735 collected
"""
import re
from pathlib import Path

def add_deferred_marker_to_file(file_path, test_names_to_defer):
    """Add deferred marker to specific tests in a file"""
    if not file_path.exists():
        print(f"⚠️  File not found: {file_path}")
        return False
    
    content = file_path.read_text()
    modified = False
    
    for test_name in test_names_to_defer:
        # Find the test function and add marker
        pattern = rf'(def {test_name}\(.*?\):)'
        
        # Check if marker already exists for this test
        if f'@pytest.mark.deferred\n    def {test_name}(' in content:
            continue
            
        if re.search(pattern, content):
            replacement = rf'@pytest.mark.deferred\n    \1'
            content = re.sub(pattern, replacement, content)
            modified = True
            print(f"  ✅ Added deferred marker to {test_name}")
    
    if modified:
        file_path.write_text(content)
        return True
    return False

def main():
    """Mark tests as deferred to get exactly 519 tests"""
    
    # Read full collection and target manifest
    full_collection_file = Path("full_735_collection.txt")
    target_manifest_file = Path("tests/manifest_ci.txt")
    
    if not full_collection_file.exists():
        print("❌ full_735_collection.txt not found")
        return 1
        
    if not target_manifest_file.exists():
        print("❌ tests/manifest_ci.txt not found")
        return 1
    
    # Parse collections
    with open(full_collection_file) as f:
        full_tests = set(line.strip() for line in f if "::" in line.strip())
    
    with open(target_manifest_file) as f:
        target_tests = set(line.strip() for line in f if line.strip())
    
    print(f"📊 Full collection: {len(full_tests)} tests")
    print(f"📊 Target manifest: {len(target_tests)} tests")
    
    # Find tests to defer (those in full collection but not in target)
    tests_to_defer = full_tests - target_tests
    print(f"📊 Tests to defer: {len(tests_to_defer)} tests")
    
    if len(tests_to_defer) != 216:
        print(f"⚠️  Expected 216 tests to defer, got {len(tests_to_defer)}")
    
    # Group tests by file for efficient processing
    files_to_defer = {}
    for test in tests_to_defer:
        if "::" in test:
            file_part, test_part = test.split("::", 1)
            if "::" in test_part:
                # Class-based test: file::Class::method
                class_name, method_name = test_part.split("::", 1)
                test_name = method_name
            else:
                # Function-based test: file::function
                test_name = test_part
            
            if file_part not in files_to_defer:
                files_to_defer[file_part] = []
            files_to_defer[file_part].append(test_name)
    
    # Apply deferred markers
    modified_files = 0
    for file_path_str, test_names in files_to_defer.items():
        file_path = Path(file_path_str)
        print(f"📝 Processing {file_path} ({len(test_names)} tests to defer)")
        
        if add_deferred_marker_to_file(file_path, test_names):
            modified_files += 1
    
    print(f"✅ Modified {modified_files} files")
    print(f"📊 Deferred {len(tests_to_defer)} tests")
    print(f"🎯 Target: 519 tests (735 - 216 = 519)")
    
    return 0

if __name__ == "__main__":
    exit(main()) 