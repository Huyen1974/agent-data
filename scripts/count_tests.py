#!/usr/bin/env python3
"""
Simple test counter to count tests by marker category.
Bypasses conftest import issues by directly parsing test files.
"""

import os
import re
import sys
from pathlib import Path

def count_tests_in_file(file_path):
    """Count test functions in a single file and extract their markers."""
    test_count = 0
    markers = set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find all test functions
        test_functions = re.findall(r'def test_\w+\(', content)
        test_count = len(test_functions)
        
        # Find pytest markers
        marker_patterns = [
            r'@pytest\.mark\.(\w+)',
            r'pytestmark\s*=\s*pytest\.mark\.(\w+)',
            r'pytestmark\s*=\s*\[([^\]]+)\]',
        ]
        
        for pattern in marker_patterns:
            marker_matches = re.findall(pattern, content)
            for match in marker_matches:
                if isinstance(match, str):
                    if ',' in match:
                        # Handle list of markers
                        for marker in match.split(','):
                            marker = marker.strip().replace('pytest.mark.', '')
                            if marker:
                                markers.add(marker)
                    else:
                        markers.add(match)
        
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        
    return test_count, markers

def main():
    # Get the test directory
    test_dir = Path("tests")
    if not test_dir.exists():
        print("Tests directory not found!")
        return
    
    total_tests = 0
    marker_counts = {}
    file_results = []
    
    # Walk through all test files
    for test_file in test_dir.rglob("test_*.py"):
        if test_file.is_file():
            count, markers = count_tests_in_file(test_file)
            total_tests += count
            
            file_results.append({
                'file': str(test_file),
                'count': count,
                'markers': markers
            })
            
            # Count markers
            for marker in markers:
                marker_counts[marker] = marker_counts.get(marker, 0) + count
    
    # Output results
    print(f"=== TEST COUNT ANALYSIS ===")
    print(f"Total test files: {len(file_results)}")
    print(f"Total test functions: {total_tests}")
    print()
    
    print(f"=== MARKER DISTRIBUTION ===")
    for marker, count in sorted(marker_counts.items()):
        print(f"{marker}: {count}")
    print()
    
    print(f"=== FILES WITH MOST TESTS ===")
    file_results.sort(key=lambda x: x['count'], reverse=True)
    for result in file_results[:10]:
        print(f"{result['file']}: {result['count']} tests")
    
    # Write detailed results to log
    with open('.cursor/logs/CLI147_test_count.log', 'w') as f:
        f.write(f"=== TOTAL TEST COUNT ===\n")
        f.write(f"Total test files: {len(file_results)}\n")
        f.write(f"Total test functions: {total_tests}\n\n")
        
        f.write(f"=== MARKER DISTRIBUTION ===\n")
        for marker, count in sorted(marker_counts.items()):
            f.write(f"{marker}: {count}\n")
        f.write("\n")
        
        f.write(f"=== DETAILED FILE BREAKDOWN ===\n")
        for result in file_results:
            f.write(f"{result['file']}: {result['count']} tests, markers: {', '.join(result['markers'])}\n")

if __name__ == "__main__":
    main()
